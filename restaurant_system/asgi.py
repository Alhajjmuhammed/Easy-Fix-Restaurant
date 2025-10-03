"""
ASGI config for restaurant_system project.
It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import orders.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_system.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                orders.routing.websocket_urlpatterns
            )
        )
    ),
})