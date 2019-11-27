# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import pprint
import sys
from io import open

import yaml

from .utils import create_directory, reraise

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "cache": os.path.expanduser("~/.cache/dbcut"),
    "log_level": 3,
    "log_file": ":stderr:",
    "log_format": "[%(levelname)8s] [%(asctime)s] [%(name)s]: %(message)s",
    "default_limit": 10,
    "default_backref_limit": 10,
    "default_backref_depth": 5,
    "default_join_depth": 5,
    "global_exclude": [],
}


class Configuration(dict):
    def __init__(self, filename, defaults=None):
        defaults = dict(DEFAULT_CONFIG)
        defaults.update(defaults or {})
        dict.__init__(self, defaults)
        self.load_file(filename)

    def load_file(self, filename):
        """Updates the values in the config from a config file.
        :param filename: the filename of the config.  This can either be an
            absolute filename or a filename relative to the root path.
        """
        try:
            conf = {}
            with open(filename, encoding="utf-8") as config_file:
                conf = yaml.safe_load(config_file.read())
            for k, v in conf.items():
                self[k] = v
        except IOError as e:
            e.strerror = "Unable to load configuration file (%s)" % e.strerror
            exc_type, exc_value, tb = sys.exc_info()
            reraise(exc_type, exc_value, tb.tb_next)

        self["cache"] = create_directory(self["cache"])
        if self.get("queries", None) is None:
            self["queries"] = []

    def __str__(self):
        return pprint.pprint(self)
