from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import DatapointViewSet, DatapointValueViewSet
from .views import DatapointScheduleViewSet, DatapointSetpointViewSet


urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema")),
    path(
        "datapoint/<int:dp_id>/",
        DatapointViewSet.as_view({
            "get": "retrieve",
        })
    ),
    path(
        "datapoint/<int:dp_id>/value/",
        DatapointValueViewSet.as_view({
            "get": "list",
            "post": "create",
        })
    ),
    path(
        "datapoint/<int:dp_id>/value/<int:timestamp>/",
        DatapointValueViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "delete": "destroy",
        })
    ),
    path(
        "datapoint/<int:dp_id>/schedule/",
        DatapointScheduleViewSet.as_view({
            "get": "list",
            "post": "create",
        })
    ),
    path(
        "datapoint/<int:dp_id>/schedule/<int:timestamp>/",
        DatapointScheduleViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "delete": "destroy",
        })
    ),
    path(
        "datapoint/<int:dp_id>/setpoint/",
        DatapointSetpointViewSet.as_view({
            "get": "list",
            "post": "create",
        })
    ),
    path(
        "datapoint/<int:dp_id>/setpoint/<int:timestamp>/",
        DatapointSetpointViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "delete": "destroy",
        })
    ),
]
