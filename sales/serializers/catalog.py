from rest_framework import serializers

from ..models import catalog


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.Catalog
        fields = ('id', 'name', 'parents', 'sequence', 'cost_table', 'icon', 'is_ancestor')
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
