from rest_framework import views, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sales.models.lead_list import Photos
from sales.serializers.lead_list import PhotoSerializer
from django.core.files.base import ContentFile
from knox.auth import TokenAuthentication
import uuid


class FileUploadView(views.APIView):
    parser_classes = [MultiPartParser]
    authentication_classes = [TokenAuthentication]
    permission_classes = (IsAuthenticated,)

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
