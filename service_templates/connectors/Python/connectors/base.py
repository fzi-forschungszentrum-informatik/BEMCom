#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic and generic functionality for connectors.
"""
import asyncio

import threading
import pytest


class BaseConnector():

    _arguments = []
    _is_connected = False
    _child_threads = []

    def add_argument(self, *, name, required, description, default_value=None):
        """
        Add an argument
        """
        if name in [a[0] for a in self._arguments]:
            emsg = 'Argument with name %s already exists'
            self.log.critical(emsg, name)
            raise ValueError(emsg % name)
        self._arguments.append((name, required, description, default_value))

    def get_arguments(self):
        return self._arguments

    def connect(self):
        """
        This triggers the connector to connect to the respective endpoint.
        """
        pass

    def parse_message(self):
        """
        Convert raw message to
        """
        pass

    def start_asynchronously(self, function, args=[], kwargs={}):
        """
        Wrapper/helper function to start functions non blocking in background.

        Arguments:
        ----------
        function: function
            The python function to call.
        args: list or tuple
            Positional Arguments for function
        kwargs: dict
            Keyword arguements for function
        """
#        loop = asyncio.get_event_loop()
#        async def wrapper(f, args, kwargs):
#            f(*args, **kwargs)
#        _ = asyncio.create_task(wrapper(function, args, kwargs))

        thread = threading.Thread(
            target=function,
            args=args,
            kwargs=kwargs,
        )
        thread.start()
        self._child_threads.append(thread)

    def start_thread_manager(self):
        """
        A simple manager that ????
        """


class PollConnector(BaseConnector):
    """
    A connector that receives data by periodically polling the endpoint.
    """

    def __init__(self):
        self.add_argument(
            name='poll_seconds',
            required=True,
            description='Time in seconds between polling the endpoint for '
                        'data.',
        )


# Execute the corresponding tests if executing this file.
if __name__ == '__main__':
    pytest.main(['-v', '../tests/test_connectors/test_base/'])
