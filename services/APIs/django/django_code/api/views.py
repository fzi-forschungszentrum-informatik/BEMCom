from rest_framework import viewsets

from .serializers import DatapointSerializer
from admin_interface.models.datapoint import Datapoint


class DatapointViewSet(viewsets.ModelViewSet):
    queryset = Datapoint.objects.filter(is_active=True)
    serializer_class = DatapointSerializer
