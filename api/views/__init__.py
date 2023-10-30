from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)
from ..serializers import CustomObtainPairSerializer


TokenObtainPairView.serializer_class = CustomObtainPairSerializer