from ..models.lead_list import LeadDetail
from ..serializers.lead_list import LeadDetailSerializer

from rest_framework import generics, permissions


class LeadDetailList(generics.ListCreateAPIView):
    queryset = LeadDetail.objects.all()
    serializer_class = LeadDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeadDetailRUD(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeadDetail.objects.all()
    serializer_class = LeadDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
