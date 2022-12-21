import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.viewsets import GenericViewSet
from ..models.lead_schedule import ToDo, TagSchedule, CheckListItems, Attachments, Messaging, DailyLog, \
    AttachmentDailyLog, DailyLogTemplateNotes, TodoTemplateChecklistItem, ScheduleEvent, CheckListItemsTemplate
from ..serializers import lead_schedule


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


# class FileChecklistGenericView(GenericViewSet):
#     serializer_class = lead_schedule.FileChecklistSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_queryset(self):
#         get_object_or_404(CheckListItems.objects.all(), pk=self.kwargs['pk_checklist'])
#         return FileCheckListItems.objects.filter(checklist_item=self.kwargs['pk_checklist'])
#
#     def create_file(self, request, **kwargs):
#         serializer = lead_schedule.FileChecklistSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = request.user
#         pk_checklist = self.kwargs.get('pk_checklist')
#         daily_log = get_object_or_404(CheckListItems.objects.all(), pk=self.kwargs['pk_checklist'])
#         file_checklist_item = FileCheckListItems.objects.filter(checklist_item=pk_checklist)
#         file_checklist_item.delete()
#         files = request.FILES.getlist('file')
#         file_checklist_item_create = list()
#         for file in files:
#             file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
#             content_file = ContentFile(file.read(), name=file_name)
#             file_checklist = FileCheckListItems(
#                 file=content_file,
#                 daily_log=daily_log,
#                 user_create=user
#             )
#             file_checklist_item_create.append(file_checklist)
#
#         FileCheckListItems.objects.bulk_create(file_checklist_item_create)
#
#         file_checklist = FileCheckListItems.objects.filter(checklist_item=pk_checklist)
#         data = lead_schedule.FileChecklistModelSerializer(
#             file_checklist, many=True, context={'request': request}).data
#         return Response(status=status.HTTP_200_OK, data=data)
#
#     def get_file(self, request, **kwargs):
#         get_object_or_404(CheckListItems.objects.all(), pk=self.kwargs['pk_checklist'])
#         data_file = FileCheckListItems.objects.filter(pk_checklist=self.kwargs['pk_checklist'])
#         data = lead_schedule.FileChecklistModelSerializer(
#             data_file, many=True, context={'request': request}).data
#         return Response(status=status.HTTP_200_OK, data=data)


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

        checklist_item_template = CheckListItemsTemplate.objects.filter(todo=todo.id, uuid=uuid, to_do_checklist_template=None)
        checklist_item_children_template = CheckListItemsTemplate.objects.filter(todo=todo.id, parent_uuid=uuid, to_do_checklist_template=None)

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


class ScheduleEventGenericView(generics.ListCreateAPIView):
    queryset = ScheduleEvent.objects.all()
    serializer_class = lead_schedule.ScheduleEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleEventDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleEvent.objects.all()
    serializer_class = lead_schedule.ScheduleEventSerializer
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
    data_checklist = list(CheckListItemsTemplate.objects.filter(todo=pk_todo, to_do_checklist_template=None))
    if not data_checklist:
        data_checklist = CheckListItems.objects.filter(to_do=pk_todo)
        for checklist_item in data_checklist:
            user = get_user_model().objects.filter(pk__in=[at.id for at in checklist_item.assigned_to.all()])
            checklist_item_template = CheckListItemsTemplate.objects.create(
                user_create=user_create, user_update=user_update,
                uuid=checklist_item.uuid,
                parent_uuid=checklist_item.parent_uuid,
                description=checklist_item.description,
                is_check=checklist_item.is_check,
                is_root=checklist_item.is_root,
                todo_id=pk_todo
            )
            checklist_item_template.assigned_to.add(*user)
        data_checklist = list(CheckListItemsTemplate.objects.filter(todo=pk_todo, to_do_checklist_template=None))
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

        user = get_user_model().objects.filter(pk__in=[at.id for at in checklist.assigned_to.all()])
        checklist_item_create = CheckListItems.objects.create(
            user_create=user_create, user_update=user_update,
            to_do_id=pk_todo, **temp
        )
        checklist_item_create.assigned_to.add(*user)
        checklist_item_template = CheckListItemsTemplate.objects.create(
            user_create=user_create, user_update=user_update,
            todo_id=pk_todo, **temp
        )
        checklist_item_template.assigned_to.add(*user)

    rs_checklist = CheckListItems.objects.filter(to_do=pk_todo)
    rs = lead_schedule.ToDoChecklistItemSerializer(
        rs_checklist, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)

