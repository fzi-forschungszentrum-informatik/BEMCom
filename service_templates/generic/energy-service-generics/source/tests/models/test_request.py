#!/usr/bin/env python3
"""
"""
import uuid
import json

from esg.models import request


class TestRequestId:
    def test_data_to_json(self):
        """
        Test conversion to JSON for all fields.
        """
        expected_json_content = {
            "request_ID": str(uuid.uuid1()),
        }
        actual_json = request.RequestId(**expected_json_content).json()
        assert json.loads(actual_json) == expected_json_content

    def test_json_to_data(self):
        """
        Test JSON can be parsed to Python objects.
        """
        test_uuid = str(uuid.uuid1())
        test_json = """
            {
                "request_ID": "%s"
            }
        """
        test_json = test_json % test_uuid
        expected_data = {
            "request_ID": test_uuid,
        }
        actual_data = request.RequestId.parse_raw(test_json)
        assert actual_data == request.RequestId(**expected_data)


class TestRequestStatus:
    def test_data_to_json(self):
        """
        Test conversion to JSON for all fields.
        """
        expected_json_content = {
            "status_text": "running",
            "percent_complete": 27.1,
            "ETA_seconds": 15.7,
        }
        actual_json = request.RequestStatus(**expected_json_content).json()
        assert json.loads(actual_json) == expected_json_content

    def test_json_to_data(self):
        """
        Test JSON can be parsed to Python objects.
        """
        test_json = """
            {
                "status_text": "running",
                "percent_complete": 27.1,
                "ETA_seconds": 15.7
            }
        """
        expected_data = {
            "status_text": "running",
            "percent_complete": 27.1,
            "ETA_seconds": 15.7,
        }
        actual_data = request.RequestStatus.parse_raw(test_json)
        assert actual_data.dict() == expected_data

    def test_data_to_json_without_optional(self):
        """
        Test conversion to JSON if only non optional values are provided.
        """
        expected_json_content = {
            "status_text": "running",
            "percent_complete": None,
            "ETA_seconds": None,
        }
        actual_json = request.RequestStatus(
            status_text=expected_json_content["status_text"]
        ).json()
        print(actual_json)
        assert json.loads(actual_json) == expected_json_content

    def test_json_to_data_without_optional(self):
        """
        Test JSON can be parsed to Python objects even if only non optional
        values are given in the JSON.
        """
        test_json = """
            {
                "status_text": "running"
            }
        """
        expected_data = {
            "status_text": "running",
            "percent_complete": None,
            "ETA_seconds": None,
        }
        actual_data = request.RequestStatus.parse_raw(test_json)
        assert actual_data.dict() == expected_data
