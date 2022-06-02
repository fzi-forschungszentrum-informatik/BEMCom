#!/usr/bin/env python3
"""
Generic definitions of request related data types (aka. messages)
in pydantic for serialization (e.g. to JSON) and for auto generation
of endpoint schemas.

Requests are here meant as the information exchanges with product or data
services.
"""
from enum import Enum
from uuid import UUID

from pydantic import Field

from esg.models.base import _BaseModel


class RequestId(_BaseModel):
    """
    This is the expected response for the POST /request/ endpoint.
    """

    request_ID: UUID = Field(
        None,
        description=(
            "The ID of the created request. Must use this ID to request "
            "the status or result of the request."
        ),
    )


class RequestStatusTextEnum(str, Enum):
    """
    The three states in which the request can be.

    The result can be retrieved immediately if the state is `ready`.
    Otherwise requesting the result will block until the result is ready.
    """

    queued = "queued"
    running = "running"
    ready = "ready"


class RequestStatus(_BaseModel):
    """
    The expected response for the GET /request/{request_id}/status/ endpoint.
    """

    status_text: RequestStatusTextEnum = Field(
        None, example="running",
    )
    percent_complete: float = Field(
        None,
        example=27.1,
        nullable=True,
        description=(
            "An estimate how much of the request has already been processed "
            "in percent. Is `null` if the service does not provide this "
            "information."
        ),
    )
    ETA_seconds: float = Field(
        None,
        example=15.7,
        nullable=True,
        description=(
            "An estimate how long it will take until the request is completely "
            "processed. Is `null` if the service cannot (maybe only "
            "temporarily) provide such an estimate."
        ),
    )


# It should not be necessary to use this model directly. It is mainly here
# to allow completing the API schema with the error messages.
class HTTPError(_BaseModel):
    """
    This is the default FastAPI format for error messages.
    """

    detail: str = Field(example="Some error msg text.")
