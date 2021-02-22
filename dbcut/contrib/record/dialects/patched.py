# -*- coding: utf-8 -*-
import sys
from types import ModuleType


# lazy-loading module
class Module(ModuleType):
    """Automatically import objects from the modules."""

    def __getattr__(self, name):

        if "BaseDialect" in name:
            from sqlalchemy.dialects import _auto_fn

            from .base import BaseDialect

            sa_dialect_name = ".".join(name.split("_")[1:])
            sa_dialect_class = _auto_fn(sa_dialect_name)()
            return type(name, (BaseDialect, sa_dialect_class), {})

        return ModuleType.__getattribute__(self, name)

    def __dir__(self):
        """Just show what we want to show."""
        result = list(new_module.__all__)
        result.extend(("__file__", "__doc__", "__all__", "__name__", "__package__"))
        return result


# keep a reference to this module so that it's not garbage collected
old_module = sys.modules["dbcut_record.dialects.patched"]


# setup the new module and patch it into the dict of loaded modules
new_module = sys.modules["dbcut_record.dialects.patched"] = Module(
    "dbcut_record.dialects.patched"
)
new_module.__dict__.update(
    {
        "__file__": __file__,
        "__package__": "dbcut_record.dialects.patched",
        "__doc__": __doc__,
        "__all__": [],
    }
)
