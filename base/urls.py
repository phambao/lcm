from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from base.views import country_state_city

# Define path for Base App ------------------------------------------------------
url_base = [
    path('location/',
         include([
             path('countries/', country_state_city.CountryList.as_view()),
             path('countries/<int:pk_country>/states/',
                  country_state_city.CountryStateList.as_view()),
             path('countries/<int:pk_country>/states/<int:pk_state>/cities/',
                  country_state_city.CountryStateCityList.as_view()),
         ])
         ),
]

# Create schema view for Swagger ------------------------------------------------
schema_view_base = get_schema_view(
    openapi.Info(
        title='API FOR BASE APP',
        default_version='v1',
    ),
    patterns=[
        path('api/base/', include(url_base))
    ],
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('', include(url_base)),
    path('', schema_view_base.with_ui(
        'swagger', cache_timeout=0), name='schema-swagger-ui'),
]
