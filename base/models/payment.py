from django.contrib.auth import get_user_model
from django.db import models

from api.models import BaseModel


class Product(BaseModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    book_url = models.URLField()

    def __str__(self):
        return self.name


class PaymentHistoryStripe(BaseModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    payment_status = models.BooleanField()

    def __str__(self):
        return self.product.name
