# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class DBCutException(Exception):
    pass


class InvalidOperatorError(DBCutException):
    pass


class InvalidComparatorError(DBCutException):
    pass


class QuerySyntaxError(DBCutException):
    pass


class InvalidTableError(DBCutException):
    pass


class InvalidFieldError(DBCutException):
    pass


class InvalidConfiguration(DBCutException):
    pass


class DatabaseError(DBCutException):
    pass


class DoesNotExist(DBCutException):
    pass
