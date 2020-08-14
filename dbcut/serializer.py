# -*- coding: utf-8 -*-
import datetime
import decimal
import json
import uuid
from collections import OrderedDict
from io import open

import yaml
from sqlalchemy.orm import Query

from .utils import to_unicode


class JSONEncoder(json.JSONEncoder):
    """JSON Encoder class that handles conversion for a number of types not
    supported by the default json library, especially the sqlalchemy objects.

    :returns: object that can be converted to json
    """

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            if representation.endswith("+00:00"):
                representation = representation[:-6] + "Z"
            return to_unicode(representation)
        if isinstance(obj, (datetime.date, datetime.time)):
            return to_unicode(obj.isoformat())
        elif isinstance(obj, (decimal.Decimal)):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return to_unicode(obj)
        elif isinstance(obj, Query):
            return list(obj)
        elif isinstance(obj, bytes):
            return obj.decode()
        elif hasattr(obj, "tolist"):
            return obj.tolist()
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "__getitem__"):
            try:
                return dict(obj)
            except Exception:
                pass
        elif hasattr(obj, "__iter__"):
            return list(item for item in obj)
        return super(JSONEncoder, self).default(obj)


def to_json(data, **extra_kwargs):
    kwargs = {
        "ensure_ascii": False,
        "indent": 2,
        "separators": (",", ": "),
        "cls": JSONEncoder,
    }
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


def represent_ordereddict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode(u"tag:yaml.org,2002:map", value)


yaml.add_representer(OrderedDict, represent_ordereddict)


def dump_yaml(data):
    return yaml.dump(data, default_flow_style=False, indent=2)
