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
    path('contacts/delete/', lead_list.delete_contacts),
]

url_contact_types = [
    path('contact-types/', lead_list.ContactTypeNameGenericView.as_view()),
    path('contact-types/<int:pk>/',
         lead_list.ContactTypeNameDetailGenericView.as_view()),
]

# Define Path for Leads ---------------------------------------------------------
url_leads = [
    # Leads
    path('leads/', lead_list.LeadDetailList.as_view()),
    path('leads/uploads', FileUploadView.as_view()),
    path('leads/<int:pk>/', lead_list.LeadDetailGeneric.as_view()),
    path('leads/delete/', lead_list.delete_leads),
    # Contacts
    path('leads/<int:pk_lead>/contacts/', lead_list.LeadContactsViewSet.as_view()),
    path('leads/<int:pk_lead>/contacts/<int:pk>/', lead_list.LeadContactDetailsViewSet.as_view()),
    path('leads/<int:pk_lead>/contacts/unlink/', lead_list.unlink_contact_from_lead),
    # Activities
    path('leads/<int:pk_lead>/activities/',
         lead_list.LeadActivitiesViewSet.as_view()),
    path('leads/<int:pk_lead>/activities/<int:pk>/',
         lead_list.LeadActivitiesDetailViewSet.as_view()),
    path('leads/<int:pk_lead>/activities/delete/', lead_list.delete_activities),
    path('activity/', include([
        path('tags/', lead_list.TagActivitiesGenericView.as_view()),
        path('tags/<int:pk>/', lead_list.TagActivityDetailGenericView.as_view())
    ])),
    path('activity/', include([
        path('phase/', lead_list.PhaseActivitiesGenericView.as_view()),
        path('phase/<int:pk>/', lead_list.PhaseActivityDetailGenericView.as_view())
    ])),
    # Photos
    path('leads/<int:pk_lead>/photos/', lead_list.LeadPhotosViewSet.as_view()),
    path('leads/<int:pk_lead>/photos/<int:pk>/',
         lead_list.LeadPhotosDetailViewSet.as_view()),
    # Project type
    path('project-types/', lead_list.ProjectTypeGenericView.as_view()),
    path('project-types/<int:pk>/',
         lead_list.ProjectTypeDetailGenericView.as_view()),
    # Tags
    path('tags/', lead_list.TagLeadGenericView.as_view()),
    path('tags/<int:pk>/', lead_list.TagLeadDetailGenericView.as_view()),

    # Source
    path('sources/', lead_list.SourceLeadGenericView.as_view()),
    path('sources/<int:pk>/', lead_list.SourceLeadDetailGenericView.as_view()),
]

# Define Path for Catalog -------------------------------------------------------
url_catalog = [
    # Materials
    path('materials/', catalog.MaterialList.as_view()),
    path('materials/<int:pk>/', catalog.MaterialDetail.as_view()),
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
