#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper methods for writing tests, both for stuff residing in the this
package but also for derived services and other programs.
"""
import asyncio

import pytest


def async_return(return_value=None, loop=None):
    """
    A small helper that allows a MagicMock to be used in place of a
    async function. Use with MagicMock(return_value=async_return())
    """
    f = asyncio.Future(loop=loop)
    f.set_result(return_value)
    return f


class TestClassWithFixtures:
    """
    Allows the use of pytest fixtures as attributes in test classes.
    """

    fixture_names = ()

    @pytest.fixture(autouse=True)
    def auto_injector_fixture(self, request):
        names = self.fixture_names
        for name in names:
            setattr(self, name, request.getfixturevalue(name))
