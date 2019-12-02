#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Some generic code relevant for all tests.
"""

import unittest

import pytest


class TestClassWithFixtures(unittest.TestCase):
    """
    Allows the use of pytest fixtures as attributes in test classes.
    """

    fixture_names = ()

    @pytest.fixture(autouse=True)
    def auto_injector_fixture(self, request):
        names = self.fixture_names
        for name in names:
            setattr(self, name, request.getfixturevalue(name))
