import os
import uuid

from django.core.files.base import ContentFile
from rest_framework import views, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sales.models.lead_list import Photos
from sales.serializers.lead_list import PhotoSerializer


class FileUploadView(views.APIView):
    parser_classes = [MultiPartParser]
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        queryset = Photos.objects.all()
        serializer = PhotoSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        try:
            files = request.FILES.getlist('files')
        except KeyError:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "File not found"})
        photo_id = []
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)

            # is needed to bulk_create?
            photo = Photos.objects.create(photo=content_file, user_create=request.user,
                                          user_update=request.user)
            photo_id.append(photo.id)
        photos = Photos.objects.filter(pk__in=photo_id)
        serializer = PhotoSerializer(photos, many=True)

        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        ids = request.data.get('ids').split(',')
        if ids:
            queryset = Photos.objects.filter(id__in=ids)
            for photo in queryset:
                os.remove(photo.photo.path)
            queryset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
