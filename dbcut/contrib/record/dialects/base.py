# -*- coding: utf-8 -*-
from contextlib import contextmanager


class BaseDialect(object):
    def do_execute(self, cursor, statement, parameters, context=None):
        # This is our own Base Dialect that overwrite all SQLALchemy dialects
        return super(BaseDialect, self).do_execute(
            cursor, statement, parameters, context
        )


@contextmanager
def patched_sqlalchemy_dialects():
    registry.clear()
    for key in get_all_dialects():
        sa_dialect_name = "_".join(key.split("."))
        registry.register(
            key,
            "dbcut.contrib.record.dialects.patched",
            "BaseDialect_{}".format(sa_dialect_name),
        )
    yield
    registry.clear()


def get_all_dialects():
    """
    iterate over the modules in sqlalchemy.dialects packages and modules
    Return a list of modules of all subclasses of DefaultDialect.
    """
    pkg = sqlalchemy.dialects
    default_dialects = []
    for loader, module_name, is_pkg in pkgutil.iter_modules(pkg.__path__):
        if is_pkg:
            module = importlib.import_module("sqlalchemy.dialects." + module_name)
            for name, cls in module.__dict__.items():
                if isinstance(cls, type):
                    if issubclass(cls, DefaultDialect):
                        default_dialects.append(".".join(cls.__module__.split(".")[2:]))

    return default_dialects
