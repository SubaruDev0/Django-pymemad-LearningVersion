# pymemadweb/middleware.py - Versión mejorada

from django.core.cache import cache
from django_redis import get_redis_connection
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SmartCacheInvalidationMiddleware:
    """
    Middleware para invalidar cache inteligentemente cuando
    los editores/periodistas hacen cambios
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesar la request
        response = self.get_response(request)

        # Si es una petición POST/PUT/DELETE desde el panel
        # Excluir rutas de perfil de usuario que no afectan cache público
        if (request.method in ['POST', 'PUT', 'DELETE', 'PATCH'] and
                not request.path.startswith('/accounts/profile/') and
                (request.path.startswith('/dashboard/') or
                 request.path.startswith('/admin/') or
                 '/update/' in request.path or
                 '/create/' in request.path or
                 '/delete/' in request.path)):
            # Limpiar cache relacionado
            self.invalidate_related_cache(request)

            # Agregar headers para no cachear esta respuesta
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['X-Cache-Status'] = 'BYPASS'

        return response

    def invalidate_related_cache(self, request):
        """Invalida cache relacionado con la acción"""
        try:
            # Usar Redis directamente para mejor control
            redis_conn = get_redis_connection("default")
            prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

            # Patrones a limpiar cuando se edita contenido
            patterns_to_clear = [
                f"{prefix}:*home*",
                f"{prefix}:*latest*",
                f"{prefix}:*recent*",
                f"{prefix}:*list*",
                f"{prefix}:*page*",
                f"{prefix}:*GET:*",  # Cache del middleware
                f"{prefix}:*HEAD:*",
            ]

            # Si es una acción sobre noticias o contenido
            if 'news' in request.path or 'magazine' in request.path:
                patterns_to_clear.extend([
                    f"{prefix}:*news*",
                    f"{prefix}:*magazine*",
                    f"{prefix}:*members*",
                ])
            
            # Si es una acción sobre miembros
            if 'members' in request.path:
                patterns_to_clear.extend([
                    f"{prefix}:*members*",
                    f"{prefix}:*directory*",
                ])

            # Limpiar usando SCAN para evitar bloqueos
            total_deleted = 0
            for pattern in patterns_to_clear:
                cursor = 0
                batch_count = 0
                while batch_count < 100:  # Limitar a 100 keys por patrón
                    cursor, keys = redis_conn.scan(cursor, match=pattern, count=10)
                    if keys:
                        redis_conn.delete(*keys)
                        total_deleted += len(keys)
                        batch_count += len(keys)
                    if cursor == 0:
                        break

            if total_deleted > 0:
                logger.info(
                    f"🧹 Cache invalidado por {request.method} {request.path}: {total_deleted} claves eliminadas")

        except Exception as e:
            logger.error(f"Error clearing cache in middleware: {e}")


class NoCacheForStaffMiddleware:
    """
    Desactiva cache completamente para usuarios staff/admin
    """

    # URLs que NUNCA deben cachearse
    NO_CACHE_PATHS = [
        '/dashboard/',  # Panel de control del proyecto
        '/admin/',
        '/api/',  # Por si agregas API en el futuro
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/',  # Todas las rutas de accounts
        '/i18n/',
        '/contact/',
        '/captcha/',  # Descomentado cuando actives captcha
        '/refresh-captcha/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar si debe omitirse el cache
        should_skip_cache = self._should_skip_cache(request)

        if should_skip_cache:
            # Marcar para no cachear
            request._cache_update_cache = False
            # También establecer un atributo personalizado
            request._force_no_cache = True

        response = self.get_response(request)

        # Agregar headers anti-cache si es necesario
        if should_skip_cache:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Vary'] = 'Cookie'

            # Agregar header informativo
            if hasattr(request, 'user') and request.user.is_authenticated:
                if request.user.is_staff:
                    response['X-Cache-Status'] = 'BYPASS-STAFF'
                else:
                    response['X-Cache-Status'] = 'BYPASS-AUTH'
            else:
                response['X-Cache-Status'] = 'BYPASS-PATH'

        return response

    def _should_skip_cache(self, request):
        """Determina si se debe omitir el cache para esta request"""

        # 1. Nunca cachear ciertas rutas
        for path in self.NO_CACHE_PATHS:
            if request.path.startswith(path):
                return True

        # 2. No cachear para usuarios autenticados (especialmente staff)
        if hasattr(request, 'user') and request.user.is_authenticated:
            return True

        # 3. No cachear requests con ciertos parámetros
        if request.GET.get('preview') or request.GET.get('draft'):
            return True

        # 4. No cachear métodos que no sean GET/HEAD
        if request.method not in ('GET', 'HEAD'):
            return True

        return False


class CacheDebugMiddleware:
    """
    Middleware para debug - agrega headers informativos sobre el cache
    Solo activar en desarrollo
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Agregar timestamp de inicio
        import time
        start_time = time.time()

        response = self.get_response(request)

        # Solo en DEBUG
        if settings.DEBUG:
            # Tiempo de procesamiento
            duration = time.time() - start_time
            response['X-Process-Time'] = f"{duration:.3f}s"

            # Estado del cache
            if hasattr(request, '_cache_update_cache'):
                response['X-Cache-Update'] = str(request._cache_update_cache)

            # Si fue servido desde cache
            if hasattr(response, '_from_cache'):
                response['X-From-Cache'] = 'HIT'
            else:
                response['X-From-Cache'] = 'MISS'

        return response