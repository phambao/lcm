from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    code = models.IntegerField(blank=True, null=True)
    token = models.CharField(max_length=128, blank=True)


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    user_create = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_create', null=True, blank=True)
    user_update = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_update', null=True, blank=True)

    class Meta:
        abstract = True
