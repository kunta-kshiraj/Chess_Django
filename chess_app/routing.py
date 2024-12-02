from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/challenges/', consumers.ChallengeConsumer.as_asgi()),
    path('ws/game/<int:game_id>/', consumers.GameConsumer.as_asgi()),
]
