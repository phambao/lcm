from datetime import datetime
from io import BytesIO

from celery import shared_task, current_task
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.http import HttpRequest
from django.core.files.base import ContentFile
from openpyxl.workbook import Workbook

from api.middleware import set_request
from api.models import ActivityLog
from base.models.config import FileBuilder365
from base.utils import str_to_class
from sales.models import Catalog


@shared_task()
def process_export_catalog(pk, company, user_id):
    from sales.views.catalog import handle_export
    workbook = Workbook()
    task_id = current_task.request.id
    if pk is None:
        data_catalog = Catalog.objects.filter(is_ancestor=True, parents=None, company=company)
        for catalog in data_catalog:
            child_catalogs = Catalog.objects.filter(parents=catalog.id)
            for data_catalog in child_catalogs:
                handle_export(data_catalog.id, workbook, catalog.name)

    else:
        check_catalog = Catalog.objects.get(id=pk)
        if check_catalog.is_ancestor:
            child_catalogs = Catalog.objects.filter(parents=pk)
            for data_catalog in child_catalogs:
                handle_export(data_catalog.id, workbook, check_catalog.name)

        else:
            data_parent_catalog = check_catalog.parents.first()
            handle_export(pk, workbook, data_parent_catalog.name)

    default_sheet = workbook.active
    workbook.remove(default_sheet)
    bytes_io = BytesIO()
    workbook.save(bytes_io)
    bytes_io.seek(0)

    content = ContentFile(bytes_io.read())
    content.seek(0)

    attachment = FileBuilder365()
    user = get_user_model().objects.get(pk=user_id)
    request = HttpRequest()
    request.user = user
    set_request(request)

    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"catalog_{current_datetime}.xlsx"
    attachment.file.save(filename, content)
    attachment.size = content.size
    attachment.name = filename
    attachment.task_id = task_id
    attachment.save()


@shared_task()
def celery_send_mail(subject, message, from_email, recipient_list,
                     fail_silently=False, auth_user=None, auth_password=None,
                     connection=None, html_message=None):
    send_mail(subject, message, from_email, recipient_list,
              fail_silently=fail_silently, auth_user=auth_user, auth_password=auth_password,
              connection=connection, html_message=html_message)


@shared_task()
def activity_log(model, instance, action, serializer_name, base_import_file, user_id):
    """
    Parameters:
        model: int
        instance: pk
        action: int
        serializer_name: str
        base_import_file: str
    """
    user = get_user_model().objects.get(pk=user_id)
    request = HttpRequest()
    request.user = user
    set_request(request)

    content_type = ContentType.objects.get_for_id(model)
    model_class = content_type.model_class()
    instance = model_class.objects.get(pk=instance)
    serializer = str_to_class(base_import_file, serializer_name)
    data = serializer(instance).data
    ActivityLog.objects.create(content_type=content_type, content_object=instance, object_id=instance.pk,
                               action=action, last_state=data, next_state={})
