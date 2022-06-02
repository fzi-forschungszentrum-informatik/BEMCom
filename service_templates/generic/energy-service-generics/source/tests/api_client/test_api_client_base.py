#!/usr/bin/env python3
"""
"""
import pytest
import requests
from unittest.mock import MagicMock

from esg.api_client.base import HttpBaseClient


class TestHttpBaseClientInit:
    """
    Tests for `HttpBaseClient.__init__`
    """

    def test_session_created(self, httpserver):
        """
        Verify that init creates a session and this can be used to make http
        calls. Also checks that the test http server works.
        """
        client = HttpBaseClient(base_url=httpserver.url_for("/"))

        httpserver.expect_request("/").respond_with_data(b"")

        response = client.http.get(httpserver.url_for("/"))
        assert response.status_code == 200

    def test_session_raises_on_error(self, httpserver):
        """
        We expect an automatic exception on error responses from session hook.
        """
        client = HttpBaseClient(base_url=httpserver.url_for("/"))

        # Test typical error responses
        for error_status in [400, 401, 403, 404, 500, 503, 504]:
            httpserver.expect_request("/").respond_with_data(
                b"", status=error_status
            )
            with pytest.raises(requests.exceptions.HTTPError):
                _ = client.http.get(httpserver.url_for("/"))

    def test_basic_auth_object_created(self):
        """
        Verify that if username and password are provided, these
        trigger the createion of a `requests.auth.HTTPBasicAuth` object.
        """
        # First check that if no username, or just username or password
        # is provided auth should be None
        client = HttpBaseClient(base_url="http://localhost")
        assert client.auth is None
        client = HttpBaseClient(base_url="http://localhost", username="user")
        assert client.auth is None
        client = HttpBaseClient(base_url="http://localhost", password="pass")
        assert client.auth is None

        # Finally, if both are provided, the auth object should be populated.
        test_username = MagicMock()
        test_password = MagicMock()
        client = HttpBaseClient(
            base_url="http://localhost",
            username=test_username,
            password=test_password,
        )
        assert isinstance(client.auth, requests.auth.HTTPBasicAuth)
        assert client.auth.username == test_username
        assert client.auth.password == test_password


class TestHttpBaseClientComputeFullUrl:
    """
    Tests for `HttpBaseClient.compute_full_url`
    """

    def test_urls_combined(self):
        """
        Test the basic functionality works.
        """
        client = HttpBaseClient(base_url="http://localhost:8080/api")

        expected_full_url = "http://localhost:8080/api/datapoint/"
        actual_full_url = client.compute_full_url("/datapoint/")

        assert actual_full_url == expected_full_url

    def test_double_slashes_removed(self):
        """
        People may not take care and leave a trailing slash at `base_url`
        and provide a leading slash too. Remove these, they are almost
        surley not desired.
        """
        client = HttpBaseClient(base_url="http://localhost:8080/api/")

        expected_full_url = "http://localhost:8080/api/datapoint/"
        actual_full_url = client.compute_full_url("/datapoint/")

        assert actual_full_url == expected_full_url


class GenericHttpBaseClientHttpMethodsTests:
    """
    Generic tests for `HttpBaseClient`'s HTTP methods.
    """

    http_method = "get"

    def test_uses_sessions(self):
        """
        Test that the session object is used (for automatic status code check).
        """
        client = HttpBaseClient(base_url="http://localhost:8080/api")
        client.http = MagicMock()

        _ = getattr(client, self.http_method)("/")

        assert getattr(client.http, self.http_method).called

    def test_used_url_correct(self):
        """
        Verify that the full_url is used in the request.
        """
        client = HttpBaseClient(base_url="http://localhost:8080/api")
        client.http = MagicMock()

        _ = getattr(client, self.http_method)("/datapoint/")

        expected_full_url = "http://localhost:8080/api/datapoint/"
        call_args = getattr(client.http, self.http_method).call_args
        actual_full_url = call_args.args[0]

        assert actual_full_url == expected_full_url

    def test_args_and_kwargs_forwarded(self):
        """
        User may want to forward stuff like data for the body and query params.
        """
        client = HttpBaseClient(base_url="http://localhost:8080/api")
        client.http = MagicMock()

        _ = getattr(client, self.http_method)("/datapoint/", "a", "b", c="d")

        expected_args = ("a", "b")
        expected_kwargs = {"c": "d"}
        call_args = getattr(client.http, self.http_method).call_args
        actual_args = call_args.args[1:]
        actual_kwargs = call_args.kwargs

        for expected_arg in expected_args:
            assert expected_arg in actual_args
        for parameter in expected_kwargs:
            assert parameter in actual_kwargs
            assert actual_kwargs[parameter] == expected_kwargs[parameter]

    def test_auth_used(self):
        """
        Verify that the calls use the auth object provided by the client.
        """
        client = HttpBaseClient(base_url="http://localhost:8080/api")
        client.http = MagicMock()
        client.auth = MagicMock()

        _ = getattr(client, self.http_method)("/datapoint/")

        call_kwargs = getattr(client.http, self.http_method).call_args.kwargs
        assert "auth" in call_kwargs
        assert call_kwargs["auth"] == client.auth


class TestHttpBaseClientComputeGet(GenericHttpBaseClientHttpMethodsTests):
    """
    Tests for `HttpBaseClient.get`.
    """

    http_method = "get"


class TestHttpBaseClientComputePost(GenericHttpBaseClientHttpMethodsTests):
    """
    Tests for `HttpBaseClient.get`.
    """

    http_method = "post"


class TestHttpBaseClientComputePut(GenericHttpBaseClientHttpMethodsTests):
    """
    Tests for `HttpBaseClient.get`.
    """

    http_method = "put"


class TestHttpBaseClientComputeDelete(GenericHttpBaseClientHttpMethodsTests):
    """
    Tests for `HttpBaseClient.get`.
    """

    http_method = "delete"
