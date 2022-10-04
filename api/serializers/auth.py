from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'last_name', 'first_name')


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}, 'email': {'required': True}}

    def validate(self, data):
        if not data['email']:
            raise serializers.ValidationError({'message': 'Email is not valid.'})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'message': 'Email has been exist.'})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(username=validated_data['email'],
                                        email=validated_data['email'],
                                        password=validated_data['password'])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError({'message': 'Login fail'})
