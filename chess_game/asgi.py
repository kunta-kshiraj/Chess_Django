# asgi.py

import os
import django

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_game.settings")
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Now import your routing after Django has been set up
import chess_app.routing

# Define the application
application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            chess_app.routing.websocket_urlpatterns
        )
    ),
})
