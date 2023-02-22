from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.postgres.fields import ArrayField


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
