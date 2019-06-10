#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

test_dbcut
----------------------------------

Tests for `dbcut` module.
"""
import pytest

from dbcut import dbcut


@pytest.fixture
def response():
    """Sample pytest fixture.
    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/SalemHarrache/python-dbcut')
    pass


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument.
    """
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string
    pass
