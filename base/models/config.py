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
    city = models.ForeignKey('base.City', on_delete=models.SET_NULL,
                             related_name='company_cities', null=True, blank=True)
    state = models.ForeignKey('base.State', on_delete=models.SET_NULL,
                              related_name='company_states', null=True, blank=True)
    zip_code = models.CharField(verbose_name='Zip Code', max_length=6, blank=True)
    size = models.IntegerField(null=True, blank=True)
    tax = models.CharField(blank=True, max_length=128)
    business_phone = models.CharField(blank=True, max_length=11)
    cell_phone = models.CharField(blank=True, max_length=11)
    fax = models.CharField(blank=True, max_length=11)
    email = models.EmailField(blank=True, max_length=128)
    cell_mail = models.CharField(blank=True, max_length=128)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    user_create = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_create',
                                    null=True, blank=True)
    user_update = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_update',
                                    null=True, blank=True)


class Division(BaseModel):
    class Meta:
        db_table = 'division'

    name = models.CharField(max_length=128)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, related_name='division_company', null=True, blank=True)