import sys


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
