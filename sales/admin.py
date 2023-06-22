from django.contrib import admin

from sales.models.catalog import Catalog
from sales.models.lead_list import LeadDetail
from sales.models.estimate import EstimateTemplate
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


admin.site.register(Catalog, CatalogAdmin)
admin.site.register(LeadDetail, LeadDetailAdmin)
admin.site.register(EstimateTemplate, EstimateTemplateAdmin)
admin.site.register(ProposalWriting, ProposalWritingAdmin)
