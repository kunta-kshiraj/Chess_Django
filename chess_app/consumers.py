# Chess_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game
# from .utils import fen_to_dict, move_piece

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'
        self.user = self.scope['user']

        # Verify if the user is part of this game
        game = await database_sync_to_async(Game.objects.get)(id=self.game_id)

        # Fetch player IDs asynchronously
        player1_id = await database_sync_to_async(lambda: game.player1_id)()
        player2_id = await database_sync_to_async(lambda: game.player2_id)()

        if self.user.id != player1_id and self.user.id != player2_id:
            await self.close()
        else:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', 'move')

        if action == 'move':
            move = data.get('move')
            move_result = await self.process_move(move)
            if move_result['valid']:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_update',
                        'message': {
                            'type': 'move',
                            'data': move_result
                        }
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': move_result['message']
                }))
        elif action == 'resign':
            resign_result = await self.process_resign()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_update',
                    'message': {
                        'type': 'resign',
                        'data': resign_result
                    }
                }
            )

    async def process_move(self, move_input):
        game = await database_sync_to_async(Game.objects.get)(id=self.game_id)
        move_result = await database_sync_to_async(move_piece)(self.user, game, move_input)
        return move_result

    async def process_resign(self):
        game = await database_sync_to_async(Game.objects.get)(id=self.game_id)
        if not game:
            return {'valid': False, 'message': 'No active game.'}
        if game.status != 'in_progress':
            return {'valid': False, 'message': 'Game is not in progress.'}

        # Determine the winner
        winner = await database_sync_to_async(lambda: game.player2 if game.player1_id == self.user.id else game.player1)()
        game.status = 'finished'
        game.winner = winner
        game.result = '1-0' if winner.id == game.player1_id else '0-1'
        await database_sync_to_async(game.save)()
        return {
            'valid': True,
            'message': f'{self.user.username} has resigned. {winner.username} wins.',
            'status': game.status,
            'winner': winner.username,
            'result': game.result
        }

    async def game_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
        else:
            self.group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        pass  # Not expecting any messages from the client

    async def notify(self, event):
        # Send notification to client
        await self.send(text_data=json.dumps(event['message']))
