#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from time import time
from threading import Event
from unittest.mock import MagicMock


from .base import TestClassWithFixtures
from pyconnector_template.dispatch import DispatchOnce


class TestDispatchOnce__init__(TestClassWithFixtures):

    fixture_names = ()

    def test_required_attributes_created(self):
        """
        Verify that all required attributes are created by __init__
        """
        target_func = MagicMock()
        target_args = MagicMock()
        target_kwargs = MagicMock()
        cleanup_func = MagicMock()
        cleanup_args = MagicMock()
        cleanup_kwargs = MagicMock()

        do = DispatchOnce(
            target_func=target_func,
            target_args=target_args,
            target_kwargs=target_kwargs,
            cleanup_func=cleanup_func,
            cleanup_args=cleanup_args,
            cleanup_kwargs=cleanup_kwargs,
        )

        assert do.target_func == target_func
        assert do.target_args == target_args
        assert do.target_kwargs == target_kwargs
        assert do.cleanup_func == cleanup_func
        assert do.cleanup_args == cleanup_args
        assert do.cleanup_kwargs == cleanup_kwargs
        assert isinstance(do.termination_event, Event)

    def test_default_parameters(self):
        """
        Check that defaults for args and kwargs are created.
        """
        do = DispatchOnce()

        assert do.target_args == ()
        assert do.target_kwargs == {}
        assert do.cleanup_args == ()
        assert do.cleanup_kwargs == {}

    def test_termination_event_injected_if_exected(self):
        """
        Verify that the termination_event is added to kwargs if the target
        function has a termination_event argument.
        """
        def target_func(termination_event):
            pass

        do = DispatchOnce(target_func=target_func)

        assert "termination_event" in do.target_kwargs
        assert do.target_kwargs["termination_event"] == do.termination_event

    def test_termination_event_not_injected_if_not_exected(self):
        """
        Verify that the termination_event is not add to kwargs if the target
        function has no termination_event argument.
        """
        def target_func():
            pass

        do = DispatchOnce(target_func=target_func)
        #do.start()
        assert "termination_event" not in do.target_kwargs


class TestDispatchOnceRun(TestClassWithFixtures):
    """
    Nothing to do here, run should work fine if the integration tests below
    run through.
    """
    fixture_names = ()


class TestDispatchOnceTerminate(TestClassWithFixtures):

    fixture_names = ()

    def test_termination_event_set(self):
        """
        Verify that the termination event is fired.
        """
        do = DispatchOnce()
        do.start()
        do.terminate()

        assert do.termination_event.is_set()


class TestDispatchOnceIntregration(TestClassWithFixtures):
    """
    Integration tests to verify functionality.
    """

    fixture_names = ()

    def test_terminate_quits_thread_immediatly(self):
        """
        Verify that a thread is started, and stopped immediatly after
        terminate is called.
        """
        def target_func(termination_event, got_system_exit):
            """
            This would sleep one second if the test fails and return faster
            if the SystemExit is received as expected.
            """
            # Don't use sleep here, it will not be affected by SystemExit.
            termination_event.wait(1)

        thread = DispatchOnce(
            target_func=target_func,
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

        # Check that the try loop has been left immediatly.
        assert runtime < 0.1

    def test_cleanup_func_called_after_terminate_called(self):
        """
        Verify that the cleanup function is called even if we exit
        with SystemExit.
        """

        def target_func(termination_event):
            """
            This would sleep one second if the test fails and return faster
            if the SystemExit is received as expected.
            """
            # Don't use sleep here, it will not be affected by SystemExit.
            termination_event.wait(1)

        def cleanup_func(got_system_exit):
            got_system_exit["state"] = True

        got_system_exit = {"state": False}

        thread = DispatchOnce(
            target_func=target_func,
            cleanup_func=cleanup_func,
            cleanup_kwargs={"got_system_exit": got_system_exit}
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

        # Verify that the cleanup function has been executed.
        assert got_system_exit["state"]

        # Check that the try loop has been left immediatly.
        assert runtime < 0.1

    def test_cleanup_func_called_after_target_func_exits(self):
        """
        Verify that the cleanup function is called after the target
        function has exited normally.
        """

        def target_func():
            pass

        def cleanup_func(got_system_exit):
            got_system_exit["state"] = True

        got_system_exit = {"state": False}

        thread = DispatchOnce(
            target_func=target_func,
            cleanup_func=cleanup_func,
            cleanup_kwargs={"got_system_exit": got_system_exit}
        )

        # Run thread and wait until it finished.
        thread.start()
        thread.join()

        # Verify that the cleanup function has been executed.
        assert got_system_exit["state"]