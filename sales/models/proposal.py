from django.contrib.auth import get_user_model
from django.db import models

from api.models import BaseModel
from base.models.config import Config


class ProposalTemplate(BaseModel):
    class Meta:
        db_table = 'proposal_template'

    name = models.CharField(max_length=64)


class ProposalWidget(BaseModel):
    class Meta:
        db_table = 'proposal_widget'

    proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE, related_name='proposal__template_widget')
    type = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=128, blank=True)
    display_order = models.IntegerField(blank=True, null=True)
    data_widget = models.JSONField(default=dict)
