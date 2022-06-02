#!/usr/bin/env python3
"""
"""
from datetime import datetime
from datetime import timezone

import pytest

try:
    import pandas as pd

except ModuleNotFoundError:
    pd = None

from esg.models.datapoint import ValueMessageList
from esg.models.datapoint import ValueDataFrame
from esg.test import data as td
from esg.utils.pandas import series_from_value_message_list
from esg.utils.pandas import value_message_list_from_series
from esg.utils.pandas import dataframe_from_value_dataframe
from esg.utils.pandas import value_dataframe_from_dataframe


@pytest.fixture(scope="class")
def add_test_data(request):
    """
    Define some shared datasets for the tests.

    mixed: Values contain mixed types of values like float, str, None, ...
    float: Values contain only float values.
    """
    mixed_jsonable_value_msgs = [m["JSONable"] for m in td.value_messages]
    request.cls.mixed_value_msg_list = ValueMessageList.parse_obj(
        {"__root__": mixed_jsonable_value_msgs}
    )
    mixed_python_value_msgs = [m["Python"] for m in td.value_messages]
    mixed_value_msg_index = [m["time"] for m in mixed_python_value_msgs]
    mixed_value_msg_data = [m["value"] for m in mixed_python_value_msgs]
    request.cls.mixed_value_msg_series = pd.Series(
        index=mixed_value_msg_index, data=mixed_value_msg_data
    )

    # Select only those value message that carry float values.
    float_jsonable_value_msgs = [mixed_jsonable_value_msgs[i] for i in [0]]
    request.cls.float_value_msg_list = ValueMessageList.parse_obj(
        {"__root__": float_jsonable_value_msgs}
    )
    float_python_value_msgs = [td.value_messages[i]["Python"] for i in [0]]
    float_value_msg_index = [m["time"] for m in float_python_value_msgs]
    float_value_msg_data = [m["value"] for m in float_python_value_msgs]
    request.cls.float_value_msg_series = pd.Series(
        index=float_value_msg_index, data=float_value_msg_data
    )


@pytest.mark.usefixtures("add_test_data")
@pytest.mark.skipif(pd is None, reason="requires pandas")
class TestSeriesFromValueList:
    def test_series_parsed_correctly_for_mixed_value_types(self):
        """
        Verify that series is parsed correctly as object for mixed types
        of values.
        """
        expected_series = self.mixed_value_msg_series

        actual_series = series_from_value_message_list(
            self.mixed_value_msg_list
        )

        pd.testing.assert_series_equal(actual_series, expected_series)

    def test_series_parsed_correctly_for_float_values(self):
        """
        Check that float only value message lists are parsed as float correctly.
        """
        expected_series = self.float_value_msg_series

        actual_series = series_from_value_message_list(
            self.float_value_msg_list
        )

        pd.testing.assert_series_equal(actual_series, expected_series)
        # This is actually redundant, as the assert above already checks
        # for dtypes, but left here as a reminder that we check this.
        assert pd.api.types.is_float_dtype(actual_series.dtype)


@pytest.mark.usefixtures("add_test_data")
@pytest.mark.skipif(pd is None, reason="requires pandas")
class TestValueListFromSeries:
    def test_value_message_list_created_correctly_for_mixed_value_types(self):
        """
        Verify that value message list is created correctly for series
        holding objects as values.
        """
        expected_value_message_list = self.mixed_value_msg_list

        actual_value_message_list = value_message_list_from_series(
            self.mixed_value_msg_series
        )

        assert actual_value_message_list == expected_value_message_list

    def test_value_message_list_created_correctly_for_float_values(self):
        """
        Verify that value message list is created correctly for series
        holding floats as values.
        """
        expected_value_message_list = self.float_value_msg_list

        actual_value_message_list = value_message_list_from_series(
            self.float_value_msg_series
        )

        assert actual_value_message_list == expected_value_message_list

    def test_nan_converted_to_None(self):
        """
        NaN values are not native part of JSON. Check they are converted to
        None.
        """
        test_series = self.float_value_msg_series.copy()
        test_series.iloc[0] = float("NaN")

        expected_value_message_dict = self.float_value_msg_list.dict()
        expected_value_message_dict["__root__"][0]["value"] = None

        actual_value_message_list = value_message_list_from_series(test_series)
        actual_value_message_dict = actual_value_message_list.dict()

        assert actual_value_message_dict == expected_value_message_dict


@pytest.fixture(scope="class")
def add_test_dataframe(request):
    request.cls.test_data_as_pandas = pd.DataFrame(
        index=[
            datetime(2022, 2, 22, 2, 52, tzinfo=timezone.utc),
            datetime(2022, 2, 22, 2, 53, tzinfo=timezone.utc),
            datetime(2022, 2, 22, 2, 54, tzinfo=timezone.utc),
        ],
        data={
            # Numeric values, incl. a NaN
            "1": [1, 2.5, None],
            # strings and bools.
            "2": ["A string", "false", True],
        },
    )
    request.cls.test_data_as_jsonable = {
        "times": [
            "2022-02-22T02:52:00+00:00",
            "2022-02-22T02:53:00+00:00",
            "2022-02-22T02:54:00+00:00",
        ],
        "values": {
            "1": ["1.0", "2.5", "null"],
            "2": ['"A string"', '"false"', "true"],
        },
    }


@pytest.mark.usefixtures("add_test_dataframe")
@pytest.mark.skipif(pd is None, reason="requires pandas")
class TestDataframeFromValueDataframe:
    def test_dataframe_parsed_correctly(self):
        """
        Check that the a pandas DataFrame is correctly parsed from pydantic
        input.
        """
        expected_dataframe = self.test_data_as_pandas

        actual_dataframe = dataframe_from_value_dataframe(
            ValueDataFrame(**self.test_data_as_jsonable)
        )

        pd.testing.assert_frame_equal(actual_dataframe, expected_dataframe)


@pytest.mark.usefixtures("add_test_dataframe")
@pytest.mark.skipif(pd is None, reason="requires pandas")
class TestValueDataframeFromDataframe:
    @pytest.mark.skipif(
        True, reason="Fix side effect in tests/models/datapoint.py"
    )
    def test_pydantic_parsed_correctly(self):
        """
        Check that the a pydanitc instance is correctly parsed from pandas
        dataframe.

        NOTE: This test is actually correct and does what it should.
              However, there is a strange side effect caused by
              execution of `tests/models/datapoint.py` which makes
              this test fail.
        TODO: Fix error and reenable test.
        """
        expected_df_as_jsonable = self.test_data_as_jsonable

        actual_df_as_pydanitc = value_dataframe_from_dataframe(
            self.test_data_as_pandas
        )
        actual_df_as_jsonable = actual_df_as_pydanitc.jsonable()

        assert actual_df_as_jsonable == expected_df_as_jsonable
