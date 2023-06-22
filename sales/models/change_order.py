from django.db import models

from api.models import BaseModel


class GroupEstimate(BaseModel):
    name = models.CharField(max_length=128, blank=True)
    order = models.IntegerField(blank=True, default=0)
    estimates = models.ManyToManyField('sales.EstimateTemplate', blank=True, symmetrical=False,
                                       related_name='change_order_group')
    change_order = models.ForeignKey('sales.ChangeOrder', on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='groups')


class ChangeOrder(BaseModel):
    name = models.CharField(max_length=128)
    proposal = models.ForeignKey('sales.ProposalFormatting', null=True, blank=True,
                                 on_delete=models.CASCADE, related_name='change_orders')
    existing_estimates = models.ManyToManyField('sales.EstimateTemplate', blank=True,
                                                related_name='change_order', symmetrical=False)
