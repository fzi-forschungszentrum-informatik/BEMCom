from django.contrib import admin
from django.utils.text import slugify
from .models import Connector, Device

"""
Add actions to be performed on selected objects.
Below: example to change the heartbeat topic to "beat":
--------------------
    def change_mqtt_topic_heartbeat(modeladmin, request, queryset):
        queryset.update(mqtt_topic_heartbeat='beat')
        
    change_mqtt_topic_heartbeat.short_description = "Change MQTT topic for heartbeat"
--------------------
"""


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
    list_display = ('name', 'date_created')

    # Ordering of objects
    ordering = ('-date_created',)

    # Filter
    # list_filter = ('attr', )

    # Search fields
    search_fields = ('name', )

    # Add action function defined above
    # actions = [change_mqtt_topic_heartbeat]

    """
    Add view customizations
    """
    # Fields to be displayed in add view
    # fields = ('name',)

    # Fields to be hidden in add view
    # exclude = ('attr', )

    # Fieldsets allow grouping of fields with corresponding title & description
    # Doc: https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.fieldsets
    # fieldsets = (
    #     ('Field group 1 title', {
    #         'fields': ('name', 'date_created')
    #     }),
    #     ('Field group 2 title', {
    #         'description': 'Further info for this group.',
    #         'classes': ('collapse', ),
    #         'fields': ()
    #     })
    # )

    # Things that shall be displayed in add model view, but not change model view
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
            })
        )
        return super(ConnectorAdmin, self).add_view(request)

    # Things that shall be displayed in change model view, but not add model view
    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.fieldsets = (
            ('Basic information', {
                'fields': ('name', 'date_created')
            }),
            ('MQTT topics', {
                'fields': [topic for topic in Connector.get_mqtt_topics(Connector()).keys()]
            })
        )
        return super(ConnectorAdmin, self).change_view(request, object_id)


# Register your models here.
admin.site.register(Device)