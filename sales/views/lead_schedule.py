import uuid

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.viewsets import GenericViewSet
from ..models.lead_schedule import ToDo, TagSchedule, CheckListItems, Attachments, Messaging
from ..serializers import lead_schedule


class ScheduleAttachmentsGenericView(GenericViewSet):
    serializer_class = lead_schedule.ScheduleAttachmentsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(ToDo.objects.all(), pk=self.kwargs['pk_todo'])
        return Attachments.objects.filter(to_do=self.kwargs['pk_todo'])

    @staticmethod
    def create_file(request, **kwargs):
        serializer = lead_schedule.ScheduleAttachmentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        pk_todo = kwargs.get('pk_todo')
        todo = ToDo.objects.filter(id=pk_todo).first()
        data_attachments = Attachments.objects.filter(to_do=pk_todo)
        data_attachments.delete()
        if not todo:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='ToDo not found')
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
        attachments = list(Attachments.objects.filter(to_do=pk_todo).values())
        return Response(attachments)

    @staticmethod
    def get_file(request, **kwargs):
        pk_todo = kwargs.get('pk_todo')
        if not ToDo.objects.filter(pk=pk_todo).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST, data='ToDo not found')
        data_file = list(Attachments.objects.filter(to_do=pk_todo).values())
        return Response(data_file)


class SourceScheduleToDoGenericView(generics.ListCreateAPIView):
    queryset = ToDo.objects.all()
    serializer_class = lead_schedule.ToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ScheduleDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ToDo.objects.all()
    serializer_class = lead_schedule.ToDoCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        to_do_id = kwargs.get('pk')

        # DELETE CHECK LIST
        check_list = CheckListItems.objects.filter(to_do=to_do_id)
        check_list.delete()

        # DELETE ATTACHMENT
        attachments = Attachments.objects.filter(to_do=to_do_id)
        attachments.delete()

        # DELETE MESSAGING
        messaging = Messaging.objects.filter(to_do=to_do_id)
        messaging.delete()

        # DELETE TO_DO
        todo = ToDo.objects.filter(id=to_do_id)
        todo.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TagScheduleGenericView(generics.ListCreateAPIView):
    queryset = ToDo.objects.all()
    serializer_class = lead_schedule.TagScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]


class TagScheduleDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ToDo.objects.all()
    serializer_class = lead_schedule.TagScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
