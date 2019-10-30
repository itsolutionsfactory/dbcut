# -*- coding: utf-8 -*-
from collections import OrderedDict

import yaml
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


def represent_ordereddict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)

yaml.add_representer(OrderedDict, represent_ordereddict)


def dump_yaml(data):
    return yaml.dump(data, default_flow_style=False, indent=2)
