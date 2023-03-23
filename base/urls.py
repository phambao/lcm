from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from base.views import country_state_city, base

# Define path for Base App ------------------------------------------------------
url_base = [
    path('location/',
         include([
             path('countries/', country_state_city.CountryList.as_view()),
             path('mcountries/', country_state_city.CountryV2List.as_view()),
             path('countries/<int:pk_country>/states/',
                  country_state_city.CountryStateList.as_view()),
             path('countries/<int:pk_country>/states/<int:pk_state>/cities/',
                  country_state_city.CountryStateCityList.as_view()),
             path('zipcodes/', country_state_city.Zipcode.as_view()),
         ])
         ),
    path('content-type/', base.ContentTypeList.as_view()),
    path('search/', base.SearchLeadGenericView.as_view()),
    path('search/<int:pk>/', base.SearchLeadDetailGenericView.as_view()),
    path('column/', base.ColumnLeadGenericView.as_view()),
    path('column/<int:pk>/', base.ColumnLeadDetailGenericView.as_view()),
    path('column/<int:pk>/active/', base.active_column),
    path('grid-setting/', base.GridSettingListView.as_view()),
    path('grid-setting/<int:pk>/', base.GridSettingDetailGenericView.as_view()),
    path('config/<str:model>/', base.config_view),
    path('logs/', base.ActivityLogList.as_view()),
    path('logs/<int:pk>/', base.ActivityLogDetail.as_view()),
    path('company/', base.CompanyListView.as_view()),
    path('company/<int:pk>/', base.CompanyDetailGenericView.as_view()),
    path('company/division/', base.DivisionListView.as_view()),
    path('company/division/<int:pk>/', base.DivisionDetailGenericView.as_view()),

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
