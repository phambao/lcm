import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from .middleware import get_request


class User(AbstractUser):
    class ServiceProvider(models.TextChoices):
        USNETWORK = 'us-network', 'U.S. Networks'
        TMOBILE = 't-mobile', 'T-Mobile'
        ATANDT = 'at&t', 'AT&T'
        SPRINT = 'sprint', 'Sprint'
        USCELLULAR = 'us-cellular', 'U.S. Cellular'
        MOBIFONE = 'mobifone', 'Mobifone'
        VIETTEL = 'viettel', 'Viettel'
        VINAFONE = 'vinafone', 'Vinafone'

    code = models.IntegerField(blank=True, null=True)
    token = models.CharField(max_length=128, blank=True)
    image = models.CharField(max_length=128, blank=True, null=True)
    company = models.ForeignKey('api.CompanyBuilder', on_delete=models.CASCADE, related_name='%(class)s_company_builder', null=True, blank=True)
    lang = models.CharField(max_length=128, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True)
    phone = models.CharField(max_length=16, blank=True, default='')
    stripe_customer = models.CharField(max_length=100, default=uuid.uuid4, blank=True)
    is_admin_company = models.BooleanField(default=False, blank=True)
    create_code = models.IntegerField(blank=True, null=True)
    expire_code_register = models.DateTimeField(auto_now=True)
    service_provider = models.CharField(blank=True, choices=ServiceProvider.choices,
                                        default=ServiceProvider.USNETWORK, max_length=16)

    def __str__(self):
        return self.email

    def check_perm(self, perm: str, obj: object=None) -> bool:
        if self.is_admin_company:
            return True
        return self.has_perm(str, obj)


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


# class FieldChoices(models.TextChoices):
#     LANDSCAPE_CONSTRUCTION = 'LANDSCAPE_CONSTRUCTION', 'Landscape Construction'
#     LANDSCAPE_MAINTENANCE = 'LANDSCAPE_MAINTENANCE', 'Landscape Maintenance'
#     HOME_BUILDER = 'HOME_BUILDER', 'Home Builder'
#     CARPENTRY = 'CARPENTRY', 'Carpentry'
#     PLUMBING = 'PLUMBING', 'Plumbing'
#     POOL_BUILDER = 'POOL_BUILDER', 'Pool Builder'
#     MASONRY = 'MASONRY', 'Masonry'
#     DEMO_AND_GRADING = 'DEMO_AND_GRADING', 'Demo and Grading'
#     CARPENTRY = 'CARPENTRY', 'Carpentry'
#     CARPENTRY = 'CARPENTRY', 'Carpentry'
class SizeCompanyChoices(models.TextChoices):
    SMALL = '1-5', '1-5'
    MEDIUM = '6-10', '6-10'
    LARGE = '11-25', '11-25'
    EXTRA_LARGE = '25+', '25+'


class EstimatedAnnualRevenueChoices(models.TextChoices):
    ESTIMATED_1 = '$0 - $499K', '$0 - $499K'
    ESTIMATED_2 = '$500 - $999K', '$500 - $999K'
    ESTIMATED_3 = '$1M - $1.99M', '$1M - $1.99M'
    ESTIMATED_4 = '$2M - $4.99M', '$2M - $4.99M'
    ESTIMATED_5 = '$5M - $9.99M', '$5M - $9.99M'
    ESTIMATED_6 = '$10M - $14.9', '$10M - $14.9'
    ESTIMATED_7 = '$15M - $24.99M', '$15M - $24.99M'
    ESTIMATED_8 = '$25M - $', '$25M - $'


class CompanyBuilder(models.Model):
    class Meta:
        db_table = 'company_builder'

    logo = models.CharField(blank=True, max_length=128)
    description = models.CharField(blank=True, max_length=128)
    company_name = models.CharField(blank=True, max_length=128)
    address = models.CharField(blank=True, max_length=128)
    # field = models.CharField(max_length=128, choices=FieldChoices.choices, default=FieldChoices.EDUCATION, blank=True)
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
    customer_stripe = models.CharField(blank=True, max_length=128, null=True)
    is_payment = models.BooleanField(default=True)
    website = models.CharField(blank=True, max_length=128, null=True)
    trades = models.ManyToManyField('Trades', related_name='company_trades')
    company_size = models.CharField(max_length=128, choices=SizeCompanyChoices.choices, default=SizeCompanyChoices.SMALL)
    revenue = models.CharField(max_length=128, choices=EstimatedAnnualRevenueChoices.choices, default=EstimatedAnnualRevenueChoices.ESTIMATED_1)
    referral_code = models.CharField(blank=True, max_length=6)

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


class InvoiceApproveType(models.TextChoices):
    OWN = '0', _('User themselves create invoice for change order')
    SYSTEM = '1', _('the system automatically create invoice')
    AUTO_SEND = '2', _('the system automatically create invoice and send it to the client')


class InvoiceSetting(models.Model):
    company = models.OneToOneField(CompanyBuilder, on_delete=models.CASCADE, null=True)
    prefix = models.CharField(max_length=128, blank=True)
    is_notify_internal_deadline = models.BooleanField(default=False)
    is_notify_owners_deadline = models.BooleanField(default=False)
    is_notify_owners_after_deadline = models.BooleanField(default=False)
    is_default_show = models.BooleanField(default=False)
    day_before = models.IntegerField(null=True, blank=True)
    default_owners_invoice = models.TextField(blank=True)
    create_invoice_after_approving = models.CharField(blank=True, choices=InvoiceApproveType.choices,
                                                      default=InvoiceApproveType.OWN, max_length=8)


class GroupCompany(models.Model):
    company = models.ForeignKey(CompanyBuilder, null=True, on_delete=models.CASCADE,
                                related_name='groups', blank=True)
    group = models.OneToOneField(Group, null=True, on_delete=models.CASCADE,
                                 related_name='group', blank=True)


class SubscriptionStripeCompany(models.Model):
    company = models.ForeignKey(CompanyBuilder, null=True, on_delete=models.CASCADE,
                                related_name='subscription_company', blank=True)
    customer_stripe = models.CharField(blank=True, max_length=128, null=True)
    subscription_id = models.CharField(blank=True, max_length=128, null=True)
    subscription_name = models.CharField(blank=True, max_length=128, null=True)
    expiration_date = models.DateTimeField()
    is_activate = models.BooleanField(default=False)


class Trades(models.Model):
    class Meta:
        db_table = 'trades'

    name = models.CharField(max_length=64)
    is_show = models.BooleanField(default=False)