from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel


class ProposalTemplate(BaseModel):
    class Meta:
        db_table = 'proposal_template'

    name = models.CharField(max_length=64)
    proposal_formatting = models.ForeignKey('ProposalFormatting', on_delete=models.CASCADE,
                                            related_name='proposal_formatting_template', null=True)
    config = models.JSONField(default=dict)


class ProposalElement(BaseModel):
    class Meta:
        db_table = 'proposal_element'

    proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
                                          related_name='proposal_template_element', null=True)
    title = models.CharField(max_length=128, blank=True)
    display_order = models.IntegerField(blank=True, null=True)


class ProposalWidget(BaseModel):
    class Meta:
        db_table = 'proposal_widget'

    proposal_element = models.ForeignKey(ProposalElement, on_delete=models.CASCADE,
                                         related_name='proposal_widget_element', null=True)
    type_widget = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=128, blank=True)
    display_order = models.IntegerField(blank=True, null=True)
    data_widget = models.JSONField(default=dict)


class PriceComparison(BaseModel):
    name = models.CharField(max_length=128)
    cost_different = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)


class ProposalWriting(BaseModel):
    name = models.CharField(max_length=128)
    total_project_price = models.IntegerField(blank=True, default=0, null=True)
    total_project_cost = models.IntegerField(blank=True, default=0, null=True)
    gross_profit = models.IntegerField(blank=True, default=0, null=True)
    gross_profit_percent = models.IntegerField(blank=True, default=0, null=True)
    avg_markup = models.IntegerField(blank=True, default=0, null=True)
    costs = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)


class ProposalFormatting(BaseModel):
    class Meta:
        db_table = 'proposal_formatting'

    name = models.CharField(max_length=64)
    proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
                                          related_name='proposal_template_formatting', null=True)


class GroupByEstimate(BaseModel):
    name = models.CharField(max_length=128)
    order = models.IntegerField(default=0, blank=True, null=True)
    writing = models.ForeignKey('sales.ProposalWriting', null=True, blank=True,
                                on_delete=models.CASCADE, related_name='writing_groups')


# class ProposalTemplateConfig(BaseModel):
#     class Meta:
#         db_table = 'proposal_template_config'
#     proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
#                                           related_name='config_proposal_template', null=True)
#     config = models.JSONField(default=dict)