import datetime
import uuid

import pytz
from django.core.files.base import ContentFile
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import filters as rf_filters
from rest_framework import generics
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.permissions import SchedulePermissions
from base.serializers.base import IDAndNameSerializer
from base.views.base import CompanyFilterMixin
from ..filters.schedule import DailyLogFilter, EventFilter, ToDoFilter
from ..models import LeadDetail
from ..models.lead_schedule import ToDo, TagSchedule, CheckListItems, Attachments, DailyLog, \
    AttachmentDailyLog, DailyLogTemplateNotes, TodoTemplateChecklistItem, ScheduleEvent, CheckListItemsTemplate, \
    FileScheduleEvent, CustomFieldScheduleSetting, TodoCustomField, ScheduleToDoSetting, ScheduleDailyLogSetting, \
    CustomFieldScheduleDailyLogSetting, Messaging, ScheduleEventSetting, ScheduleEventPhaseSetting, DailyLogCustomField, \
    FileCheckListItems, FileCheckListItemsTemplate, MessageEvent, CommentDailyLog, EventShiftReason, ShiftReason, \
    SetupWorkDay
from ..serializers import lead_schedule
from ..serializers.lead_schedule import EventLinkSerializer


class ScheduleAttachmentsGenericView(GenericViewSet):
    serializer_class = lead_schedule.ScheduleAttachmentsSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Attachments.objects.none()
        get_object_or_404(ToDo.objects.all(), pk=self.kwargs['pk_todo'])
        return Attachments.objects.filter(to_do=self.kwargs['pk_todo'])

    def create_file(self, request, **kwargs):
        serializer = lead_schedule.ScheduleAttachmentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_todo = self.kwargs.get('pk_todo')
        todo = get_object_or_404(ToDo.objects.all(), pk=self.kwargs['pk_todo'])
        # data_attachments = Attachments.objects.filter(to_do=pk_todo)
        # data_attachments.delete()
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = Attachments(
                file=content_file,
                to_do=todo,
                user_create=user,
                name=file.name
            )
            attachment_create.append(attachment)

        Attachments.objects.bulk_create(attachment_create)

        attachments = Attachments.objects.filter(to_do=pk_todo)
        data = lead_schedule.ScheduleAttachmentsModelSerializer(
            attachments, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)

    def get_file(self, request, **kwargs):
        get_object_or_404(ToDo.objects.all(), pk=self.kwargs['pk_todo'])
        data_file = Attachments.objects.filter(to_do=self.kwargs['pk_todo'])
        data = lead_schedule.ScheduleAttachmentsModelSerializer(
            data_file, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)


class AttachmentsDailyLogGenericView(GenericViewSet):
    serializer_class = lead_schedule.AttachmentsDailyLogSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AttachmentDailyLog.objects.none()
        get_object_or_404(DailyLog.objects.all(), pk=self.kwargs['pk_daily_log'])
        return AttachmentDailyLog.objects.filter(to_do=self.kwargs['pk_daily_log'])

    def create_file(self, request, **kwargs):
        serializer = lead_schedule.AttachmentsDailyLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_daily_log = self.kwargs.get('pk_daily_log')
        daily_log = get_object_or_404(DailyLog.objects.all(), pk=self.kwargs['pk_daily_log'])
        # data_attachments = AttachmentDailyLog.objects.filter(daily_log=pk_daily_log)
        # data_attachments.delete()
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = AttachmentDailyLog(
                file=content_file,
                daily_log=daily_log,
                user_create=user,
                name=file.name
            )
            attachment_create.append(attachment)

        AttachmentDailyLog.objects.bulk_create(attachment_create)

        attachments = AttachmentDailyLog.objects.filter(daily_log=pk_daily_log)
        data = lead_schedule.AttachmentsDailyLogModelSerializer(
            attachments, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)

    def get_file(self, request, **kwargs):
        get_object_or_404(DailyLog.objects.all(), pk=self.kwargs['pk_daily_log'])
        data_file = AttachmentDailyLog.objects.filter(daily_log=self.kwargs['pk_daily_log'])
        data = lead_schedule.AttachmentsDailyLogModelSerializer(
            data_file, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)


class AttachmentsEventGenericView(GenericViewSet):
    serializer_class = lead_schedule.AttachmentsEventSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FileScheduleEvent.objects.none()
        get_object_or_404(ScheduleEvent.objects.all(), pk=self.kwargs['pk_event'])
        return FileScheduleEvent.objects.filter(event=self.kwargs['pk_event'])

    def create_file(self, request, **kwargs):
        serializer = lead_schedule.AttachmentsEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_event = self.kwargs.get('pk_event')
        data_event = get_object_or_404(ScheduleEvent.objects.all(), pk=self.kwargs['pk_event'])
        # data_attachments = FileScheduleEvent.objects.filter(event=pk_event)
        # data_attachments.delete()
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = FileScheduleEvent(
                file=content_file,
                event=data_event,
                user_create=user,
                name=file.name
            )
            attachment_create.append(attachment)

        FileScheduleEvent.objects.bulk_create(attachment_create)

        attachments = FileScheduleEvent.objects.filter(event=pk_event)
        data = lead_schedule.AttachmentsEventModelSerializer(
            attachments, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)

    def get_file(self, request, **kwargs):
        get_object_or_404(ScheduleEvent.objects.all(), pk=self.kwargs['pk_event'])
        data_file = FileScheduleEvent.objects.filter(event=self.kwargs['pk_event'])
        data = lead_schedule.AttachmentsEventModelSerializer(
            data_file, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)


class SourceScheduleToDoGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ToDo.objects.all().prefetch_related('tags', 'assigned_to', 'check_list', 'messaging',
                                                   'check_list__assigned_to', 'messaging__notify',
                                                   'messaging__todo_message_file',
                                                   'custom_filed_to_do', 'attachments', 'check_list__file_check_list')
    serializer_class = lead_schedule.ToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ToDoFilter
    # search_fields = ['first_name', 'last_name', 'email', 'phone_contacts__phone_number']


class ScheduleDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ToDo.objects.all().prefetch_related('tags', 'assigned_to', 'check_list', 'messaging')
    serializer_class = lead_schedule.ToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class TagScheduleGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = TagSchedule.objects.all()
    serializer_class = lead_schedule.TagScheduleSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class TagScheduleDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = TagSchedule.objects.all()
    serializer_class = lead_schedule.TagScheduleSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleCheckListItemGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleCheckListItemDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleTodoMessageGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Messaging.objects.all().prefetch_related('todo_message_file')
    serializer_class = lead_schedule.MessagingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleTodoMessageDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Messaging.objects.all().prefetch_related('todo_message_file')
    serializer_class = lead_schedule.MessagingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class DailyLogGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = DailyLog.objects.all().prefetch_related('tags', 'to_dos')
    serializer_class = lead_schedule.DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = DailyLogFilter
    # search_fields = ['first_name', 'last_name', 'email', 'phone_contacts__phone_number']


class DailyLogDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = DailyLog.objects.all()
    serializer_class = lead_schedule.DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class DailyLogTemplateNoteGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = DailyLogTemplateNotes.objects.all()
    serializer_class = lead_schedule.DailyLogNoteSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class DailyLogTemplateNoteDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = DailyLogTemplateNotes.objects.all()
    serializer_class = lead_schedule.DailyLogNoteSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class DaiLyLogCommentGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = CommentDailyLog.objects.all().prefetch_related('attachment_daily_log_comment')
    serializer_class = lead_schedule.CommentDailyLogSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class DaiLyLogCommentDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = CommentDailyLog.objects.all().prefetch_related('attachment_daily_log_comment')
    serializer_class = lead_schedule.CommentDailyLogSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class CheckListItemGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class CheckListItemDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]

    def delete(self, request, *args, **kwargs):
        pk_checklist = kwargs.get('pk')
        checklist_item = CheckListItems.objects.get(pk=pk_checklist)
        uuid = checklist_item.uuid
        todo = checklist_item.to_do
        checklist_item_children = get_id_by_parent_checklist(uuid)
        checklist_item_template_children = get_id_by_parent_checklist_template(uuid)
        checklist_item_children = CheckListItems.objects.filter(to_do=todo.id, id__in=checklist_item_children)

        checklist_item_template = CheckListItemsTemplate.objects.filter(todo=todo.id, uuid=uuid,
                                                                        to_do_checklist_template=None)
        checklist_item_children_template = CheckListItemsTemplate.objects.filter(todo=todo.id,
                                                                                 id__in=checklist_item_template_children,
                                                                                 to_do_checklist_template=None)

        checklist_item.delete()
        checklist_item_children.delete()
        checklist_item_template.delete()
        checklist_item_children_template.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ToDoChecklistItemTemplateGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = TodoTemplateChecklistItem.objects.all()
    serializer_class = lead_schedule.ToDoCheckListItemsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ToDoChecklistItemTemplateDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = TodoTemplateChecklistItem.objects.all()
    serializer_class = lead_schedule.ToDoCheckListItemsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class TemplateChecklistItemGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = CheckListItemsTemplate.objects.all()
    serializer_class = lead_schedule.CheckListItemsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class TemplateChecklistItemDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = CheckListItemsTemplate.objects.all()
    serializer_class = lead_schedule.CheckListItemsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ToDoMessageCustomFieldGenericView(GenericViewSet):
    serializer_class = lead_schedule.MessageAndCustomFieldToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]

    def create_message_custom_field(self, request, **kwargs):
        serializer = lead_schedule.MessageAndCustomFieldToDoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        data_create = dict(serializer.validated_data)
        pk_todo = data_create['todo']
        todo = get_object_or_404(ToDo.objects.all(), pk=pk_todo)

        data_message = data_create['message']
        data_custom_field = data_create['custom_field']
        data_create_messaging = list()
        for message in data_message:
            rs_message = Messaging(
                message=message['message'],
                to_do=todo,
                user_create=user,
                user_update=user
            )
            data_create_messaging.append(rs_message)
        Messaging.objects.bulk_create(data_create_messaging)

        data_create_custom_field = list()
        for custom_field in data_custom_field:
            temp = TodoCustomField(
                custom_field=custom_field['custom_field'],
                todo=todo,
                label=custom_field['label'],
                data_type=custom_field['data_type'],
                required=custom_field['required'],
                include_in_filters=custom_field['include_in_filters'],
                display_order=custom_field['display_order'],
                tool_tip_text=custom_field['tool_tip_text'],
                show_owners=custom_field['show_owners'],
                allow_permitted_sub=custom_field['allow_permitted_sub'],
                value=custom_field['value'],
                value_date=custom_field['value_date'],
                value_checkbox=custom_field['value_checkbox'],
                value_number=custom_field['value_number'],
                user_create=user,
                user_update=user,

            )
            data_create_custom_field.append(temp)
        TodoCustomField.objects.bulk_create(data_create_custom_field)
        messaging = Messaging.objects.filter(to_do=pk_todo).values()
        rs_custom_field = TodoCustomField.objects.filter(todo=pk_todo).values()
        data_rs = {
            'todo': pk_todo,
            'message': messaging,
            'custom_field': rs_custom_field
        }
        rs = lead_schedule.MessageAndCustomFieldToDoCreateSerializer(
            data_rs, context={'request': request}).data

        return Response(status=status.HTTP_200_OK, data=rs)

    def update_message_custom_field(self, request, **kwargs):
        serializer = lead_schedule.MessageAndCustomFieldToDoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        data_create = dict(serializer.validated_data)
        pk_todo = data_create['todo']
        todo = get_object_or_404(ToDo.objects.all(), pk=pk_todo)

        data_message = data_create['message']
        data_custom_field = data_create['custom_field']

        for message in data_message:
            data_message = lead_schedule.Messaging.objects.filter(pk=message['id'])
            data_message.update(message=message['message'])

        TodoCustomField.objects.filter(todo=pk_todo).delete()
        data_create_custom_field = list()
        for custom_field in data_custom_field:
            temp = TodoCustomField(
                custom_field=custom_field['custom_field'],
                todo=todo,
                label=custom_field['label'],
                data_type=custom_field['data_type'],
                required=custom_field['required'],
                include_in_filters=custom_field['include_in_filters'],
                display_order=custom_field['display_order'],
                tool_tip_text=custom_field['tool_tip_text'],
                show_owners=custom_field['show_owners'],
                allow_permitted_sub=custom_field['allow_permitted_sub'],
                value=custom_field['value'],
                value_date=custom_field['value_date'],
                value_checkbox=custom_field['value_checkbox'],
                value_number=custom_field['value_number'],
                user_create=user,
                user_update=user,

            )
            data_create_custom_field.append(temp)
        TodoCustomField.objects.bulk_create(data_create_custom_field)
        messaging = Messaging.objects.filter(to_do=pk_todo).values()
        rs_custom_field = TodoCustomField.objects.filter(todo=pk_todo).values()
        data_rs = {
            'todo': pk_todo,
            'message': messaging,
            'custom_field': rs_custom_field
        }
        rs = lead_schedule.MessageAndCustomFieldToDoCreateSerializer(
            data_rs, context={'request': request}).data

        return Response(status=status.HTTP_200_OK, data=rs)


class ScheduleEventGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ScheduleEvent.objects.all().prefetch_related('assigned_user', 'viewing', 'tags', 'event_message', 'shift_event')
    serializer_class = lead_schedule.ScheduleEventSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = EventFilter
    # search_fields = ['first_name', 'last_name', 'email', 'phone_contacts__phone_number']


class ScheduleEventDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEvent.objects.all()
    serializer_class = lead_schedule.ScheduleEventSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventShiftReasonGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = EventShiftReason.objects.all()
    serializer_class = lead_schedule.ScheduleEventShiftReasonSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventShiftReasonDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = EventShiftReason.objects.all()
    serializer_class = lead_schedule.ScheduleEventShiftReasonSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleShiftReasonGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ShiftReason.objects.all()
    serializer_class = lead_schedule.ShiftReasonSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleShiftReasonDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ShiftReason.objects.all()
    serializer_class = lead_schedule.ShiftReasonSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleToDoCustomFieldGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = CustomFieldScheduleSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleSettingSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleToDoCustomFieldDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomFieldScheduleSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleSettingSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleToDoSettingGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ScheduleToDoSetting.objects.all()
    serializer_class = lead_schedule.ScheduleToDoSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleToDoSettingDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleToDoSetting.objects.all()
    serializer_class = lead_schedule.ScheduleToDoSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleDailyLogSettingGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.ScheduleDailyLogSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleDailyLogSettingDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.ScheduleDailyLogSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleDailyLogCustomFieldSettingGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = CustomFieldScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleDailyLogSettingSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleDailyLogCustomFieldSettingDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomFieldScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleDailyLogSettingSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventSettingGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ScheduleEventSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventSettingDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEventSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventPhaseSettingGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ScheduleEventPhaseSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventPhaseSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventPhaseSettingDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEventPhaseSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventPhaseSettingSerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventMessageGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = MessageEvent.objects.all().prefetch_related('file_message_event')
    serializer_class = lead_schedule.MessageEventSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleEventMessageDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = MessageEvent.objects.all().prefetch_related('file_message_event')
    serializer_class = lead_schedule.MessageEventSerialized
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleSetUpWorkDayGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = SetupWorkDay.objects.all().prefetch_related('setup_workday_holiday')
    serializer_class = lead_schedule.ScheduleSetupWordDaySerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


class ScheduleSetUpWorkDayDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = SetupWorkDay.objects.all().prefetch_related('setup_workday_holiday')
    serializer_class = lead_schedule.ScheduleSetupWordDaySerializer
    permission_classes = [permissions.IsAuthenticated & SchedulePermissions]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def get_checklist_by_todo(request, *args, **kwargs):
    pk_todo = kwargs.get('pk_todo')
    get_object_or_404(ToDo.objects.all(), pk=pk_todo)
    data_checklist = CheckListItems.objects.filter(to_do=pk_todo)
    data = lead_schedule.ToDoChecklistItemSerializer(
        data_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def get_checklist_template_by_todo(request, *args, **kwargs):
    user_create = user_update = request.user
    pk_todo = kwargs.get('pk_todo')
    get_object_or_404(ToDo.objects.all(), pk=pk_todo)
    data_checklist = CheckListItemsTemplate.objects.filter(todo=pk_todo, to_do_checklist_template=None)
    if not data_checklist:
        data_checklist = CheckListItems.objects.filter(to_do=pk_todo)
        for checklist_item in data_checklist:
            checklist_item_template = CheckListItemsTemplate.objects.create(
                user_create=user_create, user_update=user_update,
                uuid=checklist_item.uuid,
                parent_uuid=checklist_item.parent_uuid,
                description=checklist_item.description,
                is_check=checklist_item.is_check,
                is_root=checklist_item.is_root,
                todo_id=pk_todo
            )
            checklist_item_template.assigned_to.add(*checklist_item.assigned_to.all())

            data_file = FileCheckListItems.objects.filter(checklist_item=checklist_item.id)
            file_checklist_item_template_create = list()
            for file in data_file:
                attachment_template = FileCheckListItemsTemplate(
                    file=file.file,
                    checklist_item_template=checklist_item_template,
                    user_update=user_update
                )
                file_checklist_item_template_create.append(attachment_template)
            FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
        data_checklist = CheckListItemsTemplate.objects.filter(todo=pk_todo, to_do_checklist_template=None)
        data = lead_schedule.CheckListItemsTemplateSerializer(
            data_checklist, many=True, context={'request': request}).data
        Response(status=status.HTTP_200_OK, data=data)

    data = lead_schedule.CheckListItemsTemplateSerializer(
        data_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def select_checklist_template(request, *args, **kwargs):
    user_create = user_update = request.user
    pk_template = kwargs.get('pk_template')
    pk_todo = kwargs.get('pk_todo')
    get_object_or_404(ToDo.objects.all(), pk=pk_todo)
    CheckListItems.objects.filter(to_do=pk_todo).delete()
    CheckListItemsTemplate.objects.filter(todo=pk_todo, to_do_checklist_template=None).delete()
    data_checklist = CheckListItemsTemplate.objects.filter(to_do_checklist_template=pk_template)
    for checklist in data_checklist:
        temp = dict()
        temp['uuid'] = checklist.uuid
        temp['parent_uuid'] = checklist.parent_uuid
        temp['description'] = checklist.description
        temp['is_check'] = checklist.is_check
        temp['is_root'] = checklist.is_root

        checklist_item_create = CheckListItems.objects.create(
            user_create=user_create, user_update=user_update,
            to_do_id=pk_todo, **temp
        )
        checklist_item_create.assigned_to.add(*checklist.assigned_to.all())
        checklist_item_template = CheckListItemsTemplate.objects.create(
            user_create=user_create, user_update=user_update,
            todo_id=pk_todo, **temp
        )
        checklist_item_template.assigned_to.add(*checklist.assigned_to.all())
        data_file = FileCheckListItemsTemplate.objects.filter(checklist_item_template=checklist.id)
        file_checklist_item_create = list()
        file_checklist_item_template_create = list()
        for file in data_file:
            attachment = FileCheckListItems(
                file=file.file,
                checklist_item=checklist_item_create,
                user_update=user_update
            )
            attachment_template = FileCheckListItemsTemplate(
                file=file.file,
                checklist_item_template=checklist_item_template,
                user_update=user_update
            )
            file_checklist_item_create.append(attachment)
            file_checklist_item_template_create.append(attachment_template)
        FileCheckListItems.objects.bulk_create(file_checklist_item_create)
        FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)

    rs_checklist = CheckListItems.objects.filter(to_do=pk_todo)
    rs = lead_schedule.ToDoChecklistItemSerializer(
        rs_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def select_event_predecessors(request, *args, **kwargs):
    rs = ScheduleEvent.objects.filter(company=request.user.company.id).values('id', 'is_after', 'is_before', 'due_days', 'start_day', 'end_day', name=Lower('event_title'))
    rs = EventLinkSerializer(
        rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def select_event_link(request, *args, **kwargs):
    event_id = kwargs.get('pk')
    list_id = get_id_by_group(event_id)
    list_id.append(event_id)
    rs = ScheduleEvent.objects.exclude(id__in=list_id, company=request.user.company.id).values('id', name=Lower('event_title'))
    # rs = ScheduleEvent.objects.exclude(id__in=list_id).annotate(
    #     name=Subquery(ScheduleEvent.objects.exclude(id__in=list_id).values('event_title')[:1])
    # )
    rs = IDAndNameSerializer(
        rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def select_lead_list(request, *args, **kwargs):
    rs = LeadDetail.objects.filter(company=request.user.company.id).values('id', name=Lower('lead_title'))
    rs = IDAndNameSerializer(
        rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_custom_field(request, *args, **kwargs):
    custom_field_id = kwargs.get('pk')
    todo_list = request.data
    temp = [data['id'] for data in todo_list]
    custom_field_setting = CustomFieldScheduleSetting.objects.filter(id=custom_field_id)
    todo_custom_field = TodoCustomField.objects.filter(todo__in=temp, custom_field=custom_field_id)
    todo_custom_field.delete()
    custom_field_setting.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_custom_field_daily_log(request, *args, **kwargs):
    custom_field_id = kwargs.get('pk')
    daily_log_list = request.data
    temp = [data['id'] for data in daily_log_list]
    custom_field_setting = CustomFieldScheduleDailyLogSetting.objects.filter(id=custom_field_id)
    daily_log_custom_field = DailyLogCustomField.objects.filter(daily_log__in=temp, custom_field=custom_field_id)
    daily_log_custom_field.delete()
    custom_field_setting.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_phase(request, *args, **kwargs):
    phase_id = kwargs.get('pk')
    event_list = request.data
    temp = [data['id'] for data in event_list]
    phase_setting = ScheduleEventPhaseSetting.objects.filter(id=phase_id)
    model_event_phase = ScheduleEvent.objects.filter(id__in=temp, phase_setting=phase_id)
    update_list = []
    for phase in model_event_phase:
        phase.phase_label = None
        phase.phase_display_order = None
        phase.phase_color = None
        phase.phase_setting = None
        update_list.append(phase)
    ScheduleEvent.objects.bulk_update(update_list, ['phase_label', 'phase_display_order', 'phase_color', 'user_create',
                                                    'phase_setting', 'user_update'])
    phase_setting.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def select_checklist_item_template(request, pk_template, pk_todo):
    data_checklist = CheckListItemsTemplate.objects.filter(to_do_checklist_template=pk_template)
    for checklist in data_checklist:
        temp = dict()
        temp['uuid'] = checklist.uuid
        temp['parent_uuid'] = checklist.parent_uuid
        temp['description'] = checklist.description
        temp['is_check'] = checklist.is_check
        temp['is_root'] = checklist.is_root

        checklist_item_template = CheckListItemsTemplate.objects.create(
            todo_id=pk_todo, **temp
        )
        checklist_item_template.assigned_to.add(*checklist.assigned_to.all())
        data_file = FileCheckListItemsTemplate.objects.filter(checklist_item_template=checklist.id)
        file_checklist_item_template_create = list()
        for file in data_file:
            attachment_template = FileCheckListItemsTemplate(
                file=file.file,
                checklist_item_template=checklist_item_template,

            )
            file_checklist_item_template_create.append(attachment_template)
        FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
    rs_checklist = CheckListItems.objects.filter(to_do=pk_todo)
    rs = lead_schedule.ToDoChecklistItemSerializer(
        rs_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def filter_event(request, *args, **kwargs):
    data = request.query_params
    start_day = datetime.datetime.fromisoformat(data['start_day'])
    end_day = datetime.datetime.fromisoformat(data['end_day'])

    start_day = start_day.astimezone(pytz.UTC)
    end_day = end_day.astimezone(pytz.UTC)
    rs_event = ScheduleEvent.objects.filter(Q(start_day__gte=start_day, end_day__lte=end_day, company=request.user.company.id)
                                            | Q(end_day__gte=start_day, end_day__lte=end_day, company=request.user.company.id)
                                            | Q(start_day__gte=start_day, start_day__lte=end_day, company=request.user.company.id))
    event = lead_schedule.ScheduleEventSerializer(
        rs_event, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=event)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def get_event_of_day(request, *args, **kwargs):
    data = request.query_params
    start_day = datetime.strptime(data['day'], '%Y-%m-%d %H:%M:%S')
    time_obj = datetime.strptime(data['day'], '%Y-%m-%d %H:%M:%S')
    end_of_day = time_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
    delta = end_of_day - time_obj
    end_day = time_obj + delta

    rs_event = ScheduleEvent.objects.filter(Q(start_day__startswith=start_day.date(), end_day__gte=end_day, company=request.user.company.id)
                                            | Q(start_day__lte=start_day, end_day__startswith=end_day.date(), company=request.user.company.id)
                                            | Q(start_day__lte=start_day, end_day__gte=end_day, company=request.user.company.id)
                                            )
    event = lead_schedule.ScheduleEventSerializer(
        rs_event, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=event)


def get_id_by_group(pk):
    rs = []
    event = ScheduleEvent.objects.filter(predecessor=pk)
    for e in event:
        rs.append(e.id)
        rs.extend(get_id_by_group(e.id))
    return rs


def get_id_by_parent_checklist(pk):
    rs = []
    checklist = CheckListItems.objects.filter(parent_uuid=pk)
    for e in checklist:
        rs.append(e.id)
        rs.extend(get_id_by_parent_checklist(e.uuid))
    return rs


def get_id_by_parent_checklist_template(pk):
    rs = []
    checklist = CheckListItemsTemplate.objects.filter(parent_uuid=pk)
    for e in checklist:
        rs.append(e.id)
        rs.extend(get_id_by_parent_checklist_template(e.uuid))
    return rs


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_file_todo_checklist_item(request, *args, **kwargs):
    file_id = kwargs.get('pk')
    pk_checklist = kwargs.get('pk_checklist')
    checklist_item = lead_schedule.CheckListItems.objects.get(pk=pk_checklist)
    checklist_item_template = lead_schedule.CheckListItemsTemplate.objects.filter(todo=checklist_item.to_do,
                                                                                  uuid=checklist_item.uuid,
                                                                                  to_do_checklist_template=None).first()
    file_checklist = FileCheckListItems.objects.filter(pk=file_id)
    file_checklist_template = FileCheckListItemsTemplate.objects.filter(
        checklist_item_template=checklist_item_template.id)
    file_checklist.delete()
    file_checklist_template.delete()

    data_file = FileCheckListItems.objects.filter(checklist_item=checklist_item.id)
    file_checklist_item_template_create = list()
    for file in data_file:
        attachment_template = FileCheckListItemsTemplate(
            file=file.file,
            checklist_item_template=checklist_item_template,
            name=file.name
        )
        file_checklist_item_template_create.append(attachment_template)
    FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_file_todo(request, *args, **kwargs):
    file_id = kwargs.get('pk')
    data_attachments = Attachments.objects.filter(pk=file_id)
    data_attachments.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_file_daily_log(request, *args, **kwargs):
    file_id = kwargs.get('pk')
    data_attachments = AttachmentDailyLog.objects.filter(pk=file_id)
    data_attachments.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_file_event(request, *args, **kwargs):
    file_id = kwargs.get('pk')
    data_attachments = FileScheduleEvent.objects.filter(pk=file_id)
    data_attachments.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_file_checklist_template(request, *args, **kwargs):
    file_id = kwargs.get('pk')
    data_attachments = FileCheckListItemsTemplate.objects.filter(pk=file_id)
    data_attachments.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_event(request):
    """
        DELETE: delete multiple event
    """

    if request.method == 'DELETE':
        ids = request.data
        event = ScheduleEvent.objects.filter(id__in=ids)
        event.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_todo(request):
    """
        DELETE: delete multiple to_do
    """

    if request.method == 'DELETE':
        ids = request.data
        todo = ToDo.objects.filter(id__in=ids)
        todo.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_daily_log(request):
    """
        DELETE: delete multiple daily log
    """

    if request.method == 'DELETE':
        ids = request.data
        daily_log = DailyLog.objects.filter(id__in=ids)
        daily_log.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & SchedulePermissions])
def delete_template_daily_log(request):
    """
        DELETE: delete multiple daily log template
    """

    if request.method == 'DELETE':
        ids = request.data
        daily_log_template = DailyLogTemplateNotes.objects.filter(id__in=ids)
        daily_log_template.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)