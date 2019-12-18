from django.contrib import admin
from django.utils.text import slugify
from .models import Connector, Device, ConnectorAvailableDatapoints

"""
Add actions to be performed on selected objects.
Below: example to change the heartbeat topic to "beat":
--------------------
    def change_mqtt_topic_heartbeat(modeladmin, request, queryset):
        queryset.update(mqtt_topic_heartbeat='beat')
        
    change_mqtt_topic_heartbeat.short_description = "Change MQTT topic for heartbeat"
--------------------
"""


class AvDPInline(admin.TabularInline):
    model = ConnectorAvailableDatapoints

@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):
    # prepopulated_fields = {}
    # mqtt_topics = Connector.get_mqtt_topics(Connector)
    # for topic in mqtt_topics:
    #     prepopulated_fields[topic] = ("name", mqtt_topics[topic])
    # prepopulated_fields = {"mqtt_topic_heartbeat": ("name", )}

    """
    List view customizations
    """
    # Attributes to be displayed
    list_display = ('name', 'date_created', 'available_datapoints')

    # Ordering of objects
    ordering = ('-date_created',)

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

    #inlines = [AvDPInline]

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

    def available_datapoints(self, obj):
        datapoints = []
        for dp in ConnectorAvailableDatapoints.objects.filter(connector=obj.id):
            datapoints.append(dp.__str__())
        if datapoints:
            return ", ".join(datapoints)  # return list as string
        return "-"

    # Things that shall be displayed in add object view, but not change object view
    def add_view(self, request, form_url='', extra_context=None):
        self.fieldsets = (
            ('Basic information', {
                'fields': ('name', 'date_created')
            }),
            ('MQTT topics', {
                'description': '<h3>Click "Save and continue editing" to prefill the MQTT topics '
                               'with <i>connector-name/topic</i>.</h3>',
                'classes': ('collapse',),
                'fields': [topic for topic in Connector.get_mqtt_topics(Connector()).keys()]
            }),
        )
        return super(ConnectorAdmin, self).add_view(request)

    # Things that shall be displayed in change object view, but not add object view
    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.fieldsets = (
            ('Basic information', {
                'fields': ('name', 'date_created')
            }),
            ('MQTT topics', {
                'fields': [topic for topic in Connector.get_mqtt_topics(Connector()).keys()]
            }),
            ('Data', {
                'fields': ('available_datapoints', )
            }),
        )
        self.readonly_fields = ('available_datapoints', )  # Necessary to display the field
        return super(ConnectorAdmin, self).change_view(request, object_id)

@admin.register(ConnectorAvailableDatapoints)
class ConnectorAvailableDatapointsAdmin(admin.ModelAdmin):
    list_display = ('connector', 'datapoint_type', 'datapoint_example_value', 'active', )

    def connector(self, obj):
        return obj.connector.name


# Register your models here.
admin.site.register(Device)
