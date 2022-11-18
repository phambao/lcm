from django.db import IntegrityError
from rest_framework import serializers
from ..models.config import Column, Search, Config


class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ('id', 'params', 'content_type', 'user')


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
    column = CustomColumnSerializer()
    search = CustomSearchSerializer()

    class Meta:
        model = Config
        fields = ('id', 'search', 'column', 'content_type')

    def create(self, validated_data):
        user = self.context['request'].user
        content_type = validated_data.get('content_type')
        column_data = validated_data.get('column', {})
        column = Column.objects.create(user=user, content_type=content_type,
                                       params=column_data.get('params', []))
        try:
            config = Config.objects.create(user=user, search_id=validated_data.get('search', {}).get('id'),
                                           column=column, content_type=content_type)
        except IntegrityError:
            raise serializers.ValidationError({'detail': 'Duplicate unique constraint'})
        return config

    def update(self, instance, validated_data):
        instance.search_id = validated_data['search'].get('id')
        instance.column.params = validated_data['column'].get('params')
        instance.save()
        return instance
