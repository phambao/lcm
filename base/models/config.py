from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel


class Column(models.Model):
    name = models.CharField(max_length=128, default="")
    params = ArrayField(models.CharField(max_length=64), blank=True)
    hidden_params = ArrayField(models.CharField(max_length=64), default=list, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    is_public = models.BooleanField(default=False, blank=True)
    is_active = models.BooleanField(default=False, blank=True)


class Search(models.Model):
    name = models.CharField(max_length=64)
    params = models.CharField(max_length=512, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)


class Config(models.Model):
    settings = models.JSONField(default=dict)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'content_type')


class GridSetting(models.Model):
    name = models.CharField(max_length=128)
    params = ArrayField(models.CharField(max_length=64), blank=True)
    hidden_params = ArrayField(models.CharField(max_length=64), default=list, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    is_public = models.BooleanField(default=False, blank=True)


class FileBuilder365(BaseModel):
    class Meta:
        db_table = 'file_builder365'

    file = models.FileField(upload_to='%Y/%m/%d/')
    name = models.CharField(blank=True, max_length=128)


class Company(models.Model):
    class Meta:
        db_table = 'company'

    logo = models.CharField(blank=True, max_length=128)
    company_name = models.CharField(blank=True, max_length=128)
    address = models.CharField(blank=True, max_length=128)
    tax = models.CharField(blank=True, max_length=128)
    phone = models.CharField(blank=True, max_length=128)
    email = models.CharField(blank=True, max_length=128)
    website = models.CharField(blank=True, max_length=128)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    user_create = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_create',
                                    null=True, blank=True)
    user_update = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_update',
                                    null=True, blank=True)