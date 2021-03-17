import json
from django import forms, db
from django.contrib import admin
from django.utils.safestring import mark_safe

from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue
from api_main.models.datapoint import DatapointSetpoint
from api_main.models.datapoint import DatapointSchedule
from ems_utils.timestamp import datetime_to_pretty_str
from api_main.connector_mqtt_integration import ConnectorMQTTIntegration

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
        "is_active",
        "data_format",
        "short_name",
        "description",
        "unit",
        "example_value_truncated",
        "last_value_truncated",
        "last_value_timestamp_pretty",
    )
    list_display_links = (
        "key_in_connector",
    )
    list_editable = (
        "is_active",
        "data_format",
        "short_name",
        "description",
        "unit",
    )
    list_filter = (
        "type",
        "connector",
        "data_format",
        "is_active",
        ("short_name", admin.EmptyFieldListFilter)
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
        return datetime_to_pretty_str(ts)
    last_value_timestamp_pretty.admin_order_field = "last_value_timestamp"
    last_value_timestamp_pretty.short_description = "Last value timestamp"

    def last_setpoint_timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.last_setpoint_timestamp
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)
    last_setpoint_timestamp_pretty.admin_order_field = "last_setpoint_timestamp"
    last_setpoint_timestamp_pretty.short_description = "Last setpoint timestamp"

    def last_schedule_timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.last_schedule_timestamp
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)
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

    def example_value_truncated(self, obj):
        """
        Return a possible truncated value if the example value is very long.
        """
        value = obj.example_value
        truncation_length = 100
        if value is not None and len(value) >= truncation_length: 
            value = value[:truncation_length] + " [truncated]"
        return value
    example_value_truncated.admin_order_field = "example_value"
    example_value_truncated.short_description = "example_value"
    
    def last_value_truncated(self, obj):
        """
        Return a possible truncated value if the example value is very long.
        """
        value = obj.last_value
        truncation_length = 100
        if value is not None and len(value) >= truncation_length: 
            value = value[:truncation_length] + " [truncated]"
        return value
    last_value_truncated.admin_order_field = "last_value"
    last_value_truncated.short_description = "last_value"

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
                "short_name",
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
        """
        Flag a list of datapoints as active.

        The update method doesn't call the save method of each object, hence
        we need to manually trigger the update operations of
        ConnectorMQTTIntegration, i.e. that we subscribe to the topics of
        the activated datapoints and send a corrected datatpoint map to the
        connectors.

        TODO: This currently creates an updated datapoint map for call
              connectors, regardless if these are affected by the changes or
              not. This could be made more efficient.

        """
        queryset.update(is_active=True)
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.update_topics()
        cmi.update_subscriptions()
        cmi.create_and_send_datapoint_map()
    mark_active.short_description = "Mark datapoints as active"

    def mark_not_active(self, request, queryset):
        """
        Similar to mark_active above, but deactivates these datapoints.
        """
        queryset.update(is_active=False)
        cmi = ConnectorMQTTIntegration.get_instance()
        cmi.update_topics()
        cmi.update_subscriptions()
        cmi.create_and_send_datapoint_map()
    mark_not_active.short_description = "Mark datapoints as not active"

    def mark_data_format_as_generic_text(self, request, queryset):
        """
        Updates data_format for a list of datapoints at once.

        This has no effect on the configuration of services, especially
        Connectors. It is thus fine that the signals wont't fire and the
        save hooks won't be executed.
        """
        queryset.update(data_format="generic_text")
    mark_data_format_as_generic_text.short_description = (
        "Mark data_format of datapoints as generic_text"
    )

    def mark_data_format_as_discrete_text(self, request, queryset):
        """
        Updates data_format. Similar to mark_data_format_as_generic_text
        """
        queryset.update(data_format="discrete_text")
    mark_data_format_as_discrete_text.short_description = (
        "Mark data_format of datapoints as discrete_text"
    )

    def mark_data_format_as_generic_numeric(self, request, queryset):
        """
        Updates data_format. Similar to mark_data_format_as_generic_text
        """
        queryset.update(data_format="generic_numeric")
    mark_data_format_as_generic_numeric.short_description = (
        "Mark data_format of datapoints as generic_numeric"
    )

    def mark_data_format_as_discrete_numeric(self, request, queryset):
        """
        Updates data_format. Similar to mark_data_format_as_generic_text
        """
        queryset.update(data_format="discrete_numeric")
    mark_data_format_as_discrete_numeric.short_description = (
        "Mark data_format of datapoints as discrete_numeric"
    )

    def mark_data_format_as_continuous_numeric(self, request, queryset):
        """
        Updates data_format. Similar to mark_data_format_as_generic_text
        """
        queryset.update(data_format="continuous_numeric")
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

    def get_changelist_formset(self,request, **kwargs):
        """
        This ensures that when we edit a couple of datapoints in list
        mode we can save and ignore those datapoints that have not been
        touched. If we don't inject these methods the Admin will interpret
        the empty string in short name as string and raise a Validation
        Error, as two emtpy strings are not different (while two None
        values are). Hence we tell the admin to reset the empty strings
        to Nones, which makes the Admin think then that the fields have
        not changed and need not be saved.

        To do so we overload the clean method of the short_name field.
        However accessing this field is only possible after the formset
        has been intialized, which happens shortly before is_valid is
        called. Hence we use an extended is_valid method to inject the
        changed clean function in the short_name form object. See:
        https://github.com/django/django/blob/3.1/django/contrib/admin/options.py#L1758
        """
        formset = super().get_changelist_formset(request, **kwargs)

        def clean(short_name):
            if short_name == "":
                short_name = None
            return short_name

        def is_valid(self):
            for form in self.forms:
                form.fields["short_name"].clean = clean
            return super(type(self), self).is_valid()

        formset.is_valid = is_valid
        return formset


@admin.register(DatapointValue)
class DatapointValueAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "datapoint",
        "timestamp_pretty",
        "value",
    )
    list_filter = (
        "datapoint",
    )
    readonly_fields = (
        "id",
    )

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.timestamp
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)
    timestamp_pretty.admin_order_field = "timestamp"
    timestamp_pretty.short_description = "Timestamp"


@admin.register(DatapointSetpoint)
class DatapointSetpointAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "datapoint",
        "timestamp_pretty",
        "setpoint",
    )
    list_filter = (
        "datapoint",
    )
    readonly_fields = (
        "id",
    )

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.timestamp
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)
    timestamp_pretty.admin_order_field = "timestamp"
    timestamp_pretty.short_description = "Timestamp"

@admin.register(DatapointSchedule)
class DatapointScheduleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "datapoint",
        "timestamp_pretty",
        "schedule",
    )
    list_filter = (
        "datapoint",
    )
    readonly_fields = (
        "id",
    )

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.timestamp
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)
    timestamp_pretty.admin_order_field = "timestamp"
    timestamp_pretty.short_description = "Timestamp"
