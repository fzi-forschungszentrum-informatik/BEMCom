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

from api_main.models.connector import Connector
from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue
from api_main.models.datapoint import DatapointSchedule
from api_main.models.datapoint import DatapointSetpoint
from api_main.connector_mqtt_integration import ConnectorMQTTIntegration
from ems_utils.message_format.views import DatapointViewSetTemplate
from ems_utils.message_format.views import ViewSetWithDatapointFK

from ems_utils.message_format.serializers import DatapointValueSerializer
from ems_utils.message_format.serializers import DatapointScheduleSerializer
from ems_utils.message_format.serializers import DatapointSetpointSerializer
from ems_utils.message_format.serializers import PutMsgSummary
from .serializers import DatapointSerializer
from .filters import DatapointFilter, DatapointValueFilter
from .filters import DatapointSetpointFilter, DatapointScheduleFilter

from drf_spectacular.utils import extend_schema, inline_serializer, extend_schema_serializer

class DatapointViewSet(DatapointViewSetTemplate):
    __doc__ = DatapointViewSetTemplate.__doc__
    datapoint_model = Datapoint
    serializer_class = DatapointSerializer
    queryset = Datapoint.objects.all()
    filterset_class = DatapointFilter
    # Ids might change in between instances. The combinations of
    # these too fields in contrast should be unique even if the ID changed.
    unique_together_fields = ("connector", "key_in_connector")

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
    list.__doc__ = DatapointViewSetTemplate.list.__doc__

    def create(self, request):
        raise NotImplementedError(
            "It is not possible to manually create datapoints. Only "
            "connectors can define new Datapoints."
        )


    @extend_schema(
        request=serializer_class(Datapoint, many=True),
        ##
        ## This might help with the broken schema but will introduce some
        ## query parameters which do not make much sense here.
        ##
        # responses=serializer_class(Datapoint, many=True),
        parameters=[],
    )
    def update_many(self, request):
        """
        This method allows to update a a bunch of datapoints which must exist
        already.
        Method will try to match the input to the existing datapoints.
        This is done by searching for field connector_name and key_in_connector.
        """
        # Check first that the DB lookups are worth it. This also verifies
        # that we receive a list of objects as expected.
        serializer = self.serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        errors = []
        for data in request.data:
            if not "connector" in data:
                errors.append({})
                continue
            cn_qs = Connector.objects.filter(name=data["connector"])
            if cn_qs.count() == 0:
                errors.append({
                    "connector": (
                        "No Connector found matching name: %s."
                        % data["connector"]
                    )
                })
            # This should not be possible, but better save..
            elif cn_qs.count() > 1:
                errors.append({
                    "connector": (
                        "Multiple connectors found matching name: %s."
                        % data["connector"]
                    )
                })
            else:
                errors.append({})
                data["connector"] = cn_qs[0].id

        if any(errors):
            raise ValidationError(errors)
        else:
            return super().update_many(request)
    update_many.__doc__ = __doc__ + "<br><br>" + update_many.__doc__.strip()

class DatapointValueViewSet(ViewSetWithDatapointFK):
    __doc__ = DatapointValue.__doc__.strip()
    model = DatapointValue
    datapoint_model = Datapoint
    queryset = DatapointValue.objects.all()
    serializer_class = DatapointValueSerializer
    create_for_actuators_only = True
    filterset_class = DatapointValueFilter

    def create(self, request, dp_id):
        """
        This publishes the posted value message on the BEMCom internal
        message broker. The message will also be written to the API
        database, but only once the message has been received back from
        the message broker by the API.
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

    @extend_schema(
        request=serializer_class(DatapointValue, many=True),
        responses=PutMsgSummary,
        parameters=[],
    )
    def update_many(self, *args, **kwargs):
        return super().update_many(*args, **kwargs)

class DatapointScheduleViewSet(ViewSetWithDatapointFK):
    __doc__ = DatapointSchedule.__doc__.strip()
    model = DatapointSchedule
    datapoint_model = Datapoint
    queryset = DatapointSchedule.objects.all()
    serializer_class = DatapointScheduleSerializer
    create_for_actuators_only = True
    filterset_class = DatapointScheduleFilter

    def create(self, request, dp_id):
        """
        This publishes the posted schedule message on the BEMCom internal
        message broker. The message will also be written to the API
        database, but only once the message has been received back from
        the message broker by the API.
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
        print(validated_data)

        # Send the message to the MQTT broker.
        mqtt_topic = datapoint.get_mqtt_topics()["schedule"]
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.client.publish(
            topic=mqtt_topic,
            payload=json.dumps(validated_data),
            retain=True,
        )
        return Response(validated_data, status=status.HTTP_201_CREATED)

    # This lives here to make the schema correct.
    @extend_schema(
        request=serializer_class(DatapointSchedule, many=True),
        responses=PutMsgSummary,
        parameters=[],
    )
    def update_many(self, *args, **kwargs):
        return super().update_many(*args, **kwargs)

class DatapointSetpointViewSet(ViewSetWithDatapointFK):
    __doc__ = DatapointSetpoint.__doc__.strip()
    model = DatapointSetpoint
    datapoint_model = Datapoint
    queryset = DatapointSetpoint.objects.all()
    serializer_class = DatapointSetpointSerializer
    create_for_actuators_only = True
    filterset_class = DatapointSetpointFilter

    def create(self, request, dp_id):
        """
        This publishes the posted setpoint message on the BEMCom internal
        message broker. The message will also be written to the API
        database, but only once the message has been received back from
        the message broker by the API.
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

        # This lives here to make the schema correct.
        @extend_schema(
            request=serializer_class(DatapointSetpoint, many=True),
            responses=PutMsgSummary,
            parameters=[],
        )
        def update_many(self, *args, **kwargs):
            return super().update_many(*args, **kwargs)
