import json
from django import forms, db
from django.contrib import admin
from django.utils.safestring import mark_safe

from main.models.datapoint import Datapoint
from main.utils import datetime_iso_format


@admin.register(Datapoint)
class DatapointAdmin(admin.ModelAdmin):
    """
    Admin model instance for Datapoints, that also displays fields of the
    addition models.

    This model does not allow adding datapoints manually, it doesn't make
    sense, all datapoints are created by the connectors.

    TODO: Verify that the fields are correct on save, i.e. that those fields
    that are required for a data_format are set with appropriate values, and
    that e.g. jsons fields are parsable.
    """
    list_display = (
        "connector",
        "key_in_connector",
        "type",
        "example_value",
        "last_value",
        "last_value_timestamp_pretty",
        "is_active",
        "data_format",
        "description"
    )
    list_display_links = (
        "key_in_connector",
    )
    list_editable = (
        "description",
        "data_format",
    )
    list_filter = (
        "type",
        "connector",
        "data_format",
        "is_active",
    )
    search_fields = (
        "key_in_connector",
        "example_value",
        "type",
    )
    readonly_fields = (
        "connector",
        "key_in_connector",
        "type",
        "example_value",
        "last_value",
        "last_value_timestamp_pretty",
        "last_setpoint_pretty",
        "last_setpoint_timestamp_pretty",
        "last_schedule_pretty",
        "last_schedule_timestamp_pretty",
    )

    def last_value_timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.last_value_timestamp
        if ts is None:
            return "-"
        return datetime_iso_format(ts, hide_microsec=True)
    last_value_timestamp_pretty.admin_order_field = "last_value_timestamp"
    last_value_timestamp_pretty.short_description = "Last value timestamp"

    def last_setpoint_timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.last_setpoint_timestamp
        if ts is None:
            return "-"
        return datetime_iso_format(ts, hide_microsec=True)
    last_setpoint_timestamp_pretty.admin_order_field = "last_setpoint_timestamp"
    last_setpoint_timestamp_pretty.short_description = "Last setpoint timestamp"

    def last_schedule_timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.last_schedule_timestamp
        if ts is None:
            return "-"
        return datetime_iso_format(ts, hide_microsec=True)
    last_schedule_timestamp_pretty.admin_order_field = "last_schedule_timestamp"
    last_schedule_timestamp_pretty.short_description = "Last schedule timestamp"

    def last_schedule_pretty(self, obj):
        """
        Pretty print json of schedule.
        """
        schedule = obj.last_schedule
        if schedule is None:
            return "-"
        try:
            schedule = json.dumps(json.loads(schedule), indent=4)
            schedule = mark_safe("<pre>" + schedule + "</pre>")

        except Exception:
            pass
        return schedule
    last_schedule_pretty.short_description = "Last schedule"

    def last_setpoint_pretty(self, obj):
        """
        Pretty print json of setpoint.
        """
        setpoint = obj.last_setpoint
        if setpoint is None:
            return "-"

        try:
            setpoint = json.dumps(json.loads(setpoint), indent=4)
            setpoint = mark_safe("<pre>" + setpoint + "</pre>")

        except Exception:
            pass
        return setpoint
    last_setpoint_pretty.short_description = "Last setpoint"

    def get_fieldsets(self, request, obj=None):
        """
        Dynamically add fields that are only relevant for specific values
        of data_format or additional fields for actuators.
        """
        generic_metadata_fields = [
                "connector",
                "key_in_connector",
                "type",
                "example_value",
                "is_active",
                "data_format",
                "description",
        ]

        data_format_specific_fields = []
        if "_numeric" in obj.data_format:
            data_format_specific_fields.append("unit")
        if "discrete_" in obj.data_format:
            data_format_specific_fields.append("allowed_values")
        if "continuous_numeric" in obj.data_format:
            data_format_specific_fields.append("min_value")
            data_format_specific_fields.append("max_value")

        last_datapoint_msg_fields = [
            "last_value",
            "last_value_timestamp_pretty",
        ]
        if obj.type == "actuator":
            last_datapoint_msg_fields.append("last_setpoint_pretty")
            last_datapoint_msg_fields.append("last_setpoint_timestamp_pretty")
            last_datapoint_msg_fields.append("last_schedule_pretty")
            last_datapoint_msg_fields.append("last_schedule_timestamp_pretty")

        fieldsets = (
            (
                "GENERIC METADATA",
                {
                    "fields": generic_metadata_fields
                }
            ),
            (
                "DATA FORMAT SPECIFIC METADATA",
                {
                    "fields": data_format_specific_fields
                }
            ),
            (
                "LAST DATAPOINT MESSAGES",
                {
                    "fields": last_datapoint_msg_fields
                }
            ),
        )
        return fieldsets

    # Display wider version of normal TextInput for all text fields, as
    # default forms look ugly.
    formfield_overrides = {
        db.models.TextField: {'widget': forms.TextInput(attrs={'size': '60'})},
    }
    """
    Define list view actions below.

    Actions changing the data format should not call queryset.update, as this
    will not call the Datapoints save() method, and hence the Datapoint
    Addition models will not be updated.
    TODO: This is outdated.
    """
    actions = (
        "mark_active",
        "mark_not_active",
        "mark_data_format_as_generic_text",
        "mark_data_format_as_discrete_text",
        "mark_data_format_as_generic_numeric",
        "mark_data_format_as_discrete_numeric",
        "mark_data_format_as_continuous_numeric",
    )

    def mark_active(self, request, queryset):
        for datapoint in queryset:
            datapoint.is_active = True
            datapoint.save()
    mark_active.short_description = "Mark datapoints as active"

    def mark_not_active(self, request, queryset):
        for datapoint in queryset:
            datapoint.is_active = False
            datapoint.save()
    mark_not_active.short_description = "Mark datapoints as not active"

    def mark_data_format_as_generic_text(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "generic_text"
            datapoint.save()
    mark_data_format_as_generic_text.short_description = (
        "Mark data_format of datapoints as generic_text"
    )

    def mark_data_format_as_discrete_text(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "discrete_text"
            datapoint.save()
    mark_data_format_as_discrete_text.short_description = (
        "Mark data_format of datapoints as discrete_text"
    )

    def mark_data_format_as_generic_numeric(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "generic_numeric"
            datapoint.save()
    mark_data_format_as_generic_numeric.short_description = (
        "Mark data_format of datapoints as generic_numeric"
    )

    def mark_data_format_as_discrete_numeric(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "discrete_numeric"
            datapoint.save()
    mark_data_format_as_discrete_numeric.short_description = (
        "Mark data_format of datapoints as discrete_numeric"
    )

    def mark_data_format_as_continuous_numeric(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "continuous_numeric"
            datapoint.save()
    mark_data_format_as_continuous_numeric.short_description = (
        "Mark data_format of datapoints as continuous_numeric"
    )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False
