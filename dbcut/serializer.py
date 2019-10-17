# -*- coding: utf-8 -*-
from io import open

try:
    import ujson as json
except ImportError:
    import json


def to_json(data, **extra_kwargs):
    kwargs = {"ensure_ascii": False, "indent": 2}
    kwargs.update(extra_kwargs)
    return json.dumps(data, **kwargs)


def dump_json(data, filepath):
    """Serialize ``data`` as a JSON formatted stream to ``filepath``"""
    with open(filepath, "w", encoding="utf-8") as fd:
        fd.write(to_json(data))


def load_json(filepath):
    """Deserialize ``filepath`` to a Python object."""
    with open(filepath, "r", encoding="utf-8") as fd:
        return json.load(fd)
