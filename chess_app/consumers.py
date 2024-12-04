# consumers.py
import asyncio
from datetime import timedelta
from django.utils import timezone
import json
import chess
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game
from .utils import apply_move_to_board
import logging
from .models import OnlineUser

logger = logging.getLogger(__name__)

# consumers.py
class ChallengeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            logger.warning("Anonymous user attempted to connect via WebSocket.")
        else:
            self.user_group_name = f"user_{self.user.id}"
            self.global_group_name = "all_users"

            # Mark the user as online in the database
            await database_sync_to_async(self.mark_user_online)()

            try:
                # Join individual user group
                await self.channel_layer.group_add(
                    self.user_group_name,
                    self.channel_name
                )
                logger.info(f"User {self.user.id} joined group {self.user_group_name}")

                # Join global group
                await self.channel_layer.group_add(
                    self.global_group_name,
                    self.channel_name
                )
                logger.info(f"User {self.user.id} joined group {self.global_group_name}")

                await self.accept()
                logger.info(f"WebSocket connection established for user {self.user.id}")

                # Notify all users that this user is online
                await self.channel_layer.group_send(
                    self.global_group_name,
                    {
                        "type": "user_status",
                        "user_id": self.user.id,
                        "username": self.user.username,
                        "status": "online",
                    }
                )

                # Send the list of currently online users to the new user
                online_users = await database_sync_to_async(self.get_online_users)()
                for user in online_users:
                    if user.id != self.user.id:
                        await self.send(text_data=json.dumps({
                            "type": "user_status",
                            "user_id": user.id,
                            "username": user.username,
                            "status": "online",
                        }))

            except Exception as e:
                logger.error(f"Error during WebSocket connection for user {self.user.id}: {e}")
                await self.close()

    async def disconnect(self, close_code):
        if not self.user.is_anonymous:
            await asyncio.sleep(1)  # Wait to check if the user reconnects
            if not await self.is_user_connected():
                await database_sync_to_async(self.mark_user_offline)()
                try:
                    # Leave individual user group
                    await self.channel_layer.group_discard(
                        self.user_group_name,
                        self.channel_name
                    )
                    logger.info(f"User {self.user.id} left group {self.user_group_name}")

                    # Leave global group
                    await self.channel_layer.group_discard(
                        self.global_group_name,
                        self.channel_name
                    )
                    logger.info(f"User {self.user.id} left group {self.global_group_name}")

                    # Notify all users that this user is offline
                    await self.channel_layer.group_send(
                        self.global_group_name,
                        {
                            "type": "user_status",
                            "user_id": self.user.id,
                            "username": self.user.username,
                            "status": "offline",
                        }
                    )

                except Exception as e:
                    logger.error(f"Error during WebSocket disconnection for user {self.user.id}: {e}")

    async def is_user_connected(self):
        # Check if the user has any active connections
        return await database_sync_to_async(self._user_is_connected)()

    def _user_is_connected(self):
        try:
            online_status = self.user.online_status
            return online_status.connection_count > 0
        except OnlineUser.DoesNotExist:
            return False

    def mark_user_online(self):
        # Update or create the OnlineUser entry
        online_user, created = OnlineUser.objects.update_or_create(
            user=self.user,
            defaults={'last_seen': timezone.now(), 'connection_count': 1}
        )
        if not created:
            online_user.connection_count += 1
            online_user.save()

    def mark_user_offline(self):
        # Delete the OnlineUser entry
        OnlineUser.objects.filter(user=self.user).delete()

    def get_online_users(self):
        # Retrieve all users who are currently online
        now = timezone.now()
        timeout = now - timedelta(minutes=3)
        online_users = OnlineUser.objects.filter(last_seen__gte=timeout).exclude(user=self.user)
        logger.info(f"Online users: {[user.user.username for user in online_users]}")
        return [online_user.user for online_user in online_users]

    async def user_status(self, event):
        # Send the user status update to the WebSocket

        if event['user_id'] == self.user.id:
            return
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "user_id": event['user_id'],
            "username": event['username'],
            "status": event['status'],
        }))

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')

        if message_type == 'heartbeat':
            # Update the last_seen timestamp for the user
            await database_sync_to_async(self.update_last_seen)()
        elif message_type == 'logout':
            # Handle user logout
            await self.close()
        else:
            # Handle other message types if needed
            pass

    def update_last_seen(self):
        # Update the last_seen timestamp in the database
        OnlineUser.objects.filter(user=self.user).update(last_seen=timezone.now())

    async def send_challenge_notification(self, event):
        data = event.get("data", {})
        logger.info(f"Sending data to user {self.user.id}: {data}")
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending data to user {self.user.id}: {e}")


        
class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.game_group_name = f'game_{self.game_id}'

        # Authenticate the user
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            logger.warning("Anonymous user tried to connect via GameConsumer.")
        else:
            await self.channel_layer.group_add(
                self.game_group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"User {self.user.username} connected to game {self.game_id}.")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.game_group_name,
            self.channel_name
        )
        logger.info(f"User {self.user.username} disconnected from game {self.game_id}.")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            move = text_data_json.get('move')
            action = text_data_json.get('action')

            if action == 'resign':
                success, response = await self.handle_resign()
                if success:
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            'type': 'game_update',
                            'message': response,
                        }
                    )
                else:
                    await self.send(text_data=json.dumps(response))
            elif action == 'move' and move:
                success, response = await self.process_move(move)
                if success:
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            'type': 'game_update',
                            'message': response,
                        }
                    )
                else:
                    # Send error message back to sender
                    await self.send(text_data=json.dumps(response))
            else:
                # Invalid action
                await self.send(text_data=json.dumps({'error': 'Invalid action.'}))
        except Exception as e:
            logger.exception("Exception in receive: %s", e)
            await self.send(text_data=json.dumps({'error': 'An error occurred.'}))
            await self.close()

    async def game_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    @database_sync_to_async
    def process_move(self, move):
        try:
            game = Game.objects.get(id=self.game_id)
            chess_board = chess.Board(game.board.fen)
            current_player = game.current_turn
            opponent = game.player2 if current_player == game.player1 else game.player1
            user = self.user

            if user != current_player:
                return False, {'error': "It's not your turn."}

            try:
                new_fen = apply_move_to_board(game.board.fen, move)
                game.board.fen = new_fen
                game.board.save()

                game.move_count += 1
                game.current_turn = opponent
                game.save()

                # Check for game termination conditions
                chess_board = chess.Board(new_fen)
                if chess_board.is_checkmate():
                    game.status = 'finished'
                    game.winner = user
                    game.save()
                    return True, {
                        'move': move,
                        'fen': new_fen,
                        'status': 'finished',
                        'winner': user.username,
                        'current_turn': None,
                    }
                elif chess_board.is_stalemate():
                    game.status = 'finished'
                    game.winner = None  # Draw
                    game.save()
                    return True, {
                        'move': move,
                        'fen': new_fen,
                        'status': 'finished',
                        'winner': None,
                        'current_turn': None,
                    }
                else:
                    return True, {
                        'move': move,
                        'fen': new_fen,
                        'status': 'ongoing',
                        'current_turn': opponent.username,
                    }
            except ValueError as ve:
                return False, {'error': str(ve)}
        except Game.DoesNotExist:
            return False, {'error': "Game not found."}
        except Exception as e:
            logger.exception("Exception in process_move: %s", e)
            return False, {'error': "An error occurred while processing the move."}

    @database_sync_to_async
    def handle_resign(self):
        try:
            game = Game.objects.get(id=self.game_id)
            opponent = game.player2 if self.user == game.player1 else game.player1
            game.winner = opponent
            game.status = 'finished'
            game.save()

            return True, {
                'action': 'resign',
                'status': 'finished',
                'winner': opponent.username,
                'current_turn': None,
                'fen': game.board.fen,  # Include the final FEN
            }
        except Game.DoesNotExist:
            return False, {'error': "Game not found."}
        except Exception as e:
            logger.exception("Exception in handle_resign: %s", e)
            return False, {'error': "An error occurred while handling resignation."}


# # consumers.py
# class ChallengeConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user_id = self.scope["user"].id
#         self.user_group_name = f"user_{self.user_id}"

#         await self.channel_layer.group_add(
#             self.user_group_name,
#             self.channel_name
#         )
#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.user_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         # Handle challenge acceptance or rejection if needed
#         pass

#     async def send_challenge_notification(self, event):
#         await self.send(text_data=json.dumps(event["data"]))