#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging

import pickle

import pytest

# Tests should always be run in the root dir.
# This is for direct execution of the test file, hence for development.
if __name__ == '__main__':
    os.chdir('../../..')

from tests.base import TestClassWithFixtures
from connectors.base import BaseConnector


class Test_start_asynchronously(TestClassWithFixtures):

    fixture_names = ('caplog', )

    def setup_class(self):
        self.base_connector = BaseConnector()

    def test_function_is_executed_non_blocking(self):

        def tester():
            time.sleep(2)

        start_time = time.time()
        self.base_connector.start_asynchronously(
            function=tester
        )
        end_time = time.time()

        required_time = end_time - start_time

        assert required_time < 0.1

    def test_function_can_modify_class_attributes(self):
        """
        Also test that args and kwargs are handled correctly, that the function
        is actually executed and finally that class attributes can be changed
        from the function run in background.
        """

        class tester():

            def write(self, arg1, arg2, *, kwarg1, kwarg2):

                self.arg1 = arg1
                self.arg2 = arg2
                self.kwarg1 = kwarg1
                self.kwarg2 = kwarg2

        # Create class with some attributes so we can inspect later
        # whether those have changed.
        tester_instance = tester()
        tester_instance.write('a', 'b', kwarg1=1, kwarg2=[1, 2, 3])

        assert tester_instance.arg1 == 'a'
        assert tester_instance.arg2 == 'b'
        assert tester_instance.kwarg1 == 1
        assert tester_instance.kwarg2 == [1, 2, 3]

        # Now check whether the async function can modify these attributes.
        self.base_connector.start_asynchronously(
            function=tester_instance.write,
            args=[(2, 3), 'asdashd'],
            kwargs={'kwarg1': 55, 'kwarg2': None}
        )

        # Give the function some time to write the attributes before
        # checking if they exist.
        time.sleep(0.1)

        assert tester_instance.arg1 == (2, 3)
        assert tester_instance.arg2 == 'asdashd'
        assert tester_instance.kwarg1 == 55
        assert tester_instance.kwarg2 is None

    def test_function_can_write_log(self):
        """
        Verify that a method of a class can access the classes log attribute
        to generate log messages (Which is obviously necassary in multi
        processing).
        """

        # Set up a new and empty logger for the test
        logger_name = str(id(self))
        self.caplog.set_level(logging.DEBUG, logger=logger_name)
        self.caplog.clear()

        # Prepare class with a method that writes to the logger.
        class tester():

            def __init__(self):
                self.log = logging.getLogger(logger_name)

            def write_logs(self):
                self.log.debug('a debug message')
                self.log.info('an info message')
                self.log.warning('a warning')
                self.log.error('An error')
                self.log.critical('CRITICAL')

        # Run the write logs function in background.
        tester_instance = tester()
        self.base_connector.start_asynchronously(
            function=tester_instance.write_logs,
        )

        # Give the function some time to call the log function before expecting
        # the results.
        time.sleep(0.1)

        records = self.caplog.records
        assert records[0].levelname == 'DEBUG'
        assert records[0].message == 'a debug message'
        assert records[1].levelname == 'INFO'
        assert records[1].message == 'an info message'
        assert records[2].levelname == 'WARNING'
        assert records[2].message == 'a warning'
        assert records[3].levelname == 'ERROR'
        assert records[3].message == 'An error'
        assert records[4].levelname == 'CRITICAL'
        assert records[4].message == 'CRITICAL'

    def test_function_can_throw_exception(self):
        """
        Verify that an exception occurred in a background process is passed
        to the main application (which is also not necessarily the case while
        usin threading).
        """

        class tester():

            def throw(self):

                raise RuntimeError('A test exception')

        tester_instance = tester()
        with pytest.raises(RuntimeError):
            self.base_connector.start_asynchronously(
                function=tester_instance.throw,
            )


if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])
