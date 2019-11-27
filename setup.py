#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path as op
import re
from codecs import open

from setuptools import find_packages, setup


def read(fname):
    """ Return the file content. """
    here = op.abspath(op.dirname(__file__))
    with open(op.join(here, fname), "r", "utf-8") as fd:
        return fd.read()


def get_requirements(basename):
    return read("requirements/{}.txt".format(basename)).strip().split("\n")


readme = read("README.rst")
changelog = read("CHANGES.rst")

version = ""
version = re.search(
    r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    read(op.join("dbcut", "__init__.py")),
    re.MULTILINE,
).group(1)

if not version:
    raise RuntimeError("Cannot find version information")

extras_require = {
    key: get_requirements(key)
    for key in ["mysql", "postgresql", "profiler", "fastjson", "dev", "test"]
}

setup(
    name="dbcut",
    author="Salem Harrache",
    python_requires=">=3.6",
    author_email="dev@salem.harrache.info",
    version=version,
    url="https://github.com/itsolutionsfactory/dbcut",
    package_dir={"dbcut": "dbcut"},
    packages=find_packages(),
    install_requires=get_requirements("base"),
    extras_require=extras_require,
    include_package_data=True,
    license="MIT license",
    zip_safe=False,
    description="Extract a lightweight subset of your relational production database for development and testing purpose.",
    long_description=readme + "\n\n" + changelog,
    keywords="dbcut",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    entry_points="""
    [console_scripts]
    dbcut=dbcut.cli.main:main
    """,
)
