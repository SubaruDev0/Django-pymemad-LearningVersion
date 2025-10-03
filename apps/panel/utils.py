"""
Utilidades para el panel de administración
Este módulo contiene funciones auxiliares para el panel
"""

# =====================================================================
# IMPORTACIONES ESTÁNDAR DE PYTHON
# =====================================================================
import logging

# =====================================================================
# IMPORTACIONES DE TERCEROS
# =====================================================================
import boto3
from bs4 import BeautifulSoup

# =====================================================================
# IMPORTACIONES DE DJANGO
# =====================================================================
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django_redis import get_redis_connection
from parler.utils.context import switch_language
from typing import Union, IO # para save_file_to_s3
from datetime import datetime # para save_file_to_s3
# =====================================================================
# IMPORTACIONES LOCALES
# =====================================================================


# =====================================================================
# CONFIGURACIÓN
# =====================================================================
logger = logging.getLogger(__name__)


# =====================================================================
# =====================================================================
#                    SECCIÓN 1: UTILIDADES GENERALES
# =====================================================================
# =====================================================================

def normalize_phone_number(phone):
    """
    Normaliza el número de teléfono para asegurarse de que tenga el prefijo 569.

    Args:
        phone (str): Número de teléfono ingresado por el usuario.

    Returns:
        str: Número de teléfono normalizado.
    """
    phone = phone.strip()  # Eliminar espacios al inicio y al final
    if not phone.startswith("569"):
        phone = f"569{phone}"
    return phone


# =====================================================================
# =====================================================================
#                  SECCIÓN 2: PROCESAMIENTO HTML
# =====================================================================
# =====================================================================

def segment_html_with_placeholders(html):
    """
    Segmenta HTML reemplazando texto con placeholders para traducción.
    
    Args:
        html (str): HTML a segmentar
        
    Returns:
        tuple: HTML con placeholders y diccionario de placeholders
    """
    soup = BeautifulSoup(html, 'html.parser')
    placeholders = {}
    count = 1

    for text_node in soup.find_all(string=True):
        text = text_node.strip()
        if text:
            placeholder = f"{{{{TEXT_{count}}}}}"
            placeholders[placeholder] = text
            text_node.replace_with(placeholder)
            count += 1

    return str(soup), placeholders


def reintegrate_translations(html_with_placeholders, translated_placeholders):
    """
    Reintegra las traducciones en el HTML con placeholders.
    
    Args:
        html_with_placeholders (str): HTML con placeholders
        translated_placeholders (dict): Diccionario con traducciones
        
    Returns:
        str: HTML con traducciones reintegradas
    """
    for placeholder, translated_text in translated_placeholders.items():
        html_with_placeholders = html_with_placeholders.replace(placeholder, translated_text)
    return html_with_placeholders


# =====================================================================
# =====================================================================
#                SECCIÓN 3: NOTIFICACIONES POR EMAIL
# =====================================================================
# =====================================================================

def send_translation_complete_email(user_email, post_title, post_id):
    """
    Envía un correo electrónico notificando que la traducción se completó.
    
    Args:
        user_email (str): Email del usuario
        post_title (str): Título del post
        post_id (int): ID del post
    """
    subject = f"Traducción completada: {post_title}"

    message = f"""
    Hola,

    El proceso de traducción para el artículo "{post_title}" (ID: {post_id}) ha sido completado exitosamente.

    Ya puedes revisar las traducciones en inglés y portugués en el panel de administración.

    Saludos,
    El equipo de {settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Nuestro Sitio'}
    """

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
        cc=settings.ADMIN_EMAIL_NOTIFICATIONS if hasattr(settings, 'ADMIN_EMAIL_NOTIFICATIONS') else []
    )

    try:
        email.send(fail_silently=False)
        logger.info(f"Email de traducción completada enviado a {user_email}")
    except Exception as e:
        logger.error(f"Error enviando email de traducción completada: {e}")


def send_translation_error_email(user_email, post_id, error_message):
    """
    Envía un correo electrónico notificando que hubo un error en la traducción.
    
    Args:
        user_email (str): Email del usuario
        post_id (int): ID del post
        error_message (str): Mensaje de error
    """
    subject = f"Error en traducción del post #{post_id}"

    message = f"""
    Hola,

    Ha ocurrido un error al intentar traducir el artículo con ID: {post_id}.

    Error: {error_message}

    Por favor, intenta nuevamente o contacta al equipo de soporte si el problema persiste.

    Saludos,
    El equipo de {settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Nuestro Sitio'}
    """

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
        cc=settings.ADMIN_EMAIL_NOTIFICATIONS if hasattr(settings, 'ADMIN_EMAIL_NOTIFICATIONS') else []
    )

    try:
        email.send(fail_silently=False)
        logger.warning(f"Email de error de traducción enviado a {user_email}")
    except Exception as e:
        logger.error(f"Error enviando email de error de traducción: {e}")



# =====================================================================
# =====================================================================
#                  SECCIÓN 5: GESTIÓN DE CACHÉ
# =====================================================================
# =====================================================================

def clear_cache_for_post(post, deep_clean=True):
    """
    Limpia TODO el cache relacionado con un post, incluyendo:
    - Cache de vistas
    - Cache de traducciones
    - Cache del middleware
    - Cache de componentes
    - Cache del panel de administración
    
    Args:
        post: Instancia del post
        deep_clean (bool): Si realizar limpieza profunda
        
    Returns:
        int: Número de claves eliminadas
    """
    try:
        deleted_count = 0
        redis_conn = get_redis_connection("default")
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

        # 1. Limpiar cache específico del post por ID
        patterns_to_clear = [
            f"{prefix}:*post_{post.pk}*",
            f"{prefix}:*post-{post.pk}*",
            f"{prefix}:*post:{post.pk}*",
            f"{prefix}:*post/{post.pk}*",
            f"{prefix}:*post_{post.pk}_*",
            f"{prefix}:*postdetail*{post.pk}*",
            f"{prefix}:*detail*{post.pk}*",
        ]

        # 2. Limpiar cache de las URLs del post en todos los idiomas
        for lang_code, _ in settings.LANGUAGES:
            try:
                with switch_language(post, lang_code):
                    if post.slug and post.publish:
                        # URL patterns del post
                        year = post.publish.year
                        month = post.publish.month
                        day = post.publish.day

                        # Diferentes formatos de URL que podrían estar cacheados
                        url_patterns = [
                            f"*/{lang_code}/noticias/{year}/{month:02d}/{day:02d}/{post.slug}*",
                            f"*/noticias/{year}/{month:02d}/{day:02d}/{post.slug}*",
                            f"*/{lang_code}/news/{year}/{month:02d}/{day:02d}/{post.slug}*",
                        ]

                        for url_pattern in url_patterns:
                            patterns_to_clear.append(f"{prefix}:{url_pattern}")
                            patterns_to_clear.append(f"{prefix}:views.decorators.cache.cache_page{url_pattern}")
                            patterns_to_clear.append(f"{prefix}:views.decorators.cache.cache_header{url_pattern}")
                            patterns_to_clear.append(f"{prefix}:GET:{url_pattern}")
                            patterns_to_clear.append(f"{prefix}:HEAD:{url_pattern}")
            except Exception as e:
                logger.warning(f"Error limpiando cache para idioma {lang_code}: {e}")

        # 3. Limpiar cache del panel de administración
        panel_patterns = [
            f"{prefix}:*panel*post*{post.pk}*",
            f"{prefix}:*update*{post.pk}*",
            f"{prefix}:*update*",  
            f"{prefix}:*panel/post/*",
        ]
        patterns_to_clear.extend(panel_patterns)

        # 4. Limpiar cache de Parler (traducciones)
        parler_patterns = [
            f"{prefix}:*parler*post*{post.pk}*",
            f"{prefix}:*translation*{post.pk}*",
            f"{prefix}:*post_{post.pk}_translation*",
        ]
        patterns_to_clear.extend(parler_patterns)

        # 5. Limpiar cache de componentes relacionados
        component_patterns = [
            f"{prefix}:*latest_posts*",
            f"{prefix}:*recent_posts*",
            f"{prefix}:*home*",
            f"{prefix}:*sidebar*",
            f"{prefix}:*category*{post.category.pk if post.category else ''}*",
            f"{prefix}:*tag*",
            f"{prefix}:*list*",
            f"{prefix}:*page*",
        ]
        patterns_to_clear.extend(component_patterns)

        # 6. Ejecutar limpieza con Redis SCAN
        for pattern in patterns_to_clear:
            cursor = 0
            while True:
                cursor, keys = redis_conn.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted_count += len(keys)
                    redis_conn.delete(*keys)
                    logger.debug(f"Eliminadas {len(keys)} claves con patrón: {pattern}")
                if cursor == 0:
                    break

        # 7. Limpiar cache adicional usando las claves directas de Django
        django_keys_to_delete = []

        # Claves específicas del post
        django_keys_to_delete.extend([
            f'post_{post.pk}',
            f'post_detail_{post.pk}',
            f'post-{post.pk}',
        ])

        # Claves por idioma
        for lang_code, _ in settings.LANGUAGES:
            django_keys_to_delete.extend([
                f'post_{post.pk}_{lang_code}',
                f'post_detail_{post.pk}_{lang_code}',
                f'post_translations_{post.pk}_{lang_code}',
            ])

        # Eliminar claves directas
        for key in django_keys_to_delete:
            try:
                cache.delete(key)
                deleted_count += 1
            except:
                pass

        # 8. Si deep_clean está activado, limpiar aún más agresivamente
        if deep_clean:
            # Limpiar todo el cache de listas y páginas
            aggressive_patterns = [
                f"{prefix}:*noticias*",
                f"{prefix}:*news*",
                f"{prefix}:*GET:*",  # Todo el cache del middleware GET
                f"{prefix}:*HEAD:*",  # Todo el cache del middleware HEAD
            ]

            for pattern in aggressive_patterns:
                cursor = 0
                count = 0
                while count < 1000:  # Limitar a 1000 claves por patrón
                    cursor, keys = redis_conn.scan(cursor, match=pattern, count=50)
                    if keys:
                        deleted_count += len(keys)
                        count += len(keys)
                        redis_conn.delete(*keys)
                    if cursor == 0:
                        break

        logger.info(f"✅ Cache limpiado completamente para post {post.pk}: {deleted_count} claves eliminadas")

        # 9. Invalidar cache de sesión si es necesario
        _invalidate_session_cache_for_post(post)

        return deleted_count

    except Exception as e:
        logger.error(f"❌ Error limpiando cache para post {post.pk}: {e}")
        # En caso de error, intentar limpieza básica
        try:
            cache.clear()  # Nuclear option
            logger.warning("Cache completamente limpiado debido a error")
        except:
            pass
        return 0


def _invalidate_session_cache_for_post(post):
    """
    Invalida el cache de sesión relacionado con el post.
    
    Args:
        post: Instancia del post
    """
    try:
        redis_conn = get_redis_connection("default")
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

        # Incrementar versión del cache para forzar invalidación
        version_key = f"{prefix}:cache_version:post:{post.pk}"
        redis_conn.incr(version_key)

    except Exception as e:
        logger.error(f"Error invalidando cache de sesión: {e}")


def clear_panel_cache():
    """
    Limpia específicamente el cache del panel de administración.
    
    Returns:
        int: Número de claves eliminadas
    """
    try:
        redis_conn = get_redis_connection("default")
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

        patterns = [
            f"{prefix}:*panel*",
            f"{prefix}:*admin*",
            f"{prefix}:*dashboard*",
            f"{prefix}:*update*",
        ]

        deleted = 0
        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = redis_conn.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += len(keys)
                    redis_conn.delete(*keys)
                if cursor == 0:
                    break

        logger.info(f"Cache del panel limpiado: {deleted} claves eliminadas")
        return deleted

    except Exception as e:
        logger.error(f"Error limpiando cache del panel: {e}")
        return 0


# =====================================================================
# =====================================================================
#                    SECCIÓN (MOVIDO DE CORE): ALMACENAMIENTO EN S3
# =====================================================================
# =====================================================================

def save_file_to_s3(
        file_obj: Union[IO, any],
        filename: str,
        folder_path: str = "uploads",
        bucket_name: str = None,
        file_extension: str = None,
        add_timestamp: bool = True
):
    """
    Función genérica para subir archivos a Amazon S3.

    NOTA: El bucket debe tener configuradas las políticas de acceso público
    ya que no se usa ACL en la subida para compatibilidad con buckets modernos.

    Args:
        file_obj: Objeto de archivo temporal o file-like object
        filename (str): Nombre base del archivo (sin extensión si se proporciona file_extension)
        folder_path (str, optional): Ruta de la carpeta en S3. Default: "uploads"
        bucket_name (str, optional): Nombre del bucket S3. Default: desde settings
        file_extension (str, optional): Extensión del archivo (ej: "xlsx", "pdf"). Default: detectada del filename
        add_timestamp (bool, optional): Si agregar timestamp al nombre. Default: True

    Returns:
        str: URL pública del archivo en S3 si la carga fue exitosa
        None: Si ocurre un error

    Ejemplos:
        # Para Excel
        save_file_to_s3(temp_file, "reporte_informes", "excel/informes", file_extension="xlsx")

        # Para PDF
        save_file_to_s3(pdf_file, "documento", "pdfs/contratos", file_extension="pdf")
    """

    # Configuración de AWS desde settings o valores por defecto
    aws_access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    aws_secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    aws_region = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
    default_bucket = bucket_name or getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'loginfor-cdn')

    if not aws_access_key or not aws_secret_key:
        logger.error("Credenciales AWS no configuradas")
        return None

    # Detectar extensión si no se proporciona
    if not file_extension:
        if '.' in filename:
            file_extension = filename.split('.')[-1]
        else:
            file_extension = 'bin'

    # Limpiar nombre de archivo
    clean_filename = filename.split('.')[0] if '.' in filename else filename

    # Generar nombre único si se requiere timestamp
    if add_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{clean_filename}_{timestamp}.{file_extension}"
    else:
        unique_filename = f"{clean_filename}.{file_extension}"

    # Construir ruta completa en S3
    s3_key = f"{folder_path.strip('/')}/{unique_filename}"

    try:
        # Crear cliente S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )

        # Subir archivo sin ACL (el bucket debe tener políticas públicas configuradas)
        s3_client.upload_fileobj(
            file_obj,
            default_bucket,
            s3_key
        )

        # Construir URL pública
        file_url = f"https://{default_bucket}.s3.{aws_region}.amazonaws.com/{s3_key}"

        logger.info(f"Archivo {unique_filename} subido exitosamente a S3: {s3_key}")
        return file_url

    except Exception as e:
        logger.error(f'Error al subir archivo a S3: {str(e)}')
        return None