def pop(data, key, default_type):
    """
    Same as get method and remove the key
    """
    try:
        return data.pop(key)
    except KeyError:
        pass
    return default_type
