from datetime import datetime, timezone

from django import forms, db
from django.contrib import admin
from django.http import HttpResponseRedirect

from api_main.models.connector import Connector, ConnectorHeartbeat
from api_main.models.connector import ConnectorLogEntry
from api_main.models.datapoint import Datapoint
from ems_utils.timestamp import datetime_to_pretty_str


class UsedDatapointsInline(admin.TabularInline):
    """
    Inline view of the active datapoints by a connector.
    """
    model = Datapoint
    fields = (
        "key_in_connector",
        "type",
        "example_value",
        "is_active",
        "data_format",
        "description"
        )
    readonly_fields = (
        "key_in_connector",
        "type",
        "example_value"
    )
    ordering = ('key_in_connector', )
    verbose_name_plural = "Active datapoints of connector"
    can_delete = False
    show_change_link = True
    classes = ['collapse']
    # Display wider version of normal TextInput for all text fields, as
    # default forms look ugly.
    formfield_overrides = {
        db.models.TextField: {'widget': forms.TextInput(attrs={'size': '60'})},
    }

    def has_add_permission(self, request, obj=None):
        """
        Remove the add another button at the bottom of the inline, makes no
        sense to add another datapoint.
        """
        return False

    def get_queryset(self, request):
        """
        Limit query to Datapoints marked not as "not_used"
        """
        queryset = super(UsedDatapointsInline, self).get_queryset(request)
        return queryset.filter(is_active=True)


class ConnectorLogEntryInline(admin.TabularInline):
    """
    Inline view for connector to list the last log messages received by this
    connector.
    """
    model = ConnectorLogEntry
    verbose_name_plural = "Last 10 log entries"
    fields = ('timestamp', 'msg', 'emitter', )
    readonly_fields = fields
    ordering = ('timestamp', )
    can_delete = False
    classes = ('collapse', )

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """
        Note: Getting query set in descending order (by timestamp) and slicing
              it throws error ("filtering is not possible after slicing"),
              because the custom (returned) query set is filtered again for the
              current connector. Hence this workaround: First get IDs of last
              ten entries, then filter all entries based on these IDs.
              -> Returned query set can now be filtered again for the current
              connector :)
        """
        all_entries = super().get_queryset(request)
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
        db.models.TextField: {'widget': forms.TextInput(attrs={'size': '60'})},
    }

    # Adapted change form template to display "Go to available datapoints"
    # button
    change_form_template = '../templates/api_admin_ui/connector_change_form.html'

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
        return dpo.filter(connector=obj.id).filter(is_active=True).count()
    num_used_datapoints.short_description = "Number of used datapoints"

    @staticmethod
    def last_heartbeat(obj, pretty=True):
        """
        :param obj: current connector object
        :param pretty: If true (default), timestamp will be returned like this:
                        "yyyy-mm-dd hh:mm:ss (UTC)"
                        If false, format is "yyyy-mm-dd hh:mm:ss.mmmmmm+00:00"
        :return: UTC timestamp of last received heartbeat
        """
        last_hb = obj.connectorheartbeat.last_heartbeat
        if pretty:
            last_hb = datetime_to_pretty_str(last_hb)
        return last_hb

    @staticmethod
    def next_heartbeat(obj, pretty=True):
        """
        see last_heartbeat()
        :return: UTC timestamp of next expected heartbeat
        """
        next_hb = obj.connectorheartbeat.next_heartbeat
        if pretty:
            next_hb = datetime_to_pretty_str(next_hb)
        return next_hb

    def alive(self, obj):
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
                "/admin/api_main/datapoint/?connector__id__exact={}"
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
        return datetime_to_pretty_str(obj.last_heartbeat)
    last_hb_pretty.admin_order_field = "last_heartbeat"
    last_hb_pretty.short_description = "Last heartbeat"

    def next_hb_pretty(self, obj):
        """
        Displays a prettier timestamp format.
        """
        return datetime_to_pretty_str(obj.next_heartbeat)
    next_hb_pretty.admin_order_field = "next_heartbeat"
    next_hb_pretty.short_description = "Next heartbeat"

    def has_add_permission(cls, request, obj=None):
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
        return datetime_to_pretty_str(obj.timestamp)
    timestamp_pretty.admin_order_field = "timestamp"
    timestamp_pretty.short_description = "Timestamp"

    def has_add_permission(cls, request, obj=None):
        """
        Remove `add` and `save and add another` button.
        """
        return False

    def has_change_permission(cls, request, obj=None):
        """
        Disable remaining save buttons, there is nothing to change anyway.
        """
        return False
