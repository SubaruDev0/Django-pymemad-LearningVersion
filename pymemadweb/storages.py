"""
Custom S3 Storage classes with smart cache optimization
"""
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """
    Storage para archivos estáticos con cache inteligente.
    - Archivos en /front/: sin cache para desarrollo
    - Archivos del template/vendor: cache largo porque no cambian
    """
    location = 'static'
    file_overwrite = True  # Sobrescribir para actualizar inmediatamente
    default_acl = None  # Sin ACL ya que el bucket tiene política pública
    querystring_auth = False  # URLs públicas sin firma
    
    def get_object_parameters(self, name):
        """Define cache headers inteligentes según el archivo"""
        params = {}
        
        # === ARCHIVOS PERSONALIZADOS EN /front/ (sin cache) ===
        if '/front/' in name or 'front/' in name:
            # Sin cache para archivos que modificas frecuentemente
            params['CacheControl'] = 'no-cache, no-store, must-revalidate'
            params['Pragma'] = 'no-cache'
            params['Expires'] = '0'
        
        # === ARCHIVOS DEL TEMA BASE (cache largo) ===
        # Archivos vendor (librerías externas)
        elif 'vendor/' in name:
            params['CacheControl'] = 'max-age=31536000, immutable'  # 1 año
        
        # Archivos del tema (theme.js, theme.min.js, theme-switcher.js)
        elif name.endswith(('theme.js', 'theme.min.js', 'theme-switcher.js')):
            params['CacheControl'] = 'max-age=2592000'  # 30 días
        
        # Archivos CSS del tema
        elif name.endswith(('theme.css', 'theme.min.css')):
            params['CacheControl'] = 'max-age=2592000'  # 30 días
        
        # Fuentes - nunca cambian
        elif name.endswith(('.woff', '.woff2', '.ttf', '.eot', '.otf')):
            params['CacheControl'] = 'max-age=31536000, immutable'  # 1 año
        
        # Iconos y archivos de íconos
        elif 'icons/' in name or name.endswith(('.svg', '.ico')):
            params['CacheControl'] = 'max-age=604800'  # 7 días
        
        # Imágenes en general
        elif name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            params['CacheControl'] = 'max-age=604800'  # 7 días
        
        # Archivos admin de Django
        elif 'admin/' in name:
            params['CacheControl'] = 'max-age=604800'  # 7 días
        
        # Archivos CSS y JS no categorizados
        elif name.endswith(('.css', '.js')):
            params['CacheControl'] = 'max-age=86400'  # 1 día por defecto
        
        # Cualquier otro archivo
        else:
            params['CacheControl'] = 'max-age=3600'  # 1 hora por defecto
        
        # Siempre mostrar en navegador, no descargar
        params['ContentDisposition'] = 'inline'
        
        return params


class MediaStorage(S3Boto3Storage):
    """Storage para archivos media con cache moderado"""
    location = 'media'
    file_overwrite = False  # No sobrescribir uploads de usuarios
    default_acl = None  # Sin ACL ya que el bucket tiene política pública
    querystring_auth = False  # URLs públicas sin firma
    
    def get_object_parameters(self, name):
        """Define cache headers para archivos media"""
        params = {}
        # Media files - Cache moderado
        params['CacheControl'] = 'max-age=2592000'  # 30 días
        params['ContentDisposition'] = 'inline'
        return params