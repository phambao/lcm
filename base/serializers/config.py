import re
from rest_framework import serializers

from ..models.config import Column, Search, Config, GridSetting, Company, Division
from ..utils import pop

from base.serializers import base


class ColumnSerializer(serializers.ModelSerializer):
    model = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Column
        fields = ('id', 'name', 'params', 'content_type', 'user', 'model', 'is_public',
                  'hidden_params', 'is_active')
        extra_kwargs = {'is_active': {'read_only': True}}


class SearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Search
        fields = ('id', 'name', 'params', 'content_type', 'user')


class CustomColumnSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    params = serializers.ListField(allow_null=True)


class CustomSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    params = serializers.CharField(allow_null=True, allow_blank=True)


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Config
        fields = ('id', 'settings', 'content_type')


class GridSettingSerializer(serializers.ModelSerializer):
    model = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = GridSetting
        fields = ('id', 'name', 'params', 'content_type', 'user', 'model', 'is_public', 'hidden_params')


class CompanySerializer(serializers.ModelSerializer):
    division = base.IDAndNameSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = Company
        fields = ('id', 'logo', 'company_name', 'address', 'city', 'state', 'zip_code', 'division', 'tax',
                  'business_phone', 'cell_phone', 'fax', 'email', 'cell_mail', 'created_date', 'modified_date')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        division = pop(validated_data, 'division', [])

        company_create = Company.objects.create(
            user_create=user_create, user_update=user_update,
            **validated_data
        )

        division_objects = Division.objects.filter(pk__in=[data['id'] for data in division])
        company_create.division.add(*division_objects)

        return company_create

    def update(self, instance, data):
        division = pop(data, 'division', [])
        company_update = Company.objects.filter(pk=instance.pk)
        company_update.update(**data)
        company_update = company_update.first()

        division_objects = Division.objects.filter(pk__in=[data['id'] for data in division])
        company_update.division.clear()
        company_update.division.add(*division_objects)

        instance.refresh_from_db()
        return instance


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = '__all__'