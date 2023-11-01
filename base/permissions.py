from rest_framework import permissions

from sales.models.catalog import Catalog
from sales.models.change_order import ChangeOrder
from sales.models.estimate import EstimateTemplate
from sales.models.invoice import Invoice
from sales.models.lead_list import LeadDetail
from sales.models.lead_schedule import ScheduleEvent
from sales.models.proposal import ProposalWriting


class FullDjangoModelPermissions(permissions.DjangoModelPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class CatalogPermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, Catalog)
        return request.user.has_perms(perms)


class ChangeOrderPermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, ChangeOrder)
        return request.user.has_perms(perms)


class EstimatePermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, EstimateTemplate)
        return request.user.has_perms(perms)


class InvoicePermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, Invoice)
        return request.user.has_perms(perms)


class LeadPermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, LeadDetail)
        return request.user.has_perms(perms)


class SchedulePermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, ScheduleEvent)
        return request.user.has_perms(perms)


class ProposalPermissions(FullDjangoModelPermissions):
    def has_permission(self, request, view):
        if request.user.is_superuser == False and request.user.company.is_payment == False:
            return False
        if request.user.is_admin_company == True:
            return True
        perms = self.get_required_permissions(request.method, ProposalWriting)
        return request.user.has_perms(perms)
