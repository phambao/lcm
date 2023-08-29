from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from base.models.config import FileBuilder365


class IDAndNameSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ('id', 'app_label', 'model')


class FileBuilder365ResSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileBuilder365
        fields = '__all__'


class FileBuilder365ReqSerializer(serializers.Serializer):
    file = serializers.FileField()


class DeleteDataSerializer(serializers.Serializer):
    name = serializers.CharField()
    created_date = serializers.DateTimeField()
