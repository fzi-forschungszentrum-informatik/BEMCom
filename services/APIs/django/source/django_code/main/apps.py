import sys
from django.apps import AppConfig

class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        import main.signals

        if 'runserver' in sys.argv:
            # Startup the MQTT integration.
            from .connector_mqtt_integration import ConnectorMQTTIntegration
            ConnectorMQTTIntegration()
