from django.apps import AppConfig
from django.db.models.signals import post_save, pre_delete


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'

    def ready(self):
        from . import signals
        post_save.connect(signals.log_sales_handler)
        # request_finished.connect(signals.my_callback)
