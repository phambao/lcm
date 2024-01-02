from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from api.serializers.auth import CustomPermissionSerializer

from base.models.config import PersonalInformation
from base.serializers.auth import GroupSerializer, PermissionSerializer
from base.serializers.config import PersonalInformationSerializer
from base.views.base import CompanyFilterMixin


class GroupFilterCompanyMixin:
    def get_queryset(self):
        return Group.objects.filter(group__company=self.request.user.company)


class GroupList(GroupFilterCompanyMixin, generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupDetail(GroupFilterCompanyMixin, generics.RetrieveUpdateDestroyAPIView):
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


class PersonalInformationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PersonalInformation.objects.all()
    serializer_class = PersonalInformationSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_permission(request):
    from sales.models import (Catalog, ChangeOrder, EstimateTemplate, Invoice, LeadDetail,
                              ScheduleEvent, ToDo, DailyLog, ProposalWriting)

    def get_perm_by_models(models):
        perms = Permission.objects.none()
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            perms |= Permission.objects.filter(content_type=content_type)
        return perms

    v1 = request.GET.get('v1', False)
    perms = get_perm_by_models((Catalog, ChangeOrder, EstimateTemplate, Invoice, LeadDetail, ScheduleEvent,
                                ToDo, DailyLog, ProposalWriting))
    if v1:
        data = []
        data.append({
            'name': 'Sales',
            'roles': CustomPermissionSerializer(get_perm_by_models([LeadDetail]), many=True).data
        })
        data.append({
            'name': 'Project Management',
            'roles': CustomPermissionSerializer(get_perm_by_models(
                [Catalog, ChangeOrder, EstimateTemplate, Invoice, ScheduleEvent, ToDo, DailyLog, ProposalWriting]), many=True).data
        })
        return Response(status=status.HTTP_200_OK, data=data)

    return Response(status=status.HTTP_200_OK, data=perms.values())
