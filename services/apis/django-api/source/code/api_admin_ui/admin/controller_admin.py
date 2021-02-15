from django.contrib import admin
from django import forms, db

from api_main.models.controller import Controller, ControlledDatapoint


@admin.register(Controller)
class ControllerAdmin(admin.ModelAdmin):
    """
    Simple Admin instance for Controllers.
    """
    list_display = (
        "id",
        "name",
        "mqtt_topic_controlled_datapoints"
    )
    list_editable = list_display[1:]
    list_filter = list_display[1:]
    search_fields = list_display[1:]

    # Display wider version of normal TextInput for all text fields, as
    # default forms look ugly.
    formfield_overrides = {
        db.models.TextField: {'widget': forms.TextInput(attrs={'size': '60'})},
    }


@admin.register(ControlledDatapoint)
class ControlledDatapoint(admin.ModelAdmin):
    """
    Same, same. A simple Admin Instance too.

    TODO: The autocomplete fields currently list the datapoint key_in_connector
          and a trailing connector name. The connector name cannot be used
          in the autocomplete which is counter intuitive. Also it should be
          changed thus that only sensor/actuator datapoints can be selected.
          The following function apparently needs to be overwritten to
          implement the desired behaviour:
          https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.get_search_results
    """
    list_display = (
        "id",
        "controller",
        "sensor_datapoint",
        "actuator_datapoint",
        "is_active",
    )
    list_editable = list_display[1:]
    list_filter = [
        "is_active",
        "controller",
    ]
    search_fields = [
        "sensor_datapoint",
        "actuator_datapoint",
    ]
    autocomplete_fields = [
        "sensor_datapoint",
        "actuator_datapoint",
    ]
