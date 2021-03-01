from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema, inline_serializer
from django_filters import rest_framework as filters

from ems_utils.timestamp import datetime_from_timestamp
from .serializers import DatapointSerializer
from .serializers import DatapointValueSerializer
from .serializers import DatapointScheduleSerializer
from .serializers import DatapointSetpointSerializer


# TODO: Would be nice to have more details about the possible errors.
# TODO This also overrides the default 200/201 responses.
# Use with     @extend_schema(responses=common_resonses_all)
common_resonses_read_list = {
        401: NotAuthenticated,
        403: PermissionDenied,
    }
common_resonses_read_single = {
        401: NotAuthenticated,
        403: PermissionDenied,
        404: NotFound,
    }
common_resonses_all = {
        400: ValidationError,
        401: NotAuthenticated,
        403: PermissionDenied,
        404: NotFound,
    }

class DatapointViewSetTemplate(GenericViewSet):
    """
    Generic code to interact with datapoint objects.

    Subclass to use. Overload the attriubtes as required.

    Attriubtes:
    -----------
    datapoint_model : Django model
        The django model which we use to query for the datapoints.
    queryset : A valid queryset belonging to the Datapoint model.
        Should be something like Datapoint.objects.all()and must be
        provided to allow automatic schema generation and filtering.
    serializer_class : DRF serializier class.
        The serializer used to pack/unpack the objects into JSON.
    filter_backends : List of filter backends.
        You should not need to change this. See also:
        https://www.django-rest-framework.org/api-guide/filtering/
    """
    datapoint_model = None
    queryset = None
    serializer_class = DatapointSerializer
    filter_backends = (filters.DjangoFilterBackend,)

    def retrieve(self, request, dp_id):
        datapoint = get_object_or_404(self.queryset, id=dp_id)
        serializer = self.serializer_class(datapoint)
        return Response(serializer.data)

    def list(self, request):
        datapoints = self.queryset.all()
        serializer = self.serializer_class(datapoints, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Check if a datapoint with matching external_id exists already
        # and create one if not.
        q = {"origin_id": validated_data["origin_id"]}
        if not self.datapoint_model.objects.filter(**q).exists():
            datapoint = Datapoint(**validated_data)
        else:
            datapoint = Datapoint.objects.get(**q)
            for field in validated_data:
                setattr(datapoint, field, validated_data[field])
        datapoint.save()
        serializer = self.serializer_class(datapoint)
        # Return datapoint also with auto generated data like i.d.
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ViewSetWithDatapointFK(GenericViewSet):
    """
    Generic Code for ViewSets that have a Datapoint associated as ForeignKey.

    Subclass to use. You must overload `model`, `datapoint_model`, `queryset`
    and `serializer_class` to make the subclass work.

    Everything else is pretty standard, like desribed here:
    https://www.django-rest-framework.org/api-guide/viewsets/

    TODO: Add some tests here.

    Attributes:
    -----------
    model : Django model.
        The django model to use. Must have a foreign key field to
        the datapoint_model.
    datapoint_model : Django model
        The django model which we use to query for the datapoint to which
        the model belongs.
    queryset : A valid queryset belonging to the model.
        E.g. DatapointValue.objects.all(). Is used to allow automatic
        filter generation for the output.
    serializer_class : DRF serializier class.
        The serializer used to pack/unpack the objects into JSON.
    create_for_actuators_only : bool, default False
        If True allows create or update operations for actuator datapoints.
        This makes sense as there are no schedules or setpoints for sensor
        datapoints by definition.
    filter_backends : List of filter backends.
        You should not need to change this. See also:
        https://www.django-rest-framework.org/api-guide/filtering/
    """
    model = None
    datapoint_model = None
    queryset = None
    serializer_class = None
    create_for_actuators_only = False
    filter_backends = (filters.DjangoFilterBackend,)

    def list(self, request, dp_id):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        objects = self.queryset.filter(datapoint=datapoint)
        objects = self.filter_queryset(objects)
        serializer = self.serializer_class(objects, many=True)
        return Response(serializer.data)

    def retrieve(self, request, dp_id, timestamp=None):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        dt = datetime_from_timestamp(timestamp)
        object = get_object_or_404(
            self.queryset, datapoint=datapoint, timestamp=dt
        )
        serializer = self.serializer_class(object)
        return Response(serializer.data)

    def create(self, request, dp_id):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        dt = datetime_from_timestamp(validated_data["timestamp"])
        if self.create_for_actuators_only and datapoint.type != "actuator":
            raise ValidationError(
                "This message can only be written for an actuator datapoint."
            )
        object, created = self.model.objects.get_or_create(
            datapoint=datapoint, timestamp=dt
        )
        if not created:
            raise ValidationError({
                "timestamp": [
                    "Entry for this datapoint and timestamp exists already."
                ],
            })

        for field in validated_data:
            if field == "timestamp":
                continue
            setattr(object, field, validated_data[field])
        object.save()

        return Response(validated_data, status=status.HTTP_201_CREATED)

    def update(self, request, dp_id, timestamp=None):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data


        dt = datetime_from_timestamp(validated_data["timestamp"])
        if self.create_for_actuators_only and datapoint.type != "actuator":
            raise ValidationError(
                "This message can only be written for an actuator datapoint."
            )
        object, created = self.model.objects.get_or_create(
            datapoint=datapoint, timestamp=dt
        )
        for field in validated_data:
            if field == "timestamp":
                continue
            setattr(object, field, validated_data[field])
        object.save()
        return Response(validated_data, status=status.HTTP_201_CREATED)

    def destroy(self, request, dp_id, timestamp=None):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        dt = datetime_from_timestamp(timestamp)
        object = get_object_or_404(
            self.model, datapoint=datapoint, timestamp=dt
        )
        object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DatapointValueViewSetTemplate(ViewSetWithDatapointFK):
    """
    Generic code to interact with DatapointValue objects.

    Subclass to use. Overload the class attributes with appropriate values
    """
    serializer_class = DatapointValueSerializer


class DatapointScheduleViewSetTemplate(ViewSetWithDatapointFK):
    """
    Generic code to interact with DatapointSchedule objects.

    Subclass to use, ensure to overload `model` and `serializer_class`
    with appropriate values.
    """
    serializer_class = DatapointScheduleSerializer

class DatapointSetpointViewSetTemplate(ViewSetWithDatapointFK):
    """
    Generic code to interact with DatapointSetpoint objects.

    Subclass to use, ensure to overload `model` and `serializer_class`
    with appropriate values.
    """
    serializer_class = DatapointSetpointSerializer
