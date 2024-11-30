import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_game.settings")
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chess_app.routing
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chess_app.routing.websocket_urlpatterns
        )
    ),
})
