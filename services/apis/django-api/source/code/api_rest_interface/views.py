"""
Quickly create the necessary viewsets for the REST API, by adapting the
generic versions from ems_utils.model_format.

The __doc__ objects are overloaded to extract the right docs from
the generic implementation in ems_utils to display in the API schema.
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
from .serializers import DatapointSerializer

class DatapointViewSet(DatapointViewSetTemplate):
    __doc__ = Datapoint.__doc__
    datapoint_model = Datapoint
    serializer_class = DatapointSerializer
    queryset = Datapoint.objects.none() # Required for DjangoModelPermissions

    def create(self, request):
        raise NotImplementedError(
            "It is not possible to manually create datapoints. Only "
            "connectors can define new Datapoints."
        )


class DatapointValueViewSet(DatapointValueViewSetTemplate):
    __doc__ = DatapointValue.__doc__.strip()
    model = DatapointValue
    datapoint_model = Datapoint
    create_for_actuators_only = True
    # Required for DjangoModelPermissions
    queryset = DatapointValue.objects.none()


class DatapointScheduleViewSet(DatapointScheduleViewSetTemplate):
    __doc__ = DatapointSchedule.__doc__.strip()
    model = DatapointSchedule
    datapoint_model = Datapoint
    create_for_actuators_only = True
    # Required for DjangoModelPermissions
    queryset = DatapointSchedule.objects.none()


class DatapointSetpointViewSet(DatapointSetpointViewSetTemplate):
    __doc__ = DatapointSetpoint.__doc__.strip()
    model = DatapointSetpoint
    datapoint_model = Datapoint
    create_for_actuators_only = True
    # Required for DjangoModelPermissions
    queryset = DatapointSetpoint.objects.none()
