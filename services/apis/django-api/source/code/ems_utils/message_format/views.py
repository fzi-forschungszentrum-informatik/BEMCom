from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ViewSet

from ems_utils.timestamp import datetime_from_timestamp
from .serializers import DatapointSerializer
from .serializers import DatapointValueSerializer
from .serializers import DatapointScheduleSerializer
from .serializers import DatapointSetpointSerializer


class DatapointViewSetTemplate(ViewSet):
    """
    """
    datapoint_model = None
    serializer_class = DatapointSerializer

    def retrieve(self, request, dp_id):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        serializer = self.serializer_class(datapoint)
        return Response(serializer.data)

    def list(self, request):
        datapoints = self.datapoint_model.objects.all()
        serializer = self.serializer_class(datapoints, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        print("Validation Finished")

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

class ViewSetWithDatapointFK(ViewSet):
    """
    Generic Code for ViewSets that have a Datapoint associated as ForeignKey.

    All ViewSet actions required the datapoint id as additional arguement.
    We also support overloading the model of the Datapoint, as different
    implementations may have different meta data they want to store in
    the datapoint object.

    Everything else is pretty standard, like desribed here:
    https://www.django-rest-framework.org/api-guide/viewsets/

    TODO: Add some tests here.
    """
    datapoint_model = None

    def list(self, request, dp_id):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        objects = self.model.objects.filter(datapoint=datapoint)
        serializer = self.serializer_class(objects, many=True)
        return Response(serializer.data)

    def retrieve(self, request, dp_id, timestamp=None):
        datapoint = get_object_or_404(Datapoint, id=dp_id)
        dt = datetime_from_timestamp(timestamp)
        object = get_object_or_404(
            self.model.objects, datapoint=datapoint, timestamp=dt
        )
        serializer = self.serializer_class(object)
        return Response(serializer.data)

    def create(self, request, dp_id):
        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        dt = datetime_from_timestamp(validated_data["timestamp"])
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
        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        dt = datetime_from_timestamp(validated_data["timestamp"])
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
    """
    model = None
    serializer_class = DatapointValueSerializer


class DatapointScheduleViewSetTemplate(ViewSetWithDatapointFK):
    """
    """
    model = None
    serializer_class = DatapointScheduleSerializer

class DatapointSetpointViewSetTemplate(ViewSetWithDatapointFK):
    """
    """
    model = None
    serializer_class = DatapointSetpointSerializer
