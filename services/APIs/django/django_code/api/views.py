from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from admin_interface.models.datapoint import Datapoint
from .serializers import DatapointSerializer
from .serializers import DatapointValueSerializer
from .serializers import DatapointScheduleSerializer
from .serializers import DatapointSetpointSerializer


class DatapointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Datapoint.objects.filter(is_active=True)
    serializer_class = DatapointSerializer

    @action(methods=["get", "put"], detail=True)
    def value(self, request, pk=None):
        datapoint = self.get_object()
        addition_object = datapoint.get_addition_object()
        return Response({"last_value": addition_object.last_value})


class DatapointValueViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)
        serializer = DatapointValueSerializer(datapoint)
        return Response(serializer.data)


class DatapointScheduleViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)
        serializer = DatapointScheduleSerializer(
            datapoint,
            context={'request': request}
        )
        return Response(serializer.data)


class DatapointSetpointViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        datapoint = get_object_or_404(Datapoint, pk=pk)
        serializer = DatapointSetpointSerializer(datapoint)
        return Response(serializer.data)
