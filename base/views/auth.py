from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from base.models.config import PersonalInformation
from base.serializers.auth import GroupSerializer, PermissionSerializer
from base.serializers.config import PersonalInformationSerializer
from base.views.base import CompanyFilterMixin


class GroupList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class PermissionList(generics.ListCreateAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class PermissionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class PersonalInformationView(generics.ListCreateAPIView):
    queryset = PersonalInformation.objects.all()
    serializer_class = PersonalInformationSerializer
    permission_classes = [permissions.IsAuthenticated]


class PersonalInformationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PersonalInformation.objects.all()
    serializer_class = PersonalInformationSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_permission(request):
    from sales.models.catalog import Catalog
    from sales.models.change_order import ChangeOrder
    from sales.models.estimate import EstimateTemplate
    from sales.models.invoice import Invoice
    from sales.models.lead_list import LeadDetail
    from sales.models.lead_schedule import ScheduleEvent
    from sales.models.proposal import ProposalWriting

    perms = Permission.objects.none()
    content_type = ContentType.objects.get_for_model(Catalog)
    perms = perms | Permission.objects.filter(content_type=content_type)
    content_type = ContentType.objects.get_for_model(ChangeOrder)
    perms = perms | Permission.objects.filter(content_type=content_type)
    content_type = ContentType.objects.get_for_model(EstimateTemplate)
    perms = perms | Permission.objects.filter(content_type=content_type)
    content_type = ContentType.objects.get_for_model(Invoice)
    perms = perms | Permission.objects.filter(content_type=content_type)
    content_type = ContentType.objects.get_for_model(LeadDetail)
    perms = perms | Permission.objects.filter(content_type=content_type)
    content_type = ContentType.objects.get_for_model(ScheduleEvent)
    perms = perms | Permission.objects.filter(content_type=content_type)
    content_type = ContentType.objects.get_for_model(ProposalWriting)
    perms = perms | Permission.objects.filter(content_type=content_type)
    return Response(status=status.HTTP_200_OK, data=perms.values())
