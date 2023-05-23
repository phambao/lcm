import re
from rest_framework import serializers

from api.models import DivisionCompany, CompanyBuilder
from ..models.config import Column, Search, Config, GridSetting
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

    class Meta:
        model = CompanyBuilder
        fields = ('id', 'logo', 'company_name', 'address', 'city', 'state', 'zip_code', 'tax', 'size',
                  'business_phone', 'fax', 'email', 'cell_phone', 'cell_mail', 'created_date', 'modified_date',
                  'user_create', 'user_update', 'currency')

    # def create(self, validated_data):
    #     request = self.context['request']
    #     user_create = user_update = request.user
    #
    #     company_create = Company.objects.create(
    #         user_create=user_create, user_update=user_update,
    #         **validated_data
    #     )
    #     return company_create
    #
    # def update(self, instance, data):
    #     company_update = Company.objects.filter(pk=instance.pk)
    #     company_update.update(**data)
    #     instance.refresh_from_db()
    #     return instance


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DivisionCompany
        fields = '__all__'