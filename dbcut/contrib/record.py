import hashlib
import os
import base64
from enum import Enum

from mock import patch
from contextlib import contextmanager

from sqlalchemy.ext import serializer as sa_serializer
from sqlalchemy.orm import Query

from dbcut.serializer import dump_json, load_json, to_json
from dbcut.utils import sorted_nested_dict
from dbcut.query import render_query


class Recorder:
    def __init__(self, name, mode=None, output_dir=None):
        # load records
        self.name = name
        self.record_mode = mode or RecordMode.ONCE
        self.output_dir = output_dir or os.path.join(os.getcwd(), "db-records")
        self.records = self.open()

        if self.record_mode == RecordMode.ALL:
            self.records.clear()

        data_members = {
            "recorder": self,
            "record_mode": self.record_mode,
            "cached_keys": [r["key"] for r in self.records],
            "iter_count": 0,
        }

        self.query_class = type("CachingQuery", (BaseCachingQuery,), data_members)
        self.patcher = self._patch_generator()

    @property
    def record_path(cls):
        return "{}.json".format(os.path.join(cls.output_dir, cls.name))

    def open(self):
        if os.path.exists(self.record_path):
            return load_json(self.record_path)
        return []

    def save(self):
        if self.records:
            output_dir = os.path.dirname(self.record_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            dump_json(self.records, self.record_path)

    def load_record(self, key):
        for record in self.records:
            if record["key"] == key:
                return record

    def _patch_generator(self):
        with patch("sqlalchemy.orm.query.Query", self.query_class):
            with patch("sqlalchemy.orm.Query", self.query_class):
                yield

    def __enter__(self):
        next(self.patcher)

    def __exit__(self, *args):
        next(self.patcher, None)
        self.save()


class BaseCachingQuery(Query):
    def fetch_from_database(self):
        return list(super(BaseCachingQuery, self).__iter__())

    def fetch_from_cache(self):
        record = self.recorder.load_record(self.cache_key)
        return sa_serializer.loads(base64.b64decode(record["data"]))

    def __iter__(self):
        if self.cache_key in self.cached_keys:
            objects = self.fetch_from_cache()
        else:
            if self.write_protected:
                raise Exception(
                    "Cannot overwrite existing record '{}'".format(self.recorder.name)
                )
            objects = self.fetch_from_database()
            self.recorder.records.append(self.dump_record(objects))

        self.__class__.iter_count += 1
        return iter(objects)

    @property
    def write_protected(self):
        return (
            len(self.cached_keys) and self.record_mode == RecordMode.ONCE
        ) or self.record_mode == RecordMode.NONE

    @property
    def info(self):
        return {
            "engine_info": self.session.bind.url.__to_string__(),
            "statement": render_query(self),
            "tables": list(set([t.name for t in self.selectable.locate_all_froms()])),
            "iter_count": self.__class__.iter_count,
        }

    @property
    def cache_key(self):
        return hashlib.sha1(
            to_json(sorted_nested_dict(self.info)).encode("utf-8")
        ).hexdigest()

    def dump_record(self, objects):
        record = self.info.copy()
        record["key"] = self.cache_key
        record["data"] = base64.b64encode(sa_serializer.dumps(objects)).decode("utf-8")
        return record


class RecordMode(str, Enum):
    ALL = "ALL"
    ONCE = "ONCE"
    NONE = "NONE"
