#!/usr/bin/env python3
"""
"""
import os
import asyncio
import logging
from uuid import uuid1
from uuid import UUID
from unittest.mock import MagicMock
import time

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
import pytest

from esg.models.request import RequestId
from esg.services.base import BaseService
from esg.services.base import GenericUnexpctedException
from esg.services.base import RequestInducedException
from esg.test.tools import async_return
from esg.test.tools import TestClassWithFixtures


class TestGenericUnexpctedException:
    def test_raises_with_code_500(self):
        """
        Verify that the expected HTTPExpection is raised with the expected
        HTTP status code.
        """
        with pytest.raises(HTTPException) as e:
            raise GenericUnexpctedException()

        assert e.value.status_code == 500

    def test_detail_message_is_provided(self):
        """
        We expect a detail providing generic info that there was an error
        while processing the the request.
        """
        with pytest.raises(HTTPException) as e:
            raise GenericUnexpctedException(status_code=500)

        for expected_word in ["service", "encountered", "error", "request."]:
            assert expected_word in e.value.detail

    def test_detail_message_can_contain_request_ID(self):
        """
        If provided the requestID should be part of the detail message.
        """
        test_uuid = uuid1()
        with pytest.raises(HTTPException) as e:
            raise GenericUnexpctedException(request_ID=test_uuid)

        assert str(test_uuid) in e.value.detail


class TestRequestInducedException:
    def test_raises_with_code_400(self):
        """
        Verify that the expected HTTPExpection is raised with the expected
        HTTP status code.
        """
        expected_detail = "The reason for this error is 42."
        with pytest.raises(HTTPException) as e:
            raise RequestInducedException(detail=expected_detail)

        assert e.value.status_code == 400

    def test_provided_detail_is_in_exception(self):
        """
        Verify that the detail argument is forwarded.
        """
        expected_detail = "The reason for this error is 42."
        with pytest.raises(HTTPException) as e:
            raise RequestInducedException(detail=expected_detail)

        assert expected_detail == e.value.detail


class TestInit(TestClassWithFixtures):

    fixture_names = ("caplog",)

    def test_environment_variables_loaded(self):
        """
        Verify that the environment variable settings are parsed to the
        expected values.
        """
        os.environ["LOGLEVEL"] = "CRITICAL"
        os.environ["GC_FETCHED_REQUESTS_AFTER_S"] = "150"
        os.environ["GC_FINISHED_REQUESTS_AFTER_S"] = "1800"
        os.environ["ROOT_PATH"] = "/test/v1/"
        os.environ["VERSION"] = "0.1.0"

        bs = BaseService()

        assert bs._loglevel == logging.CRITICAL
        assert bs.gc_fetched_requests_after_seconds == 150
        assert bs.gc_finished_requests_after_seconds == 1800
        assert bs.fastapi_root_path == "/test/v1/"
        assert bs.fastapi_version == "0.1.0"

    def test_default_environment_variables(self):
        """
        Check that the environment variables have the expected values,
        i.e. those defined in the Readme.
        """
        os.environ["LOGLEVEL"] = ""
        os.environ["GC_FETCHED_REQUESTS_AFTER_S"] = ""
        os.environ["GC_FINISHED_REQUESTS_AFTER_S"] = ""
        os.environ["ROOT_PATH"] = ""
        os.environ["VERSION"] = ""
        bs = BaseService()

        assert bs._loglevel == logging.INFO
        assert bs.gc_fetched_requests_after_seconds == 300
        assert bs.gc_finished_requests_after_seconds == 3600
        assert bs.fastapi_root_path == ""
        assert bs.fastapi_version == "unknown"

    def test_logger_available(self):
        """
        Verify that it is possible to use the logger of the service to create
        log messages.
        """
        # Set the environment variable to nothing, to let the default value
        # kick in.
        os.environ["LOGLEVEL"] = ""

        bs = BaseService()

        self.caplog.clear()

        bs.logger.info("A test info message")

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == "INFO"
        assert records[0].message == "A test info message"

    def test_loglevel_changed(self):
        """
        Verify that it is possible to change ot logging level of the logger
        by setting the corresponding environment variable.
        """
        os.environ["LOGLEVEL"] = "WARNING"
        bs = BaseService()

        self.caplog.clear()

        # This message should not appear in the log,
        bs.logger.info("A test info message")
        # .. while this message should due to LOGLEVEL set to WARNING.
        bs.logger.warning("A test warning message")

        records = self.caplog.records
        assert len(records) == 1
        assert records[0].levelname == "WARNING"
        assert records[0].message == "A test warning message"

    def test_attributes_are_created(self):
        """
        Verify that the class attributes expected by other methods are
        exposed.
        """

        class TestInputData(BaseModel):
            test1: str

        class TestOutputData(BaseModel):
            test2: float

        bs = BaseService(InputData=TestInputData, OutputData=TestOutputData)

        assert bs.InputData == TestInputData
        assert bs.OutputData == TestOutputData
        assert hasattr(bs, "requests")
        assert isinstance(bs.app, FastAPI)


class TestPostRequest:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        bs = BaseService()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(bs.post_request())


class TestHandlePostRequest:
    def setup(self):
        self.event_loop = asyncio.new_event_loop()

        self.bs = BaseService()
        self.test_uuid = uuid1()
        request_values = {
            "ID": self.test_uuid,
        }
        self.test_request = MagicMock()
        self.test_request.__getitem__.side_effect = request_values.__getitem__
        self.bs.create_request = MagicMock(return_value=(self.test_request))
        self.bs.schedule_request_processing = MagicMock(
            return_value=async_return(loop=self.event_loop)
        )
        self.input_data = MagicMock()

    def test_create_request_is_called(self):
        """
        Verify that the intended method for creating requests is used.
        """
        _ = self.event_loop.run_until_complete(
            self.bs.handle_post_request(input_data=self.input_data)
        )

        assert self.bs.create_request.called
        assert "input_data" in self.bs.create_request.call_args.kwargs
        assert (
            self.bs.create_request.call_args.kwargs["input_data"]
            == self.input_data
        )

    def test_request_is_added_to_requests(self):
        """
        .. as the get_request_status and get_request_result methods use the
        self.requests dict to pick up the request matching the request_ID.
        """
        assert self.bs.requests == {}
        _ = self.event_loop.run_until_complete(
            self.bs.handle_post_request(input_data=self.input_data)
        )
        assert len(self.bs.requests) == 1
        assert self.test_uuid in self.bs.requests
        assert self.bs.requests[self.test_uuid] == self.test_request

    def test_response_is_RequestId_instance(self):
        """
        As this is what we have told the API schema in __init__.
        """
        response = self.event_loop.run_until_complete(
            self.bs.handle_post_request(input_data=self.input_data)
        )
        assert isinstance(response, RequestId)

    def test_uuid_in_response(self):
        """
        Verify that the unique ID computed by create_request part of the
        response as expected.
        """
        response = self.event_loop.run_until_complete(
            self.bs.handle_post_request(input_data=self.input_data)
        )
        assert response.request_ID == self.test_uuid

    def test_schedule_request_processing_is_called(self):
        """
        As without calling this method the response might never be computed.
        """
        _ = self.event_loop.run_until_complete(
            self.bs.handle_post_request(input_data=self.input_data)
        )

        assert self.bs.schedule_request_processing.called
        call_args = self.bs.schedule_request_processing.call_args
        assert call_args.kwargs["request"] == self.test_request


class TestCreateRequest:
    """
    Some straight forward tests to check that the created request object
    contains all the stuff it is supposed to have. See the docstring
    if create_request for more details.
    """

    def setup(self):
        self.input_data = MagicMock()
        bs = BaseService()
        self.actual_request = bs.create_request(input_data=self.input_data)

    def test_request_is_dict(self):
        assert isinstance(self.actual_request, dict)

    def test_ID_present_and_value_correct(self):
        assert "ID" in self.actual_request
        assert isinstance(self.actual_request["ID"], UUID)

    def test_input_data_present_and_value_correct(self):
        assert "input_data" in self.actual_request
        assert self.actual_request["input_data"] is self.input_data

    def test_created_at_present_and_value_correct(self):
        now = time.monotonic()
        assert "created_at" in self.actual_request
        assert (now - self.actual_request["created_at"]) < 0.5

    def test_processing_started_at_present_and_value_correct(self):
        assert "processing_started_at" in self.actual_request
        assert self.actual_request["processing_started_at"] is None

    def test_result_ready_at_present_and_value_correct(self):
        assert "result_ready_at" in self.actual_request
        assert self.actual_request["result_ready_at"] is None

    def test_result_last_fetched_at_present_and_value_correct(self):
        assert "result_last_fetched_at" in self.actual_request
        assert self.actual_request["result_last_fetched_at"] is None


class TestScheduleRequestProcessing:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        bs = BaseService()
        request = MagicMock()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(
                bs.schedule_request_processing(request=request)
            )


class TestProcessRequest:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        bs = BaseService()
        input_data = MagicMock()
        with pytest.raises(NotImplementedError):
            bs.process_request(input_data=input_data)


class TestGetRequestOrRaise:
    def test_existing_request_is_returned(self):
        """
        Verify that the method returns a request object if it exists in
        BaseService.requests.
        """
        test_request_ID = uuid1()
        test_request = MagicMock()
        bs = BaseService()
        bs.requests[test_request_ID] = test_request

        actual_request = bs.get_request_or_raise(request_ID=test_request_ID)
        assert actual_request == test_request

    def test_non_exsting_request_raises_404(self):
        """
        Non existing IDs should trigger an exception for the user to notice.
        """
        test_request_ID = uuid1()
        bs = BaseService()
        with pytest.raises(HTTPException):
            bs.get_request_or_raise(request_ID=test_request_ID)

    def test_last_fetched_at_is_set(self):
        """
        This is required for correct garbage collection.
        """
        bs = BaseService()
        test_request = bs.create_request(input_data=None)
        bs.requests[test_request["ID"]] = test_request

        now = time.monotonic()
        actual_request = bs.get_request_or_raise(request_ID=test_request["ID"])

        now = time.monotonic()
        assert "result_last_fetched_at" in actual_request
        assert actual_request["result_last_fetched_at"] is not None
        assert (now - actual_request["result_last_fetched_at"]) < 0.5


class TestHandleGetRequestStatus:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        bs = BaseService()
        request_id = MagicMock()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(
                bs.get_request_status(request_id=request_id)
            )


class TestHandleGetRequestResult:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        bs = BaseService()
        request_id = MagicMock()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(
                bs.get_request_result(request_id=request_id)
            )


class TestPostRequestAndReturnResult:
    def test_exception_raised_if_not_overloaded(self):
        """
        Check that an exception is raised if the method is not overloaded
        as expected, to remind the developer that they have forgotten about it.
        """
        bs = BaseService()
        input_data = MagicMock()
        with pytest.raises(NotImplementedError):
            asyncio.new_event_loop().run_until_complete(
                bs.post_request_and_return_result(input_data=input_data)
            )


class TestHandlePostRequestAndReturnResult:
    def setup_method(self):
        self.event_loop = asyncio.new_event_loop()

        request_ID = uuid1()
        self.test_request_id = RequestId(request_ID=request_ID)
        self.test_result = MagicMock()

        self.bs = BaseService()
        self.bs.handle_post_request = MagicMock(
            return_value=async_return(
                return_value=self.test_request_id, loop=self.event_loop
            )
        )
        self.bs.get_request_result = MagicMock(
            return_value=async_return(
                return_value=self.test_result, loop=self.event_loop
            )
        )
        self.bs.requests = {request_ID: MagicMock()}

    def execute_handle_post_request_and_return_result(self, *args, **kwargs):
        """
        Simple wrapper that handles the asyncio related hazzle.
        """
        return self.event_loop.run_until_complete(
            self.bs.handle_post_request_and_return_result(*args, **kwargs)
        )

    def test_handle_post_request_called_correctly(self):
        """
        The tested method must forward `input_data` to `handle_post_request`
        to trigger processing of the request.
        """
        input_data = MagicMock()

        _ = self.execute_handle_post_request_and_return_result(
            input_data=input_data
        )

        assert self.bs.handle_post_request.called

        expected_kwargs = {"input_data": input_data}
        actual_kwargs = self.bs.handle_post_request.call_args.kwargs

        assert actual_kwargs == expected_kwargs

    def test_handle_get_request_result_called_correctly(self):
        """
        The tested method must forward the computed request ID
        `get_request_result` to trigger retrieval of the result.
        """
        _ = self.execute_handle_post_request_and_return_result(
            input_data=MagicMock()
        )

        assert self.bs.get_request_result.called

        expected_kwargs = {"request_ID": self.test_request_id.request_ID}
        actual_kwargs = self.bs.get_request_result.call_args.kwargs

        assert actual_kwargs == expected_kwargs

    def test_result_returned(self):
        """
        The output of `get_request_result` should be returned.
        """
        expected_result = self.test_result

        actual_result = self.execute_handle_post_request_and_return_result(
            input_data=MagicMock()
        )

        assert actual_result == expected_result

    def test_result_garbage_collected(self):
        """
        The result should be removed from memory immediately after retrieval.
        """
        _ = self.execute_handle_post_request_and_return_result(
            input_data=MagicMock()
        )
        assert len(self.bs.requests) == 0


class TestGarbageCollectRequests:
    def setup(self):
        os.environ["GC_FETCHED_REQUESTS_AFTER_S"] = "100"
        os.environ["GC_FINISHED_REQUESTS_AFTER_S"] = "200"
        self.bs = BaseService()

    def test_scheduled_request_is_not_collected(self):
        """
        Verify that a request that has already been fetched is not garbage
        collected before the time specified in GC_FETCHED_REQUESTS_AFTER_S
        is reached.
        """
        request = self.bs.create_request(input_data=None)
        request["result_last_fetched_at"] = None
        request["result_ready_at"] = None
        self.bs.requests[request["ID"]] = request

        self.bs.garbage_collect_requests()

        assert request["ID"] in self.bs.requests

    def test_fetched_request_is_not_collected_before_it_is_time(self):
        """
        Verify that a request that has already been fetched is not garbage
        collected before the time specified in GC_FETCHED_REQUESTS_AFTER_S
        is reached.
        """
        request = self.bs.create_request(input_data=None)
        request["result_last_fetched_at"] = time.monotonic() - 90
        self.bs.requests[request["ID"]] = request

        self.bs.garbage_collect_requests()

        assert request["ID"] in self.bs.requests

    def test_fetched_request_is_collected_once_it_is_time(self):
        """
        Verify that a request that has already been fetched is garbage
        collected once the time specified in GC_FETCHED_REQUESTS_AFTER_S
        has passed reached.
        """
        request = self.bs.create_request(input_data=None)
        request["result_last_fetched_at"] = time.monotonic() - 110
        self.bs.requests[request["ID"]] = request

        self.bs.garbage_collect_requests()

        assert request["ID"] not in self.bs.requests

    def test_finished_request_is_not_collected_before_it_is_time(self):
        """
        Verify that a request that has already been fetched is not garbage
        collected before the time specified in GC_FETCHED_REQUESTS_AFTER_S
        is reached.
        """
        request = self.bs.create_request(input_data=None)
        request["result_last_fetched_at"] = None
        request["result_ready_at"] = time.monotonic() - 190
        self.bs.requests[request["ID"]] = request

        self.bs.garbage_collect_requests()

        assert request["ID"] in self.bs.requests

    def test_finished_request_is_collected_once_it_is_time(self):
        """
        Verify that a request that has already been fetched is garbage
        collected once the time specified in GC_FETCHED_REQUESTS_AFTER_S
        has passed reached.
        """
        request = self.bs.create_request(input_data=None)
        request["result_last_fetched_at"] = None
        request["result_ready_at"] = time.monotonic() - 210
        self.bs.requests[request["ID"]] = request

        self.bs.garbage_collect_requests()

        assert request["ID"] not in self.bs.requests


class TestRequestsGarbageCollector:
    def setup(self):
        self.bs = BaseService()
        self.bs._GC_SLEEP_SECONDS = 0.1
        self.bs.garbage_collect_requests = MagicMock(
            # Allows us to terminate the GC cycle.
            side_effect=KeyboardInterrupt()
        )

    def test_garbage_collect_requests_is_called(self):
        """
        At least check that worker has executed the target function once,
        although we expect that it will do it periodically.
        """
        try:
            self.bs.requests_garbage_collector()
        except KeyboardInterrupt:
            pass

        assert self.bs.garbage_collect_requests.called


class TestRun:
    def setup(self):
        os.environ["LOGLEVEL"] = "INFO"
        self.bs = BaseService()
        # This would run forever if we would not raise.
        self.bs.app = MagicMock(side_effect=KeyboardInterrupt())

    def test_close_executed(self):
        """
        The run method should call the close method clean up.
        """
        self.bs.close = MagicMock()

        try:
            self.bs.run()
        except KeyboardInterrupt:
            pass

        assert self.bs.close.called

    def test_garbage_collector_task_created(self):
        """
        Verify that the run method executed the garbage collector.
        """
        self.bs.requests_garbage_collector = MagicMock()

        try:
            self.bs.run()
        except KeyboardInterrupt:
            pass

        assert self.bs.requests_garbage_collector.called
