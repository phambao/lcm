from django.urls import path
from api.views.auth import SignInAPI, SignUpAPI, MainUser
from knox import views as knox_views
from sales.views import lead_list
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    # For authenticate
    path('register', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path(r'logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user', MainUser.as_view()),

    # For sales
    path('leads/', lead_list.LeadDetailList.as_view()),
    path('leads/<int:pk>/', lead_list.LeadDetailRUD.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
