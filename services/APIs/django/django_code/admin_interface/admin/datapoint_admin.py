from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from ..models.datapoint import Datapoint


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
        readonly_fields = [f.name for f in model_fields if f.editable is False]

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
        """
        Flag all selected datapoints as not used.

        It is important that this method does not call queryset.update(..)
        as the Datapoint save method would not be called, and also the signal
        would not be emitted. This leads to the situation where the Datapoint
        Addition entries are not  matching the datapoints and that no
        datapoint_map is sent to the connector
        """
        for datapoint in queryset:
            datapoint.use_as = "not used"
            datapoint.save()
    mark_not_used.short_description = (
        "Mark selected datapoints as not used"
    )

    def mark_numeric(self, request, queryset):
        """
        Flag all selected datapoints as numeric.

        See mark_not_used.
        """
        for datapoint in queryset:
            datapoint.use_as = "numeric"
            datapoint.save()
    mark_numeric.short_description = (
        "Mark selected datapoints as numeric"
    )

    def mark_text(self, request, queryset):
        """
        Flag all selected datapoints as text.

        See mark_not_used.
        """
        for datapoint in queryset:
            datapoint.use_as = "text"
            datapoint.save()
    mark_text.short_description = (
        "Mark selected datapoints as text"
    )

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False
