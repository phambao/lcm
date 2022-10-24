from django.urls import path, include
from knox import views as knox_views

from api.views.auth import SignInAPI, SignUpAPI, MainUser, UserList
from api.views.upload_file import FileUploadView
from sales.views import lead_list, catalog

urlpatterns = [
    # For authenticate
    path('register', SignUpAPI.as_view()),
    path('login', SignInAPI.as_view()),
    path('logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    path('user', MainUser.as_view()),
    path('users', UserList.as_view()),

    # For sales
    path('leads/', lead_list.LeadDetailList.as_view()),
    path('leads/uploads', FileUploadView.as_view()),
    path('leads/<int:pk>/', lead_list.LeadDetailGeneric.as_view()),
    path('leads-params/', lead_list.LeadDetailList.as_view()),
    path('leads-params/<int:pk>/', lead_list.LeadDetailGeneric.as_view()),
    # Activities
    path('leads/<int:pk_lead>/activities/', lead_list.LeadActivitiesViewSet.as_view()),
    path('leads/<int:pk_lead>/activities/delete', lead_list.delete_activities),
    path('leads/<int:pk_lead>/activities/<int:pk>/', lead_list.LeadActivitiesDetailViewSet.as_view()),
    # Contacts
    path('leads/<int:pk_lead>/contacts/', lead_list.LeadContactsViewSet.as_view()),
    path('leads/<int:pk_lead>/contacts/<int:pk>/', lead_list.LeadContactDetailsViewSet.as_view()),
    path('contacts/', lead_list.ContactsViewSet.as_view()),
    path('contacts/<int:pk>/', lead_list.ContactsDetailViewSet.as_view()),
    path('contacts/<int:pk_contact>/phone_contacts/', lead_list.PhoneOfContactsViewSet.as_view()),
    path('contacts/<int:pk_contact>/phone_contacts/<int:pk>/', lead_list.PhoneOfContactsDetailViewSet.as_view()),
    # Photos
    path('leads/<int:pk_lead>/photos/', lead_list.LeadPhotosViewSet.as_view()),
    path('leads/<int:pk_lead>/photos/<int:pk>/', lead_list.LeadPhotosDetailViewSet.as_view()),
    # Contact Type Name
    path('contact-types/', lead_list.ContactTypeNameGenericView.as_view()),
    path('contact-types/<int:pk>/', lead_list.ContactTypeNameDetailGenericView.as_view()),
    # Project type
    path('project-types/', lead_list.ProjectTypeGenericView.as_view()),
    path('project-types/<int:pk>/', lead_list.ProjectTypeDetailGenericView.as_view()),

    path('catalog/materials/', catalog.MaterialList.as_view()),
    path('catalog/materials/<int:pk>/', catalog.MaterialDetail.as_view()),
    path('catalog/cost-tables/', catalog.CostTableList.as_view()),
    path('catalog/cost-tables/<int:pk>/', catalog.CostTableDetail.as_view()),
    
    # For country, state, city
    path('location/', include('base.urls'))
]
