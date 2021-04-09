# -*- coding: utf-8 -*-
import sqlalchemy

from .compiler import *  # noqa

__version__ = "0.5.0.dev0"
VERSION = __version__
SQLALCHEMY_VERSION = sqlalchemy.__version__
