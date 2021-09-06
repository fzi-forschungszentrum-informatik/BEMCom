import logging

from django.conf import settings
from django.db.utils import DataError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema, inline_serializer
from django_filters import rest_framework as filters
from timescale.db.models.querysets import TimescaleQuerySet

from ems_utils.timestamp import datetime_from_timestamp
from .models import DatapointTemplate
from .serializers import DatapointSerializer
from .serializers import DatapointValueSerializer
from .serializers import DatapointScheduleSerializer
from .serializers import DatapointSetpointSerializer
from .serializers import PutMsgSummary


logger = logging.getLogger(__name__)


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
        # Note that the valid data will not contain many of the relevant
        # fields for querying a unique datapoint.
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
        If True allows create operations for actuator datapoints.
        This makes sense as there are no schedules or setpoints for sensor
        datapoints by definition and value messages can only be posted to
        actuator datapoints too.
    filter_backends : List of filter backends.
        You should not need to change this. See also:
        https://www.django-rest-framework.org/api-guide/filtering/
    """
    model = None
    datapoint_model = None
    queryset = None
    serializer_class = None
    filter_backends = (filters.DjangoFilterBackend,)

    def list(self, request, dp_id):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        queryset = self.queryset.filter(datapoint=datapoint)
        queryset = self.filter_queryset(queryset)

        """
        Usually objects would be a normal Django queryset.
        However, if we applied time_bucket, it will be TimescaleQuerySet,
        that looks something like this:
        [
            {
                'bucket': datetime.datetime(2021, 7, 9, 13, 30, tzinfo=<UTC>),
                'value': 8990758.993710691
            },
            ...
        ]
        Note that the items are in fact dicts (contrary to object instances
        for normal querysets). Hence here some workaround that transforms
        the TimescaleQuerySet such that it works with the serializer.
        """
        if isinstance(queryset, TimescaleQuerySet):
            patched_queryset = []
            # Wrong values for the frequency parameter will only be raised
            # here as the iteration triggers the query to be executed.
            try:
                for bucket_item in queryset:
                    patched_queryset.append(
                        self.model(
                            datapoint=datapoint,
                            value=bucket_item["value"],
                            time=bucket_item["bucket"],

                        )
                    )
                queryset = patched_queryset
            except DataError as ex:
                logger.info("Caught exception: %s" % ex)
                raise ValidationError({
                    "frequency": [
                        "Encountered invalid value for frequency. "
                        "A valid value is something like this: '15 minutes' "
                        "Check the server logs if you are absolutely sure "
                        "that your value was valid.",
                    ],
                })

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, dp_id, timestamp=None):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        dt = datetime_from_timestamp(timestamp)
        object = get_object_or_404(
            self.queryset, datapoint=datapoint, time=dt
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
            datapoint=datapoint, time=dt
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
        """
        Places one message in the database. This is an upsert operation,
        i.e. the message will be created if no message exists for the distinct
        combination of datapoint and timestamp and updated otherwise.
        """
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        dt = datetime_from_timestamp(validated_data["timestamp"])
        object, created = self.model.objects.get_or_create(
            datapoint=datapoint, time=dt
        )
        for field in validated_data:
            if field == "timestamp":
                continue
            setattr(object, field, validated_data[field])
        object.save()
        if created:
            return Response(validated_data, status=status.HTTP_201_CREATED)
        else:
            return Response(validated_data, status=status.HTTP_200_OK)

    @extend_schema(
        responses=PutMsgSummary,
    )
    def update_many(self, request, dp_id):
        """
        Places one or more messages in the database. This is an upsert
        operation, i.e. the message will be created if no message exists for
        the distinct combination of datapoint and timestamp and updated
        otherwise.
        """
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)

        # Returns HTTP 400 (by exception) if sent data is not valid.
        serializer = self.serializer_class(
            datapoint, data=request.data, many=True
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Capture the corner case if someone adds an empty message.
        if not validated_data:
            put_msg_summary = PutMsgSummary().to_representation(
                instance={
                    "msgs_created": 0,
                    "msgs_updated": 0
                }
            )
            return Response(put_msg_summary, status=status.HTTP_200_OK)

        msgs = []
        for msg in validated_data:
            msg["datapoint"] = datapoint
            msg["time"] = datetime_from_timestamp(msg.pop("timestamp"))
            msgs.append(msg)

        msg_stats = self.model.bulk_update_or_create(
            model=self.model, msgs=msgs
        )

        put_msg_summary = PutMsgSummary().to_representation(
            instance={
                "msgs_created": msg_stats[0],
                "msgs_updated": msg_stats[1]
            }
        )
        return Response(put_msg_summary, status=status.HTTP_200_OK)

    def destroy(self, request, dp_id, timestamp=None):
        datapoint = get_object_or_404(self.datapoint_model, id=dp_id)
        dt = datetime_from_timestamp(timestamp)
        object = get_object_or_404(
            self.model, datapoint=datapoint, time=dt
        )
        object.delete()
        return Response(validated_data, status=status.HTTP_204_NO_CONTENT)

# XXX:
# Seems like we do not use these three subclasses any more as we need the
# serializer_class is required while actually defining the views to extend
# the schema documentation.
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
