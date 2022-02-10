from django.urls import path
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import DatapointViewSet
from .views import DatapointValueViewSet
from .views import DatapointScheduleViewSet
from .views import DatapointSetpointViewSet
from .views import DatapointLastValueViewSet
from .views import DatapointLastScheduleViewSet
from .views import DatapointLastSetpointViewSet
from .views import PrometheusMetricsViewSet

# Which endpoints are provided depends on these two setting flags (see Readme):
ACTIVATE_CONTROL_EXTENSION = settings.ACTIVATE_CONTROL_EXTENSION
ACTIVATE_HISTORY_EXTENSION = settings.ACTIVATE_HISTORY_EXTENSION

# These endpoints don't depend on the settings above. They are always provided.
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
]

# No history and no control, hence there are only value messages and we can
# read and write only the most recent ones.
if not ACTIVATE_CONTROL_EXTENSION and not ACTIVATE_HISTORY_EXTENSION:
    urlpatterns.extend(
        [
            path(
                "datapoint/last_value/",
                DatapointLastValueViewSet.as_view({"get": "list"}),
            ),
            path(
                "datapoint/<int:dp_id>/value/",
                DatapointValueViewSet.as_view({"post": "create"}),
            ),
        ]
    )

# Schedules and Setpoints are used, but only read and write operations of the
# last messages are allowed.
elif ACTIVATE_CONTROL_EXTENSION and not ACTIVATE_HISTORY_EXTENSION:
    urlpatterns.extend(
        [
            path(
                "datapoint/last_value/",
                DatapointLastValueViewSet.as_view({"get": "list"}),
            ),
            path(
                "datapoint/last_schedule/",
                DatapointLastScheduleViewSet.as_view({"get": "list"}),
            ),
            path(
                "datapoint/last_setpoint/",
                DatapointLastSetpointViewSet.as_view({"get": "list"}),
            ),
            path(
                "datapoint/<int:dp_id>/value/",
                DatapointValueViewSet.as_view({"post": "create"}),
            ),
            path(
                "datapoint/<int:dp_id>/schedule/",
                DatapointScheduleViewSet.as_view({"post": "create"}),
            ),
            path(
                "datapoint/<int:dp_id>/setpoint/",
                DatapointSetpointViewSet.as_view({"post": "create"}),
            ),
        ]
    )

# History is enabled, but only for value messages.
elif not ACTIVATE_CONTROL_EXTENSION and ACTIVATE_HISTORY_EXTENSION:
    urlpatterns.extend(
        [
            path(
                "datapoint/last_value/",
                DatapointLastValueViewSet.as_view({"get": "list"}),
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
        ]
    )

# Full API available.
elif ACTIVATE_CONTROL_EXTENSION and ACTIVATE_HISTORY_EXTENSION:
    urlpatterns.extend(
        [
            path(
                "datapoint/last_value/",
                DatapointLastValueViewSet.as_view({"get": "list"}),
            ),
            path(
                "datapoint/last_schedule/",
                DatapointLastScheduleViewSet.as_view({"get": "list"}),
            ),
            path(
                "datapoint/last_setpoint/",
                DatapointLastSetpointViewSet.as_view({"get": "list"}),
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
    )
