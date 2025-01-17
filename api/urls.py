from django.contrib.auth import views as auth_views
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from api.views.auth import SignUpAPI, MainUser, UserList, forgot_password, check_private_code, profile, \
    reset_credential, \
    reset_password, SignUpUserCompanyAPI, InternalUserListView, InternalUserDetailView, check_link, \
    check_private_code_create, resend_mail, CustomTokenRefreshView
from api.views.company_setting import setting_change_order, setting_invoice
from sales.views.proposal import proposal_setting_field

urlpatterns = [
    # For authenticate
    path('check-link', check_link),
    path('register', SignUpAPI.as_view()),
    path('login', TokenObtainPairView.as_view()),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    # path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user/<int:pk>/', MainUser.as_view()),
    path('internal-user/', InternalUserListView.as_view()),
    path('internal-user/<int:pk>/reset-credential/', reset_credential),
    path('internal-user/<int:pk>/', InternalUserDetailView.as_view()),
    path('profile/', profile),
    path('users', UserList.as_view()),
    path('company/user/register', SignUpUserCompanyAPI.as_view()),
    path('company/setting/change-order/', setting_change_order),
    path('company/setting/invoice/', setting_invoice),
    path('company/setting/proposal/', proposal_setting_field),

    # For password reset
    path('auth/', include([
        path('reset-password/', forgot_password, name='reset-password'),
        path('check-code/', check_private_code, name='check-private-code'),
        path('reset/', reset_password, name='reset-password'),
        path('check-code-create/', check_private_code_create, name='check-private-code-create'),
        path('resend-mail/', resend_mail),
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
