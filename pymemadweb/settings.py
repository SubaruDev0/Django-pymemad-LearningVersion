import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-z=9r8smtg$&sxs4c5=5kcl=8mhra5i3&t3a0xe)mtm(#f+)wi2')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

allowed_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost, 127.0.0.1')
ALLOWED_HOSTS = allowed_hosts.split(', ')

# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'anymail',  # Para AWS SES email
    'django_filters',
    'simple_history',
    'parler',  # Para soporte multiidioma
    'captcha',  # Para reCAPTCHA
    'django_celery_beat',  # Para tareas programadas
    'django_celery_results',  # Para almacenar resultados de Celery
]

LOCAL_APPS = [
    'apps.news',
    'apps.scrapers',
    'apps.landing',
    'apps.accounts',
    'apps.core',
    'apps.members',
    'apps.governance',
    'apps.billing',
    'apps.communications',
    'apps.documents',
    'apps.strategy',
    'apps.panel',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',  # PRIMERO - Para cache
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Importante
    'apps.core.middleware.TimezoneMiddleware',  # Activar timezone de Chile
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # MIDDLEWARE PERSONALIZADO - ANTES del FetchFromCacheMiddleware
    'pymemadweb.middleware.NoCacheForStaffMiddleware',
    'pymemadweb.middleware.SmartCacheInvalidationMiddleware',
    
    'django.middleware.cache.FetchFromCacheMiddleware',  # ÚLTIMO - Para cache
]

ROOT_URLCONF = 'pymemadweb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pymemadweb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'pymemaddb'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'sslmode': os.environ.get('DB_SSL_MODE', 'prefer' if DEBUG else 'require'),
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization


# Idiomas soportados
LANGUAGES = [
    ('es', _('Español')),
    ('en', _('English')),
    ('pt', _('Português')),
]

# Configuración específica de django-parler
PARLER_LANGUAGES = {
    None: (
        {'code': 'es'},  # Idioma predeterminado
        {'code': 'en'},
        {'code': 'pt'},
    ),
    'default': {
        'fallbacks': ['es'],  # Si falta traducción, usa español por defecto
        'hide_untranslated': False,  # Mostrar registros no traducidos
    }
}


LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale'
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION_NAME = os.environ.get("AWS_REGION")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_BUCKET")

AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# Para archivos estáticos:
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
STATICFILES_STORAGE = 'pymemadweb.storages.StaticStorage'

# Para archivos multimedia (como imágenes del blog):
DEFAULT_FILE_STORAGE = 'pymemadweb.storages.MediaStorage'
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

AWS_DEFAULT_ACL = None  # Deshabilitado - El bucket no permite ACLs

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "media")
]

# Configuración para archivos en S3 sin ACL
# IMPORTANTE: No usar AWS_S3_OBJECT_PARAMETERS global cuando ACLs están deshabilitados
# Los parámetros se manejan en las clases de almacenamiento personalizadas

# Cache headers específicos por tipo de archivo
AWS_S3_FILE_OVERWRITE = False  # No sobrescribir archivos (importante para cache)
AWS_QUERYSTRING_AUTH = False  # URLs públicas sin firma
AWS_S3_SIGNATURE_VERSION = 's3v4'  # Usar firma v4 para mejor compatibilidad
AWS_S3_VERIFY = True  # Verificar certificados SSL

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Captcha Configuration
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'
CAPTCHA_NOISE_FUNCTIONS = ('captcha.helpers.noise_dots',)
CAPTCHA_BACKGROUND_COLOR = '#ffffff'
CAPTCHA_FOREGROUND_COLOR = '#001100'
CAPTCHA_LENGTH = 4
CAPTCHA_TIMEOUT = 5

# Email configuration with AWS SES via Anymail
ANYMAIL = {
    "AMAZON_SES_CLIENT_PARAMS": {
        # AWS credentials specifically for email sending
        "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.environ.get("AWS_REGION", "us-east-1"),
        # Connection configuration
        "config": {
            "connect_timeout": 30,
            "read_timeout": 30,
        }
    },
}

# Use Anymail with Amazon SES for both production and development
EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"

# Fallback to console for local development if AWS credentials are not set
if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print("⚠️  AWS credentials not found. Using console email backend for development.")

# Common email settings
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@pymemad.cl')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)
EMAIL_MAIN = os.environ.get('EMAIL_MAIN', 'PymeMad <noreply@pymemad.cl>')

# Security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Admin emails for error notifications
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', 'yllorca@helloworld.cl')),
]
MANAGERS = ADMINS

# Email subject prefix for admin emails
EMAIL_SUBJECT_PREFIX = '[PymeMad] '

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'email.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Email logging
        'django.core.mail': {
            'handlers': ['console', 'mail_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'anymail': {
            'handlers': ['console', 'mail_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Celery task logging
        'apps.landing.tasks': {
            'handlers': ['console', 'mail_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.core.tasks': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Custom app logging
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

# Redis Configuration
REDIS_BASE_URL = os.environ.get('REDIS_BASE_URL', 'redis://localhost:6379/0')

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_BASE_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,  # Aumentar para mayor concurrencia
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'pymemad',
        'VERSION': 1,
        'TIMEOUT': 60 * 60,  # 1 hora por defecto
    }
}

# Configuración de Cache Middleware
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 60 * 15  # 15 minutos para páginas completas
CACHE_MIDDLEWARE_KEY_PREFIX = 'pymemad'

# Configuración variable por tipo de contenido (adaptado a pymemaddir)
CACHE_TIMES = {
    'home': 60 * 30,           # 30 minutos para página principal
    'about': 60 * 60 * 24,     # 24 horas para página sobre nosotros
    'members_list': 60 * 60,   # 1 hora para directorio de miembros
    'news_list': 60 * 30,      # 30 minutos para lista de noticias
    'news_detail': 60 * 60 * 4,  # 4 horas para detalle de noticias
    'magazine': 60 * 60 * 12,  # 12 horas para revista
    'join': 60 * 60 * 24,      # 24 horas para página de unirse
    'contact': 60 * 10,        # 10 minutos para contacto
    'dashboard': 0,            # No cachear dashboard (requiere login)
    'api': 60 * 5,             # 5 minutos para APIs futuras
    'static_components': 60 * 60,  # 1 hora para componentes estáticos
}

# Configurar vary headers para cache multiidioma
USE_ETAGS = True  # Añadir ETags para mejor cache HTTP
CACHE_MIDDLEWARE_VARY_HEADERS = [
    'Accept-Language',
    'Accept-Encoding',
    'Cookie',  # Importante para usuarios autenticados
]

# Cache para sesiones
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 1 semana

# IMPORTANTE: Solo cachear usuarios anónimos
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

# Función personalizada para excluir rutas del caché
def should_skip_cache(request):
    """
    Determina si una request debe saltar el caché.
    Retorna True para cachear, False para omitir.
    """
    # No cachear para usuarios autenticados
    if request.user.is_authenticated:
        return False
    
    # No cachear formularios POST
    if request.method == 'POST':
        return False
    
    # No cachear admin
    if request.path.startswith('/admin/'):
        return False
    
    # No cachear páginas de login/logout
    if 'login' in request.path or 'logout' in request.path:
        return False
    
    # No cachear páginas de contacto
    if 'contact' in request.path:
        return False
    
    # No cachear URLs de captcha
    if 'captcha' in request.path:
        return False
    
    # No cachear refresh de captcha
    if 'refresh-captcha' in request.path:
        return False
    
    return True

# Configuración específica de django-redis
DJANGO_REDIS_IGNORE_EXCEPTIONS = True
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True
DJANGO_REDIS_CONNECTION_FACTORY = 'django_redis.pool.ConnectionFactory'
DJANGO_REDIS_CLOSE_CONNECTION = False  # Reutilizar conexiones

# Señales para limpiar cache al editar
CACHE_INVALIDATION_ON_SAVE = True  # Flag para activar limpieza automática

# Celery Configuration
CELERY_BROKER_URL = REDIS_BASE_URL
CELERY_RESULT_BACKEND = REDIS_BASE_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat Configuration
from celery.schedules import crontab

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SYNC_EVERY = 10  # Sync schedule every 10 beats
CELERY_BEAT_MAX_LOOP_INTERVAL = 5  # Max seconds between schedule checks

# Celery Beat Schedule - Para tareas básicas de PyMemad
CELERY_BEAT_SCHEDULE = {
    # Calentar cache cada 30 minutos
    'warm-cache-comprehensive': {
        'task': 'apps.core.tasks.comprehensive_cache_warm',
        'schedule': crontab(minute='*/30'),  # Cada 30 minutos
        'options': {'queue': 'short_tasks'}
    },

    # Calentar home cada 15 minutos durante horas pico
    'warm-cache-home-frequent': {
        'task': 'apps.core.tasks.warm_cache_home',
        'schedule': crontab(minute='*/15', hour='7-22'),  # Cada 15 min de 7AM a 10PM
        'options': {'queue': 'short_tasks'}
    },

    # Calentar posts/noticias recientes cada hora
    'warm-recent-posts-hourly': {
        'task': 'apps.core.tasks.warm_cache_recent_posts',
        'schedule': crontab(minute='5'),  # A los 5 minutos de cada hora
        'options': {'queue': 'short_tasks'}
    },

    # Calentar categorías cada 2 horas
    'warm-categories': {
        'task': 'apps.core.tasks.warm_cache_categories',
        'schedule': crontab(minute='0', hour='*/2'),  # Cada 2 horas
        'options': {'queue': 'short_tasks'}
    },

    # Limpiar sesiones viejas diariamente
    'clear-old-sessions': {
        'task': 'apps.core.tasks.clear_old_sessions',
        'schedule': crontab(hour='3', minute='30'),  # 3:30 AM
        'options': {'queue': 'short_tasks'}
    },

    # Estadísticas cada 2 horas
    'generate-cache-stats': {
        'task': 'apps.core.tasks.generate_cache_stats',
        'schedule': crontab(minute='0', hour='*/2'),  # Cada 2 horas
        'options': {'queue': 'long_tasks'}
    },

    # Limpieza de cache huérfano semanalmente
    'cleanup-orphaned-cache': {
        'task': 'apps.core.tasks.cleanup_orphaned_cache',
        'schedule': crontab(hour='4', minute='0', day_of_week='0'),  # Domingos 4AM
        'options': {'queue': 'long_tasks'}
    },
}


LOGIN_URL = 'accounts:login'
LOGOUT_URL = 'accounts:logout'

# CSRF Configuration for production (after AWS settings)
CSRF_TRUSTED_ORIGINS = [
    'https://www.pymemad.cl',
    'https://pymemad.cl',
]
# Add S3 domain if configured
if AWS_STORAGE_BUCKET_NAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com')

# URLs que NUNCA deben cachearse
def should_cache_request(request):
    """Determina si una request debe ser cacheada"""
    # No cachear si el usuario está autenticado
    if hasattr(request, 'user') and request.user.is_authenticated:
        return False
    
    # No cachear requests POST
    if request.method != 'GET':
        return False
    
    # No cachear URLs administrativas
    if request.path.startswith('/admin/'):
        return False
    
    # No cachear la página de contacto completa
    if 'contact' in request.path:
        return False
    
    # No cachear URLs de captcha
    if 'captcha' in request.path:
        return False
    
    # No cachear refresh de captcha
    if 'refresh-captcha' in request.path:
        return False
    
    return True

# Comando personalizado para limpiar cache
CACHE_CLEAR_COMMAND = 'clear_cache'

# Sentry Configuration
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

# Determinar el entorno actual
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local' if DEBUG else 'production')

# Configuración de Sentry solo si tenemos DSN Y NO estamos en modo local
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

# Solo inicializar Sentry si tenemos DSN y NO estamos en modo local
if SENTRY_DSN and ENVIRONMENT != 'local':
    # Configuración de logging para Sentry
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Captura logs INFO y superiores
        event_level=logging.ERROR   # Envía eventos ERROR y superiores a Sentry
    )
    
    # Configuración base de Sentry
    sentry_config = {
        'dsn': SENTRY_DSN,
        'integrations': [
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
            sentry_logging,
        ],
        'environment': ENVIRONMENT,
        'release': os.environ.get('RELEASE_VERSION', 'unknown'),
        
        # Configuración de performance monitoring
        'traces_sample_rate': 0.1 if ENVIRONMENT == 'production' else 1.0,
        'profiles_sample_rate': 0.1 if ENVIRONMENT == 'production' else 1.0,
        
        # Configuración de PII (Información Personal Identificable)
        'send_default_pii': False if ENVIRONMENT == 'production' else True,
        
        # Filtros y opciones adicionales
        'attach_stacktrace': True,
        'max_request_body_size': 'medium',  # small, medium, or always
        'include_local_variables': DEBUG,  # Solo en desarrollo
        
        # Configuración de errores ignorados
        'ignore_errors': [
            'django.security.DisallowedHost',
            'django.core.exceptions.DisallowedHost',
            'KeyboardInterrupt',
            'SystemExit',
        ],
        
        # Configuración de breadcrumbs
        'max_breadcrumbs': 50,
        'before_breadcrumb': lambda crumb, hint: crumb,  # Siempre procesar breadcrumbs
    }
    
    # Configuración específica para Kubernetes/Producción
    if ENVIRONMENT == 'production':
        sentry_config.update({
            'server_name': os.environ.get('KUBERNETES_POD_NAME', 'unknown'),
        })
    
    # Inicializar Sentry
    sentry_sdk.init(
        **sentry_config,
        # enable_logs no existe en sentry-sdk, se configura via integrations
    )
    
    # Configurar tags después de la inicialización
    if ENVIRONMENT == 'production':
        sentry_sdk.set_tag('kubernetes.namespace', os.environ.get('KUBERNETES_NAMESPACE', 'default'))
        sentry_sdk.set_tag('kubernetes.deployment', os.environ.get('KUBERNETES_DEPLOYMENT', 'unknown'))
        sentry_sdk.set_tag('kubernetes.pod', os.environ.get('KUBERNETES_POD_NAME', 'unknown'))
        sentry_sdk.set_tag('kubernetes.node', os.environ.get('KUBERNETES_NODE_NAME', 'unknown'))
    
    # Log de confirmación
    print(f"✅ Sentry configurado en modo: {ENVIRONMENT}")
else:
    if ENVIRONMENT == 'local':
        print("⚠️  Sentry está deshabilitado en modo local")
    elif not SENTRY_DSN:
        print("⚠️  Sentry DSN no configurado. Sentry está deshabilitado.")


