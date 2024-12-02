# consumers.py
import json
import chess
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game
from .utils import apply_move_to_board
import logging

logger = logging.getLogger(__name__)

class ChallengeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            logger.warning("Anonymous user attempted to connect via WebSocket.")
        else:
            self.user_group_name = f"user_{self.user.id}"
            self.global_group_name = "all_users"

            # Join individual user group
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )

            # Join global group
            await self.channel_layer.group_add(
                self.global_group_name,
                self.channel_name
            )

            await self.accept()
            logger.info(f"WebSocket connected for user {self.user.id}")

    async def disconnect(self, close_code):
        # Leave individual user group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

        # Leave global group
        await self.channel_layer.group_discard(
            self.global_group_name,
            self.channel_name
        )

        logger.info(f"WebSocket disconnected for user {self.user.id}")

    async def receive(self, text_data):
        # Currently, no need to handle incoming messages for challenges
        pass

    async def send_challenge_notification(self, event):
        data = event.get("data", {})
        logger.info(f"Sending data to user {self.user.id}: {data}")
        await self.send(text_data=json.dumps(data))

        
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


# consumers.py
class ChallengeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["user"].id
        self.user_group_name = f"user_{self.user_id}"

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle challenge acceptance or rejection if needed
        pass

    async def send_challenge_notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))

