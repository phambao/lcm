from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.serializers.base import SerializerMixin
from base.serializers.base import IDAndNameSerializer
from ..models import catalog, Catalog


class DataPointUnitSerializer(serializers.ModelSerializer):

    class Meta:
        model = catalog.DataPointUnit
        fields = ('id', 'name')
        extra_kwargs = {'name': {'required': False},
                        'id': {'required': False}}


class DataPointSerializer(serializers.ModelSerializer):
    unit = IDAndNameSerializer(required=False, allow_null=True)

    class Meta:
        model = catalog.DataPoint
        fields = ('id', 'value', 'unit', 'linked_description', 'is_linked')


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
            print(data_point)
            unit = data_point.pop('unit')
            catalog.DataPoint.objects.create(catalog=instance, **data_point, unit_id=unit.get('id'))
        return instance
    
    def update(self, instance, validated_data):
        data_points = validated_data.pop('data_points', [])
        parent = validated_data.pop('parent', None)
        if parent:
            validated_data['parents'] = [parent]
        instance = super().update(instance, validated_data)
        instance.data_points.all().delete()
        catalog.DataPoint.objects.bulk_create(
            [catalog.DataPoint(catalog=instance, unit_id=data_point.pop('unit').get('id'), **data_point) for data_point in data_points]
        )
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['parents']:
            data['parent'] = data['parents'][0]
        else:
            data['parent'] = None
        del data['parents']
        data['children'] = catalog.Catalog.objects.filter(parents__id=instance.pk).values_list('pk', flat=True)
        return data

    def validate(self, data):
        # Check sub category's name if it's exist
        records = catalog.Catalog.objects.filter(parents__id=data['parent'], name__exact=data['name'])
        records = records | catalog.Catalog.objects.filter(level=data['level'], name__exact=data['name'])
        if records.exists():
            raise ValidationError({'name': 'Name has been exist.'})
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

    def validate_parent(self, value):
        if self.is_param_exist('pk_catalog'):
            # Only one level in catalog has parent is null
            c = Catalog.objects.get(pk=self.get_params()['pk_catalog'])
            levels = c.all_levels.all()
            if levels and not value:
                raise ValidationError('parent is not null')
            if not levels and value:
                raise ValidationError('parent must null')
        if value:
            if catalog.CatalogLevel.objects.filter(parent=value).exists():
                raise ValidationError(f'Level has only one child. Level id: {value}')
        return value
