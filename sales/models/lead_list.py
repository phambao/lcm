from django.db import models

from api.models import BaseModel


class LeadPartner(BaseModel):

    class Meta:
        db_table = 'lead_partner'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    gender = models.CharField(
        max_length=6, choices=Gender.choices, default=Gender.MALE)
    email = models.EmailField(max_length=128)
    street = models.CharField(max_length=64)
    city = models.CharField(max_length=32)
    state = models.CharField(max_length=32)
    country = models.CharField(max_length=32)
    zip_code = models.CharField(max_length=32)
    image = models.ImageField(upload_to='partner_image')


class PhoneCategory(models.Model):

    class Meta:
        db_table = 'phone_categories'

    name = models.CharField(max_length=16, unique=True)


class PhoneContact(models.Model):

    class Meta:
        db_table = 'phone_contact'

    phone = models.CharField(max_length=20, unique=True)
    phone_category = models.ForeignKey(
        PhoneCategory, on_delete=models.CASCADE, related_name='+')
    text_massage_received = models.BooleanField(default=False)
    mobile_phone_service_provider = models.CharField(max_length=32)
    partner = models.ForeignKey(
        LeadPartner, on_delete=models.CASCADE, related_name='partner_phones')


class LeadDetail(BaseModel):

    class Meta:
        db_table = 'lead_detail'

    # General
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSE = 'close', 'Close'

    class ProposalStatus(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        RELEASE = 'release', 'Release'
        UNRELEASED = 'unreleased', 'Unreleased'

    # Lead information
    lead_title = models.CharField(max_length=128)
    street_address = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128)
    zip_code = models.CharField(max_length=6)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN)
    proposal_status = models.CharField(
        max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.APPROVED)
    notes = models.TextField(blank=True)
    confidence = models.IntegerField(default=0)
    estimate_revenue_from = models.DecimalField(
        max_digits=9, decimal_places=2, default=0, blank=True)
    estimate_revenue_to = models.DecimalField(
        max_digits=9, decimal_places=2, default=0, blank=True)
    projected_sale_date = models.DateTimeField()
    # project_type = models
    source = models.CharField(max_length=128, blank=True)
    tags = models.CharField(max_length=128, blank=True)

    # Contact information of partner
    partner = models.ManyToManyField(LeadPartner)
