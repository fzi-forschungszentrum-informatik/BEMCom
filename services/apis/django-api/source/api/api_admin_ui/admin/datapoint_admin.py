from django import forms, db
from django.contrib import admin

from api_main.models.datapoint import Datapoint
from api_main.models.datapoint import DatapointValue, DatapointLastValue
from api_main.models.datapoint import DatapointSetpoint, DatapointLastSetpoint
from api_main.models.datapoint import DatapointSchedule, DatapointLastSchedule
from ems_utils.timestamp import datetime_to_pretty_str
from api_main.mqtt_integration import ApiMqttIntegration
from .connector_admin import AdminWithoutListsOnDelete


class DatapointLastValueInline(admin.TabularInline):
    model = DatapointLastValue
    verbose_name_plural = "Datapoint Last Value"
    fields = ("value", "time")


class DatapointLastScheduleInline(admin.TabularInline):
    model = DatapointLastSchedule
    verbose_name_plural = "Datapoint Last Schedule"
    fields = ("schedule", "time")


class DatapointLastSetpointInline(admin.TabularInline):
    model = DatapointLastSetpoint
    verbose_name_plural = "Datapoint Last Setpoint"
    fields = ("setpoint", "time")


@admin.register(Datapoint)
class DatapointAdmin(AdminWithoutListsOnDelete):
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
        "id",
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
    list_display_links = ("id",)
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
        ("short_name", admin.EmptyFieldListFilter),
    )
    search_fields = (
        "key_in_connector",
        "short_name",
        "description",
        "example_value",
    )
    readonly_fields = (
        "id",
        "connector",
        "key_in_connector",
        "type",
        "example_value",
        "last_value_truncated",
        "last_value_timestamp_pretty",
    )
    inlines = [
        DatapointLastValueInline,
    ]

    def last_value_timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        if hasattr(obj, "last_value_message"):
            ts = obj.last_value_message.time
            if ts is not None:
                return datetime_to_pretty_str(ts)
        return "-"

    last_value_timestamp_pretty.admin_order_field = "last_value_timestamp"
    last_value_timestamp_pretty.short_description = "Last value timestamp"

    def example_value_truncated(self, obj):
        """
        Return a possible truncated value if the example value is very long.
        """
        value = str(obj.example_value)
        truncation_length = 100
        if len(value) >= truncation_length:
            value = value[:truncation_length] + " [truncated]"
        return value

    example_value_truncated.admin_order_field = "example_value"
    example_value_truncated.short_description = "example_value"

    def last_value_truncated(self, obj):
        """
        Return a possible truncated value if the last value is very long.
        """
        value = "-"
        if hasattr(obj, "last_value_message"):
            if obj.last_value_message.value is not None:
                value = str(obj.last_value_message.value)

        truncation_length = 100
        if len(value) >= truncation_length:
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
            "id",
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

        if obj.type == "actuator":
            self.inlines.append(DatapointLastScheduleInline)
            self.inlines.append(DatapointLastSetpointInline)

        fieldsets = (
            ("GENERIC METADATA", {"fields": generic_metadata_fields}),
            (
                "DATA FORMAT SPECIFIC METADATA",
                {"fields": data_format_specific_fields},
            ),
        )
        return fieldsets

    # Display wider version of normal TextInput for all text fields, as
    # default forms look ugly.
    formfield_overrides = {
        db.models.TextField: {"widget": forms.TextInput(attrs={"size": "60"})}
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
        ApiMqttIntegration, i.e. that we subscribe to the topics of
        the activated datapoints and send a corrected datatpoint map to the
        connectors.

        TODO: This currently creates an updated datapoint map for call
              connectors, regardless if these are affected by the changes or
              not. This could be made more efficient.

        """
        queryset.update(is_active=True)
        ami = ApiMqttIntegration.get_instance()
        ami.trigger_update_topics_and_subscriptions()
        ami.trigger_create_and_send_datapoint_map()

    mark_active.short_description = "Mark datapoints as active"

    def mark_not_active(self, request, queryset):
        """
        Similar to mark_active above, but deactivates these datapoints.
        """
        queryset.update(is_active=False)
        ami = ApiMqttIntegration.get_instance()
        ami.trigger_update_topics_and_subscriptions()
        ami.trigger_create_and_send_datapoint_map()

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

    def get_changelist_formset(self, request, **kwargs):
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
class DatapointValueAdmin(AdminWithoutListsOnDelete):

    list_display = ("id", "datapoint", "timestamp_pretty", "value")
    list_filter = ("datapoint",)
    # This is just to order the fields in the object detail page
    fields = ("id", "datapoint", "value", "time")
    readonly_fields = ("id", "datapoint")
    exclude = ("_value_float", "_value_bool")

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.time
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)

    timestamp_pretty.admin_order_field = "time"
    timestamp_pretty.short_description = "Timestamp"

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False


@admin.register(DatapointSetpoint)
class DatapointSetpointAdmin(AdminWithoutListsOnDelete):

    list_display = ("id", "datapoint", "timestamp_pretty", "setpoint")
    list_filter = ("datapoint",)
    # This is just to order the fields in the object detail page
    fields = ("id", "datapoint", "setpoint", "time")
    readonly_fields = ("id", "datapoint")

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.time
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)

    timestamp_pretty.admin_order_field = "time"
    timestamp_pretty.short_description = "Timestamp"

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False


@admin.register(DatapointSchedule)
class DatapointScheduleAdmin(AdminWithoutListsOnDelete):

    list_display = ("id", "datapoint", "timestamp_pretty", "schedule")
    list_filter = ("datapoint",)
    fields = ("id", "datapoint", "setpoint", "time")
    readonly_fields = ("id", "datapoint")

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        ts = obj.time
        if ts is None:
            return "-"
        return datetime_to_pretty_str(ts)

    timestamp_pretty.admin_order_field = "time"
    timestamp_pretty.short_description = "Timestamp"

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False
