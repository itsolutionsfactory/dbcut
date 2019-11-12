# -*- coding: utf-8 -*-
import sys
from types import ModuleType


# lazy-loading module
class Module(ModuleType):
    """Automatically import objects from the modules."""

    __all_models__ = {}

    def register_new_model(self, model):
        model_name = model.__name__
        if model_name not in self.__all_models__:
            self.__all_models__[model_name] = model
        if model_name not in self.__all__:
            self.__all__.append(model_name)

    def __getattr__(self, name):
        if name in self.__all_models__:
            return self.__all_models__[name]
        return ModuleType.__getattribute__(self, name)

    def __dir__(self):
        """Just show what we want to show."""
        result = list(new_module.__all__)
        result.extend(("__file__", "__doc__", "__all__", "__name__", "__package__"))
        return result


# keep a reference to this module so that it's not garbage collected
old_module = sys.modules["dbcut.generated_models"]


# setup the new module and patch it into the dict of loaded modules
new_module = sys.modules["dbcut.generated_models"] = Module("dbcut.generated_models")
new_module.__dict__.update(
    {
        "__file__": __file__,
        "__package__": "dbcut.generated_models",
        "__doc__": __doc__,
        "__all__": [],
    }
)
