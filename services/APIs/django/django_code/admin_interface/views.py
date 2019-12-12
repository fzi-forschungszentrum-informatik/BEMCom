from django.shortcuts import render
"""
TODO: Determine appropriate Views
"""
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.shortcuts import get_object_or_404, reverse, render
from django.core import serializers
from . import models, forms

"""
TODO: Combine add and edit views -> single form and template
"""


class ConnectorListView(ListView):
    template_name = "connector_list.html"
    queryset = models.Connector.objects.all().order_by("-date_created")


class AddConnectorView(CreateView):
    template_name = "add_connector.html"
    # form_class = forms.ConnectorForm
    model = models.Connector
    #queryset = models.Connector.objects.order_by("name")
    fields = ['name'] #"__all__"
    context_object_name = "Connectors"
    #success_url = "/connectors"

    # def get_success_url(self, *args, **kwargs):
    #     return reverse("connector_list")

    def get_object(self):
        object_id = self.kwargs.get("id")
        return get_object_or_404(models.Connector, id=object_id)


class EditConnectorView(UpdateView):
    template_name = "edit_connector.html"
    queryset = models.Connector.objects.all()
    fields = "__all__"
    # form_class = forms.ConnectorForm

    def get_object(self):
        object_id = self.kwargs.get("id")
        return get_object_or_404(models.Connector, id=object_id)

    def get_success_url(self, *args, **kwargs):
        return reverse("connector_list")


class DeleteConnectorView(DeleteView):
    template_name = "delete_connector.html"

    def get_object(self):
        object_id = self.kwargs.get("id")
        return get_object_or_404(models.Connector, id=object_id)

    def get_success_url(self, *args, **kwargs):
        return reverse("connector_list")


class ConnectorDetailView(DetailView):
    template_name = "connector_detail.html"
    model = models.Connector
    connector_attr = model.__dict__
    #all_connector_data = serializers.serialize("python", models.Connector.objects.all())

    def get_object(self):
        object_name = self.kwargs.get("name")
        return get_object_or_404(models.Connector, name=object_name)
    #
    # def show(self, request):
    #     connector = models.Connector.objects.filter(id=self.id).values()[0]
    #     print(connector)
    #     return render_to(request,'connector_detail.html', {'object': connector}, context_instance=RequestContext(request))



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











