from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import DatapointViewSet, DatapointValueViewSet
from .views import DatapointScheduleViewSet, DatapointSetpointViewSet
from .views import PrometheusMetricsViewSet


urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema")),
    path(
        "metrics/",
        PrometheusMetricsViewSet.as_view({"get": "retrieve"}),
        name="metrics",
    ),
    path(
        "datapoint/",
        DatapointViewSet.as_view(
            {"get": "list", "post": "create", "put": "update_many"}
        ),
    ),
    path(
        "datapoint/<int:dp_id>/value/",
        DatapointValueViewSet.as_view(
            {"get": "list", "post": "create", "put": "update_many"}
        ),
    ),
    path(
        "datapoint/<int:dp_id>/value/<int:timestamp>/",
        DatapointValueViewSet.as_view({"delete": "destroy"}),
    ),
    path(
        "datapoint/<int:dp_id>/schedule/",
        DatapointScheduleViewSet.as_view(
            {"get": "list", "post": "create", "put": "update_many"}
        ),
    ),
    path(
        "datapoint/<int:dp_id>/schedule/<int:timestamp>/",
        DatapointScheduleViewSet.as_view({"delete": "destroy"}),
    ),
    path(
        "datapoint/<int:dp_id>/setpoint/",
        DatapointSetpointViewSet.as_view(
            {"get": "list", "post": "create", "put": "update_many"}
        ),
    ),
    path(
        "datapoint/<int:dp_id>/setpoint/<int:timestamp>/",
        DatapointSetpointViewSet.as_view({"delete": "destroy"}),
    ),
]
