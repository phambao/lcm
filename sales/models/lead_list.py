from django.db import models

from api.models import BaseModel


class LeadDetail(BaseModel):

    # General
    class State(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSE = 'close', 'Close'

    class ProposalStatus(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        RELEASE = 'release', 'Release'
        UNRELEASED = 'unreleased', 'Unreleased'

    lead_title = models.CharField(max_length=128)
    street_address = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=16, choices=State.choices, default=State.OPEN)
    proposal_status = models.CharField(max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.APPROVED)
    zip_code = models.CharField(max_length=6)
    notes = models.TextField(blank=True)
    confidence = models.IntegerField(default=0)
    estimate_revenue_from = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True)
    estimate_revenue_to = models.DecimalField(max_digits=9, decimal_places=2, default=0, blank=True)
    projected_sale_date = models.DateTimeField()
    # project_type = models
    source = models.CharField(max_length=128, blank=True)
    tags = models.CharField(max_length=128, blank=True)
