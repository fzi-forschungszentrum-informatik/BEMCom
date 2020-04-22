import os
import json
import signal
import logging
from urllib.parse import quote_plus

from pymongo import MongoClient
from paho.mqtt.client import Client


# Trigger graceful shutdown on docker container stop
def call_sysexit(signal, frame):
    raise SystemExit()
signal.signal(signal.SIGTERM, call_sysexit)


# Load the settings/configuratiion.
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_LOGIN_DB = os.getenv("MONGO_LOGIN_DB")
MQTT_TOPIC_ALL_RAW_MESSAGES = os.getenv("MQTT_TOPIC_ALL_RAW_MESSAGES")
MQTT_INTEGRATION_LOG_LEVEL = os.getenv("MQTT_INTEGRATION_LOG_LEVEL")

# Log everything, also debug, if requested or invalid log level specified.
LOGLEVEL = 10
if MQTT_INTEGRATION_LOG_LEVEL == "INFO":
    LOGLEVEL = 20
elif MQTT_INTEGRATION_LOG_LEVEL == "WARNING":
    LOGLEVEL = 30
elif MQTT_INTEGRATION_LOG_LEVEL == "ERROR":
    LOGLEVEL = 40
elif MQTT_INTEGRATION_LOG_LEVEL == "CRITICAL":
    LOGLEVEL = 50

log_format =  "%(asctime)s MQTT-Integration %(name)s %(levelname)s %(message)s"
logging.basicConfig(level=LOGLEVEL, format=log_format)
logger = logging.getLogger(__name__)


logger.info("Starting up monog-raw-message-db MQTT integration")

# Connect ot MongoDb, handle potentially given usernames and passwords.
logger.info('Initiating mongodb client')

def create_mongo_host_str(username, password, host, port, login_db):
    """
    Build host str, add username and password only if set.
    The full template looks like this: 'mongodb://%s:%s@%s:%s'
    """
    mongo_host_str = 'mongodb://'
    if username:
        mongo_host_str += '%s' % quote_plus(username)
        if password:
            mongo_host_str += ':%s' % quote_plus(password)
        mongo_host_str += '@'

    mongo_host_str += '%s:%s' % (
        host,
        port,
    )
    if login_db:
        mongo_host_str += '/?authSource=%s' % quote_plus(login_db)
    return mongo_host_str

mongo_host_str = create_mongo_host_str(
    username=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    host=MONGO_HOST,
    port=MONGO_PORT,
    login_db=MONGO_LOGIN_DB
)

# Create a version without password for the log.
password_blinded = MONGO_PASSWORD
if password_blinded:
    password_blinded = 'x'*10
mongo_host_str_blinded = create_mongo_host_str(
    username=MONGO_USERNAME,
    password=password_blinded,
    host=MONGO_HOST,
    port=MONGO_PORT,
    login_db=MONGO_LOGIN_DB
)
logger.debug('Connecting to MongoDB: %s', mongo_host_str_blinded)
mc = MongoClient(mongo_host_str)
logger.info('Connected to MongoDB: %s', mongo_host_str_blinded)

if "bemcom_db" not in mc.list_database_names():
    # This should only happen while starting the container, else there
    # is likely an issue with the volumne mount.
    logger.warning("BEMCom Database does not exist yet")
bemcom_db = mc["bemcom_db"]

# Define the Callbacks for the MQTT client.nt.
def on_connect(client, userdata, flags, rc):
    logger.info(
        'Connected to MQTT broker tcp://%s:%s',
        userdata['connect_kwargs']['host'],
        userdata['connect_kwargs']['port'],
    )
    client.subscribe(MQTT_TOPIC_ALL_RAW_MESSAGES, qos=2)

def on_disconnect(client, userdata, rc):
    """
    Atempt Reconnecting if disconnect was not called from a call to
    client.disconnect().
    """
    if rc != 0:
        logger.info(
            'Lost connection to MQTT broker with code %s. Reconnecting',
            rc
        )

def on_message(client, userdata, msg):
    """
    Write incoming message to MongoDB
    """
    logger.debug(
        "Recieved msg on topic \"%s\" with payload:\n%s",
        *(msg.topic, msg.payload)
    )

    # Use connector name as collection to keep messages sorted
    # The topic convention that we expect here is:
    # connector_name + "/raw_message_to_db"
    connector_name = msg.topic.split("/")[0]

    bemcom_db = userdata["bemcom_db"]
    collection = bemcom_db[connector_name]
    collection.insert_one(json.loads(msg.payload))

    logger.debug(
        "Wrote message for topic \"%s\" to DB.", msg.topic
    )

logger.info("Connecting to MQTT broker")
# MQTT broker settings, used for inital connect and reconnect.
connect_kwargs = {
    "host": MQTT_BROKER_HOST,
    "port": MQTT_BROKER_PORT,
}

# The private userdata, used by the callbacks.
userdata = {
    "connect_kwargs": connect_kwargs,
    "bemcom_db": bemcom_db,
}
client = Client(userdata=userdata)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# Initial connection to broker.
client.connect(**connect_kwargs)

# This blocks until the container shuts down, or someone presses ctrl+c while
# developing. Will run the remaining code then and shut down the integration.
try:
    client.loop_forever()
except SystemExit:
    pass
except KeyboardInterrupt:
    pass

logger.info("Shutting down.")
client.disconnect()
mc.close()
logger.info("Disconnected from MQTT Broker and MongoDB.")
