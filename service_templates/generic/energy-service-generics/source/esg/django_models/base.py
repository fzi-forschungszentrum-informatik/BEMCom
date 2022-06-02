#!/usr/bin/env python3
"""
Provides the DjangoBaseModel class which other django models should be derived
from to get nice benefits.
"""
import logging

from django.core.exceptions import ValidationError
from django.db import models
from pydantic import ValidationError as PydanticValidationError

from esg.services.base import RequestInducedException


logger = logging.getLogger(__name__)


class DjangoBaseModel(models.Model):
    """
    Generic useful stuff that every Django model should have.

    Note: No direct tests for this bad boy. However, every Model
          using `esg.test.django.GenericDjangoModelTestMixin` uses
          all of these methods here.
    """

    class Meta:
        abstract = True

    pydantic_model = None

    def clean(self):
        """
        Automatic check the model fields -> for Django Admin!

        Seems like the only generic way of using the pydantic models for
        validation right now is to convert the data to jsonable and then
        parse it back. In any other case Pydantic will complain about
        JSON fields not being strs because parsed allready.
        """
        assert_error = (
            "cannot clean as `{}.pydantic_model` is not defined"
            "".format(type(self).__name__)
        )
        assert self.pydantic_model is not None, assert_error

        obj_as_dict = self.load_to_dict()
        try:
            obj_as_pydantic = self.pydantic_model.construct_recursive(
                **obj_as_dict
            )
            obj_as_jsonable = obj_as_pydantic.jsonable()
        except Exception:
            # TODO: Improve this! Invalid data will raise random errors
            #       which crash the the calls to `construct_recursive`.
            #       However, this reports an unknown error while chances
            #       high that this message might have caused a more
            #       expressive error.
            emsg = (
                "Validation Error with unknown reason. There should be "
                "logged exception in the logs."
            )
            logger.exception(emsg)
            raise ValidationError(emsg)
        try:
            _ = self.pydantic_model(**obj_as_jsonable)
        except PydanticValidationError as validation_error:
            raise ValidationError(str(validation_error))

    def save_from_pydantic(self, pydantic_instance):
        """
        Save an object including nested models from pydantic model.

        Arguments:
        ----------
        pydantic_instance : pydantic model instance
            The pydantic version of the data that should be stored.
        """
        local_fields = [f.name for f in self._meta.fields]
        related_or_nonexisting_fields = {}
        for field_name, field_value in pydantic_instance:
            if field_name in local_fields:
                setattr(self, field_name, field_value)
            else:
                related_or_nonexisting_fields[field_name] = field_value

        # Finally, save the data.
        self.save()

        for field_name, field_value in related_or_nonexisting_fields.items():
            setattr(self, field_name, field_value)

        self.save()

    def get_related_model(self, related_name):
        """
        Fetch the related model.

        Use the django default procedure if possible and fall back to
        the customized solution if we test models outside applications.

        Arguments:
        -----------
        related_name : str
            This is the related name defined in the child model, with which
            the parent model can access the child.
            E.g. `_geographic_position` for the following relation field:
                plant = models.OneToOneField(
                    Plant,
                    related_name="_geographic_position",
                )

        Returns:
        --------
        related_model: django.db.models.Model like
            The model matching the field

        Raises:
        -------
        ValueError:
            If no model for the related name could be found.

        """
        if related_name in self._meta.fields_map:
            # This is the default way that uses django relation
            # system.
            relation = self._meta.fields_map[related_name]
            related_model = relation.related_model
        else:
            # However, if testing outside a django app (like in esg)
            # the lookup above is not possible, probably because the
            # mock app init in the test class is not sufficient.
            if (
                hasattr(self, "_related_name_to_model")
                and related_name in self._related_name_to_model
            ):
                related_model = self._related_name_to_model[related_name]
            else:
                emsg = (
                    "If this error has been raised from within a "
                    "django app check if `related_name` argument ({}) "
                    "matches the value of `related_name` of the related model. "
                    "If this error has been raised from outside a django "
                    "app please add the related model manually to "
                    '`{}._related_name_to_model["{}"]`'.format(
                        related_name, self._meta.label, related_name,
                    )
                )
                raise ValueError(emsg)

        return related_model

    def store_pydantic_instance_in_related_obj(
        self, related_name, field_name_parent_reference, pydantic_instance,
    ):
        """
        Stores the content of a pydantic instance in a related model.

        See `esg.django_models.PlantTemplate` for an example how to use a
        setter to invoke this method.

        Arguments:
        -----------
        related_name : str
            This is the related name defined in the child model, with which
            the parent model can access the child.
            E.g. `_geographic_position` for the following relation field:
                plant = models.OneToOneField(
                    Plant,
                    related_name="_geographic_position",
                )
        field_name_parent_reference : str
            This is the field of the child model that references the parent.
            In the exmample above it would be plant.
        pydantic_instance : pydantic model instance
            The pydantic version of the data that should be stored.

        """

        if hasattr(self, related_name):
            # If a related object exists already we can just update ...
            related_obj = getattr(self, related_name)
            if pydantic_instance is None:
                # .. but not if the new item is None, that means we
                # delete the related object to prevent orphans.
                related_obj.delete()
            else:
                related_obj.save_from_pydantic(pydantic_instance)
        else:
            # If the related object doesn't exist yet, we create well
            # at least if the new item contains data.
            if pydantic_instance is None:
                # Nothing to do here, no related object exist and no one
                # should exist.
                pass
            else:
                # Fetch the django model of the related item in order to
                # create a new obj.
                related_model = self.get_related_model(
                    related_name=related_name
                )

                # Now we have the model, create a new item and store the
                # payload.
                related_obj = related_model(
                    **{field_name_parent_reference: self}
                )
                related_obj.save_from_pydantic(pydantic_instance)

    def set_fk_obj_by_id(self, id, related_model):
        if id is None:
            return None

        try:
            return related_model.objects.get(id=id)
        except related_model.DoesNotExist:
            # This Exception is request related and does usually
            # not belong in the model. However, it is much simpler
            # to raise here, then to reconstruct the reason later.
            print(related_model.objects.all())
            raise RequestInducedException(
                detail=(
                    "Cannot link {} to {}, no "
                    "{} object with id {}.".format(
                        self.__class__.__name__,
                        related_model.__name__,
                        related_model.__name__,
                        id,
                    )
                )
            )

    def get_fk_id_from_field(self, field):
        if field is None:
            return None
        else:
            return getattr(field, "id")

    def load_to_dict(self):
        """
        Loads the content of the object into a dict.

        This method has an advantage over `django.forms.models.model_to_dict`
        that it only returns field values that are actually expected by the
        corresponding pydantic model. This removes the burden of removing
        unexpected fields (like e.g. often ID) through validation and allows
        faster construction of JSON responses.

        Note that for this work, curret model and all child models must define
        `pydantic_model` too.

        Returns:
        --------
        obj_as_dict : dict
            The data requested by the pydantic models as potentially nested
            dict structure.
        """
        obj_as_dict = {}

        for field_name in self.pydantic_model.__fields__.keys():
            obj_as_dict[field_name] = getattr(self, field_name)

        return obj_as_dict

    def load_to_pydantic(self):
        """
        Loads all data into pydanitc model defined in `self.pydantic_model`

        Note that for this work, curret model and all child models must define
        `pydantic_model` too.

        Returns:
        --------
        obj_as_pydantic : instance of self.pydantic_model
            Instance of pydantic model with fields populated from django
            object.
        """
        obj_as_dict = self.load_to_dict()

        obj_as_pydantic = self.pydantic_model.construct_recursive(**obj_as_dict)

        return obj_as_pydantic

    def load_dict_from_related_obj(self, related_name):
        """
        Loads the content of a related obj into a dict.

        This is method is usually invoked via a `@property` (See example in
        `esg.django_models.PlantTemplate`) during a `load_to_pydantic` call.

        This method has an advantage over `django.forms.models.model_to_dict`
        that it only returns field values that are actually expected by the
        corresponding pydantic model. This removes the burden of removing
        unexpected fields (like e.g. often ID) through validation and allows
        faster construction of JSON responses.
        """
        if not hasattr(self, related_name):
            return None
        else:
            related_obj = getattr(self, related_name)

            assert_error = (
                "Method `load_dict_from_related_obj` requires that model `{}` "
                "defines the corresponding pydantic model in field "
                "`pydantic_model`."
                "".format(related_obj._meta.label)
            )
            assert hasattr(related_obj, "pydantic_model"), assert_error

            pydantic_model = related_obj.pydantic_model

            obj_as_dict = {}
            for field_name in pydantic_model.__fields__.keys():
                field_value = getattr(related_obj, field_name)
                obj_as_dict[field_name] = field_value

            return obj_as_dict
