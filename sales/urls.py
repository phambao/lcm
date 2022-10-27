from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from sales.views import lead_list, catalog
from api.views.upload_file import FileUploadView


# Define Path for Contacts -----------------------------------------------------
url_contacts = [
    path('contacts/', lead_list.ContactsViewSet.as_view()),
    path('contacts/<int:pk>/', lead_list.ContactsDetailViewSet.as_view()),
    path('contacts/<int:pk_contact>/phone_contacts/',
         lead_list.PhoneOfContactsViewSet.as_view()),
    path('contacts/<int:pk_contact>/phone_contacts/<int:pk>/',
         lead_list.PhoneOfContactsDetailViewSet.as_view()),
]

url_contact_types = [
    path('contact-types/', lead_list.ContactTypeNameGenericView.as_view()),
    path('contact-types/<int:pk>/',
         lead_list.ContactTypeNameDetailGenericView.as_view()),
]

url_tag_activity = [
    path('tags/', lead_list.TagActivitiesGenericView.as_view()),
    path('tags/<int:pk>/', lead_list.TagActivityDetailGenericView.as_view())
]

url_phase_activity = [
    path('phase/', lead_list.PhaseActivitiesGenericView.as_view()),
    path('phase/<int:pk>/', lead_list.PhaseActivityDetailGenericView.as_view())
]

# Define Path for Leads ---------------------------------------------------------
url_leads = [
    # Leads
    path('leads/', lead_list.LeadDetailList.as_view()),
    path('leads/uploads', FileUploadView.as_view()),
    path('leads/<int:pk>/', lead_list.LeadDetailGeneric.as_view()),
    path('leads-params/', lead_list.LeadDetailList.as_view()),
    path('leads-params/<int:pk>/', lead_list.LeadDetailGeneric.as_view()),
    # Contacts
    path('leads/<int:pk_lead>/contacts/', lead_list.LeadContactsViewSet.as_view()),
    path('leads/<int:pk_lead>/contacts/<int:pk>/', lead_list.LeadContactDetailsViewSet.as_view()),
    # Activities
    path('leads/<int:pk_lead>/activities/',
         lead_list.LeadActivitiesViewSet.as_view()),
    path('leads/<int:pk_lead>/activities/<int:pk>/',
         lead_list.LeadActivitiesDetailViewSet.as_view()),
    path('leads/<int:pk_lead>/activities/delete/', lead_list.delete_activities),
    path('activity/', include(url_tag_activity)),
    path('activity/', include(url_phase_activity)),
    # Photos
    path('leads/<int:pk_lead>/photos/', lead_list.LeadPhotosViewSet.as_view()),
    path('<int:pk_lead>/photos/<int:pk>/',
         lead_list.LeadPhotosDetailViewSet.as_view()),
    # Project type
    path('project-types/', lead_list.ProjectTypeGenericView.as_view()),
    path('project-types/<int:pk>/',
         lead_list.ProjectTypeDetailGenericView.as_view()),
]

# Define Path for Catalog -------------------------------------------------------
url_catalog = [
    path('list/', catalog.CatalogList.as_view()),
    path('list/<int:pk>/', catalog.CatalogDetail.as_view()),
    path('cost-tables/', catalog.CostTableList.as_view()),
    path('cost-tables/<int:pk>/', catalog.CostTableDetail.as_view()),
]

# DEFINE PATH FOR SALES APP -----------------------------------------------------
url_sales = [
    path('', include(url_contacts)),
    path('', include(url_contact_types)),
    path('lead-list/', include(url_leads)),
    path('catalog/', include(url_catalog)),
]

schema_view_sales = get_schema_view(
    openapi.Info(
        title="API FOR SALES APP",
        default_version='v1',
    ),
    patterns=[
        path('api/sales/', include(url_contacts)),
        path('api/sales/', include(url_contact_types)),
        path('api/sales/lead-list/', include(url_leads)),
        path('api/sales/catalog/', include(url_catalog)),
    ],
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('', include(url_sales)),
    path('', schema_view_sales.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
