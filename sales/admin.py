from django.contrib import admin

from sales.models.catalog import Catalog
from sales.models.lead_list import LeadDetail
from sales.models.estimate import EstimateTemplate
from sales.models.proposal import ProposalWriting
# Register your models here.

admin.site.register(Catalog)
admin.site.register(LeadDetail)
admin.site.register(EstimateTemplate)
admin.site.register(ProposalWriting)
