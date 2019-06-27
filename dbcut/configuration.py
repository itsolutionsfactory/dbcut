# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import pprint
import sys

import yaml
from io import open

from .compat import reraise
from .helpers import create_directory

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    "queries": [],
    "convert_unicode": True,
    "echo": False,
    "cache": os.path.expanduser("~/.cache/dbcut"),
    "log_level": 3,
    "log_file": ":stderr:",
    "log_format": "[%(levelname)8s] [%(asctime)s] [%(name)s]: %(message)s",
}


class Configuration(dict):
    def __init__(self, filename, defaults=None):
        defaults = dict(DEFAULT_CONFIG)
        defaults.update(defaults or {})
        dict.__init__(self, defaults)
        self.load_file(filename)

    def load_file(self, filename, silent=False):
        """Updates the values in the config from a config file.
        :param filename: the filename of the config.  This can either be an
            absolute filename or a filename relative to the root path.
        :param silent: If True, fail silently.
        """
        try:
            conf = {}
            with open(filename, encoding="utf-8") as config_file:
                conf = yaml.safe_load(config_file.read())
            for k, v in conf.items():
                self[k] = v
        except IOError as e:
            e.strerror = "Unable to load configuration file (%s)" % e.strerror
            if silent:
                logger.warning(e.strerror)
                return False
            else:
                exc_type, exc_value, tb = sys.exc_info()
                reraise(exc_type, exc_value, tb.tb_next)
        self["cache"] = create_directory(self["cache"])

        return True

    def __str__(self):
        return pprint.pprint(self)
