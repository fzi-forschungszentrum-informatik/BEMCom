#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""
import struct
import logging
from time import sleep
from threading import Thread

from pymodbus import payload
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

# Log everything to stdout by default, i.e. to docker container logs.
LOGFORMAT = "%(asctime)s-%(funcName)s-%(levelname)s: %(message)s"
logging.basicConfig(format=LOGFORMAT, level=logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DemoDeviceDataBlock(ModbusSequentialDataBlock):
    """
    This translates between the DemoDevice class and pymodbus.
    """

    def __init__(self, demo_device, variable_name):
        """
        Init the class and add the link to the demo device instance.
        """
        self.demo_device = demo_device
        self.variable_name = variable_name

        values = self.encode_registers()
        # Not sure why the address is 2, but it matches fetching the
        # value from register 1.
        super().__init__(2, values)

    def encode_registers(self):
        """
        Encode the requested value to the registers convention of pymodbus.
        """
        value = getattr(self.demo_device, self.variable_name)
        builder = payload.BinaryPayloadBuilder(byteorder="<", wordorder="<",)
        builder.add_16bit_float(round(value, 1))
        return builder.to_registers()

    def setValues(self, address, value):
        """
        Decode the value (which is the pymodbus internal representation of
        registers as list of 16bit unsinged integers) and set the value
        to the variable in demo device.
        """
        value_b = b"".join(struct.pack("!H", x) for x in value)
        value_py = struct.unpack("<e", value_b)[0]
        if value_py < 15.0:
            value_py = 15.0
        elif value_py > 30.0:
            value_py = 30.0
        setattr(self.demo_device, self.variable_name, value_py)

    def getValues(self, address, count=1):
        """
        """
        values = self.encode_registers()
        return values


class DemoDevice:
    """
    A program that should behave like a simple Modbus device.

    See `../../Readme.md` for details.
    """

    def __init__(self):
        """
        Definie initial temperature and setpoint. Start the Modbus Server.
        """
        self.current_temperature = 21.0
        self.temperature_setpoint = 24.0

        slaves = ModbusSlaveContext(
            ir=DemoDeviceDataBlock(self, "current_temperature"),
            hr=DemoDeviceDataBlock(self, "temperature_setpoint"),
        )
        modbus_context = ModbusServerContext(slaves=slaves, single=True)
        self.modbus_server_thread = Thread(
            target=StartTcpServer,
            kwargs={"context": modbus_context, "address": ("0.0.0.0", 502),},
            # Auto close modbus server if main loop exits.
            daemon=True,
        )

    def run(self):
        """
        Main loop, updates the simulated room temperature every second.
        """
        try:
            self.modbus_server_thread.start()
            while True:
                logger.info(
                    "Current temperature: {:.1f}".format(
                        self.current_temperature
                    )
                )
                # Slowly move towards the setpoint.
                delta = self.temperature_setpoint - self.current_temperature
                self.current_temperature += delta * 0.1
                sleep(1)
        except (KeyboardInterrupt, SystemExit):
            # This is the normal way to exit the demo deivce.
            # No need to log the exception.
            logger.info(
                "Demo device received KeyboardInterrupt or SystemExit"
                ", shuting down."
            )


if __name__ == "__main__":
    dd = DemoDevice()
    dd.run()
