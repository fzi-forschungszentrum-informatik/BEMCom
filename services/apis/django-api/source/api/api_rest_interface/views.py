"""
Quickly create the necessary viewsets for the REST API, by adapting the
generic versions from ems_utils.model_format.

The __doc__ objects are overloaded to extract the right docs from
the generic implementation in ems_utils to display in the API schema.
"""
import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404

from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue
from api_main.models.datapoint import DatapointSchedule
from api_main.models.datapoint import DatapointSetpoint
from api_main.connector_mqtt_integration import ConnectorMQTTIntegration
from ems_utils.message_format.views import DatapointViewSetTemplate
from ems_utils.message_format.views import DatapointValueViewSetTemplate
from ems_utils.message_format.views import DatapointScheduleViewSetTemplate
from ems_utils.message_format.views import DatapointSetpointViewSetTemplate
from .serializers import DatapointSerializer
from .filters import DatapointFilter, DatapointValueFilter
from .filters import DatapointSetpointFilter, DatapointScheduleFilter

class DatapointViewSet(DatapointViewSetTemplate):
    __doc__ = Datapoint.__doc__
    datapoint_model = Datapoint
    serializer_class = DatapointSerializer
    queryset = Datapoint.objects.all()
    filterset_class = DatapointFilter

    def retrieve(self, request, dp_id):
        datapoint = get_object_or_404(
            self.queryset, id=dp_id, is_active=True
        )
        serializer = self.serializer_class(datapoint)
        return Response(serializer.data)

    def list(self, request):
        """
        Similar to the version DatapointViewSetTemplate but only returns
        active Datapoints.
        """
        datapoints = self.queryset.filter(is_active=True)
        datapoints = self.filter_queryset(datapoints)
        serializer = self.serializer_class(datapoints, many=True)
        return Response(serializer.data)

    def create(self, request):
        raise NotImplementedError(
            "It is not possible to manually create datapoints. Only "
            "connectors can define new Datapoints."
        )


class DatapointValueViewSet(DatapointValueViewSetTemplate):
    __doc__ = DatapointValue.__doc__.strip()
    model = DatapointValue
    datapoint_model = Datapoint
    queryset = DatapointValue.objects.all()
    create_for_actuators_only = True
    filterset_class = DatapointValueFilter

    def create(self, request, dp_id):
        """
        Don't write to DB, this is done automatically once the message is
        received back from the message broker. Instead just publish the msg.
        """
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        if self.create_for_actuators_only and datapoint.type != "actuator":
            raise ValidationError(
                "This message can only be written for an actuator datapoint."
            )

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Send the message to the MQTT broker.
        mqtt_topic = datapoint.get_mqtt_topics()["value"]
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.client.publish(
            topic=mqtt_topic,
            payload=json.dumps(validated_data)
        )
        return Response(validated_data, status=status.HTTP_201_CREATED)

class DatapointScheduleViewSet(DatapointScheduleViewSetTemplate):
    __doc__ = DatapointSchedule.__doc__.strip()
    model = DatapointSchedule
    datapoint_model = Datapoint
    queryset = DatapointSchedule.objects.all()
    create_for_actuators_only = True

    def create(self, request, dp_id):
        """
        Don't write to DB, this is done automatically once the message is
        received back from the message broker. Instead just publish the msg.
        """
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        if self.create_for_actuators_only and datapoint.type != "actuator":
            raise ValidationError(
                "This message can only be written for an actuator datapoint."
            )

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Send the message to the MQTT broker.
        mqtt_topic = datapoint.get_mqtt_topics()["schedule"]
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.client.publish(
            topic=mqtt_topic,
            payload=json.dumps(validated_data),
            retain=True,
        )
        return Response(validated_data, status=status.HTTP_201_CREATED)

class DatapointSetpointViewSet(DatapointSetpointViewSetTemplate):
    __doc__ = DatapointSetpoint.__doc__.strip()
    model = DatapointSetpoint
    datapoint_model = Datapoint
    queryset = DatapointSetpoint.objects.all()
    create_for_actuators_only = True

    def create(self, request, dp_id):
        """
        Don't write to DB, this is done automatically once the message is
        received back from the message broker. Instead just publish the msg.
        """
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        if self.create_for_actuators_only and datapoint.type != "actuator":
            raise ValidationError(
                "This message can only be written for an actuator datapoint."
            )

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Send the message to the MQTT broker.
        mqtt_topic = datapoint.get_mqtt_topics()["setpoint"]
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.client.publish(
            topic=mqtt_topic,
            payload=json.dumps(validated_data),
            retain=True,
        )
        return Response(validated_data, status=status.HTTP_201_CREATED)
