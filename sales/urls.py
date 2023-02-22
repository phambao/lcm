from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from sales.views import lead_list, catalog, lead_schedule, estimate
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
    path('leads/<int:pk_lead>/contacts/link/', lead_list.link_contacts_to_lead),
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
    path('leads/summary/', lead_list.get_summaries),
]

# Define Path for Catalog -------------------------------------------------------
url_catalog = [
    path('list/', catalog.CatalogList.as_view(), name='catalogs'),
    path('list/<int:pk>/', catalog.CatalogDetail.as_view()),
    path('list/<int:pk>/children/', catalog.get_catalog_children),
    # path('list/<int:pk>/levels/', catalog.get_catalog_levels), temporarily removed
    path('list/<int:pk>/tree/', catalog.get_catalog_tree),
    path('list/<int:pk>/list/', catalog.get_catalog_list),
    path('list/ancestors/', catalog.get_catalog_ancestors),
    path('list/<int:pk>/copy/', catalog.duplicate_catalogs),
    path('list/<int:pk>/copy-tree/', catalog.duplicate_catalogs_on_tree),
    path('list/delete/', catalog.delete_catalogs),
    path('cost-tables/', catalog.CostTableList.as_view()),
    path('cost-tables/<int:pk>/', catalog.CostTableDetail.as_view()),
    path('list/<int:pk_catalog>/levels/', catalog.CatalogLevelList.as_view()),
    path('list/<int:pk_catalog>/levels/<int:pk>/', catalog.CatalogLevelDetail.as_view()),
    path('list/<int:pk_catalog>/swap-level/', catalog.swap_level, name='swap-level'),
    path('list/add-catalog-levels/', catalog.add_multiple_level, name='add-multiple-level'),
    path('unit/', catalog.DataPointUnitView.as_view()),
    path('unit/<int:pk>/', catalog.DataPointUnitDetailView.as_view()),
]
# define path for Schedule -------------------------------------------------------
url_schedule = [
    # TO_DO
    path('todo/', lead_schedule.SourceScheduleToDoGenericView.as_view()),
    path('todo/message/', lead_schedule.ScheduleTodoMessageGenericView.as_view()),
    path('todo/<int:pk>/', lead_schedule.ScheduleDetailGenericView.as_view()),
    path('todo/message-custom-field/', lead_schedule.ToDoMessageCustomFieldGenericView.as_view({
        "post": "create_message_custom_field", "put": "update_message_custom_field"})),
    # FILE
    path('todo/<int:pk_todo>/attachments/', lead_schedule.ScheduleAttachmentsGenericView.as_view({
        "post": "create_file", "get": "get_file"})),

    path('todo/checklist-item/<int:pk_checklist>/file/<int:pk>/', lead_schedule.delete_file_todo_checklist_item),
    path('todo/file/<int:pk>/', lead_schedule.delete_file_todo),
    # TAG
    path('tags/', lead_schedule.TagScheduleGenericView.as_view()),
    path('tags/<int:pk>/', lead_schedule.TagScheduleDetailGenericView.as_view()),
    # SHIFT REASON
    path('shift-reason/', lead_schedule.ScheduleShiftReasonGenericView.as_view()),
    path('shift-reason/<int:pk>/', lead_schedule.ScheduleShiftReasonDetailGenericView.as_view()),
    # CHECKLIST ITEM
    path('checklist-item/', lead_schedule.CheckListItemGenericView.as_view()),
    path('checklist-item/<int:pk>/', lead_schedule.CheckListItemDetailGenericView.as_view()),
    path('todo/<int:pk_todo>/checklist-item/', lead_schedule.get_checklist_by_todo),
    path('todo/<int:pk_todo>/checklist-item/template/', lead_schedule.get_checklist_template_by_todo),
    path('checklist-item/template/', lead_schedule.TemplateChecklistItemGenericView.as_view()),
    path('checklist-item/template/<int:pk>/', lead_schedule.TemplateChecklistItemDetailGenericView.as_view()),
    path('checklist-item/template/file/<int:pk>/', lead_schedule.delete_file_checklist_template),


    # TEMPLATE CHECKLIST ITEM
    path('todo/checklist-item/template/', lead_schedule.ToDoChecklistItemTemplateGenericView.as_view()),
    path('todo/checklist-items/template/<int:pk>/', lead_schedule.ToDoChecklistItemTemplateDetailGenericView.as_view()),
    path('todo/<int:pk_todo>/template/<int:pk_template>/', lead_schedule.select_checklist_template),
    path('todo/<int:pk_todo>/other-template/<int:pk_template>/', lead_schedule.select_checklist_template),
    # DAILY LOGS
    path('daily-logs/', lead_schedule.DailyLogGenericView.as_view()),
    path('daily-logs/<int:pk>/', lead_schedule.DailyLogDetailGenericView.as_view()),
    path('daily-logs/comment/', lead_schedule.DaiLyLogCommentGenericView.as_view()),
    path('daily-logs/comment/<int:pk>/', lead_schedule.DaiLyLogCommentDetailGenericView.as_view()),
    # FILE DAILY LOG
    path('daily-logs/<int:pk_daily_log>/attachments/', lead_schedule.AttachmentsDailyLogGenericView.as_view({
        "post": "create_file", "get": "get_file"})),
    path('daily-logs/file/<int:pk>/', lead_schedule.delete_file_daily_log),
    # TEMPLATE NOTE DAILY LOG
    path('daily-logs/template/', lead_schedule.DailyLogTemplateNoteGenericView.as_view()),
    path('daily-logs/template/<int:pk>/', lead_schedule.DailyLogTemplateNoteDetailGenericView.as_view()),
    # SETTING DAILY LOG
    path('daily-logs/setting/', lead_schedule.ScheduleDailyLogSettingGenericView.as_view()),
    path('daily-logs/setting/<int:pk>/', lead_schedule.ScheduleDailyLogSettingDetailGenericView.as_view()),
    path('daily-logs/custom-field/', lead_schedule.ScheduleDailyLogCustomFieldSettingGenericView.as_view()),
    path('daily-logs/custom-field/<int:pk>/', lead_schedule.ScheduleDailyLogCustomFieldSettingDetailGenericView.as_view()),
    path('daily-logs/delete-custom-field/<int:pk>/', lead_schedule.delete_custom_field_daily_log),
    # path('daily-logs/default-value/', lead_schedule.config_setting_daily_log),

    # SCHEDULE EVENT
    path('schedule-event/', lead_schedule.ScheduleEventGenericView.as_view()),
    path('schedule-events/delete/', lead_schedule.delete_event),
    path('schedule-event/filter/', lead_schedule.filter_event),
    path('schedule-event/<int:pk>/', lead_schedule.ScheduleEventDetailGenericView.as_view()),
    path('select-schedule-event/', lead_schedule.select_event_predecessors),
    path('select-schedule-event-link/<int:pk>/', lead_schedule.select_event_link),
    path('schedule-event/message/', lead_schedule.ScheduleEventMessageGenericView.as_view()),
    path('schedule-event/shift/reason/', lead_schedule.ScheduleEventShiftReasonGenericView.as_view()),
    path('schedule-event/shift/reason/<int:pk>/', lead_schedule.ScheduleEventShiftReasonDetailGenericView.as_view()),

    # FILE EVENT
    path('event/<int:pk_event>/attachments/', lead_schedule.AttachmentsEventGenericView.as_view({
        "post": "create_file", "get": "get_file"})),
    path('event/file/<int:pk>/', lead_schedule.delete_file_event),
    # SETTING EVENT
    path('schedule-event/setting/', lead_schedule.ScheduleEventSettingGenericView.as_view()),
    path('schedule-event/setting/<int:pk>/', lead_schedule.ScheduleEventSettingDetailGenericView.as_view()),
    path('schedule-event/setting/phase/', lead_schedule.ScheduleEventPhaseSettingGenericView.as_view()),
    path('schedule-event/setting/phase/<int:pk>/', lead_schedule.ScheduleEventPhaseSettingDetailGenericView.as_view()),
    path('schedule-event/delete-phase/<int:pk>/', lead_schedule.delete_phase),

    # CUSTOM FIELD SCHEDULE TO_DO
    path('schedule-todo/setting/', lead_schedule.ScheduleToDoSettingGenericView.as_view()),
    path('schedule-todo/setting/<int:pk>/', lead_schedule.ScheduleToDoSettingDetailGenericView.as_view()),
    path('schedule-todo/custom-field/', lead_schedule.ScheduleToDoCustomFieldGenericView.as_view()),
    path('schedule-todo/custom-field/<int:pk>/', lead_schedule.ScheduleToDoCustomFieldDetailGenericView.as_view()),
    path('schedule-todo/delete-custom-field/<int:pk>/', lead_schedule.delete_custom_field),

]

# URL Estimate
url_estimate = [
    path('po-formula/', estimate.POFormulaList.as_view()),
    path('po-formula/<int:pk>/', estimate.POFormulaDetail.as_view()),
    path('formula-grouping/', estimate.POFormulaGroupingList.as_view()),
    path('formula-grouping/<int:pk>/', estimate.POFormulaGroupingDetail.as_view()),
    path('data-entry/', estimate.DataEntryList.as_view()),
    path('data-entry/<int:pk>/', estimate.DataEntryDetail.as_view()),
    path('template-name/', estimate.TemplateNameList.as_view()),
    path('template-name/<int:pk>/', estimate.TemplateNameDetail.as_view()),
    path('unit-library/', estimate.UnitLibraryList.as_view()),
    path('unit-library/<int:pk>/', estimate.UnitLibraryDetail.as_view()),
]
# URL Config
url_config = [
    path('options-lead-list/', lead_schedule.select_lead_list),
]
# DEFINE PATH FOR SALES APP -----------------------------------------------------
url_sales = [
    path('', include(url_config)),
    path('', include(url_contacts)),
    path('', include(url_contact_types)),
    path('lead-list/', include(url_leads)),
    path('catalog/', include(url_catalog)),
    path('schedule/', include(url_schedule)),
    path('estimate/', include(url_estimate)),
]

schema_view_sales = get_schema_view(
    openapi.Info(
        title="API FOR SALES APP",
        default_version='v1',
    ),
    patterns=[
        path('api/sales/', include(url_config)),
        path('api/sales/', include(url_contacts)),
        path('api/sales/', include(url_contact_types)),
        path('api/sales/lead-list/', include(url_leads)),
        path('api/sales/catalog/', include(url_catalog)),
        path('api/sales/schedule/', include(url_schedule)),
        path('api/sales/estimate/', include(url_estimate))
    ],
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('', include(url_sales)),
    path('', schema_view_sales.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
