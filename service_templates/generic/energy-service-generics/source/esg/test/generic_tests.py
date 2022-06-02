#!/usr/bin/env python3
"""
Generic Tests that can be reused to accelerate test implementation.
"""
import asyncio
from inspect import iscoroutinefunction
import json
from unittest.mock import MagicMock

from pydantic import ValidationError
import pytest

from esg.test.tools import async_return


class GenericMessageSerializationTest:
    """
    A generic set of tests to verify that the data can be serialized between
    the expected representations.

    Attributes:
    -----------
    ModelClass : pydantic model class
        The model that is used to serialize/deserialize the data.
    msgs_as_python : list of anything.
        The Python representation of the as defined in `testdata`.
        Each item in the list is treated as distinct message to
        verfiy correct operation for.
    msgs_as_jsonable : list of anything.
        Similar to `data_as_pyhton` but for JSONable representation.
        See the `testdata` module docstring for a discussion why we
        use JSONable representation instead of direct JSON.
    invalid_msgs_as_jsonable : list of anything.
        Similar to `msgs_as_jsonable` but messages that are expected
        to cause an error during validation.
    """

    ModelClass = None
    msgs_as_python = None
    msgs_as_jsonable = None
    invalid_msgs_as_jsonable = None

    def test_python_to_jsonable(self):
        """
        Verify that the model can be used to generate the expected JSONable
        output.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_jsonable)
        for msg_as_python, expected_msg_as_jsonable in test_messages:

            model_instance = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            actual_msg_as_jsonable = model_instance.jsonable()

            assert actual_msg_as_jsonable == expected_msg_as_jsonable

    def test_python_to_json(self):
        """
        Verify that the model can be used to generate the expected JSON output.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_jsonable)
        for msg_as_python, expected_msg_as_jsonable in test_messages:

            model_instance = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            actual_msg_as_json = model_instance.json()
            actual_msg_as_jsonable = json.loads(actual_msg_as_json)

            assert actual_msg_as_jsonable == expected_msg_as_jsonable

    def test_jsonable_to_python_object(self):
        """
        Check that the model can be used to parse the JSONable representation.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_jsonable)
        for msg_as_python, msg_as_jsonable in test_messages:

            expected_msg_as_obj = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            actual_msg_as_obj = self.ModelClass.parse_obj(msg_as_jsonable)

            assert actual_msg_as_obj == expected_msg_as_obj

    def test_json_to_python_object(self):
        """
        Check that the model can be used to parse the JSON representation.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_jsonable)
        for msg_as_python, msg_as_jsonable in test_messages:

            expected_msg_as_obj = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            msg_as_json = json.dumps(msg_as_jsonable)
            actual_msg_as_obj = self.ModelClass.parse_raw(msg_as_json)

            assert actual_msg_as_obj == expected_msg_as_obj

    def test_validation_error_raised_for_invalid_jsonable(self):
        """
        Verify that each invalid message provided to `parse_obj()`triggers
        a `ValidationError`
        """
        for invalid_msg_as_jsonable in self.invalid_msgs_as_jsonable:
            with pytest.raises(ValidationError):
                _ = self.ModelClass.parse_obj(invalid_msg_as_jsonable)
                # This will only be executed if the test fails.
                print(invalid_msg_as_jsonable)

    def test_validation_error_raised_for_invalid_json(self):
        """
        Verify that each invalid message provided to `parse_raw()`triggers
        a `ValidationError`
        """
        for invalid_msg_as_jsonable in self.invalid_msgs_as_jsonable:
            invalid_msg_as_json = json.dumps(invalid_msg_as_jsonable)
            with pytest.raises(ValidationError):
                _ = self.ModelClass.parse_raw(invalid_msg_as_json)
                # This will only be executed if the test fails.
                print(invalid_msg_as_jsonable)


class GenericMessageSerializationTestBEMcom(GenericMessageSerializationTest):
    """
    Extends `GenericMessageSerializationTest` with tests about serialization
    from and to BEMCom message format.

    Attributes:
    -----------
    ModelClass : pydantic model class
        The model that is used to serialize/deserialize the data.
    msgs_as_python : list of anything.
        The Python representation of the as defined in `testdata`.
        Each item in the list is treated as distinct message to
        verfiy correct operation for.
    msgs_as_jsonable : list of anything.
        Similar to `data_as_pyhton` but for JSONable representation.
        See the `testdata` module docstring for a discussion why we
        use JSONable representation instead of direct JSON.
    msgs_as_bemcom : list of anything.
        Similar to `msgs_as_jsonable` but for the BEMCom representation.
    invalid_msgs_as_jsonable : list of anything.
        Similar to `msgs_as_jsonable` but messages that are expected
        to cause an error during validation.
    """

    ModelClass = None
    msgs_as_bemcom = None

    def test_python_to_jsonable_bemcom(self):
        """
        Verify that the model can be used to generate the expected JSONable
        output in BEMCom format.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_bemcom)
        for msg_as_python, expected_msg_as_bemcom in test_messages:

            model_instance = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            actual_msg_as_bemcom = model_instance.jsonable_bemcom()

            assert actual_msg_as_bemcom == expected_msg_as_bemcom

    def test_python_to_json_bemcom(self):
        """
        Verify that the model can be used to generate the expected JSON output
        in BEMCom format.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_bemcom)
        for msg_as_python, expected_msg_as_bemcom in test_messages:

            model_instance = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            actual_msg_as_json_bemcom = model_instance.json_bemcom()
            actual_msg_as_bemcom = json.loads(actual_msg_as_json_bemcom)

            assert actual_msg_as_bemcom == expected_msg_as_bemcom

    def test_bemcom_jsonable_to_python_object(self):
        """
        Check that the model can be used to parse BEMcom messages that
        have already been processed with `json.loads`
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_bemcom)
        for msg_as_python, msg_as_bemcom in test_messages:

            expected_msg_as_obj = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            actual_msg_as_obj = self.ModelClass.parse_obj_bemcom(msg_as_bemcom)

            assert actual_msg_as_obj == expected_msg_as_obj

    def test_bemcom_json_to_python_object(self):
        """
        Check that the model can be used to parse the BEMCom messages
        represented as JSON string.
        """
        test_messages = zip(self.msgs_as_python, self.msgs_as_bemcom)
        for msg_as_python, msg_as_bemcom in test_messages:

            expected_msg_as_obj = self.ModelClass.construct_recursive(
                **msg_as_python
            )
            msg_as_json = json.dumps(msg_as_bemcom)
            actual_msg_as_obj = self.ModelClass.parse_raw_bemcom(msg_as_json)

            assert actual_msg_as_obj == expected_msg_as_obj


class GenericServiceMethodTests:
    """
    A collection of test methods that should be useful for all
    product services derived from `esg.services`.

    Attributes:
    -----------
    service : Service class instance.
        This is the service class to be tested, e.g. `ExampleService()`
    inputs_jsonable : list of dict (JSONable representation)
        A list of input objects that `test_process_request_output_correct`
        uses to validate the `process_request` method.
    expected_outputs_jsonable : list of dict (JSONable representation)
        A list of output objects that `test_process_request_output_correct`
        will expect the `process_request` method to compute.
    """

    service = None
    inputs_jsonable = None
    expected_outputs_jsonable = None

    def call_service_method(self, method, *args, **kwargs):
        """
        This is a helper that methods and returns the result, regardless
        if the message is async or sync.
        """
        if iscoroutinefunction(method):
            result = asyncio.new_event_loop().run_until_complete(
                method(*args, **kwargs)
            )
        else:
            result = method(*args, **kwargs)
        return result

    def test_post_request_passes_input_data(self):
        """
        Check that `post_request` passes the input data to the correct
        function. There is nothing else the method should do.
        """
        service = self.service
        service.handle_post_request = MagicMock(return_value=async_return())
        test_input_data = MagicMock()

        self.call_service_method(
            service.post_request, input_data=test_input_data
        )

        assert service.handle_post_request.called
        actual_kwargs = service.handle_post_request.call_args.kwargs
        expected_kwargs = {"input_data": test_input_data}

        assert actual_kwargs == expected_kwargs

    def test_post_request_and_return_result_passes_input_data(self):
        """
        Check that `post_request_and_return_result` passes the input data
        to the correct function. There is nothing else the method should do.
        """
        service = self.service
        service.handle_post_request_and_return_result = MagicMock(
            return_value=async_return()
        )
        test_input_data = MagicMock()

        self.call_service_method(
            service.post_request_and_return_result, input_data=test_input_data
        )

        assert service.handle_post_request_and_return_result.called
        actual_kwargs = (
            service.handle_post_request_and_return_result.call_args.kwargs
        )
        expected_kwargs = {"input_data": test_input_data}

        assert actual_kwargs == expected_kwargs

    def test_process_request_output_correct(self):
        """
        Verify that process request computes the intended outputs.
        """
        service = self.service

        test_data = zip(self.inputs_jsonable, self.expected_outputs_jsonable)
        for input_data_jsonable, expected_output_data_jsonable in test_data:
            input_data = service.InputData.parse_obj(input_data_jsonable)
            actual_output_data_jsonable = self.call_service_method(
                method=service.process_request, input_data=input_data,
            )

            assert actual_output_data_jsonable == expected_output_data_jsonable


class GenericEndToEndServiceTests:
    """
    Checks that the service can be used end to end.

    This checks some functionality that is not directly defined by
    the Service but it's parent class. It is checked here again for
    those functions that affect the usage of the service.

    Attributes:
    -----------
    service : Service class instance.
        This is the service class to be tested, e.g. `ExampleService()`
    test_client: fastapi.fastapi.testclient.TestClient instance
        This is the test client to fake service operation.
        E.g. `TestClient(self.service.app)`
    inputs_jsonable : list of dict (JSONable representation)
        A list of input objects that that are presented to the service.
    expected_outputs_jsonable : list of dict (JSONable representation)
        A list of output objects that will be expected to be returned.
    """

    service = None
    test_client = None
    inputs_jsonable = None
    expected_outputs_jsonable = None

    def test_service_root_online(self):
        """
        If this is ok the FastApi app should be able to start up.
        """
        response = self.test_client.get("/")
        assert response.status_code == 200

    def test_request_id_returned(self):
        """
        Verify that upon creating a request we get a request_ID back.
        """
        test_data = zip(self.inputs_jsonable, self.expected_outputs_jsonable)
        for input_data_jsonable, expected_output_data_jsonable in test_data:
            response = self.test_client.post(
                "/request/", data=json.dumps(input_data_jsonable)
            )
            assert response.status_code == 201
            assert "request_ID" in response.json()

    def test_status_text_is_returned(self):
        """
        Check that we can access a status text directly after posting a request.
        """
        test_data = zip(self.inputs_jsonable, self.expected_outputs_jsonable)
        for input_data_jsonable, expected_output_data_jsonable in test_data:
            response = self.test_client.post(
                "/request/", data=json.dumps(input_data_jsonable)
            )
            request_ID = response.json()["request_ID"]
            response = self.test_client.get("/request/%s/status/" % request_ID,)
            assert response.status_code == 200
            assert "status_text" in response.json()

    def test_result_can_be_obtained_and_status_becomes_ready(self):
        """
        Validate that the result of the request can be retrieved and contains
        the expected data. Also verify that the status of the request is
        "ready" once the result is available.
        """
        test_data = zip(self.inputs_jsonable, self.expected_outputs_jsonable)
        for input_data_jsonable, expected_output_data_jsonable in test_data:
            response = self.test_client.post(
                "/request/", data=json.dumps(input_data_jsonable)
            )
            request_ID = response.json()["request_ID"]
            response = self.test_client.get("/request/%s/result/" % request_ID,)
            assert response.status_code == 200
            assert response.json() == expected_output_data_jsonable

            # Once the result is ready the status should be set to "ready", it
            # easier to test this way as polling here until ready is set and
            # then retrieve the result as the /request/{request_ID}/result/
            # endpoint should be able to wait until the result is ready.
            response = self.test_client.get("/request/%s/status/" % request_ID,)
            assert response.status_code == 200
            assert response.json()["status_text"] == "ready"
