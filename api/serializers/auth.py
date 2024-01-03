from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from base.tasks import celery_send_mail
from base.utils import pop
from sales.models import (Catalog, ChangeOrder, EstimateTemplate, Invoice, LeadDetail,
                              ScheduleEvent, ToDo, DailyLog, ProposalWriting)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'last_name', 'first_name', 'image', 'company', 'user_permissions', 'groups', 'is_active')

    def to_representation(self, instance):
        data = super(UserSerializer, self).to_representation(instance)
        data['name'] = data['first_name'] + ' ' + data['last_name']
        return data


class InternalUserSerializer(serializers.ModelSerializer):
    group = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'last_name', 'first_name', 'email', 'image', 'group', 'is_active', 'is_admin_company',
                  'phone', 'is_staff', 'date_joined', 'service_provider')
        read_only_fields = ['date_joined', 'username']

    def create(self, validated_data):
        validated_data['username'] = validated_data['email']
        validated_data['company'] = self.context['request'].user.company
        group = pop(validated_data, 'group', None)
        instance = super().create(validated_data)
        if group:
            instance.groups.add(group)
        return instance

    def update(self, instance, validated_data):
        instance.groups.clear()
        group = pop(validated_data, 'group', None)
        instance = super().update(instance, validated_data)
        if group:
            instance.groups.add(group)
        instance.username = instance.email
        instance.save()
        return instance

    def validate_group(self, value):
        if value:
            try:
                value = Group.objects.get(id=value)
            except Group.DoesNotExist:
                raise serializers.ValidationError('The choice is not exist')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['group'] = None
        data['auto_access'] = True
        data['role'] = ''
        role = instance.groups.all()
        if role:
            data['group'] = instance.groups.all().first().pk
            data['role'] = role.first().name
        return data


class UserCustomSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['name'] = data['first_name'] + ' ' + data['last_name']
        return data


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'company', 'stripe_customer')
        extra_kwargs = {'password': {'write_only': True}, 'email': {'required': True}}

    def validate(self, data):
        if not data['email']:
            raise serializers.ValidationError({'message': 'Email is not valid.'})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'message': 'Email has been exist.'})
        return data

    def create(self, validated_data):
        code = get_random_string(length=6, allowed_chars='1234567890')
        user = User.objects.create_user(username=validated_data['username'],
                                        email=validated_data['email'],
                                        password=validated_data['password'],
                                        is_admin_company=True
                                        )
        stripe_customer = pop(validated_data, 'stripe_customer', '')
        user.last_name = validated_data['last_name']
        user.first_name = validated_data['first_name']
        user.is_active = False
        user.create_code = code
        user.expire_code_register = timezone.now()
        user.stripe_customer = stripe_customer
        user.save()
        content = render_to_string('auth/create-user-otp.html', {'username': user.get_username(),
                                                                 'otp': user.create_code})
        celery_send_mail.delay(f'Create account for {user.get_username()}',
                               content, settings.EMAIL_HOST_USER, [validated_data['email']], False)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError({'message': 'Login fail'})


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class CheckCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=6, required=True)


class ChangePasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    token = serializers.CharField(max_length=128, required=True)
    password1 = serializers.CharField(max_length=64, required=True)
    password2 = serializers.CharField(max_length=64, required=True)

    def validate(self, attrs):
        if attrs['password1'] != attrs['password2']:
            return serializers.ValidationError('password is not match!')
        return attrs


class CustomPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['action'] = self.get_action(instance)
        data['type'] = self.get_name(instance)
        data['relations'] = []
        if not data['action']:
            data['type'] = instance.name
        else:
            data['relations'] = self.get_relation(instance.codename)
        return data

    def get_action(self, instance):
        list_action = ['view', 'add', 'delete', 'change']
        code_name = instance.codename
        action = code_name.split('_')[0]
        if action in list_action:
            return action.title()
        return None

    def get_name(self, instance):
        models = [Catalog, ChangeOrder, EstimateTemplate, Invoice, ScheduleEvent, ToDo, DailyLog, ProposalWriting, LeadDetail]
        names = ['Catalog', 'Change Order', 'Estimate Template', 'Invoice', 'Schedule Event',
                 'To Do', 'Daily Log', 'Proposal Writing', 'Leads']
        name = None
        for i, model in enumerate(models):
            name = self._get_name(instance, model, names[i])
            if name:
                return name

        return None

    def _get_name(self, instance, model, name):
        content_type = ContentType.objects.get_for_model(model)
        if instance.content_type == content_type:
            return name
        return ''

    def get_relation(self, code_name):
        suffix = code_name.split('_')[-1]
        code_names = ['add_' + suffix, 'change_' + suffix, 'delete_' + suffix, 'view_' + suffix]
        permissions = Permission.objects.filter(codename__in=code_names)
        return permissions.values_list('id', flat=True)
