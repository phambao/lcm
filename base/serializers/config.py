from django.db import IntegrityError
from rest_framework import serializers
from ..models.config import Column, Search, Config


class ColumnSerializer(serializers.ModelSerializer):
    model = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Column
        fields = ('id', 'name', 'params', 'content_type', 'user', 'model')


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
