#!/usr/bin/env python3
"""
Note: This file is called `test_base_model` to prevent name clashes with
`test_base` in the services folder.
"""
from datetime import datetime
from datetime import timezone
import json
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Json

from esg.models.base import _BaseModel


class TestModelWithListAsRoot:
    """
    These tests should only fail if pydantic changes conventions for handling
    lists as root elements. If these fail you can expect a lot of other model
    related tests to fail too.

    Background:
    Pydantic docs suggest to to overload `__iter__` and `__getitem__` for
    models that use a list as root element. See here:
    https://pydantic-docs.helpmanual.io/usage/models/#custom-root-types
    However, this would break convention with the expected inputs of
    `construct` and  outputs of `dict` which both explicitly require the
    `__root__` key.

    """

    @classmethod
    def setup_class(cls):
        """
        Define model used for all tests here.

        Don't use `_BaseModel` here, as test might fail then if
        `ModelWithListAsRootMixin` has side effects with it.
        This case is reflected in `TestBaseModel` above for models using
        lists.
        """

        class TestListItemModel(BaseModel):
            value: float

        cls.TestListItemModel = TestListItemModel

        class TestListModel(BaseModel):
            __root__: List[TestListItemModel]

        cls.TestListModel = TestListModel

        cls.test_obj = {"__root__": [{"value": 21.0}, {"value": 22.5}]}

    def test_parse_obj(self):
        """
        Verify that we can specify the '__root__' element explicitly.
        """
        _ = self.TestListModel.parse_obj(self.test_obj)

    def test_dict(self):
        """
        Verify that once converted back to Python we will receive the
        `__root__` key back.

        If `test_parse_obj` above fails this test will always fail too.
        """
        instance = self.TestListModel.parse_obj(self.test_obj)

        expected_dict = self.test_obj

        actual_dict = instance.dict()

        assert actual_dict == expected_dict


class TestBaseModel:
    """
    Verify that functionality of the custom `_BaseModel`.

    `_BaseModel` is only used to allow the custom handling of Json fields
    and to add additional functionality for parsing BEMCom messages.
    Hence we only test these aspects.

    These tests are certainly partly redundant to the tests of the models
    derived from `_BaseModel`. However, if the tests of this class fail
    you know that any downstream failure is due to errors in `_BaseModel`.
    """

    def setup_method(self, method):
        """
        Provide a simple model suitable for many tests.
        """

        class GenericTestModel(_BaseModel):
            json_value: Json
            float_value: float
            string_value: str
            time: datetime

        self.GenericTestModel = GenericTestModel

        self.generic_test_obj_python_values = {
            "json_value": 21.1,
            "float_value": 22.2,
            "string_value": "23.3",
            "time": datetime(2022, 2, 22, 2, 53, tzinfo=timezone.utc),
        }

        self.generic_test_obj = GenericTestModel.construct(
            **self.generic_test_obj_python_values
        )

        self.generic_test_obj_jsonable = {
            "json_value": "21.1",
            "float_value": 22.2,
            "string_value": "23.3",
            "time": "2022-02-22T02:53:00+00:00",
        }

        self.generic_test_obj_jsonable_bemcom = {
            "json_value": "21.1",
            "float_value": 22.2,
            "string_value": "23.3",
            "timestamp": 1645498380000,
        }

    def test_json_field_parsed(self):
        """
        Verify that a JSON field is parsed on object creation.

        This is actually taken care of by pydantic, but as this feature
        is super important for use we better double check.
        """

        class TestModel(_BaseModel):
            json_value: Json

        # Note that construct doesn't validate and hence does not parse.
        expected_obj = TestModel.construct(json_value=21.1)
        actual_obj = TestModel(json_value="21.1")

        assert actual_obj == expected_obj

    def test_to_jsonable_on_root(self):
        """
        Test that the the Value of any Json type field on model root level
        is encoded as expected.
        """
        actual_jsonable = self.generic_test_obj.jsonable()
        expected_jsonable = self.generic_test_obj_jsonable

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_for_model_lists(self):
        """
        We often have the Json field stored in some list of messages.
        Verify these fields are handled correctly too.
        """

        class TestListItemModel(_BaseModel):
            value: Json

        class TestListModel(_BaseModel):
            __root__: List[TestListItemModel]

        obj = TestListModel.construct(
            __root__=[
                TestListItemModel.construct(value=21.0),
                TestListItemModel.construct(value=False),
                TestListItemModel.construct(value="True"),
            ]
        )

        expected_jsonable = [
            {"value": "21.0"},
            {"value": "false"},
            {"value": '"True"'},
        ]

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_json_field_direct_in_list(self):
        """
        Check that Json fields directly placed in lists are encoded.
        Use case is the Datapoint model.
        """

        class TestListModel(_BaseModel):
            value: List[Json]

        obj = TestListModel.construct(value=[21.0, False, "True"],)

        expected_jsonable = {"value": ["21.0", "false", '"True"']}

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_for_normal_types_on_root(self):
        """
        _Value and _Time models are directly defined as a normal (i.e. not
        list or dict) type assigned to model root.
        """

        class TestItemModel(_BaseModel):
            __root__: Json

        class TestModel(_BaseModel):
            items_list: List[TestItemModel]
            items_dict: Dict[str, TestItemModel]

        obj = TestModel.construct(
            items_list=[
                TestItemModel.construct(__root__=21.0),
                TestItemModel.construct(__root__=False),
                TestItemModel.construct(__root__="True"),
            ],
            items_dict={
                "1": TestItemModel.construct(__root__=21.0),
                "2": TestItemModel.construct(__root__=False),
                "3": TestItemModel.construct(__root__="True"),
            },
        )

        expected_jsonable = {
            "items_list": ["21.0", "false", '"True"'],
            "items_dict": {"1": "21.0", "2": "false", "3": '"True"'},
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_for_nested_models(self):
        """
        Also verify that nested models are covered.
        """

        class TestChildModel(_BaseModel):
            value: Json

        class TestParentModel(_BaseModel):
            child: TestChildModel

        obj = TestParentModel.construct(
            child=TestChildModel.construct(value=21.0),
        )

        expected_jsonable = {
            "child": {"value": "21.0"},
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_for_list_models(self):
        """
        Setpoint and Schedule Messages use lists of models.
        """

        class TestListItemModel(_BaseModel):
            value: Json

        class TestListModel(_BaseModel):
            list_name: List[TestListItemModel]

        obj = TestListModel.construct(
            list_name=[
                TestListItemModel.construct(value=21.0),
                TestListItemModel.construct(value=False),
                TestListItemModel.construct(value="True"),
            ]
        )

        expected_jsonable = {
            "list_name": [
                {"value": "21.0"},
                {"value": "false"},
                {"value": '"True"'},
            ]
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_for_nested_lists(self):
        """
        Some models (like ValueMessageList) are defined directly with a
        list as root type. Check these can be parsed to json too.
        """

        class TestListItemModel(_BaseModel):
            value: Json

        class TestListModel(_BaseModel):
            __root__: List[TestListItemModel]

        class TestListParentModel(_BaseModel):
            test_list: TestListModel

        obj = TestListParentModel.construct(
            test_list=TestListModel.construct(
                __root__=[
                    TestListItemModel.construct(value=21.0),
                    TestListItemModel.construct(value=False),
                    TestListItemModel.construct(value="True"),
                ]
            )
        )

        expected_jsonable = {
            "test_list": [
                {"value": "21.0"},
                {"value": "false"},
                {"value": '"True"'},
            ]
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_for_nested_dicts(self):
        """
        Some models (like GeographicPositionDict) are defined directly with a
        dict as root type. Check these can be parsed to json too.
        """

        class TestDictItemModel(_BaseModel):
            value: Json

        class TestDictModel(_BaseModel):
            __root__: Dict[str, TestDictItemModel]

        class TestDictParentModel(_BaseModel):
            test_dict: TestDictModel

        obj = TestDictParentModel.construct(
            test_dict=TestDictModel.construct(
                __root__={
                    "1": TestDictItemModel.construct(value=21.0),
                    "2": TestDictItemModel.construct(value=False),
                    "3": TestDictItemModel.construct(value="True"),
                }
            )
        )

        expected_jsonable = {
            "test_dict": {
                "1": {"value": "21.0"},
                "2": {"value": "false"},
                "3": {"value": '"True"'},
            }
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_to_jsonable_bemcom(self):
        """
        Test that a message is converted into BEMCom format as expected.
        is encoded into BEMCom format as expected.
        """
        actual_jsonable = self.generic_test_obj.jsonable_bemcom()
        expected_jsonable = self.generic_test_obj_jsonable_bemcom

        assert actual_jsonable == expected_jsonable

    def test_to_json(self):
        """
        Simple consistency test that `json()` returns the right stuff
        assuming that `jsonable()` is implemented correctly.
        """
        expected_json = json.dumps(self.generic_test_obj.jsonable())
        actual_json = self.generic_test_obj.json()

        assert actual_json == expected_json

    def test_to_json_bemcom(self):
        """
        Simple consistency test that `json()` returns the right stuff
        assuming that `jsonable()` is implemented correctly.
        """
        expected_json = json.dumps(self.generic_test_obj.jsonable_bemcom())
        actual_json = self.generic_test_obj.json_bemcom()

        assert actual_json == expected_json

    def test_parse_obj_bemcom(self):
        """
        Test that `parse_obj_bemcom` handles timestamp fields as expected.
        """
        expected_obj = self.generic_test_obj

        actual_obj = self.GenericTestModel.parse_obj_bemcom(
            self.generic_test_obj_jsonable_bemcom
        )

        assert actual_obj == expected_obj

    def test_parse_raw_bemcom(self):
        """
        Test that `parse_obj_bemcom` handles timestamp fields as expected.
        """
        expected_obj = self.generic_test_obj
        actual_obj = self.GenericTestModel.parse_raw_bemcom(
            json.dumps(self.generic_test_obj_jsonable_bemcom)
        )

        assert actual_obj == expected_obj

    def test_construct_recursive_for_flat_models(self):
        """
        Sanity check, verify that `construct_recursive` works on flat
        models (i.e. for models which don't need recursion).
        """
        expected_obj = self.generic_test_obj
        actual_obj = self.GenericTestModel.construct_recursive(
            **self.generic_test_obj_python_values
        )

        # Compare jsonable, as jsonable fails if the values have
        # not been set correctly.
        assert actual_obj.jsonable() == expected_obj.jsonable()

    def test_construct_recursive_for_list_models(self):
        """
        Check that child models in lists are instantiated correctly
        """

        class TestListItemModel(_BaseModel):
            value: Json

        class TestListModel(_BaseModel):
            __root__: List[TestListItemModel]

        obj = TestListModel.construct_recursive(
            __root__=[{"value": 21.0}, {"value": False}, {"value": "True"}]
        )

        expected_jsonable = [
            {"value": "21.0"},
            {"value": "false"},
            {"value": '"True"'},
        ]

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_json_field_direct_in_list(self):
        """
        Check that Json fields directly placed in lists are encoded.
        Use case is the Datapoint model.
        """

        class TestListModel(_BaseModel):
            value: List[Json]

        obj = TestListModel.construct_recursive(value=[21.0, False, "True"],)

        expected_jsonable = {"value": ["21.0", "false", '"True"']}

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_normal_types_on_root(self):
        """
        _Value and _Time models are directly defined as a normal (i.e. not
        list or dict) type assigned to model root.
        """

        class TestItemModel(_BaseModel):
            __root__: Json

        class TestModel(_BaseModel):
            items_list: List[TestItemModel]
            items_dict: Dict[str, TestItemModel]

        obj = TestModel.construct_recursive(
            items_list=[21.0, False, "True"],
            items_dict={"1": 21.0, "2": False, "3": "True"},
        )

        expected_jsonable = {
            "items_list": ["21.0", "false", '"True"'],
            "items_dict": {"1": "21.0", "2": "false", "3": '"True"'},
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_nested_list(self):
        """
        Check that lists that are child models are correctly handled too.
        """

        class TestListItemModel(_BaseModel):
            value: Json

        class TestListModel(_BaseModel):
            __root__: List[TestListItemModel]

        class TestListParentModel(_BaseModel):
            test_list: TestListModel

        obj = TestListParentModel.construct_recursive(
            test_list=[{"value": 21.0}, {"value": False}, {"value": "True"}]
        )

        expected_jsonable = {
            "test_list": [
                {"value": "21.0"},
                {"value": "false"},
                {"value": '"True"'},
            ]
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_nested_list_of_normal_types(self):
        """
        Like the test above, but this time for a list with conventional
        types as items.

        Note: This also tests if `jsonable()` handles this case correctly.
        """

        class TestListModel(_BaseModel):
            __root__: List[str]

        class TestListParentModel(_BaseModel):
            test_list: TestListModel

        obj = TestListParentModel.construct_recursive(
            test_list=["21.0", "false", "True"]
        )

        expected_jsonable = {"test_list": ["21.0", "false", "True"]}

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_nested_dicts(self):
        """
        Some models (like GeographicPositionDict) are defined directly with a
        dict as root type. Check recursive construction works for those too.
        """

        class TestDictItemModel(_BaseModel):
            value: Json

        class TestDictModel(_BaseModel):
            __root__: Dict[str, TestDictItemModel]

        class TestDictParentModel(_BaseModel):
            test_dict: TestDictModel

        obj = TestDictParentModel.construct_recursive(
            test_dict={
                "1": {"value": 21.0},
                "2": {"value": False},
                "3": {"value": "True"},
            }
        )

        expected_jsonable = {
            "test_dict": {
                "1": {"value": "21.0"},
                "2": {"value": "false"},
                "3": {"value": '"True"'},
            }
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_nested_dict_of_normal_types(self):
        """
        Like the test above, but this time for a list with conventional
        types as items.

        Note: This also tests if `jsonable()` handles this case correctly.
        """

        class TestDictModel(_BaseModel):
            __root__: Dict[str, str]

        class TestDictParentModel(_BaseModel):
            test_dict: TestDictModel

        obj = TestDictParentModel.construct_recursive(
            test_dict={"1": "21.0", "2": "false", "3": "True"}
        )

        expected_jsonable = {
            "test_dict": {"1": "21.0", "2": "false", "3": "True"}
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_nested_model(self):
        """
        Check that child models in lists are instantiated correctly
        """

        class TestChildModel(_BaseModel):
            value: Json

        class TestParentModel(_BaseModel):
            child: TestChildModel

        obj = TestParentModel.construct_recursive(**{"child": {"value": 21.0}})

        expected_jsonable = {
            "child": {"value": "21.0"},
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_none_nested_model_(self):
        """
        Check that child models are handled correctly if they are set to None.
        """

        class TestChildModel(_BaseModel):
            value: Json

        class TestParentModel(_BaseModel):
            child: TestChildModel

        obj = TestParentModel.construct_recursive(**{"child": None})

        expected_jsonable = {
            "child": None,
        }

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable

    def test_construct_recursive_for_list_field_with_None_value(self):
        """
        A list item holding a None value (instead of a list) might happen
        but has caused errors in construct_recursive.
        """

        class TestListModel(_BaseModel):
            value: List[str]

        obj = TestListModel.construct_recursive(value=None,)

        expected_jsonable = {"value": None}

        actual_jsonable = obj.jsonable()

        assert actual_jsonable == expected_jsonable
