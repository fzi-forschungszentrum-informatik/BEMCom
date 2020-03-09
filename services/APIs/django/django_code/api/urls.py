from django.urls import include, path
from rest_framework import routers

from .views import DatapointViewSet
from .views import DatapointValueViewSet
from .views import DatapointScheduleViewSet
from .views import DatapointSetpointViewSet


urlpatterns = [
    path(
        "datapoints/",
        DatapointViewSet.as_view({
            "get": "list",
        })
    ),
    path(
        "datapoint/<pk>/",
        DatapointViewSet.as_view({
            "get": "retrieve",
        })
    ),
    path(
        "datapoint/<pk>/value/",
        DatapointValueViewSet.as_view({
            "get": "retrieve",
        })
    ),
    path(
        "datapoint/<pk>/schedule/",
        DatapointScheduleViewSet.as_view({
            "get": "retrieve",
        })
    ),
    path(
        "datapoint/<pk>/setpoint/",
        DatapointSetpointViewSet.as_view({
            "get": "retrieve",
        })
    ),
]
