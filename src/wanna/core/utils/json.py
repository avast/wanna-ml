from caseconverter import snakecase


def remove_nones(d):
    """
    Delete keys with the value ``None`` or `null` in a dictionary, recursively.

    """

    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            remove_nones(value)
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, dict):
                    remove_nones(v)
        else:
            del d[key]
            d[snakecase(key)] = value
    return d
