from decimal import Decimal
from django.db import models
from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db.models import Sum
from api.middleware import get_request

from api.models import BaseModel
from base.constants import DECIMAL_PLACE, MAX_DIGIT
from sales.models import Catalog


class UnitLibrary(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(default='', blank=True)

    class Meta:
        unique_together = ('name', 'company')

    def get_related_cost_table(self, unit_name):
        model = apps.get_model(app_label='sales', model_name='Catalog')
        catalogs = model.objects.filter(c_table__data__icontains=unit_name, company=get_request().user.company)
        return catalogs


class DataEntry(BaseModel):

    name = models.CharField(max_length=128)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.SET_NULL,
                             blank=True, null=True, related_name='data_entries')
    is_dropdown = models.BooleanField(default=False)
    dropdown = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)
    is_material_selection = models.BooleanField(default=False, blank=True, null=True)
    material_selections = models.ManyToManyField('sales.Catalog', blank=True,
                                                 related_name='data_entries', symmetrical=False)
    levels = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)
    material = models.JSONField(blank=True, null=True, default=dict)
    default_column = models.JSONField(blank=True, default=dict)
    is_show = models.BooleanField(default=True, blank=True)

    def __int__(self):
        return self.pk

    def export_to_json(self):
        unit = self.unit.name if self.unit else None
        material_selections = ','.join([str(i.name) for i in self.material_selections.all()])
        return [self.name, unit, self.is_dropdown, str(self.dropdown), self.is_material_selection,
                material_selections]


class RoundUpChoice(models.TextChoices):
    WHOLE_NUMBER = 'whole_number', 'Whole Number'
    INCREMENT = 'increment', 'Increment'


class RoundUpActionChoice(models.TextChoices):
    WHOLE_NUMBER = 'whole_number', 'Whole Number'
    INCREMENT = 'increment', 'Increment'
    NONE = 'none', 'None'


class POFormula(BaseModel):

    name = models.CharField(max_length=128)
    linked_description = ArrayField(models.JSONField(default=dict), default=list, blank=True, null=True)
    formula = models.TextField(blank=True)
    group = models.ForeignKey('sales.POFormulaGrouping', blank=True, related_name='group_formulas', null=True, on_delete=models.SET_NULL)
    assemble = models.ForeignKey('sales.Assemble', blank=True, related_name='assemble_formulas', null=True, on_delete=models.SET_NULL)
    created_from = models.IntegerField(default=None, blank=True, null=True)
    is_show = models.BooleanField(default=True, blank=True)  # Only show formula page
    quantity = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    markup = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    charge = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    material = models.TextField(blank=True)
    unit = models.CharField(max_length=32, blank=True)
    unit_price = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    cost = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    total_cost = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    margin = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=None, null=True)
    formula_mentions = models.TextField(blank=True)  # for FE
    formula_data_mentions = models.CharField(blank=True, max_length=256)  # for FE
    gross_profit = models.CharField(max_length=32, blank=True)
    description_of_formula = models.TextField(blank=True)
    formula_scenario = models.TextField(blank=True)
    material_data_entry = models.JSONField(blank=True, default=dict, null=True)
    formula_for_data_view = models.IntegerField(blank=True, default=0, null=True)  # Used for dataview in other model
    original = models.IntegerField(default=0, blank=True, null=True)
    catalog_materials = ArrayField(models.JSONField(default=dict, null=True), default=list, blank=True, null=True)
    order = models.IntegerField(default=0, blank=True, null=True)
    default_column = models.JSONField(blank=True, default=dict, null=True)
    round_up = models.JSONField(blank=True, default=dict, null=True)
    order_quantity = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=None, null=True)

    def parse_material(self):
        primary_key = eval(self.material)
        pk_catalog, row_index = primary_key.get('id').split(':')
        return pk_catalog, row_index

    def get_link_catalog_by_material(self):
        try:
            pk_catalog, _ = self.parse_material()
            catalog = Catalog.objects.get(pk=pk_catalog)
            return catalog.get_full_ancestor()
        except:
            return []

    def _parse_value(self, name, value):
        return {
            'display_tag': f'@({name})[{name}]',
            'display': name,
            'value': value,
            'display_tag_with_parent': f'[{self.assemble.name}].[{self.name}].{name}',
        }

    def parse_value_with_tag(self):
        """
            Parse formula value for calculating
        """
        quantity = self._parse_value('Quantity', self.quantity)
        cost = self._parse_value('Cost', self.cost)
        charge = self._parse_value('Charge', self.charge)
        markup = self._parse_value('Markup', self.markup)
        return [quantity, cost, charge, markup]

    def status(self):
        if self.material and self.formula and self.formula_mentions:
            return True
        return False

    def get_related_formula(self):
        from sales.models.proposal import PriceComparison, ProposalWriting
        data = {}
        data['formulas'] = POFormula.objects.filter(is_show=True, formula__icontains=self.name).values('id', 'name')
        assembles = Assemble.objects.filter(is_show=True, assemble_formulas__original=self.pk).distinct()
        data['assembles'] = assembles.values('id', 'name')
        # for assemble in assembles:
        #     data['assembles'].append({
        #         'id': assemble.id, 'name': assemble.name,
        #         'formulas': POFormula.objects.filter(assemble__pk=assemble.id, original=self.pk).values('id', 'name')})

        # data['estimates'] = []
        # estimates = EstimateTemplate.objects.filter(
        #     is_show=True, assembles__assemble_formulas__original=self.pk
        # ).distinct()
        # for estimate in estimates:
        #     assembles = [assemble.id for assemble in estimate.assembles.all()]
        #     data['estimates'].append({
        #         'id': estimate.id, 'name': estimate.name,
        #         'formulas': POFormula.objects.filter(assemble__pk__in=assembles, original=self.pk).values('id', 'name')
        #     })
        #
        # data['price_comparisons'] = []
        # price_comparisons = PriceComparison.objects.filter(
        #     groups__estimate_templates__assembles__assemble_formulas__original=self.pk
        # ).distinct()
        # for price_comparison in price_comparisons:
        #     formulas = price_comparison.get_formulas()
        #     data['price_comparisons'].append({
        #         'id': price_comparison.id, 'name': price_comparison.name,
        #         'formulas': formulas.filter(original=self.pk).values('id', 'name')
        #     })
        #
        # data['proposal_writings'] = []
        # proposal_writings = ProposalWriting.objects.filter(
        #     writing_groups__estimate_templates__assembles__assemble_formulas__original=self.pk
        # ).distinct()
        # for proposal_writing in proposal_writings:
        #     formulas = proposal_writing.get_data_formula()
        #     data['proposal_writings'].append({
        #         'id': proposal_writing.id, 'name': proposal_writing.name,
        #         'formulas': formulas.filter(original=self.pk).values('id', 'name')
        #     })
        return data

    def export_to_json(self):
        group = self.group
        if group:
            group = group.id
        return [
            self.name, str(self.linked_description), self.formula, self.group, self.quantity, self.markup,
            self.charge, str(self.material), self.unit, self.unit_price, self.cost, self.total_cost,
            self.formula_mentions, self.gross_profit, self.description_of_formula, self.formula_scenario,
            str(self.material_data_entry), str(self.catalog_materials)
        ]

    def get_unit_cost(self):
        try:
            return Decimal(self.default_column.get('value', 0))
        except TypeError:
            return 0

    def get_total_cost(self):
        return self.quantity * self.get_unit_cost()

    def get_unit_price(self):
        return self.get_unit_cost()

    def get_charge(self):
        return ((100 + self.markup)/100) * self.get_unit_price()


class POFormulaToDataEntry(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    po_formula = models.ForeignKey(POFormula, on_delete=models.CASCADE, blank=True,
                                   null=True, related_name='self_data_entries')
    value = models.CharField(verbose_name='Default Value', max_length=32, blank=True)
    index = models.IntegerField(blank=True, default=0, null=True)
    dropdown_value = models.JSONField(blank=True, default=dict)
    material_value = models.JSONField(blank=True, default=dict)
    estimate_template = models.ForeignKey('sales.EstimateTemplate', on_delete=models.CASCADE,
                                          blank=True, null=True, related_name='data_entries')
    copies_from = ArrayField(models.JSONField(blank=True, default=dict, null=True), default=list, blank=True, null=True)
    group = models.CharField(blank=True, default='', max_length=128)
    material_data_entry_link = ArrayField(models.JSONField(default=dict), default=list, blank=True, null=True)  # Need delete
    levels = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)  # Next level of data entry
    is_client_view = models.BooleanField(blank=True, default=False)

    def get_value(self):
        return self.value or self.dropdown_value.get('value')

    def get_unit(self):
        if self.data_entry.unit:
            return self.data_entry.unit.name
        return None


class MaterialView(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=128, default='', blank=True)
    material_value = models.JSONField(blank=True, default=dict)
    copies_from = ArrayField(models.JSONField(blank=True, default=dict, null=True), default=list, blank=True, null=True)
    estimate_template = models.ForeignKey('sales.EstimateTemplate', on_delete=models.CASCADE,
                                          blank=True, null=True, related_name='material_views')
    catalog_materials = ArrayField(models.JSONField(blank=True, default=dict, null=True), default=list, blank=True,
                                   null=True)
    levels = ArrayField(models.JSONField(default=dict), default=list, blank=True, null=True)
    is_client_view = models.BooleanField(blank=True, default=False)
    default_column = models.JSONField(blank=True, default=dict)


class POFormulaGrouping(BaseModel):
    name = models.CharField(max_length=128)


class Assemble(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_show = models.BooleanField(default=True, blank=True)
    original = models.IntegerField(default=0, blank=True, null=True)

    def export_to_json(self):
        return [self.name]


class DescriptionLibrary(BaseModel):
    name = models.CharField(max_length=128)
    linked_description = models.TextField(verbose_name='Description', blank=True)


class EstimateTemplate(BaseModel):
    class Meta:
        permissions = [('takeoff', 'Takeoff')]
    name = models.CharField(max_length=128)
    proposal_name = models.CharField(max_length=128, blank=True, default='')
    assembles = models.ManyToManyField(Assemble, related_name='estimate_templates', blank=True, )
    contract_description = models.TextField(blank=True, default='')
    catalog_links = ArrayField(models.CharField(max_length=128, blank=True, default=''), default=list, blank=True)
    group_by_proposal = models.ForeignKey('sales.GroupByEstimate', on_delete=models.CASCADE,
                                          related_name='estimate_templates', null=True, blank=True)
    is_show = models.BooleanField(default=True, blank=True)
    original = models.IntegerField(default=0, blank=True, null=True)
    order = models.IntegerField(default=0, blank=True)
    is_checked = models.BooleanField(default=False, blank=True)
    description = models.TextField(blank=True, default='')
    changed_description = models.TextField(blank=True, default='')  # change order
    note = models.TextField(blank=True, default='')
    changed_items = ArrayField(models.JSONField(blank=True, default=dict, null=True),
                               default=list, blank=True, null=True)  # change order
    quantity = models.JSONField(blank=True, default=None, null=True)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_formula(self):
        assembles = self.assembles.all()
        poformulas = POFormula.objects.none()
        for assemble in assembles:
            poformulas |= assemble.assemble_formulas.all()
        return poformulas

    def export_to_json(self):
        return [self.name]

    def get_value_quantity(self):
        return 1

    def get_info(self):
        self.info = self.get_formula().aggregate(total_charge=Sum('charge'), unit_cost=Sum('cost'),
                                                 unit_price=Sum('unit_price'), quantity=Sum('quantity'),
                                                 total_cost=Sum('total_cost'))

    def get_total_prices(self):
        return self.info.get('total_charge')

    def get_unit_cost(self):
        return self.info.get('unit_cost')

    def get_total_cost(self):
        return self.info.get('total_cost')

    def get_unit_price(self):
        return self.info.get('unit_price')

    def get_quantity(self):
        return self.info.get('quantity')


class DataView(BaseModel):
    class Type(models.TextChoices):
        COST = 'cost', 'Cost'
        CHARGE = 'charge', 'Charge'
        PROFIT = 'profit', 'Profit'
        CUSTOM = 'custom', 'Custom'

    name = models.CharField(verbose_name='Formula Name', max_length=128)
    formula = models.TextField(verbose_name='Formula', blank=True)
    estimate_template = models.ForeignKey('sales.EstimateTemplate', on_delete=models.CASCADE, related_name='data_views',
                                          null=True, blank=True)
    index = models.IntegerField(blank=True, default=0, null=True)
    type = models.CharField(max_length=8, choices=Type.choices, default=Type.CUSTOM, blank=True)
    value = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
    is_client_view = models.BooleanField(blank=True, default=False)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.SET_NULL,
                             blank=True, null=True, related_name='data_views')
    result = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, blank=True, default=0, null=True)
