import uuid

from django.core.files.base import ContentFile
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.serializers.base import IDAndNameSerializer
from base.utils import pop
from ..models import LeadDetail
from ..models.lead_schedule import ToDo, TagSchedule, CheckListItems, Attachments, DailyLog, \
    AttachmentDailyLog, DailyLogTemplateNotes, TodoTemplateChecklistItem, ScheduleEvent, CheckListItemsTemplate, \
    FileScheduleEvent, CustomFieldScheduleSetting, TodoCustomField, ScheduleToDoSetting, ScheduleDailyLogSetting, \
    CustomFieldScheduleDailyLogSetting, Messaging, ScheduleEventSetting, ScheduleEventPhaseSetting, DailyLogCustomField
from ..serializers import lead_schedule
from ..serializers.lead_schedule import ScheduleEventPhaseSettingSerializer


class ScheduleAttachmentsGenericView(GenericViewSet):
    serializer_class = lead_schedule.ScheduleAttachmentsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(ToDo.objects.all(), pk=self.kwargs['pk_todo'])
        return Attachments.objects.filter(to_do=self.kwargs['pk_todo'])

    def create_file(self, request, **kwargs):
        serializer = lead_schedule.ScheduleAttachmentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_todo = self.kwargs.get('pk_todo')
        todo = get_object_or_404(ToDo.objects.all(), pk=self.kwargs['pk_todo'])
        data_attachments = Attachments.objects.filter(to_do=pk_todo)
        data_attachments.delete()
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)

            attachment = Attachments(
                file=content_file,
                to_do=todo,
                user_create=user
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(DailyLog.objects.all(), pk=self.kwargs['pk_daily_log'])
        return AttachmentDailyLog.objects.filter(to_do=self.kwargs['pk_daily_log'])

    def create_file(self, request, **kwargs):
        serializer = lead_schedule.AttachmentsDailyLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_daily_log = self.kwargs.get('pk_daily_log')
        daily_log = get_object_or_404(DailyLog.objects.all(), pk=self.kwargs['pk_daily_log'])
        data_attachments = AttachmentDailyLog.objects.filter(daily_log=pk_daily_log)
        data_attachments.delete()
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = AttachmentDailyLog(
                file=content_file,
                daily_log=daily_log,
                user_create=user
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(ScheduleEvent.objects.all(), pk=self.kwargs['pk_event'])
        return FileScheduleEvent.objects.filter(event=self.kwargs['pk_event'])

    def create_file(self, request, **kwargs):
        serializer = lead_schedule.AttachmentsEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_event = self.kwargs.get('pk_event')
        data_event = get_object_or_404(ScheduleEvent.objects.all(), pk=self.kwargs['pk_event'])
        data_attachments = FileScheduleEvent.objects.filter(event=pk_event)
        data_attachments.delete()
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = FileScheduleEvent(
                file=content_file,
                event=data_event,
                user_create=user
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


class SourceScheduleToDoGenericView(generics.ListCreateAPIView):
    queryset = ToDo.objects.all()
    serializer_class = lead_schedule.ToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ToDo.objects.all()
    serializer_class = lead_schedule.ToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class TagScheduleGenericView(generics.ListCreateAPIView):
    queryset = TagSchedule.objects.all()
    serializer_class = lead_schedule.TagScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]


class TagScheduleDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TagSchedule.objects.all()
    serializer_class = lead_schedule.TagScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleCheckListItemGenericView(generics.ListCreateAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleCheckListItemDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailyLogGenericView(generics.ListCreateAPIView):
    queryset = DailyLog.objects.all()
    serializer_class = lead_schedule.DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailyLogDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DailyLog.objects.all()
    serializer_class = lead_schedule.DailyLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailyLogTemplateNoteGenericView(generics.ListCreateAPIView):
    queryset = DailyLogTemplateNotes.objects.all()
    serializer_class = lead_schedule.DailyLogNoteSerializer
    permission_classes = [permissions.IsAuthenticated]


class DailyLogTemplateNoteDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DailyLogTemplateNotes.objects.all()
    serializer_class = lead_schedule.DailyLogNoteSerializer
    permission_classes = [permissions.IsAuthenticated]


class CheckListItemGenericView(generics.ListCreateAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class CheckListItemDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CheckListItems.objects.all()
    serializer_class = lead_schedule.ToDoChecklistItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        pk_checklist = kwargs.get('pk')
        checklist_item = CheckListItems.objects.get(pk=pk_checklist)
        uuid = checklist_item.uuid
        todo = checklist_item.to_do
        checklist_item_children = CheckListItems.objects.filter(to_do=todo.id, parent_uuid=uuid)

        checklist_item_template = CheckListItemsTemplate.objects.filter(todo=todo.id, uuid=uuid,
                                                                        to_do_checklist_template=None)
        checklist_item_children_template = CheckListItemsTemplate.objects.filter(todo=todo.id, parent_uuid=uuid,
                                                                                 to_do_checklist_template=None)

        checklist_item.delete()
        checklist_item_children.delete()
        checklist_item_template.delete()
        checklist_item_children_template.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ToDoChecklistItemTemplateGenericView(generics.ListCreateAPIView):
    queryset = TodoTemplateChecklistItem.objects.all()
    serializer_class = lead_schedule.ToDoCheckListItemsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ToDoChecklistItemTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TodoTemplateChecklistItem.objects.all()
    serializer_class = lead_schedule.ToDoCheckListItemsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ToDoMessageCustomFieldGenericView(GenericViewSet):
    serializer_class = lead_schedule.MessageAndCustomFieldToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

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


class ScheduleEventGenericView(generics.ListCreateAPIView):
    queryset = ScheduleEvent.objects.all()
    serializer_class = lead_schedule.ScheduleEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleEventDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEvent.objects.all()
    serializer_class = lead_schedule.ScheduleEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleToDoCustomFieldGenericView(generics.ListCreateAPIView):
    queryset = CustomFieldScheduleSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleSettingSerialized
    permission_classes = [permissions.IsAuthenticated]


class ScheduleToDoCustomFieldDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomFieldScheduleSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleSettingSerialized
    permission_classes = [permissions.IsAuthenticated]


class ScheduleToDoSettingGenericView(generics.ListCreateAPIView):
    queryset = ScheduleToDoSetting.objects.all()
    serializer_class = lead_schedule.ScheduleToDoSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleToDoSettingDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleToDoSetting.objects.all()
    serializer_class = lead_schedule.ScheduleToDoSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleDailyLogSettingGenericView(generics.ListCreateAPIView):
    queryset = ScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.ScheduleDailyLogSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleDailyLogSettingDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.ScheduleDailyLogSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleDailyLogCustomFieldSettingGenericView(generics.ListCreateAPIView):
    queryset = CustomFieldScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleDailyLogSettingSerialized
    permission_classes = [permissions.IsAuthenticated]


class ScheduleDailyLogCustomFieldSettingDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomFieldScheduleDailyLogSetting.objects.all()
    serializer_class = lead_schedule.CustomFieldScheduleDailyLogSettingSerialized
    permission_classes = [permissions.IsAuthenticated]


class ScheduleEventSettingGenericView(generics.ListCreateAPIView):
    queryset = ScheduleEventSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleEventSettingDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEventSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleEventPhaseSettingGenericView(generics.ListCreateAPIView):
    queryset = ScheduleEventPhaseSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventPhaseSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleEventPhaseSettingDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEventPhaseSetting.objects.all()
    serializer_class = lead_schedule.ScheduleEventPhaseSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_checklist_by_todo(request, *args, **kwargs):
    pk_todo = kwargs.get('pk_todo')
    get_object_or_404(ToDo.objects.all(), pk=pk_todo)
    data_checklist = CheckListItems.objects.filter(to_do=pk_todo)
    data = lead_schedule.CheckListItemSerializer(
        data_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
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
        data_checklist = CheckListItemsTemplate.objects.filter(todo=pk_todo, to_do_checklist_template=None)
        data = lead_schedule.CheckListItemsTemplateSerializer(
            data_checklist, many=True, context={'request': request}).data
        Response(status=status.HTTP_200_OK, data=data)

    data = lead_schedule.CheckListItemsTemplateSerializer(
        data_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
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

    rs_checklist = CheckListItems.objects.filter(to_do=pk_todo)
    rs = lead_schedule.ToDoChecklistItemSerializer(
        rs_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def select_event_predecessors(request, *args, **kwargs):
    rs = ScheduleEvent.objects.all().values('id', name=Lower('event_title'))
    rs = IDAndNameSerializer(
        rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def select_event_link(request, *args, **kwargs):
    event_id = kwargs.get('pk')
    list_id = get_id_by_group(event_id)
    list_id.append(event_id)
    rs = ScheduleEvent.objects.exclude(id__in=list_id).values('id', name=Lower('event_title'))
    # rs = ScheduleEvent.objects.exclude(id__in=list_id).annotate(
    #     name=Subquery(ScheduleEvent.objects.exclude(id__in=list_id).values('event_title')[:1])
    # )
    rs = IDAndNameSerializer(
        rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def select_lead_list(request, *args, **kwargs):
    rs = LeadDetail.objects.all().values('id', name=Lower('lead_title'))
    rs = IDAndNameSerializer(
        rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
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
@permission_classes([permissions.IsAuthenticated])
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
@permission_classes([permissions.IsAuthenticated])
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


def get_id_by_group(pk):
    rs = []
    event = ScheduleEvent.objects.filter(predecessor=pk)
    for e in event:
        rs.append(e.id)
        rs.extend(get_id_by_group(e.id))
    return rs
