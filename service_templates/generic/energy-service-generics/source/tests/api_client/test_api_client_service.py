#!/usr/bin/env python3
"""
"""
from datetime import datetime
from datetime import timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from esg.api_client.service import GenericServiceClient
from esg.models.base import _BaseModel


class TestGenericServiceClientInit:
    """
    Tests for `GenericServiceClient.__init__`
    """

    def test_connection_checked(self, httpserver):
        """
        Verify that upon init, the client tries to ckeck the connection
        to the service.
        """
        httpserver.expect_request("/").respond_with_data(b"")

        _ = GenericServiceClient(base_url=httpserver.url_for("/"))

        # Check that the test server has received exactly one call.
        assert len(httpserver.log) == 1


def create_client(httpserver):
    """
    Create GenericServiceClient instance.
    This expects one request to API root fired during creating the
    client. Afterwards we clean up so that the tests can work with
    httpserver as if this call would not have happened.
    """
    httpserver.expect_oneshot_request("/").respond_with_data(b"")
    client = GenericServiceClient(base_url=httpserver.url_for("/"))
    httpserver.clear_log()
    return client


class TestGenericServiceClientPostRequestJsonable:
    """
    Tests for `GenericServiceClient.post_request_jsonable`
    """

    test_request_id = uuid4()

    def post_request(self, httpserver, client):
        """
        prevent redundant code.
        """
        test_input_data = {"test": 1}
        expected_request = httpserver.expect_request(
            "/request/", method="POST", json=test_input_data
        )
        expected_request.respond_with_json(
            {"request_ID": str(self.test_request_id)}, status=201
        )

        client.post_request_jsonable(test_input_data)

    def test_endpoint_called(self, httpserver):
        """
        Verify that the POST request endpoitn is called and the payload is
        forwared.
        """

        client = create_client(httpserver)

        self.post_request(httpserver, client)

        # Check that the test server has received exactly one call.
        assert len(httpserver.log) == 1

    def test_request_ID_stored(self, httpserver):
        """
        The request ID must be stored to allow fetching results later.
        """

        client = create_client(httpserver)

        other_id = uuid4()
        client.request_ids.append(other_id)

        self.post_request(httpserver, client)

        expected_request_id = self.test_request_id
        assert expected_request_id in client.request_ids

        # Also check that the method hasn't done stupid stuff with other
        # request IDs or inserted multiple times.
        assert other_id in client.request_ids
        assert len(client.request_ids) == 2

        # Check that the test server has received exactly one call.
        assert len(httpserver.log) == 1


class TestGenericServiceClientPostRequest:
    """
    Tests for `GenericServiceClient.post_request`
    """

    def test_post_request_jsonable_called(self, httpserver):
        """
        Verify that input data is converted using the model and that
        `post_request_jsonable` is called to call the service.
        """

        class InputModel(_BaseModel):
            test: datetime

        client = create_client(httpserver)
        client.InputModel = InputModel
        client.post_request_jsonable = MagicMock()

        test_input_data_obj = {
            "test": datetime(2022, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            # this should be removed by the model.
            "test2": 1,
        }
        client.post_request(input_data_obj=test_input_data_obj)

        assert client.post_request_jsonable.called

        call_args = client.post_request_jsonable.call_args
        expected_input_data_jsonable = {"test": "2022-01-02T03:04:05+00:00"}
        actual_input_data_jsonable = call_args.kwargs["input_data_as_jsonable"]
        assert actual_input_data_jsonable == expected_input_data_jsonable


class TestGenericServiceClientWaitForResults:
    """
    Tests for `GenericServiceClient.wait_for_results`
    """

    test_request_ids = [uuid4(), uuid4(), uuid4()]

    # JSONable representation of valid request status responses.
    status_running = {
        "status_text": "running",
        "percent_complete": None,
        "ETA_seconds": None,
    }
    status_ready = {
        "status_text": "ready",
        "percent_complete": None,
        "ETA_seconds": None,
    }

    def call_wait_for_results(self, httpserver, client, max_retries=3):
        """
        prevent redundant code.

        This will make the first call to status for the first request_id
        return "running" and subsequent calls will return "ready".
        Note that this will also cause errors (HTTP 500) if `wait_for_results`
        doesn't request in order or requests too often.
        """
        client.request_ids = self.test_request_ids

        expected_request_1 = httpserver.expect_ordered_request(
            "/request/{}/status/".format(self.test_request_ids[0]), method="GET"
        )
        expected_request_1.respond_with_json(self.status_running, status=200)

        expected_request_2 = httpserver.expect_ordered_request(
            "/request/{}/status/".format(self.test_request_ids[0]), method="GET"
        )
        expected_request_2.respond_with_json(self.status_ready, status=200)

        expected_request_3 = httpserver.expect_ordered_request(
            "/request/{}/status/".format(self.test_request_ids[1]), method="GET"
        )
        expected_request_3.respond_with_json(self.status_running, status=200)

        expected_request_4 = httpserver.expect_ordered_request(
            "/request/{}/status/".format(self.test_request_ids[1]), method="GET"
        )
        expected_request_4.respond_with_json(self.status_ready, status=200)

        expected_request_5 = httpserver.expect_ordered_request(
            "/request/{}/status/".format(self.test_request_ids[2]), method="GET"
        )
        expected_request_5.respond_with_json(self.status_ready, status=200)

        client.wait_for_results(retry_wait=0, max_retries=max_retries)

    def test_status_for_all_requests_fetched(self, httpserver):
        """
        Check that the status of all three items in `test_request_ids` has
        been fetched. Based on `self.call_wait_for_results` the method
        should need exactly 5 calls to the status endpoint for this.
        """
        client = create_client(httpserver)
        self.call_wait_for_results(httpserver, client)

    def test_all_requests_finished_set(self, httpserver):
        """
        We expect this flat to be set once everything is done.
        """
        client = create_client(httpserver)
        self.call_wait_for_results(httpserver, client)

        assert client.all_requests_finished is True

    def test_client_request_ids_not_changed(self, httpserver):
        """
        Verify that the method hasn't altered `client.request_ids`.
        It is need to fetch the results.


        """
        client = create_client(httpserver)
        self.call_wait_for_results(httpserver, client)

        # Should be OK if it is as long as before the call.
        assert len(client.request_ids) == 3

    def test_raises_on_timeout(self, httpserver):
        """
        Verify a timeout raises as documented in the docstring.
        """
        client = create_client(httpserver)
        with pytest.raises(RuntimeError):
            self.call_wait_for_results(httpserver, client, max_retries=1)


class TestGenericServiceClientGetResultJsonable:
    """
    Tests for `GenericServiceClient.get_result_jsonable`
    """

    test_request_ids = [uuid4(), uuid4(), uuid4()]
    test_output_data = [
        {"out": "2022-01-02T03:04:05+00:00"},
        {"out": "2022-01-02T03:04:06+00:00"},
        {"out": "2022-01-02T03:04:07+00:00"},
    ]

    def get_result(self, httpserver, client):
        """
        prevent redundant code.
        """
        expected_request_1 = httpserver.expect_ordered_request(
            "/request/{}/result/".format(self.test_request_ids[0]),
            method="GET",
        )
        expected_request_1.respond_with_json(
            self.test_output_data[0], status=200
        )

        expected_request_2 = httpserver.expect_ordered_request(
            "/request/{}/result/".format(self.test_request_ids[1]),
            method="GET",
        )
        expected_request_2.respond_with_json(
            self.test_output_data[1], status=200
        )

        expected_request_2 = httpserver.expect_ordered_request(
            "/request/{}/result/".format(self.test_request_ids[2]),
            method="GET",
        )
        expected_request_2.respond_with_json(
            self.test_output_data[2], status=200
        )

        # Mock prevents that we need to define additional expected requests.
        client.wait_for_results = MagicMock()
        client.request_ids = self.test_request_ids.copy()

        return client.get_result_jsonable()

    def test_wait_for_results_called(self, httpserver):
        """
        If not fetching the result may block and cause nasty errors like
        gateway timeouts and stuff.
        """
        client = create_client(httpserver)
        client.wait_for_results = MagicMock()

        _ = self.get_result(httpserver, client)

        assert client.wait_for_results.called

    def test_endpoint_called(self, httpserver):
        """
        """
        client = create_client(httpserver)
        client.wait_for_results = MagicMock()

        _ = self.get_result(httpserver, client)

        assert len(httpserver.log) == 3

    def test_request_ids_cleared_after_fetched(self, httpserver):
        """
        Verify that the request IDs that have been fetched already will
        be removed. Else the client will continue to fetch all previous
        results too.
        """
        client = create_client(httpserver)
        client.wait_for_results = MagicMock()

        _ = self.get_result(httpserver, client)

        assert len(client.request_ids) == 0

    def test_results_correct_and_in_order(self, httpserver):
        """
        Ordering is important here, as this is the only link to the requests.
        """
        client = create_client(httpserver)
        client.wait_for_results = MagicMock()

        output_data_jsonable = self.get_result(httpserver, client)

        assert output_data_jsonable == self.test_output_data


class TestGenericServiceClientGetResult:
    """
    Tests for `GenericServiceClient.get_result`
    """

    def test_get_result_jsonable_called(self, httpserver):
        """
        Verify that output data is converted using the model and that
        `get_result_jsonable` is called to retrueve the result.
        """

        class OutputModel(_BaseModel):
            out: datetime

        test_output_data = [
            {"out": "2022-01-02T03:04:05+00:00"},
            {"out": "2022-01-02T03:04:06+00:00"},
            {"out": "2022-01-02T03:04:07+00:00"},
        ]

        client = create_client(httpserver)
        client.OutputModel = OutputModel
        client.get_result_jsonable = MagicMock(return_value=test_output_data)

        actual_output_data = client.get_results()

        assert client.get_result_jsonable.called

        expected_output_data = [
            {"out": datetime(2022, 1, 2, 3, 4, 5, tzinfo=timezone.utc)},
            {"out": datetime(2022, 1, 2, 3, 4, 6, tzinfo=timezone.utc)},
            {"out": datetime(2022, 1, 2, 3, 4, 7, tzinfo=timezone.utc)},
        ]

        assert actual_output_data == expected_output_data
