from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.urls import reverse

from base.tasks import activity_log
from base.utils import pop, extra_kwargs_for_base_model
from sales.models import ProposalTemplate, ProposalElement, ProposalWidget, PriceComparison, ProposalFormatting, \
    ProposalWriting, GroupByEstimate, ProposalTemplateConfig, ProposalFormattingConfig, GroupEstimatePrice, \
    EstimateTemplate
from sales.serializers import estimate
from sales.serializers.catalog import CatalogImageSerializer
from sales.serializers.estimate import EstimateTemplateSerializer, POFormulaDataSerializer


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


class ProposalTemplateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    proposal_template_element = ProposalElementSerializer('proposal_template', allow_null=True, required=False,
                                                          many=True)
    config_proposal_template = ProposalTemplateConfigSerializer('proposal_template', allow_null=True, required=False)

    class Meta:
        model = ProposalTemplate
        fields = ('id', 'name', 'proposal_template_element', 'config_proposal_template', 'screen_shot', 'created_date', 'user_create')

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
        if self.context['request'].path != reverse('proposal') or (self.context['request'].method != 'GET' and self.context['request'].path == reverse('proposal')):
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
        for estimate_template in estimate_templates:
            serializer = estimate.EstimateTemplateSerializer(data=estimate_template, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(group_by_proposal_id=instance.pk, is_show=False)

    def reparse(self, data):
        writing = data.get('writing')
        if writing:
            data['writing'] = ProposalWriting.objects.get(pk=writing)
        comparison = data.get('comparison')
        if comparison:
            data['comparison'] = PriceComparison.objects.get(pk=comparison)
        return data

    def create(self, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])
        validated_data = self.reparse(validated_data)
        instance = super().create(validated_data)
        self.create_estimate_template(estimate_templates, instance)
        return instance

    def update(self, instance, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])
        self.create_estimate_template(estimate_templates, instance)
        validated_data = self.reparse(validated_data)
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        writing = data.get('writing')
        if writing:
            data['writing'] = writing.pk
        comparison = data.get('comparison')
        if comparison:
            data['comparison'] = comparison.pk
        return data


class PriceComparisonCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceComparison
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(PriceComparison).pk
        return data


class PriceComparisonSerializer(serializers.ModelSerializer):
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
                c.update({'first_id': new_ids[c['first_id']], 'second_id': new_ids[c['second_id']]})
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
        activity_log.delay(ContentType.objects.get_for_model(PriceComparison).pk, instance.pk, 1,
                           PriceComparisonSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        groups = pop(validated_data, 'groups', [])
        instance.groups.all().delete()
        new_ids = self.create_groups(groups, instance)
        cost_different = pop(validated_data, 'cost_different', [])
        instance.cost_different = self.parse_cost_diff(cost_different, new_ids)
        instance.save(update_fields=['cost_different'])
        activity_log.delay(ContentType.objects.get_for_model(PriceComparison).pk, instance.pk, 2,
                           PriceComparisonSerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(PriceComparison).pk
        return data


class ProposalWritingDataSerializer(serializers.ModelSerializer):
    writing_groups = GroupByEstimateMiniSerializer('writing', many=True, allow_null=True, required=False)

    class Meta:
        model = ProposalWriting
        fields = ('id', 'name', 'writing_groups')


class ProposalWritingCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalWriting
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(ProposalWriting).pk
        return data


class ProposalWritingSerializer(serializers.ModelSerializer):
    writing_groups = GroupByEstimateSerializers('writing', many=True, allow_null=True, required=False)

    class Meta:
        model = ProposalWriting
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def create_group(self, writing_groups, instance):
        for writing_group in writing_groups:
            serializer = GroupByEstimateSerializers(data=writing_group, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(writing_id=instance.pk)

    def create(self, validated_data):
        writing_groups = pop(validated_data, 'writing_groups', [])
        instance = super().create(validated_data)
        self.create_group(writing_groups, instance)
        activity_log.delay(ContentType.objects.get_for_model(ProposalWriting).pk, instance.pk, 1,
                           ProposalWritingSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        writing_groups = pop(validated_data, 'writing_groups', [])
        instance.writing_groups.all().update(writing=None)
        self.create_group(writing_groups, instance)
        activity_log.delay(ContentType.objects.get_for_model(ProposalWriting).pk, instance.pk, 2,
                           ProposalWritingSerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(ProposalWriting).pk
        return data


class ProposalFormattingTemplateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalFormattingConfig
        fields = ('id', 'config', 'html_code', 'css_code', 'script')


class ProposalFormattingTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProposalFormatting
        fields = ('id', 'html_code', 'css_code', 'config', 'screen_shot', 'show_fields', 'script', 'element')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(ProposalFormatting).pk
        data['row_data'] = []
        data['images'] = []
        if instance.proposal_writing:
            data['row_data'] = ProposalWritingDataSerializer(instance.proposal_writing).data
            imgs = instance.proposal_writing.get_imgs()
            images = CatalogImageSerializer(imgs, context=self.context, many=True).data
            data['images'] = images
        return data
