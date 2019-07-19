# -*- coding: utf-8 -*-
import os


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


def is_bytes(x):
    return isinstance(x, (bytes, memoryview, bytearray))


def to_unicode(obj, encoding="utf-8"):
    """
    Convert ``obj`` to unicode"""
    # unicode support
    if isinstance(obj, str):
        return obj

    # bytes support
    if is_bytes(obj):
        if hasattr(obj, "tobytes"):
            return str(obj.tobytes(), encoding)
        if hasattr(obj, "decode"):
            return obj.decode(encoding)
        else:
            return str(obj, encoding)

    # string support
    if isinstance(obj, (str, bytes)):
        if hasattr(obj, "decode"):
            return obj.decode(encoding)
        else:
            return str(obj, encoding)

    return str(obj)


def merge_dicts(*dict_args):
    """Merge given dicts into a new dict."""
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


class CachedProperty(object):
    """A property that is only computed once per instance and then replaces
    itself with an ordinary attribute. Deleting the attribute resets the
    property."""

    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        obj.__dict__.setdefault("_cache", {})
        cached_value = obj._cache.get(self.__name__, None)
        if cached_value is None:
            # don't cache None value
            obj._cache[self.__name__] = self.func(obj)
        return obj._cache.get(self.__name__)

    def __delete__(self, obj):
        cache_obj = getattr(obj, "_cache", {})
        if self.__name__ in cache_obj:
            del cache_obj[self.__name__]


cached_property = CachedProperty


def generate_valid_index_name(index, dialect):
    table_name = index.table.name
    columns_names = "_".join([cn.name for cn in index.columns])
    if index.unique:
        full_index_name = "%s_%s_unique_idx" % (table_name, columns_names)
    else:
        full_index_name = "%s_%s_idx" % (table_name, columns_names)
    return full_index_name


def create_directory(dir_path):
    absolute_dir_path = os.path.realpath(
        os.path.join(os.getcwd(), os.path.expanduser(dir_path))
    )
    if not os.path.exists(absolute_dir_path):
        os.makedirs(absolute_dir_path)
    return absolute_dir_path
