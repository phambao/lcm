from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from base.utils import pop, extra_kwargs_for_base_model
from base.tasks import activity_log
from sales.models import ChangeOrder, GroupEstimate, FlatRate, GroupFlatRate
from sales.models.change_order import WritingGroup
from sales.serializers.estimate import EstimateTemplateForInvoiceSerializer, EstimateTemplateSerializer, POFormulaDataSerializer, \
    POFormulaForInvoiceSerializer


class WritingGroupSerializer(serializers.ModelSerializer):
    estimate_templates = EstimateTemplateSerializer('change_order_group', many=True, required=False, allow_null=True)

    class Meta:
        model = WritingGroup
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'group': {'read_only': True}}}

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
        instance = super().create(validated_data)
        estimate_templates = self.create_estimate_template(estimate_templates)
        instance.estimate_templates.add(*estimate_templates)
        return instance


class GroupEstimateSerializer(serializers.ModelSerializer):
    estimate_templates = EstimateTemplateSerializer('change_order_group', many=True, required=False, allow_null=True)
    writing_groups = WritingGroupSerializer('group', many=True, required=False, allow_null=True)

    class Meta:
        model = GroupEstimate
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'change_order': {'read_only': True}}}

    def create_writing_groups(self, writing_groups, instance):
        for writing_group in writing_groups:
            obj = WritingGroupSerializer(data=writing_group, context=self.context)
            obj.is_valid(raise_exception=True)
            obj.save(group=instance)

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
        writing_groups = pop(validated_data, 'writing_groups', [])
        instance = super().create(validated_data)
        estimate_templates = self.create_estimate_template(estimate_templates)
        instance.estimate_templates.add(*estimate_templates)
        self.create_writing_groups(writing_groups, instance)
        return instance


class FlatRateSerializer(serializers.ModelSerializer):

    class Meta:
        model = FlatRate
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'group': {'read_only': True}}}


class GroupFlatRateSerializer(serializers.ModelSerializer):
    flat_rates = FlatRateSerializer('group', many=True, required=False, allow_null=True)

    class Meta:
        model = GroupFlatRate
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'change_order': {'read_only': True}}}

    def create_flat_rates(self, flat_rates, instance):
        for fl in flat_rates:
            serializer = FlatRateSerializer(data=fl, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(group=instance)

    def create(self, validated_data):
        flat_rates = pop(validated_data, 'flat_rates', [])
        instance = super().create(validated_data)
        self.create_flat_rates(flat_rates, instance)
        return instance


class ChangeOrderSerializerMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        proposal_writing = instance.proposal_writing
        data['proposal_name'] = proposal_writing.name if proposal_writing else None
        data['content_type'] = instance.get_content_type().pk
        return data


class ChangeOrderSerializerCompact(ChangeOrderSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ChangeOrder
        fields = '__all__'


class ChangeOrderSerializer(ChangeOrderSerializerMixin, serializers.ModelSerializer):
    existing_estimates = EstimateTemplateSerializer('change_order', many=True, required=False, allow_null=True)
    groups = GroupEstimateSerializer('change_order', many=True, required=False, allow_null=True)
    flat_rate_groups = GroupFlatRateSerializer('change_order', many=True, required=False, allow_null=True)

    class Meta:
        model = ChangeOrder
        fields = '__all__'
        extra_kwargs = {**{'approval_deadline': {'required': True}}, **extra_kwargs_for_base_model()}

    def create_existing_estimate(self, existing_estimates):
        objs = []
        for estimate in existing_estimates:
            serializer = EstimateTemplateSerializer(data=estimate, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False, group_by_proposal=None)
            objs.append(obj)
        return objs

    def create_groups(self, groups, instance):
        for group in groups:
            obj = GroupEstimateSerializer(data=group, context=self.context)
            obj.is_valid(raise_exception=True)
            obj.save(change_order=instance)

    def create_flat_rate_groups(self, flat_rate_groups, instance):
        for group in flat_rate_groups:
            serializer = GroupFlatRateSerializer(data=group, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(change_order=instance)

    def create(self, validated_data):
        existing_estimates = pop(validated_data, 'existing_estimates', [])
        groups = pop(validated_data, 'groups', [])
        flat_rate_groups = pop(validated_data, 'flat_rate_groups', [])
        objs = self.create_existing_estimate(existing_estimates)
        instance = super().create(validated_data)
        self.create_flat_rate_groups(flat_rate_groups, instance)
        self.create_groups(groups, instance)
        instance.existing_estimates.add(*objs)
        activity_log.delay(ContentType.objects.get_for_model(ChangeOrder).pk, instance.pk, 1,
                           ChangeOrderSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        existing_estimates = pop(validated_data, 'existing_estimates', [])
        groups = pop(validated_data, 'groups', [])
        flat_rate_groups = pop(validated_data, 'flat_rate_groups', [])
        instance = super().update(instance, validated_data)
        instance.groups.all().delete()
        instance.flat_rate_groups.all().delete()
        self.create_flat_rate_groups(flat_rate_groups, instance)
        self.create_groups(groups, instance)
        instance.existing_estimates.clear()
        instance.existing_estimates.add(*self.create_existing_estimate(existing_estimates))
        activity_log.delay(ContentType.objects.get_for_model(ChangeOrder).pk, instance.pk, 2,
                           ChangeOrderSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance


class FlatRateForInvoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = FlatRate
        fields = ('id', 'name', 'cost')
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'group': {'read_only': True}}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['unit'] = 'USD'
        data['invoice_overview'] = 0
        return data


class ChangeOrderForInvoice(serializers.ModelSerializer):
    class Meta:
        model = ChangeOrder
        fields = ('id', 'name')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['formula_groups'] = POFormulaForInvoiceSerializer(instance._get_formulas(), many=True).data
        data['flat_rate_groups'] = instance._get_flat_rate().values(
            'id', 'name', 'quantity', 'cost', 'charge', 'markup', 'unit'
        )
        data['estimate_templates'] = EstimateTemplateForInvoiceSerializer(instance.existing_estimates.all(), many=True).data
        return data
