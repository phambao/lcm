from rest_framework import serializers


class ContentTypeSerializerMixin(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = instance.get_content_type().pk
        return data
