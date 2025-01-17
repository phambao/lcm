from datetime import datetime
import io
import sys

from django.http import FileResponse
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


def pop(data, key, default_type):
    """
    Same as get method and remove the key
    """
    try:
        return data.pop(key) or default_type
    except KeyError:
        pass
    return default_type


def extra_kwargs_for_base_model():
    return {'created_date': {'read_only': True},
            'modified_date': {'read_only': True},
            'user_create': {'read_only': True},
            'user_update': {'read_only': True},
            'company': {'read_only': True}}


def str_to_class(base_path, classname):
    return getattr(sys.modules[base_path], classname)


def file_response(workbook, title):
    workbook.remove(workbook['Sheet'])
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{title}_{current_datetime}.xlsx"
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename=filename)


def get_perm_by_models(models):
    perms = Permission.objects.none()
    for model in models:
        content_type = ContentType.objects.get_for_model(model)
        perms |= Permission.objects.filter(content_type=content_type)
    return perms
