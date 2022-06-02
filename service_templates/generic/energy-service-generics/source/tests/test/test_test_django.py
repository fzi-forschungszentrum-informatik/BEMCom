#!/usr/bin/env python3
"""
"""
import pytest


try:
    from django.core.exceptions import ValidationError

    from esg.test.django import GenericDjangoModelTemplateTest
    from esg.test.django import GenericDjangoModelTestMixin

    django_unavailable = False
except ModuleNotFoundError:

    class GenericDjangoModelTemplateTest:
        pass

    class GenericDjangoModelTestMixin:
        pass

    django_unavailable = True

from esg.models.datapoint import Datapoint as PydDatapoint
from esg.test import data as td


@pytest.mark.skipif(django_unavailable, reason="requires django")
class TestGenericDjangoModelTemplateTest(
    GenericDjangoModelTemplateTest, GenericDjangoModelTestMixin
):
    """
    Test both `GenericDjangoModelTest` and `GenericDjangoModelTemplateTest`
    can be used as expected.
    """

    model_name = "Datapoint"
    # Take care to pick a datapoint with id set here.
    # Else set an id in `prepare_messages`.
    msgs_as_python = [td.datapoints[1]["Python"]]
    msgs_as_jsonable = [td.datapoints[1]["JSONable"]]
    invalid_msgs_as_python = [{}]

    @classmethod
    def define_models(cls):
        """
        This is the intended way of creating a temporary django model.
        """
        from esg.django_models.datapoint import DatapointTemplate

        class Datapoint(DatapointTemplate):
            pydantic_model = PydDatapoint

            class Meta:
                app_label = cls.__name__

        return [Datapoint]

    def test_model_created_and_accessible(self):
        """
        If the template and especially `define_models` work as expected then
        we should now able to save a datapoint.
        """
        dp = self.Datapoint(type="Sensor")
        dp.save()

        assert self.Datapoint.objects.count() == 1

    def test_objects_deleted_after_test(self):
        """
        Verify stuff is deleted after every test. Assumes this test runs in
        order after `test_model_created_and_accessible`, which may not always
        be the case.
        """
        assert self.Datapoint.objects.count() == 0

    def test_generic_test_method_works(self):
        """
        We expect the class to have the method
        `test_valid_data_can_be_stored_and_retrieved`. If that is the case
        this method should also be executed by pytest.
        """
        assert hasattr(self, "test_valid_data_can_be_stored_and_retrieved")
        assert hasattr(self, "test_invalid_data_raises_validation_error")
