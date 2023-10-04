from django.contrib.auth import get_user_model
from django.db import models

from api.models import BaseModel


class Product(BaseModel):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True)
    stripe_product_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_product')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_activate = models.BooleanField(default=False, blank=True)


class PaymentHistoryStripe(models.Model):
    class Meta:
        db_table = 'payment_history_stripe'
    date = models.DateTimeField(auto_now_add=True)
    subscription_id = models.CharField(max_length=100, blank=True)
    customer_stripe_id = models.CharField(max_length=100, blank=True)
    # is_activate = models.BooleanField(default=False, blank=True)

