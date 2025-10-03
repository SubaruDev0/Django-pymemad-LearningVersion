# pymemadweb/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from kombu import Exchange, Queue

# Obteniendo la URL base de Redis de las variables de entorno
REDIS_BASE_URL = os.environ.get('REDIS_BASE_URL', 'redis://localhost:6379/0')

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pymemadweb.settings')

app = Celery('pymemadweb')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# This allows you to schedule items in the Django admin.
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'

# Define las colas
app.conf.task_queues = (
    Queue('long_tasks', Exchange('long_tasks'), routing_key='long.tasks'),
    Queue('short_tasks', Exchange('short_tasks'), routing_key='short.tasks'),
)
# Explicitly include accounts tasks
app.autodiscover_tasks(['apps.accounts']) #NUEVO

# Update configuration
app.conf.update(
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_soft_time_limit=7200,  # 2 horas para tareas largas
    task_time_limit=7260,  # 2 horas y 1 minuto para tareas largas
    broker_url=REDIS_BASE_URL,
    result_backend=REDIS_BASE_URL,
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='America/Santiago',
    broker_connection_retry_on_startup=True  # Nueva configuración recomendada
)