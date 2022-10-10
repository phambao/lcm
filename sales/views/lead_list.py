from ..models.lead_list import LeadDetail, Activities
from ..serializers import lead_list

from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class LeadDetailsViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = LeadDetail.objects.all()
        serializer = lead_list.LeadDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        data = request.data
        try:
            activities = data.pop('activities')
        except KeyError:
            activities = []
        ld = LeadDetail.objects.create(user_create=request.user, user_update=request.user, **data)
        if activities:
            Activities.objects.bulk_create([Activities(lead=ld, user_create=request.user,
                                                       user_update=request.user, **activity)
                                            for activity in activities])
        serializer = lead_list.LeadDetailCreateSerializer(ld)
        return Response(serializer.data)


class LeadDetailList(generics.ListCreateAPIView):
    """
    Used for get params
    """
    queryset = LeadDetail.objects.all()
    serializer_class = lead_list.LeadDetailCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeadDetailViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        queryset = LeadDetail.objects.all()
        ld = get_object_or_404(queryset, pk=pk)
        serializer = lead_list.LeadDetailCreateSerializer(ld)
        return Response(serializer.data)

    def update(self, request, pk=None):
        data = request.data
        try:
            activities = data.pop('activities')
        except KeyError:
            activities = []
        queryset = LeadDetail.objects.all()
        ld = get_object_or_404(queryset, pk=pk)
        ld.activities.all().delete()
        if activities:
            Activities.objects.bulk_create([Activities(lead=ld,
                                                       user_update=request.user, **activity)
                                            for activity in activities])
        ld = LeadDetail.objects.filter(pk=pk)
        ld.update(user_update=request.user, **data)
        serializer = lead_list.LeadDetailCreateSerializer(ld[0])
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        queryset = LeadDetail.objects.all()
        ld = get_object_or_404(queryset, pk=pk)
        ld.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
