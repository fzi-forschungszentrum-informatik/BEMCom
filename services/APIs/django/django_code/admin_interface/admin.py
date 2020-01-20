from datetime import datetime, timezone

from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.views.main import ChangeList as ChangeListDefault

from admin_interface.models import Connector, Datapoint
from admin_interface.models import ConnectorHeartbeat, ConnectorLogEntry
from admin_interface.models import NumericDatapointAddition
from admin_interface.models import TextDatapointAddition

from .utils import datetime_iso_format


#def action_delete_devices(modeladmin, request, queryset):
#    """
#    TODO: Add intermediate confirmation page
#        (see https://docs.djangoproject.com/en/3.0/ref/contrib/admin/actions/#actions-that-provide-intermediate-pages)
#    @david: only necessary for the abstract-device-base-class-solution
#    """
#    all_device_classes = GenericDevice.get_list_of_subclasses_with_identifier()
#    for obj_pk in request._post.getlist('_selected_action'):
#        cls_id = obj_pk[0]  # Example: obj_pk is "d-3", because object is of class Device -> class identifier is 'd'
#        obj_class = all_device_classes[cls_id]['class']
#        obj_class.objects.filter(pk=obj_pk).delete()
#
#action_delete_devices.short_description = "Delete selected objects"


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


class ConnectorAdminForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = Connector
        widgets = {f: forms.TextInput for f in [
            'name',
            'mqtt_topic_logs',
            'mqtt_topic_heartbeat',
            'mqtt_topic_available_datapoints',
            'mqtt_topic_datapoint_map',
            'mqtt_topic_raw_message_to_db',
            'mqtt_topic_raw_message_reprocess',
            'mqtt_topic_datapoint_message_wildcard',
        ]}


@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):

    form = ConnectorAdminForm
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
    )

    # Needs to be initialized here when overriding change_view() and adding
    # Inline objects inside the method
    inlines = (UsedDatapointsInline, ConnectorLogEntryInline, )

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


class NumericDatapointAdditionInline(admin.StackedInline):
    model = NumericDatapointAddition

class TextDatapointAdditionInline(admin.StackedInline):
    model = TextDatapointAddition

@admin.register(Datapoint)
class DatapointAdmin(admin.ModelAdmin):
    """
    Admin model instance for Datapoints, that also displays fields of the
    additions. Hence, there is no seperate
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

    def get_inline_instances(self, request, obj):
        """
        Look up the model of DatapointAddition and generate a matching inline
        admin instance.

        Inspired by: https://docs.djangoproject.com/en/3.0/ref/contrib/admin/#django.contrib.admin.ModelAdmin.get_inline_instances

        TODO: This deserves one or the other test.
        """
        if obj is None:
        # Add form, obj does not exist, the remaining code would fail.
            return []

        use_as = obj.use_as
        use_as_addition_models = obj.use_as_addition_models

        # This is False for "not used" and potentially an other
        # datapoint usage pattern that requires no additional metadata.
        if not use_as in use_as_addition_models:
            return []

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

        # Now build the inline class based on the above and return it.
        class DatapointAdditionInline(admin.StackedInline):
            # TODO This throws an error on changing use_as, may be related to
            # checking the formsets, which then have already changed.
            # See als: https://stackoverflow.com/questions/13526792/validation-of-dependant-inlines-in-django-admin
            can_delete = False
            verbose_name = "verbose_name"
            verbose_name_plural = "Additional metadata"
            def __init__(self, model, admin_site, addition_model, fields,
                         readonly_fields):
                self.model = addition_model
                self.fields = fields
                self.readonly_fields = readonly_fields
                super().__init__(model, admin_site)

        inline_instance = DatapointAdditionInline(
            model=self.model,
            admin_site=self.admin_site,
            addition_model=addition_model,
            fields=fields,
            readonly_fields=readonly_fields,
        )
        return [inline_instance]

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


#@admin.register(Device)
#class DeviceAdmin(admin.ModelAdmin):
#    """
#    List view customizations for Device model:
#        - list all device types together (i.e. of class Device, NonDevice, ...)
#        - remove default delete action, because it doesn't work with this custom list
#        - add custom delete action
#    @david: only necessary for the abstract-device-base-class-solution
#    """
#
#    list_display = ('type', 'location_detail', 'full_id','spec_id')
##    actions = [action_delete_devices]
#
#    def get_changelist(self, request, **kwargs):
#        return DeviceChangeList
#
#    def get_actions(self, request):
#        all_actions = super().get_actions(request)
#        if 'delete_selected' in all_actions:
#            del all_actions['delete_selected']
#        return all_actions

# Register your models here.
#admin.site.register(NonDevice)
##admin.site.register(TestDevice)
#admin.site.register(NumericDatapoint)
#admin.site.register(TextDatapoint)


