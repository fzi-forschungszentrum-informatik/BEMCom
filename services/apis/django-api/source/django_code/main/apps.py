import sys
import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        import main.signals

        if 'runserver' in sys.argv or "daphne" in sys.argv[0]:
            logger.info("Starting up the main module of the API & Admin UI.")
            from .connector_mqtt_integration import ConnectorMQTTIntegration
            try:
                ConnectorMQTTIntegration()
            except ConnectionRefusedError:
                logger.critical("")
                logger.critical(
                    "Could not connect to MQTT broker of backend. Exiting"
                )
                logger.critical("")
                sys.exit(1)
                
            
