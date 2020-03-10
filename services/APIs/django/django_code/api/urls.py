from django.urls import include, path
from rest_framework import routers

from .views import DatapointViewSet
from .views import DatapointValueViewSet
from .views import DatapointScheduleViewSet
from .views import DatapointSetpointViewSet

# Calling the default router is necessary for generate the api-root view.
# However we manage our routes manually below, hence we remove the
# datapoint detail urls from the router as they would generate an alternative
# route/view under /datapoints/<id> which we don't want.
router = routers.DefaultRouter()
router.register(r'datapoints', DatapointViewSet)
selected_urls = []
for url in router.urls:
    if "datapoints/(?P" in url.pattern.describe():
        continue
    selected_urls.append(url)

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
    path('', include(selected_urls)),
]

