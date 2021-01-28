"""
Quickly create the necessary viewsets for the REST API, by adapting the
generic versions from ems_utils.model_format
"""

from django.shortcuts import render

from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue
from api_main.models.datapoint import DatapointSchedule
from api_main.models.datapoint import DatapointSetpoint
from ems_utils.message_format.views import DatapointViewSetTemplate
from ems_utils.message_format.views import DatapointValueViewSetTemplate
from ems_utils.message_format.views import DatapointScheduleViewSetTemplate
from ems_utils.message_format.views import DatapointSetpointViewSetTemplate


class DatapointViewSet(DatapointViewSetTemplate):
    datapoint_model = Datapoint

    def create(self, request):
        raise NotImplementedError(
            "It is not possible to manually create datapoints. Only "
            "connectors can define new Datapoints."
        )


class DatapointValueViewSet(DatapointValueViewSetTemplate):
    model = DatapointValue
    datapoint_model = Datapoint


class DatapointScheduleViewSet(DatapointScheduleViewSetTemplate):
    model = DatapointSchedule
    datapoint_model = Datapoint


class DatapointSetpointViewSet(DatapointSetpointViewSetTemplate):
    model = DatapointSetpoint
    datapoint_model = Datapoint
