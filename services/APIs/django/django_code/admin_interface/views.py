from django.shortcuts import render
"""
TODO: Determine appropriate Views
"""
from django.views.generic.edit import CreateView, UpdateView, FormView
from django.views.generic.list import ListView
from django.shortcuts import get_object_or_404, reverse
from . import models, forms

"""
TODO: Everything below is just conceptual -> needs 'working code' or to be removed
"""


class ConnectorListView(ListView):
    template_name = "connector_list.html"
    queryset = models.Connector.objects.all().order_by("name")


class AddConnectorView(CreateView):
    template_name = "add_connector.html"
    # form_class = forms.ConnectorForm
    model = models.Connector
    #queryset = models.Connector.objects.order_by("name")
    fields = ['name']#"__all__"
    context_object_name = "Connectors"
    success_url = "/connectors"

    # def get_success_url(self, *args, **kwargs):
    #     return reverse("connector_list")


class EditConnectorView(UpdateView):
    template_name = "edit_connector.html"
    model = models.Connector
    # form_class = forms.ConnectorForm

    # def get_object(self, queryset=None):
    #     connector = get_object_or_404(models.Connector, pk=self.kwargs['pk'])
    #     return connector

# class AddDatapointView(ListView):
#     template_name = "add_datapoint.html"
#
#     def get_queryset(self):
#         """
#         Function to get all available datapoints connected to a specific connector
#         :return: list of available datapoints with new datapoints first
#         """
#         connector_name = self.kwargs['name']
#         connector = get_object_or_404(models.Connector, name=connector_name)
#         available_datapoints = models.ConnectorAvailableDatapoints.objects.filter(connector=connector_name)
#         return available_datapoints.order_by(active=False)











