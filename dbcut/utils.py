# -*- coding: utf-8 -*-
# coding: utf8
import os
import sys
from collections import OrderedDict
from contextlib import contextmanager

from io import StringIO
from pptree import print_tree


@contextmanager
def redirect_stdout():
    stream = StringIO()
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield stream
    finally:
        sys.stdout = old_stdout


def tree_pretty_print(tree):
    with redirect_stdout() as stream:
        print_tree(tree)

    def flatten(node):
        yield node.name
        for child in node.children:
            yield from flatten(child)  # noqa

    flat = list(flatten(tree))

    return stream.getvalue() + "\n\n" + "Include %s tables\n" % len(flat)


def uncache_module(exclude):
    """Remove package modules from cache except excluded ones.
    On next import they will be reloaded.

    Args:
        exclude (iter<str>): Sequence of module paths.
    """
    pkgs = []
    for mod in exclude:
        pkg = mod.split(".", 1)[0]
        pkgs.append(pkg)

    to_uncache = []
    for mod in sys.modules:
        if mod in exclude:
            continue

        if mod in pkgs:
            to_uncache.append(mod)
            continue

        for pkg in pkgs:
            if mod.startswith(pkg + "."):
                to_uncache.append(mod)
                break

    for mod in to_uncache:
        del sys.modules[mod]


@contextmanager
def monkeypatched(owner, attr, value):
    """Monkey patch context manager.

    with patch(os, 'open', myopen):
        ...
    """
    old = getattr(owner, attr)
    setattr(owner, attr, value)
    try:
        yield getattr(owner, attr)
    finally:
        setattr(owner, attr, old)


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


class classproperty(object):
    """
    @property for @classmethod
    taken from http://stackoverflow.com/a/13624858
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def generate_valid_index_name(index, dialect):
    table_name = index.table.name
    columns_names = "_".join([cn.name for cn in index.columns])
    if index.unique:
        full_index_name = "%s_%s_unique_idx" % (table_name, columns_names)
    else:
        full_index_name = "%s_%s_idx" % (table_name, columns_names)
    return full_index_name


def aslist(generator):
    """A decorator to convert a generator into a list."""

    def wrapper(*args, **kwargs):
        return list(generator(*args, **kwargs))

    return wrapper


def create_directory(dir_path):
    absolute_dir_path = os.path.realpath(
        os.path.join(os.getcwd(), os.path.expanduser(dir_path))
    )
    if not os.path.exists(absolute_dir_path):
        os.makedirs(absolute_dir_path)
    return absolute_dir_path


class VoidObject(object):
    def __init__(*args, **kwargs):
        pass

    def __getattribute__(self, name):
        return lambda *args, **kwargs: self


def sorted_nested_dict(data):
    res = OrderedDict()
    for k, v in sorted(data.items()):
        if isinstance(v, dict):
            res[k] = sorted_nested_dict(v)
        elif isinstance(v, (list, tuple)):
            res[k] = sorted(v)
        else:
            res[k] = v
    return res
