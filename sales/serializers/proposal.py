from rest_framework import serializers
from django.apps import apps
from django.urls import reverse

from base.tasks import activity_log
from base.utils import pop, extra_kwargs_for_base_model
from api.middleware import get_request
from sales.models import ProposalTemplate, ProposalElement, ProposalWidget, PriceComparison, ProposalFormatting, \
    ProposalWriting, GroupByEstimate, ProposalTemplateConfig, ProposalFormattingConfig, GroupEstimatePrice, \
    ProposalFormattingSign, ProposalSetting
from sales.models.lead_list import ActivitiesLog
from sales.serializers import ContentTypeSerializerMixin, estimate
from sales.serializers.catalog import CatalogImageSerializer
from sales.serializers.estimate import EstimateTemplateSerializer
from sales.serializers.lead_list import ContactsSerializer


class ProposalWidgetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProposalWidget
        fields = ('id', 'proposal_element', 'type_widget', 'title', 'display_order', 'data_widget')


class ProposalElementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    proposal_widget_element = ProposalWidgetSerializer('proposal_element', allow_null=True, required=False, many=True)

    class Meta:
        model = ProposalElement
        fields = ('id', 'proposal_template', 'display_order', 'proposal_widget_element', 'title')


class ProposalTemplateHtmlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalTemplateConfig
        fields = ('id', 'html_code', 'css_code')


class ProposalTemplateHtmlCssSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    proposal_template_element = ProposalElementSerializer('proposal_template', allow_null=True, required=False,
                                                          many=True)
    config_proposal_template = ProposalTemplateHtmlSerializer(allow_null=True, required=False)

    class Meta:
        model = ProposalTemplate
        fields = ('id', 'name', 'proposal_template_element', 'config_proposal_template', 'screen_shot', 'created_date', 'user_create')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context['request'].path != reverse('proposal') or (self.context['request'].method != 'GET' and self.context['request'].path == reverse('proposal')):
            temp = instance.proposal_formatting_template_config.first()
            rs = ProposalTemplateHtmlSerializer(temp)
            data['config_proposal_template'] = rs.data
        return data


class ProposalTemplateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalTemplateConfig
        fields = ('id', 'config', 'html_code', 'css_code', 'script')


class ProposalTemplateSerializer(ContentTypeSerializerMixin):
    id = serializers.IntegerField(required=False)
    proposal_template_element = ProposalElementSerializer('proposal_template', allow_null=True, required=False,
                                                          many=True)
    config_proposal_template = ProposalTemplateConfigSerializer('proposal_template', allow_null=True, required=False)

    class Meta:
        model = ProposalTemplate
        fields = ('id', 'name', 'proposal_template_element', 'config_proposal_template',
                  'screen_shot', 'created_date', 'user_create', 'is_default')
        read_only_fields = ('is_default',)

    def create(self, validated_data):
        elements = pop(validated_data, 'proposal_template_element', [])
        config_proposal_template = pop(validated_data, 'config_proposal_template', dict())
        config = dict()
        html_code = None
        css_code = None
        script = None
        if config_proposal_template != dict():
            config = config_proposal_template['config']
            html_code = config_proposal_template['html_code']
            css_code = config_proposal_template['css_code']
            script = config_proposal_template['script']
        proposal_template = ProposalTemplate.objects.create(
            **validated_data
        )
        ProposalTemplateConfig.objects.create(
            proposal_template=proposal_template,
            config=config,
            html_code=html_code,
            css_code=css_code,
            script=script
        )
        data_create_widget = []
        for element in elements:
            proposal_element = ProposalElement.objects.create(
                proposal_template=proposal_template,
                title=element['title'],
                display_order=element['display_order']
            )
            for widget in element['proposal_widget_element']:
                data = ProposalWidget(
                    proposal_element=proposal_element,
                    type_widget=widget['type_widget'],
                    title=widget['title'],
                    display_order=widget['display_order'],
                    data_widget=widget['data_widget']
                )
                data_create_widget.append(data)

        ProposalWidget.objects.bulk_create(data_create_widget)
        return proposal_template

    def update(self, instance, data):
        elements = pop(data, 'proposal_template_element', [])
        config_proposal_template = pop(data, 'config_proposal_template', dict())
        config = dict()
        html_code = None
        css_code = None
        script = None
        if config_proposal_template != dict():
            config = config_proposal_template['config']
            html_code = config_proposal_template['html_code']
            css_code = config_proposal_template['css_code']
            script = config_proposal_template['script']
        proposal_template = ProposalTemplate.objects.filter(pk=instance.pk)
        proposal_template.update(**data)
        temp = proposal_template.first()
        proposal_template_config = ProposalTemplateConfig.objects.filter(
            proposal_template=temp
        )
        proposal_template_config.update(config=config, html_code=html_code, css_code=css_code, script=script)

        data_create_widget = []
        proposal_element = ProposalElement.objects.filter(proposal_template=proposal_template.first().id)
        proposal_element.delete()
        for element in elements:
            proposal_element = ProposalElement.objects.create(
                proposal_template=proposal_template.first(),
                title=element['title'],
                display_order=element['display_order']
            )
            for widget in element['proposal_widget_element']:
                data = ProposalWidget(
                    proposal_element=proposal_element,
                    type_widget=widget['type_widget'],
                    title=widget['title'],
                    display_order=widget['display_order'],
                    data_widget=widget['data_widget']
                )
                data_create_widget.append(data)

        ProposalWidget.objects.bulk_create(data_create_widget)
        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        temp = instance.proposal_formatting_template_config.first()
        rs = ProposalTemplateConfigSerializer(temp)
        data['config_proposal_template'] = rs.data
        return data


class GroupEstimatePriceSerializer(serializers.ModelSerializer):
    estimate_templates = EstimateTemplateSerializer('group_price', many=True, required=False, allow_null=True)

    class Meta:
        model = GroupEstimatePrice
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'price_comparison': {'read_only': True}},
                        **{'id': {'read_only': False, 'required': False}}}

    def create_estimate_template(self, estimates):
        objs = []
        for estimate in estimates:
            serializer = EstimateTemplateSerializer(data=estimate, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False)
            objs.append(obj)
        return objs

    def create(self, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])
        pk = pop(validated_data, 'id', None)
        instance = super().create(validated_data)
        estimate_templates = self.create_estimate_template(estimate_templates)
        instance.estimate_templates.add(*estimate_templates)
        return instance


class GroupByEstimateMiniSerializer(serializers.ModelSerializer):
    estimate_templates = estimate.EstimateTemplateMiniSerializer('group_by_proposal', many=True, allow_null=True,
                                                                 required=False)
    class Meta:
        model = GroupByEstimate
        fields = ('id', 'estimate_templates', 'type', 'open_index')


class GroupByEstimateSerializers(serializers.ModelSerializer):
    estimate_templates = estimate.EstimateTemplateSerializer('group_by_proposal', many=True, allow_null=True,
                                                             required=False)

    class Meta:
        model = GroupByEstimate
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'writing': {'read_only': True}}}

    def create_estimate_template(self, estimate_templates, instance):
        open_index = int(instance.open_index or 0)
        for idx, estimate_template in enumerate(estimate_templates):
            is_selected = False
            if idx == open_index:
                is_selected = True
            serializer = estimate.EstimateTemplateSerializer(data=estimate_template, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(group_by_proposal_id=instance.pk, is_show=False, order=idx, is_selected=is_selected)

    def create(self, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])
        instance = super().create(validated_data)
        self.create_estimate_template(estimate_templates, instance)
        return instance

    def update(self, instance, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])
        self.create_estimate_template(estimate_templates, instance)
        return super().update(instance, validated_data)


class PriceComparisonCompactSerializer(ContentTypeSerializerMixin):
    class Meta:
        model = PriceComparison
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = ''
        estimate_ids = self.context['request'].GET.getlist('estimate')
        related_estimate = EstimateTemplate.objects.filter(
            group_price__price_comparison=instance, original__in=estimate_ids
        ).values_list('original')
        data['group_by'] = EstimateTemplate.objects.filter(id__in=related_estimate).distinct().values('id', 'name')
        return data


class PriceComparisonSerializer(ContentTypeSerializerMixin):
    groups = GroupEstimatePriceSerializer('price_comparison', many=True, allow_null=True,
                                          required=False)

    class Meta:
        model = PriceComparison
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def parse_cost_diff(self, cost_different, new_ids):
        different_cost = []
        for c in cost_different:
            try:
                c.update({'first_id': new_ids[int(c['first_id'])], 'second_id': new_ids[int(c['second_id'])]})
            except KeyError:
                """It update more than one time so we catch the second time"""
            different_cost.append(c)
        return different_cost

    def create_groups(self, groups, instance):
        ids = {}
        for group in groups:
            serializer = GroupEstimatePriceSerializer(data=group, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(price_comparison=instance)
            ids[group.get('id')] = obj.pk
        return ids

    def create(self, validated_data):
        groups = pop(validated_data, 'groups', [])
        instance = super().create(validated_data)
        new_ids = self.create_groups(groups, instance)
        cost_different = pop(validated_data, 'cost_different', [])
        instance.cost_different = self.parse_cost_diff(cost_different, new_ids)
        instance.save(update_fields=['cost_different'])
        activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                           PriceComparisonSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        groups = pop(validated_data, 'groups', [])
        instance.groups.all().delete()
        new_ids = self.create_groups(groups, instance)
        cost_different = pop(validated_data, 'cost_different', [])
        instance.cost_different = self.parse_cost_diff(cost_different, new_ids)
        instance.save(update_fields=['cost_different'])
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           PriceComparisonSerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)


class ProposalWritingDataSerializer(serializers.ModelSerializer):
    writing_groups = GroupByEstimateMiniSerializer('writing', many=True, allow_null=True, required=False)

    class Meta:
        model = ProposalWriting
        fields = ('id', 'name', 'writing_groups')


class ProposalWritingCompactSerializer(ContentTypeSerializerMixin):
    class Meta:
        model = ProposalWriting
        fields = '__all__'
        read_only_fields = ['status']
        extra_kwargs = extra_kwargs_for_base_model()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['house_address'] = ''
        data['customer_contact'] = []
        if instance.lead:
            data['house_address'] = instance.lead.street_address
            data['customer_contact'] = instance.lead.contacts.all().values(
                'first_name', 'last_name', 'gender', 'email', 'phone_contacts', 'street',
                'city', 'state', 'zip_code', 'country'
                )
        estimate_ids = self.context['request'].GET.getlist('estimate')
        related_estimates = EstimateTemplate.objects.filter(
            group_by_proposal__writing=instance, original__in=estimate_ids
        ).values_list('original')
        data['group_by'] = EstimateTemplate.objects.filter(pk__in=related_estimates).distinct().values('id', 'name')
        return data


class ProposalWritingByLeadSerializer(ProposalWritingCompactSerializer):
    class Meta:
        model = ProposalWriting
        fields = ('id', 'name', 'created_date', 'modified_date', 'total_project_cost', 'avg_markup')
        extra_kwargs = extra_kwargs_for_base_model()


class CostBreakDownSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_null=True)
    avg_markup = serializers.FloatField(required=False, allow_null=True)
    cost = serializers.FloatField(required=False, allow_null=True)
    count = serializers.FloatField(required=False, allow_null=True)
    markup = serializers.FloatField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)
    profit = serializers.FloatField(required=False, allow_null=True)
    profit_percent = serializers.FloatField(required=False, allow_null=True)
    total_price = serializers.FloatField(required=False, allow_null=True)


class WritingStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalWriting
        fields = ('status',)


class ProposalFormattingTemplateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalFormattingConfig
        fields = ('id', 'config', 'html_code', 'css_code', 'script')


class ProposalFormattingTemplateSerializer(ContentTypeSerializerMixin):

    class Meta:
        model = ProposalFormatting
        fields = ('id', 'html_code', 'css_code', 'config', 'screen_shot', 'show_writing_fields',
                  'show_estimate_fields', 'script', 'element', 'html_view')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['writing_groups'] = []
        data['images'] = []
        if instance.proposal_writing:
            data['writing_groups'] = ProposalWritingDataSerializer(instance.proposal_writing).data.get('writing_groups')
            imgs = instance.proposal_writing.get_imgs()
            images = CatalogImageSerializer(imgs, context=self.context, many=True).data
            data['images'] = images
        signs = ProposalFormattingTemplateSignSerializer(instance.sign_proposal_formatting.all(), many=True)
        data['signs'] = signs.data
        return data


class FormatEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = apps.get_model('sales', 'EstimateTemplate')
        fields = ('id', 'name', 'contract_description')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['unit'] = instance.unit.name if instance.unit else ''
        data['quantity'] = instance.get_value_quantity()
        instance.get_info()
        data['total_price'] = instance.get_total_prices()
        data['unit_price'] = data['total_price'] / data['quantity']
        data['description'] = data['contract_description']
        data['formulas'] = FormatFormulaSerializer(instance.get_formula().order_by('order'), many=True).data
        del data['contract_description']
        return data


class FormatFormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = apps.get_model('sales', 'POFormula')
        fields = ('id', 'name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'unit', 'order',
                  'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['catalog_name'] = instance.get_catalog()['name']
        data['total_price'] = instance.total_cost
        return data


Contact = apps.get_model('sales', 'Contact')
GroupTemplate = apps.get_model('sales', 'GroupTemplate')
POFormula = apps.get_model('sales', 'POFormula')
EstimateTemplate = apps.get_model('sales', 'EstimateTemplate')
from decimal import Decimal


class GroupTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupTemplate
        fields = ('id', 'name', 'order', 'is_single', 'items', 'is_formula', 'type', 'section')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_formula:
            formulas = POFormula.objects.filter(pk__in=instance.items)
            data['items'] = FormatFormulaSerializer(formulas, many=True).data
            data['total_price'] = sum(Decimal(d['total_cost'] or 0) for d in data['items'])
        else:
            estimates = EstimateTemplate.objects.filter(pk__in=instance.items)
            data['items'] = FormatEstimateSerializer(estimates, many=True).data
            data['total_price'] = sum(Decimal(d['total_price'] or 0) for d in data['items'])
        return data


class ProposalFormattingTemplateMinorSerializer(serializers.ModelSerializer):
    template_groups = GroupTemplateSerializer('proposal', many=True, allow_null=True, required=False)

    class Meta:
        model = ProposalFormatting
        fields = ('id', 'show_format_fields', 'show_formula_fields', 'contacts', 'intro', 'default_note', 'signature',
                  'pdf_file', 'closing_note', 'contract_note', 'print_date', 'primary_contact', 'sign_date',
                  'template_groups', 'template_type')
        read_only_fields = ['sign_date']

    def create(self, validated_data):
        template_groups = pop(validated_data, 'template_groups', [])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        template_groups = pop(validated_data, 'template_groups', [])
        instance.template_groups.all().delete()
        for idx, group in enumerate(template_groups):
            serializer = GroupTemplateSerializer(data=group)
            serializer.is_valid(raise_exception=True)
            serializer.save(proposal=instance, order=idx)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        estimates = instance.proposal_writing.get_checked_estimate().order_by('format_order')
        data['estimates'] = FormatEstimateSerializer(estimates, many=True).data
        data['total_price'] = sum([value['total_price'] for value in data['estimates']])
        data['contacts'] = ContactsSerializer(Contact.objects.filter(id__in=instance.contacts),
                                              many=True, context=self.context).data
        if not data['primary_contact']:
            data['primary_contact'] = instance.contacts[0] if instance.contacts else None
        data['lead'] = instance.proposal_writing.lead.get_info_for_proposal_formatting() if instance.proposal_writing.lead else None
        data['proposal_progress'] = instance.proposal_writing.additional_information
        data['number_column'] = ['quantity', 'unit_price', 'total_price', 'markup', 'charge',
                                 'unit_price', 'cost', 'total_cost', 'gross_profit']
        return data


class ProposalFormattingTemplateSignSerializer(ContentTypeSerializerMixin):
    url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = ProposalFormattingSign
        fields = '__all__'


class ProposalFormattingTemplateSignsSerializer(serializers.Serializer):
    signs = ProposalFormattingTemplateSignSerializer(many=True, allow_null=True, required=False)


class ProposalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalSetting
        fields = ('intro', 'default_note', 'pdf_file', 'closing_note', 'contract_note')


class ProposalWritingSerializer(ContentTypeSerializerMixin):
    writing_groups = GroupByEstimateSerializers('writing', many=True, allow_null=True, required=False)
    cost_breakdown = CostBreakDownSerializer(many=True, allow_null=True, required=False)
    proposal_formatting = ProposalFormattingTemplateMinorSerializer('proposal_writing', allow_null=True, required=False)

    class Meta:
        model = ProposalWriting
        fields = '__all__'
        read_only_fields = ['status']
        extra_kwargs = extra_kwargs_for_base_model()

    def create_group(self, writing_groups, instance):
        for writing_group in writing_groups:
            serializer = GroupByEstimateSerializers(data=writing_group, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(writing_id=instance.pk)

    def create_formatting(self, proposal_formatting, instance):
        if proposal_formatting:
            serializer = ProposalFormattingTemplateMinorSerializer(data=proposal_formatting, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(proposal_writing=instance)

    def create(self, validated_data):
        writing_groups = pop(validated_data, 'writing_groups', [])
        proposal_formatting = pop(validated_data, 'proposal_formatting', {})
        instance = super().create(validated_data)
        self.create_formatting(proposal_formatting, instance)
        self.create_group(writing_groups, instance)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                           ProposalWritingSerializer.__name__, __name__, self.context['request'].user.pk)
        if instance.lead:
            ActivitiesLog.objects.create(lead=instance.lead, status='draft', type_id=instance.pk,
                                        title=f'{instance.name}', type='proposal', start_date=instance.created_date)
        return instance

    def update(self, instance, validated_data):
        writing_groups = pop(validated_data, 'writing_groups', [])
        proposal_formatting = pop(validated_data, 'proposal_formatting', {})
        if hasattr(instance, 'proposal_formatting'):
            instance.proposal_formatting.delete()
            self.create_formatting(proposal_formatting, instance)
        instance.writing_groups.all().update(writing=None)
        self.create_group(writing_groups, instance)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           ProposalWritingSerializer.__name__, __name__, self.context['request'].user.pk)
        if hasattr(instance, 'proposal_formatting'):
            proposal_formatting = instance.proposal_formatting
            proposal_formatting.has_send_mail = False
            proposal_formatting.has_signed = False
            proposal_formatting.print_date = None
            proposal_formatting.signature = ''
            proposal_formatting.sign_date = None
            proposal_formatting.save()
        validated_data['status'] = 'draft'
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = get_request().user
        data['permissions'] = {
            'internal_view': user.check_perm('internal_view'),
            'client_view': user.check_perm('client_view')
        }

        return data
