"""
Utilidades compartidas para todo el proyecto
Este módulo contiene funciones auxiliares reutilizables
"""

# =====================================================================
# IMPORTACIONES ESTÁNDAR DE PYTHON
# =====================================================================
import logging
import os
import secrets
import uuid
from datetime import datetime
from typing import Union, IO

# =====================================================================
# IMPORTACIONES DE TERCEROS
# =====================================================================
import boto3

# =====================================================================
# IMPORTACIONES DE DJANGO
# =====================================================================
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.signing import TimestampSigner, Signer
from django.utils.text import slugify
from django_redis import get_redis_connection

# =====================================================================
# CONFIGURACIÓN
# =====================================================================
logger = logging.getLogger(__name__)

# Instancias globales de firmado
signer = Signer()
timestamp_signer = TimestampSigner()


# =====================================================================
# =====================================================================
#                    SECCIÓN 1: MANEJO DE ARCHIVOS
# =====================================================================
# =====================================================================

def generate_upload_path(folder, filename, use_uuid=True, uuid_length=8, preserve_name=False):
    """
    Función genérica para generar rutas de archivos subidos.
    
    Args:
        folder (str): Carpeta base donde se guardará el archivo (ej: 'posts', 'profiles', 'documents')
        filename (str): Nombre original del archivo
        use_uuid (bool): Si usar UUID para el nombre del archivo (default: True)
        uuid_length (int): Longitud del UUID a usar (default: 8)
        preserve_name (bool): Si preservar el nombre original del archivo (default: False)
        
    Returns:
        str: Ruta completa donde se guardará el archivo
        
    Examples:
        generate_upload_path('posts', 'mi-imagen.jpg')
        # Retorna: 'posts/a1b2c3d4.jpg'
        
        generate_upload_path('documents', 'archivo.pdf', preserve_name=True)
        # Retorna: 'documents/archivo-a1b2c3d4.pdf'
        
        generate_upload_path('profiles', 'foto.png', use_uuid=False, preserve_name=True)
        # Retorna: 'profiles/foto.png'
    """
    # Separar nombre y extensión
    name, extension = os.path.splitext(filename)
    
    # Limpiar la extensión (remover el punto y convertir a minúsculas)
    extension = extension.lower().lstrip('.')
    
    if use_uuid:
        uuid_str = str(uuid.uuid4())[:uuid_length]
        
        if preserve_name:
            # Slugificar el nombre original para hacerlo URL-safe
            clean_name = slugify(name)
            final_name = f"{clean_name}-{uuid_str}"
        else:
            # Solo usar UUID
            final_name = uuid_str
    else:
        if preserve_name:
            # Solo usar el nombre original (slugificado)
            final_name = slugify(name)
        else:
            # Generar nombre aleatorio sin UUID
            final_name = str(uuid.uuid4())[:uuid_length]
    
    return f"{folder}/{final_name}.{extension}"


def create_upload_handler(folder, **kwargs):
    """
    Crea una función de upload personalizada para usar en FileField/ImageField.
    
    Args:
        folder (str): Carpeta base donde se guardará el archivo
        **kwargs: Argumentos adicionales para generate_upload_path
        
    Returns:
        callable: Función que puede ser usada en upload_to (compatible con Django FileField)
        
    Examples:
        # En models.py
        upload_to_posts = create_upload_handler('posts')
        image = models.ImageField(upload_to=upload_to_posts)
        
        # Con opciones personalizadas
        upload_to_docs = create_upload_handler('documents', preserve_name=True)
        document = models.FileField(upload_to=upload_to_docs)
    """
    def upload_handler(instance, filename: str) -> str:
        """Django upload_to callable"""
        return generate_upload_path(folder, filename, **kwargs)
    
    # Agregar metadatos para que Django reconozca la función
    upload_handler.__name__ = f'upload_to_{folder}'
    upload_handler.__doc__ = f'Upload handler for {folder} folder'
    
    return upload_handler


# =====================================================================
# =====================================================================
#                    SECCIÓN 2: FIRMADO Y SEGURIDAD
# =====================================================================
# =====================================================================

def encode_with_signer(value_encode):
    """
    Esta función codifica y firma un objeto que contiene un valor proporcionado utilizando un objeto Signer.

    Args:
        value_encode (Any): El valor a codificar y firmar.

    Returns:
        str: El objeto codificado y firmado en forma de cadena de caracteres.
    """

    # Crea un objeto con el valor proporcionado y firma el objeto usando el Signer
    value = signer.sign_object({'value_encode': value_encode})

    # Retorna el objeto firmado y codificado
    return value


def decode_with_signer(value_dencode):
    """
    Esta función intenta descodificar y verificar un mensaje firmado y codificado.

    Args:
        value_decode (str): El valor firmado y codificado que se desea descodificar y verificar.

    Returns:
        dict or signing.BadSignature: Si la firma es válida, devuelve el objeto
        original. Si la firma no es válida, devuelve un objeto de excepción
        signing.BadSignature.
    """
    try:
        # Intenta descodificar y verificar el valor utilizando el método unsign_object() del Signer
        value = signer.unsign_object(value_dencode)
        return value
    except signing.BadSignature as bs:
        # Atrapa la excepción signing.BadSignature y retorna el objeto de excepción bs
        return bs


def encode_with_timestamp_signer(value_encode):
    """
        Esta función codifica y firma un objeto que contiene un valor proporcionado utilizando un objeto Signer.

        Args:
            value_encode (Any): El valor a codificar y firmar.

        Returns:
            str: El objeto codificado y firmado en forma de cadena de caracteres.
        """

    # Crea un objeto con el valor proporcionado y firma el objeto usando el Signer
    value = timestamp_signer.sign_object({'value_encode': value_encode})

    # Retorna el objeto firmado y codificado
    return value


def decode_with_timestamp_signer(value_decode):
    """
    Esta función intenta descodificar y verificar un mensaje firmado y codificado.

    Args:
        value_decode (str): El valor firmado y codificado que se desea descodificar y verificar.

    Returns:
        dict or signing.BadSignature: Si la firma es válida y no ha expirado, devuelve el objeto
        original. Si la firma no es válida o ha expirado, devuelve un objeto de excepción
        signing.BadSignature.
    """
    try:
        # Intenta descodificar y verificar el valor utilizando el método unsign_object() del Signer
        value = timestamp_signer.unsign_object(value_decode, max_age=300)
        return value
    except signing.BadSignature as bs:
        # Atrapa la excepción signing.BadSignature y retorna el objeto de excepción bs
        print("error bs", bs)
        return bs


def generate_random_code():
    """
    Genera un código aleatorio de 4 dígitos.

    Utiliza la función randbelow de la librería secrets para generar un número aleatorio
    entre 0 y 9999, y luego lo formatea para asegurarse de que tenga exactamente 4 dígitos,
    añadiendo ceros a la izquierda si es necesario.

    Returns:
        str: Código aleatorio de 4 dígitos.
    """
    return f"{secrets.randbelow(10000):04}"


# # =====================================================================
# # =====================================================================
# #                    SECCIÓN 3: ALMACENAMIENTO EN S3
# # =====================================================================
# # =====================================================================

# def save_file_to_s3(
#         file_obj: Union[IO, any],
#         filename: str,
#         folder_path: str = "uploads",
#         bucket_name: str = None,
#         file_extension: str = None,
#         add_timestamp: bool = True
# ):
#     """
#     Función genérica para subir archivos a Amazon S3.

#     NOTA: El bucket debe tener configuradas las políticas de acceso público
#     ya que no se usa ACL en la subida para compatibilidad con buckets modernos.

#     Args:
#         file_obj: Objeto de archivo temporal o file-like object
#         filename (str): Nombre base del archivo (sin extensión si se proporciona file_extension)
#         folder_path (str, optional): Ruta de la carpeta en S3. Default: "uploads"
#         bucket_name (str, optional): Nombre del bucket S3. Default: desde settings
#         file_extension (str, optional): Extensión del archivo (ej: "xlsx", "pdf"). Default: detectada del filename
#         add_timestamp (bool, optional): Si agregar timestamp al nombre. Default: True

#     Returns:
#         str: URL pública del archivo en S3 si la carga fue exitosa
#         None: Si ocurre un error

#     Ejemplos:
#         # Para Excel
#         save_file_to_s3(temp_file, "reporte_informes", "excel/informes", file_extension="xlsx")

#         # Para PDF
#         save_file_to_s3(pdf_file, "documento", "pdfs/contratos", file_extension="pdf")
#     """

#     # Configuración de AWS desde settings o valores por defecto
#     aws_access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
#     aws_secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
#     aws_region = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
#     default_bucket = bucket_name or getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'loginfor-cdn')

#     if not aws_access_key or not aws_secret_key:
#         logger.error("Credenciales AWS no configuradas")
#         return None

#     # Detectar extensión si no se proporciona
#     if not file_extension:
#         if '.' in filename:
#             file_extension = filename.split('.')[-1]
#         else:
#             file_extension = 'bin'

#     # Limpiar nombre de archivo
#     clean_filename = filename.split('.')[0] if '.' in filename else filename

#     # Generar nombre único si se requiere timestamp
#     if add_timestamp:
#         timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
#         unique_filename = f"{clean_filename}_{timestamp}.{file_extension}"
#     else:
#         unique_filename = f"{clean_filename}.{file_extension}"

#     # Construir ruta completa en S3
#     s3_key = f"{folder_path.strip('/')}/{unique_filename}"

#     try:
#         # Crear cliente S3
#         s3_client = boto3.client(
#             's3',
#             aws_access_key_id=aws_access_key,
#             aws_secret_access_key=aws_secret_key,
#             region_name=aws_region
#         )

#         # Subir archivo sin ACL (el bucket debe tener políticas públicas configuradas)
#         s3_client.upload_fileobj(
#             file_obj,
#             default_bucket,
#             s3_key
#         )

#         # Construir URL pública
#         file_url = f"https://{default_bucket}.s3.{aws_region}.amazonaws.com/{s3_key}"

#         logger.info(f"Archivo {unique_filename} subido exitosamente a S3: {s3_key}")
#         return file_url

#     except Exception as e:
#         logger.error(f'Error al subir archivo a S3: {str(e)}')
#         return None


# =====================================================================
# =====================================================================
#                    SECCIÓN 4: GESTIÓN DE CACHÉ
# =====================================================================
# =====================================================================

def clear_panel_cache():
    """
    Limpia específicamente el cache del panel de administración
    """
    try:
        redis_conn = get_redis_connection("default")
        prefix = settings.CACHES['default'].get('KEY_PREFIX', '')

        patterns = [
            f"{prefix}:*panel*",
            f"{prefix}:*admin*",
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
