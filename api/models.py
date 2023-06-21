from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .middleware import get_request


class User(AbstractUser):
    code = models.IntegerField(blank=True, null=True)
    token = models.CharField(max_length=128, blank=True)
    image = models.CharField(max_length=128, blank=True, null=True)
    company = models.ForeignKey('api.CompanyBuilder', on_delete=models.CASCADE, related_name='%(class)s_company_builder', null=True, blank=True)
    lang = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return self.email


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    user_create = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, related_name='%(class)s_user_create',
                                    null=True, blank=True)
    user_update = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, related_name='%(class)s_user_update',
                                    null=True, blank=True)
    company = models.ForeignKey('api.CompanyBuilder', on_delete=models.CASCADE,
                                related_name='%(class)s_company_builder', null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        request = get_request()
        if self.pk:
            self.user_update = request.user
        else:
            self.user_create = request.user
        if not self.company:
            self.company = request.user.company
        return super(BaseModel, self).save(force_insert=force_insert, force_update=force_update,
                                           using=using, update_fields=update_fields)


class CompanyBuilder(models.Model):
    class Meta:
        db_table = 'company_builder'

    logo = models.CharField(blank=True, max_length=128)
    description = models.CharField(blank=True, max_length=128)
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
    fax = models.CharField(blank=True, max_length=11)
    email = models.EmailField(blank=True, max_length=128)
    cell_mail = models.CharField(blank=True, max_length=128)
    cell_phone = models.CharField(blank=True, max_length=11)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    user_create = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_create',
                                    null=True, blank=True)
    user_update = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_update',
                                    null=True, blank=True)
    currency = models.CharField(blank=True, max_length=128)

    def __str__(self):
        return self.company_name


class DivisionCompany(models.Model):
    class Meta:
        db_table = 'division_company'

    name = models.CharField(max_length=128)
    company = models.ForeignKey(CompanyBuilder, on_delete=models.SET_NULL, related_name='division_company_builder', null=True, blank=True)


class Action(models.IntegerChoices):
    CREATE = 1, 'Create'
    UPDATE = 2, 'Update'
    DELETE = 3, 'Delete'


class ActivityLog(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    action = models.IntegerField(choices=Action.choices, blank=True, default=Action.CREATE)
    last_state = models.JSONField(default=dict, blank=True)
    next_state = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def get_action_name(self):
        if self.action == Action.CREATE:
            return 'Create'
        if self.action == Action.UPDATE:
            return 'Update'
        return 'Delete'
