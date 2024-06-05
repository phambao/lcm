import os
import logging
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcm.settings')

app = Celery('lcm',
             broker=f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_CELERY_DATABASE}',
             backend=f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_CELERY_DATABASE}')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'add-every-30-seconds': {
        'task': 'base.tasks.check_events',
        'schedule': 20.0
    },
}
app.conf.timezone = 'UTC'
# logger = logging.getLogger(__name__)
# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     # Calls test('hello') every 10 seconds.
#     sender.add_periodic_task(20.0, test.s(), name='add every 20')
#
# @app.task
# def test():
#     logger.info(f"Email sent successfully with argument 11:")
#     print('3333333333333333')
#     send_mail('truong create', 'truong 123', 'acctmgmt@builder365.com', ['nguyenxuantruongee@gmail.com'],fail_silently=False, auth_user=None, auth_password=None,connection=None, html_message=None)
#     logger.info(f"Email sent successfully with argument:")
#     return f"Email sent with argument: "
