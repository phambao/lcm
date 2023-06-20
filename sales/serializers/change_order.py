from rest_framework import serializers

from base.utils import pop
from sales.models import ChangeOrder
from sales.serializers.estimate import EstimateTemplateSerializer


class ChangeOrderSerializer(serializers.ModelSerializer):
    existing_estimates = EstimateTemplateSerializer('change_order', many=True, required=False, allow_null=True)
    add_new_estimates = EstimateTemplateSerializer('new_change_order', many=True, required=False, allow_null=True)

    class Meta:
        model = ChangeOrder
        fields = ('id', 'name', 'proposal', 'existing_estimates', 'add_new_estimates')

    def create_existing_estimate(self, existing_estimates):
        objs = []
        for estimate in existing_estimates:
            serializer = EstimateTemplateSerializer(data=estimate, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False)
            objs.append(obj)
        return objs

    def create(self, validated_data):
        existing_estimates = pop(validated_data, 'existing_estimates', [])
        add_new_estimates = pop(validated_data, 'add_new_estimates', [])
        objs = self.create_existing_estimate(existing_estimates)
        add_new_estimates = self.create_existing_estimate(add_new_estimates)
        instance = super().create(validated_data)
        instance.existing_estimates.add(*objs)
        instance.add_new_estimates.add(*add_new_estimates)
        return instance

    def update(self, instance, validated_data):
        existing_estimates = pop(validated_data, 'existing_estimates', [])
        add_new_estimates = pop(validated_data, 'add_new_estimates', [])
        instance = super().update(instance, validated_data)
        instance.existing_estimates.all().delete()
        instance.add_new_estimates.all().delete()
        instance.existing_estimates.add(*self.create_existing_estimate(existing_estimates))
        instance.add_new_estimates.add(*self.create_existing_estimate(add_new_estimates))
        return instance
