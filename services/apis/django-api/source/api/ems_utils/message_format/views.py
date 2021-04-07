from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema, inline_serializer
from django_filters import rest_framework as filters

from ems_utils.timestamp import datetime_from_timestamp
from .models import DatapointTemplate
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
    unique_together_fields : list of strings,
        A list of field names of the datapoint_model that identify a
        single datapoint. These fields will be used for create and
        update operations to find the datapoint to which the data
        belongs to. This is id by default, but other combinations
        may be useful to provide portability of the metadata.
    """
    datapoint_model = None
    queryset = None
    serializer_class = None
    filter_backends = (filters.DjangoFilterBackend,)
    unique_together_fields = ("origin_id", )

    # Reuse the Docstring of Datapoint of the API schema.
    __doc__ = DatapointTemplate.__doc__

    def retrieve(self, request, dp_id):
        """
        This methods allows to retrieve the data of a single datapoint identified
        with the datapoint id.
        """
        datapoint = get_object_or_404(self.queryset, id=dp_id)
        serializer = self.serializer_class(datapoint)
        return Response(serializer.data)
    retrieve.__doc__ = __doc__ + "<br><br>" + retrieve.__doc__.strip()

    def list(self, request):
        """
        This methods allows to retrieve the data of multiple datapoints.
        """
        datapoints = self.queryset.all()
        datapoints = self.filter_queryset(datapoints)
        serializer = self.serializer_class(datapoints, many=True)
        return Response(serializer.data)
    list.__doc__ = __doc__ + "<br><br>" + list.__doc__.strip()


    def create(self, request):
        """
        This method allows to create a single datapoint which does not exist
        yet.
        """
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        # Not that the valid data will not contain many of the relevant
        # fields for quering a unique datatpoin.
        vd = serializer.validated_data

        q = {k: data[k] for k in self.unique_together_fields if k in data}
        if self.datapoint_model.objects.filter(**q).exists():
            raise ValidationError(
                "A datapoint with such field values exists already: %s" % q
            )

        datapoint = self.datapoint_model(**vd)
        datapoint.save()

        serializer = self.serializer_class(datapoint)
        # Return datapoint also with auto generated data like id.
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    create.__doc__ = __doc__ + "<br><br>" + create.__doc__.strip()

    def update(self, request):
        """
        This method allows to update a single datapoint which must exist
        already.
        """
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        q = {k: data[k] for k in self.unique_together_fields if k in data}
        datapoint = get_object_or_404(self.datapoint_model, **q)
        for field in vd:
            setattr(datapoint, field, vd[field])
        datapoint.save()

        serializer = self.serializer_class(datapoint)
        # Return datapoint also with auto generated data like id.
        return Response(serializer.data, status=status.HTTP_200_OK)
    update.__doc__ = __doc__ + "<br><br>" + update.__doc__.strip()

    def update_many(self, request):
        """
        This method allows to update a a bunch of datapoints which must exist
        already.
        """
        serializer = self.serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        errors = []
        datapoints = []
        for data in request.data:
            single_serializer = self.serializer_class(data=data)
            # This is redundant but we need it to compute the validated data
            # of this datapoint.
            single_serializer.is_valid()
            vd = single_serializer.validated_data
            q = {k: data[k] for k in self.unique_together_fields if k in data}
            dp_qs = self.datapoint_model.objects.filter(**q)
            if dp_qs.count() == 0:
                errors.append({
                    "datapoint": "No datapoint found matching query: %s." % q
                })
            elif dp_qs.count() > 1:
                errors.append({
                    "datapoint": "Multiple datapoints found matching query: %s." % q
                })
            else:
                errors.append({})
                datapoint = dp_qs[0]
                datapoints.append(datapoint)
                for field in vd:
                    setattr(datapoint, field, vd[field])

        # All or nothing, either all has gone through or we save nothing.
        if any(errors):
            raise ValidationError(errors)
        for datapoint in datapoints:
            datapoint.save()

        serializer = self.serializer_class(datapoints, many=True)
        # Return datapoint also with auto generated data like id.
        return Response(serializer.data, status=status.HTTP_200_OK)
    update_many.__doc__ = __doc__ + "<br><br>" + update_many.__doc__.strip()

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
