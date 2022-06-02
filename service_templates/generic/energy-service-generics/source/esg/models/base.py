#!/usr/bin/env python3
"""
Provides the _BaseModel class which other models should be derived from.
"""
from datetime import datetime
import json
from typing import get_type_hints

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from pydantic import fields
from pydantic.main import ModelMetaclass


class _BaseModel(BaseModel):
    """
    This overloads the pydantic.BaseModel with a custom adapted version.

    The main motivation for this class is to allow automatic encoding of
    the `Value` fields to a JSON string. This is necessary to keep the
    REST-API reasonably lean while still putting as little as possible
    constraints of what can be transported as values. Furthermore we add
    some additional methods for interaction with BEMCom messages.

    ATTENTION
    ---------
    These adaptions (i.e. `jsonable()` and `construct_recursive()` have only
    been implemented and tested for the following model types:
    - Flat models (i.e. all fields carry singleton values like floats,
      strings or alike.
    - Direct nested models, i.e. where one field directly refers to
      another field.
    - Fields that carry lists of models.
    - Fields that carry lists of normal types.
    - Fields that carry dicts of models.
    - Fields that carry dicts of normal types.
    If you ask yourself what other types of fields exist, check here:
    https://github.com/samuelcolvin/pydantic/blob/master/pydantic/fields.py#L322
    """

    def jsonable(self, custom_json_encoders=None):
        """
        Create a dict representation of the model instance that be dumped
        directly with `json.dumps`. This makes use of this fastapi tool:
        https://fastapi.tiangolo.com/tutorial/encoder/#json-compatible-encoder

        Furthermore this method searches for fields of type `Json` and
        encodes the content of these to JSON as pydantic doesn't seem
        to do this.

        Note that this method might be rather slow as it sweeps over the
        model several times.

        Arguments:
        ----------
        custom_json_encoders : dict or None.
            If provided overloads the serialization of certain types
            of values. Note this is the actual type of the value not
            the type specified in the model. For example for a field
            `test : Json = 21.0` it will not work to have an entry
            for `Json`, but an entry for `float` would work.
            See the pydanitc docs for a practical example:
            https://pydantic-docs.helpmanual.io/usage/exporting_models/#json_encoders

        Returns:
        --------
        obj_as_jsonable : object
            A Python object that can be converted to JSON.
        """
        # Make a copy to not change the values for any other application
        # that uses the object afterwards.
        obj = self.copy()

        def encode_json_fields_to_strings(obj):

            if not isinstance(obj, BaseModel):
                # Don't go deeper if the current obj is just a field value
                # like a string or a float.
                return obj

            for field_name, field_type in get_type_hints(obj).items():
                field_value = getattr(obj, field_name)

                if (
                    hasattr(field_type, "__name__")
                    and field_type.__name__ == "Json"
                ):
                    field_value = json.dumps(field_value)

                elif isinstance(field_value, BaseModel):
                    # We want to recurse deeper into child models.
                    field_value = encode_json_fields_to_strings(field_value)

                # Also recurse deeper for lists.
                elif isinstance(field_value, list):
                    # .. but not if we have a list with direct values.
                    encoded_list = []
                    if field_type.__args__[0].__name__ == "Json":
                        for field_value_item in field_value:
                            encoded_list.append(json.dumps(field_value_item))
                    else:
                        # If the list contains a model, recursion is good.
                        for field_value_item in field_value:
                            encoded_list.append(
                                encode_json_fields_to_strings(field_value_item)
                            )
                    field_value = encoded_list

                # Also recurse deeper for fields that hold dicts.
                elif isinstance(field_value, dict):
                    encoded_dict = {}
                    for key, field_value_item in field_value.items():
                        encoded_dict[key] = encode_json_fields_to_strings(
                            field_value_item
                        )
                    field_value = encoded_dict

                setattr(obj, field_name, field_value)
            return obj

        obj = encode_json_fields_to_strings(obj)
        obj_as_jsonable = jsonable_encoder(
            obj, custom_encoder=custom_json_encoders
        )

        return obj_as_jsonable

    def jsonable_bemcom(self):
        """
        Like `jsonable()` but outputs the message in BEMCom format.

        The only difference here is that fields storing time values are
        named `timestamp` instead of `time` and that the values are encoded
        in a Unix Timestamp in milliseconds instead of a string.

        Returns:
        --------
        obj_as_jsonable : object
            A Python object that can be converted to JSON.
        """
        custom_json_encoders = {
            datetime: lambda dt: round(dt.timestamp() * 1000)
        }
        obj_as_jsonable = self.jsonable(
            custom_json_encoders=custom_json_encoders
        )

        if "time" in obj_as_jsonable:
            obj_as_jsonable["timestamp"] = obj_as_jsonable.pop("time")

        return obj_as_jsonable

    def json(self):
        """
        Overload the default version of pydantic to make use of jsonable.

        This might yield better performance but most importantly provides
        more control over the serializaton process.

        Returns:
        --------
        obj_as_json : string
            The object represented as JSON string.
        """
        return json.dumps(self.jsonable())

    def json_bemcom(self):
        """
        Like `json()` but outputs the message in BEMCom format.

        Returns:
        --------
        obj_as_json : string
            The object represented as JSON string.
        """
        return json.dumps(self.jsonable_bemcom())

    @classmethod
    def parse_obj_bemcom(cls, obj):
        """
        Like pydantics `parse_obj` but adapting the BEMCom message.

        The only important thing this does is to rename the fields carrying
        time values.

        Note that this function should be named `parse_dict_bemcom` as this
        is what it does, but we stick to pydantic naming convention.

        Arguments:
        ----------
        obj : dict
            A dictionary carrying the field_name, field_value pairs. See also:
            https://pydantic-docs.helpmanual.io/usage/models/#helper-functions

        Returns:
        --------
        obj : pydantic model object
            The parsed and validated model object.

        Raises:
        -------
        pydantic.error_wrappers.ValidationError:
            If anything goes wrong or the input is not a dict.
        """
        if isinstance(obj, dict):
            # Only handle dicts. For any other type parse_obj below will raise
            # pydantic.error_wrappers.ValidationError anyway.
            if "timestamp" in obj:
                obj["time"] = obj.pop("timestamp")

        return cls.parse_obj(obj)

    @classmethod
    def parse_raw_bemcom(cls, json_string):
        """
        Like pydantics `parse_raw` but adapting the BEMCom message.

        The only important thing this does is to rename the fields carrying
        time values.

        Arguments:
        ----------
        json_string : string
            A JSON string carrying the field_name, field_value pairs. See also:
            https://pydantic-docs.helpmanual.io/usage/models/#helper-functions

        Returns:
        --------
        obj : pydantic model object
            The parsed and validated model object.

        Raises:
        -------
        pydantic.error_wrappers.ValidationError:
            If anything goes wrong or the input is not a JSON string.
        """
        if isinstance(json_string, str):
            json_string = json_string.replace('"timestamp":', '"time":')

        return cls.parse_raw(json_string)

    @classmethod
    def construct_recursive(cls, **values):
        """
        Recursivly construct the object from data.

        A wrapper around the `construct` method of pydantic that automatically
        creates the child models (in contrast to the original `construct`
        method which doesn't do that). The intended way in pydantic would be
        to use cls.validate which creates all the submodels but at the price
        of running the full validation, which might be rather slow.

        ATTENTION:
        ----------
        Note that all submodels that should be created must provide a
        `construct_recursive` method too.

        Arguments:
        ----------
        values : dict
            A dictionary carrying the field_name, field_value pairs.

        Returns:
        --------
        obj : pydantic model object
            The UNVALIDATED model object.
        """

        # Handle fields depending on category (shape in pydantic terminology)
        # See the pydantic code for definitions of shape:
        # https://github.com/samuelcolvin/pydantic/blob/d7a8272d7e0c151b0bd43df596be02e0d436ebdf/pydantic/fields.py#L322
        for name, field in cls.__fields__.items():

            if name not in values:
                # These hits for fields for which no value was provided.
                continue

            if field.shape == fields.SHAPE_SINGLETON:
                # This is a field which holds a normal value, like a float
                # a string or a nested model.
                if isinstance(field.type_, ModelMetaclass):
                    # This should only be true for nested models.
                    child_cls = field.type_
                    if "__root__" in child_cls.__fields__:
                        # This means that the nested model has a custom
                        # root type. We hence give the payload to root of
                        # this model and hope that it can cope with it.
                        values[name] = child_cls.construct_recursive(
                            __root__=values[name]
                        )
                    else:
                        # OK, no custom root type. Hence this should be normal
                        # single model. This also means that `values[name]`
                        # must be a dict to make sense.
                        # However, the child model could also be set to None.
                        if values[name] is not None:
                            values[name] = child_cls.construct_recursive(
                                **values[name]
                            )
                continue

            elif field.shape == fields.SHAPE_LIST and values[name] is not None:
                # This is field that holds a list. For such we iterate over
                # the items and construct each of those incl. all children.
                # But only for non None values (List could be set to None too).
                child_objects = []
                child_cls = field.type_
                if hasattr(child_cls, "construct_recursive"):
                    # Only call `construct_recursive` if the children actually
                    # have this method. This takes care that we don't try
                    # to call `construct_recursive` on normal strings, floats
                    # and other conventional types.
                    if "__root__" in child_cls.__fields__:
                        # Like above, distinguish between models that have
                        # custom root and those that have not.
                        for list_item in values[name]:
                            child_objects.append(
                                child_cls.construct_recursive(
                                    __root__=list_item
                                )
                            )
                    else:
                        for list_item in values[name]:
                            child_objects.append(
                                child_cls.construct_recursive(**list_item)
                            )
                    values[name] = child_objects

            elif field.shape == fields.SHAPE_DICT and values[name] is not None:
                # This field holds a dictionary. Like for list, we iterate
                # over all children and construct for each of those.
                child_objects = {}
                child_cls = field.type_
                if hasattr(child_cls, "construct_recursive"):
                    if "__root__" in child_cls.__fields__:
                        # Like above, distinguish between models that have
                        # custom root and those that have not.
                        for key, item in values[name].items():
                            child_objects[key] = child_cls.construct_recursive(
                                __root__=item
                            )
                    else:
                        for key, item in values[name].items():
                            child_objects[key] = child_cls.construct_recursive(
                                **item
                            )
                    values[name] = child_objects

        obj = cls.construct(**values)
        return obj
