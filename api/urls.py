from django.contrib.auth import views as auth_views
from django.urls import path, include
from knox import views as knox_views

from api.views.auth import SignInAPI, SignUpAPI, MainUser, UserList, forgot_password, check_private_code, \
    reset_password, SignUpUserCompanyAPI, InternalUserListView, InternalUserDetailView, check_link, \
    check_private_code_create
from api.views.company_setting import setting_change_order, setting_invoice

urlpatterns = [
    # For authenticate
    path('check-link', check_link),
    path('register', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user/<int:pk>/', MainUser.as_view()),
    path('internal-user/', InternalUserListView.as_view()),
    path('internal-user/<int:pk>/', InternalUserDetailView.as_view()),
    path('users', UserList.as_view()),
    path('company/user/register', SignUpUserCompanyAPI.as_view()),
    path('company/setting/change-order/', setting_change_order),
    path('company/setting/invoice/', setting_invoice),

    # For password reset
    path('auth/', include([
        path('reset-password/', forgot_password, name='reset-password'),
        path('check-code/', check_private_code, name='check-private-code'),
        path('reset/', reset_password, name='reset-password'),
        path('check-code-create/', check_private_code_create, name='check-private-code-create'),
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
