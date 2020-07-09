#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import argparse

import pytest
import pytest_httpserver

# Tests should always be run in the root dir.
# This is for direct execution of the test file, hence for development.
if __name__ == '__main__':
    os.chdir('../../..')

from tests.base import TestClassWithFixtures

from connectors.HTTP import SimpleText
from connectors.HTTP import LogConnector


class test_append_argparser():

    fixture_names = ('capsys', )

    def setup_class(self):
        parser = argparse.ArgumentParser()
        self.parser = SimpleText.append_argparser(parser=parser)

    def test_optional_arguements_are_listed(self):
        """

        """
        # Get the help text of argparser, also catch it's exit call
        try:
            self.parser.parse_args(['-h'])
        except SystemExit:
            pass
        captured_stdout = self.capsys.readouterr().out

        """
        captured_stdout is now at least:

        usage: [-h]

        optional arguments:
          -h, --help  show this help message and exit
        """

        help_text_blocks = captured_stdout.split('\n\n')
        for help_text_block in help_text_blocks:
            if help_text_block.startswith('optional arguments:'):
                optional_arguments_block = help_text_block
                break

        assert optional_arguments_block is not None


    # TODO: Assert that latin_1 is decoded correctly.


#class TestClassAttributes():
#
#    def test_required_args_specified(self):
#        expected_required_args = {
#            'POLL_SECONDS',
#            'URL',
#        }
#
#        assert HTTPConnctor.required_args == expected_required_args
#
#    def test_optional_args_specified(self):
#        optional_required_args = {
#            'POLL_SECONDS',
#            'URL',
#        }
#
#        assert HTTPConnctor.optional_args == optional_required_args

#
#
#
#rt = []
#class TestLogConncetior(TestBase):
#
#    fixture_names = ('caplog', )
#
#    def setup(self):
#        self.log = logging.getLogger()
#        self.log.warn('setup complete')
#
#    def test_stuff(self):
#        print('\n')
#        lc = LogConnector()
#        lc.send('key', 'stuff')
#
#        print(self.caplog.record_tuples)
#
#        rt.extend(self.caplog.record_tuples)
#
#
#
#def test_my_client(httpserver): # httpserver is a pytest fixture which starts the server
#    # set up the server to serve /foobar with the json
#    httpserver.expect_request("/foobar").respond_with_json({"foo": "bar"})
#    # check that the request is served

if __name__ == '__main__':
    # Test this file only.
    pytest.main(['-v', __file__])