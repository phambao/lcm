from django.contrib.auth import get_user_model
from django.db import models

from api.models import BaseModel


class Product(models.Model):
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
    payment_method_id = models.CharField(max_length=100, blank=True)
    subscription_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    card_number = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_day = models.IntegerField(blank=True, null=True)
    # is_activate = models.BooleanField(default=False, blank=True)
