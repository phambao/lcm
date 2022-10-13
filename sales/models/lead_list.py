from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models import BaseModel


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


class Contact(models.Model):
    """Contact information"""

    class Meta:
        db_table = 'contact'

    class Gender(models.TextChoices):
        MALE = 'male', _('Male')
        FEMALE = 'female', _('Female')
        OTHER = 'other', _('Other')

    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    gender = models.CharField(
        max_length=6, choices=Gender.choices, default=Gender.MALE)
    email = models.EmailField(max_length=128)
    street = models.CharField(max_length=64)
    city = models.CharField(max_length=32)
    state = models.CharField(max_length=32)
    country = models.CharField(max_length=32)
    zip_code = models.CharField(max_length=32, blank=True)
    image = models.ImageField(upload_to='contact_image', blank=True, null=True)
    lead = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='contacts',
                             blank=True, null=True)
    # lead = models.ManyToManyField(LeadDetail)


class PhoneOfContact(models.Model):
    """List phone of contact"""

    class Meta:
        db_table = 'phone_of_contact'

    class PhoneType(models.TextChoices):
        MOBILE = 'mobile', _('Mobile')
        CELL = 'cell', _('Cell')
        LANDLINE = 'landline', _('Landline')
        OTHER = 'other', _('Other')

    phone_number = models.CharField(max_length=20, unique=True)
    phone_type = models.CharField(
        max_length=8, choices=PhoneType.choices, default=PhoneType.MOBILE)
    text_massage_received = models.BooleanField(default=True)
    mobile_phone_service_provider = models.CharField('Mobile Phone Service Provider', max_length=32, blank=True, null=True)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='phone_contacts')


class ContactTypeName(models.Model):
    name = models.CharField(max_length=128)


class ContactType(models.Model):
    class Meta:
        db_table = 'contact_type'
        unique_together = ['contact_type_name', 'contact', 'lead']

    contact_type_name = models.ForeignKey(ContactTypeName, on_delete=models.CASCADE,
                                          related_name="contact_info", null=True)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='contact_type', blank=True,
        null=True)  # TODO: not null, not blank
    lead = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='contact_partner_type',
                             blank=True, null=True)


class Activities(BaseModel):

    class Meta:
        db_table = 'activities'

    class Status(models.TextChoices):
        NONE = 'none', 'None'
        UPCOMING = 'upcoming', 'Upcoming'
        COMPLETED = 'completed', 'Completed'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IN_COMPLETE = 'in_complete', 'In Complete'
        PAST_DUE = 'past_due', 'Past Due'
        UNCONFIRMED = 'unconfirmed', 'Unconfirmed'

    class Tags(models.TextChoices):
        UNASSIGNED = 'unassigned', 'Unassigned'
        DESIGN_BUILD = 'design_build', 'Design Build'
        BUILD_ONLY = 'build_only', 'Build Only'
        ART_TURF = 'art_turf', 'Art Turf'
        PAVER_INSTALL = 'paver_install', 'Paver Install'
        BIG_JOB = 'big_job', 'Big Job'

    class Phases(models.TextChoices):
        PHASE_1 = 'phase_1', 'Phase 1 Learning'
        JOB_LEARNING = 'job_learning', 'Job Learning'
        PRE_CONSTRUCTION = 'pre_construction', 'Pre-Construction'
        UNASSIGNED = 'unassigned', 'Unassigned'

    title = models.CharField(max_length=128)
    is_completed = models.BooleanField(default=False)
    phase = models.CharField(
        max_length=128, choices=Phases.choices, default=Phases.UNASSIGNED)
    tag = models.CharField(
        max_length=128, choices=Tags.choices, default=Tags.UNASSIGNED)
    status = models.CharField(
        max_length=128, choices=Status.choices, default=Status.NONE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    assigned_to = models.CharField(
        max_length=128, blank=True)  # TODO: Change to user
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='activities')


class Proposals(BaseModel):
    class Meta:
        db_table = 'proposal'
    
    class Status(models.TextChoices):
        STATUS_1 = 'status_1', 'Status 1'
        STATUS_2 = 'status_2', 'Status 2'
    
    proposal_name = models.CharField(max_length=64)
    estimate_number = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.STATUS_1)
    owner_price = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True)
    file = models.FileField(upload_to='proposal', blank=True)
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='proposals')


class Photos(BaseModel):
    class Meta:
        db_table = 'photos'

    photo = models.ImageField(upload_to='photo')
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='photos', null=True)
