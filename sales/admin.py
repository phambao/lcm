from django.contrib import admin

from sales.models.catalog import Catalog
from sales.models.lead_list import LeadDetail
from sales.models.estimate import EstimateTemplate
from sales.models.lead_schedule import ToDo, ScheduleEvent, DailyLog
from sales.models.proposal import ProposalWriting
# Register your models here.


class FilterUserCreateAdmin(admin.ModelAdmin):
    list_filter = ('user_create', )
    list_display = ('id', 'name')


class CatalogAdmin(FilterUserCreateAdmin):
    search_fields = ['name']


class LeadDetailAdmin(FilterUserCreateAdmin):
    list_display = ('id', 'lead_title')
    search_fields = ['lead_title']


class EstimateTemplateAdmin(FilterUserCreateAdmin):
    search_fields = ['name']


class ProposalWritingAdmin(FilterUserCreateAdmin):
    search_fields = ['name']


class ScheduleTodoAdmin(FilterUserCreateAdmin):
    list_display = ('id', 'title')
    search_fields = ['title']


class ScheduleEventAdmin(FilterUserCreateAdmin):
    list_display = ('id', 'event_title')
    search_fields = ['event_title']


class ScheduleDailyLogAdmin(FilterUserCreateAdmin):
    list_display = ('id', 'title')
    search_fields = ['title']


admin.site.register(DailyLog, ScheduleDailyLogAdmin)
admin.site.register(ScheduleEvent, ScheduleEventAdmin)
admin.site.register(ToDo, ScheduleTodoAdmin)
admin.site.register(Catalog, CatalogAdmin)
admin.site.register(LeadDetail, LeadDetailAdmin)
admin.site.register(EstimateTemplate, EstimateTemplateAdmin)
admin.site.register(ProposalWriting, ProposalWritingAdmin)
