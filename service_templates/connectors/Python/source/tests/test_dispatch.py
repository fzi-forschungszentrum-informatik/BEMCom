#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from threading import Event
from unittest.mock import MagicMock

import pytest

from .base import TestClassWithFixtures
from pyconnector_template.dispatch import DispatchOnce, DispatchInInterval


class TestDispatchOnce__init__(TestClassWithFixtures):

    fixture_names = ()

    def setup_class(self):
        """
        Allow overloading the dispatcher, so we can reuse the test later.
        """
        self.dispatcher = DispatchOnce

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

        do = self.dispatcher(
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
        assert do.exception is None

    def test_default_parameters(self):
        """
        Check that defaults for args and kwargs are created.
        """
        do = self.dispatcher()

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

        do = self.dispatcher(target_func=target_func)

        assert "termination_event" in do.target_kwargs
        assert do.target_kwargs["termination_event"] == do.termination_event

    def test_termination_event_not_injected_if_not_exected(self):
        """
        Verify that the termination_event is not add to kwargs if the target
        function has no termination_event argument.
        """
        def target_func():
            pass

        do = self.dispatcher(target_func=target_func)
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

    def setup_class(self):
        """
        Allow overloading the dispatcher, so we can reuse the test later.
        """
        self.dispatcher = DispatchOnce

    def test_termination_event_set(self):
        """
        Verify that the termination event is fired.
        """
        do = self.dispatcher()
        do.start()
        do.terminate()

        assert do.termination_event.is_set()


class TestDispatchOnceIntegration(TestClassWithFixtures):
    """
    Integration tests to verify functionality.
    """

    fixture_names = ()

    def setup_class(self):
        """
        Allow overloading the dispatcher, so we can reuse the test later.
        """
        self.dispatcher = DispatchOnce

    def test_terminate_quits_thread_immediatly(self):
        """
        Verify that a thread is started, and stopped immediatly after
        terminate is called.
        """
        def target_func(termination_event):
            """
            This would sleep one second if the test fails and return faster
            if the SystemExit is received as expected.
            """
            # Don't use sleep here, it will not be affected by SystemExit.
            termination_event.wait(1)

        thread = self.dispatcher(
            target_func=target_func,
        )

        thread.start()
        start_time = time.monotonic()

        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # Ask the thread to exit and measure how long it takes.
        thread.terminate()
        thread.join()
        runtime = time.monotonic() - start_time

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

        thread = self.dispatcher(
            target_func=target_func,
            cleanup_func=cleanup_func,
            cleanup_kwargs={"got_system_exit": got_system_exit}
        )

        thread.start()
        start_time = time.monotonic()

        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # Ask the thread to exit and measure how long it takes.
        thread.terminate()
        thread.join()
        runtime = time.monotonic() - start_time

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

        thread = self.dispatcher(
            target_func=target_func,
            cleanup_func=cleanup_func,
            cleanup_kwargs={"got_system_exit": got_system_exit}
        )

        # Run thread and wait until it finished.
        thread.start()
        thread.join()

        # Verify that the cleanup function has been executed.
        assert got_system_exit["state"]

    def test_exception_in_target_function_is_caught(self):
        """
        Exceptions in threads won't be raised in the main thread. Hence,
        if an exception occures, we store it away so it can be reraised in
        the main thread.

        Test this for a "normal" exception but also for SystemExit and
        KeyboardInterrupt as these are not caought by "except Exception"
        and the information that the thread was killed by a normal
        SystemExit or KeyboardInterupt is important for error handling in
        the main thread.
        """
        for e in (RuntimeError, SystemExit, KeyboardInterrupt):
            def target_func():
                raise e("test")

            thread = self.dispatcher(
                target_func=target_func,
            )

            thread.start()
            thread.join()
            assert isinstance(thread.exception, e)


class TestDispatchInInterval__init__(TestDispatchOnce__init__):
    """
    Reuse the tests for DispatchOnce above and only check new functionality.
    """

    def setup_class(self):
        """
        Allow overloading the dispatcher, so we can reuse the test later.
        """
        self.dispatcher = DispatchInInterval

    def test_required_attributes_created_extended(self):
        """
        Verify that all required attributes are created by __init__
        """
        call_interval = MagicMock()

        do = self.dispatcher(call_interval=call_interval)

        assert do.call_interval == call_interval


class TestDispatchInIntervalRun(TestDispatchOnceRun):
    """
    Nothing to do here, run should work fine if the integration tests below
    run through.
    """
    fixture_names = ()


class TestDispatchInIntervalTerminate(TestDispatchOnceTerminate):
    """
    Reuse the tests for DispatchOnce above and only check new functionality.
    """

    def setup_class(self):
        """
        Allow overloading the dispatcher, so we can reuse the test later.
        """
        self.dispatcher = DispatchInInterval


class TestDispatchInIntervalIntegration(TestClassWithFixtures):
    """
    Integration tests to verify functionality.

    Don't inherit from TestDispatchInIntervalIntegration here, as it would
    only affect one of the test methods but add unintended side effects for
    tests that expect that the run is finished after one exection of the
    target function.
    """

    fixture_names = ()

    def setup_class(self):
        """
        Allow overloading the dispatcher, so we can reuse the test later.
        """
        self.dispatcher = DispatchInInterval

    def test_terminate_quits_thread_immediatly(self):
        """
        Verify that a thread is started, and stopped immediatly after
        terminate is called.
        """
        def target_func(termination_event):
            pass

        thread = self.dispatcher(
            target_func=target_func,
            call_interval=1,
        )

        thread.start()
        start_time = time.monotonic()

        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # Ask the thread to exit and measure how long it takes.
        thread.terminate()
        thread.join()
        runtime = time.monotonic() - start_time

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
            pass

        def cleanup_func(got_system_exit):
            got_system_exit["state"] = True

        got_system_exit = {"state": False}

        thread = self.dispatcher(
            target_func=target_func,
            cleanup_func=cleanup_func,
            cleanup_kwargs={"got_system_exit": got_system_exit},
            call_interval=1,
        )

        thread.start()
        start_time = time.monotonic()

        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # Ask the thread to exit and measure how long it takes.
        thread.terminate()
        thread.join()
        runtime = time.monotonic() - start_time

        # Check thread has exited as expected.
        assert not thread.is_alive()

        # Verify that the cleanup function has been executed.
        assert got_system_exit["state"]

        # Check that the try loop has been left immediatly.
        assert runtime < 0.1

    def test_target_func_called_at_specified_interval(self):
        """
        Verify that the target function is triggered in call_interval
        seconds, up to some tollerance.
        """
        execution_times = []

        def target_func(termination_event, execution_times):
            execution_times.append(time.monotonic())

        thread = self.dispatcher(
            target_func=target_func,
            target_kwargs={"execution_times": execution_times},
            call_interval=0.1,
        )

        thread.start()
        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # wait until the target_function should have been called three times.
        time.sleep(0.25)

        # Ask the thread to exit.
        thread.terminate()
        thread.join()

        # Check thread has exited as expected.
        assert not thread.is_alive()

        # We expect that target_func has been executed three times with less
        # then a percent deviation from the requested call interval.
        assert len(execution_times) == 3
        actual_execution_time_0 = execution_times[1] - execution_times[0]
        actual_execution_time_1 = execution_times[2] - execution_times[1]
        expected_execution_time = pytest.approx(0.1, 0.01)
        assert actual_execution_time_0 == expected_execution_time
        assert actual_execution_time_1 == expected_execution_time

    def test_call_interval_extended_for_longer_target_func_runs(self):
        """
        We expect the dispatcher to immediatly start the next run of the
        target function if the runtime of it was longer then the
        call_intervall.
        """
        execution_times = []

        def target_func(termination_event, execution_times):
            execution_times.append(time.monotonic())
            time.sleep(0.2)

        thread = self.dispatcher(
            target_func=target_func,
            target_kwargs={"execution_times": execution_times},
            call_interval=0.1,
        )

        thread.start()
        # Ensure the thread was started correctly.
        assert thread.is_alive()

        # wait until the target_function should have been called three times.
        time.sleep(0.42)

        # Ask the thread to exit.
        thread.terminate()
        thread.join()

        # Check thread has exited as expected.
        assert not thread.is_alive()

        # We expect that target_func has been executed three times with less
        # then a percent deviation from the run time of the target function.
        assert len(execution_times) == 3
        actual_execution_time_0 = execution_times[1] - execution_times[0]
        actual_execution_time_1 = execution_times[2] - execution_times[1]
        expected_execution_time = pytest.approx(0.2, 0.01)
        assert actual_execution_time_0 == expected_execution_time
        assert actual_execution_time_1 == expected_execution_time

    def test_exception_in_target_function_is_caught(self):
        """
        Exceptions in threads won't be raised in the main thread. Hence,
        if an exception occures, we store it away so it can be reraised in
        the main thread.

        Test this for a "normal" exception but also for SystemExit and
        KeyboardInterrupt as these are not caought by "except Exception"
        and the information that the thread was killed by a normal
        SystemExit or KeyboardInterupt is important for error handling in
        the main thread.
        """
        for e in (RuntimeError, SystemExit, KeyboardInterrupt):
            def target_func():
                raise e("test")

            thread = self.dispatcher(
                target_func=target_func,
                call_interval=1,
            )

            thread.start()
            start_time = time.monotonic()

            thread.join()
            runtime = time.monotonic() - start_time

            assert isinstance(thread.exception, e)

            # Check that the try loop has been left immediatly.
            assert runtime < 0.1
