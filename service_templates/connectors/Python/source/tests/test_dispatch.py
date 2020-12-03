#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from time import time

from .base import TestClassWithFixtures
from pyconnector_template.dispatch import BaseDispatcher



class TestBaseDispatcherTerminate(TestClassWithFixtures):

    fixture_names = ()

    def test_terminate_quits_thread_immediatly(self):
        """
        The terminate method should inject a SystemExit exception into the
        target executed by Thread.run. Ensure this happens.
        """
        got_system_exit = {"state": False}

        def test_function(termination_event, got_system_exit):
            """
            This would sleep one second if the test fails and return faster
            if the SystemExit is received as expected.
            """
            try:
                termination_event.wait(1)
            except SystemExit:
                got_system_exit["state"] = True
                raise

        thread = BaseDispatcher(
            target=test_function,
            kwargs={"got_system_exit": got_system_exit}
        )
        thread.start()
        start_time = time()

        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # Ask the thread to exit and measure how long it takes.
        thread.terminate()
        thread.join()
        runtime = time() - start_time

        # Check thread has exited as expected.
        assert not thread.is_alive()

        # Verify that except block has been executed.
        assert got_system_exit["state"]

        # Check that the try loop has been left immediatly.
        assert runtime < 0.1