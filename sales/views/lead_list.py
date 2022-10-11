from ..models.lead_list import LeadDetail, Activities, Contact, PhoneOfContact, ContactType
from ..serializers import lead_list

from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


def pop(data, key, type):
    try:
        return data.pop(key)
    except KeyError:
        pass
    return type


class LeadDetailsViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = LeadDetail.objects.all()
        serializer = lead_list.LeadDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        data = request.data
        activities = pop(data, 'activities', [])
        contacts = pop(data, 'contacts', [])

        ld = LeadDetail.objects.create(
            user_create=request.user, user_update=request.user, **data)
        if activities:
            Activities.objects.bulk_create([Activities(lead=ld, user_create=request.user,
                                                       user_update=request.user, **activity)
                                            for activity in activities])
        if contacts:
            for contact in contacts:
                contact_type = pop(contact, 'contact_type', '')
                phones = pop(contact, 'phone_contact', [])
                ct = Contact.objects.create(lead=ld, **contact)
                if contact_type:
                    ContactType.objects.create(
                        contact=ct, lead=ld, name=contact_type[0].get('name'))
                PhoneOfContact.objects.bulk_create(
                    [PhoneOfContact(contact=ct, **phone) for phone in phones])
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
        activities = pop(data, 'activities', [])

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


class LeadActivitiesViewSet(generics.ListCreateAPIView):
    """
    Used for get params
    """
    queryset = Activities.objects.all()
    serializer_class = lead_list.ActivitiesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(LeadDetail.objects.all(), pk=self.kwargs['pk_lead'])
        return Activities.objects.filter(lead_id=self.kwargs['pk_lead'])


class LeadActivitiesDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    """
    Used for get params
    """
    queryset = Activities.objects.all()
    serializer_class = lead_list.ActivitiesSerializer
    permission_classes = [permissions.IsAuthenticated]
