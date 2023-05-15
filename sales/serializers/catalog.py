from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.serializers.base import SerializerMixin
from base.serializers.base import IDAndNameSerializer
from base.constants import true, null, false
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
    data_points = serializers.CharField(required=False, max_length=256, allow_blank=True)
    parent = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = catalog.Catalog
        fields = ('id', 'name', 'parents', 'parent', 'sequence', 'cost_table', 'icon',
                  'is_ancestor', 'level', 'data_points', 'level_index', 'c_table',
                  'created_date', 'modified_date', 'user_create', 'user_update'
                  )
        extra_kwargs = {'icon': {'required': False,
                                 'allow_null': True},
                        'created_date': {'read_only': True},
                        'modified_date': {'read_only': True},
                        'user_create': {'read_only': True},
                        'user_update': {'read_only': True}}

    def create(self, validated_data):
        data_points = validated_data.pop('data_points', '[]')
        if data_points:
            data_points = eval(data_points)
        else:
            data_points = []
        parent = validated_data.pop('parent', None)

        if parent:
            if catalog.Catalog.objects.filter(parents__id=parent, name__exact=validated_data['name']).exists():
                raise ValidationError({'name': 'Name has been exist.'})
            validated_data['parents'] = [parent]
            data_catalog_parent = catalog.Catalog.objects.filter(id=parent).first()
            validated_data['c_table'] = data_catalog_parent.c_table
            data_catalog_parent.c_table = dict()
            data_catalog_parent.save()
        instance = super().create(validated_data)
        instance.user_create = self.context['request'].user
        instance.created_date = timezone.now()
        instance.save()
        for data_point in data_points:
            unit = data_point.pop('unit')
            catalog.DataPoint.objects.create(catalog=instance, **data_point, unit_id=unit.get('id'))
        return instance

    def update(self, instance, validated_data):
        data_points = validated_data.pop('data_points', '[]')
        if data_points:
            data_points = eval(data_points)
        else:
            data_points = []
        parent = validated_data.pop('parent', None)
        if parent:
            validated_data['parents'] = [parent]
        instance = super().update(instance, validated_data)
        instance.data_points.all().delete()
        instance.user_update = self.context['request'].user
        instance.modified_date = timezone.now()
        instance.save()
        catalog.DataPoint.objects.bulk_create(
            [catalog.DataPoint(catalog=instance, unit_id=data_point.pop('unit').get('id'), **data_point) for data_point
             in data_points]
        )
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['parents']:
            data['parent'] = data['parents'][0]
        else:
            data['parent'] = None
        del data['parents']
        data['data_points'] = DataPointSerializer(instance.data_points.all(), many=True).data
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

    def validate(self, attrs):
        c = Catalog.objects.get(pk=self.get_params()['pk_catalog'])
        num_levels = c.all_levels.all().count()
        parent = attrs.get('parent')

        # update
        if self.is_param_exist('pk'):
            list_levels = c.get_ordered_levels()
            if list_levels[0].id == self.get_params()['pk'] and parent:
                raise ValidationError('parent must null')
            if list_levels[0].id != self.get_params()['pk'] and not parent:
                raise ValidationError('parent must have a value')

        # create
        if not self.is_param_exist('pk'):
            if num_levels == 0 and parent:
                raise ValidationError('parent must null')
            if num_levels > 0 and not parent:
                raise ValidationError('parent must have a value')
        return attrs


class CatalogEstimateSerializer(serializers.ModelSerializer):
    level = serializers.PrimaryKeyRelatedField(read_only=True, queryset=None)
    class Meta:
        model = Catalog
        fields = ('id', 'name', 'level', 'level_index')
        extra_kwargs = {'id': {'read_only': False, 'required': False}}
