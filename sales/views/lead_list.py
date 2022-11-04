from rest_framework.decorators import api_view, permission_classes

from base.models.search import Search
from base.serializers.search import SearchSerializer
from ..models.lead_list import LeadDetail, Activities, Contact, PhoneOfContact, ContactType, Photos, ContactTypeName, \
    ProjectType, TagLead, PhaseActivity, TagActivity, SourceLead
from ..serializers import lead_list

from rest_framework import generics, permissions
from rest_framework import status, filters as rf_filters
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from ..filters.lead_list import ContactsFilter, ActivitiesFilter, LeadDetailFilter

PASS_FIELDS = ['user_create', 'user_update', 'lead']


class LeadDetailList(generics.ListCreateAPIView):

    queryset = LeadDetail.objects.all()
    serializer_class = lead_list.LeadDetailCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = LeadDetailFilter
    search_fields = ['lead_title', 'street_address', 'notes']


class LeadDetailGeneric(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeadDetail.objects.all()
    serializer_class = lead_list.LeadDetailCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        data = super().get_serializer_context()
        data['pk_lead'] = self.kwargs.get('pk')
        return data

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if not instance.number_of_click:
            instance.number_of_click = 0
        instance.number_of_click += 1
        instance.recent_click = timezone.now()
        instance.save()
        return Response(serializer.data)


class LeadActivitiesViewSet(generics.ListCreateAPIView):
    serializer_class = lead_list.ActivitiesSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ActivitiesFilter
    search_fields = ['title', 'phase', 'tag', 'status', 'assigned_to']

    def get_queryset(self):
        get_object_or_404(LeadDetail.objects.all(), pk=self.kwargs['pk_lead'])
        return Activities.objects.filter(lead_id=self.kwargs['pk_lead'])


class LeadActivitiesDetailViewSet(generics.RetrieveUpdateDestroyAPIView):

    queryset = Activities.objects.all()
    serializer_class = lead_list.ActivitiesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        data = request.data
        [data.pop(field) for field in PASS_FIELDS if field in data]
        instance = self.get_object()
        instance.user_update = request.user
        instance.save()
        return super().put(request, *args, **kwargs)


class LeadPhotosViewSet(generics.ListCreateAPIView):
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
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ContactsFilter


class ContactsDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    serializer_class = lead_list.ContactsSerializer
    permission_classes = [permissions.IsAuthenticated]


class PhoneOfContactsViewSet(generics.ListCreateAPIView):
    serializer_class = lead_list.PhoneContactsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(Contact.objects.all(), pk=self.kwargs['pk_contact'])
        return PhoneOfContact.objects.filter(contact_id=self.kwargs['pk_contact'])


class LeadContactsViewSet(generics.ListCreateAPIView):

    queryset = Contact.objects.all()
    serializer_class = lead_list.ContactsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ContactsFilter
    search_fields = ['first_name', 'last_name', 'email', 'phone_contacts__phone_number']

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


class ContactTypeNameGenericView(generics.ListCreateAPIView):
    queryset = ContactTypeName.objects.all()
    serializer_class = lead_list.ContactTypeNameSerializer
    permission_classes = [permissions.IsAuthenticated]


class ContactTypeNameDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ContactTypeName.objects.all()
    serializer_class = lead_list.ContactTypeNameSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectTypeGenericView(generics.ListCreateAPIView):
    queryset = ProjectType.objects.all()
    serializer_class = lead_list.ProjectTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectTypeDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProjectType.objects.all()
    serializer_class = lead_list.ProjectTypeSerializer
    permission_classes = [permissions.IsAuthenticated]


class TagLeadGenericView(generics.ListCreateAPIView):
    queryset = TagLead.objects.all()
    serializer_class = lead_list.TagLeadSerializer
    permission_classes = [permissions.IsAuthenticated]
    

class TagLeadDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TagLead.objects.all()
    serializer_class = lead_list.TagLeadSerializer
    permission_classes = [permissions.IsAuthenticated]


class TagActivitiesGenericView(generics.ListCreateAPIView):
    queryset = TagActivity.objects.all()
    serializer_class = lead_list.TagActivitySerializer
    permission_classes = [permissions.IsAuthenticated]


class TagActivityDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TagActivity.objects.all()
    serializer_class = lead_list.TagActivitySerializer
    permission_classes = [permissions.IsAuthenticated]


class PhaseActivitiesGenericView(generics.ListCreateAPIView):
    queryset = PhaseActivity.objects.all()
    serializer_class = lead_list.PhaseActivitySerializer
    permission_classes = [permissions.IsAuthenticated]


class PhaseActivityDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PhaseActivity.objects.all()
    serializer_class = lead_list.PhaseActivitySerializer
    permission_classes = [permissions.IsAuthenticated]


class SourceLeadGenericView(generics.ListCreateAPIView):
    queryset = SourceLead.objects.all()
    serializer_class = lead_list.SourceLeadSerializer
    permission_classes = [permissions.IsAuthenticated]


class SourceLeadDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SourceLead.objects.all()
    serializer_class = lead_list.SourceLeadSerializer
    permission_classes = [permissions.IsAuthenticated]


class SearchLeadGenericView(generics.ListCreateAPIView):
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        data = super().get_queryset()
        content_type = ContentType.objects.get_for_model(LeadDetail)
        data = data.filter(user=self.request.user, content_type=content_type)
        return data

    def create(self, request, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(LeadDetail)
        data = request.data.copy()
        data['content_type'] = content_type.id
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SearchLeadDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        data = super().get_queryset()
        content_type = ContentType.objects.get_for_model(LeadDetail)
        data = data.filter(user=self.request.user, content_type=content_type)
        return data


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_activities(request, pk_lead):
    """
        DELETE: delete multiple activities
    """

    if request.method == 'DELETE':
        ids = request.data
        activities = Activities.objects.filter(id__in=ids, lead=pk_lead)
        activities.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_leads(request):
    """
        DELETE: delete multiple leads
    """

    if request.method == 'DELETE':
        ids = request.data
        leads = LeadDetail.objects.filter(id__in=ids)
        leads.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_contacts(request):
    """
        DELETE: delete multiple contacts
    """

    if request.method == 'DELETE':
        ids = request.data
        contacts = Contact.objects.filter(id__in=ids)
        contacts.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def unlink_contact_from_lead(request, pk_lead):
    """
        PUT: unlink contact from lead
    """

    if request.method == 'PUT':
        contact_ids = request.data
        lead = LeadDetail.objects.get(pk=pk_lead)
        contacts_to_unlink = lead.contacts.all().filter(id__in=contact_ids)
        lead.contacts.remove(*contacts_to_unlink)
        data = lead_list.ContactsSerializer(
            contacts_to_unlink, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_summaries(request):
    data = {
        'closed_job': {'title': 'TOTAL CLOSED JOBS',
                       'number': 350,
                       'content': 200},
        'number_of_job': {'title': 'TOTAL # OF JOBS IN PROGRESS',
                          'number': 89,
                          'content': 200},
        'closed_ratio': {'title': 'CLOSED RATIO',
                         'number': 45,
                         'content': -200},
        'dollar_of_job': {'title': 'TOTAL $ OF JOBS IN PROGRESS',
                          'number': 60090,
                          'content': 2000},
    }
    if request.method == 'GET':
        pass
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['PUT'])
def link_contacts_to_lead(request, pk_lead):
    """
        PUT: link contacts to lead
    """

    if request.method == 'PUT':
        contact_ids = request.data
        lead = LeadDetail.objects.get(pk=pk_lead)
        contacts_to_link = Contact.objects.filter(id__in=contact_ids)
        lead.contacts.add(*contacts_to_link)
        data = lead_list.ContactsSerializer(
            contacts_to_link, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)
