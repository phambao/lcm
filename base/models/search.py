from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Search(models.Model):
    name = models.CharField(max_length=64)
    params = models.CharField(max_length=128)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
