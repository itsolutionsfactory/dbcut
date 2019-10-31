# -*- coding: utf-8 -*-


class UndefinedError(Exception):
    def __init__(self, keyname):
        self.keyname = keyname

    def __str__(self):
        return self.message

    @property
    def message(self):
        return "%r is undefined" % self.keyname
