import signal
import logging
from time import sleep

from django.core.management.base import BaseCommand

from api_main.mqtt_integration import MqttToDb


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Executes api_main.mqtt_integration.MqttToDb."

    def handle(self, *args, **kwargs):
        """
        Start MqttToDb and run until we receive a shut down signal.

        Do automatic restart on errors after 60 seconds wait time. This should
        handle infrequent errors, as might happen if the MQTT broker is
        offline for some time, without spamming the log to much if permanent
        errors occur.
        """
        # Signals trigger graceful shutdown on keyboard interrupt and
        # SIGTERM signal.
        signal.signal(signal.SIGINT, self.initiate_shutdown)
        signal.signal(signal.SIGTERM, self.initiate_shutdown)

        while True:
            mqtt_to_db = MqttToDb()
            self.shut_down_now = False
            try:
                while True:
                    if self.shut_down_now:
                        break
                    sleep(0.5)
            except Exception:
                logger.exception("Caught exception in MqttToDb. Restarting in 60s.")
            except (KeyboardInterrupt, SystemExit):
                # In theory, this branch should never be executed.
                # But better safe then sorry, right?
                logger.info(
                    "Caught KeyboardInterrupt or SysmteExit. " "Initiating shut down."
                )
                self.initiate_shutdown()
            finally:
                mqtt_to_db.disconnect()

            if self.shut_down_now:
                break
            else:
                sleep(60)

    def initiate_shutdown(self, *args, **kwargs):
        self.shut_down_now = True
