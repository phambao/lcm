from django.db import models

from api.models import BaseModel


class ChangeOrder(BaseModel):
    name = models.CharField(max_length=128)
    proposal = models.ForeignKey('sales.ProposalFormatting', null=True, blank=True,
                                 on_delete=models.CASCADE, related_name='change_orders')
    existing_estimates = models.ManyToManyField('sales.EstimateTemplate', blank=True,
                                                related_name='change_order', symmetrical=False)
    add_new_estimates = models.ManyToManyField('sales.EstimateTemplate', blank=True, symmetrical=False,
                                               related_name='new_change_order')
