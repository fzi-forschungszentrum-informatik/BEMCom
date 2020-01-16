from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib.admin import actions
from django.utils.text import slugify
from django.contrib.admin.views.main import ChangeList as ChangeListDefault
from django.urls import reverse
from .models import Connector, ConnectorAvailableDatapoints, ConnectorHeartbeat, ConnectorLogEntry, \
    Device, NonDevice, TestDevice, GenericDevice, \
    NumericDatapoint, TextDatapoint
from .utils import datetime_iso_format
from datetime import datetime, timezone
import uuid

"""
Custom actions to be performed on selected objects.
Add action to a model's list view with 'actions= [actionfunction1, actionfunction2, ]' inside the ModelAdmin class
"""


def action_delete_devices(modeladmin, request, queryset):
    """
    TODO: Add intermediate confirmation page
        (see https://docs.djangoproject.com/en/3.0/ref/contrib/admin/actions/#actions-that-provide-intermediate-pages)
    @david: only necessary for the abstract-device-base-class-solution
    """
    all_device_classes = GenericDevice.get_list_of_subclasses_with_identifier()
    for obj_pk in request._post.getlist('_selected_action'):
        cls_id = obj_pk[0]  # Example: obj_pk is "d-3", because object is of class Device -> class identifier is 'd'
        obj_class = all_device_classes[cls_id]['class']
        obj_class.objects.filter(pk=obj_pk).delete()

action_delete_devices.short_description = "Delete selected objects"


def action_make_numeric(modeladmin, request, queryset):
    for obj in queryset:
        setattr(obj, 'format', 'num')
        obj.save(update_fields=['format'])
action_make_numeric.short_description = "Change format to numeric"


def action_make_text(modeladmin, request, queryset):
    for obj in queryset:
        setattr(obj, 'format', 'text')
        obj.save(update_fields=['format'])
action_make_text.short_description = "Change format to text"


def action_make_unused(modeladmin, request, queryset):
    for obj in queryset:
        setattr(obj, 'format', 'unused')
        obj.save(update_fields=['format'])
action_make_unused.short_description = "Mark as not used"


class AvailableDatapointsInline(admin.TabularInline):
    """
    @david: only necessary when available datapoints should be displayed in connector views
    """
    model = ConnectorAvailableDatapoints
    extra = 0
    fields = ('datapoint_key_in_connector', 'datapoint_type', 'datapoint_example_value', 'format', )
    readonly_fields = ('datapoint_key_in_connector', 'datapoint_type', 'datapoint_example_value', )
    ordering = ('datapoint_key_in_connector', )
    verbose_name_plural = "Available datapoints subscription management"
    can_delete = False

    def get_queryset(self, request):
        """
        Limited query set for dev
        """
        queryset = super(AvailableDatapointsInline, self).get_queryset(request)
        return queryset.filter(datapoint_key_in_connector__istartswith='meter_1_')


class DatapointsInline(admin.TabularInline):
    """
    Base class for numeric and text datapoint inline classes (see below)
    @david: relevant, although you might need to adapt it to your Generic/Numeric/TextDatapoint model structure/relations
    """
    extra = 0
    fields = ('datapoint_key_in_connector', 'mqtt_topic', 'last_value', 'last_timestamp')
    readonly_fields = fields
    ordering = ('datapoint_key_in_connector',)
    show_change_link = True
    can_delete = False
    classes = ('collapse', )

    def has_add_permission(self, request, obj):
        return False


class NumericDatapointsInline(DatapointsInline):
    model = NumericDatapoint
    verbose_name_plural = "Active numeric datapoints of this connector"


class TextDatapointsInline(DatapointsInline):
    model = TextDatapoint
    verbose_name_plural = "Active text datapoints of this connector"


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
    """
    @david: whole class is relevant if not stated differently
    """
    """
    List view customizations
    """
    # Attributes to be displayed
    list_display = ('name', 'date_added', 'alive', )

    # Ordering of objects
    ordering = ('-date_added',)

    # Filter
    # list_filter = ('attr', )

    # Search fields
    search_fields = ('name', )


    """
    Add/Change object view customizations
    """
    # Fields to be displayed
    # fields = ('name',)

    # Fields to be hidden
    # exclude = ('name', )

    # Inline objects to be displayed in change/add view
    # Needs to be initialized here when overriding change_view() and adding Inline objects inside the method
    inlines = ()

    # def num_subscribed_datapoints(self, obj):
    #         """
    #         Number of datapoints from a connector I have subscribed to
    #         TODO: Keep for now as reference for possible similar implementation or idea
    #             -> delete if not needed anymore
    #         """
    #     num = ConnectorDatapointTopicMapper.objects.filter(connector=obj.id, subscribed=True).count()
    #     return num
    # num_subscribed_datapoints.short_description = "Number of subscribed datapoints"

    @staticmethod
    def last_heartbeat(obj, pretty=True):
        """
        :param obj: current connector object
        :param pretty: If true (default), timestamp will be returned like this: "yyyy-mm-dd hh:mm:ss (UTC)"
                        If false, format is "yyyy-mm-dd hh:mm:ss.mmmmmm+00:00"
        :return: UTC timestamp of last received heartbeat
        """
        latest_hb_message = ConnectorHeartbeat.objects.filter(connector=obj.id).latest('last_heartbeat')
        last_hb = latest_hb_message.last_heartbeat
        if pretty:
            last_hb = datetime_iso_format(last_hb, hide_microsec=True)
        return last_hb

    @staticmethod
    def next_heartbeat(obj, pretty=True):
        """
        see last_heartbeat()
        :return: UTC timestamp of next expected heartbeat
        """
        latest_hb_message = ConnectorHeartbeat.objects.filter(connector=obj.id).latest('next_heartbeat')
        next_hb = latest_hb_message.next_heartbeat
        if pretty:
            next_hb = datetime_iso_format(next_hb, hide_microsec=True)
        return next_hb

    def alive(self, obj):
        """
        Connector is alive if the current time has not yet passed the timestamp of the next expected heartbeat
        """
        current_time = datetime.now(timezone.utc)
        next_hb = ConnectorHeartbeat.objects.filter(connector=obj.id).latest('next_heartbeat').next_heartbeat
        return True if current_time <= next_hb else False
    alive.boolean = True

    def add_view(self, request, form_url='', extra_context=None):
        """
        General: Things that shall be displayed in add object view, but not change object view.
        Here: Only display the name field to enter connector name and some instruction.
        """
        self.inlines = ()
        self.fieldsets = (
            (None, {
                'description': '<h3>After entering the connector name, '
                               'click "Save and continue editing" to proceed with the connector integration.</h3>',
                'fields': ('name', )
            }),
        )
        return super(ConnectorAdmin, self).add_view(request)

    # Adapted change form template to display "Go to available datapoints" button
    change_form_template = '../templates/connector_change_form.html'

    def response_change(self, request, obj):
        """
        Overridden to provide redirect URL for a custom button ("Go to available datapoints").
        :param request: POST request sent when clicking one of the buttons in the change view (e.g. "SAVE")
        :param obj: current connector
        :return: URL
        """
        if "_av_dp" in request.POST:
            return HttpResponseRedirect("/admin/admin_interface/"
                                        "connectoravailabledatapoints/?connector__id__exact={}".format(obj.id))
        return super().response_change(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        General: Things that shall be displayed in change object view, but not add object view.
        Here:
            - Selected connector fields or information
            - Active datapoints
            - Last 10 log entries
        """
        # Add Inline objects to be displayed
        self.inlines = [NumericDatapointsInline, TextDatapointsInline, ConnectorLogEntryInline]

        self.fieldsets = (
            ('Basic information', {
                'fields': ('name', 'date_added', ('alive', 'last_heartbeat', 'next_heartbeat'), )
            }),
            ('MQTT topics', {
                'fields': [topic for topic in Connector.get_mqtt_topic_fields(Connector.objects.get(id=object_id)).keys()],
                'classes': ('collapse', )
            }),
        )

        self.readonly_fields = ('date_added', 'last_heartbeat', 'next_heartbeat', 'alive', )

        return super(ConnectorAdmin, self).change_view(request, object_id)

    # def save_related(self, request, form, formsets, change):
    #     """
    #     Overridden to trigger update of a Datapoint's subscription status when status of corresponding
    #     mapping object was changed.
    #     Update is triggered via post_save signal, which necessitates the provision of the update_fields argument.
    #     TODO: Keep for now as reference for possible similar implementation
    #         -> delete if not needed anymore
    #     """
    #     all_saved = False
    #     for inlines in formsets:
    #         if inlines.has_changed() and str(inlines).__contains__("connectordatapointtopicmapper"):
    #             old_subscription_status = {}
    #             # Save old subscription status before saving the new ones
    #             for mapping in ConnectorDatapointTopicMapper.objects.filter(connector=form.instance.id):
    #                 old_subscription_status[mapping.id] = mapping.subscribed
    #
    #             # Save all inline objects
    #             super().save_related(request, form, formsets, change)
    #             all_saved = True
    #
    #             # Save mapper object again if subscription status has changed to trigger update on
    #             # corresponding datapoint via post_save signal
    #             for mapping_id, status in old_subscription_status.items():
    #                 mapping = ConnectorDatapointTopicMapper.objects.get(pk=mapping_id)
    #                 if mapping.subscribed != status:
    #                     mapping.save(update_fields=['subscribed'])
    #     if not all_saved:
    #         super().save_related(request, form, formsets, change)


@admin.register(ConnectorAvailableDatapoints)
class ConnectorAvailableDatapointsAdmin(admin.ModelAdmin):
    list_display = ('id', 'connector', 'datapoint_type', 'datapoint_example_value',
                    'datapoint_key_in_connector', 'format', )
    list_filter = ('connector', 'format', )
    search_fields = ('datapoint_key_in_connector', )

    actions = (action_make_numeric, action_make_text, action_make_unused, )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def save_model(self, request, obj, form, change):
        """
        Add field name to update_fields if a field value has has been changed in the change view.
        (Update_fields is an argument for the model's save method.)
        Here: Used together with a post_save signal to create a corresponding Datapoint object when format/status
         changes from "unused" to "numeric" or "text"
        @david: Probably not relevant, because you have your own solution
        """

        update_fields = []

        # True if model is changed not added
        if change:
            for field, new_value in form.cleaned_data.items():
                print("field: {}, new_value={}, old_value={}".format(field, new_value, form.initial[field]))
                if new_value != form.initial[field] and form.initial[field] == 'unused':
                    update_fields.append(field)
        obj.save(update_fields=update_fields)


@admin.register(ConnectorHeartbeat)
class ConnectorHeartbeatAdmin(admin.ModelAdmin):
    """
    List view customization
    @david: adopt it if you like it
    """
    list_display = ('connector', 'last_hb_iso', 'next_hb_iso', )
    list_filter = ('connector', )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    # displays a prettier timestamp format
    def last_hb_iso(self, obj):
        return obj.last_heartbeat.isoformat(sep=' ')
    last_hb_iso.admin_order_field = 'last_heartbeat'
    last_hb_iso.short_description = "Last heartbeat"

    # displays a prettier timestamp format
    def next_hb_iso(self, obj):
        return obj.next_heartbeat.isoformat(sep=' ')
    next_hb_iso.admin_order_field = 'next_heartbeat'
    next_hb_iso.short_description = "Next heartbeat"


@admin.register(ConnectorLogEntry)
class ConnectorLogsAdmin(admin.ModelAdmin):
    """
    List view customization
    @david: adopt it if you like it
    """
    list_display = ('id', 'connector', 'timestamp_iso', 'msg', 'emitter', 'level')
    list_filter = ('connector', 'emitter', )

    @staticmethod
    def connector(obj):
        return obj.connector.name

    # displays a prettier timestamp format
    def timestamp_iso(self, obj):
        return obj.timestamp.isoformat(sep=' ')
    timestamp_iso.admin_order_field = 'timestamp'
    timestamp_iso.short_description = "Timestamp"


class DeviceChangeList(ChangeListDefault):
    """
    Custom ChangeList for displaying all (non-) device types together
    Note: root_queryset is defined before get_queryset is called -> contains only Device objects
    """
    def get_queryset(self, request):
        """
        Returns the union of all query sets from all device types (except for POST requests)
        """
        if request.method == 'GET' and self.root_queryset.exists():
            # Get base class of the Device class
            base_class = self.root_queryset[0].__class__.__bases__[0]
            # Get all respective classes of the different device types
            all_subclasses = base_class.get_list_of_subclasses_with_identifier()
            querysets = []
            # For each subclass (model), get all objects and add the resulting query set to the list
            for cls_id, cls_dict in all_subclasses.items():
                querysets.append(cls_dict['class'].objects.all())
            # Create union of all subclass-query sets
            united_queryset = querysets[0].union(querysets[1])
            if len(querysets) > 2:
                for i in range(2, len(querysets)):
                    united_queryset = united_queryset.union(querysets[i])

            return united_queryset

        return super().get_queryset(request)

    def url_for_result(self, result):
        """
        Provides the correct change-view-URL for each non-device object listed in the Device list view
        :param result: a model object displayed in the list view
        :return: URL to the change view of the respective object
        @david: only necessary for the abstract-device-base-class-solution
        """
        devices_only_queryset = self.root_queryset
        base_class = devices_only_queryset[0].__class__.__bases__[0]

        # Check if the current model (result) is a Device or other type by searching the Device DB for its primary key
        if not devices_only_queryset.filter(pk=result.pk).exists():
            # Model is a not a Device -> adapt URL to this model's change page
            current_model_name = self.root_queryset[0].__class__.__name__
            excluded_classes = [self.root_queryset[0].__class__.get_class_identifier()]
            new_model_name = base_class.get_list_of_subclasses_with_identifier(exclude=excluded_classes)[result.pk[0]]['name']
            new_device_url = super().url_for_result(result).replace(current_model_name.lower(), new_model_name.lower())
            return new_device_url

        return super().url_for_result(result)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """
    List view customizations for Device model:
        - list all device types together (i.e. of class Device, NonDevice, ...)
        - remove default delete action, because it doesn't work with this custom list
        - add custom delete action
    @david: only necessary for the abstract-device-base-class-solution
    """

    list_display = ('type', 'location_detail', 'full_id','spec_id')
    actions = [action_delete_devices]

    def get_changelist(self, request, **kwargs):
        return DeviceChangeList

    def get_actions(self, request):
        all_actions = super().get_actions(request)
        if 'delete_selected' in all_actions:
            del all_actions['delete_selected']
        return all_actions

# Register your models here.
admin.site.register(NonDevice)
admin.site.register(TestDevice)
admin.site.register(NumericDatapoint)
admin.site.register(TextDatapoint)


