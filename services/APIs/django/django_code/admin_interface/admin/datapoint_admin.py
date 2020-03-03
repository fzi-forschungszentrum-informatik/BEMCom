import logging

from django import forms, db
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from ..models.datapoint import Datapoint

logger = logging.getLogger(__name__)


def create_datapoint_addition_inlines():
    """
    This creates StackedInline admin objects for all ModelAdditions known
    to datapoint. It is used by the DatapointAdmin.
    """
    datapoint_addition_inlines = {}
    data_format_addition_models = Datapoint.data_format_addition_models
    for data_format in data_format_addition_models.keys():

        # Get te model of the DatapointAddition
        ct_kwargs = data_format_addition_models[data_format]
        addition_type = ContentType.objects.get(**ct_kwargs)
        addition_model = addition_type.model_class()

        # Compute fields and readonly fields. Access to _meta following
        # https://docs.djangoproject.com/en/3.0/ref/models/meta/
        model_fields = addition_model._meta.get_fields()
        # datapoint is not relevant to display.
        fields = [f.name for f in model_fields if f.name != "datapoint"]

        # Define an order how the fields will be sorted from top to bottom
        # if the fields exist in the addition model.
        field_sorting_order = [
            "last_value",
            "last_timestamp",
            "unit",
            "min_value",
            "max_value",
            "allowed_values",
        ]
        fields_sorted = []
        for field in field_sorting_order:
            if field in fields:
                fields_sorted.append(field)
                fields.remove(field)
        fields_sorted.extend(fields)
        fields = fields_sorted
        fieldsets = (
            (None, {
                "fields": fields
            }),
        )

        # There might be more fields that must be set readonly.
        readonly_fields = [f.name for f in model_fields if f.editable is False]

        # Display Text Input for text field in Addition Models.
        formfield_overrides = {
            db.models.TextField: {
                'widget': forms.TextInput()
            },
        }

        # Now build the inline class based on the above and store it.
        class DatapointAdditionInline(admin.StackedInline):
            can_delete = False
            verbose_name_plural = "Additional metadata"
        DatapointAdditionInline.model = addition_model
        DatapointAdditionInline.fields = fields
        DatapointAdditionInline.fieldsets = fieldsets
        DatapointAdditionInline.readonly_fields = readonly_fields
        DatapointAdditionInline.formfield_overrides = formfield_overrides
        datapoint_addition_inlines[data_format] = DatapointAdditionInline

    return datapoint_addition_inlines


# This fails while creating the inital migrations as the django_content_type
# table does not exist yet.
try:
    datapoint_addition_inlines = create_datapoint_addition_inlines()
except Exception:
    logger.warning(
        "Could not load Inline Models for Datapoint Additions. The content"
        "of the Datapoint Additions may not be displayed correclty. "
        "Ignore this warning if initially executing makemigrations or "
        "migrating."
    )
    datapoint_addition_inlines = {}


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
        "example_value",
        "is_active",
        "data_format",
        "description"
    )
    list_display_links = (
        "key_in_connector",
    )
    list_editable = (
        "description",
    )
    list_filter = (
        "type",
        "connector",
        "data_format",
        "is_active",
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
                    "connector",
                    "key_in_connector",
                    "type",
                    "example_value",
                    "is_active",
                    "data_format",
                    "description",
                )
            }),
    )
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
        queryset.update(is_active=True)
    mark_active.short_description = "Mark datapoints as active"

    def mark_not_active(self, request, queryset):
        queryset.update(is_active=False)
    mark_not_active.short_description = "Mark datapoints as not active"

    def mark_data_format_as_generic_text(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "generic_text"
            datapoint.save()
    mark_data_format_as_generic_text.short_description = (
        "Mark data_format of datapoints as generic_text"
    )

    def mark_data_format_as_discrete_text(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "discrete_text"
            datapoint.save()
    mark_data_format_as_discrete_text.short_description = (
        "Mark data_format of datapoints as discrete_text"
    )

    def mark_data_format_as_generic_numeric(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "generic_numeric"
            datapoint.save()
    mark_data_format_as_generic_numeric.short_description = (
        "Mark data_format of datapoints as generic_numeric"
    )

    def mark_data_format_as_discrete_numeric(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "discrete_numeric"
            datapoint.save()
    mark_data_format_as_discrete_numeric.short_description = (
        "Mark data_format of datapoints as discrete_numeric"
    )

    def mark_data_format_as_continuous_numeric(self, request, queryset):
        for datapoint in queryset:
            datapoint.data_format = "continuous_numeric"
            datapoint.save()
    mark_data_format_as_continuous_numeric.short_description = (
        "Mark data_format of datapoints as continuous_numeric"
    )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        Dynamically display the according DatapointAdditionInline based on
        `data_format`
        """
        data_format = Datapoint.objects.get(id=object_id).data_format
        if data_format not in datapoint_addition_inlines:
            self.inlines = ()
        else:
            DatapointAdditionInline = datapoint_addition_inlines[data_format]
            self.inlines = (DatapointAdditionInline, )
        return super().change_view(request, object_id)

    @staticmethod
    def connector(obj):
        return obj.connector.name

    def has_add_permission(cls, request):
        """
        Remove `add` and `save and add another` button.
        """
        return False

    def has_delete_permission(cls, *args, **kwargs):
        """
        Remove `delete` button, the deleted datapoints
        """
        return False
