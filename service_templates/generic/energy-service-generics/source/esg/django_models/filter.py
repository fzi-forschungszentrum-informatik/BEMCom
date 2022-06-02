#!/usr/bin/env python3
"""
Definition (pydantic models) of filter parameters for GET
endpoints of the EMP.

This lives here and not in the EMP repo as clients need to use these too.

Note the keys must match something expect by `django.QuerySets.filter` of the
corresponding model.
See: https://docs.djangoproject.com/en/4.0/ref/models/querysets/#filter
"""
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel
from pydantic import Field

from esg.models.datapoint import DatapointType
from esg.models.datapoint import DatapointDataFormat


class DatapointFilterParams(BaseModel):
    """
    Filter query parameters for the `esg.django_models.datapoint.Datapoint`
    model.
    """

    id__in: List[int] = Field(None, description="`Datapoint.id` in list")
    origin__exact: str = Field(
        None, description="`Datapoint.origin` exact match"
    )
    origin__regex: str = Field(
        None, description="`Datapoint.origin` regex match"
    )
    origin_id__in: List[str] = Field(
        None, description="`Datapoint.origin_id` in list"
    )
    origin_id__regex: str = Field(
        None, description="`Datapoint.origin_id` regex match"
    )
    short_name__regex: str = Field(
        None, description="`Datapoint.short_name` regex match"
    )
    # Use in here instead of exact as the List[] makes the field
    # not required in SwaggerUI.
    type__in: List[DatapointType] = Field(
        None, description="`Datapoint.type` in list"
    )
    data_format__in: List[DatapointDataFormat] = Field(
        None, description="`Datapoint.data_format` in list"
    )
    description__regex: str = Field(
        None, description="`Datapoint.description` regex match"
    )
    unit__regex: str = Field(None, description="`Datapoint.unit` regex match")


class ValueMessageFilterParams(BaseModel):
    """
    Filter query parameters for the `esg.django_models.datapoint.ValueMessage`
    model.
    """

    time__gte: datetime = Field(
        None, description="`ValueMessage.time` greater or equal this value."
    )
    time__lt: datetime = Field(
        None, description="`ValueMessage.time` less this value."
    )


class ScheduleMessageFilterParams(BaseModel):
    """
    Filter query parameters for the
    `esg.django_models.datapoint.ScheduleMessage` model.
    """

    time__gte: datetime = Field(
        None, description="`ScheduleMessage.time` greater or equal this value.",
    )
    time__lt: datetime = Field(
        None, description="`ScheduleMessage.time` less this value."
    )


class SetpointFilterParams(BaseModel):
    """
    Filter query parameters for the
    `esg.django_models.datapoint.SetpointMessage` model.
    """

    time__gte: datetime = Field(
        None, description="`SetpointMessage.time` greater or equal this value.",
    )
    time__lt: datetime = Field(
        None, description="`SetpointMessage.time` less this value."
    )


class ProductRunFilterParams(BaseModel):
    """
    Filter query parameters for the `esg.django_models.metadata.ProductRun`
    model.
    """

    id__in: List[int] = Field(
        None,
        description=("Matches `ProductRun` items with `id` in this list."),
    )
    _product__id__in: List[int] = Field(
        None,
        description=(
            "Matches `ProductRun` for which `Product.id` is in this list."
        ),
    )
    _product__name__regex: str = Field(
        None,
        description=(
            "Matches `ProductRun` for which `Product.name` regex matches."
        ),
    )
    plants__id__in: List[int] = Field(
        None,
        description=(
            "Matches `ProductRun` for which `Plant.id` is in this list."
        ),
    )
    plants__name__regex: str = Field(
        None,
        description=(
            "Matches `ProductRun` for which `Plant.name` regex matches."
        ),
    )
    available_at__gte: datetime = Field(
        None,
        description=(
            "Matches items with `available_at` greater or equal this value."
        ),
    )
    available_at__lt: datetime = Field(
        None,
        description=("Matches items with `available_at` less this value."),
    )
    coverage_from__gte: datetime = Field(
        None,
        description=(
            "Matches items with `coverage_from` greater or equal this value."
        ),
    )
    coverage_from__lt: datetime = Field(
        None,
        description=("Matches items with `coverage_from` less this value."),
    )
    coverage_to__gte: datetime = Field(
        None,
        description=(
            "Matches items with `coverage_to` greater or equal this value."
        ),
    )
    coverage_to__lt: datetime = Field(
        None, description=("Matches items with `coverage_to` less this value."),
    )


class ProductFilterParams(BaseModel):
    """
    Filter query parameters for the `esg.django_models.metadata.Product` model.
    """

    id__in: List[int] = Field(
        None, description=("Matches `Product` items with `id` in this list."),
    )
    name__regex: str = Field(
        None, description=("Regex match `Product.name`."),
    )


class PlantFilterParams(BaseModel):
    """
    Filter query parameters for the `esg.django_models.metadata.Plant` model.
    """

    products__id__in: List[int] = Field(
        None, description=("Matches `Plant` with `product_ids` in this list."),
    )


class TimeBucketAggregation(str, Enum):
    """
    Defines the type of temporal aggregation.
    """

    avg = "Avg"
    count = "Count"
    max = "Max"
    min = "Min"
    sum = "Sum"
    std = "StdDev"
    var = "Variance"


class TimeBucketParams(BaseModel):
    """
    Additional query parameter for requests that utilize time buckets to
    aggregate in temporal dimension already in DB.
    """

    interval: str = Field(
        ...,
        example="15 minutes",
        help_text=(
            "The target interval. Must be a valid PostgreSQL interval "
            "string."
        ),
    )
    aggregation: TimeBucketAggregation = Field(
        default="Avg", help_text="The type of temporal aggregation to use.",
    )
