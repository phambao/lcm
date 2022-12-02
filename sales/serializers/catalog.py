from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.serializers.base import SerializerMixin
from ..models import catalog, Catalog


class DataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.DataPoint
        fields = ('value', 'unit', 'linked_description', 'is_linked')


class CatalogSerializer(serializers.ModelSerializer):
    data_points = DataPointSerializer(many=True, required=False)
    parent = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = catalog.Catalog
        fields = ('id', 'name', 'parents', 'parent', 'sequence', 'cost_table', 'icon', 'is_ancestor', 'level', 'data_points')
        extra_kwargs = {'icon': {'required': False,
                                 'allow_null': True}}

    def create(self, validated_data):
        data_points = validated_data.pop('data_points', [])
        parent = validated_data.pop('parent', None)
        if parent:
            validated_data['parents'] = [parent]
        instance = super().create(validated_data)
        for data_point in data_points:
            catalog.DataPoint.objects.create(catalog=instance, **data_point)
        return instance
    
    def update(self, instance, validated_data):
        data_points = validated_data.pop('data_points', [])
        parent = validated_data.pop('parent', None)
        if parent:
            validated_data['parents'] = [parent]
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


class CatalogLevelModelSerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = catalog.CatalogLevel
        fields = ('id', 'name', 'parent', 'catalog')
        extra_kwargs = {'catalog': {'read_only': True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.is_param_exist('pk_catalog'):
            c = catalog.Catalog.objects.get(pk=self.get_params()['pk_catalog'])
            ordered_levels = c.get_ordered_levels()
            data['index'] = ordered_levels.index(instance)
        return data

    def create(self, validated_data):
        if self.is_param_exist('pk_catalog'):
            # Only one level in catalog has parent is null
            c = Catalog.objects.get(pk=self.get_params()['pk_catalog'])
            levels = c.all_levels.all()
            if levels and not validated_data.get('parent'):
                raise ValidationError({'parent': 'parent not null'})
        return super().create(validated_data)
