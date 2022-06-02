#!/usr/bin/env python3
"""
"""
import os
import asyncio
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import time
from uuid import uuid1
from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.responses import JSONResponse
import pytest

from esg.models.base import _BaseModel
from esg.services.thread import ThreadPoolExecutorService
from esg.test.tools import TestClassWithFixtures


class TestPostRequest:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        tpes = ThreadPoolExecutorService()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(tpes.post_request())


class TestScheduleRequestProcessing:
    """
    Tests for ThreadPoolExecutorService.schedule_request_processing
    """

    def setup_method(self):
        self.test_request = {"ID": uuid1()}

        def _process_request_wrapper(request):
            request["was_executed"] = True

        self.tpes = ThreadPoolExecutorService()
        self.tpes._process_request_wrapper = MagicMock()

    def execute_schedule_request(self):
        """
        A simple wrapper to reduce redundant code.
        """
        asyncio.new_event_loop().run_until_complete(
            self.tpes.schedule_request_processing(request=self.test_request)
        )

    def test_executor_created(self):
        """
        `schedule_request_processing` is expected to dynamically crated
        a ThreadPoolExecutor instance if required.
        """
        self.execute_schedule_request()

        assert isinstance(self.tpes.executor, ThreadPoolExecutor)

    def test_executor_created_first_time_only(self):
        """
        The executor should only be created if non existing, to prevent
        that new jobs kill the executor of previous jobs.
        """
        self.execute_schedule_request()
        expected_excutor_id = id(self.tpes.executor)

        self.execute_schedule_request()
        actual_excutor_id = id(self.tpes.executor)

        assert actual_excutor_id == expected_excutor_id

    def test_process_request_wrapper_is_executed(self):
        """
        Verify that the wrapper function is executed as this is necessary to
        allow the wrapper function to call the actual process_request method.
        """
        self.execute_schedule_request()

        assert self.tpes._process_request_wrapper.called

        # While we are here, also check that args are correct.
        expected_kwargs = {"request": self.test_request}
        actual_kwargs = self.tpes._process_request_wrapper.call_args.kwargs

        assert actual_kwargs == expected_kwargs

    def test_task_created(self):
        """
        The method is expected to create a Future, verify that.
        """
        self.execute_schedule_request()

        assert "future" in self.test_request
        assert isinstance(self.test_request["future"], Future)


class TestProcessRequestWrapper(TestClassWithFixtures):
    """
    Tests for ThreadPoolExecutorService._process_request_wrapper
    """

    fixture_names = ("caplog",)

    def setup_method(self):
        os.environ["LOGLEVEL"] = "DEBUG"
        self.input_data = MagicMock()
        self.test_request = {
            "ID": uuid1(),
            "processing_started_at": None,
            "result_ready_at": None,
            "input_data": self.input_data,
        }

        self.tpes = ThreadPoolExecutorService()
        self.tpes.process_request = MagicMock()

    def test_process_request_is_called(self):
        """
        .. as this is the main functionality of the wrapper.
        """
        self.tpes.process_request = MagicMock()
        self.tpes._process_request_wrapper(request=self.test_request)

        assert self.tpes.process_request.called

        exepcted_kwargs = {"input_data": self.input_data}
        actual_kwargs = self.tpes.process_request.call_args.kwargs

        assert actual_kwargs == exepcted_kwargs

    def test_processing_started_at_value_correct(self):
        """
        This key should hold the time right before processing.
        """
        now = time.monotonic()
        self.tpes._process_request_wrapper(request=self.test_request)

        assert "processing_started_at" in self.test_request
        assert (self.test_request["processing_started_at"] - now) < 0.1

    def test_result_ready_at_value_correct(self):
        """
        This key should hold the right after the result is ready.
        """
        self.tpes._process_request_wrapper(request=self.test_request)
        now = time.monotonic()
        assert "result_ready_at" in self.test_request
        assert (now - self.test_request["result_ready_at"]) < 0.1

    def test_exception_is_logged(self):
        """
        If an exception occurred we expect the wrapper log that immediately.
        If it wouldn't do that the exception would only logged once the
        client requested the result.
        """
        self.caplog.clear()
        self.caplog.set_level(logging.ERROR)

        def side_effect(*args, **kwargs):
            raise RuntimeError("test-runtime-error")

        self.tpes.process_request = MagicMock(side_effect=side_effect)

        with pytest.raises(RuntimeError):
            self.tpes._process_request_wrapper(request=self.test_request)

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == "ERROR"
        assert "test-runtime-error" in str(records[0].exc_info[1])


class TestProcessRequest:
    """
    Tests for ThreadPoolExecutorService.process_request
    """

    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        tpes = ThreadPoolExecutorService()
        input_data = MagicMock()
        with pytest.raises(NotImplementedError):
            tpes.process_request(input_data=input_data)


class TestGetRequestStatus:
    """
    Tests for ThreadPoolExecutorService.get_request_status
    """

    def setup(self):
        os.environ["LOGLEVEL"] = "DEBUG"
        self.test_request_ID = uuid1()
        self.test_request = {"ID": self.test_request_ID}
        self.tpes = ThreadPoolExecutorService()
        self.tpes.requests[self.test_request_ID] = self.test_request

    def test_status_is_queued_if_no_task_set_yet(self):
        """
        If all threads are used already, the status should be queued
        """
        assert "future" not in self.test_request

        actual_status = asyncio.new_event_loop().run_until_complete(
            self.tpes.get_request_status(request_ID=self.test_request_ID)
        )
        actual_status_text = actual_status.status_text
        expected_status_text = "queued"

        assert actual_status_text == expected_status_text

    def test_status_is_running_if_task_done_is_false(self):
        """
        The status should be running if the future exists and done is False.
        """
        test_future = MagicMock()
        test_future.done = MagicMock(return_value=False)
        self.test_request["future"] = test_future

        actual_status = asyncio.new_event_loop().run_until_complete(
            self.tpes.get_request_status(request_ID=self.test_request_ID)
        )
        actual_status_text = actual_status.status_text
        expected_status_text = "running"

        assert actual_status_text == expected_status_text

    def test_status_is_ready_if_task_done_is_true(self):
        """
        The status should be ready if the future exists and done is True.
        """
        test_future = MagicMock()
        test_future.done = MagicMock(return_value=True)
        self.test_request["future"] = test_future

        actual_status = asyncio.new_event_loop().run_until_complete(
            self.tpes.get_request_status(request_ID=self.test_request_ID)
        )
        actual_status_text = actual_status.status_text
        expected_status_text = "ready"

        assert actual_status_text == expected_status_text


class TestGetRequestResult:
    """
    Tests for ThreadPoolExecutorService.get_request_result
    """

    def setup(self):
        os.environ["LOGLEVEL"] = "DEBUG"
        self.test_request_ID = uuid1()

        class OutputData(_BaseModel):
            test: int

        self.OutputData = OutputData

        self.test_result = {"test": 1}
        self.test_future = MagicMock()
        self.test_future.done = MagicMock(return_value=True)
        self.test_future.result = MagicMock(return_value=self.test_result)

        self.tpes = ThreadPoolExecutorService()
        self.test_request = {
            "ID": self.test_request_ID,
            "future": self.test_future,
        }
        self.tpes.OutputData = self.OutputData
        self.tpes.requests[self.test_request_ID] = self.test_request

    def test_result_is_fetched_from_task(self):
        """
        This is the expected way of fetching the result of the request.
        The result() function will also reraise any exception that FastAPI
        should return as a 500 error.
        """
        _ = asyncio.new_event_loop().run_until_complete(
            self.tpes.get_request_result(request_ID=self.test_request_ID)
        )
        assert self.test_future.result.called

    def test_output_data_object_returned(self):
        """
        By convention we expect an OutputData instance as this matches the
        configuration in __init__ .
        """
        actual_response = asyncio.new_event_loop().run_until_complete(
            self.tpes.get_request_result(request_ID=self.test_request_ID)
        )
        assert isinstance(actual_response, JSONResponse)

    def test_result_contains_output_data(self):
        """
        Further verify that the output_data object contains the result.
        """
        actual_response = asyncio.new_event_loop().run_until_complete(
            self.tpes.get_request_result(request_ID=self.test_request_ID)
        )
        assert json.loads(actual_response.body) == self.test_result

    def test_exception_in_result_is_caught(self):
        """
        It has already been logged by _process_request_wrapper so no need
        to log it again, which would happen if we just call result()
        without a try except block.
        """

        def side_effect():
            raise RuntimeError("test")

        self.test_future.result = MagicMock(side_effect=side_effect)
        with pytest.raises(HTTPException):
            _ = asyncio.new_event_loop().run_until_complete(
                self.tpes.get_request_result(request_ID=self.test_request_ID)
            )
