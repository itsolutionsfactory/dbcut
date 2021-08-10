#!/usr/bin/env python
# coding: utf-8
import itertools
import os
import re
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


def generate_pipeline_name(env_value):
    images = re.findall(r"\.*IMAGE=(.*?)(?!\S)", env_value, re.DOTALL)
    return "_".join(image.replace(":", "") for image in images)


def generate_pipeline_variables(env_value):
    variables = {}
    for key_value in env_value.split():
        key, value = key_value.split("=")
        variables[key] = value
    return variables


def generate_pipelines():
    """Parse command-line arguments and execute bumpversion command."""
    env = yaml.safe_load(read(".ci/env.yml"))

    iterables = [[f"{key}={value}" for value in values] for key, values in env.items()]
    env_list = [" ".join(t) for t in itertools.product(*iterables)]

    pipelines = [
        {
            "env": env_value,
            "name": generate_pipeline_name(env_value),
            "variables": generate_pipeline_variables(env_value),
        }
        for env_value in env_list
    ]
    write(
        Template(read(".ci/travis.yml.j2")).render(pipelines=pipelines), ".travis.yml"
    )


if __name__ == "__main__":
    generate_pipelines()
