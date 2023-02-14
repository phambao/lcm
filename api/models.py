from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models

from .middleware import get_request


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

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        request = get_request()
        if self.pk:
            self.user_update = request.user
        else:
            self.user_create = request.user
        return super(BaseModel, self).save(force_insert=force_insert, force_update=force_update,
                                           using=using, update_fields=update_fields)
