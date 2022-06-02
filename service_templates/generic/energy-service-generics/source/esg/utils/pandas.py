#!/usr/bin/env python3
"""
Some utility methods to parse time series to Pandas objects and vice versa.
"""
try:
    import pandas as pd
    from numpy import nan as np_nan

except ModuleNotFoundError:
    pd = None

from esg.models.datapoint import ValueMessageList
from esg.models.datapoint import ValueDataFrame


def _check_pandas_available():
    if pd is None:
        raise ModuleNotFoundError("This function requires pandas to work.")


def series_from_value_message_list(value_message_list):
    """
    Parses a pandas.Series from the content of a `ValueMessageList` instance.

    Arguments:
    ----------
    value_message_list : ValueMessageList instance
        As defined in esg.models.datapoint.ValueMessageList

    Returns:
    --------
    series : pandas.Series
        A series holding the same information as the value_message_list.
    """
    _check_pandas_available()
    msg_as_dict = value_message_list.dict()
    times = [m["time"] for m in msg_as_dict["__root__"]]
    values = [m["value"] for m in msg_as_dict["__root__"]]
    series = pd.Series(index=times, data=values)

    return series


def value_message_list_from_series(series):
    """
    Transforms a pandas.Series into a `ValueMessageList` instance.

    Arguments:
    ----------
    series : pandas.Series
        A series holding the same information as the value_message_list.

    Returns:
    --------
    value_message_list : ValueMessageList instance
        As defined in esg.models.datapoint.ValueMessageList
    """
    _check_pandas_available()
    value_messages = []
    for time, value in series.iteritems():
        if value != value:
            # This should only be true for NaN values.
            value = None
        value_messages.append({"value": value, "time": time})
    value_message_list = ValueMessageList.construct_recursive(
        __root__=value_messages
    )
    return value_message_list


def dataframe_from_value_dataframe(value_dataframe):
    """
    Parse Pydantic object to Pandas dataframe.

    Arguments:
    ----------
    value_dataframe : ValueDataFrame instance.
        The pydantic object representation of the data.

    Returns:
    --------
    pandas_dataframe : pandas.DataFrame
        The pandas dataframe representation of the data.
    """
    value_dataframe_as_dict = value_dataframe.dict()
    pandas_dataframe = pd.DataFrame(
        index=value_dataframe_as_dict["times"],
        data=value_dataframe_as_dict["values"],
    )
    return pandas_dataframe


def value_dataframe_from_dataframe(pandas_dataframe):
    """
    Parse Pydantic object to Pandas dataframe.

    Arguments:
    ----------
    pandas_dataframe : pandas.DataFrame
        The pandas dataframe representation of the data.

    Returns:
    --------
    value_dataframe : ValueDataFrame instance.
        The pydantic object representation of the data.
    """
    from pprint import pprint

    pandas_dataframe_non_nan = pandas_dataframe.replace(np_nan, None)
    value_dataframe = ValueDataFrame.construct_recursive(
        times=pandas_dataframe_non_nan.index,
        values=pandas_dataframe_non_nan.to_dict(orient="list"),
    )
    # raise RuntimeError()
    return value_dataframe
