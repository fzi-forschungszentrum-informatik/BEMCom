#!/usr/bin/env python3
"""
Generic definitions of metadata models.
"""
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from typing import Dict
from typing import List

from pydantic import Field
from pydantic import HttpUrl

from esg.models.base import _BaseModel


class GeographicPosition(_BaseModel):
    """
    Defines the position of a point somewhere on or above the Earth surface.
    """

    latitude: float = Field(
        example=49.01365,
        nullable=False,
        ge=-90.0,
        le=90.0,
        description=(
            "Latitude angle (North: +, South: -) of the position in degree."
        ),
    )
    longitude: float = Field(
        example=8.40444,
        nullable=False,
        ge=-180.0,
        le=180.0,
        description=(
            "Longitude angle (West: -, East: +) of the position in degree."
        ),
    )
    height: float = Field(
        default=None,
        example=75.3,
        nullable=True,
        ge=0.0,
        # 1000m Seems a sane limit for know just prevent people from
        # accidentally requesting strange high heights. Beyond it
        # has no critical function and is hence also not tested for.
        le=1000.0,
        description=(
            "Height above ground surface. This is optional and `null` "
            "(i.e. the default) means that the value is not specified."
        ),
    )


class GeographicPositionList(_BaseModel):
    """
    Defines a list of positions.
    """

    __root__: List[GeographicPosition] = Field(
        ...,
        nullable=False,
        description=("A list of geographic position items."),
    )


class GeographicPositionDict(_BaseModel):
    """
    Defines a dict of positions, i.e. each position has a name associated to it.
    """

    __root__: Dict[str, GeographicPosition] = Field(
        ...,
        nullable=False,
        description=(
            "A Dict of names (e.g. ids) and the corresponding "
            "geographic position items."
        ),
    )


class PVSystem(_BaseModel):
    azimuth_angle: float = Field(
        example=0,
        nullable=False,
        ge=-90.0,
        le=90.0,
        description=(
            "The azimuth angle indicates the deviation of a photovoltaic "
            "module from the South. As coordinates are counted clockwise, "
            "for the East negative values are used, for the West "
            "positive ones. The unit of the azimuth angle is degrees °. "
        ),
    )
    inclination_angle: float = Field(
        example=30,
        nullable=False,
        ge=0,
        le=90,
        description=(
            "The inclination angle describes the deviation "
            "of the photovoltaic modules from the horizontal, "
            "e.g. an inclination angle of 0° indicates that "
            "the module faces right up."
            "The unit of the inclination angle is degrees °. "
        ),
    )
    nominal_power: float = Field(
        example=15,
        nullable=False,
        ge=0.0,
        description=(
            "The nominal power is a quantity specified in the "
            "data sheet of the PV module and measured at "
            "Standard Test Conditions (STC) by the manufacturer. "
            "The unit of the nominal power is kWp."
        ),
    )
    power_datapoint_id: int = Field(
        ...,
        example=1,
        nullable=False,
        description=(
            "The id of the datapoint which is used to store forecasts "
            "of power production and measurements of the same, at least "
            "if such measurements exist."
        ),
    )


class PVSystemList(_BaseModel):
    """
    Defines a list of pv systems.
    """

    __root__: List[PVSystem] = Field(
        ..., nullable=False, description="A list of pv system items.",
    )


class PVSystemDict(_BaseModel):
    """
    Defines a dict of pv systems, i.e. each pv system has a name
    associated to it.
    """

    __root__: Dict[str, PVSystem] = Field(
        ...,
        nullable=False,
        description=(
            "A Dict of names (e.g. ids) and the corresponding "
            "pv system items."
        ),
    )


class Plant(_BaseModel):
    """
    Defines the metadata necessary to compute optimized schedules or forecasts
    for a physical entity, e.g. a PV plant or a building.
    """

    id: int = Field(
        default=None,
        nullable=True,
        example=1,
        description=("The ID of plant object in the central database."),
    )
    name: str = Field(
        ...,
        nullable=False,
        min_length=3,
        example="Karlsruhe city center",
        description=(
            "A meaningful name for the plant. Should be short but precise. "
            "Is used in e.g. in plots to analyses the product quality."
        ),
    )
    product_ids: List[int] = Field(
        default=list(),
        nullable=False,
        example=[1],
        description=(
            "A list of product IDs that should be computed for this plant."
        ),
    )
    geographic_position: GeographicPosition = Field(
        default=None,
        nullable=True,
        description=(
            "The position of the plant on earth. Is required for "
            " computing weather forecast data etc."
        ),
    )
    pv_system: PVSystem = Field(
        default=None,
        nullable=True,
        description=(
            "Metadata of the photovoltaic plant. Is required for "
            "forecasting the photovoltaic power production of the plant"
        ),
    )


class PlantList(_BaseModel):
    """
    Defines a list of plant items.
    """

    __root__: List[Plant] = Field(
        ..., nullable=False, description=("A list of plant items."),
    )


class Product(_BaseModel):
    """
    Defines the metadata for a product.
    """

    id: int = Field(
        default=None,
        nullable=True,
        example=1,
        description=("The ID of product object in the central database."),
    )
    name: str = Field(
        ...,
        nullable=False,
        min_length=3,
        example="PV Forecast",
        description=(
            "A meaningful name for the product. Should be short but precise. "
            "Is used in e.g. in plots to analyses the product quality."
        ),
    )
    service_url: HttpUrl = Field(
        ...,
        nullable=False,
        example="https://iik-energy-services.fzi.de/pv_forecast/v1/",
        description=("The URL of the product service."),
    )
    coverage_from: timedelta = Field(
        ...,
        nullable=False,
        example=-900,
        description=(
            "For any run given time a product run is started this is the "
            "difference between the start time and the begin of the covered "
            "time range, i.e. the time range for which forecasts or schedules "
            "are computed. E.g. if a run started at `2022-02-02T03:00:52` "
            "and `coverage_from` is `P0DT01H15M00S` then we expect the first "
            "forecasted value at time larger or equal `2022-02-02T04:15:52`."
        ),
    )
    coverage_to: timedelta = Field(
        ...,
        nullable=False,
        example=89940,
        description=(
            "For any run given time a product run is started this is the "
            "difference between the start time and the end of the covered "
            "time range, i.e. the time range for which forecasts or schedules "
            "are computed. E.g. if a run started at `2022-02-02T03:00:52` "
            "and `coverage_from` is `P0DT05H15M00S` then we expect the last "
            "forecasted value at time less then `2022-02-02T08:15:52`."
        ),
    )


class ProductList(_BaseModel):
    """
    Defines a list of product items.
    """

    __root__: List[Product] = Field(
        ..., nullable=False, description=("A list of products items."),
    )


class ProductRun(_BaseModel):
    """
    Identifies the computed result of a product service at a certain
    point in time. This should carry all information to repeat that
    computation if required.
    """

    id: int = Field(
        default=None,
        nullable=True,
        example=1,
        description=("The ID of product run object in the central database."),
    )
    product_id: int = Field(
        ...,
        nullable=False,
        example=1,
        description=(
            "The ID of the corresponding product object in the "
            "central database."
        ),
    )
    plant_ids: List[int] = Field(
        default=list(),
        nullable=False,
        example=[1],
        description=(
            "The IDs of the corresponding plant objects in the "
            "central database."
        ),
    )
    available_at: datetime = Field(
        default=datetime.now(tz=timezone.utc),
        nullable=False,
        description=(
            "Will be forwarded to product services and trigger those to "
            "compute only with data that has been available at this time."
        ),
    )
    coverage_from: datetime = Field(
        ...,
        nullable=False,
        example=datetime.now(tz=timezone.utc) - timedelta(seconds=900),
        description=(
            "The covered time span by this product run is equal or larger "
            "this value."
        ),
    )
    coverage_to: datetime = Field(
        ...,
        nullable=False,
        example=datetime.now(tz=timezone.utc) + timedelta(days=1),
        description=(
            "The covered time span by this product run is less " "this value."
        ),
    )


class ProductRunList(_BaseModel):
    """
    Defines a list of product run items.
    """

    __root__: List[ProductRun] = Field(
        ..., nullable=False, description=("A list of product run items."),
    )
