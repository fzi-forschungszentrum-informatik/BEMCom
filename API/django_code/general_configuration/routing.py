from channels.routing import ProtocolTypeRouter

from general_configuration.connector_mqtt_integration import ConnectorMQTTIntegration

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
})

cmi = ConnectorMQTTIntegration()
