from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from base.utils import pop
from api.models import GroupCompany


class GroupSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions', 'description')

    def create(self, validated_data):
        description = pop(validated_data, 'description', '')
        company = self.context['request'].user.company
        instance = super().create(validated_data)
        GroupCompany.objects.create(company=company, group=instance, description=description)
        return instance

    def update(self, instance, validated_data):
        description = pop(validated_data, 'description', '')
        group = instance.group
        group.description = description
        group.save(update_fields=['description'])
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = instance.group.description
        return data


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'content_type')
        read_only_fields = ('content_type',)
