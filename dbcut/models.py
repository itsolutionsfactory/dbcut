# -*- coding: utf-8 -*-
from collections import OrderedDict

from sqlalchemy import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta, declared_attr
from sqlalchemy.orm.state import InstanceState

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

    def __to_dict__(self, excluded_keys=set()):
        return {
            key: getattr(self, key)
            for key in get_entity_loaded_propnames(self, excluded_keys)
        }

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


def get_entity_loaded_propnames(entity, excluded=()):
    """Get entity property names that are loaded (e.g. won't produce new
    queries)

    :param entity: SQLAlchemy entity
    :param excluded: List of excluded properties
    :returns: List of entity property names
    """
    ins = entity if isinstance(entity, InstanceState) else inspect(entity)
    columns = ins.mapper.column_attrs.keys() + ins.mapper.relationships.keys()
    keynames = set(columns)
    keynames -= set(excluded)
    # If the entity is not transient -- exclude unloaded keys
    # Transient entities won't load these anyway, so it's safe to include
    # all columns and get defaults
    if not ins.transient:
        keynames -= ins.unloaded

    # If the entity is expired -- reload expired attributes as well
    # Expired attributes are usually unloaded as well!
    if ins.expired:
        keynames |= ins.expired_attributes
    return sorted(keynames, key=lambda x: columns.index(x))
