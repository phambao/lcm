from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response

from ..models import catalog


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.Material
        fields = ('id', 'type', 'name', 'parents', 'sequence', 'cost_table', 'icon')
        extra_kwargs = {'icon': {'required': False,
                                 'allow_null': True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.icon:
            data['icon'] = r'(?<=/media/).+?(?=/)'.replace(r'(?<=/media/).+?(?=/)', instance.icon.url)
        return data


class CostTableModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.CostTable
        fields = ('id', 'name', 'data')
