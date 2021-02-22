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
        'cassettes': [],
        'cassette_dir': output_dir,
        'last_cache_key': ""
    }
    return type('CachingQuery', (BaseCachingQuery,), data_members)


class BaseCachingQuery(Query):
    cassette_dir = "dbcut_casette"
    namespace = None
    cassettes = []
    parser = JsonSerializer
    last_cache_key = ""
    mode = RecordMode.ONCE

    # def get_current_test_func(self):
    #     i = 0
    #     __import__("pdb").set_trace()
    #     for s in inspect.stack():
    #         if s.function == "pytest_pyfunc_call":
    #             func_name = inspect.stack()[i - 1].function
    #             return func_name
    #         i += 1

    def __iter__(self):
        if self.namespace is None:
            raise RuntimeError("CachingQuery.namespace is missing")
        self.key_from_query()
        objects = list(super(BaseCachingQuery, self).__iter__())
        cassette_dict = self._as_dict(list(objects))
        self.append_to_list_or_save_cassette(cassette_dict, JsonSerializer)
        return iter(objects)

    def append_to_list_or_save_cassette(self, cassette_dict, serializer):
        # curr_test_func = self.get_current_test_func()
        # if self.test_func == "" or self.test_func == curr_test_func:
        #     self.cassettes.append(cassette_dict)
        #     self._test_func = curr_test_func
        # else:
        cassette_path = self.get_cassette_path()
        FilesystemPersister.save_cassette(cassette_path, self.cassettes, serializer)

    def key_from_query(self):
        stmt = self.with_labels().statement
        compiled = stmt.compile()
        params = compiled.params

        values = [str(compiled)]
        for k in sorted(params):
            values.append(repr(params[k]))
        key = " ".join(values)
        hashed_key = hashlib.md5(key.encode("utf8")).hexdigest()
        # The first key will be based on the first query only
        if self.last_cache_key == "":
            self.last_cache_key = hashed_key
            return hashed_key
        else:
            # The others will have the previous keys appended to them
            hashed_key += self.last_cache_key
            self.last_cache_key = hashed_key
            return hashed_key

    def _as_dict(self, objects):
        try:
            content = dumps(objects)
            cassette_dict = {
                "key": str(self.key_from_query()),
                "value": str(content),
                "uri": str(self.session.get_bind().url),
            }
            return cassette_dict
        except PicklingError:
            pass

    def render_query(self, reindent=True):
        """Generate an SQL expression string with bound parameters rendered inline
        for the given SQLAlchemy statement.
        """

        compiled = self.statement.compile(
            dialect=self.session.get_bind().dialect,
            compile_kwargs={"literal_binds": True},
        )

        raw_sql = str(compiled)
        try:  # pragma: no cover
            import sqlparse

            return sqlparse.format(raw_sql, reindent=reindent)
        except ImportError:  # pragma: no cover
            return raw_sql

    def get_cassette_path(self):
        """
        Append function name to cassette dir
        """
        return f"{self.cassette_dir}/{self.namespace}.json"

    @cached_property
    def cache_key(self):
        return hashlib.sha1(
            to_json(sorted_nested_dict(self.info)).encode("utf-8")
        ).hexdigest()
