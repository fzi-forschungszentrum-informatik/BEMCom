#!/usr/bin/env python3
"""
Generic code relevant for all product/data services.
"""
import os
import sys
import logging
from threading import Thread
import time
from uuid import uuid1, UUID

from dotenv import find_dotenv
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
import uvicorn

from esg.models.request import HTTPError
from esg.models.request import RequestId
from esg.models.request import RequestStatus


class GenericUnexpctedException(HTTPException):
    """
    This defines a generic HTTP error (500) that should be returned
    for any unexpected error encountered during processing the request,
    that is a bug in the service.

    This error doesn't contain any additional information as the user
    of the service has no chance to fix it anyways and the responsible
    maintainer can look up the full traceback in the logs.
    """

    def __init__(self, request_ID=None, **kwargs):
        """
        Set `status_code` and `detail` with the desired generic
        information.

        Arguments:
        ----------
        request_id : UUID
            If provided will add the ID to the error detail message.
        kwargs : dict
            Any other keyword arguments that should be forwarded to
            fastapi.HTTPException
        """
        kwargs["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR

        base_detail = "The service encountered an error while processing the "
        if request_ID is not None:
            detail = base_detail + "request with ID: %s" % request_ID
        else:
            detail = base_detail + "request."
        kwargs["detail"] = detail

        super().__init__(**kwargs)


class RequestInducedException(HTTPException):
    """
    This defines a HTTP error (400) that should be returned for any
    foreseeable error that might occur during handling the request and
    that is caused by the request arguments (but cannot eliminated with
    reasonable effort during validation). E.g. the user request triggers
    reading data from a file or database which may not always exist but
    if the data exists is only known after the file has been opened or
    the DB has been queried.

    The `detail` field of this exception should always be populated
    with enough information to allow the user of a service to understand
    why the request failed and how to alter the request arguments to
    make it work.

    Note that the `status_code` is set fixed to 400 to distinguish the
    error from other common errors like (403, 404) which have other reasons
    and also from validation errors (422) as the latter returns a different
    data format.
    """

    def __init__(self, detail, **kwargs):
        """
        Overload `status_code`  with the desired generic value and
        validate that a detail is provided.

        This keeps the signature of fastapi.HTTPException and any
        additional arguments are forwarded to it.

        Arguments:
        ----------
        detail : str
            A string explaining the user what went wrong.
        kwargs : dict
            Any other keyword arguments that should be forwarded to
            fastapi.HTTPException

        Raises:
        -------
        ValueError:
            If detail is empty.
        """
        kwargs["status_code"] = status.HTTP_400_BAD_REQUEST

        if not detail:
            raise ValueError(
                "RequestInducedException requires a non empty detail "
                "that explains what went wrong while processing the request."
            )
        kwargs["detail"] = detail

        super().__init__(**kwargs)


class BaseService:
    """
    This is the base service containing the basic functionality that all
    product and data services have in common. This class is not complete
    to directly derive functional services from it. Especially there are
    no mechanisms implemented to process the requests.

    In order the derive a functional service the following methods must be
    overloaded:
        - post_request
        - schedule_request_processing
        - process_request
        - get_request_status
        - get_request_result (This should be an async function to not block
            the service while waiting for the result if not ready yet.)

    Attributes:
    -----------
    logger : Pyhton logger object.
        Use this logger for all logging of the service.
    app : FastAPI instance
        The FastAPI app to run.
    requests : dict
        A dict that holds requests that are currently scheduled, running or
        ready and that have not been cleaned up yet.
    InputData : pydantic model
        A Model defining the structure and documentation of the input data,
        i.e. the data that is necessary to process a request.
    OutputData : pydantic model
        A Model defining the structure and documentation of the output data,
        i.e. the result of the request.
    post_request_responses : dict
        Allows defining additional responses for the POST /request/ endpoint.
        This information is solely used for extending the API schema.
    get_request_status_responses : dict
        Like above but for GET /request/{request_ID}/status/
    get_request_result_responses : dict
        Like above but for GET /request/{request_ID}/result/
    """

    # By default we expect this call to work. Any input that would cause an
    # error should be caught during validation of the input_data, while
    # the ValidationError is added automatically to the schema.
    post_request_responses = {}

    # This endpoint should only fail if the ID is unknown.
    get_request_status_responses = {
        404: {
            "model": HTTPError,
            "description": "No request with the provided ID exists.",
        }
    }

    # Besides the 404 it could also happen that an error during processing
    # the request occured. See the docstrings of `GenericUnexpctedException`
    # and `RequestInducedException` for details.
    get_request_result_responses = {
        400: {
            "model": HTTPError,
            "description": (
                "Returned if processing the request yields an error that "
                "is related to the request arguments. The detail string "
                "provides additional information on the error source."
            ),
        },
        404: get_request_status_responses[404],
        500: {
            "model": HTTPError,
            "description": (
                "Returned if processing the request yields an unexpected "
                "error. Please contact the provider of the service for "
                "support."
            ),
        },
    }

    # Same as `get_request_result_responses` but without the issue that
    # might be caused by the request_ID.
    post_request_and_return_result_responses = {
        400: get_request_result_responses[400],
        500: get_request_result_responses[500],
    }

    # Here the description texts for the three endpoints. FastAPI uses
    # the docstrings by default. However, these contain a lot if internal
    # stuff that is not relevant for the user. Hence the here the option
    # to set these explicitly.
    post_request_description = (
        "Create a request that is computed in the background."
    )
    get_request_status_description = "Return the status of request."
    get_request_result_description = (
        "Return the result of a response.\n"
        "This method should return immediately if the status is `ready`."
        "If the status is not `ready` the method will wait until the result is."
    )
    post_request_and_return_result_description = (
        "Issue a request, block until it is ready and return result.\n"
        "This is a purce convenience wrapper that internally does the "
        "same thing as calling POST /request/ and immediately afterwards "
        "GET request/{request_ID}/result/."
    )

    def __init__(
        self,
        InputData=BaseModel,
        OutputData=BaseModel,
        fastapi_kwargs={},
        expose_request_with_ID_endpoints=True,
        expose_request_and_return_endpoint=True,
    ):
        """
        Init basic stuff like the logger and configure the REST API.

        Configuration is partly taken from arguments and partly from
        environment variables. Here anything that is likely be set in the
        source code of the derived service is expected as argument. Any
        configuration that users want to change for single instances of
        the services are environment variables, e.g. the log level or
        credentials.

        Environment variables:
        ----------------------
        LOGLEVEL : str
            The loglevel to use for *all* loggers. Defaults to logging.INFO.
        GC_FETCHED_REQUESTS_AFTER_S : int as str
            Requests will be deleted by the garbage collector once the last
            fetch of the result is this many seconds ago. Keeping the
            result for a little time after fetching allows services to
            re-request results if something went wrong without needing
            to compute the request again. Defaults to 300 (i.e. 5 minutes).
        GC_FINISHED_REQUESTS_AFTER_S : int as str
            Requests that have never been fetched will be deleted by the
            garbage collector once the time the result was ready is this many
            seconds ago. This will clean up requests the client has forgotten
            about, and prevents that the main memory consumption of the
            service continuously raises. Defaults to 3600 (i.e. one hour).


        Arguments:
        ----------
        InputData : pydantic model
            A Model defining the structure and documentation of the input data,
            i.e. the data that is necessary to process a request.
        OutputData : pydantic model
            A Model defining the structure and documentation of the output data,
            i.e. the result of the request.
        fastapi_kwargs : dict
            Additional keyword arguments passed to FastAPI(), e.g. useful
            to extend schema docs.
        expose_request_with_ID_endpoints : bool, default True
            if `True` the endpoints for POST request GET request status and
            GET request result will be exposed.
        expose_request_and_return_endpoint : bool, default True
            if `True` the endpoints for POST request and return will be exposed.
        """
        # Log everything to stdout by default, i.e. to docker container logs.
        # This comes on top as we want to emit our initial log message as soon
        # as possible to support debugging if anything goes wrong.
        self._logger_name = "service"
        self.logger = logging.getLogger(self._logger_name)
        stream_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(levelname)-10s%(asctime)s - %(message)s"
        )
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)
        self.logger.setLevel(logging.INFO)

        self.logger.info("Initiating BaseService.")

        # dotenv allows us to load env variables from .env files which is
        # convenient for developing. If you set override to True tests
        # may fail as the tests assume that the existing environ variables
        # have higher priority over ones defined in the .env file.
        # usecwd will make finding dotens relative to the derived service
        # and not relative to this file, which is the default.
        load_dotenv(find_dotenv(usecwd=True), verbose=True, override=False)

        # Parse the requested log level from environment variables and
        # configure all loggers accordingly.
        self._loglevel = getattr(logging, (os.getenv("LOGLEVEL") or "INFO"))
        self.logger.info(
            "Changing log level for all loggers to %s", self._loglevel
        )
        for logger_name in logging.root.manager.loggerDict:
            logging.getLogger(logger_name).setLevel(self._loglevel)

        # Load FastAPI related settings
        self.fastapi_root_path = os.getenv("ROOT_PATH") or ""
        self.fastapi_version = os.getenv("VERSION") or "unknown"

        # Load the settings for the automatic garbage collection of requests.
        self.gc_fetched_requests_after_seconds = int(
            os.getenv("GC_FETCHED_REQUESTS_AFTER_S") or 300
        )
        self.logger.debug(
            "Setting GC_FETCHED_REQUESTS_AFTER_S to: %s",
            self.gc_fetched_requests_after_seconds,
        )
        self.gc_finished_requests_after_seconds = int(
            os.getenv("GC_FINISHED_REQUESTS_AFTER_S") or 3600
        )
        self.logger.debug(
            "Setting GC_FINISHED_REQUESTS_AFTER_S to: %s",
            self.gc_finished_requests_after_seconds,
        )
        # This determines the wait time between two GC cycles.
        # You should not need to change it, but it may be override to
        # speed up tests.
        self._GC_SLEEP_SECONDS = 10

        # Define the REST API Endpoint.
        self.app = FastAPI(
            docs_url="/",
            redoc_url=None,
            root_path=self.fastapi_root_path,
            version=self.fastapi_version,
            **fastapi_kwargs
        )
        if expose_request_with_ID_endpoints:
            self.app.post(
                "/request/",
                status_code=status.HTTP_201_CREATED,
                response_model=RequestId,
                responses=self.post_request_responses,
                description=self.post_request_description,
            )(self.post_request)
            self.app.get(
                "/request/{request_ID}/status/",
                response_model=RequestStatus,
                responses=self.get_request_status_responses,
                description=self.get_request_status_description,
            )(self.get_request_status)
            self.app.get(
                "/request/{request_ID}/result/",
                response_model=OutputData,
                responses=self.get_request_result_responses,
                description=self.get_request_result_description,
            )(self.get_request_result)
        if expose_request_and_return_endpoint:
            self.app.post(
                "/request_and_return_result/",
                response_model=OutputData,
                responses=self.post_request_and_return_result_responses,
                description=self.post_request_and_return_result_description,
            )(self.post_request_and_return_result)

        # Expose some attributes which are required for other methods.
        # Note: InputData is currently not in use but exposed for completeness.
        self.requests = {}
        self.InputData = InputData
        self.OutputData = OutputData

    def get_api_docs_from_description_file(self, description_path):
        """
        Extract API `title` and `description` from markdown file.

        This makes writing docs nicer, no more markdown in python docstrings!
        See also the fastapit docs about the fields:
        https://fastapi.tiangolo.com/tutorial/metadata/

        Arguments:
        ----------
        description_path: pathlib.Path
            The path of the markdown file to open.

        Returns:
        --------
        title: str
            The title of the API (for the API docs etc.). Method assumes
            that the title is in the first line of the description file.
        description: str
            The description of the API for the docs. It is assumed that
            these are all lines apart from the first.
        """
        with description_path.open("r") as description_file:
            lines = description_file.readlines()
        # Remove the header signs, the title is always formated as headline.
        title = lines[0].replace("#", "")
        if len(lines) > 1:
            description = "\n".join(lines[1:])
        else:
            description = ""

        return title, description

    async def post_request(self, input_data: BaseModel = None):
        """
        This method answers calls to the POST /request/ endpoint.

        This method must be overloaded with a service specific version
        in order to publish the correct InputData model. To do so copy this
        method, change the Model in the arguments line and remove the Exception
        below.

        Arguments:
        ----------
        input_data : pydantic model instance or equivalent dict.
            .. holding all necessary input data to compute the request.

        Returns:
        --------
        response : .models.RequestID
            A simple pydantic model instance containing the request_ID
        """
        raise NotImplementedError(
            "Service has not implemented post_request method."
        )
        return await self.handle_post_request(input_data=input_data)

    async def handle_post_request(self, input_data):
        """
        The actual worker for the POST /request/ endpoint.

        This creates a request object and a unique ID for it, stores the
        request object for the other methods and schedules its execution.
        it's execution.

        Arguments:
        ----------
        input_data : pydantic model instance or equivalent dict.
            .. holding all necessary input data to compute the request.

        Returns:
        --------
        request_id : base_service.models.RequestID
            A simple pydantic model instance containing the request_ID
        """
        request = self.create_request(input_data=input_data)
        await self.schedule_request_processing(request=request)
        self.requests[request["ID"]] = request
        request_id = RequestId(request_ID=request["ID"])
        return request_id

    def create_request(self, input_data):
        """
        Creates a request object holding all information for processing.

        Arguments:
        ----------
        input_data : pydantic model instance or equivalent dict.
            .. holding all necessary input data to compute the request.

        Returns:
        --------
        request : dict
            A dict with the following content. All times may be used to
            compute diagnostic values, like how long a request might have
            been scheduled or processing took.
                ID : UUID
                    The unique ID of the request.
                input_data : pydantic model instance or equivalent dict.
                    see above.
                created_at : time.monotonic
                    The time this request was created by this function.
                processing_started_at : time.monotonic or None
                    The time the processing of this request has started.
                    Defaults to None to indicate that the request has not
                    been processed yet.
                result_ready_at : time.monotonic or None
                    The time the processing of this request has finished.
                    Defaults to None to indicate that the request has not
                    finished processing yet.
                result_last_fetched_at : time.monotonic or None
                    The last time the result of the request has been fetched
                    via the GET "/request/{request_ID}/result/" endpoint.
                    This allows cleaning up old requests.
        """
        # Each request should have a unique ID, so even if two requests use
        # same exact same arguments we still know that the same result has
        # been requested two times. This allows us to ensure that we keep
        # each result at least as long until it was requested once.
        request_ID = uuid1()

        self.logger.debug("Creating new request with ID: %s", request_ID)
        request = {
            "ID": request_ID,
            "input_data": input_data,
            "created_at": time.monotonic(),
            "processing_started_at": None,
            "result_ready_at": None,
            "result_last_fetched_at": None,
        }
        return request

    async def schedule_request_processing(self, request):
        """
        This method triggers the computation of the result from the request.

        This method must be overloaded as the BaseService has not implemented
        any logic how to schedule the processing of requests.

        Arguments:
        ----------
        request : dict
            See create_request docstring for details
        """
        raise NotImplementedError(
            "Service has not implemented schedule_request_processing method."
        )

    def process_request(self, input_data):
        """
        This method defines how to compute the result from the request.

        This method must be overloaded with the logic of final service.

        Arguments:
        ----------
        input_data : pydantic model instance or equivalent dict.
            .. holding all necessary input data to compute the request.

        Should return:
        --------------
        result : dict
            A dict containing the result data. Should allow to compute the
            output_data instance with output_data = self.OutputData(**result)
        """
        raise NotImplementedError(
            "Service has not implemented process_request method."
        )

    def get_request_or_raise(self, request_ID):
        """
        Returns the request for an ID or raises 404 if not existing.

        Arguments:
        ----------
        request_id : base_service.models.RequestId instance
            As returned by POST /request/

        Returns:
        ----------
        request : dict
            See create_request docstring for details.

        Raises:
        -------
        fastapi.HTTPException
            - With code 404 if no request is found that matches request_id.
        """
        if request_ID not in self.requests:
            self.logger.info("Could find not request with ID: %s", request_ID)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not find request with ID: %s" % request_ID,
            )
        request = self.requests[request_ID]
        request["result_last_fetched_at"] = time.monotonic()
        return request

    async def get_request_status(self, request_id: UUID):
        """
        This method triggers the computation of the status response, it thus
        answers any calls to the  GET /request/{request_ID}/status/ endpoint.

        This method must be overloaded as the BaseService has not implemented
        any logic how to schedule the processing of requests. It can thus
        not know how to compute a status.

        The overloading method is expected to return an instance of
        base_service.models.RequestStatus.

        Arguments:
        ----------
        request_id : base_service.models.RequestId instance
            As returned by POST /request/

        Should return:
        --------------
        status : UUID
            The computed status of the request.

        Should raise:
        -------------
        fastapi.HTTPException
            With code 404 if no request is found that matches request_id.
        """
        raise NotImplementedError(
            "Service has not implemented get_request_status method."
        )

    async def get_request_result(self, request_id: UUID):
        """
        This method triggers the computation of the result response, it thus
        answers any calls to the  GET /request/{request_ID}/result/ endpoint.

        This method must be overloaded as the BaseService has not implemented
        any logic how to schedule the processing of requests. It can thus
        not know how to retrieve the result.

        Arguments:
        ----------
        request_id : UUID
            As returned by POST /request/

        Should return:
        --------------
        response : fastapi.responses.JSONResponse instance
            The validated output data in a JSON repsonse object.

        Should raise:
        -------------
        fastapi.HTTPException
            If something goes wrong, e.g. no request with such ID exists.
        esg.services.base.GenericUnexpctedException
            Upon unexpected errors during handling the request,
            see Exception docstring for details.
        esg.services.base.RequestInducedException
            Upon request induced errors during handling the request,
            see Exception docstring for details.
        """
        raise NotImplementedError(
            "Service has not implemented get_request_result method."
        )

    async def post_request_and_return_result(
        self, input_data: BaseModel = None
    ):
        """
        This is an additional and optional method that handles calls
        to GET /request/result/ endpoint. It opens up a shortcut so users
        can directly post a process and wait for the process in once go
        if they like. This might be useful for services that usually
        react fast, like in a couple of seconds.

        This method must be overloaded with a service specific version
        in order to publish the correct InputData model. To do so copy this
        method, change the Model in the arguments line and remove the Exception
        below.

        Arguments:
        ----------
        input_data : pydantic model instance or equivalent dict.
            .. holding all necessary input data to compute the request.

        Should return:
        --------------
        output_data : OutputData instance
            The computed results of the request.

        Should raise:
        -------------
        esg.services.base.GenericUnexpctedException
            Upon unexpected errors during handling the request,
            see Exception docstring for details.
        esg.services.base.RequestInducedException
            Upon request induced errors during handling the request,
            see Exception docstring for details.
        """
        raise NotImplementedError(
            "Service has not implemented post_request_and_return_result method."
        )
        return await self.handle_post_request_and_return_result(
            input_data=input_data
        )

    async def handle_post_request_and_return_result(self, input_data):
        """
        The actual worker for the POST /request_and_return_result/ endpoint.

        This issues processing of the request, waits until the result is
        ready and retrieves it and returns it. The result is also directly
        garbage collected as the user never knows the request_ID and thus
        has no chance of rerequesting if something went wrong.

        Arguments:
        ----------
        input_data : pydantic model instance or equivalent dict.
            .. holding all necessary input data to compute the request.

        Returns:
        --------
        output_data : OutputData instance
            The computed results of the request.
        """
        request_id = await self.handle_post_request(input_data=input_data)
        request_ID = request_id.request_ID
        result = await self.get_request_result(request_ID=request_ID)

        # This is the same thing `garbage_collect_requests` does after a while.
        del self.requests[request_ID]

        return result

    def garbage_collect_requests(self):
        """
        This cleans up old requests to free memory.

        Removes request that have been fetched longer ago then
        GC_FETCHED_REQUESTS_AFTER_S as well as those that have never been
        fetched but are in ready state for more then
        GC_FINISHED_REQUESTS_AFTER_S seconds.
        """
        self.logger.debug("Running garbage_collect_requests().")
        for request in list(self.requests.values()):
            rlfa = request["result_last_fetched_at"]
            if rlfa is not None:
                s_since_last_fetch = time.monotonic() - rlfa
                if s_since_last_fetch > self.gc_fetched_requests_after_seconds:
                    del self.requests[request["ID"]]
                    self.logger.debug(
                        "Garbage collector removed fetched request with ID: %s",
                        request["ID"],
                    )

            if request["result_ready_at"] is not None:
                # Handling for requests that have not been fetched yet.
                s_since_ready = time.monotonic() - request["result_ready_at"]
                if s_since_ready > self.gc_finished_requests_after_seconds:
                    del self.requests[request["ID"]]
                    self.logger.debug(
                        "Garbage collector deleted finished request with ID: "
                        "%s",
                        request["ID"],
                    )

    def requests_garbage_collector(self):
        """
        This is the worker that calls garbage_collect_requests every 10 seconds.

        """

        try:
            self.logger.debug("Starting garbage collector loop.")
            while True:
                self.garbage_collect_requests()
                time.sleep(self._GC_SLEEP_SECONDS)
        except Exception:
            self.logger.exception("Exception in garbage collector thread.")

    def close(self):
        """
        Place here anything that needs to be done to clean up.

        That is nothing in case of the BaseService.
        """
        pass

    def run(self):
        """
        Run the FastAPI app with uvicorn.
        """
        try:
            self.logger.info("Initiating API execution.")
            # Create the garbage collector in parallel thread that
            # will exit hard once the main program exits.
            gc_thread = Thread(
                target=self.requests_garbage_collector, daemon=True,
            )
            gc_thread.start()
            # Exposes a Prometheus endpoint for monitoring.
            # TODO: Add metrics for size of request queue
            Instrumentator().instrument(self.app).expose(
                self.app, include_in_schema=False
            )
            # Serve the REST endpoint.
            uvicorn.run(
                self.app, host="0.0.0.0", port=8800,
            )
        except Exception:
            self.logger.exception("Exception in run method of BaseService")
            raise
        finally:
            # This should be called on system exit and keyboard interrupt.
            self.logger.info("Shutting down service.")
            self.close()
            self.logger.info("Service shutdown completed. Good bye!")
