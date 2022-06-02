#!/usr/bin/env python3
"""
Basic stuff for HTTP clients.

Check out this page to get some inspiration on advanded stuff like
retries and timeouts:
https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
"""
import json
import logging
from urllib3 import disable_warnings

import requests


logger = logging.getLogger(__name__)


class HttpBaseClient:
    """
    Generic setup and configuration for HTTP(s) clients.

    This client implements wrappers around the fundamental http
    methods GET, POST, PUT and DELETE. All methods expect a `relative_url`
    which is appended to `base_url` to compute the final URL.
    """

    def __init__(self, base_url, verify=True, username=None, password=None):
        """
        Set up the session for all requests.

        Arguments:
        ----------
        base_url: str
            The root URL of the API, e.g. `http://localhost:8080/api`
        verify: bool
            If set to `False` will disable certificate checking.
            Useful if self signed certificates are used but a potential
            security risk. See also the requests docs on the topic:
            https://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification
        username: str
            The username to use for HTTP basic auth. Only used in combination
            with `password`.
        password: str
            The username to use for HTTP basic auth. Only used in combination
            with `username`.
        """
        self.base_url = base_url
        self.verify = verify

        # urllib3 would emit one warning for EVERY made without verification.
        if not self.verify:
            disable_warnings()
            # This is basically the same warning urllib3 emits, but just onnce.
            logger.warning(
                "Client will make unverified HTTPS request to host `{}`. "
                "Adding certificate verification is strongly advised."
                "".format(self.base_url)
            )

        self.http = requests.Session()

        if username is None or password is None:
            self.auth = None
        else:
            self.auth = requests.auth.HTTPBasicAuth(
                username=username, password=password
            )

        # Automatically check the status code for every request.
        def assert_status_hook(response, *args, **kwargs):
            # Log validation errors, these contain more information about
            # what went wrong.
            if response.status_code in [400, 422]:
                try:
                    error_detail = json.dumps(response.json(), indent=4)
                except requests.exceptions.JSONDecodeError:
                    # Some errors are not JSON, especially those
                    # directly returned by Django in DEBUG model
                    error_detail = response.text
                logger.error(
                    "HTTP request returned error: \n{}".format(error_detail)
                )

            response.raise_for_status()

        self.http.hooks["response"] = [assert_status_hook]

    def compute_full_url(self, relative_url):
        """
        Computes a full URL based on `self.base_url` and `relative_url`
        """
        # The strings are here in case someone provided a Path object.
        full_url = str(self.base_url)
        relative_url = str(relative_url)

        # People may not take care and leave a trailing slash at `base_url`
        # and provide a leading slash too. Remove these, they are almost
        # surley not desired.
        if full_url[-1] == "/" and relative_url[0] == "/":
            full_url += relative_url[1:]
        else:
            full_url += relative_url

        return full_url

    def get(self, relative_url, *args, **kwargs):
        full_url = self.compute_full_url(relative_url=relative_url)
        response = self.http.get(
            full_url, *args, auth=self.auth, verify=self.verify, **kwargs
        )
        return response

    def post(self, relative_url, *args, **kwargs):
        full_url = self.compute_full_url(relative_url=relative_url)
        response = self.http.post(
            full_url, *args, auth=self.auth, verify=self.verify, **kwargs
        )
        return response

    def put(self, relative_url, *args, **kwargs):
        full_url = self.compute_full_url(relative_url=relative_url)
        response = self.http.put(
            full_url, *args, auth=self.auth, verify=self.verify, **kwargs
        )
        return response

    def delete(self, relative_url, *args, **kwargs):
        full_url = self.compute_full_url(relative_url=relative_url)
        response = self.http.delete(
            full_url, *args, auth=self.auth, verify=self.verify, **kwargs
        )
        return response
