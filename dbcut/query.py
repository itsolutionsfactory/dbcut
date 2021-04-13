# -*- coding: utf-8 -*-
import hashlib
import os
from pickle import PicklingError
from weakref import WeakSet

import yaml
from pptree import print_tree
from sqlalchemy import event
from sqlalchemy.ext import serializer as sa_serializer
from sqlalchemy.orm import (
    Bundle,
    Query,
    class_mapper,
    interfaces,
    joinedload,
    selectinload,
    subqueryload,
)
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.session import make_transient, object_session

from . import SQLALCHEMY_VERSION
from .serializer import dump_json, load_json, to_json
from .utils import aslist, cached_property, redirect_stdout, sorted_nested_dict


class BaseQuery(Query):

    query_dict = None
    relation_tree = None

    def __init__(self, *args, **kwargs):
        super(BaseQuery, self).__init__(*args, **kwargs)
        if SQLALCHEMY_VERSION < "1.4.0":
            event.listen(
                self,
                "before_compile",
                lambda query: _apply_backref_limit(query, self.session),
                retval=True,
            )

    class QueryStr(str):
        # Useful for debug
        def __repr__(self):
            return self.replace(" \n", "\n").strip()

    def render(self, reindent=True):
        """Generate an SQL expression string with bound parameters rendered inline
        for the given SQLAlchemy query.
        """
        return self.QueryStr(render_query(self))

    @cached_property
    def query_yaml(self):
        return yaml.dump(
            dict(self.query_dict), default_flow_style=False, sort_keys=False
        )

    @cached_property
    def info(self):
        return {
            "engine_info": self.session.db.engine.url.__to_string__(),
            "table_info": self.model_class._table_info,
            "query_info": self.query_dict,
        }

    @cached_property
    def cache_key(self):
        return hashlib.sha1(
            to_json(sorted_nested_dict(self.info)).encode("utf-8")
        ).hexdigest()

    @property
    def cache_basename(self):
        basename = "{}-{}".format(self.model_class.__name__, self.cache_key)
        return os.path.join(self.session.db.cache_dir, basename)

    @property
    def cache_file(self):
        return "{}.cache".format(self.cache_basename)

    @property
    def json_file(self):
        basename = "{}-{}".format(self.model_class.__name__, self.cache_key)
        return os.path.abspath(os.path.join(os.getcwd(), "{}.json".format(basename)))

    @property
    def count_cache_file(self):
        return "{}.count".format(self.cache_basename)

    @property
    def is_cached(self):
        if self.query_dict is not None:
            return os.path.isfile(self.cache_file) and os.path.isfile(
                self.count_cache_file
            )
        return False

    @property
    def model_class(self):
        if hasattr(self, "_bind_mapper"):
            mapper = self._bind_mapper()
        else:
            mapper = self._only_full_mapper_zero("get")
        return self.session.db.models[mapper.class_.__name__]

    def save_to_cache(self, objects=None):
        if objects is None:
            objects = list(self.objects())
        try:
            content = sa_serializer.dumps(objects)
            with open(self.cache_file, "wb") as fd:
                fd.write(content)
            count_data = {"count": len(objects)}
            dump_json(count_data, self.count_cache_file)
        except PicklingError:
            pass

    def export_to_json(self, objects=None):
        if objects is None:
            objects = list(self.objects())
        dump_json(objects, self.json_file)

    def load_from_cache(self, session=None):
        session = session or self.session
        metadata = session.db.metadata
        count = load_json(self.count_cache_file)["count"]

        with open(self.cache_file, "rb") as fd:
            return count, sa_serializer.loads(fd.read(), metadata, session)

    def objects(self, session=None):
        yield from self.transient_objects()

    def transient_objects(self, objects=None, session=None):
        if objects is None:
            objects = self
        for obj in objects:
            if session is None:
                session = object_session(obj)
            for instance in session or []:
                make_transient(instance)
            yield obj

    def with_loaded_relations(
        self, max_join_depth, max_backref_depth, exclude, include
    ):
        query = self._clone()
        models_to_exclude = [
            self.session.db.models.get(table_name)
            for table_name in exclude
            if table_name in self.session.db.models
        ]
        models_to_browse = {
            k: v
            for k, v in self.session.db.models.items()
            if v not in models_to_exclude
        }
        models_to_load = dict(models_to_browse)

        relations_to_load = []
        root_node = RelationTree(self.model_class.__name__)

        list(
            breadth_first_load_generator(
                relations_to_load,
                root_node,
                self.model_class,
                models_to_load,
                models_to_browse,
                max_join_depth,
                max_backref_depth,
                [],
                1,
                [],
                [],
            )
        )

        if include:

            def get_direct_path(target_name):
                direct_paths = []
                leaf_relationship = None
                relations = sorted(relations_to_load, key=lambda x: x[2])
                for relationship, path, weight in relations:
                    if relationship.target.name == target_name:
                        leaf_relationship = (relationship, path, weight)
                        break
                if leaf_relationship is None:
                    return []
                direct_paths = [leaf_relationship]
                other_relations = sorted(
                    list(set(relations) - set([leaf_relationship])), key=lambda x: x[1]
                )
                for relationship, path, weight in other_relations:
                    if path in leaf_relationship[1]:
                        direct_paths.append(tuple([relationship, path, weight]))

                return direct_paths

            def cut_relation_tree(relations_to_keep, tree):
                if tree.relationship in relations_to_keep or tree.relationship is None:
                    children = []
                    for child in tree.children:
                        child_tree = cut_relation_tree(relations_to_keep, child)
                        if child_tree is not None:
                            children.append(child_tree)
                    tree.children = children
                    return tree

            new_relations_to_load = []
            leaf_relationships = []
            for target_name in include:
                direct_paths = get_direct_path(target_name)
                if len(direct_paths) > 0:
                    leaf_relationships.append(direct_paths[0])
                    new_relations_to_load.extend(get_direct_path(target_name))
            relations_to_load = new_relations_to_load
            cut_relation_tree([r for r, p, w in relations_to_load], root_node)

            for _, leaf_path, _ in leaf_relationships:
                query = query.join(*leaf_path.split("."), isouter=True)

            if leaf_relationships:
                query = query.group_by(query.model_class)

        query.relation_tree = root_node

        for relationship, path, weight in sorted(relations_to_load, key=lambda x: x[1]):
            if relationship.direction is interfaces.ONETOMANY:
                query = query.options(selectinload(path))
            elif relationship.direction is interfaces.MANYTOMANY:
                query = query.options(selectinload(path))
            elif relationship.direction is interfaces.MANYTOONE:
                query = query.options(joinedload(path))

        return query


class QueryProperty(object):
    def __init__(self, db):
        self.db = db

    def __get__(self, obj, type):
        try:
            mapper = class_mapper(type)
            if mapper:
                return self.db.query_class(mapper, session=self.db.session)
        except UnmappedClassError:
            return self


def render_query(query, reindent=True):
    """Generate an SQL expression string with bound parameters rendered inline
    for the given SQLAlchemy statement.
    """

    compiled = query.statement.compile(
        dialect=query.session.get_bind().dialect, compile_kwargs={"literal_binds": True}
    )

    raw_sql = str(compiled)
    try:  # pragma: no cover
        import sqlparse

        return sqlparse.format(raw_sql, reindent=reindent)
    except ImportError:  # pragma: no cover
        return raw_sql


class RelationTree(object):
    def __init__(self, name, parent=None, relationship=None, weight=1):
        self.name = name
        self.parent = parent
        self.relationship = relationship
        self.weight = weight
        self.children = []

        if relationship is not None:
            if self.relationship.direction in (
                interfaces.ONETOMANY,
                interfaces.MANYTOMANY,
            ):
                self.repr_name = "─ⁿ─{}".format(self.name)
            else:
                self.repr_name = "─¹─{}".format(self.name)
        else:
            self.repr_name = self.name

        if parent:
            self.parent.children.append(self)

    @cached_property
    @aslist
    def flatten(self):
        yield self.name
        for child in self.children:
            yield from child.flatten  # noqa

    def render(self, return_value=False):
        with redirect_stdout() as stream:
            print_tree(self, childattr="children", nameattr="repr_name")

        tables = self.flatten

        value = (
            stream.getvalue()
            + "\n\n"
            + "%s table" % len(tables)
            + ("s" if len(tables) > 1 else "")
            + " loaded\n"
        )
        if return_value:
            return value
        else:
            print(value)


def get_relationships(model):
    values = model.__mapper__.relationships.values()
    return sorted(values, key=lambda r: (r.direction is interfaces.MANYTOONE, r.key))


def get_relationship_path(relationship):
    local_table_name = relationship.parent.class_._table_info["table_name"]
    if relationship.direction in (interfaces.ONETOMANY, interfaces.MANYTOMANY):
        key = relationship.key
    else:
        key = list(relationship.local_columns)[0].name
    return "{}.{}".format(local_table_name, key)


def get_relationship_reverse_path(relationship):
    remote_table_name = relationship.target.name
    if relationship.direction in (interfaces.ONETOMANY, interfaces.MANYTOMANY):
        key = list(relationship.remote_side)[0].name
    else:
        key = relationship.back_populates
    return "{}.{}".format(remote_table_name, key)


def get_relationships_path(relationships):
    path = [get_relationship_path(r) for r in relationships]
    return path + [get_relationship_reverse_path(r) for r in relationships]


STOP_BREADTH_FIRST_LOAD_GENERATOR = object()


def breadth_first_load_generator(
    relations_to_load,
    root_node,
    model,
    models_to_load,
    models_to_browse,
    join_depth,
    backref_depth,
    path,
    weight,
    already_seen_relationships,
    already_browse_models,
):
    next_models = []
    already_seen_relationships_path = get_relationships_path(already_seen_relationships)
    model_name = model.__name__
    if model_name in models_to_load and model_name not in already_browse_models:
        for relationship in get_manytoone_relationships_first(model):
            if relationship.target.name in models_to_browse:
                relationship_path = get_relationship_path(relationship)
                next_path = path + [relationship.key]
                full_path = ".".join(next_path)
                target_model = models_to_browse[relationship.target.name]
                if relationship_path not in already_seen_relationships_path:
                    if (
                        relationship.direction
                        in (interfaces.ONETOMANY, interfaces.MANYTOMANY)
                        and (backref_depth is None or backref_depth > 0)
                        and relationship.target.name not in already_browse_models
                    ) or (
                        relationship.direction is interfaces.MANYTOONE
                        and (join_depth is None or join_depth > 0)
                    ):
                        if relationship.direction in (
                            interfaces.ONETOMANY,
                            interfaces.MANYTOMANY,
                        ):
                            next_weight = weight * 2
                        else:
                            next_weight = weight * 1

                        relations_to_load.append((relationship, full_path, next_weight))
                        next_models.append(
                            (target_model, next_path, relationship, next_weight)
                        )
            yield relationship
        already_browse_models.append(model_name)

    join_depth = max(0, join_depth - 1) if join_depth is not None else join_depth
    backref_depth = (
        max(0, backref_depth - 1) if backref_depth is not None else backref_depth
    )
    nodes = []

    for next_model, next_path, relationship, next_weight in sorted(
        next_models, key=lambda x: x[3]
    ):
        next_node = RelationTree(
            next_model.__name__, root_node, relationship, next_weight
        )
        gen = breadth_first_load_generator(
            relations_to_load,
            next_node,
            next_model,
            models_to_load,
            models_to_browse,
            join_depth,
            backref_depth,
            next_path,
            next_weight,
            already_seen_relationships + [relationship],
            already_browse_models,
        )
        nodes.append({"generator": gen, "stop_iteration": False})

    yield

    for node in nodes:
        next(node["generator"])

    yield

    while not all(node["stop_iteration"] for node in nodes):
        for node in nodes:
            if not node["stop_iteration"]:
                for value in node["generator"]:
                    if value is STOP_BREADTH_FIRST_LOAD_GENERATOR:
                        node["stop_iteration"] = True
                        break
                    if value is None:
                        break
        yield

    yield STOP_BREADTH_FIRST_LOAD_GENERATOR


def get_manytoone_relationships_first(model):
    def key(relationship):
        if relationship.direction is interfaces.MANYTOONE:
            return 0
        return 1

    return sorted(model.__mapper__.relationships.values(), key=key)


def _apply_backref_limit(query, session):
    parsed_query = session.parsed_query

    for desc in query.column_descriptions:
        if desc["entity"] is None and desc["name"] == "pk" and desc["type"] == Bundle:
            # this is a selectin query
            backref_limit = parsed_query.query_dict.get("backref_limit", None)
            if backref_limit:
                query = query.limit(backref_limit)

    return query
