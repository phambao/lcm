from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from sales.models.lead_list import LeadDetail, Contact, Photos

LOG_MODEL = [LeadDetail, Contact, Photos]


@receiver(post_save)
def log_sales_handler(sender, **kwargs):
    if sender in LOG_MODEL:
        print('hi')
    print(sender, kwargs, LeadDetail)
