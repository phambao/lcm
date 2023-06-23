from rest_framework import serializers

from base.utils import pop, extra_kwargs_for_base_model
from sales.models import ChangeOrder, GroupEstimate
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


class ChangeOrderSerializer(serializers.ModelSerializer):
    existing_estimates = EstimateTemplateSerializer('change_order', many=True, required=False, allow_null=True)
    groups = GroupEstimateSerializer('change_order', many=True, required=False, allow_null=True)

    class Meta:
        model = ChangeOrder
        fields = ('id', 'name', 'proposal', 'existing_estimates', 'groups')

    def create_existing_estimate(self, existing_estimates):
        objs = []
        for estimate in existing_estimates:
            serializer = EstimateTemplateSerializer(data=estimate, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False)
            objs.append(obj)
        return objs

    def create_groups(self, groups, instance):
        for group in groups:
            obj = GroupEstimateSerializer(data=group, context=self.context)
            obj.is_valid(raise_exception=True)
            obj.save(change_order=instance)

    def create(self, validated_data):
        existing_estimates = pop(validated_data, 'existing_estimates', [])
        groups = pop(validated_data, 'groups', [])
        objs = self.create_existing_estimate(existing_estimates)
        instance = super().create(validated_data)
        self.create_groups(groups, instance)
        instance.existing_estimates.add(*objs)
        return instance

    def update(self, instance, validated_data):
        existing_estimates = pop(validated_data, 'existing_estimates', [])
        groups = pop(validated_data, 'groups', [])
        instance = super().update(instance, validated_data)
        instance.groups.all().delete()
        self.create_groups(groups, instance)
        instance.existing_estimates.all().delete()
        instance.existing_estimates.add(*self.create_existing_estimate(existing_estimates))
        return instance
