from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from api.models import BaseModel
from sales.models import EstimateTemplate, Assemble, POFormula, Catalog
from base.constants import DECIMAL_PLACE, MAX_DIGIT, true, null, false


class ProposalTemplate(BaseModel):
    class Meta:
        db_table = 'proposal_template'

    name = models.CharField(max_length=64)
    # proposal_formatting = models.ForeignKey('ProposalFormatting', on_delete=models.CASCADE,
    #                                         related_name='proposal_formatting_template', null=True)
    is_default = models.BooleanField(default=False, blank=True)
    screen_shot = models.CharField(max_length=1000, blank=True)


class ProposalTemplateConfig(BaseModel):
    class Meta:
        db_table = 'proposal_template_config'

    proposal_template = models.ForeignKey(ProposalTemplate, on_delete=models.CASCADE,
                                          related_name='proposal_formatting_template_config', null=True)
    config = models.JSONField(default=dict)
    html_code = models.TextField(blank=True, null=True)
    css_code = models.TextField(blank=True, null=True)
    script = models.TextField(blank=True, null=True)


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
    lead = models.ForeignKey('sales.LeadDetail', on_delete=models.CASCADE, related_name='price_comparisons',
                             blank=True, null=True)

    def get_formulas(self):
        groups = self.groups.all()
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


class ProposalWriting(BaseModel):
    name = models.CharField(max_length=128)
    budget = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    total_project_price = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    total_project_cost = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    gross_profit = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    gross_profit_percent = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    avg_markup = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    cost_breakdown = models.JSONField(blank=True, null=True, default=dict)

    add_on_total_project_price = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    add_on_total_project_cost = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    add_on_gross_profit = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    add_on_gross_profit_percent = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    add_on_avg_markup = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    add_on_cost_breakdown = models.JSONField(blank=True, null=True, default=dict)

    additional_cost_total_project_price = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    additional_cost_total_project_cost = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    additional_cost_gross_profit = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    additional_cost_gross_profit_percent = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    additional_cost_avg_markup = models.DecimalField(blank=True, default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, null=True)
    additional_cost_breakdown = models.JSONField(blank=True, null=True, default=dict)

    project_start_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    project_end_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    estimated_start_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    estimated_end_date = models.DateTimeField(blank=True, null=True, default=timezone.now)
    additional_information = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)

    lead = models.ForeignKey('sales.LeadDetail', on_delete=models.SET_NULL, blank=True, null=True, related_name='proposals')

    class Meta:
        permissions = [('client_view', 'Client View'), ('internal_view', 'Internal View')]

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

    def get_estimates(self):
        groups = self.writing_groups.all()
        estimates = EstimateTemplate.objects.none()
        for group in groups:
            estimates |= group.estimate_templates.all()
        return estimates

    def get_checked_estimate(self):
        return self.get_estimates().filter(is_selected=True)

    def get_checked_formula(self):
        estimates = self.get_checked_estimate()
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
            try:
                primary_key = eval(poformula.material)
            except SyntaxError:
                continue
            if isinstance(primary_key, dict) and primary_key:
                """Somehow material on poformula is still string so we ignore this"""
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

    screen_shot = models.TextField(blank=True, default='')
    config = models.JSONField(default=dict, blank=True)
    html_code = models.TextField(blank=True, null=True, default='')
    css_code = models.TextField(blank=True, null=True, default='')
    script = models.TextField(blank=True, null=True, default='')
    proposal_writing = models.OneToOneField('sales.ProposalWriting', on_delete=models.SET_NULL,
                                            related_name='proposal_formatting', null=True, blank=True)
    show_writing_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    show_estimate_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    show_format_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    has_send_mail = models.BooleanField(default=False, blank=True)
    has_signed = models.BooleanField(default=False, blank=True)
    element = models.TextField(blank=True, null=True, default='')
    html_view = models.TextField(blank=True, null=True, default='')
    contacts = ArrayField(models.IntegerField(blank=True, null=True, default=None), default=list, blank=True, null=True)
    print_date = models.DateTimeField(default=None, blank=True, null=True)
    intro = models.TextField(blank=True)
    default_note = models.TextField(blank=True)
    pdf_file = models.CharField(max_length=128, blank=True)
    closing_note = models.TextField(blank=True)
    contract_note = models.TextField(blank=True)
    primary_contact = models.IntegerField(blank=True, null=True, default=None)
    otp = models.CharField(max_length=8, blank=True, default='', null=True)
    signature = models.CharField(max_length=256, blank=True, default='')


class ProposalFormattingConfig(BaseModel):
    class Meta:
        db_table = 'proposal_formatting_config'

    name = models.CharField(max_length=64)
    proposal_formatting = models.ForeignKey(ProposalFormatting, on_delete=models.CASCADE,
                                            related_name='config_proposal_formatting', null=True)
    config = models.JSONField(default=dict)
    html_code = models.TextField(blank=True, null=True)
    css_code = models.TextField(blank=True, null=True)
    script = models.TextField(blank=True, null=True)


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


class GroupEstimatePrice(BaseModel):
    name = models.CharField(max_length=128, blank=True)
    order = models.IntegerField(blank=True, default=0)
    estimate_templates = models.ManyToManyField('sales.EstimateTemplate', blank=True, symmetrical=False,
                                                related_name='group_price')
    price_comparison = models.ForeignKey('sales.PriceComparison', on_delete=models.CASCADE, blank=True, null=True,
                                         related_name='groups')


class ProposalFormattingSign(BaseModel):
    class Meta:
        db_table = 'proposal_formatting_sign'

    proposal_formatting = models.ForeignKey(ProposalFormatting, on_delete=models.CASCADE,
                                            related_name='sign_proposal_formatting', null=True)
    sign = models.CharField(max_length=128, blank=True)
    is_show = models.BooleanField(default=False, blank=True)
    code = models.CharField(max_length=6, blank=True)
    email = models.CharField(max_length=128, blank=True)
    code_location = models.CharField(max_length=128, blank=True)


class ProposalSetting(BaseModel):
    intro = models.TextField(blank=True)
    default_note = models.TextField(blank=True)
    pdf_file = models.CharField(max_length=128, blank=True)
    closing_note = models.TextField(blank=True)
    contract_note = models.TextField(blank=True)
