from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.apps import apps

from api.models import BaseModel
from base.constants import DECIMAL_PLACE, MAX_DIGIT


class SourceLead(BaseModel):
    name = models.CharField(max_length=64)


class ProjectType(BaseModel):
    name = models.CharField(max_length=64)


class TagLead(BaseModel):
    class Meta:
        db_table = 'tag_lead'

    name = models.CharField(max_length=64)


class LeadDetail(BaseModel):
    class Meta:
        db_table = 'lead_detail'
        ordering = ['-modified_date']
        permissions = [('assign_salesperson', 'Can Assign Salesperson'),
                       ('view_salesperson_and_activity', 'View other Salesperson Lead & Activitíes'),
                       ('convert_to_job', 'Can Convert to Job'),
                       ('export_to_excel', 'Can Export to Excel')]

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSE = 'close', 'Close'

    class ProposalStatus(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        RELEASE = 'release', 'Release'
        UNRELEASED = 'unreleased', 'Unreleased'

    # Lead information
    lead_title = models.CharField('Lead Title', max_length=128)
    street_address = models.CharField('Street Address', max_length=128, blank=True)
    country = models.CharField('Country', max_length=128, blank=True, default='', null=True)
    city = models.CharField('City', max_length=128, blank=True, default='', null=True)
    state = models.CharField('State', max_length=128, blank=True, default='', null=True)
    zip_code = models.CharField(verbose_name='Zip Code', max_length=16, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN)
    proposal_status = models.CharField(verbose_name='Proposal Status', max_length=16,
                                       choices=ProposalStatus.choices, default=ProposalStatus.APPROVED)
    notes = models.TextField(blank=True)
    confidence = models.IntegerField(default=0)
    estimate_revenue_from = models.DecimalField(
        max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    estimate_revenue_to = models.DecimalField(
        max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    projected_sale_date = models.DateTimeField(verbose_name='Projected Sales Date', null=True)
    project_types = models.ManyToManyField(ProjectType, verbose_name='Project Types', related_name='leads', blank=True)
    salesperson = models.ManyToManyField(get_user_model(), related_name='lead_persons', blank=True)
    sources = models.ManyToManyField(SourceLead, related_name='leads', blank=True)
    tags = models.ManyToManyField(TagLead, related_name='lead_tags', blank=True)
    number_of_click = models.IntegerField(default=0, null=True, blank=True)  # For filter
    recent_click = models.DateTimeField(null=True, blank=True)  # For filter
    primary_contact_id = models.IntegerField(null=True, blank=True, default=None)

    def __str__(self):
        return self.lead_title

    def get_change_order(self):
        proposals = self.proposals.all()
        change_orders = apps.get_model(app_label='sales', model_name='ChangeOrder').objects.none()
        for proposal in proposals:
            change_orders |= proposal.change_orders.all()
        return change_orders

    def get_info_for_proposal_formatting(self):
        return {
            'lead_title': self.lead_title,
            'street_address': self.street_address,
            'country': self.country,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code
        }


class Contact(BaseModel):
    """Contact information"""

    class Meta:
        db_table = 'contact'

    class Gender(models.TextChoices):
        MALE = 'male', _('Male')
        FEMALE = 'female', _('Female')
        OTHER = '', _('Other')

    first_name = models.CharField(verbose_name='First Name', max_length=128)
    last_name = models.CharField(verbose_name='Last Name', max_length=128)
    gender = models.CharField(
        max_length=6, choices=Gender.choices, default=Gender.MALE)
    email = models.EmailField(max_length=128, blank=True)
    street = models.CharField(max_length=256, null=True, blank=True)
    country = models.CharField('Country', max_length=128, blank=True, default='', null=True)
    city = models.CharField('City', max_length=128, blank=True, default='', null=True)
    state = models.CharField('State', max_length=128, blank=True, default='', null=True)
    zip_code = models.CharField(verbose_name='Zip Code', max_length=32, blank=True)
    image = models.ImageField(upload_to='contact_image', blank=True, null=True)
    leads = models.ManyToManyField(LeadDetail, related_name='contacts',
                                   blank=True)


class PhoneOfContact(BaseModel):
    """List phone of contact"""

    class Meta:
        db_table = 'phone_of_contact'

    class PhoneType(models.TextChoices):
        MOBILE = 'mobile', _('Mobile')
        CELL = 'cell', _('Cell')
        LANDLINE = 'landline', _('Landline')
        OTHER = '', _('')

    phone_number = models.CharField(verbose_name='Phone Number', max_length=20, blank=True)
    phone_type = models.CharField(verbose_name='Phone Type', max_length=8,
                                  choices=PhoneType.choices, default=PhoneType.OTHER)
    text_massage_received = models.CharField(verbose_name="Text Message Received", max_length=10, blank=True)
    mobile_phone_service_provider = models.CharField('Mobile Phone Service Provider', max_length=32, blank=True,
                                                     null=True)
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='phone_contacts')

    def __str__(self):
        return self.phone_number


class ContactTypeName(BaseModel):
    name = models.CharField(max_length=128, unique=True)


class ContactType(BaseModel):
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


class TagActivity(models.Model):
    class Meta:
        db_table = 'tag_activity'

    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class PhaseActivity(models.Model):
    class Meta:
        db_table = 'phase_activity'

    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Activities(BaseModel):
    class Meta:
        db_table = 'activities'
        ordering = ['-modified_date']

    class Status(models.TextChoices):
        NONE = 'none', 'None'
        UPCOMING = 'upcoming', 'Upcoming'
        COMPLETED = 'completed', 'Completed'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IN_COMPLETE = 'in_complete', 'In Complete'
        PAST_DUE = 'past_due', 'Past Due'
        UNCONFIRMED = 'unconfirmed', 'Unconfirmed'

    title = models.CharField(max_length=128)
    is_completed = models.BooleanField(default=False)
    phase = models.ForeignKey(PhaseActivity, on_delete=models.CASCADE,
                              related_name='activities_phase', null=True, blank=True)
    tags = models.ManyToManyField(TagActivity, related_name='activity_tags', blank=True)
    status = models.CharField(
        max_length=128, choices=Status.choices, default=Status.NONE)
    start_date = models.DateTimeField(verbose_name='Start Date', )
    end_date = models.DateTimeField(verbose_name='End Date', )
    assigned_to = models.ManyToManyField(get_user_model(), verbose_name='Assigned To', related_name='assigners',
                                         blank=True)
    attendees = models.ManyToManyField(get_user_model(), related_name='activity_attendees', blank=True)
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='activities')


class ActivitiesLog(BaseModel):
    class Meta:
        db_table = 'activities_log'
        ordering = ['-start_date']

    class Status(models.TextChoices):
        NONE = 'none', 'None'
        DRAFT = 'draft', 'Draft'
        APPROVED = 'approved', 'Approved'
        UPCOMING = 'upcoming', 'Upcoming'
        COMPLETED = 'completed', 'Completed'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IN_COMPLETE = 'in_complete', 'In Complete'
        PAST_DUE = 'past_due', 'Past Due'
        UNCONFIRMED = 'unconfirmed', 'Unconfirmed'

    class Type(models.TextChoices):
        EVENT = 'event', 'Event'
        TODO = 'todo', 'Todo'
        DAILY_LOG = 'daily_log', 'Daily Log'
        PROPOSAL = 'proposal', 'Proposal'
        CHANGE_ORDER = 'change_order', 'Change Order'

    title = models.CharField(max_length=128, blank=True)
    type = models.CharField(max_length=128, choices=Type.choices, default=Type.EVENT)
    phase = models.CharField(max_length=128, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=128, choices=Status.choices, default=Status.NONE)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ManyToManyField(get_user_model(), related_name='activities_log_assigned_to',
                                         blank=True)
    lead = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='activities_log_lead')
    type_id = models.IntegerField(null=True, blank=True)


class Photos(BaseModel):
    class Meta:
        db_table = 'photos'
        ordering = ['-modified_date']

    photo = models.ImageField(upload_to='photo')
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='photos', null=True)


class NoteTemplate(BaseModel):
    class Meta:
        db_table = 'note_template'
        ordering = ['-modified_date']

    name = models.CharField(max_length=128, blank=True)
    note = models.TextField(blank=True)


class Status(models.TextChoices):
    TEXT = 'text', 'TEXT'
    EMAIL = 'email', 'EMAIL'
    CALL = 'call', 'CALL'


class Communication(BaseModel):
    lead = models.ForeignKey(
        LeadDetail, on_delete=models.CASCADE, related_name='communication_lead', null=True)

    number = models.IntegerField(null=True, blank=True)
    last_date = models.DateTimeField(auto_now=True, blank=True, null=True)
    type = models.CharField(max_length=128, choices=Status.choices, default=Status.TEXT)


class StatusJob(models.TextChoices):
    OPENED = 'opened', 'OPENED'
    PENDING = 'pending', 'PENDING'
    SUCCESS = 'success', 'SUCCESS'


class Job(BaseModel):
    lead = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='job_lead', null=True)
    title = models.CharField('Jobs Title', max_length=128)
    street_address = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=128, blank=True, default='', null=True)
    state = models.CharField(max_length=128, blank=True, default='', null=True)
    zip_code = models.CharField(max_length=16, blank=True)
    salesperson = models.ManyToManyField(get_user_model(), related_name='jobs_persons', blank=True)
    status = models.CharField(max_length=128, choices=StatusJob.choices, default=StatusJob.OPENED)
    confident = models.IntegerField(null=True, blank=True)
    estimate_revenue_from = models.DecimalField(
        max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    estimate_revenue_to = models.DecimalField(
        max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    projected_sale_date = models.DateTimeField(verbose_name='Projected Sales Date', null=True)
    project_types = models.ManyToManyField(ProjectType, related_name='jobs_project_type', blank=True)
    sources = models.ManyToManyField(SourceLead, related_name='jobs_source', blank=True)
    tags = models.ManyToManyField(TagLead, related_name='job_tags', blank=True)
    note = models.TextField(blank=True)