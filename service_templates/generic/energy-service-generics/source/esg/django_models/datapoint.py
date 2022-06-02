#!/usr/bin/env python3
"""
The django models corresponding to esg.models.datapoint
"""
import json
from datetime import datetime

from django.db import models

from timescale.db.models.managers import TimescaleManager
from timescale.db.models.fields import TimescaleDateTimeField

from esg.django_models.base import DjangoBaseModel
from esg.django_models.metadata import ProductRunTemplate
from esg.models.datapoint import Datapoint
from esg.models.datapoint import DatapointType
from esg.models.datapoint import DatapointDataFormat
from esg.models.datapoint import _Value
from esg.models.datapoint import _Time
from esg.models.datapoint import ValueMessage
from esg.models.datapoint import Schedule
from esg.models.datapoint import ScheduleMessage
from esg.models.datapoint import Setpoint
from esg.models.datapoint import SetpointMessage
from esg.models.datapoint import ForecastMessage


class DatapointTemplate(DjangoBaseModel):
    """
    Devices are abstracted as a set of datapoints.

    A datapoint represents one source of information. Devices will typically
    emit information on more then one datapoints. E.g. climate sensor in a
    room might publish temperature and humidity measurements. Both will be
    treated as individual datapoints as this allows us to abstract away the
    complexity of the devices.

    Each datapoint object contains the metadata necessary to interpret
    the datapoint.
    """

    pydantic_model = Datapoint

    class Meta:
        abstract = True
        constraints = [
            # GOTCHA: This must be copy/pasted to the derived datapoint.
            # Prevents that a datapoint can be accidently added multiple times
            models.UniqueConstraint(
                fields=["origin", "origin_id"],
                name="Datapoint unique for origin and origin_id",
            )
        ]

    origin = models.TextField(
        null=Datapoint.__fields__["origin"].allow_none,
        default=Datapoint.__fields__["origin"].default,
        blank=True,  # blank is matched to `None` on save.
        help_text=Datapoint.__fields__["origin"].field_info.description,
    )
    origin_id = models.TextField(
        null=Datapoint.__fields__["origin_id"].allow_none,
        default=Datapoint.__fields__["origin_id"].default,
        blank=True,  # blank is matched to `None` on save.
        help_text=Datapoint.__fields__["origin_id"].field_info.description,
    )
    short_name = models.TextField(
        # Auto generated datapoints will be stored as null.
        null=Datapoint.__fields__["short_name"].allow_none,
        default=Datapoint.__fields__["short_name"].default,
        blank=True,
        help_text=Datapoint.__fields__["short_name"].field_info.description,
    )
    type = models.CharField(
        max_length=8,
        # This combination of `default` and `will` make any Datapoint fail
        # for which type has not specified explicitly. (On purpose!)
        default=None,
        null=False,
        choices=[(i.value, i.value) for i in DatapointType],
        help_text=Datapoint.__fields__["type"].field_info.description,
    )
    data_format = models.CharField(
        max_length=18,
        choices=[(i.value, i.value) for i in DatapointDataFormat],
        null=Datapoint.__fields__["data_format"].allow_none,
        default=Datapoint.__fields__["data_format"].default,
        help_text=Datapoint.__fields__["data_format"].field_info.description,
    )
    # Don't limit this, people should never need to use abbreviations or
    # shorten their thoughts just b/c the field is too short.
    description = models.TextField(
        editable=True,
        blank=True,
        null=Datapoint.__fields__["description"].allow_none,
        default=Datapoint.__fields__["description"].default,
        help_text=Datapoint.__fields__["description"].field_info.description,
    )
    #
    ##########################################################################
    #
    # Below all metadata fields that may or may not be populated for a
    # particular datapoint depending on the data_format and type.
    #
    ##########################################################################
    #
    allowed_values = models.JSONField(
        blank=True,
        null=Datapoint.__fields__["allowed_values"].allow_none,
        default=Datapoint.__fields__["allowed_values"].default,
        help_text=Datapoint.__fields__["allowed_values"].field_info.description,
    )
    min_value = models.FloatField(
        blank=True,
        null=Datapoint.__fields__["min_value"].allow_none,
        default=Datapoint.__fields__["min_value"].default,
        help_text=Datapoint.__fields__["min_value"].field_info.description,
    )
    max_value = models.FloatField(
        blank=True,
        null=Datapoint.__fields__["max_value"].allow_none,
        default=Datapoint.__fields__["max_value"].default,
        help_text=Datapoint.__fields__["max_value"].field_info.description,
    )
    unit = models.TextField(
        editable=True,
        blank=True,
        null=Datapoint.__fields__["unit"].allow_none,
        default=Datapoint.__fields__["unit"].default,
        help_text=Datapoint.__fields__["unit"].field_info.description,
    )

    def save(self, *args, **kwargs):
        """
        Replace an empty string in origin_id with None (which cannot be
        entered directly in the admin), as every None is unique while
        an empty string violates the unique constraint. However, we want
        external id only to be unique if it is set.
        """
        if self.origin == "":
            self.origin = None
        if self.origin_id == "":
            self.origin_id = None
        super().save(*args, **kwargs)

    def __str__(self):
        if self.short_name is not None:
            return str(self.id) + " - " + self.short_name
        else:
            return str(self.id)


class TimescaleModel(DjangoBaseModel):
    """
    A helper class for using Timescale within Django, has the TimescaleManager
    and TimescaleDateTimeField already present. This is an abstract class it
    should be inheritted by another class for use.
    """

    class Meta:
        abstract = True

    objects = models.Manager()
    timescale = TimescaleManager()

    time = TimescaleDateTimeField(
        interval="1 day",
        blank=False,
        default=None,  # Prevents messages created without data.
        null=_Time.__fields__["__root__"].allow_none,
        help_text=_Time.__fields__["__root__"].field_info.description,
    )

    @staticmethod
    def bulk_update_or_create(model, msgs):
        """
        Create or update value/setpoint/schedule messages efficiently in bulks.

        This will not send any signals as this function will likely
        be used only to restore backups.

        Arguments:
        ----------
        model : django Model
            The model for which the data should be written to.
        msgs : list of dict
            Each dict containting the fields (as keys) and desired values
            that should be stored for one object in the DB.

        Returns:
        --------
        msgs_created : int
            The number of messages that have been created.
        msgs_updated : int
            The number of messages that have been updated.
        """
        # Start with searching for msgs that exist already with the same
        # combination of timestamp and datapoint in the database.
        # These messages will be updated.
        msgs_by_datapoint = {}
        msgs_to_create = []
        msgs_updated = 0
        for msg in msgs:
            datapoint = msg["datapoint"]
            if datapoint not in msgs_by_datapoint:
                msgs_by_datapoint[datapoint] = []
            msgs_by_datapoint[datapoint].append(msg)
        for datapoint in msgs_by_datapoint:
            msgs_current_dp = msgs_by_datapoint[datapoint]
            msgs_c_dp_by_time = {msg["time"]: msg for msg in msgs_current_dp}
            existing_msg_objects = model.objects.filter(
                datapoint=datapoint, time__in=msgs_c_dp_by_time.keys()
            )

            # Now start with updating the existing messages by updating
            # the corresponding fields.
            fields_to_update = set()
            for existing_msg_object in existing_msg_objects:
                # The messages remaining in msgs_c_dp_by_time after the loop
                # are those we need to create.
                new_msg = msgs_c_dp_by_time.pop(existing_msg_object.time)
                for field in new_msg:
                    if field == "datapoint" or field == "time":
                        # These have been used to find the message and must thus
                        # not be updated.
                        continue
                    fields_to_update.add(field)
                    setattr(existing_msg_object, field, new_msg[field])

            # Without this if we will get an error like this downstream:
            # ValueError: Field names must be given to bulk_update().
            if existing_msg_objects:
                # Now let's push those updates back to DB. Use bulks of 1000
                # to prevent the SQL query from becoming too large. See:
                # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#bulk-update
                model.objects.bulk_update(
                    objs=existing_msg_objects,
                    fields=fields_to_update,
                    batch_size=1000,
                )
                msgs_updated += len(existing_msg_objects)

            msgs_to_create.extend(msgs_c_dp_by_time.values())

        # Now that we have updated the existing messages and know which ones
        # are left to create let's to this too.
        objs_to_create = [model(**msg) for msg in msgs_to_create]
        model.objects.bulk_create(objs=objs_to_create, batch_size=1000)
        msgs_created = len(objs_to_create)

        return msgs_created, msgs_updated


class LastMessageModel(DjangoBaseModel):
    """
    Mixin provides the `bulk_update_or_create` to last message models.
    """

    class Meta:
        abstract = True

    @staticmethod
    def bulk_update_or_create(model, msgs):
        """
        Create or update value/setpoint/schedule messages efficiently in bulks.

        This will not send any signals as this function will likely
        be used only to restore backups.

        Arguments:
        ----------
        model : django Model
            The model for which the data should be written to.
        msgs : list of dict
            Each dict containting the fields (as keys) and desired values
            that should be stored for one object in the DB.

        Returns:
        --------
        msgs_created : int
            The number of messages that have been created.
        msgs_updated : int
            The number of messages that have been updated.
        """
        # Start with searching for msgs that exist already with the same
        # combination of timestamp and datapoint in the database.
        # These messages will be updated.
        msgs_by_datapoint = {}
        msgs_updated = 0

        for msg in msgs:
            msgs_by_datapoint[msg["datapoint"]] = msg

        existing_msg_objects = model.objects.filter(
            datapoint__in=msgs_by_datapoint.keys(),
        )

        # Now start with updating the existing messages by updating
        # the corresponding fields.
        fields_to_update = set()
        for existing_msg_object in existing_msg_objects:
            # The messages remaining in msgs_by_datapoint after the loop
            # are those we need to create.
            new_msg = msgs_by_datapoint.pop(existing_msg_object.datapoint)
            for field in new_msg:
                if field == "datapoint":
                    # These have been used to find the message and must thus
                    # not be updated.
                    continue
                fields_to_update.add(field)
                setattr(existing_msg_object, field, new_msg[field])

        # Without this if we will get an error like this downstream:
        # ValueError: Field names must be given to bulk_update().
        if existing_msg_objects:
            # Now let's push those updates back to DB. Use bulks of 1000
            # to prevent the SQL query from becoming too large. See:
            # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#bulk-update
            model.objects.bulk_update(
                objs=existing_msg_objects,
                fields=fields_to_update,
                batch_size=1000,
            )
            msgs_updated += len(existing_msg_objects)

        msgs_to_create = msgs_by_datapoint.values()

        # Now that we have updated the existing messages and know which ones
        # are left to create let's to this too.
        objs_to_create = [model(**msg) for msg in msgs_to_create]
        model.objects.bulk_create(objs=objs_to_create, batch_size=1000)
        msgs_created = len(objs_to_create)

        return msgs_created, msgs_updated


class ValueMessageTemplate(TimescaleModel):
    """
    Django representation of `esg.models.datapoint.ValueMessage` for
    storing these messages in DB. Subclass to use.
    """

    pydantic_model = ValueMessage

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "time"],
                name="Value msg unique for timestamp",
            )
        ]

    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="value_messages",
        help_text=("The datapoint that the value message belongs to."),
    )
    # JSON should be able to store everything as the messages arive
    # packed in a JSON string.
    value = models.JSONField(
        blank=True,
        default=None,
        null=_Value.__fields__["__root__"].allow_none,
        help_text=_Value.__fields__["__root__"].field_info.description,
    )
    _value_float = models.FloatField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Similar to value but an internal float representation "
            "to store numeric values more efficiently."
        ),
    )
    _value_bool = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Similar to value but an internal bool representation "
            "to store boolean values more efficiently."
        ),
    )

    def save(self, *args, **kwargs):
        """
        Check if the value can be stored as float or bool to save storage
        space.
        """
        # Store the value in the corresponding column.
        original_value = self.value
        if isinstance(self.value, bool):
            self._value_bool = self.value
            # PGSQL should be able to store the null rather efficiently.
            self.value = None
        elif self.value is not None:
            try:
                value_float = float(self.value)
                parsable = True
            except ValueError:
                parsable = False

            if parsable:
                self._value_float = value_float
                self.value = None
        super().save(*args, **kwargs)

        # Restore the original values, for any code that continous to work with
        # the object.
        self.value = original_value
        self._value_bool = None
        self._value_float = None

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        Undo stuff done on `save`.
        """
        instance = super().from_db(db, field_names, values)
        if instance._value_float is not None:
            instance.value = instance._value_float
            instance._value_float = None
        elif instance._value_bool is not None:
            instance.value = instance._value_bool
            instance._value_bool = None
        return instance

    @staticmethod
    def bulk_update_or_create(model, msgs):
        """
        Extend the version of TimescaleModel with special handling for the
        float and bool hidden fields.

        Arguments:
        ----------
        model : django Model
            The model for which the data should be written to.
        msgs : list of dict
            Each dict containting the fields (as keys) and desired values
            that should be stored for one object in the DB.

        Returns:
        --------
        msgs_created : int
            The number of messages that have been created.
        msgs_updated : int
            The number of messages that have been updated.
        """
        for msg in msgs:
            original_value = msg["value"]
            msg["value"] = None

            if isinstance(original_value, bool):
                msg["_value_bool"] = original_value
            elif original_value is not None:
                try:
                    msg["_value_float"] = float(original_value)
                except ValueError:
                    msg["value"] = original_value

        return TimescaleModel.bulk_update_or_create(model=model, msgs=msgs)


class LastValueMessageTemplate(LastMessageModel):
    """
    Intended model to store the last value message of a datapoint.

    Subclass to use. Take care to take over the `OneToOneField` as it ensures
    that only one message can be stored per datapoint.
    """

    pydantic_model = ValueMessage

    class Meta:
        abstract = True

    datapoint = models.OneToOneField(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="last_value_message",
        help_text=("The datapoint that the value message belongs to."),
    )
    # Note that value and time must be nullable and have a default value
    # to allow any script that handles incoming data the fetch these
    # get_or_create in cache style fashion.
    value = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text=("The payload of the last received value message."),
    )
    time = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=("The timestamp of the last received value message."),
    )


class ScheduleSetpointJSONEncoder(json.JSONEncoder):
    """
    Encode datetime fields to ISO string.

    Note: This class is tested by the `test_example_data_can_be_stored` methods
    in `TestSetpointMessage` and `TestScheduleMessage`.
    """

    def encode(self, o):
        if o is None:
            # relevant edge case for Last.+Message objects, as these are
            # initialized with None, to differentiate from an empty message.
            jsonable = None
        else:
            jsonable = []
            for in_item in o:
                out_item = {}
                for field in in_item:
                    if isinstance(in_item[field], datetime):
                        out_item[field] = in_item[field].isoformat()
                    else:
                        out_item[field] = in_item[field]
                jsonable.append(out_item)
        encoded = json.dumps(jsonable)
        return encoded


class ScheduleSetpointJSONDecoder(json.JSONDecoder):
    """
    Reconstruct the Python object by inflating the datetime objects.
    """

    def decode(self, s):
        dt_fields = ["from_timestamp", "to_timestamp"]
        decoded_in = json.loads(s)
        if decoded_in is None:
            # relevant edge case for Last.+Message objects, as these are
            # initialized with None, to differentiate from an empty message.
            decoded = decoded_in
        else:
            decoded = []
            for in_item in json.loads(s):
                out_item = {}
                for field in in_item:
                    if field in dt_fields and in_item[field] is not None:
                        out_item[field] = datetime.fromisoformat(in_item[field])
                    else:
                        out_item[field] = in_item[field]
                decoded.append(out_item)
        return decoded


class ScheduleMessageTemplate(TimescaleModel):
    """
    Django representation of `esg.models.datapoint.ScheduleMessage` for
    storing these messages in DB. Subclass to use.
    """

    pydantic_model = ScheduleMessage

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "time"],
                name="Schedule msg unique for timestamp",
            )
        ]

    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="schedule_messages",
        help_text=("The datapoint that the schedule message belongs to."),
    )
    schedule = models.JSONField(
        blank=False,
        default=None,
        encoder=ScheduleSetpointJSONEncoder,
        decoder=ScheduleSetpointJSONDecoder,
        null=Schedule.__fields__["__root__"].allow_none,
        help_text=Schedule.__doc__.strip(),
    )


class LastScheduleMessageTemplate(LastMessageModel):
    """
    Intended model to store the last schedule message of a datapoint.

    Subclass to use. Take care to take over the `OneToOneField` as it ensures
    that only one message can be stored per datapoint.
    """

    pydantic_model = ScheduleMessage

    class Meta:
        abstract = True

    datapoint = models.OneToOneField(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="last_schedule_message",
        help_text=("The datapoint that the schedule message belongs to."),
    )
    # Note that schedule and time must be nullable and have a default value
    # to allow any script that handles incoming data the fetch these
    # get_or_create in cache style fashion.
    schedule = models.JSONField(
        null=True,
        blank=True,
        default=None,
        encoder=ScheduleSetpointJSONEncoder,
        decoder=ScheduleSetpointJSONDecoder,
        help_text=("The payload of the last received schedule message."),
    )
    time = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=("The timestamp of the last received schedule message."),
    )


class SetpointMessageTemplate(TimescaleModel):
    """
    Django representation of `esg.models.datapoint.SetpointMessage` for
    storing these messages in DB. Subclass to use.
    """

    pydantic_model = SetpointMessage

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "time"],
                name="Setpoint msg unique for timestamp",
            )
        ]

    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="setpoint_messages",
        help_text=("The datapoint that the setpoint message belongs to."),
    )
    setpoint = models.JSONField(
        blank=True,
        default=list,
        encoder=ScheduleSetpointJSONEncoder,
        decoder=ScheduleSetpointJSONDecoder,
        null=Setpoint.__fields__["__root__"].allow_none,
        help_text=Setpoint.__doc__.strip(),
    )


class LastSetpointMessageTemplate(LastMessageModel):
    """
    Intended model to store the last setpoint message of a datapoint.

    Subclass to use. Take care to take over the `OneToOneField` as it ensures
    that only one message can be stored per datapoint.
    """

    pydantic_model = SetpointMessage

    class Meta:
        abstract = True

    datapoint = models.OneToOneField(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="last_setpoint_message",
        help_text=("The datapoint that the setpoint message belongs to."),
    )
    # Note that setpoint and time must be nullable and have a default value
    # to allow any script that handles incoming data the fetch these
    # get_or_create in cache style fashion.
    setpoint = models.JSONField(
        null=True,
        blank=True,
        default=None,
        encoder=ScheduleSetpointJSONEncoder,
        decoder=ScheduleSetpointJSONDecoder,
        help_text=("The payload of the last received setpoint message."),
    )
    time = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=("The timestamp of the last received setpoint message."),
    )


class ForecastMessageTemplate(TimescaleModel):
    """
    Django representation of `esg.models.datapoint.ForecastMessage` for
    storing these messages in DB. Subclass to use.
    """

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "time", "product_run"],
                name="Forecast Message Unique.",
            )
        ]

    pydantic_model = ForecastMessage

    datapoint = models.ForeignKey(
        DatapointTemplate,
        on_delete=models.CASCADE,
        related_name="forecast_messages",
        help_text=("The datapoint that the forecast message belongs to."),
    )
    product_run = models.ForeignKey(
        ProductRunTemplate,
        on_delete=models.CASCADE,
        related_name="forecast_messages",
        help_text=("The product run that has generated the forecast message."),
    )
    mean = models.FloatField(
        blank=ForecastMessage.__fields__["mean"].allow_none,
        null=ForecastMessage.__fields__["mean"].allow_none,
        help_text=ForecastMessage.__fields__["mean"].field_info.description,
    )
    std = models.FloatField(
        blank=ForecastMessage.__fields__["std"].allow_none,
        null=ForecastMessage.__fields__["std"].allow_none,
        help_text=ForecastMessage.__fields__["std"].field_info.description,
    )
    p05 = models.FloatField(
        blank=ForecastMessage.__fields__["p05"].allow_none,
        null=ForecastMessage.__fields__["p05"].allow_none,
        help_text=ForecastMessage.__fields__["p05"].field_info.description,
    )
    p10 = models.FloatField(
        blank=ForecastMessage.__fields__["p10"].allow_none,
        null=ForecastMessage.__fields__["p10"].allow_none,
        help_text=ForecastMessage.__fields__["p10"].field_info.description,
    )
    p25 = models.FloatField(
        blank=ForecastMessage.__fields__["p25"].allow_none,
        null=ForecastMessage.__fields__["p25"].allow_none,
        help_text=ForecastMessage.__fields__["p25"].field_info.description,
    )
    p50 = models.FloatField(
        blank=ForecastMessage.__fields__["p50"].allow_none,
        null=ForecastMessage.__fields__["p50"].allow_none,
        help_text=ForecastMessage.__fields__["p50"].field_info.description,
    )
    p75 = models.FloatField(
        blank=ForecastMessage.__fields__["p75"].allow_none,
        null=ForecastMessage.__fields__["p75"].allow_none,
        help_text=ForecastMessage.__fields__["p75"].field_info.description,
    )
    p90 = models.FloatField(
        blank=ForecastMessage.__fields__["p90"].allow_none,
        null=ForecastMessage.__fields__["p90"].allow_none,
        help_text=ForecastMessage.__fields__["p90"].field_info.description,
    )
    p95 = models.FloatField(
        blank=ForecastMessage.__fields__["p95"].allow_none,
        null=ForecastMessage.__fields__["p95"].allow_none,
        help_text=ForecastMessage.__fields__["p95"].field_info.description,
    )

    @staticmethod
    def bulk_update_or_create(model, msgs):
        """
        Create or update value/setpoint/schedule messages efficiently in bulks.

        This will not send any signals as this function will likely
        be used only to restore backups.

        Arguments:
        ----------
        model : django Model
            The model for which the data should be written to.
        msgs : list of dict
            Each dict containting the fields (as keys) and desired values
            that should be stored for one object in the DB.

        Returns:
        --------
        msgs_created : int
            The number of messages that have been created.
        msgs_updated : int
            The number of messages that have been updated.
        """
        # Start with searching for msgs that exist already with the same
        # combination of timestamp and datapoint in the database.
        # These messages will be updated.
        msgs_by_fks = {}
        msgs_to_create = []
        msgs_updated = 0
        for msg in msgs:
            datapoint = msg["datapoint"]
            product_run = msg["product_run"]
            if (datapoint, product_run) not in msgs_by_fks:
                msgs_by_fks[(datapoint, product_run)] = []
            msgs_by_fks[(datapoint, product_run)].append(msg)
        for datapoint, product_run in msgs_by_fks:
            msgs_current_fks = msgs_by_fks[(datapoint, product_run)]
            msgs_c_fk_by_time = {msg["time"]: msg for msg in msgs_current_fks}
            existing_msg_objects = model.objects.filter(
                datapoint=datapoint,
                product_run=product_run,
                time__in=msgs_c_fk_by_time.keys(),
            )

            # Now start with updating the existing messages by updating
            # the corresponding fields.
            fields_to_update = set()
            for existing_msg_object in existing_msg_objects:
                # The messages remaining in msgs_c_dp_by_time after the loop
                # are those we need to create.
                new_msg = msgs_c_fk_by_time.pop(existing_msg_object.time)
                for field in new_msg:
                    if field in ["datapoint", "time", "product_run"]:
                        # These have been used to find the message and must thus
                        # not be updated.
                        continue
                    fields_to_update.add(field)
                    setattr(existing_msg_object, field, new_msg[field])

            # Without this if we will get an error like this downstream:
            # ValueError: Field names must be given to bulk_update().
            if existing_msg_objects:
                # Now let's push those updates back to DB. Use bulks of 1000
                # to prevent the SQL query from becoming too large. See:
                # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#bulk-update
                model.objects.bulk_update(
                    objs=existing_msg_objects,
                    fields=fields_to_update,
                    batch_size=1000,
                )
                msgs_updated += len(existing_msg_objects)

            msgs_to_create.extend(msgs_c_fk_by_time.values())

        # Now that we have updated the existing messages and know which ones
        # are left to create let's to this too.
        objs_to_create = [model(**msg) for msg in msgs_to_create]
        model.objects.bulk_create(objs=objs_to_create, batch_size=1000)
        msgs_created = len(objs_to_create)

        return msgs_created, msgs_updated
