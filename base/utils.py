from django.contrib.contenttypes.models import ContentType

from api.models import ActivityLog


def pop(data, key, default_type):
    """
    Same as get method and remove the key
    """
    try:
        return data.pop(key) or default_type
    except KeyError:
        pass
    return default_type


def activity_log(model, instance, action, serializer, next_state):
    content_type = ContentType.objects.get_for_model(model)
    data = serializer(instance).data
    ActivityLog.objects.create(content_type=content_type, content_object=instance,
                               action=action, last_state=data, next_state=next_state)
