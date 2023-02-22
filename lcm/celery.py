import os

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcm.settings')

app = Celery('lcm',
             broker=f'redis://{settings.CELERY_IP}:{settings.CELERY_PORT}/{settings.CELERY_DATABASE}',
             backend=f'redis://{settings.CELERY_IP}:{settings.CELERY_PORT}/{settings.CELERY_DATABASE}')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
