from channels.routing import ProtocolTypeRouter

from admin_interface.connector_mqtt_integration import ConnectorMQTTIntegration

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
})

cmi = ConnectorMQTTIntegration()
