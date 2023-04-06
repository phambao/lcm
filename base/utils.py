import copy

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
    """
    Parameters:
        model: Model Class
        instance: object
        action: int
        serializer: Serializer Class
        next_state: dict
    """
    content_type = ContentType.objects.get_for_model(model)
    # disable logging data temporarily
    data = serializer(instance).data
    ActivityLog.objects.create(content_type=content_type, content_object=instance, object_id=instance.pk,
                               action=action, last_state=data, next_state=next_state)


def extra_kwargs_for_base_model():
    return {'created_date': {'read_only': True},
            'modified_date': {'read_only': True},
            'user_create': {'read_only': True},
            'user_update': {'read_only': True}}
