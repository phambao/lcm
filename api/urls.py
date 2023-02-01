from django.contrib.auth import views as auth_views
from django.urls import path, include
from knox import views as knox_views

from api.views.auth import SignInAPI, SignUpAPI, MainUser, UserList, forgot_password, check_private_code, reset_password

urlpatterns = [
    # For authenticate
    path('register', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user', MainUser.as_view()),
    path('users', UserList.as_view()),

    # For password reset
    path('auth/', include([
        path('reset-password/', forgot_password, name='reset-password'),
        path('check-code/', check_private_code, name='check-private-code'),
        path('reset/', reset_password, name='reset-password')
    ])),

    path('reset_password/', auth_views.PasswordResetView.as_view(), name='reset_password'),
    path('reset_password_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # For base
    path('base/', include('base.urls')),
    # For sales
    path('sales/', include('sales.urls')),
]
