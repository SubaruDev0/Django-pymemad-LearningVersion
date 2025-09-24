# redis_security.py - Configuración de seguridad para Redis Cloud

import redis
import hashlib
import json
from django.conf import settings
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class SecureRedisClient:
    """Cliente Redis con medidas de seguridad adicionales"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_BASE_URL
        self.client = None
        self.key_prefix = self._get_environment_prefix()
        
    def _get_environment_prefix(self):
        """Prefijo basado en el ambiente para evitar colisiones"""
        if settings.DEBUG:
            return "dev_"
        return "prod_"
    
    def get_client(self):
        """Obtener cliente Redis con reintentos y timeout"""
        if not self.client:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                connection_pool_kwargs={
                    'max_connections': 50,
                    'retry_on_timeout': True,
                    'retry_on_error': [redis.ConnectionError],
                }
            )
        return self.client
    
    def safe_key(self, key):
        """Generar key segura con prefijo de ambiente"""
        # Evitar keys muy largas
        if len(key) > 200:
            key = hashlib.sha256(key.encode()).hexdigest()
        return f"{self.key_prefix}{key}"
    
    def set_with_validation(self, key, value, ex=None):
        """Set con validación de datos"""
        try:
            # Validar tamaño del valor
            if isinstance(value, str) and len(value) > 512 * 1024:  # 512KB max
                logger.warning(f"Valor muy grande para key {key}: {len(value)} bytes")
                return False
            
            # Serializar objetos complejos
            if not isinstance(value, (str, int, float, bytes)):
                value = json.dumps(value)
            
            safe_key = self.safe_key(key)
            client = self.get_client()
            
            # TTL por defecto de 24 horas para evitar memory leaks
            if ex is None:
                ex = 86400  # 24 horas
            
            return client.set(safe_key, value, ex=ex)
            
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            return False
    
    def get_with_fallback(self, key, default=None):
        """Get con fallback en caso de error"""
        try:
            safe_key = self.safe_key(key)
            client = self.get_client()
            value = client.get(safe_key)
            
            # Intentar deserializar JSON
            if value and value.startswith('{') or value.startswith('['):
                try:
                    return json.loads(value)
                except:
                    pass
            
            return value if value is not None else default
            
        except redis.TimeoutError:
            logger.warning(f"Timeout getting key {key}")
            return default
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return default
    
    def rate_limit(self, identifier, max_requests=10, window=60):
        """
        Rate limiting simple
        
        Args:
            identifier: IP o user ID
            max_requests: Máximo de requests
            window: Ventana de tiempo en segundos
        
        Returns:
            True si está dentro del límite, False si excede
        """
        try:
            key = self.safe_key(f"rate_limit:{identifier}")
            client = self.get_client()
            
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = pipe.execute()
            
            current_requests = results[0]
            
            if current_requests > max_requests:
                logger.warning(f"Rate limit exceeded for {identifier}: {current_requests}/{max_requests}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            # En caso de error, permitir el request
            return True
    
    def cleanup_old_keys(self, pattern="*", older_than_days=7):
        """Limpiar keys antiguas (ejecutar periódicamente)"""
        try:
            client = self.get_client()
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = client.scan(
                    cursor, 
                    match=f"{self.key_prefix}{pattern}",
                    count=100
                )
                
                for key in keys:
                    ttl = client.ttl(key)
                    # Si no tiene TTL, ponerle uno
                    if ttl == -1:
                        client.expire(key, older_than_days * 86400)
                        deleted += 1
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleaned up {deleted} keys without TTL")
            return deleted
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0


# Decorador para rate limiting
def rate_limit_decorator(max_requests=10, window=60, identifier_func=None):
    """
    Decorador para aplicar rate limiting a vistas
    
    Uso:
        @rate_limit_decorator(max_requests=5, window=60)
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            redis_client = SecureRedisClient()
            
            # Obtener identificador (IP por defecto)
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = request.META.get('REMOTE_ADDR', 'unknown')
            
            # Verificar rate limit
            if not redis_client.rate_limit(identifier, max_requests, window):
                from django.http import HttpResponse
                return HttpResponse(
                    "Rate limit exceeded. Please try again later.",
                    status=429
                )
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# Cache seguro con validación
class SecureCache:
    """Wrapper para cache de Django con seguridad adicional"""
    
    @staticmethod
    def set(key, value, timeout=None):
        """Set con validación"""
        redis_client = SecureRedisClient()
        return redis_client.set_with_validation(key, value, ex=timeout)
    
    @staticmethod
    def get(key, default=None):
        """Get con fallback"""
        redis_client = SecureRedisClient()
        return redis_client.get_with_fallback(key, default)


# Monitoreo de Redis
def monitor_redis_health():
    """
    Verificar salud de Redis
    Ejecutar con Celery beat cada 5 minutos
    """
    try:
        redis_client = SecureRedisClient()
        client = redis_client.get_client()
        
        # Ping
        client.ping()
        
        # Verificar memoria
        info = client.info('memory')
        used_memory_mb = info['used_memory'] / 1024 / 1024
        
        # En plan gratuito tienes 30MB
        if used_memory_mb > 25:  # 83% de 30MB
            logger.warning(f"Redis memory usage high: {used_memory_mb:.2f}MB / 30MB")
            
            # Limpiar keys viejas
            redis_client.cleanup_old_keys()
        
        # Verificar número de conexiones
        info_clients = client.info('clients')
        connected_clients = info_clients['connected_clients']
        
        if connected_clients > 40:  # Plan gratuito tiene límite de ~50
            logger.warning(f"High number of Redis connections: {connected_clients}")
        
        return {
            'status': 'healthy',
            'memory_mb': used_memory_mb,
            'connections': connected_clients
        }
        
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }