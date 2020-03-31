from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from main.models.datapoint import Datapoint
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
        Updates the fields last_value and last_value_timestamp.
        Inspred by:
        https://github.com/encode/django-rest-framework/blob/734c534dbb9c5758af335dba1fdbc2690388f076/rest_framework/mixins.py#L59
        .. but ignores the partial updates as we only allow put and not patch.
        """
        datapoint = get_object_or_404(Datapoint, pk=pk)
        serializer = DatapointValueSerializer(datapoint, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()


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


class DatapointSetpointViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)

        # Only actuators have schedules and setpoints.
        if datapoint.type != "actuator":
            raise Http404("Not found.")

        serializer = DatapointSetpointSerializer(datapoint)
        return Response(serializer.data)
