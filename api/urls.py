from django.urls import path, include
from knox import views as knox_views

from api.views.auth import SignInAPI, SignUpAPI, MainUser, UserList
from api.views.upload_file import FileUploadView
from sales.views import lead_list, catalog
from sales.urls import url_contact_types, url_contacts

urlpatterns = [
    # For authenticate
    path('register', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user', MainUser.as_view()),
    path('users', UserList.as_view()),

    # For base
    path('', include('base.urls')),
    # For sales
    path('', include('sales.urls')),
]
