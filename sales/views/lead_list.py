from ..models.lead_list import LeadDetail, Activities, Contact, PhoneOfContact, ContactType, Photos
from ..serializers import lead_list

from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


PASS_FIELDS = ['user_create', 'user_update', 'lead']


def pop(data, key, type):
    try:
        return data.pop(key)
    except KeyError:
        pass
    return type


class LeadDetailsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        queryset = LeadDetail.objects.all()
        serializer = lead_list.LeadDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        user_create = user_update = request.user
        data = request.data
        activities = pop(data, 'activities', [])
        contacts = pop(data, 'contacts', [])
        photos = pop(data, 'photos', [])
        [data.pop(field) for field in PASS_FIELDS if field in data]

        ld = LeadDetail.objects.create(
            user_create=user_create, user_update=user_update, **data)
        if activities:
            acts = []
            for activity in activities:
                [activity.pop(field) for field in PASS_FIELDS if field in activity]
                acts.append(Activities(
                    user_create=user_create, user_update=user_update, lead=ld, **activity))
            Activities.objects.bulk_create(acts)
        if contacts:
            for contact in contacts:
                contact_type = pop(contact, 'contact_type', '')
                phones = pop(contact, 'phone_contacts', [])
                contact_id = contact.get('id', None)
                if contact_id:
                    # If contact has exist in database
                    ct = Contact.objects.get(id=contact_id)
                else:
                    ct = Contact.objects.create(**contact)
                ld.contacts.add(ct)
                # if contact_type:
                #     ContactType.objects.create(
                #         contact=ct, lead=ld, name=contact_type[0].get('name'))
                PhoneOfContact.objects.bulk_create(
                    [PhoneOfContact(contact=ct, **phone) for phone in phones])
        if photos:
            photo_id = [photo.get('id') for photo in photos]
            Photos.objects.filter(pk__in=photo_id).update(lead=ld)

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
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        queryset = LeadDetail.objects.all()
        ld = get_object_or_404(queryset, pk=pk)
        serializer = lead_list.LeadDetailCreateSerializer(ld)
        return Response(serializer.data)

    def update(self, request, pk=None):
        data = request.data
        activities = pop(data, 'activities', [])
        user_update = pop(data, 'user_update', request.user)
        user_create = pop(data, 'user_create', request.user)
        photos = pop(data, 'photos', request.user)
        contacts = pop(data, 'contacts', request.user)

        queryset = LeadDetail.objects.all()
        ld = get_object_or_404(queryset, pk=pk)
        ld.activities.all().delete()
        if activities:
            Activities.objects.bulk_create([Activities(lead=ld, **activity)
                                            for activity in activities])
        ld = LeadDetail.objects.filter(pk=pk)

        ld.update(**data)
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

    def put(self, request, *args, **kwargs):
        data = request.data
        user_update = pop(data, 'user_update', request.user)
        instance = self.get_object()
        instance.user_update = user_update
        instance.save()
        return super().put(request, *args, **kwargs)


class LeadPhotosViewSet(generics.ListCreateAPIView):
    """
    Used for get params
    """
    queryset = Photos.objects.all()
    serializer_class = lead_list.PhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(LeadDetail.objects.all(), pk=self.kwargs['pk_lead'])
        return Photos.objects.filter(lead_id=self.kwargs['pk_lead'])        
    

class LeadPhotosDetailViewSet(generics.RetrieveDestroyAPIView):
    """
    Used for get params
    """
    queryset = Photos.objects.all()
    serializer_class = lead_list.PhotoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactsViewSet(generics.ListCreateAPIView):
    queryset = Contact.objects.all()
    serializer_class = lead_list.ContactsSerializer
    permission_classes = [permissions.IsAuthenticated]


class ContactsDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = lead_list.ContactsSerializer
    permission_classes = [permissions.IsAuthenticated]


class PhoneOfContactsViewSet(generics.ListCreateAPIView):
    queryset = PhoneOfContact.objects.all()
    serializer_class = lead_list.PhoneContactsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(Contact.objects.all(), pk=self.kwargs['pk_contact'])
        return PhoneOfContact.objects.filter(contact_id=self.kwargs['pk_contact'])


class LeadContactsViewSet(generics.ListCreateAPIView):

    queryset = Contact.objects.all()
    serializer_class = lead_list.ContactsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(LeadDetail.objects.all(), pk=self.kwargs['pk_lead'])
        return Contact.objects.filter(leads__id=self.kwargs['pk_lead'])


class LeadContactDetailsViewSet(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = lead_list.ContactsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LeadDetail.objects.get(pk=self.kwargs['pk_lead']).contacts.all()


class PhoneOfContactsDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset = PhoneOfContact.objects.all()
    serializer_class = lead_list.PhoneContactsSerializer
    permission_classes = [permissions.IsAuthenticated]
