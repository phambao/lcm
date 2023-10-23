from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework import serializers

from base.tasks import celery_send_mail
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
    class Meta:
        model = User
        fields = ('id', 'username', 'last_name', 'first_name', 'email', 'image', 'groups', 'is_active', 'is_admin_company',
                  'phone', 'is_staff', 'date_joined')
        read_only_fields = ['date_joined']

    def create(self, validated_data):
        validated_data['username'] = validated_data['email']
        validated_data['company'] = self.context['request'].user.company
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.username = instance.email
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['groups'] = instance.groups.all().values()
        data['auto_access'] = True
        data['role'] = ''
        role = instance.groups.all()
        if role:
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
        user.last_name = validated_data['last_name']
        user.first_name = validated_data['first_name']
        user.is_active = False
        user.create_code = code
        user.expire_code_register = timezone.now()
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
