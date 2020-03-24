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