import sys
import logging

from django.conf import settings
from django.apps import AppConfig


logger = logging.getLogger(__name__)


class ApiMainConfig(AppConfig):
    name = "api_main"

    def ready(self):

        if "runserver" in sys.argv or "gunicorn" in sys.argv[0]:
            logger.info("Starting up the API main module.")

            # Report which database is used so people have a chance to
            # see that they may be using SQLite unintendedly.
            if "sqlite" in settings.DATABASES["default"]["ENGINE"]:
                logger.warning("Using SQLite as database.")
            else:
                logger.info("Using TimescaleDB.")

            from .mqtt_integration import ApiMqttIntegration

            try:
                ApiMqttIntegration()
            except ValueError:
                logger.critical("")
                logger.critical(
                    "Could not connect to MQTT broker of backend. Exiting"
                )
                logger.critical("")
                sys.exit(1)
