from django.db import models
from django_filters import FilterSet, NumberFilter, CharFilter

from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue
from api_main.models.datapoint import DatapointSetpoint
from api_main.models.datapoint import DatapointSchedule
from ems_utils.timestamp import datetime_from_timestamp


class DatapointFilter(FilterSet):
    """
    Some useful filters for the Datapoint list.
    """

    class Meta:
        model = Datapoint
        fields = {
            "id": ["in"],
            "connector__name": ["exact", "icontains"],
            "key_in_connector": ["exact", "icontains"],
            "short_name": ["exact", "icontains"],
            "description": ["exact", "icontains"],
            "type": ["exact"],
            "data_format": ["exact", "icontains"],
            "unit": ["exact", "icontains"],
        }


class TimestampFilter(FilterSet):
    timestamp__gte = NumberFilter(
        field_name="time__gte", lookup_expr="gte", method="filter_timestamp"
    )
    timestamp__gt = NumberFilter(
        field_name="time__gt", lookup_expr="gt", method="filter_timestamp"
    )
    timestamp__lte = NumberFilter(
        field_name="time__lte", lookup_expr="lte", method="filter_timestamp"
    )
    timestamp__lt = NumberFilter(
        field_name="time__lt", lookup_expr="lt", method="filter_timestamp"
    )

    def filter_timestamp(self, queryset, lookup_expr, value):
        lookup = "__".join([lookup_expr])
        ts_as_dt = datetime_from_timestamp(float(value))
        return queryset.filter(**{lookup: ts_as_dt})


class DatapointValueFilter(TimestampFilter):
    """
    Allows selecting values by timestamp ranges.
    """

    interval = CharFilter(method="apply_timebucket")

    class Meta:
        model = DatapointValue
        fields = []  # The custom methods are added automatically.

    def apply_timebucket(self, queryset, _, value):
        """
        Applies the time bucket to compute average values over time slots.

        Arguments:
        ----------
        queryset : TimescaleQuerySet
            The queryset to filter.
        value: string
            A PostgreSQL interval string, e.g. "15 minutes"."

        TODO: Distinguish by datapoints here! E.g. with the following
        annotation:
        queryset = queryset.annotate(datapoint__id=models.F("datapoint__id")))

        """
        queryset = queryset.time_bucket("time", value)
        queryset = queryset.annotate(value=models.Avg("_value_float"))
        # Late first, newest item last in list. This should not cost anything
        # extra as the timescaledb django plugin orders too, but just the other
        # way around.
        queryset = queryset.order_by("bucket")
        return queryset


class DatapointSetpointFilter(TimestampFilter):
    """
    Allows selecting values by timestamp ranges.
    """

    class Meta:
        model = DatapointSetpoint
        fields = []  # The custom methods are added automatically.


class DatapointScheduleFilter(TimestampFilter):
    """
    Allows selecting values by timestamp ranges.
    """

    class Meta:
        model = DatapointSchedule
        fields = []  # The custom methods are added automatically.
