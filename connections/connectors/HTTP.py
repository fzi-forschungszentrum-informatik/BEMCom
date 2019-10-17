#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 15:02:12 2019

@author: david
"""

import logging

import requests


class SimpleText():
    """
    Simple connector using text over HTTP with seperators between keys and
    values and an other seperator between entries.

    E.g. something like this:
    'BD3112.Hka_Bd.ulBetriebssekunden=28236.361\nHka_Mw1.usDrehzahl=0\n\n'

    Attributes:
    -----------
    is_connected: bool
        If true the connection to the endpoint.... .

    """
    is_connected = False

    # These statements are required that a calling binding will now
    # which arguemnts it should parse from configuration.
    required_args = {
        'POLL_SECONDS',
        'URL',
    }
#
#    optional_args = [
#       'CREDENTIALS'
#    ]

    @staticmethod
    def append_argparser(parser):
        """
        Append the configuration arguments required for this connector to the
        argparser.

        This must be called before __init__ to allow the connection to parse
        the required arguments for __init__, hence a staticmethod.
        """
        parser.add_argument('--url', nargs=1, required=True)
        parser.add_argument('--key_value_seperator', nargs=1, default='\n')
        return parser

    def __init__(self, c, d):
        """
        Set up connector. See append_argparser for a documentation on
        """
        self.a = 'a'

    def from_foo(self):
        return 'bar'

    def send(self):
        raise NotImplementedError


class PrintConnector():
    """
    """

    def __init__(self):
        self.b = 'b'

    def send(self, stuff):
        print(stuff)


class LogConnector():
    """
    A simple Connector for development that writes all send messages
    to the log.
    """

    def __init__(self):
        self.log = logging.getLogger(__name__)

    def send(self, topic, payload):
        self.log.info('Topic: %s   Payload: %s', (topic, payload))

#class TestConnection(PrintConnector, HTTPConnctor):
#    pass
#
#    def __init__(self):
#        self.PrintConnector = PrintConnector
#        self.HTTPConnctor = HTTPConnctor
#
## tc = TestConnection()
