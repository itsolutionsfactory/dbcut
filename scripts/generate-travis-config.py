#!/usr/bin/env python
# coding: utf-8
import os
from io import open

import yaml
from jinja2 import Template

HERE = os.path.abspath(os.path.dirname(__file__))


def read(fname):
    with open(os.path.join(HERE, "..", fname), "r") as fd:
        return fd.read()


def write(content, fname):
    with open(os.path.join(HERE, "..", fname), "w") as fd:
        fd.write(content)


def generate_travis_config():
    """Parse command-line arguments and execute bumpversion command."""
    template_content = read(".travis/travis.yml.j2")
    travis_env = yaml.safe_load(read(".travis/env.yml"))
    env = travis_env

    import itertools

    iterables = [[f"{key}={value}" for value in values] for key, values in env.items()]
    env_list = [" ".join(t) for t in itertools.product(*iterables)]

    write(Template(template_content).render(env_list=env_list), ".travis.yml")


if __name__ == "__main__":
    generate_travis_config()
