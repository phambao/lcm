from datetime import timedelta, datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django_filters.rest_framework import DjangoFilterBackend
from knox.models import AuthToken
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
import jwt

from base.models.payment import PaymentHistoryStripe
from base.tasks import celery_send_mail
from base.views.base import CompanyFilterMixin
from ..models import CompanyBuilder
from ..serializers.auth import UserSerializer, RegisterSerializer, LoginSerializer, User, \
    ForgotPasswordSerializer, CheckCodeSerializer, ChangePasswordSerializer, InternalUserSerializer


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


class SignUpUserCompanyAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.create_user(username=request.data['username'],
                                        email=request.data['email'],
                                        password=request.data['password'])
        data_company = CompanyBuilder.objects.get(pk=request.data['company'])
        user.last_name = request.data['last_name']
        user.first_name = request.data['first_name']
        user.company = data_company
        user.save()
        # user = serializer.save()
        token = AuthToken.objects.create(user)
        return Response({
            "users": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token[1],
            "message": "Register successfully"
        })


class SignInAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1],
            "message": "Login successfully"
        })


class MainUser(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserList(CompanyFilterMixin, generics.ListAPIView):
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
        content = render_to_string('auth/reset-password-otp.html', {'username': user.get_username(),
                                                                    'otp': user.code})
        celery_send_mail.delay(f'Reset Your Password for {user.get_username()}',
                               content, settings.EMAIL_HOST_USER, [email], False)
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
def check_private_code_create(request):
    """
    Payload: {"email": string, "code": int}
    """
    email = request.data.get('email')
    code = request.data.get('code')
    serializer = CheckCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    time_delta = timedelta(minutes=1, seconds=30)
    try:
        user = get_user_model().objects.get(email=email, create_code=code)
        if user.expires + time_delta < datetime.now(timezone.utc):
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"code": "code is not valid"})
        user.is_active = True
        user.token = default_token_generator.make_token(user)
        user.save()
    except get_user_model().DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"email": "Email or code is not valid"})
    data = UserSerializer(user, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data={'user': data})


@api_view(['POST'])
def resend_mail(request):
    email = request.data.get('email')
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code = get_random_string(length=6, allowed_chars='1234567890')
    try:
        user = get_user_model().objects.get(email=email)
        user.create_code = code
        user.expires = datetime.now()
        user.save()
        content = render_to_string('auth/create-user-otp.html', {'username': user.get_username(),
                                                                 'otp': user.create_code})
        celery_send_mail.delay(f'Create account for {user.get_username()}',
                               content, settings.EMAIL_HOST_USER, [email], False)
    except get_user_model().DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"email": "Email is not valid"})
    data = UserSerializer(user, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data={'user': data})


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


class InternalUserListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = InternalUserSerializer
    permission_classes = [permissions.IsAuthenticated]


class InternalUserDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = InternalUserSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['POST'])
def check_link(request):
    link = request.data.get('link')
    try:
        decoded_payload = jwt.decode(link, settings.SECRET_KEY, algorithms=['HS256'])
        data_check = PaymentHistoryStripe.objects.filter(
                subscription_id=decoded_payload['sub'],
                customer_stripe_id=decoded_payload['customer']
            )
        data_company = CompanyBuilder.objects.get(customer_stripe=decoded_payload['customer'])
        if not data_check:
            Response(status=status.HTTP_404_NOT_FOUND, data={"data": 'link error'})
    except jwt.ExpiredSignatureError:
        return Response(status=status.HTTP_404_NOT_FOUND, data={"data": 'link error'})
    except jwt.DecodeError:
        return Response(status=status.HTTP_404_NOT_FOUND, data={"data": 'link error'})
    except jwt.InvalidTokenError:
        return Response(status=status.HTTP_404_NOT_FOUND, data={"data": 'link error'})

    return Response(status=status.HTTP_200_OK, data={"company": data_company.id,
                                                     "stripe_customer": decoded_payload['customer']})
