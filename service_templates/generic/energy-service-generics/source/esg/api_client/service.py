#!/usr/bin/env python3
"""
"""
import logging
import time

from esg.api_client.base import HttpBaseClient
from esg.models.request import RequestId
from esg.models.request import RequestStatus

logger = logging.getLogger(__name__)


class GenericServiceClient(HttpBaseClient):
    """
    A client to communicate with data and product services.

    The intended usage concept is:
        * Create a class instance.
        * create one or more requests.
        * wait for all results to be finished.
        * Retrieve all results at once.

    Raises:
    -------
        All methods will indirectly raise a `requests.exceptions.HTTPError`
        if anything goes wrong.
    """

    def __init__(
        self,
        base_url,
        verify=True,
        username=None,
        password=None,
        InputModel=None,
        OutputModel=None,
    ):
        """
        Arguments:
        ----------
        base_url : str
            The root URL of the service API, e.g. `http://localhost:8800`
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
        InputModel : esg.models.base._BaseModel related
            The pydantic model that should be used to parse the
            input data in `self.submit_request`.
        OutputModel : esg.models.base._BaseModel related
            The pydantic model that should be used to parse the
            output data in `self.fetch_result`.
        """
        logger.info("Starting up GenericServiceClient")

        self.InputModel = InputModel
        self.OutputModel = OutputModel

        super().__init__(
            base_url=base_url,
            verify=verify,
            username=username,
            password=password,
        )

        logger.info("Testing connection to service API.")
        # This will raise an error if the service is not reachable.
        self.get("/")

        # Stores created requests.
        self.request_ids = []
        # This is here to prevent `fetch_results_jsonable` from
        # needing to check again if all results are finished if
        # `wait_for_results` has been called before already.
        self.all_requests_finsished = False

    def post_request_jsonable(self, input_data_as_jsonable):
        """
        Calls POST /request/ endpoint of service.

        This will store the request_ID in an attribute so you don't have to.

        Arguments:
        ----------
        input_data_as_jsonable: python object
            The input data for computing the request in JSONable representation.
        """
        response = self.post("/request/", json=input_data_as_jsonable)

        # Check that the response contained the payload we expect and
        # store the request ID for fetching results later.
        request_id = RequestId.parse_obj(response.json()).request_ID
        self.request_ids.append(request_id)

    def post_request(self, input_data_obj):
        """
        Like `post_request_jsonable` but for a python object as input.

        This will use `self.InputModel` to parse and validate the object.

        Arguments:
        ----------
        input_data_obj: dict
            The input data for computing the request as _BaseModel instance.
        """
        input_data = self.InputModel(**input_data_obj)
        input_data_jsonable = input_data.jsonable()
        self.post_request_jsonable(input_data_as_jsonable=input_data_jsonable)

    def wait_for_results(self, max_retries=300, retry_wait=1):
        """
        Blocks until all requests are finished

        This will start with the first request and ask the product service
        if it is finished already. If not it will wait one second and ask
        again. Once the first request is finished it will continue with the
        second request and so on. That way we don't need to request the
        status of all requests every second but won't have a major
        drawback as we want to block until ALL finished anyways.

        Note: The maximum runtime of this method (timeout) is:
              `max_retries * retry_wait` in seconds.

        Arguments:
        ----------
        max_retries: int
            Maximum total number of times the request status is checked
            before it assuming the requests have failed.
        retry_wait: int
            How many seconds to wait after a not ready status before
            the script fetches the next status.

        Raises:
        -------
        RuntimeError:
            If number of stutus requests exceeded `max_retries` while
            waiting for requests to become ready.

        """
        # Shortcut, e.g. if called again by `fetch_result_jsonable`
        if self.all_requests_finsished:
            return

        request_ids_to_check = self.request_ids.copy()
        current_request_id = request_ids_to_check.pop(0)
        for _ in range(max_retries):
            while True:
                status_url = "/request/{}/status/".format(current_request_id)
                response = self.get(status_url)
                request_status = RequestStatus.parse_obj(response.json())

                # If not ready, wait a bit and try again.
                if request_status.status_text != "ready":
                    time.sleep(retry_wait)
                    break

                # If previous request is ready, directly try the next one.
                if request_ids_to_check:
                    current_request_id = request_ids_to_check.pop(0)
                else:
                    # Nothing left to check.
                    break

            if not request_ids_to_check:
                # This point will only be reached if all request are ready.
                self.all_requests_finished = True
                return

        raise RuntimeError("Timeout while waiting for requests to complete")

    def get_result_jsonable(self):
        """
        Returns a list of request results, one for each request and in the
        same order.

        Returns:
        --------
        output_data_jsonable : Python object, usually a dict or list.
            The output data as JSONable representation.
        """
        # Fetching not ready results may block and cause nasty errors like
        # gateway timeouts and stuff.
        self.wait_for_results()

        output_data_jsonable = []
        while self.request_ids:
            request_id = self.request_ids.pop(0)
            result_url = "/request/{}/result/".format(request_id)
            response = self.get(result_url)
            output_data_jsonable.append(response.json())

        return output_data_jsonable

    def get_results(self):
        """
        Like `get_result_jsonable` but for a python object as output.

        This will use `self.OutputModel` to parse and validate the response.

        Returns:
        --------
        output_data : esg.models.base._BaseModel instance.
            The output data as Pydantic Model representation.
        """
        output_data_jsonable = self.get_result_jsonable()
        output_data = []
        for jsonable_item in output_data_jsonable:
            obj = self.OutputModel(**jsonable_item)
            output_data.append(obj)

        return output_data
