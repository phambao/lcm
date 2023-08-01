from django.contrib.auth import get_user_model
from django.db import models

from api.models import BaseModel


class Product(BaseModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    book_url = models.URLField()

    def __str__(self):
        return self.name


class PaymentHistoryStripe(models.Model):
    class Meta:
        db_table = 'payment_history_stripe'
    date = models.DateTimeField(auto_now_add=True)
    subscription_id = models.CharField(max_length=100, blank=True)

