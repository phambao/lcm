from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.urls import reverse
from base.utils import pop, activity_log, extra_kwargs_for_base_model
from sales.models import ProposalTemplate, ProposalElement, ProposalWidget, PriceComparison, ProposalFormatting, \
    ProposalWriting, GroupByEstimate, ProposalTemplateConfig, ProposalFormattingConfig
from sales.serializers import estimate


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
        fields = ('id', 'config', 'html_code', 'css_code')


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
        if config_proposal_template != dict():
            config = config_proposal_template['config']
            html_code = config_proposal_template['html_code']
            css_code = config_proposal_template['css_code']
        proposal_template = ProposalTemplate.objects.create(
            **validated_data
        )
        ProposalTemplateConfig.objects.create(
            proposal_template=proposal_template,
            config=config,
            html_code=html_code,
            css_code=css_code
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
        if config_proposal_template != dict():
            config = config_proposal_template['config']
            html_code = config_proposal_template['html_code']
            css_code = config_proposal_template['css_code']
        proposal_template = ProposalTemplate.objects.filter(pk=instance.pk)
        proposal_template.update(**data)
        temp = proposal_template.first()
        proposal_template_config = ProposalTemplateConfig.objects.filter(
            proposal_template=temp
        )
        proposal_template_config.update(config=config, html_code=html_code, css_code=css_code)

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
    estimate_templates = estimate.EstimateTemplateSerializer('proposal_writing', many=True, allow_null=True,
                                                             required=False)

    class Meta:
        model = PriceComparison
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def create_estimate_template(self, estimate_templates, instance):
        new_id = {}
        for estimate_template in estimate_templates:
            serializer = estimate.EstimateTemplateSerializer(data=estimate_template, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(price_comparison_id=instance.pk, is_show=False)
            new_id[estimate_template['id']] = obj.pk
        return new_id

    def parse_cost_diff(self, cost_different, new_ids):
        different_cost = []
        for c in cost_different:
            try:
                c.update({'first_id': new_ids[c['first_id']], 'second_id': new_ids[c['second_id']]})
            except KeyError:
                """It update more than one time so we catch the second time"""
            different_cost.append(c)
        return different_cost

    def create(self, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])
        instance = super().create(validated_data)
        new_ids = self.create_estimate_template(estimate_templates, instance)
        cost_different = pop(validated_data, 'cost_different', [])
        instance.cost_different = self.parse_cost_diff(cost_different, new_ids)
        instance.save(update_fields=['cost_different'])
        activity_log(PriceComparison, instance, 1, PriceComparisonSerializer, {})
        return instance

    def update(self, instance, validated_data):
        estimate_templates = pop(validated_data, 'estimate_templates', [])

        instance.estimate_templates.all().update(price_comparison=None)
        new_ids = self.create_estimate_template(estimate_templates, instance)
        cost_different = pop(validated_data, 'cost_different', [])
        instance.cost_different = self.parse_cost_diff(cost_different, new_ids)
        instance.save(update_fields=['cost_different'])
        activity_log(PriceComparison, instance, 2, PriceComparisonSerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(PriceComparison).pk
        return data


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
        activity_log(ProposalWriting, instance, 1, ProposalWritingSerializer, {})
        return instance

    def update(self, instance, validated_data):
        writing_groups = pop(validated_data, 'writing_groups', [])
        instance.writing_groups.all().update(writing=None)
        self.create_group(writing_groups, instance)
        activity_log(ProposalWriting, instance, 2, ProposalWritingSerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(ProposalWriting).pk
        instance.get_imgs()
        return data


class ProposalFormattingTemplateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalFormattingConfig
        fields = ('id', 'config', 'html_code', 'css_code')


class ProposalFormattingTemplateSerializer(serializers.ModelSerializer):
    # choose_update_template = serializers.BooleanField(required=False)
    config_proposal_template = ProposalFormattingTemplateConfigSerializer('proposal_template', allow_null=True, required=False)

    class Meta:
        model = ProposalFormatting
        fields = ('id', 'name', 'config_proposal_template',
                  'screen_shot', 'proposal_writing', 'show_fields')

    def create_proposal_template(self, proposal_template, instance):
        serializer = ProposalTemplateSerializer(data=proposal_template)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def update_proposal_template(self, instance, proposal_template):
        serializer = ProposalTemplateSerializer(data=proposal_template)
        serializer.is_valid(raise_exception=True)
        serializer.update(instance, proposal_template)

    def create(self, validated_data):
        config_proposal_template = pop(validated_data, 'config_proposal_template', None)
        config = dict()
        html_code = None
        css_code = None
        if config_proposal_template != dict():
            config = config_proposal_template['config']
            html_code = config_proposal_template['html_code']
            css_code = config_proposal_template['css_code']
        # proposal_template_id = validated_data['proposal_template']
        # choose_update_template = pop(validated_data, 'choose_update_template', False)
        # if choose_update_template is True:
        #     proposal_template_config_update = ProposalTemplateConfig.objects.filter(
        #         proposal_template=proposal_template_id)
        #     proposal_template_config_update.update(config=config, html_code=html_code, css_code=css_code)
        #     proposal_template = ProposalTemplate.objects.filter(id=proposal_template_id.id)
        #     proposal_template.update(screen_shot=validated_data['screen_shot'])

        instance = super().create(validated_data)
        ProposalFormattingConfig.objects.create(
            proposal_formatting=instance,
            config=config,
            html_code=html_code,
            css_code=css_code
        )
        return instance

    def update(self, instance, validated_data):
        config_proposal_template = pop(validated_data, 'config_proposal_template', None)
        config = dict()
        html_code = None
        css_code = None
        if config_proposal_template != dict():
            config = config_proposal_template['config']
            html_code = config_proposal_template['html_code']
            css_code = config_proposal_template['css_code']
        # proposal_template_id = validated_data['proposal_template']
        # choose_update_template = pop(validated_data, 'choose_update_template', False)
        # if choose_update_template is True:
        #     proposal_template_config_update = ProposalTemplateConfig.objects.filter(
        #         proposal_template=proposal_template_id)
        #     proposal_template_config_update.update(config=config, html_code=html_code, css_code=css_code)
        #     proposal_template = ProposalTemplate.objects.filter(id=proposal_template_id.id)
        #     proposal_template.update(screen_shot=validated_data['screen_shot'])

        instance = super().update(instance, validated_data)
        temp = ProposalFormattingConfig.objects.filter(
            proposal_formatting=instance,
        )
        temp.update(config=config, html_code=html_code, css_code=css_code)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context['request'].path != reverse('proposal-formatting') or (self.context['request'].method != 'GET' and self.context['request'].path == reverse('proposal-formatting')):
            temp = instance.config_proposal_formatting.first()
            rs = ProposalFormattingTemplateConfigSerializer(temp)
            data['config_proposal_template'] = rs.data
        return data
