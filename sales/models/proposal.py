from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from api.models import BaseModel
from sales.models import EstimateTemplate, Assemble, POFormula, Catalog
from base.constants import true, null, false


class ProposalTemplate(BaseModel):
    class Meta:
        db_table = 'proposal_template'

    name = models.CharField(max_length=64)
    # proposal_formatting = models.ForeignKey('ProposalFormatting', on_delete=models.CASCADE,
    #                                         related_name='proposal_formatting_template', null=True)
    screen_shot = models.CharField(max_length=1000, blank=True)


class ProposalTemplateConfig(BaseModel):
    class Meta:
        db_table = 'proposal_template_config'

    proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
                                          related_name='proposal_formatting_template_config', null=True)
    config = models.JSONField(default=dict)
    html_code = models.TextField(blank=True, null=True)
    css_code = models.TextField(blank=True, null=True)


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
    budget = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    total_project_price = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    total_project_cost = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    gross_profit = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    gross_profit_percent = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    avg_markup = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    cost_breakdown = models.JSONField(blank=True, null=True, default=dict)

    add_on_total_project_price = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    add_on_total_project_cost = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    add_on_gross_profit = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    add_on_gross_profit_percent = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    add_on_avg_markup = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    add_on_cost_breakdown = models.JSONField(blank=True, null=True, default=dict)

    additional_cost_total_project_price = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    additional_cost_total_project_cost = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    additional_cost_gross_profit = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    additional_cost_gross_profit_percent = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    additional_cost_avg_markup = models.DecimalField(blank=True, default=0, max_digits=99, decimal_places=2, null=True)
    additional_cost_breakdown = models.JSONField(blank=True, null=True, default=dict)

    project_start_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    project_end_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    estimated_start_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    estimated_end_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    additional_information = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)

    def __str__(self):
        return self.name

    def _get_poformula(self):
        groups = self.writing_groups.all()
        estimates = EstimateTemplate.objects.none()
        for group in groups:
            estimates |= group.estimate_templates.all()
        assembles = Assemble.objects.none()
        for estimate in estimates:
            assembles |= estimate.assembles.all()
        poformulas = POFormula.objects.none()
        for assemble in assembles:
            poformulas |= assemble.assemble_formulas.all()
        return poformulas

    def get_data_formula(self):
        """Get data from po formula"""
        poformulas = self._get_poformula()
        return poformulas

    def get_imgs(self):
        """Get image from catalog"""
        poformulas = self._get_poformula()
        catalog_ids = set()
        for poformula in poformulas:
            primary_key = eval(poformula.material)
            pk_catalog, row_index = primary_key.get('id').split(':')
            catalog_ids.add(pk_catalog)
        catalogs = Catalog.objects.filter(pk__in=catalog_ids)
        ancestors = []
        for catalog in catalogs:
            ancestors.extend(catalog.get_ancestors())
        return set(ancestors)


class ProposalFormatting(BaseModel):
    class Meta:
        db_table = 'proposal_formatting'

    screen_shot = models.CharField(max_length=1000, blank=True)
    name = models.CharField(max_length=64)
    proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
                                          related_name='proposal_template_formatting', null=True)
    proposal_writing = models.ForeignKey('sales.ProposalWriting', on_delete=models.SET_NULL,
                                         related_name='proposal_formatting', null=True, blank=True)
    show_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)


class ProposalFormattingConfig(BaseModel):
    class Meta:
        db_table = 'proposal_formatting_config'

    name = models.CharField(max_length=64)
    proposal_formatting = models.ForeignKey(ProposalFormatting, on_delete=models.CASCADE,
                                            related_name='config_proposal_formatting', null=True)
    config = models.JSONField(default=dict)
    html_code = models.TextField(blank=True, null=True)
    css_code = models.TextField(blank=True, null=True)


class GroupByEstimate(BaseModel):

    class Type(models.IntegerChoices):
        GENERAL = 0, 'General'
        ADD_ON = 1, 'Add-on'
        ADDITIONAL_COST = 2, 'Additional-cost'

    order = models.IntegerField(default=0, blank=True, null=True)
    writing = models.ForeignKey('sales.ProposalWriting', null=True, blank=True,
                                on_delete=models.CASCADE, related_name='writing_groups')
    open_index = models.CharField(max_length=64, blank=True, default='')
    type = models.IntegerField(default=Type.GENERAL, blank=True, choices=Type.choices)


# class ProposalTemplateConfig(BaseModel):
#     class Meta:
#         db_table = 'proposal_template_config'
#     proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
#                                           related_name='config_proposal_template', null=True)
#     config = models.JSONField(default=dict)