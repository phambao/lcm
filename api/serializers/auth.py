from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'last_name', 'first_name', 'image', 'company', 'user_permissions', 'groups')

    def to_representation(self, instance):
        data = super(UserSerializer, self).to_representation(instance)
        data['name'] = data['first_name'] + ' ' + data['last_name']
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
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name', 'company')
        extra_kwargs = {'password': {'write_only': True}, 'email': {'required': True}}

    def validate(self, data):
        if not data['email']:
            raise serializers.ValidationError({'message': 'Email is not valid.'})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'message': 'Email has been exist.'})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(username=validated_data['username'],
                                        email=validated_data['email'],
                                        password=validated_data['password'])
        user.last_name = validated_data['last_name']
        user.first_name = validated_data['first_name']
        user.save()
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
