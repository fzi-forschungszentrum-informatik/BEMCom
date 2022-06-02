#!/usr/bin/env python3
"""
Generic code for asyncio based product or data services.
"""
import asyncio
import time
from uuid import UUID

from fastapi.responses import JSONResponse

from esg.models.request import RequestStatus
from esg.services.base import BaseService
from esg.services.base import GenericUnexpctedException
from esg.services.base import RequestInducedException


class AsyncioTaskService(BaseService):
    """
    This is the generic class for services that employ asyncio background
    tasks for processing the requests.

    Using the asyncio background tasks should work well for IO bound
    request processing like fetching stuff from a database. There is no
    restriction implemented that would restrict the number of background
    tasks, which might not work out well with a large number of requests.

    More details about asycio task can be found here:
    https://docs.python.org/3/library/asyncio-task.html#creating-tasks

    In order the derive a functional service the following methods must be
    overloaded:
        - post_request
        - process_request (This should be an async function as the processing
            will else block the whole service.)

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

    async def schedule_request_processing(self, request):
        """
        This method triggers the computation of the result from the request.

        Arguments:
        ----------
        request : dict
            See create_request docstring for details
        """
        self.logger.debug(
            "Scheduling processing of request with ID: %s", request["ID"]
        )
        task = asyncio.create_task(
            self._process_request_wrapper(request=request,)
        )
        request["task"] = task

    async def _process_request_wrapper(self, request):
        """
        This is wrapper around process_request that sets the time fields
        of the request object and does some development logging.

        Arguments:
        ----------
        request : dict
            See create_request docstring for details

        Returns:
        --------
        result : likely a dict
            Whatever is returned by process_request
        """

        self.logger.debug(
            "Starting processing of request with ID: %s", request["ID"]
        )
        request["processing_started_at"] = time.monotonic()
        try:
            result = await self.process_request(
                input_data=request["input_data"]
            )
        except RequestInducedException as e:
            # Don't log traceback for exceptions which are the user's fault.
            # A simple notice that something went wront is sufficient.
            self.logger.info(
                "Request %s failed with reason: %s", request["ID"], e.detail,
            )
            raise
        except Exception:
            self.logger.exception(
                "Encountered exception while processing request with ID: %s",
                request["ID"],
            )
            raise
        request["result_ready_at"] = time.monotonic()

        # Compute how long the processing of the request took for diagnostics.
        ps = request["result_ready_at"] - request["processing_started_at"]
        self.logger.debug(
            "processing of request finished in %s seconds. Request ID is: %s",
            *(ps, request["ID"])
        )

        return result

    async def process_request(self, input_data):
        """
        This method defines how to compute the result from the request.

        This method must be overloaded with the logic of final service.
        The final method is expected to be an async function to allow
        concurrent execution.

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

    async def get_request_status(self, request_ID: UUID):
        """
        This method triggers the computation of the status response, it thus
        answers any calls to the  GET /request/{request_ID}/status/ endpoint.

        Here the status contains only of the status_text, as the asyncio tasks
        provide us no information by default about the percentage complete or
        the ETA of the result.

        Arguments:
        ----------
        request_ID : UUID
            As returned by POST /request/

        Returns:
        --------
        status : models.RequestStatus instance
            The computed status of the request.

        Raises:
        -------
        fastapi.HTTPException
            - With code 404 if no request is found that matches request_id.
        """
        request = self.get_request_or_raise(request_ID=request_ID)
        if "task" not in request:
            status_text = "queued"
        elif request["task"].done():
            status_text = "ready"
        else:
            status_text = "running"
        status = RequestStatus(status_text=status_text)
        self.logger.debug(
            'Computed status "%s" for request with ID: %s',
            *(status_text, request_ID)
        )
        return status

    async def get_request_result(self, request_ID: UUID):
        """
        This method triggers the computation of the result response, it thus
        answers any calls to the  GET /request/{request_ID}/result/ endpoint.

        Arguments:
        ----------
        request_id : UUID
            As returned by POST /request/

        Returns:
        --------
        response : fastapi.responses.JSONResponse instance
            The validated output data in a JSON repsonse object.

        Raises:
        -------
        fastapi.HTTPException
            With code 404 if no request is found that matches request_id.
        esg.services.base.GenericUnexpctedException
            Upon unexpected errors during handling the request,
            see Exception docstring for details.
        esg.services.base.RequestInducedException
            Upon request induced errors during handling the request,
            see Exception docstring for details.
        """
        request = self.get_request_or_raise(request_ID=request_ID)
        self.logger.debug("Fetching result for request with ID: %s", request_ID)

        # Requesting the result will reraise any exception happened during the
        # execution of the task. However, the _process_request_wrapper has
        # already logged that exception so there is nothing else to do here,
        # apart from preventing that the exception enters the logs a second
        # time.
        try:
            # This blocks until the task is done.
            await request["task"]
            result = request["task"].result()
        except RequestInducedException as exp:
            raise exp
        except:  # NOQA This bare except is fine, see comment above.
            # If not catching this, fastapi would do and send the client a
            # 500 error message. So we do the same.
            raise GenericUnexpctedException

        self.logger.debug(
            "Validating output data for request with ID: %s", request_ID
        )
        output_data_pydantic = self.OutputData(**result)
        output_data_jsonable = output_data_pydantic.jsonable()
        response = JSONResponse(content=output_data_jsonable)

        self.logger.debug(
            "Returning result for request with ID: %s", request_ID
        )
        return response
