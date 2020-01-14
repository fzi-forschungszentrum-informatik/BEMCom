from django.contrib import admin
from django.utils.text import slugify
from django.contrib.admin.models import LogEntry
from .models import Connector, Device, GenericDatapoint, ConnectorHeartbeat, \
    ConnectorLogEntry, ConnectorDatapointTopicMapper, NumericDatapoint
from .signals import subscription_status
from .utils import datetime_iso_format
from datetime import datetime, timezone

"""
Add actions to be performed on selected objects.
Below: example to change the heartbeat topic to "beat":
--------------------
    def change_mqtt_topic_heartbeat(modeladmin, request, queryset):
        queryset.update(mqtt_topic_heartbeat='beat')
        
    change_mqtt_topic_heartbeat.short_description = "Change MQTT topic for heartbeat"
--------------------
"""


class DatapointMappingInline(admin.TabularInline):
    model = ConnectorDatapointTopicMapper
    extra = 0
    fields = ('datapoint_key_in_connector', 'mqtt_topic', 'datapoint_type', 'subscribed', )
    readonly_fields = ('datapoint_key_in_connector', 'mqtt_topic', 'datapoint_type', )
    ordering = ('subscribed', )
    verbose_name_plural = "Available datapoints subscription management"
    can_delete = False

    # Uncomment to only display unsubscribed datapoints
    # def get_queryset(self, request):
    #     queryset = super(DatapointMappingInline, self).get_queryset(request)
    #     return queryset.filter(subscribed=False)


@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):
    """
    TODO: Managing mapping and subscription in connector change view
            - human-readable name instead of key?
            - Set subscribed status of corresponding available datapoint accordingly
            - Saving of subscribed topics to connector object (?)
    TODO: Display datapoint mapping directly after the basic information (might not be possible)
    TODO: If possible: "Subscribe to all" button if possible

    """
    """
    List view customizations
    """
    # Attributes to be displayed
    list_display = ('name', 'date_added','num_subscribed_datapoints', 'alive', )

    # Ordering of objects
    ordering = ('-date_added',)

    # Filter
    # list_filter = ('attr', )

    # Search fields
    search_fields = ('name', )

    # Add action function defined above
    # actions = [change_mqtt_topic_heartbeat]

    """
    Add/Change object view customizations
    """
    # Fields to be displayed
    # fields = ('name',)

    # Fields to be hidden
    # exclude = ('name', )

    # Fieldsets allow grouping of fields with corresponding title & description
    # Doc: https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.fieldsets
    # fieldsets = (
    #     ('Datapoints', {
    #         'fields': ('available_datapoints', '')
    #     }),
    #     ('Field group 2 title', {
    #         'description': 'Further info for this group.',
    #         'classes': ('collapse', ),
    #         'fields': ()
    #     })
    # )

    inlines = ()

    # @staticmethod
    # def available_datapoints(obj):
    #     # datapoints = []
    #     # for dp in ConnectorAvailableDatapoints.objects.filter(connector=obj.id).last():
    #     #     if dp not in datapoints:
    #     #         datapoints.append(dp.__str__())
    #     #
    #     # if datapoints:
    #     #     return ", ".join(datapoints)  # return list as string
    #     datapoints = ConnectorAvailableDatapoints.objects.filter(connector=obj.id)
    #     keys = [dp.datapoint_key_in_connector for dp in datapoints]
    #     return len(keys)

    def num_subscribed_datapoints(self, obj):
        num = ConnectorDatapointTopicMapper.objects.filter(connector=obj.id, subscribed=True).count()
        return num
    num_subscribed_datapoints.short_description = "Number of subscribed datapoints"

    @staticmethod
    def last_heartbeat(obj, pretty=True):
        latest_hb_message = ConnectorHeartbeat.objects.filter(connector=obj.id).latest('last_heartbeat')
        last_hb = latest_hb_message.last_heartbeat
        if pretty:
            last_hb = datetime_iso_format(last_hb, hide_microsec=True)
        return last_hb

    @staticmethod
    def next_heartbeat(obj, pretty=True):
        latest_hb_message = ConnectorHeartbeat.objects.filter(connector=obj.id).latest('next_heartbeat')
        next_hb = latest_hb_message.next_heartbeat
        if pretty:
            next_hb = datetime_iso_format(next_hb, hide_microsec=True)
        return next_hb

    def alive(self, obj):
        current_time = datetime.now(timezone.utc)
        next_hb = ConnectorHeartbeat.objects.filter(connector=obj.id).latest('next_heartbeat').next_heartbeat
        return True if current_time <= next_hb else False
    alive.boolean = True

    @staticmethod
    def mqtt_message_topics(obj):
        key_topic_mappings = {}
        mappers = ConnectorDatapointTopicMapper.objects.filter(connector=obj.id)
        for mapper in mappers:
            av_dp = GenericDatapoint.objects.filter(connector=obj.id, datapoint_key_in_connector=mapper.datapoint_key_in_connector)[0]
            key_topic_mappings[av_dp.datapoint_key_in_connector] = mapper.mqtt_topic
        return key_topic_mappings

    # Things that shall be displayed in add object view, but not change object view
    def add_view(self, request, form_url='', extra_context=None):
        self.fieldsets = (
            (None, {
                'description': '<h3>After entering the connector name, '
                               'click "Save and continue editing" to proceed with the connector integration.</h3>',
                'fields': ('name', )
            }),
            # ('MQTT topics', {
            #     'description': '<h3>Click "Save and continue editing" to prefill the MQTT topics '
            #                    'with <i>connector-name/topic</i>.</h3>',
            #     'classes': ('collapse',),
            #     'fields': [topic for topic in Connector.get_mqtt_topics(Connector()).keys()]
            # }),
        )
        return super(ConnectorAdmin, self).add_view(request)

    # Things that shall be displayed in change object view, but not add object view
    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.inlines = [DatapointMappingInline]
        self.fieldsets = (
            ('Basic information', {
                'fields': ('name', 'date_added', ('alive', 'last_heartbeat', 'next_heartbeat'), )
            }),
            ('MQTT topics', {
                'fields': [topic for topic in Connector.get_mqtt_topics(Connector()).keys()]
            }),
        )
        self.readonly_fields = ('date_added', 'last_heartbeat', 'next_heartbeat', 'alive', )

        return super(ConnectorAdmin, self).change_view(request, object_id)

    def save_related(self, request, form, formsets, change):
        all_saved = False
        for inlines in formsets:
            if inlines.has_changed() and str(inlines).__contains__("connectordatapointtopicmapper"):
                old_subscription_status = {}
                # Save old subscription status before saving the new ones
                for mapping in ConnectorDatapointTopicMapper.objects.filter(connector=form.instance.id):
                    old_subscription_status[mapping.id] = mapping.subscribed
                print(old_subscription_status)

                # Save all inline objects
                super().save_related(request, form, formsets, change)
                all_saved = True

                # Save mapper object again if subscription status has changed to trigger update
                for mapping_id, status in old_subscription_status.items():
                    mapping = ConnectorDatapointTopicMapper.objects.get(pk=mapping_id)
                    if mapping.subscribed != status:
                        mapping.save(update_fields=['subscribed'])
        if not all_saved:
            super().save_related(request, form, formsets, change)

        # TODO: Delete stuff below if it's definitely not needed again
        # last_log = LogEntry.objects.latest('action_time')
        # print(last_log.get_edited_object())
        # for form in formsets:
        #     print(type(form))
        #     print(form)
        #     new_data = form.cleaned_data
        #     print(new_data)
        #
        #
        #     for new_object_data in new_data:
        #         print(new_object_data['id'])
        #         #old_subscription_status
        #         #print("Subscription status has changed!")


            # # form.cleaned_data : list of dictionaries for each inline object with (key,val) = (attribute,value)
            # for field, new_value in form.cleaned_data.items():
            #     #print(field)
            #     if new_value != form.initial[field]:
            #         print("Old value: {}, New value: {}".format(form.initial[field], new_value))
            # # for field, new_value in form.cleaned_data.items():
            # #     print(field)


        # mappings = ConnectorDatapointTopicMapper.objects.filter(connector=form.instance.id)
        # for map in mappings:
        #     print('{}: {}'. format(getattr(map, 'mqtt_topic'), getattr(map, 'subscribed')))

    # def save_model(self, request, obj, form, change):
    #     update_fields = []
    #     print(obj)
    #     print(change)
    #     print(request)
    #
    #     # True if something changed in model, False if model is added
    #     if change:
    #         for field, new_value in form.cleaned_data.items():
    #             print(field)
    #             if new_value != form.initial[field]:
    #                 print("Old value: {}, New value: {}".format(form.initial[field], new_value))
    #
    #                 update_fields.append(field)
    #     print(update_fields)
    #     obj.save(update_fields=update_fields)

@admin.register(GenericDatapoint)
class GenericDatapointAdmin(admin.ModelAdmin):
        
    list_display = (
        "key_in_connector",
        "connector",
        "type",
        "example_value",
        "use_as",
    )
    list_filter = (
        "connector",
        "type",
        "use_as",
    )
    search_fields = (
        "key_in_connector",
        "example_value",
    )
    readonly_fields = (
        "connector",
        "type",
        "key_in_connector",
        "example_value"
    )
    actions = (
        "mark_not_used",
        "mark_numeric",
        "mark_text",
    )

    @staticmethod
    def connector(obj):
        return obj.connector.name
    
    def mark_not_used(self, request, queryset):
        queryset.update(use_as='numeric')
    mark_not_used.short_description = "Mark selected datapoints as not used"

    def mark_numeric(self, request, queryset):
        queryset.update(use_as='numeric')
    mark_numeric.short_description = "Mark selected datapoints as numeric"
    
    def mark_text(self, request, queryset):
        queryset.update(use_as='numeric')
    mark_text.short_description = "Mark selected datapoints as text"

@admin.register(NumericDatapoint)
class NumericDatapointAdmin(GenericDatapointAdmin):
    pass

@admin.register(ConnectorHeartbeat)
class ConnectorHeartbeatAdmin(admin.ModelAdmin):
    list_display = ('connector', 'last_hb_iso', 'next_hb_iso', )
    list_filter = ('connector', )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def last_hb_iso(self, obj):
        return obj.last_heartbeat.isoformat(sep=' ')
    last_hb_iso.admin_order_field = 'last_heartbeat'
    last_hb_iso.short_description = "Last heartbeat"

    def next_hb_iso(self, obj):
        return obj.next_heartbeat.isoformat(sep=' ')
    next_hb_iso.admin_order_field = 'next_heartbeat'
    next_hb_iso.short_description = "Next heartbeat"


@admin.register(ConnectorLogEntry)
class ConnectorLogsAdmin(admin.ModelAdmin):
    list_display = ('id', 'connector', 'timestamp_iso', 'msg', 'emitter', 'level')
    list_filter = ('connector', 'emitter', )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def timestamp_iso(self, obj):
        return obj.timestamp.isoformat(sep=' ')
    timestamp_iso.admin_order_field = 'timestamp'
    timestamp_iso.short_description = "Timestamp"


@admin.register(ConnectorDatapointTopicMapper)
class ConnectorDatapointTopicMapperAdmin(admin.ModelAdmin):
    list_display = ('id', 'connector', 'datapoint_key_in_connector', 'datapoint_type', 'mqtt_topic', )
    #list_filter = ('datapoint_key_in_connector', 'connector', 'datapoint_type', 'datapoint_example_value', )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def save_model(self, request, obj, form, change):
        update_fields = []

        # True if something changed in model
        # Note that change is False at the very first time
        if change:
            for field, new_value in form.cleaned_data.items():
                if new_value != form.initial[field]:
                    update_fields.append(field)
        obj.save(update_fields=update_fields)


# Register your models here.
admin.site.register(Device)
