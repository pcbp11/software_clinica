"""
Middleware personalizado para desarrollo.

NoCacheMiddleware: agrega headers que fuerzan al navegador a NUNCA cachear
HTML/CSS/JS durante desarrollo (DEBUG=True). Esto evita el típico problema
de "no veo mis cambios" sin tener que hacer hard reload cada vez.

En producción (DEBUG=False) el middleware se desactiva automáticamente,
así que las páginas pueden cachearse normalmente para mejor performance.
"""
from django.conf import settings


class NoCacheMiddleware:
    """Headers no-cache solo en modo DEBUG."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if settings.DEBUG:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response
