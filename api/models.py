from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .middleware import get_request


class User(AbstractUser):
    code = models.IntegerField(blank=True, null=True)
    token = models.CharField(max_length=128, blank=True)
    image = models.CharField(max_length=128, blank=True, null=True)
    company = models.ForeignKey('api.CompanyBuilder', on_delete=models.CASCADE, related_name='%(class)s_company_builder', null=True, blank=True)
    lang = models.CharField(max_length=128, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True)
    phone = models.CharField(max_length=16, blank=True, default='')

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


class FieldChoices(models.TextChoices):
    IT = 'IT', 'Information Technology'
    HEALTHCARE = 'HEALTHCARE', 'Healthcare'
    EDUCATION = 'EDUCATION', 'Education'


class CompanyBuilder(models.Model):
    class Meta:
        db_table = 'company_builder'

    logo = models.CharField(blank=True, max_length=128)
    description = models.CharField(blank=True, max_length=128)
    company_name = models.CharField(blank=True, max_length=128)
    address = models.CharField(blank=True, max_length=128)
    field = models.CharField(max_length=128, choices=FieldChoices.choices, default=FieldChoices.EDUCATION, blank=True)
    country = models.CharField(blank=True, max_length=128, null=True)
    city = models.CharField(blank=True, max_length=128, null=True)
    state = models.CharField(blank=True, max_length=128, null=True)
    zip_code = models.CharField(verbose_name='Zip Code', max_length=6, blank=True)
    size = models.IntegerField(null=True, blank=True)
    tax = models.CharField(blank=True, max_length=128)
    business_phone = models.CharField(blank=True, max_length=15)
    fax = models.CharField(blank=True, max_length=15)
    email = models.EmailField(blank=True, max_length=128)
    cell_mail = models.CharField(blank=True, max_length=128)
    cell_phone = models.CharField(blank=True, max_length=15)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    user_create = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_create',
                                    null=True, blank=True)
    user_update = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='%(class)s_user_update',
                                    null=True, blank=True)
    currency = models.CharField(blank=True, max_length=128)
    company_timezone = models.CharField(blank=True, max_length=128)

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


class RequireSignature(models.TextChoices):
    ALL = 'all', 'ALL'


class ChangeOrderSetting(models.Model):
    class Meta:
        db_table = 'change_order_setting'

    company = models.OneToOneField(CompanyBuilder, on_delete=models.CASCADE, null=True)
    require_signature = models.CharField(max_length=128, choices=RequireSignature.choices, default=RequireSignature.ALL)
    change_order_approval = models.TextField(blank=True)
    default_change_order = models.TextField(blank=True)


class InvoiceSetting(models.Model):
    company = models.OneToOneField(CompanyBuilder, on_delete=models.CASCADE, null=True)
    prefix = models.CharField(max_length=128, blank=True)
    is_notify_internal_deadline = models.BooleanField(default=False)
    is_notify_owners_deadline = models.BooleanField(default=False)
    is_notify_owners_after_deadline = models.BooleanField(default=False)
    is_default_show = models.BooleanField(default=False)
    day_before = models.IntegerField(null=True, blank=True)
    default_owners_invoice = models.TextField(blank=True)


Group.add_to_class('company', models.ForeignKey(CompanyBuilder, null=True, on_delete=models.CASCADE,
                                                related_name='groups', blank=True))
