#!/usr/bin/env python3
"""
Due to short deadlines it was not possible to implement dedicated unit
tests for most of the endpoints provided in `esg.api_client.emp`

TODO: Add unit tests for all the endpoint methods.
"""
from datetime import datetime
from datetime import timezone
from unittest.mock import MagicMock

import pytest
import requests

from esg.api_client.emp import EmpClient
from esg.models.datapoint import Datapoint
from esg.models.datapoint import DatapointList
from esg.models.datapoint import ValueMessage
from esg.models.datapoint import ValueMessageByDatapointId
from esg.models.metadata import Product
from esg.models.metadata import ProductList
from esg.models.metadata import ProductRunList
from esg.models.metadata import PlantList


class TestEmpClientTestConnection:
    def test_api_root_called(self):
        """
        Verify that the method checked the API root URL.
        """
        client = EmpClient(base_url="http://localhost:8080/api")
        client.http = MagicMock()

        client.test_connection()

        assert client.http.get.called

        expected_url = "http://localhost:8080/api/"
        actual_url = client.http.get.call_args.args[0]

        assert actual_url == expected_url

    def test_nothing_happens_if_server_available(self, httpserver):
        """
        Nothing should happen if the URL is called and the server is there.
        """
        client = EmpClient(base_url=httpserver.url_for(""))

        httpserver.expect_request("/").respond_with_data(b"")

        client.test_connection()

    def test_exception_raised_if_server_unavailable(self):
        """
        Nothing should happen if the URL is called and the server is there.

        TODO: Improve this by checking that there is actually nothing
              listening on port 61080.

        """
        client = EmpClient(base_url="http://localhost:61080/api12iu1i23u12")

        with pytest.raises(requests.exceptions.ConnectionError):
            client.test_connection()


EMP_TEST_API_URL = "https://iik-test.fzi.de/emp/api"
EMP_TEST_API_URL = "http://localhost:8080/api"
try:
    live_client = EmpClient(base_url=EMP_TEST_API_URL, verify=False)
    live_client.test_connection()
except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
    # The first catches if the endpoint is not online at al.
    # The second exception catches cases where the EMP is online,
    # but misbehaves. Like e.g. host not in ALLOWED_HOSTS.
    live_client = None


@pytest.mark.skipif(live_client is None, reason="Live EMP not available")
class TestEmpClientEndToEnd:
    """
    These are basic end to end tests. They don't test that the content is
    correct, as this might change in the live test instance. Instead we just
    evaluate that the general communication seems to work.
    """

    test_datapoint = {
        "origin": "TestEmpClientTestConnection",
        "origin_id": "42",
        "short_name": "T_zone_f",
        "type": "Actuator",
        "data_format": "Continuous Numeric",
        "description": "Setpoint temperature first floor.",
        "allowed_values": None,
        "min_value": 13.37,
        "max_value": 42.0,
        "unit": "°C",
    }
    test_value_msg = {
        "value": "21.0",
        "time": "2022-02-22T02:52:00+00:00",
    }

    test_product_list = [
        {
            "id": 1,
            "name": "Test Forecast Service (for automatic tests only)",
            "service_url": "https://iik-energy-services.fzi.de/test_fct/v1/",
            "coverage_from": -900,
            "coverage_to": 900,
        }
    ]
    # Note that these values must match test_product_list[0] for the test
    # `test_create_product_run_from_product`.
    test_product_run_list = [
        {
            "id": 1,
            "product_id": 1,
            "plant_ids": [],
            "available_at": "2022-05-16T20:00:00+00:00",
            "coverage_from": "2022-05-16T19:45:00+00:00",
            "coverage_to": "2022-05-16T20:15:00+00:00",
        }
    ]
    test_plant_list = [
        {
            "id": 1,
            "name": "Karlsruhe city center",
            "product_ids": [1],
            "geographic_position": {
                "latitude": 49.01365,
                "longitude": 8.40444,
                "height": 75.3,
            },
            "pv_system": None,
        }
    ]

    def put_test_datapoint_metadata(self):
        """
        A helper that creates a test datapoint in DB.
        """
        test_datapoint_list = DatapointList.construct_recursive(
            __root__=[self.test_datapoint]
        )
        datapoint_list = live_client.put_datapoint_metadata_latest(
            test_datapoint_list
        )
        return datapoint_list

    def test_put_datapoint_metadata_latest(self):
        """
        Verify we can use the client method to create or update one datapoint
        item in DB.
        """
        datapoint_list = self.put_test_datapoint_metadata()

        # Everything below just checks that the returned datapoint matches
        # the data we have sent in.
        expected_datapoint_jsonable = Datapoint.construct_recursive(
            **self.test_datapoint
        ).jsonable()

        # This should only return a single datapoint.
        actual_datapoint_jsonable = datapoint_list.__root__[0].jsonable()

        # Don't check for ID, it is auto generated.
        actual_datapoint_jsonable["id"] = None

        assert actual_datapoint_jsonable == expected_datapoint_jsonable

    def test_get_datapoint_metadata_latest(self):
        """
        Check that we can recover a datapoint from DB.
        """
        # Store the testdatapoitn and fetch it's ID.
        datapoint_list = self.put_test_datapoint_metadata()
        datapoint_id = datapoint_list.__root__[0].id

        query_params = {"id__in": [datapoint_id]}
        datapoint_list_actual = live_client.get_datapoint_metadata_latest(
            query_params=query_params
        )

        assert len(datapoint_list_actual.__root__) == 1

        expected_datapoint = Datapoint.construct_recursive(
            **self.test_datapoint
        )
        expected_datapoint.id = int(datapoint_id)
        actual_datapoint = datapoint_list_actual.__root__[0]

        assert actual_datapoint.jsonable() == expected_datapoint.jsonable()

    def put_datapoint_value_latest(self):
        """
        A helper that creates a test value message (and the corresponding
        datapoint if necessary).
        """
        datapoint_list = self.put_test_datapoint_metadata()
        datapoint_id = datapoint_list.__root__[0].id

        value_msgs_by_dp_id = ValueMessageByDatapointId.parse_obj(
            {datapoint_id: self.test_value_msg}
        )
        put_summary = live_client.put_datapoint_value_latest(
            value_msgs_by_dp_id=value_msgs_by_dp_id
        )
        return datapoint_id, put_summary

    def test_put_datapoint_value_latest(self):
        """
        Verify we can use the client method to create or update one
        latest value message in DB.
        """
        _, put_summary = self.put_datapoint_value_latest()

        # We exepct one message to be updated or created.
        assert sum(put_summary.dict().values()) == 1

    def test_get_datapoint_value_latest(self):
        """
        Verify we can use the client method to read one
        latest value message from DB.
        """
        datapoint_id, _ = self.put_datapoint_value_latest()
        query_params = {"id__in": [datapoint_id]}

        value_msgs_by_dp_id = live_client.get_datapoint_value_latest(
            query_params=query_params,
        )

        # Expect only one message for this datapoint
        assert len(value_msgs_by_dp_id.__root__) == 1

        expected_msg = ValueMessage.parse_obj(self.test_value_msg)
        actual_msg = value_msgs_by_dp_id.__root__[str(datapoint_id)]

        assert actual_msg == expected_msg

    def put_product_latest(self):
        """
        A helper that creates a test product.
        """
        product_list = ProductList(__root__=self.test_product_list)
        product_list = live_client.put_product_latest(product_list=product_list)
        return product_list

    def test_put_product_latest(self):
        """
        Verify client can be used to interact with put endpoint.
        """
        product_list = self.put_product_latest()

        # Expect that the API has returned exactly the PUT data.
        expected_jsonable = self.test_product_list
        actual_jsonable = product_list.jsonable()
        assert expected_jsonable == actual_jsonable

    def test_get_product_latest(self):
        """
        Verify client can be used to interact with get endpoint.
        """
        _ = self.put_product_latest()

        actual_response = live_client.get_product_latest(
            query_params={"id__in": [1]}
        )

        # Expect that the API has returned exactly the PUT data.
        expected_jsonable = self.test_product_list
        actual_jsonable = actual_response.jsonable()
        assert expected_jsonable == actual_jsonable

    def test_create_product_run_from_product(self):
        """
        Verify that this method creates a product run with the intended values.
        """
        expected_product_run = self.test_product_run_list[0]
        actual_product_run = live_client.create_product_run_from_product(
            product=Product(**self.test_product_list[0]),
            available_at=datetime(2022, 5, 16, 20, tzinfo=timezone.utc),
        )
        actual_jsonable = actual_product_run.jsonable()

        for expected_field, expected_value in expected_product_run.items():
            if expected_field in ["id"]:
                # Ignore auto populated fields
                continue
            actual_value = actual_jsonable[expected_field]
            assert actual_value == expected_value, expected_field

    def put_product_run_latest(self):
        """
        A helper that creates a test product run and the corresponding product.
        """
        product_list = ProductList(__root__=self.test_product_list)
        product_list = live_client.put_product_latest(product_list=product_list)

        product_run_list = ProductRunList(__root__=self.test_product_run_list)
        product_run_list = live_client.put_product_run_latest(
            product_run_list=product_run_list
        )

        return product_run_list

    def test_put_product_run_latest(self):
        """
        Verify client can be used to interact with put endpoint.
        """
        product_run_list = self.put_product_run_latest()

        # Expect that the API has returned exactly the PUT data.
        expected_jsonable = self.test_product_run_list
        actual_jsonable = product_run_list.jsonable()
        assert expected_jsonable == actual_jsonable

    def test_get_product_run_latest(self):
        """
        Verify client can be used to interact with get endpoint.
        """
        _ = self.put_product_run_latest()

        actual_response = live_client.get_product_run_latest(
            query_params={"id__in": [1]}
        )

        # Expect that the API has returned exactly the PUT data.
        expected_jsonable = self.test_product_run_list
        actual_jsonable = actual_response.jsonable()
        assert expected_jsonable == actual_jsonable

    def put_plant_latest(self):
        """
        A helper that creates a test plant and the corresponding product.
        """
        product_list = ProductList(__root__=self.test_product_list)
        product_list = live_client.put_product_latest(product_list=product_list)

        plant_list = PlantList(__root__=self.test_plant_list)
        plant_list = live_client.put_plant_latest(plant_list=plant_list)

        return plant_list

    def test_put_plant_latest(self):
        """
        Verify client can be used to interact with put endpoint.
        """
        plant_list = self.put_plant_latest()

        # Expect that the API has returned exactly the PUT data.
        expected_jsonable = self.test_plant_list
        actual_jsonable = plant_list.jsonable()
        assert expected_jsonable == actual_jsonable

    def test_get_plant_latest(self):
        """
        Verify client can be used to interact with get endpoint.
        """
        _ = self.put_plant_latest()

        actual_response = live_client.get_plant_latest(
            query_params={"id__in": [1]}
        )

        # Expect that the API has returned exactly the PUT data.
        expected_jsonable = self.test_plant_list
        actual_jsonable = actual_response.jsonable()
        assert expected_jsonable == actual_jsonable
