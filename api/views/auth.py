from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django_filters.rest_framework import DjangoFilterBackend
from knox.models import AuthToken
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from ..serializers.auth import UserSerializer, RegisterSerializer, LoginSerializer, User, \
    ForgotPasswordSerializer, CheckCodeSerializer, ChangePasswordSerializer


class SignUpAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = AuthToken.objects.create(user)
        return Response({
            "users": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token[1],
            "message": "Register successfully"
        })


class SignInAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1],
            "message": "Login successfully"
        })


class MainUser(generics.RetrieveAPIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['username', 'email']


@api_view(['POST'])
def forgot_password(request):
    """
    Payload: {"email": string}
    """
    email = request.data.get('email')
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = get_user_model().objects.get(email=email)
        user.code = get_random_string(length=6, allowed_chars='1234567890')
        user.save()
        send_mail('Change password', user.code, settings.EMAIL_HOST_USER, [email], fail_silently=False)
    except get_user_model().DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"email": "Email is not in the system"})
    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
def check_private_code(request):
    """
    Payload: {"email": string, "code": int}
    """
    email = request.data.get('email')
    code = request.data.get('code')
    serializer = CheckCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = get_user_model().objects.get(email=email, code=code)
        user.token = default_token_generator.make_token(user)
        user.save()
    except get_user_model().DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"email": "Email or code is not valid"})
    return Response(status=status.HTTP_200_OK, data={'token': user.token})


@api_view(['POST'])
def reset_password(request):
    """
    Payload: {"email": string, "token": string, "password1": string, "password2": string}
    """
    email = request.data.get('email')
    token = request.data.get('token')
    password1 = request.data.get('password1')
    password2 = request.data.get('password2')

    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = get_user_model().objects.get(email=email, token=token)
        if default_token_generator.check_token(user, token):
            user.set_password(password2)
            user.token = ''
            user.code = None
            user.save()
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"token": "token is invalid"})
    except get_user_model().DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"email": "Email or code is not valid"})
    return Response(status=status.HTTP_200_OK)
