"""
Quickly create the necessary viewsets for the REST API, by adapting the
generic versions from ems_utils.model_format.

The __doc__ objects are overloaded to extract the right docs from
the generic implementation in ems_utils to display in the API schema.
"""
import json

import prometheus_client
from rest_framework import status, renderers
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404
from django.utils.encoding import smart_str

from api_main.models.connector import Connector
from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue
from api_main.models.datapoint import DatapointSchedule
from api_main.models.datapoint import DatapointSetpoint
from api_main.mqtt_integration import ApiMqttIntegration
from ems_utils.message_format.views import DatapointViewSetTemplate
from ems_utils.message_format.views import ViewSetWithDatapointFK

from ems_utils.message_format.serializers import DatapointValueSerializer
from ems_utils.message_format.serializers import DatapointScheduleSerializer
from ems_utils.message_format.serializers import DatapointSetpointSerializer
from ems_utils.message_format.serializers import PutMsgSummary
from .serializers import DatapointSerializer
from .filters import DatapointFilter, DatapointValueFilter
from .filters import DatapointSetpointFilter, DatapointScheduleFilter
from .models import Metric

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

    # This extends the generic version from ems_utils such that connectors
    # are generated automatically too.
    @extend_schema(
        request=serializer_class(Datapoint, many=True),
        ##
        ## This might help with the broken schema but will introduce some
        ## query parameters which do not make much sense here.
        ##
        #responses=serializer_class(Datapoint, many=True),
        parameters=[],
    )
    def create(self, request):
        """
        This method allows to create a single datapoint which does not exist
        yet.

        Please note: This endpoint is only used for replaying backups.
        Usually, datapoints are created by connector messages. Hence
        this adding datapoints this way may lead to orphaned datapoints
        which are unknown to connectors and will receive no data.
        """
        serializer = self.serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        errors = []
        new_datapoints = []
        new_connectors = []
        for data in vd:
            cn_qs = Connector.objects.filter(name=data["connector"]["name"])
            if cn_qs.count() == 0:
                connector = Connector(name=data["connector"]["name"])
                # Need to save here for next iteration.
                connector.save()
                data["connector"] = connector
                new_connectors.append(connector)
            if cn_qs.count() == 1:
                data["connector"] = cn_qs[0]
            # This should not be possible, but better save..
            else:
                errors.append({
                    "connector": (
                        "Multiple connectors found matching name: %s."
                        % data["connector"]
                    )
                })
                continue

            q = {k: data[k] for k in self.unique_together_fields if k in data}
            dp_qs = self.datapoint_model.objects.filter(**q)
            if dp_qs.count() == 1:
                errors.append({
                    "datapoint": "Datapoint exists already: %s." % q
                })
                continue
            elif dp_qs.count() > 1:
                errors.append({
                    "datapoint": "Multiple datapoints found matching query: %s." % q
                })
                continue
            else:
                # Create new datapoint as intended
                datapoint = Datapoint(**data)
                new_datapoints.append(datapoint)

                # Need to save here for next iteration.
                datapoint.save()

                # Keeps errors and input data lists aligned.
                errors.append({})


        # All or nothing, either all has gone through or we delete everything.
        # TODO Also create test for the nothing case.
        if any(errors):
            raise ValidationError(errors)

            for datapoint in new_datapoints:
                datapoint.delete()
            for connector in new_connectors:
                connector.delete()

        # Return datapoint also with auto generated data like id.
        serializer = self.serializer_class(new_datapoints, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    create.__doc__ = __doc__ + "<br><br>" + create.__doc__.strip()


    @extend_schema(
        request=serializer_class(Datapoint, many=True),
        ##
        ## This might help with the broken schema but will introduce some
        ## query parameters which do not make much sense here.
        ##
        #responses=serializer_class(Datapoint, many=True),
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
        vd = serializer.validated_data

        # The main point here is the ensure that no datapoints are updated
        # for which no connecetor exsits yet.
        errors = []
        datapoints = []
        for data in vd:
            cn_qs = Connector.objects.filter(name=data["connector"]["name"])
            if cn_qs.count() == 0:
                errors.append({
                    "connector": (
                        "No Connector found matching name: %s."
                        % data["connector"]
                    )
                })
                continue
            # This should not be possible, but better save..
            elif cn_qs.count() > 1:
                errors.append({
                    "connector": (
                        "Multiple connectors found matching name: %s."
                        % data["connector"]
                    )
                })
                continue
            else:
                data["connector"] = cn_qs[0]

            q = {k: data[k] for k in self.unique_together_fields if k in data}
            dp_qs = self.datapoint_model.objects.filter(**q)
            if dp_qs.count() == 0:
                errors.append({
                    "datapoint": "No datapoint found matching query: %s." % q
                })
                continue
            elif dp_qs.count() > 1:
                errors.append({
                    "datapoint": "Multiple datapoints found matching query: %s." % q
                })
                continue
            else:
                errors.append({})
                datapoint = dp_qs[0]
                datapoints.append(datapoint)
                for field in data:
                    setattr(datapoint, field, data[field])
                # Now save required here. The worst case szenario is that
                # duplicate entries will be overwritten.

        # All or nothing, either all has gone through or we save nothing.
        # TODO Also create test for the nothing case.
        if any(errors):
            raise ValidationError(errors)
        for datapoint in datapoints:
            datapoint.save()

        # Return datapoint also with auto generated data like id.
        serializer = self.serializer_class(datapoints, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    update_many.__doc__ = __doc__ + "<br><br>" + update_many.__doc__.strip()


class DatapointValueViewSet(ViewSetWithDatapointFK):
    __doc__ = DatapointValue.__doc__.strip()
    model = DatapointValue
    datapoint_model = Datapoint
    queryset = DatapointValue.timescale.all()
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
        ami = ApiMqttIntegration.get_instance()
        ami.client.publish(
            topic=mqtt_topic,
            payload=json.dumps(validated_data)
        )
        return Response(validated_data, status=status.HTTP_201_CREATED)

    # This lives here to make the schema correct.
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
        ami = ApiMqttIntegration.get_instance()
        ami.client.publish(
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
        ami = ApiMqttIntegration.get_instance()
        ami.client.publish(
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


class PlainTextRenderer(renderers.BaseRenderer):
    """
    As seen here:
    https://www.django-rest-framework.org/api-guide/renderers/#example
    """
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        return smart_str(data, encoding=self.charset)


class PrometheusMetricsViewSet(GenericViewSet):
    """
    Exposes Prometheus metrics.
    """

    renderer_classes = [PlainTextRenderer]
    # This is required for automatic permission checking.
    queryset = Metric.objects.all()

    def retrieve(self, request):
        metrics = prometheus_client.generate_latest()
        return Response(metrics)
