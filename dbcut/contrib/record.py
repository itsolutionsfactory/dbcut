import base64
import hashlib
import os
from enum import Enum

from sqlalchemy.ext import serializer as sa_serializer
from sqlalchemy.orm import Query

from ..serializer import dump_json, load_json
from ..utils import monkeypatched


class Recorder:
    def __init__(self, name, mode=None, output_dir=None):
        # load records
        self.name = name
        self.record_mode = mode or RecordMode.ONCE
        self.output_dir = output_dir or os.path.join(os.getcwd(), "dbcut_records")
        self.records = self.open()

        if self.record_mode == RecordMode.ALL:
            self.records.clear()

        self.patcher = self._patch_generator()

    @property
    def record_path(self):
        return "{}.json".format(os.path.join(self.output_dir, self.name))

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
        import sqlalchemy.orm.query

        CachingQuery.recorder = self
        CachingQuery.record_mode = self.record_mode
        CachingQuery.cached_keys = [r["key"] for r in self.records]
        CachingQuery.iter_count = 0

        with monkeypatched(sqlalchemy.orm.query, "Query", CachingQuery):
            with monkeypatched(sqlalchemy.orm, "Query", CachingQuery):
                yield

    def __enter__(self):
        next(self.patcher)

    def __exit__(self, *args):
        next(self.patcher, None)
        self.save()


class CachingQuery(Query):

    recorder = None
    record_mode = None
    cached_keys = []
    iter_count = 0

    def fetch_from_database(self):
        return list(super(CachingQuery, self).__iter__())

    def fetch_from_cache(self):
        record = self.recorder.load_record(self.cache_key)
        cached_value = sa_serializer.loads(base64.b64decode(record["data"]))
        return self.merge_result(cached_value, load=False)

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

        CachingQuery.iter_count += 1
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
            "statement": str(self.with_labels().statement.compile()),
            "params": self.with_labels().statement.compile().params,
            "iter_count": self.__class__.iter_count,
        }

    @property
    def cache_key(self):
        query_info = self.info
        unhashed_key = query_info["statement"] + str(query_info["iter_count"])
        return hashlib.sha1(unhashed_key.encode("utf-8")).hexdigest()

    def dump_record(self, objects):
        record = self.info.copy()
        record["key"] = self.cache_key
        record["data"] = base64.b64encode(sa_serializer.dumps(objects)).decode("utf-8")
        return record


class RecordMode(str, Enum):
    ALL = "ALL"
    ONCE = "ONCE"
    NONE = "NONE"
