from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from base.utils import pop, extra_kwargs_for_base_model
from base.tasks import activity_log
from sales.models import ChangeOrder, GroupEstimate, FlatRate, GroupFlatRate
from sales.serializers.estimate import EstimateTemplateSerializer


class GroupEstimateSerializer(serializers.ModelSerializer):
    estimate_templates = EstimateTemplateSerializer('change_order_group', many=True, required=False, allow_null=True)
    class Meta:
        model = GroupEstimate
        fields = '__all__'
        extra_kwargs = {**extra_kwargs_for_base_model(), **{'change_order': {'read_only': True}}}

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


class ChangeOrderSerializer(serializers.ModelSerializer):
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        proposal_writing = instance.proposal_writing
        data['proposal_name'] = proposal_writing.name if proposal_writing else None
        return data
