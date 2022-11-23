from rest_framework import serializers

from ..models import catalog


class DataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.DataPoint
        fields = ('name', 'value', 'unit', 'linked_description', 'is_linked')


class CatalogSerializer(serializers.ModelSerializer):
    data_points = DataPointSerializer(many=True, required=False)

    class Meta:
        model = catalog.Catalog
        fields = ('id', 'name', 'parents', 'sequence', 'cost_table', 'icon', 'is_ancestor', 'level', 'data_points')
        extra_kwargs = {'icon': {'required': False,
                                 'allow_null': True}}

    def create(self, validated_data):
        data_points = validated_data.pop('data_points', [])
        instance = super().create(validated_data)
        for data_point in data_points:
            catalog.DataPoint.objects.create(catalog=instance, **data_point)
        return instance
    
    def update(self, instance, validated_data):
        data_points = validated_data.pop('data_points', [])
        instance = super().update(instance, validated_data)
        for data_point in data_points:
            catalog.DataPoint.objects.update(catalog=instance, **data_point)
        return instance
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.icon:
            data['icon'] = r'(?<=/media/).+?(?=/)'.replace(r'(?<=/media/).+?(?=/)', instance.icon.url)
        if data['parents']:
            data['parent'] = data['parents'][0]
        else:
            data['parent'] = None
        del data['parents']
        data['children'] = catalog.Catalog.objects.filter(parents__id=instance.pk).values_list('pk', flat=True)
        return data


class CostTableModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.CostTable
        fields = ('id', 'name', 'data')


class CatalogLevelModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.CatalogLevel
        fields = ('id', 'name', 'parent', 'catalog')
        extra_kwargs = {'catalog': {'read_only': True}}
