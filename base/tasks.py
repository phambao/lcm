from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.http import HttpRequest

from api.middleware import set_request
from api.models import ActivityLog
from base.utils import str_to_class


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
