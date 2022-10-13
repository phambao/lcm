from django.urls import path
from api.views.auth import SignInAPI, SignUpAPI, MainUser, UserList
from knox import views as knox_views

from api.views.upload_file import FileUploadView
from sales.views import lead_list, catalog
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    # For authenticate
    path('register', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path(r'logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user', MainUser.as_view()),
    path('users', UserList.as_view()),

    # For sales
    path('leads/', lead_list.LeadDetailsViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('leads/uploads', FileUploadView.as_view()),
    path('leads/<int:pk>/', lead_list.LeadDetailViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
    path('leads-params/', lead_list.LeadDetailList.as_view()),
    # Activities
    path('leads/<int:pk_lead>/activities/', lead_list.LeadActivitiesViewSet.as_view()),
    path('leads/<int:pk_lead>/activities/<int:pk>/', lead_list.LeadActivitiesDetailViewSet.as_view()),
    # Contacts
    path('contacts/', lead_list.ContactsViewSet.as_view()),
    path('contacts/<int:pk>/', lead_list.ContactsDetailViewSet.as_view()),
    path('contacts/<int:pk_contact>/phone_contacts/', lead_list.PhoneOfContactsViewSet.as_view()),
    path('contacts/<int:pk_contact>/phone_contacts/<int:pk>/', lead_list.PhoneOfContactsDetailViewSet.as_view()),
    
    
    path('catalog/materials/', catalog.MaterialList.as_view()),
    path('catalog/materials/<int:pk>/', catalog.MaterialDetail.as_view()),
]
