#!/usr/bin/env python3
"""
"""
import os
import asyncio
import json
import logging
import time
from uuid import uuid1
from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.responses import JSONResponse
import pytest

from esg.models.base import _BaseModel
from esg.services.asyncio import AsyncioTaskService
from esg.test.tools import async_return
from esg.test.tools import TestClassWithFixtures


class TestPostRequest:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        ats = AsyncioTaskService()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(ats.post_request())


class TestScheduleRequestProcessing:
    def setup(self):
        self.test_request = {"ID": uuid1()}

        async def _process_request_wrapper(request):
            await asyncio.sleep(0.05)
            request["was_executed"] = True

        async def schedule_and_execute():
            await self.ats.schedule_request_processing(
                request=self.test_request
            )
            await self.test_request["task"]

        self.ats = AsyncioTaskService()
        self.ats._process_request_wrapper = _process_request_wrapper
        asyncio.new_event_loop().run_until_complete(schedule_and_execute())
        # asyncio.new_event_loop().run_until_complete()

    def test_task_created(self):
        """
        The method is expected to create a task, verify that.
        """
        assert "task" in self.test_request
        assert isinstance(self.test_request["task"], asyncio.Task)

    def test_process_request_wrapper_is_executed(self):
        """
        Verify that the wrapper function is executed as this is necessary to
        allow the wrapper function to call the actual process_request method.
        """
        assert "was_executed" in self.test_request


class TestProcessRequestWrapper(TestClassWithFixtures):

    fixture_names = ("caplog",)

    def setup_class(cls):
        os.environ["LOGLEVEL"] = "DEBUG"
        cls.input_data = MagicMock()
        cls.test_request = {
            "ID": uuid1(),
            "processing_started_at": None,
            "result_ready_at": None,
            "input_data": cls.input_data,
        }

        async def process_request(input_data):
            await asyncio.sleep(0.2)

        cls.ats = AsyncioTaskService()
        cls.ats.process_request = process_request

    def test_process_request_is_called(self):
        """
        .. as this is the main functionality of the wrapper.
        """
        event_loop = asyncio.new_event_loop()

        self.ats.process_request = MagicMock(
            return_value=async_return(loop=event_loop)
        )

        event_loop.run_until_complete(
            self.ats._process_request_wrapper(request=self.test_request)
        )
        assert self.ats.process_request.called
        exepcted_kwargs = {"input_data": self.input_data}
        actual_kwargs = self.ats.process_request.call_args.kwargs
        assert actual_kwargs == exepcted_kwargs

    def test_processing_started_at_value_correct(self):
        """
        This key should hold the time right before processing.
        """
        now = time.monotonic()
        asyncio.new_event_loop().run_until_complete(
            self.ats._process_request_wrapper(request=self.test_request)
        )
        assert "processing_started_at" in self.test_request
        assert (self.test_request["processing_started_at"] - now) < 0.1

    def test_result_ready_at_value_correct(self):
        """
        This key should hold the right after the result is ready.
        """
        asyncio.new_event_loop().run_until_complete(
            self.ats._process_request_wrapper(request=self.test_request)
        )
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

        self.ats.process_request = MagicMock(side_effect=side_effect)

        with pytest.raises(RuntimeError):
            asyncio.new_event_loop().run_until_complete(
                self.ats._process_request_wrapper(request=self.test_request)
            )

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == "ERROR"
        assert "test-runtime-error" in str(records[0].exc_info[1])


class TestProcessRequest:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        ats = AsyncioTaskService()
        input_data = MagicMock()
        with pytest.raises(NotImplementedError):
            coro = ats.process_request(input_data=input_data)
            asyncio.new_event_loop().run_until_complete(coro)


class TestGetRequestStatus:
    def setup(self):
        os.environ["LOGLEVEL"] = "DEBUG"
        self.test_request_ID = uuid1()
        self.test_request = {"ID": self.test_request_ID}
        self.ats = AsyncioTaskService()
        self.ats.requests[self.test_request_ID] = self.test_request

    def test_status_is_queued_if_no_task_set_yet(self):
        """
        This should actually not happen for this template as the
        request is scheduled for execution even before the POST /request/
        call retruns. But for completeness let's check that such scenario
        returns the queued status.
        """
        assert "task" not in self.test_request
        actual_status = asyncio.new_event_loop().run_until_complete(
            self.ats.get_request_status(request_ID=self.test_request_ID)
        )
        actual_status_text = actual_status.status_text
        expected_status_text = "queued"
        assert actual_status_text == expected_status_text

    def test_status_is_running_if_task_done_is_false(self):
        """
        The task should be running if the task exists and done is False.
        """
        test_task = MagicMock()
        test_task.done = MagicMock(return_value=False)
        self.test_request["task"] = test_task

        actual_status = asyncio.new_event_loop().run_until_complete(
            self.ats.get_request_status(request_ID=self.test_request_ID)
        )
        actual_status_text = actual_status.status_text
        expected_status_text = "running"
        assert actual_status_text == expected_status_text

    def test_status_is_ready_if_task_done_is_false(self):
        """
        The task should be running if the task exists and done is False.
        """
        test_task = MagicMock()
        test_task.done = MagicMock(return_value=True)
        self.test_request["task"] = test_task

        actual_status = asyncio.new_event_loop().run_until_complete(
            self.ats.get_request_status(request_ID=self.test_request_ID)
        )
        actual_status_text = actual_status.status_text
        expected_status_text = "ready"
        assert actual_status_text == expected_status_text


class TestGetRequestResult:
    def setup(self):
        self.event_loop = asyncio.new_event_loop()
        os.environ["LOGLEVEL"] = "DEBUG"
        self.test_request_ID = uuid1()

        class OutputData(_BaseModel):
            test: int

        self.OutputData = OutputData

        self.test_result = {"test": 1}
        self.test_task = MagicMock(
            return_value=async_return(loop=self.event_loop)
        )()
        self.test_task.result = MagicMock(return_value=self.test_result)

        self.ats = AsyncioTaskService()
        self.test_request = {"ID": self.test_request_ID, "task": self.test_task}
        self.ats.OutputData = self.OutputData
        self.ats.requests[self.test_request_ID] = self.test_request

    def test_result_is_fetched_from_task(self):
        """
        This is the expected way of fetching the result of the request.
        The result() function will also reraise any exception that FastAPI
        should return as a 500 error.
        """
        _ = self.event_loop.run_until_complete(
            self.ats.get_request_result(request_ID=self.test_request_ID)
        )
        assert self.test_task.result.called

    def test_json_response_returned(self):
        """
        As documented we expect an JSONResponse instance, as this allows us
        to use the custom json dump logic of `esg.models.base._BaseModel`.
        """
        actual_response = self.event_loop.run_until_complete(
            self.ats.get_request_result(request_ID=self.test_request_ID)
        )
        assert isinstance(actual_response, JSONResponse)

    def test_result_contains_output_data(self):
        """
        Finally verify that the output_data object contains the result.
        """
        actual_response = self.event_loop.run_until_complete(
            self.ats.get_request_result(request_ID=self.test_request_ID)
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

        self.test_task.result = MagicMock(side_effect=side_effect)
        with pytest.raises(HTTPException):
            _ = self.event_loop.run_until_complete(
                self.ats.get_request_result(request_ID=self.test_request_ID)
            )
