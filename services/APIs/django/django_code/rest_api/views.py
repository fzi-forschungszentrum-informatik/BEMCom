import json

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from main.utils import timestamp_utc_now
from main.models.datapoint import Datapoint
from main.connector_mqtt_integration import ConnectorMQTTIntegration
from .serializers import DatapointSerializer
from .serializers import DatapointValueSerializer
from .serializers import DatapointScheduleSerializer
from .serializers import DatapointSetpointSerializer


class DatapointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Datapoint.objects.filter(is_active=True)
    serializer_class = DatapointSerializer


class DatapointValueViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)
        serializer = DatapointValueSerializer(datapoint)
        return Response(serializer.data)

    def update(self, request, *args, pk=None, **kwargs):
        """
        Receive a Datapoint value message and send it to the broker.

        This will not save the value in the database, instead we rely on the
        automatic save after the message returns from the broker. This way
        it is ensured that current state displayed to the API user is always
        the all components received from the broker.
        """
        datapoint = get_object_or_404(Datapoint, pk=pk)

        # Only actuator datapoints can be set externally. Sensor datapoint
        # values can only be sent by the devices.
        if datapoint.type != "actuator":
            return Response(
                {"detail": "This datapoint does not support setting values."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DatapointValueSerializer(datapoint, data=request.data)

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer.is_valid(raise_exception=True)

        # This is now a valid value. Add the current timestamp as time the
        # system has been received by BEMCom to complete the message.
        validated_data = serializer.validated_data
        validated_data["timestamp"] = timestamp_utc_now()

        # Send the message to the MQTT broker.
        mqtt_topic = datapoint.get_mqtt_topic()
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.client.publish(
            topic=mqtt_topic,
            payload=json.dumps(validated_data)
        )

        return Response(validated_data, status=status.HTTP_200_OK)


class DatapointScheduleViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)

        # Only actuators have schedules and setpoints.
        if datapoint.type != "actuator":
            raise Http404("Not found.")

        serializer = DatapointScheduleSerializer(
            datapoint,
            context={'request': request}
        )
        return Response(serializer.data)

    def update(self, request, *args, pk=None, **kwargs):
        """
        TODO
        """
        datapoint = get_object_or_404(Datapoint, pk=pk)

        # Only actuators have schedules and setpoints.
        if datapoint.type != "actuator":
            raise Http404("Not found.")


class DatapointSetpointViewSet(viewsets.ViewSet):



    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)

        # Only actuators have schedules and setpoints.
        if datapoint.type != "actuator":
            raise Http404("Not found.")

        serializer = DatapointSetpointSerializer(datapoint)
        return Response(serializer.data)

    def update(self, request, *args, pk=None, **kwargs):
        """
        TODO
        """
        datapoint = get_object_or_404(Datapoint, pk=pk)

        # Only actuators have schedules and setpoints.
        if datapoint.type != "actuator":
            raise Http404("Not found.")
