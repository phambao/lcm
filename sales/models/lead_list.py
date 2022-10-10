from re import L
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


class PartnerTypeInLead(models.Model):
    """
        Model for relationship between lead, partner and contact type of partner in lead
    """
    class Meta:
        db_table = 'partner_type_in_lead'

    class PartnerType(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MANAGER = 'manager', 'Manager'
        EMPLOYEE = 'employee', 'Employee'

    partner = models.ForeignKey(
        LeadPartner, on_delete=models.CASCADE, related_name='partner_type')
    partner_type = models.CharField(
        max_length=16, choices=PartnerType.choices, default=PartnerType.OWNER)
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='partner_type')


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
        
    name_photo = models.CharField(max_length=64)
    photo = models.ImageField(upload_to='photo')
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='photos')