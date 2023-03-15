import uuid

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
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


# class ImageUserSerializer(serializers.ModelSerializer):
#     image = serializers.CharField(required=False)
#
#     class Meta:
#         model = User
#         fields = ('id', 'image')
#
#     def update(self, instance, data):
#         data_user = User.objects.filter(pk=instance.pk)
#         data_user.update(**data)
#
#         instance.refresh_from_db()
#         return instance
