import signal
from time import sleep

from django.core.management.base import BaseCommand

from api_main.mqtt_integration import MqttToDb

class Command(BaseCommand):
    help = "Executes api_main.mqtt_integration.MqttToDb."

    def handle(self, *args, **kwargs):
        # Signals trigger graceful shutdown on keyboard interrupt and
        # SIGTERM signal.
        signal.signal(signal.SIGINT, self.initiate_shutdown)
        signal.signal(signal.SIGTERM, self.initiate_shutdown)

        # Start MqttToDb and run until we receive a shut down signal, or
        # alternatively until an error occurs.
        mqtt_to_db = MqttToDb()
        self.shut_down_now = False
        try:
            while True:
                if self.shut_down_now:
                    break
                sleep(0.5)
        finally:
            mqtt_to_db.disconnect()

    def initiate_shutdown(self, *args, **kwargs):
        self.shut_down_now = True
