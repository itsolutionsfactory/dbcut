# -*- coding: utf-8 -*-
from collections import OrderedDict

from sqlalchemy import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta, declared_attr

from .generated_models import register_new_model
from .utils import classproperty


class BaseModel(object):

    _db = None
    __table_args__ = {"sqlite_autoincrement": True}

    @classproperty
    def _table_info(cls):  # noqa
        info = OrderedDict()
        info["table_name"] = cls.__table__.name
        info["columns"] = sorted([column.key for column in cls.__table__.columns])
        return info

    @classproperty
    def _default_ordering(cls):  # noqa
        # Order by primary keys by default
        primary_key = getattr(cls.__table__, "primary_key", None)
        if primary_key is not None:
            ordering_list = [c.desc() for c in cls.__table__.primary_key.columns]
            return ordering_list

    @declared_attr
    def __mapper_args__(cls):  # noqa
        ordering_keys = cls._default_ordering
        return {"order_by": ordering_keys} if ordering_keys is not None else {}

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, inspect(self).identity)


class BaseDeclarativeMeta(DeclarativeMeta):
    def __new__(cls, name, bases, d):
        d["__module__"] = "dbcut.generated_models"
        c = DeclarativeMeta.__new__(cls, name, bases, d)
        register_new_model(c)
        return c

    def __init__(self, name, bases, d):
        super(BaseDeclarativeMeta, self).__init__(name, bases, d)
        if self._db is not None:
            self._db._model_class_registry[name] = self
