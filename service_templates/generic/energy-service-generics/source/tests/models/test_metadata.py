#!/usr/bin/env python3
"""
"""
from esg.models import metadata
from esg.test import data as td
from esg.test.generic_tests import GenericMessageSerializationTest


class TestGeographicPosition(GenericMessageSerializationTest):

    ModelClass = metadata.GeographicPosition
    msgs_as_python = [m["Python"] for m in td.geographic_positions]
    msgs_as_jsonable = [m["JSONable"] for m in td.geographic_positions]
    invalid_msgs_as_jsonable = [
        m["JSONable"] for m in td.invalid_geographic_positions
    ]


class TestGeographicPositionList(GenericMessageSerializationTest):

    ModelClass = metadata.GeographicPositionList
    # Note the additional outer list brackets around the messages here,
    # compared to `TestGeographicPosition` defined above.
    # This defines that `test_messages` only contain a single element
    # which holds all the value messages defined in `testdata`.
    msgs_as_python = [
        {"__root__": [m["Python"] for m in td.geographic_positions]}
    ]
    msgs_as_jsonable = [[m["JSONable"] for m in td.geographic_positions]]
    invalid_msgs_as_jsonable = [
        [m["JSONable"] for m in td.invalid_geographic_positions]
    ]


# This is just here to make `TestGeographicPositionDict` more readable.
enum_gp = list(enumerate(td.geographic_positions))
inv_enum_gp = list(enumerate(td.invalid_geographic_positions))


class TestGeographicPositionDict(GenericMessageSerializationTest):

    ModelClass = metadata.GeographicPositionDict
    msgs_as_python = [{"__root__": {str(i): m["Python"] for i, m in enum_gp}}]
    msgs_as_jsonable = [{str(i): m["JSONable"] for i, m in enum_gp}]
    invalid_msgs_as_jsonable = [{str(i): m["JSONable"] for i, m in inv_enum_gp}]


class TestPVSystem(GenericMessageSerializationTest):

    ModelClass = metadata.PVSystem
    msgs_as_python = [m["Python"] for m in td.pv_systems]
    msgs_as_jsonable = [m["JSONable"] for m in td.pv_systems]
    invalid_msgs_as_jsonable = [m["JSONable"] for m in td.invalid_pv_systems]


class TestPVSystemList(GenericMessageSerializationTest):

    ModelClass = metadata.PVSystemList
    # Note the additional outer list brackets around the messages here,
    # compared to `TestPVSystem` defined above.
    # This defines that `test_messages` only contain a single element
    # which holds all the value messages defined in `testdata`.
    msgs_as_python = [{"__root__": [m["Python"] for m in td.pv_systems]}]
    msgs_as_jsonable = [[m["JSONable"] for m in td.pv_systems]]
    invalid_msgs_as_jsonable = [[m["JSONable"] for m in td.invalid_pv_systems]]


# This is just here to make `TestPVSystemDict` more readable.
enum_pvs = list(enumerate(td.pv_systems))
inv_enum_pvs = list(enumerate(td.invalid_pv_systems))


class TestPVSystemDict(GenericMessageSerializationTest):

    ModelClass = metadata.PVSystemDict
    msgs_as_python = [{"__root__": {str(i): m["Python"] for i, m in enum_pvs}}]
    msgs_as_jsonable = [{str(i): m["JSONable"] for i, m in enum_pvs}]
    invalid_msgs_as_jsonable = [
        {str(i): m["JSONable"] for i, m in inv_enum_pvs}
    ]


class TestPlant(GenericMessageSerializationTest):

    ModelClass = metadata.Plant
    msgs_as_python = [m["Python"] for m in td.plants]
    msgs_as_jsonable = [m["JSONable"] for m in td.plants]
    invalid_msgs_as_jsonable = [m["JSONable"] for m in td.invalid_plants]


class TestPlantList(GenericMessageSerializationTest):

    ModelClass = metadata.PlantList
    # Also check that empty lists are allowed
    msgs_as_python = [
        {"__root__": []},
        {"__root__": [m["Python"] for m in td.plants]},
    ]
    msgs_as_jsonable = [[], [m["JSONable"] for m in td.plants]]
    invalid_msgs_as_jsonable = [[m["JSONable"] for m in td.invalid_plants]]


class TestProduct(GenericMessageSerializationTest):

    ModelClass = metadata.Product
    msgs_as_python = [m["Python"] for m in td.products]
    msgs_as_jsonable = [m["JSONable"] for m in td.products]
    invalid_msgs_as_jsonable = [m["JSONable"] for m in td.invalid_products]


class TestProductList(GenericMessageSerializationTest):

    ModelClass = metadata.ProductList
    # Also check that empty lists are allowed
    msgs_as_python = [
        {"__root__": []},
        {"__root__": [m["Python"] for m in td.products]},
    ]
    msgs_as_jsonable = [[], [m["JSONable"] for m in td.products]]
    invalid_msgs_as_jsonable = [[m["JSONable"] for m in td.invalid_products]]


class TestProductRun(GenericMessageSerializationTest):

    ModelClass = metadata.ProductRun
    msgs_as_python = [m["Python"] for m in td.product_runs]
    msgs_as_jsonable = [m["JSONable"] for m in td.product_runs]
    invalid_msgs_as_jsonable = [m["JSONable"] for m in td.invalid_product_runs]


class TestProductRunList(GenericMessageSerializationTest):

    ModelClass = metadata.ProductRunList
    # Also check that empty lists are allowed
    msgs_as_python = [
        {"__root__": []},
        {"__root__": [m["Python"] for m in td.product_runs]},
    ]
    msgs_as_jsonable = [[], [m["JSONable"] for m in td.product_runs]]
    invalid_msgs_as_jsonable = [
        [m["JSONable"] for m in td.invalid_product_runs]
    ]
