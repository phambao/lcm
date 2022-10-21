from django.urls import path

from base.views import country_state_city

urlpatterns = [
    path('countries/', country_state_city.CountryList.as_view()),
    path('countries/<int:pk_country>/states/', country_state_city.CountryStateList.as_view()),
    path('countries/<int:pk_country>/states/<int:pk_state>/cities/', country_state_city.CountryStateCityList.as_view()),
]
