# apps/core/tasks.py - Tareas de mantenimiento de cache
from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django_redis import get_redis_connection
from parler.utils.context import switch_language
import logging
from datetime import timedelta

from apps.landing.models import Category, Post

logger = logging.getLogger(__name__)


@shared_task(queue='short_tasks', bind=True, max_retries=3)
def warm_cache_home(self):
    """Pre-calienta el cache de la página home en todos los idiomas"""
    try:
        client = Client()
        warmed = 0
        errors = 0

        for lang_code, lang_name in settings.LANGUAGES:
            try:
                # URLs a calentar para el home
                urls_to_warm = [
                    f'/{lang_code}/',  # Home con idioma
                    '/',  # Home sin idioma (redirige)
                ]

                for url in urls_to_warm:
                    response = client.get(
                        url,
                        HTTP_ACCEPT_LANGUAGE=lang_code,
                        follow=True  # Seguir redirecciones
                    )

                    if response.status_code == 200:
                        warmed += 1
                        logger.info(f"✅ Cache calentado: {url} ({lang_code})")
                    else:
                        errors += 1
                        logger.warning(f"⚠️ Error {response.status_code} en {url}")

            except Exception as e:
                errors += 1
                logger.error(f"❌ Error calentando home {lang_code}: {e}")

        # Calentar también componentes del home
        _warm_home_components()

        result = f"Home cache calentado: {warmed} páginas OK, {errors} errores"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error general en warm_cache_home: {e}")
        self.retry(countdown=300)  # Reintentar en 5 minutos


@shared_task(queue='short_tasks', bind=True, max_retries=3)
def warm_cache_recent_posts(self, limit=20):
    """Pre-calienta el cache de posts recientes"""
    try:
        warmed = 0
        errors = 0

        # Obtener posts publicados recientemente
        posts = Post.published.select_related('category').prefetch_related('tags').order_by('-publish')[:limit]

        if not posts:
            logger.warning("No hay posts publicados para calentar")
            return "No hay posts para calentar"

        client = Client()

        for post in posts:
            # Calentar cada idioma disponible del post
            for lang_code, _ in settings.LANGUAGES:
                try:
                    # Verificar si el post tiene traducción en este idioma
                    if not post.has_translation(lang_code):
                        continue

                    with switch_language(post, lang_code):
                        if not post.slug:  # Si no hay slug, saltar
                            continue

                        url = post.get_absolute_url()

                        # Hacer request
                        response = client.get(
                            url,
                            HTTP_ACCEPT_LANGUAGE=lang_code,
                            follow=True
                        )

                        if response.status_code == 200:
                            warmed += 1
                            logger.debug(f"✅ Post {post.pk} calentado en {lang_code}: {url}")
                        else:
                            errors += 1
                            logger.warning(f"⚠️ Error {response.status_code} para post {post.pk} en {lang_code}")

                except Exception as e:
                    errors += 1
                    logger.error(f"❌ Error calentando post {post.pk} en {lang_code}: {e}")

        # También calentar las páginas de lista
        _warm_list_pages()

        result = f"Posts cache calentado: {warmed} páginas OK, {errors} errores"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error general en warm_cache_recent_posts: {e}")
        self.retry(countdown=300)


@shared_task(queue='short_tasks')
def clear_old_sessions():
    """Limpia sesiones antiguas del cache de forma más eficiente"""
    try:
        redis_conn = get_redis_connection("default")
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

        # Patrones de sesión
        patterns = [
            f"{prefix}:*session*",
            f"{prefix}:*sessionid*",
        ]

        processed = 0
        expired = 0

        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = redis_conn.scan(cursor, match=pattern, count=100)

                if keys:
                    pipeline = redis_conn.pipeline()

                    for key in keys:
                        # Obtener TTL
                        ttl = redis_conn.ttl(key)

                        # Si no tiene TTL o es mayor a 7 días
                        if ttl == -1:
                            # Sin expiración, poner 1 día
                            pipeline.expire(key, 86400)
                            expired += 1
                        elif ttl > 604800:  # Más de 7 días
                            # Reducir a 1 día
                            pipeline.expire(key, 86400)
                            expired += 1

                        processed += 1

                    pipeline.execute()

                if cursor == 0:
                    break

        result = f"Sesiones procesadas: {processed}, expiración ajustada: {expired}"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error limpiando sesiones: {e}")
        return f"Error en limpieza de sesiones: {str(e)}"


@shared_task(queue='short_tasks')
def generate_cache_stats():
    """Genera estadísticas detalladas del cache"""
    try:
        redis_conn = get_redis_connection("default")

        # Obtener información general
        info = redis_conn.info()
        memory_info = redis_conn.info('memory')
        stats = redis_conn.info('stats')

        # Calcular hit rate
        hits = stats.get('keyspace_hits', 0)
        misses = stats.get('keyspace_misses', 0)
        total_ops = hits + misses
        hit_rate = (hits / total_ops * 100) if total_ops > 0 else 0

        # Contar keys por tipo
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')
        key_distribution = {}

        patterns = {
            'posts': f"{prefix}:*post*",
            'pages': f"{prefix}:*page*",
            'sessions': f"{prefix}:*session*",
            'home': f"{prefix}:*home*",
            'categories': f"{prefix}:*category*",
            'tags': f"{prefix}:*tag*",
            'middleware': f"{prefix}:*GET*",
            'celery': f"{prefix}:*celery*",
        }

        total_keys = redis_conn.dbsize()

        for key_type, pattern in patterns.items():
            count = 0
            cursor = 0
            while True:
                cursor, keys = redis_conn.scan(cursor, match=pattern, count=1000)
                count += len(keys)
                if cursor == 0:
                    break
            key_distribution[key_type] = count

        # Crear reporte
        report = {
            'timestamp': timezone.now().isoformat(),
            'server': {
                'version': info.get('redis_version'),
                'uptime_days': info.get('uptime_in_days'),
                'connected_clients': info.get('connected_clients'),
            },
            'memory': {
                'used': memory_info.get('used_memory_human'),
                'peak': memory_info.get('used_memory_peak_human'),
                'rss': memory_info.get('used_memory_rss_human'),
                'fragmentation_ratio': memory_info.get('mem_fragmentation_ratio'),
            },
            'performance': {
                'total_keys': total_keys,
                'hits': hits,
                'misses': misses,
                'hit_rate': round(hit_rate, 2),
                'ops_per_sec': stats.get('instantaneous_ops_per_sec'),
            },
            'key_distribution': key_distribution,
            'top_keys_by_memory': _get_top_keys_by_memory(redis_conn, 10),
        }

        # Log el reporte
        logger.info(f"📊 Cache stats generadas: {report['performance']}")

        # Guardar en cache para consulta posterior
        cache.set('cache_stats_report', report, timeout=3600)  # 1 hora

        # Si el hit rate es muy bajo, alertar
        if hit_rate < 50:
            logger.warning(f"⚠️ Hit rate bajo: {hit_rate:.2f}%")
            _notify_low_hit_rate(hit_rate, report)

        return report

    except Exception as e:
        logger.error(f"Error generando stats: {e}")
        return None


@shared_task(queue='short_tasks')
def warm_cache_categories():
    """Pre-calienta el cache de páginas de categorías"""
    try:
        client = Client()
        warmed = 0

        categories = Category.objects.filter(posts__status='PUBLISHED').distinct()

        for category in categories:
            # Category no es traducible, así que calentamos para cada idioma
            # usando el mismo slug (las categorías se mostrarán igual en todos los idiomas)
            for lang_code, _ in settings.LANGUAGES:
                try:
                    if category.slug:
                        url = reverse('landing:news_list_by_category', kwargs={'category_slug': category.slug})
                        response = client.get(url, HTTP_ACCEPT_LANGUAGE=lang_code)

                        if response.status_code == 200:
                            warmed += 1
                            logger.debug(f"Categoría {category.name} calentada para {lang_code}")

                except Exception as e:
                    logger.error(f"Error calentando categoría {category.pk} para {lang_code}: {e}")

        return f"Categorías calentadas: {warmed}"

    except Exception as e:
        logger.error(f"Error en warm_cache_categories: {e}")
        return "Error calentando categorías"


@shared_task(queue='long_tasks')
def cleanup_orphaned_cache():
    """Limpia entradas de cache huérfanas (sin post asociado)"""
    try:
        redis_conn = get_redis_connection("default")
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

        # Obtener todos los IDs de posts válidos
        valid_post_ids = set(Post.objects.values_list('id', flat=True))

        # Buscar keys de posts
        pattern = f"{prefix}:*post_*"
        orphaned = 0

        cursor = 0
        while True:
            cursor, keys = redis_conn.scan(cursor, match=pattern, count=100)

            for key in keys:
                key_str = key.decode('utf-8')
                # Extraer ID del post de la key
                try:
                    # Formato esperado: prefix:post_123_*
                    parts = key_str.split('post_')
                    if len(parts) > 1:
                        post_id_part = parts[1].split('_')[0]
                        if post_id_part.isdigit():
                            post_id = int(post_id_part)
                            if post_id not in valid_post_ids:
                                redis_conn.delete(key)
                                orphaned += 1
                except:
                    pass

            if cursor == 0:
                break

        result = f"Cache huérfano limpiado: {orphaned} entradas"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error en cleanup_orphaned_cache: {e}")
        return "Error limpiando cache huérfano"


@shared_task(queue='short_tasks')
def comprehensive_cache_warm():
    """Calentamiento completo del cache - ejecutar cada 30 minutos"""
    try:
        results = {
            'timestamp': timezone.now().isoformat(),
            'warmed': {},
            'errors': []
        }

        # 1. Calentar home en todos los idiomas
        try:
            home_result = warm_cache_home()
            results['warmed']['home'] = home_result
        except Exception as e:
            results['errors'].append(f"Error home: {e}")

        # 2. Calentar posts más vistos (no solo recientes)
        try:
            posts_result = warm_cache_popular_posts()
            results['warmed']['popular_posts'] = posts_result
        except Exception as e:
            results['errors'].append(f"Error posts populares: {e}")

        # 3. Calentar posts recientes
        try:
            recent_result = warm_cache_recent_posts(limit=30)  # Más posts
            results['warmed']['recent_posts'] = recent_result
        except Exception as e:
            results['errors'].append(f"Error posts recientes: {e}")

        # 4. Calentar categorías activas
        try:
            categories_result = warm_cache_categories()
            results['warmed']['categories'] = categories_result
        except Exception as e:
            results['errors'].append(f"Error categorías: {e}")

        # 5. Calentar páginas de lista
        try:
            lists_result = warm_list_pages_extended()
            results['warmed']['list_pages'] = lists_result
        except Exception as e:
            results['errors'].append(f"Error páginas lista: {e}")

        # Log resumen
        total_warmed = sum(1 for v in results['warmed'].values() if v)
        logger.info(f"🔥 Cache warming completo: {total_warmed} componentes OK, {len(results['errors'])} errores")

        if results['errors']:
            logger.error(f"Errores durante warming: {results['errors']}")

        return results

    except Exception as e:
        logger.error(f"Error crítico en comprehensive_cache_warm: {e}")
        return f"Error: {str(e)}"


@shared_task(queue='short_tasks')
def warm_cache_popular_posts(days=30, limit=50):
    """Calienta posts más vistos basado en comentarios y fecha"""
    try:
        from django.db.models import Count, Q
        from datetime import timedelta

        warmed = 0
        errors = 0

        # Posts populares: más comentados o publicados recientemente
        cutoff_date = timezone.now() - timedelta(days=days)

        popular_posts = (
            Post.published
            .filter(publish__gte=cutoff_date)
            .annotate(
                comment_count=Count('comments', filter=Q(comments__active=True))
            )
            .order_by('-comment_count', '-publish')[:limit]
        )

        client = Client()

        for post in popular_posts:
            for lang_code, _ in settings.LANGUAGES:
                try:
                    if not post.has_translation(lang_code):
                        continue

                    with switch_language(post, lang_code):
                        if post.slug:
                            url = post.get_absolute_url()
                            response = client.get(
                                url,
                                HTTP_ACCEPT_LANGUAGE=lang_code,
                                follow=True
                            )

                            if response.status_code == 200:
                                warmed += 1
                            else:
                                errors += 1

                except Exception as e:
                    errors += 1
                    logger.error(f"Error calentando post popular {post.pk}: {e}")

        result = f"Posts populares calentados: {warmed} OK, {errors} errores"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error en warm_cache_popular_posts: {e}")
        return f"Error: {str(e)}"


@shared_task(queue='short_tasks')
def warm_list_pages_extended():
    """Calienta páginas de lista con paginación"""
    try:
        client = Client()
        warmed = 0

        # URLs a calentar con diferentes páginas
        list_urls = [
            '/news/',  # URL correcta para las noticias
        ]

        for lang_code, _ in settings.LANGUAGES:
            for base_url in list_urls:
                # Calentar primeras 5 páginas
                for page in range(1, 6):
                    try:
                        url = f'/{lang_code}{base_url}'
                        if page > 1:
                            url += f'?page={page}'

                        response = client.get(
                            url,
                            HTTP_ACCEPT_LANGUAGE=lang_code,
                            follow=True
                        )

                        if response.status_code == 200:
                            warmed += 1
                            logger.debug(f"✅ Lista calentada: {url}")
                        elif response.status_code == 404 and page > 1:
                            # No más páginas, salir del loop
                            break

                    except Exception as e:
                        logger.error(f"Error calentando {url}: {e}")

        return f"Páginas de lista calentadas: {warmed}"

    except Exception as e:
        logger.error(f"Error en warm_list_pages_extended: {e}")
        return f"Error: {str(e)}"

# Corregir _warm_home_components como mencionamos antes
def _warm_home_components():
    """Calienta componentes específicos del home"""
    try:
        from apps.landing.templatetags.blog_extras import (
            total_posts, show_latest_posts, show_latest_posts_home,
            get_most_commented_posts
        )

        # Simple tags - llamar sin parámetros
        total_posts()
        get_most_commented_posts(count=5)

        # Inclusion tags con contexto de idioma
        for lang_code, _ in settings.LANGUAGES:
            from django.utils import translation
            with translation.override(lang_code):
                show_latest_posts(count=5)
                show_latest_posts_home(count=3)

        logger.info("✅ Componentes del home calentados")

    except Exception as e:
        logger.error(f"Error calentando componentes: {e}")

def _warm_list_pages():
    """Calienta las páginas de lista de posts"""
    try:
        client = Client()

        for lang_code, _ in settings.LANGUAGES:
            # Calentar las primeras 3 páginas de noticias
            for page in range(1, 4):
                url = f'/{lang_code}/news/'
                if page > 1:
                    url += f'?page={page}'

                try:
                    response = client.get(url, HTTP_ACCEPT_LANGUAGE=lang_code)
                    if response.status_code == 200:
                        logger.debug(f"Lista página {page} calentada para {lang_code}")
                except:
                    pass

    except Exception as e:
        logger.error(f"Error calentando listas: {e}")

def _get_top_keys_by_memory(redis_conn, limit=10):
    """Obtiene las keys que más memoria usan"""
    try:
        key_sizes = []
        cursor = 0
        sampled = 0
        max_sample = 1000

        while sampled < max_sample:
            cursor, keys = redis_conn.scan(cursor, count=100)

            for key in keys:
                try:
                    size = redis_conn.memory_usage(key)
                    if size:
                        key_str = key.decode('utf-8')
                        key_sizes.append({
                            'key': key_str if len(key_str) <= 50 else key_str[:47] + '...',
                            'size': size,
                            'size_human': _format_bytes(size)
                        })
                        sampled += 1
                except:
                    pass

            if cursor == 0 or sampled >= max_sample:
                break

        # Ordenar y retornar top
        key_sizes.sort(key=lambda x: x['size'], reverse=True)
        return key_sizes[:limit]

    except:
        return []


def _format_bytes(bytes):
    """Formatea bytes a formato legible"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"


def _notify_low_hit_rate(hit_rate, report):
    """Notifica si el hit rate es muy bajo"""
    try:
        # Aquí podrías enviar un email, Slack, etc.
        from django.core.mail import mail_admins

        subject = f'⚠️ Cache Hit Rate Bajo: {hit_rate:.2f}%'
        message = f"""
El hit rate del cache está por debajo del 50%:

Hit Rate: {hit_rate:.2f}%
Total Hits: {report['performance']['hits']:,}
Total Misses: {report['performance']['misses']:,}
Total Keys: {report['performance']['total_keys']:,}

Memoria Usada: {report['memory']['used']}

Considera:
1. Revisar si hay muchas invalidaciones de cache
2. Aumentar el tiempo de expiración
3. Pre-calentar más contenido
        """

        mail_admins(subject, message, fail_silently=True)

    except Exception as e:
        logger.error(f"Error enviando notificación: {e}")


# Tarea de monitoreo de Redis
@shared_task(queue='short_tasks')
def monitor_redis():
    """Monitorear salud y uso de Redis Cloud"""
    try:
        redis_conn = get_redis_connection("default")
        
        # Obtener información de Redis
        info = redis_conn.info()
        memory_info = redis_conn.info('memory')
        
        # Calcular uso de memoria en MB
        memory_bytes = memory_info.get('used_memory', 0)
        memory_mb = memory_bytes / (1024 * 1024)
        
        health = {
            'status': 'healthy',
            'memory_mb': memory_mb,
            'memory_human': memory_info.get('used_memory_human', 'N/A'),
            'connected_clients': info.get('connected_clients', 0),
            'uptime_days': info.get('uptime_in_days', 0)
        }
        
        # Verificar límites
        if memory_mb > 25:  # Límite de 30MB en Redis Cloud free tier
            logger.warning(f"Redis memory high: {memory_mb:.2f}MB, clearing old cache...")
            clear_old_sessions()
            cleanup_orphaned_cache()
            health['status'] = 'warning'
            health['message'] = 'High memory usage, cleaning initiated'
        
        return health
    except Exception as e:
        logger.error(f"Error monitoring Redis: {e}")
        return {'status': 'error', 'error': str(e)}


# Nueva tarea para calentar un post específico
@shared_task(queue='short_tasks')
def warm_specific_post(post_id):
    """Calienta el cache de un post específico después de actualización"""
    try:
        from django.test import Client

        post = Post.objects.get(pk=post_id)
        client = Client()
        warmed = 0

        for lang_code, _ in settings.LANGUAGES:
            try:
                if post.has_translation(lang_code):
                    with switch_language(post, lang_code):
                        if post.slug:
                            url = post.get_absolute_url()
                            response = client.get(url, HTTP_ACCEPT_LANGUAGE=lang_code)
                            if response.status_code == 200:
                                warmed += 1
                                logger.info(f"✅ Post {post_id} calentado en {lang_code}")
            except Exception as e:
                logger.error(f"Error calentando post {post_id} en {lang_code}: {e}")

        return f"Post {post_id} calentado en {warmed} idiomas"

    except Exception as e:
        logger.error(f"Error en warm_specific_post: {e}")
        return f"Error: {str(e)}"

@shared_task(queue='short_tasks')
def cleanup_expired_captchas():
    """
    Limpia los captchas expirados de la base de datos
    """
    from captcha.models import CaptchaStore
    try:
        initial_count = CaptchaStore.objects.count()
        CaptchaStore.remove_expired()
        final_count = CaptchaStore.objects.count()
        removed = initial_count - final_count
        logger.info(f"Captchas expirados eliminados: {removed} (de {initial_count} a {final_count})")
        return removed
    except Exception as e:
        logger.error(f"Error al limpiar captchas: {str(e)}")
        return 0
