from datetime import datetime, timezone

from django import forms, db
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType

from admin_interface.models import Connector, Datapoint
from admin_interface.models import ConnectorHeartbeat, ConnectorLogEntry
from admin_interface.utils import datetime_iso_format


class UsedDatapointsInline(admin.TabularInline):
    """
    @david: only necessary when available datapoints should be displayed in connector views
    """
    model = Datapoint
    fields = ("key_in_connector", "use_as", "type", "example_value", )
    readonly_fields = fields
    ordering = ('key_in_connector', )
    verbose_name_plural = "Used datapoints of connector"
    can_delete = False
    classes = ['collapse']

    def has_add_permission(self, request):
        """
        Remove the add another button at the bottom of the inline, makes no
        sense to add another datapoint.
        """
        return False

    def get_queryset(self, request):
        """
        Limited query set for dev
        """
        queryset = super(UsedDatapointsInline, self).get_queryset(request)
        return queryset.exclude(use_as='not used')


class ConnectorLogEntryInline(admin.TabularInline):
    """
    @david: relevant
    """
    model = ConnectorLogEntry
    verbose_name_plural = "Last 10 log entries"
    fields = ('timestamp', 'msg', 'emitter', )
    readonly_fields = fields
    ordering = ('timestamp', )
    can_delete = False
    classes = ('collapse', )

    def has_add_permission(self, request, obj):
        return False

    def get_queryset(self, request):
        """
        Note: Getting query set in descending order (by timestamp) and slicing it throws error ("filtering is
                not possible after slicing"), because the custom (returned) query set is filtered again for the
                current connector.
                Hence this workaround: First get IDs of last ten entries, then filter all entries based on these IDs.
                -> Returned query set can now be filtered again for the current connector :)
        """
        all_entries = super(ConnectorLogEntryInline, self).get_queryset(request)
        ids_of_last_ten_entries = all_entries.order_by('-timestamp').values('id')[:10]
        last_ten_entries = ConnectorLogEntry.objects.filter(id__in=ids_of_last_ten_entries)
        return last_ten_entries


@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):

    list_display = ('name', 'added', 'last_changed', 'alive', )
    ordering = ('-name', )
    search_fields = ('name', )


    readonly_fields = (
        'added',
        'last_changed',
        'last_heartbeat',
        'next_heartbeat',
        'alive',
        'num_available_datapoints',
        'num_used_datapoints',
        'mqtt_topic_logs',
        'mqtt_topic_heartbeat',
        'mqtt_topic_available_datapoints',
        'mqtt_topic_datapoint_map',
        'mqtt_topic_raw_message_to_db',
        'mqtt_topic_raw_message_reprocess',
        'mqtt_topic_datapoint_message_wildcard',
    )

    # Display wider version of normal TextInput for all text fields, as
    # default forms look ugly.
    formfield_overrides = {
        db.models.TextField: {'widget': forms.TextInput(attrs={'size':'60'})},
    }

    # Adapted change form template to display "Go to available datapoints"
    # button
    change_form_template = '../templates/connector_change_form.html'

    @staticmethod
    def num_available_datapoints(obj):
        """
        Numer of available datapoints.

        That is all datapoints incl. the "not used" ones.
        """
        dpo = Datapoint.objects
        return dpo.filter(connector=obj.id).count()
    num_available_datapoints.short_description = (
        "Number of available datapoints"
    )

    @staticmethod
    def num_used_datapoints(obj):
         """
         Numer of used datapoints.
         """
         dpo = Datapoint.objects
         return dpo.filter(connector=obj.id).exclude(use_as="not used").count()
    num_used_datapoints.short_description = "Number of used datapoints"

    @staticmethod
    def last_heartbeat(obj, pretty=True):
        """
        :param obj: current connector object
        :param pretty: If true (default), timestamp will be returned like this: "yyyy-mm-dd hh:mm:ss (UTC)"
                        If false, format is "yyyy-mm-dd hh:mm:ss.mmmmmm+00:00"
        :return: UTC timestamp of last received heartbeat
        """
        last_hb = obj.connectorheartbeat.last_heartbeat
        if pretty:
            last_hb = datetime_iso_format(last_hb, hide_microsec=True)
        return last_hb

    @staticmethod
    def next_heartbeat(obj, pretty=True):
        """
        see last_heartbeat()
        :return: UTC timestamp of next expected heartbeat
        """
        next_hb = obj.connectorheartbeat.next_heartbeat
        if pretty:
            next_hb = datetime_iso_format(next_hb, hide_microsec=True)
        return next_hb

    @staticmethod
    def alive(obj):
        """
        Connector is alive if the current time has not yet passed the timestamp
        of the next expected heartbeat
        """
        current_time = datetime.now(timezone.utc)
        next_hb = obj.connectorheartbeat.next_heartbeat
        return True if current_time <= next_hb else False
    alive.boolean = True

    def add_view(self, request, form_url='', extra_context=None):
        """
        Display only name and a hint while adding a new connector. This is as
        most other fields are not populated yet, and will only after the MQTT
        topics have been set.
        """
        self.fieldsets = (
            (None, {
                'description': '<h3>After entering the connector name, '
                               'click "Save and continue editing" to proceed '
                               'with the connector integration.</h3>',
                'fields': ('name', )
            }),
        )
        self.inlines = ()
        return super(ConnectorAdmin, self).add_view(request)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Display the full formsets content in change view.
        """
        self.fieldsets = (
            ('Basic information', {
                'fields': (
                    'name',
                    ('added', 'last_changed'),
                    ('num_available_datapoints', 'num_used_datapoints'),
                    ('alive', 'last_heartbeat', 'next_heartbeat'),
                )
            }),
            ('MQTT topics', {
                'fields': (
                    'mqtt_topic_logs',
                    'mqtt_topic_heartbeat',
                    'mqtt_topic_available_datapoints',
                    'mqtt_topic_datapoint_map',
                    'mqtt_topic_raw_message_to_db',
                    'mqtt_topic_raw_message_reprocess',
                    'mqtt_topic_datapoint_message_wildcard',
                ),
                'classes': ('collapse', )
            }),
        )
        self.inlines = (UsedDatapointsInline, ConnectorLogEntryInline, )
        return super(ConnectorAdmin, self).change_view(request, object_id)

    def response_change(self, request, obj):
        """
        Overridden to provide redirect URL for a custom button
        ("Go to available datapoints").
        :param request: POST request sent when clicking one of the
                        buttons in the change view (e.g. "SAVE")
        :param obj: current connector
        :return: URL
        """
        if "_av_dp" in request.POST:
            return HttpResponseRedirect(
                "/admin/admin_interface/datapoint/?connector__id__exact={}"
                .format(obj.id)
            )
        return super().response_change(request, obj)


@admin.register(ConnectorHeartbeat)
class ConnectorHeartbeatAdmin(admin.ModelAdmin):
    """
    Readonly model to search and view heartbeat entries.
    """
    list_display = (
        "connector",
        "last_hb_pretty",
        "next_hb_pretty",
    )
    list_filter = (
        "connector",
    )
    list_display_links = (
        "last_hb_pretty",
        "next_hb_pretty"
    )
    fields = list_display
    readonly_fields = fields

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def last_hb_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        return datetime_iso_format(obj.last_heartbeat, hide_microsec=True)
    last_hb_pretty.admin_order_field = "last_heartbeat"
    last_hb_pretty.short_description = "Last heartbeat"

    def next_hb_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        return datetime_iso_format(obj.next_heartbeat, hide_microsec=True)
    next_hb_pretty.admin_order_field = "next_heartbeat"
    next_hb_pretty.short_description = "Next heartbeat"

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False

    def has_change_permission(cls, request, obj=None):
        """
        Disable remaining save buttons, there is nothing to change anyway.
        """
        return False


@admin.register(ConnectorLogEntry)
class ConnectorLogsAdmin(admin.ModelAdmin):
    """
    Readonly model to search and view log entries.
    """
    list_display = (
        "connector",
        "level",
        "timestamp_pretty",
        "emitter",
        "msg",
    )
    list_filter = (
        "connector",
        "level",
        "emitter",
    )
    list_display_links = (
        "msg",
    )
    search_fields = (
        "msg",
    )
    fields = list_display
    readonly_fields = fields

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def timestamp_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        return datetime_iso_format(obj.timestamp, hide_microsec=True)
    timestamp_pretty.admin_order_field = "timestamp"
    timestamp_pretty.short_description = "Timestamp"

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False

    def has_change_permission(cls, request, obj=None):
        """
        Disable remaining save buttons, there is nothing to change anyway.
        """
        return False


def create_datapoint_addition_inlines():
    """
    This creates StackedInline admin objects for all ModelAdditions known
    to datapoint. It is used by the DatapointAdmin.
    """
    datapoint_addition_inlines = {}
    use_as_addition_models = Datapoint.use_as_addition_models
    for use_as in use_as_addition_models.keys():

        # Get te model of the DatapointAddition
        ct_kwargs = use_as_addition_models[use_as]
        addition_type = ContentType.objects.get(**ct_kwargs)
        addition_model = addition_type.model_class()

        # Compute fields and readonly fields. Access to _meta following
        # https://docs.djangoproject.com/en/3.0/ref/models/meta/
        model_fields = addition_model._meta.get_fields()
        # datapoint is not relevant to display.
        fields = [f.name for f in model_fields if f.name != "datapoint"]
        # There might be more fields that must be set readonly.
        readonly_fields = [f.name for f in model_fields if f.editable == False]

        # Now build the inline class based on the above and store it.
        class DatapointAdditionInline(admin.StackedInline):
            can_delete = False
            verbose_name_plural = "Additional metadata"
        DatapointAdditionInline.model = addition_model
        DatapointAdditionInline.fields = fields
        DatapointAdditionInline.readonly_fields = readonly_fields
        datapoint_addition_inlines[use_as] = DatapointAdditionInline
    return datapoint_addition_inlines

datapoint_addition_inlines = create_datapoint_addition_inlines()


@admin.register(Datapoint)
class DatapointAdmin(admin.ModelAdmin):
    """
    Admin model instance for Datapoints, that also displays fields of the
    addition models.

    This model does not allow adding datapoints manually, it doesn't make
    sense, all datapoints are created by the connectors.
    """
    list_display = (
        "connector",
        "key_in_connector",
        "type",
        "use_as",
        "example_value",
    )
    list_display_links = (
        "key_in_connector",
    )
    list_filter = (
        "type",
        "connector",
        "use_as",
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
    )
    fieldsets = (
            ('GENERIC METADATA', {
                "fields": (
                    "use_as",
                    "connector",
                    "key_in_connector",
                    "type",
                    "example_value",
                )
            }),
    )
    actions = (
        "mark_not_used",
        "mark_numeric",
        "mark_text",
    )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Dynamically display the according DatapointAdditionInline based on
        `use_as`
        """
        use_as = Datapoint.objects.get(id=object_id).use_as
        if use_as not in datapoint_addition_inlines:
            self.inlines = ()
        else:
            DatapointAdditionInline = datapoint_addition_inlines[use_as]
            self.inlines = (DatapointAdditionInline, )
        return super().change_view(request, object_id)

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def mark_not_used(self, request, queryset):
        queryset.update(use_as="not used")
    mark_not_used.short_description = (
        "Mark selected datapoints as not used"
    )

    def mark_numeric(self, request, queryset):
        queryset.update(use_as="numeric")
    mark_numeric.short_description = (
        "Mark selected datapoints as numeric"
    )

    def mark_text(self, request, queryset):
        queryset.update(use_as="text")
    mark_text.short_description = (
        "Mark selected datapoints as text"
    )

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False
