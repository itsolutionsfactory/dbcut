from enum import Enum


class RecordMode(str, Enum):

    ALL = "ALL"
    ONCE = "ONCE"
    NONE = "NONE"
