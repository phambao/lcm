from django.contrib import admin

from sales.models.catalog import Catalog
from sales.models.lead_list import LeadDetail
from sales.models.estimate import EstimateTemplate
from sales.models.proposal import ProposalWriting
# Register your models here.


class FilterUserCreateAdmin(admin.ModelAdmin):
    list_filter = ('user_create', )


class CatalogAdmin(FilterUserCreateAdmin):
    pass


class LeadDetailAdmin(FilterUserCreateAdmin):
    pass


class EstimateTemplateAdmin(FilterUserCreateAdmin):
    pass


class ProposalWritingAdmin(FilterUserCreateAdmin):
    pass


admin.site.register(Catalog, CatalogAdmin)
admin.site.register(LeadDetail, LeadDetailAdmin)
admin.site.register(EstimateTemplate, EstimateTemplateAdmin)
admin.site.register(ProposalWriting, ProposalWritingAdmin)
