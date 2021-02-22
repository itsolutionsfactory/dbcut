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

class Recorder:
    def __init__(self, name, mode, output_dir):
        # load records
        records = []

        data_members = {
            "name": name,
            "mode": mode or RecordMode.ONCE,
            "serializer": JsonSerializer,
            "records": records,
            "already_loaded": True,
            "output_dir": output_dir,
            "last_cache_key": "",
        }
        self.query_class = type("CachingQuery", (BaseCachingQuery,), data_members)
        self.patcher = self._patch_generator()

    def _patch_generator(self):
        with patch('sqlalchemy.orm.query.Query', self.query_class):
            with patch('sqlalchemy.orm.Query', self.query_class):
                yield

    def __enter__(self):
        next(self.patcher)

    def __exit__(self, *args):
        next(self.patcher, None)
        self.query_class.save()


class BaseCachingQuery(Query):
    def __iter__(self):

        if self.name is None:
            raise RuntimeError("CachingQuery.name is missing")
        objects = self.load_objects_from_cache(key)
        list(super(BaseCachingQuery, self).__iter__())
        self.append_record(objects)
        return iter(objects)

    @classmethod
    def save(cls):
        JsonSerializer.save_record(cls.records, cls.get_record_path())

    @classmethod
    def load(cls):
        return JsonSerializer.load_record(cls.get_record_path())

    def append_record(self, objects):
        record_dict = self._as_dict(objects)
        self.records.append(record_dict)

    def key_from_query(self):
        stmt = self.with_labels().statement
        compiled = stmt.compile()
        params = compiled.params

        values = [str(compiled)]
        for k in sorted(params):
            values.append(repr(params[k]))
        key = " ".join(values)
        return key

    def cache_key(self):
        key = self.key_from_query()
        key_plus_last_cache_key = "{}_{}".format(key, self.__class__.last_cache_key)
        hashed_key = hashlib.md5(key_plus_last_cache_key.encode("utf8")).hexdigest()
        self.__class__.last_cache_key = hashed_key
        return hashed_key

    def _as_dict(self, objects):
        content = sa_serializer.dumps(objects)
        record_dict = {
            "key": self.hashed_key(),
            "value": base64.b64encode(content).decode('utf-8'),
            "uri": str(self.session.get_bind().url),
            "statement": self.key_from_query(),
        }
        return record_dict

    @classmethod
    def get_record_path(cls):
        """
        Append function name to record dir
        """
        return "{}.json".format(os.path.join(cls.output_dir, cls.name))


class JsonSerializer:
    @classmethod
    def open_record(cls, record_path):
        try:
            return load_json(record_path)
        except OSError:
            raise ValueError("Record not found.")

    @classmethod
    def save_record(cls, record_dict, record_path):
        output_dir = os.path.dirname(record_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        dump_json(record_dict, record_path)


class RecordMode(str, Enum):
    ALL = "ALL"
    ONCE = "ONCE"
    NONE = "NONE"
