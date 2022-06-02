#!/usr/bin/env python3
"""
Tools for implementing Tests for django stuff.
"""
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
import pytest

# Setup a minimal and temporary fake django instance
try:
    settings.configure(
        **{
            "INSTALLED_APPS": [],
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    # Use in memory SQLite.
                    "NAME": ":memory:",
                }
            },
            "USE_TZ": True,
        }
    )
    apps.populate(settings.INSTALLED_APPS)
except RuntimeError:
    pass


class GenericDjangoModelTestMixin:
    """
    Generic tests for django models.

    This is intended to use the data defined in `esg.test.data`
    and operates similar to the tests in `esg.tests.generic_tests`.

    Attributes:
    -----------
    model_name: str
        The name of the model that should be tested. We assume it is
        available via `getattr(self, self.model_name)`.
    msgs_as_python : list of anything.
        The Python representation of the valid examples as defined
        in `testdata`.
    invalid_msgs_as_python : list of anything.
        The Python representation of the invalid examples as defined
        in `testdata`.
    """

    model_name = None
    msgs_as_python = None
    msgs_as_jsonable = None
    invalid_msgs_as_python = None

    def prepare_messages(self, msgs, msg_name=None):
        """
        This methods allows you to adapt the data, like to add foreign keys
        and stuff that are not present in the
        """
        return msgs

    def test_valid_data_can_be_stored_and_retrieved(self):
        """
        Check that a django model is capable of storing test data.
        """
        assert self.model_name is not None, "model_name not defined."
        assert self.msgs_as_python is not None, "msgs_as_python not defined."

        model = getattr(self, self.model_name)

        msgs_as_python = self.prepare_messages(
            self.msgs_as_python, "msgs_as_python"
        )
        msgs_as_jsonable = self.prepare_messages(
            self.msgs_as_jsonable, "msgs_as_jsonable"
        )
        msgs_zipped = zip(msgs_as_python, msgs_as_jsonable)
        for msg_as_python, msg_as_jsonable in msgs_zipped:
            try:
                pyd_obj = model.pydantic_model.construct_recursive(
                    **msg_as_python
                )
                obj = model()
                obj.save_from_pydantic(pyd_obj)

                # Check that the data can be restored from DB.
                obj.refresh_from_db()
                pyd_object_restored = obj.load_to_pydantic()

            except Exception:
                print(
                    "Error during hanlding save/restore for this object: {}"
                    "".format(msg_as_python)
                )
                raise

            expected_jsonable = msg_as_jsonable
            actual_jsonable = pyd_object_restored.jsonable()
            assert actual_jsonable == expected_jsonable

    def test_invalid_data_raises_validation_error(self):
        """
        Check that a django model is capable of storing test data.
        """
        assert self.model_name is not None, "model_name not defined."
        assert_msg = "invalid_msgs_as_python not defined."
        assert self.invalid_msgs_as_python is not None, assert_msg

        model = getattr(self, self.model_name)

        invalid_msgs_as_python = self.prepare_messages(
            self.invalid_msgs_as_python, "invalid_msgs_as_python"
        )
        for invalid_msg_as_python in invalid_msgs_as_python:
            with pytest.raises(ValidationError):
                obj = model(**invalid_msg_as_python)
                obj.clean()
                obj.save()

                # This print should only be executed if the test failed.
                print("Invalid msg that did not raise: ", invalid_msg_as_python)


class GenericDjangoModelTemplateTest(TestCase):
    """
    Generic tests for django models.

    This is useful because:
    * It makes testing templates for Django models (i.e. stuff residing in
      `esg.django_models`) easy.
    * It allows to test model templates with a faked django apps.
    """

    @classmethod
    def setup_class(cls):
        """
        Trigger creation of temporary models.
        """

        cls.models = cls.define_models()

        # Create temporary models in DB.
        with connection.schema_editor() as schema_editor:
            for model in cls.models:
                schema_editor.create_model(model)

        # Expose models, so tests can access via e.g. `self.Datapoint`
        for model in cls.models:
            setattr(cls, model.__name__, model)

    @classmethod
    def define_models(cls):
        """
        Define all temporary models.

        All models must be imported in this method. Afterwards you may
        create any temporary model from template that is required to run
        the tests. Place any model in cls.models afterwards.

        Should return:
        --------------
        models: list of django models.
            All temporary models created by this method.

        Example:
        --------
        from esg.django_models.datapoint import DatapointTemplate

        class Datapoint(DatapointTemplate):
            class Meta:
                app_label = cls.__name__

        return [Datapoint]
        """
        raise NotImplementedError("`define_models` must be overloaded.")

    @classmethod
    def teardown_class(cls):
        """
        Remove all temporarly created models.
        """
        with connection.schema_editor() as schema_editor:
            for model in cls.models:
                schema_editor.delete_model(model)

    def teardown_method(self, method):
        """
        Delete all objects after each test to prevent issues with unique
        constraints and similar side effects.
        """
        for model in self.models:
            model.objects.all().delete()
