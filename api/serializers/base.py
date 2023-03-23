from rest_framework import serializers

from api.models import ActivityLog
from api.serializers.auth import UserSerializer


class SerializerMixin:

    def get_params(self):
        return self.context['request'].__dict__[
            'parser_context']['kwargs']

    def is_param_exist(self, param):
        return param in self.get_params().keys()


class ActivityLogSerializer(serializers.ModelSerializer):
    user_create = UserSerializer()

    class Meta:
        model = ActivityLog
        fields = ('id', 'action', 'last_state', 'next_state', 'content_type', 'object_id', 'user_create', 'created_date')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['action'] = {'id': data['action'], 'name': instance.get_action_name()}
        return data
