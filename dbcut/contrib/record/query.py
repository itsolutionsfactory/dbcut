import hashlib
import inspect
from functools import cached_property
from pickle import PicklingError

from sqlalchemy.ext.serializer import dumps
from sqlalchemy.orm import Query

from dbcut.serializer import to_json
from dbcut.utils import sorted_nested_dict

from .persisters.filesystem import FilesystemPersister
from .record_mode import RecordMode
from .serializers.jsonserializer import JsonSerializer


def generate_caching_class(namespace, output_dir, mode=RecordMode.ONCE):
    cassettes=[]
    data_members = {
        'namespace': namespace,
        'mode': mode,
        'records': [],
        'cassette_dir': output_dir,
        'last_cache_key': ""
    }
    return type('CachingQuery', (BaseCachingQuery,), data_members)


class BaseCachingQuery(Query):
    cassette_dir = "dbcut_casette"
    namespace = None
    records = []
    serializer = JsonSerializer
    last_cache_key = ""
    mode = RecordMode.ONCE

    def __iter__(self):
        if self.namespace is None:
            raise RuntimeError("CachingQuery.namespace is missing")
        objects = list(super(BaseCachingQuery, self).__iter__())
        self.append_record(list(objects))
        #
        return iter(objects)

    @classmethod
    def save(cls):
        FilesystemPersister.save_cassette(
            cls.get_record_path(), cls.records, cls.serializer
        )

    @classmethod
    def load(cls):
        return FilesystemPersister.load_cassette(
            cls.get_record_path(), cls.serializer
        )

    def append_record(self, objects):
        cassette_dict = self._as_dict(objects)
        self.records.append(cassette_dict)

    def key_from_query(self):
        stmt = self.with_labels().statement
        compiled = stmt.compile()
        params = compiled.params

        values = [str(compiled)]
        for k in sorted(params):
            values.append(repr(params[k]))
        key = " ".join(values)
        return key

    def hashed_key(self):
        key = self.key_from_query()
        key_plus_last_cache_key = "{}_{}".format(key, self.__class__.last_cache_key)
        hashed_key = hashlib.md5(key_plus_last_cache_key.encode("utf8")).hexdigest()
        self.__class__.last_cache_key = hashed_key
        return hashed_key

    def _as_dict(self, objects):
        try:
            content = dumps(objects)
            cassette_dict = {
                "key": str(self.hashed_key()),
                "value": str(content),
                "uri": str(self.session.get_bind().url),
                "statement": self.key_from_query()
            }
            return cassette_dict
        except PicklingError:
            pass

    @classmethod
    def get_record_path(cls):
        """
        Append function name to record dir
        """
        return f"{cls.cassette_dir}/{cls.namespace}.json"

