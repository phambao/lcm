import uuid

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from base.models.config import FileBuilder365, ImageUser


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


class ImageUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageUser
        fields = ('id', 'image')

    def validate(self, validated_data):
        pk_user = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_user']
        if not get_user_model().objects.filter(pk=pk_user).exists():
            raise serializers.ValidationError('User not found')
        return validated_data

    def create(self, validated_data):
        pk_user = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_user']

        file = self.context['request'].FILES.get('image')
        file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
        content_file = ContentFile(file.read(), name=file_name)
        ImageUser.objects.filter(user=pk_user).delete()
        photo = ImageUser.objects.create(
            image=content_file,
            user_id=pk_user
        )
        return photo


