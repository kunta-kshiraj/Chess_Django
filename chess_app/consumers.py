import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404


logger = logging.getLogger(__name__)

class ChallengeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        logger.info(f"User in scope: {self.user}")
        if self.user.is_anonymous:
            await self.close()
            logger.warning("Anonymous user tried to connect via WebSocket.")
        else:
            self.user_room_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(
                self.user_room_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"WebSocket connected for user {self.user.id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_room_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected for user {self.user.id}")

    async def send_challenge_notification(self, event):
        data = event.get("data", {})
        logger.info(f"Sending data to user {self.user.id}: {data}")
        await self.send(text_data=json.dumps(data))


# from channels.db import database_sync_to_async
# from django.shortcuts import get_object_or_404

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_group_name = f'game_{self.game_id}'
        self.user = self.scope['user']

        # Fetch the game asynchronously
        game = await self.get_game_async(self.game_id)

        # Validate the user's participation in the game
        is_participant = await self.is_user_participant(game, self.user)
        if not is_participant:
            await self.close()
            return

        # Add the user to the WebSocket group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Remove the user from the WebSocket group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def get_game_async(self, game_id):
        # Fetch the game object asynchronously
        return get_object_or_404(Game, id=game_id)

    @database_sync_to_async
    def is_user_participant(self, game, user):
        # Validate if the user is a participant
        return user == game.player1 or user == game.player2

    async def send_game_update(self, event):
        data = event.get("data", {})
        logger.info(f"Sending game update to user {self.user.id}: {data}")
        await self.send(text_data=json.dumps(data))