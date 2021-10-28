import os
import json
import time
import logging
import unittest
from unittest.mock import MagicMock
from multiprocessing import Process

import psutil
import pytest
from pymodbus.constants import Endian
from pymodbus.server.sync import StartTcpServer
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from ..main import Connector, __version__


class ModbusTestServer():
    """
    A simple context manager that allows starting a Modbus Server for
    the tests in a dedicated process.
    """

    def __init__(self, modbus_slave_context_kwargs):
        self.modbus_slave_context_kwargs = modbus_slave_context_kwargs

    def __enter__(self):
            store = ModbusSlaveContext(**self.modbus_slave_context_kwargs)
            context = ModbusServerContext(slaves=store, single=True)
            # This will configure the Modbus server to listen on a random
            # available port. This is necessary as after using a sepcific
            # port the os takes 20-30 seconds until this port is marked
            # as free again. However, we don not want to wait so long
            # in between our tests.
            self.modbus_server_process = Process(
                target=StartTcpServer,
                kwargs={
                    "context": context,
                    "address": ("127.0.0.1", 0),
                }
            )
            self.modbus_server_process.start()
            # After the server has started we have no clue which port it used.
            # so lets find out.
            for i in range(100):
                # It may take a while after the process has started until
                # the port is claimed from the OS. Hence we poll a few times.
                psutil_process = psutil.Process(self.modbus_server_process.pid)
                if psutil_process.connections():
                    break
                time.sleep(0.01)
            connections = psutil_process.connections()
            # This should be only one, but some old connections exist with
            # a different status from previous runs.
            active_connections = [c for c in connections if c.status=="LISTEN"]
            used_port = active_connections[0].laddr.port
            return used_port

    def __exit__(self, exception_type, exception_value, traceback):
        # stop the process after we are done.
        self.modbus_server_process.terminate()
        self.modbus_server_process.join()
        self.modbus_server_process.close()


class TestReceiveRawMsg(unittest.TestCase):
    """
    Verify that we can read the expected values via Modbus.
    Assumes that PyModbus is correct in terms of byte parsing operations.
    Also partly tests that the numbers are parsed correctly as this simplifies
    the tests significantly.
    """

    @classmethod
    def setUpClass(cls):
        # These must be set to match ModbusTestServer above.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        # These must just be present to prevent errors.
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "5"
        # These make tests fail faster while developing these.
        os.environ["MODBUS_MAX_RETRIES"] = "1"
        os.environ["MODBUS_RETRY_WAIT_SECONDS"] = "0"

    def test_read_floats(self):
        """
        Verify that float values are read and parsed as expected.
        """
        expected_values = {
            "0": 12.34375,
            "1": -12.34375,
            "2": 22.0,
            "4": -22.0,
            "6": 123.45,
            "10": -123.45,
        }
        test_cases = [
            # byteorder, wordorder, used modbus function
            [Endian.Big, Endian.Big, "read_holding_registers"],
            [Endian.Little, Endian.Little, "read_holding_registers"],
            [Endian.Big, Endian.Big, "read_input_registers"],
            [Endian.Little, Endian.Little, "read_input_registers"],
        ]
        for test_case in test_cases:
            byteorder = test_case[0]
            wordorder = test_case[1]
            modbus_function = test_case[2]

            print("running test case: %s" % test_case)
            # Configure the expected_values for the temporary modbus server.
            builder = BinaryPayloadBuilder(
                byteorder=byteorder,
                wordorder=wordorder,
            )
            builder.add_16bit_float(float(expected_values["0"]))
            builder.add_16bit_float(float(expected_values["1"]))
            builder.add_32bit_float(float(expected_values["2"]))
            builder.add_32bit_float(float(expected_values["4"]))
            builder.add_64bit_float(float(expected_values["6"]))
            builder.add_64bit_float(float(expected_values["10"]))
            msc = {}
            if modbus_function == "read_holding_registers":
                msc["hr"] = ModbusSequentialDataBlock(1, builder.to_registers())
            if modbus_function == "read_input_registers":
                msc["ir"] = ModbusSequentialDataBlock(1, builder.to_registers())
            modbus_slave_context_kwargs = msc

            # Compute the matching configuration for the modbus-tcp-connector.
            test_modbus_config = {
                modbus_function: [
                    {
                        "address": 0,
                        "count": 14,
                        "unit": 2,
                        "datatypes": "{}eeffdd".format(byteorder),
                    },
                ],
            }
            os.environ["MODBUS_CONFIG"] = json.dumps(test_modbus_config)

            with ModbusTestServer(
                modbus_slave_context_kwargs=modbus_slave_context_kwargs
            ) as used_port:
                os.environ["MODBUS_MASTER_PORT"] = str(used_port)
                connector = Connector(version=__version__)
                raw_msg = connector.receive_raw_msg()
                raw_msg["payload"]["timestamp"] = 1617027818000
            parsed_msg = connector.parse_raw_msg(raw_msg=raw_msg)
            payload = parsed_msg["payload"]
            actual_values = payload["parsed_message"][modbus_function]["2"]

            assert actual_values == expected_values

    def test_read_ints(self):
        """
        Verify that int values are read and parsed as expected.
        """
        expected_values = {
            "0": 42,  # Fits into 8bit int
            "1": -42,  # Also fits into 8bit int, but only signed.
            "2": 42,  # Fits into 8bit unsigned int
            "3": 241,  # Also fits into 8bit int, but only ungsinged.
            "4": 30000,  # Fits into 16 bit int, but not 8 bit.
            "5": -30000,  # and so on ...
            "6": 30000,
            "7": 60000,
            "8": 2111222333,
            "10": -2111222333,
            "12": 2111222333,
            "14": 4111222333,
            "16": 9111222333444555666,
            "20": -9111222333444555666,
            "24": 9111222333444555666,
            "28": 18111222333444555666,
        }
        test_cases = [
            # byteorder, wordorder, used modbus function
            [Endian.Big, Endian.Big, "read_holding_registers"],
            [Endian.Little, Endian.Little, "read_holding_registers"],
            [Endian.Big, Endian.Big, "read_input_registers"],
            [Endian.Little, Endian.Little, "read_input_registers"],
        ]
        for test_case in test_cases:
            byteorder = test_case[0]
            wordorder = test_case[1]
            modbus_function = test_case[2]

            print("running test case: %s" % test_case)
            # Configure the expected_values for the temporary modbus server.
            builder = BinaryPayloadBuilder(
                byteorder=byteorder,
                wordorder=wordorder,
            )
            builder.add_8bit_int(0)  # This is a pad byte, which prevents that
            # the following bytes overlap into this register.
            builder.add_8bit_int(int(expected_values["0"]))
            builder.add_8bit_int(0)
            builder.add_8bit_int(int(expected_values["1"]))
            builder.add_8bit_int(0)
            builder.add_8bit_uint(int(expected_values["2"]))
            builder.add_8bit_int(0)
            builder.add_8bit_uint(int(expected_values["3"]))
            builder.add_16bit_int(int(expected_values["4"]))
            builder.add_16bit_int(int(expected_values["5"]))
            builder.add_16bit_uint(int(expected_values["6"]))
            builder.add_16bit_uint(int(expected_values["7"]))
            builder.add_32bit_int(int(expected_values["8"]))
            builder.add_32bit_int(int(expected_values["10"]))
            builder.add_32bit_uint(int(expected_values["12"]))
            builder.add_32bit_uint(int(expected_values["14"]))
            builder.add_64bit_int(int(expected_values["16"]))
            builder.add_64bit_int(int(expected_values["20"]))
            builder.add_64bit_uint(int(expected_values["24"]))
            builder.add_64bit_uint(int(expected_values["28"]))
            msc = {}
            if modbus_function == "read_holding_registers":
                msc["hr"] = ModbusSequentialDataBlock(1, builder.to_registers())
            if modbus_function == "read_input_registers":
                msc["ir"] = ModbusSequentialDataBlock(1, builder.to_registers())
            modbus_slave_context_kwargs = msc

            # Compute the matching configuration for the modbus-tcp-connector.
            test_modbus_config = {
                modbus_function: [
                    {
                        "address": 0,
                        "count": 32,
                        "unit": 0,
                        "datatypes": "{}xbxbxBxBhhHHllLLqqQQ".format(byteorder),
                    },
                ],
            }
            os.environ["MODBUS_CONFIG"] = json.dumps(test_modbus_config)

            with ModbusTestServer(
                modbus_slave_context_kwargs=modbus_slave_context_kwargs
            ) as used_port:
                os.environ["MODBUS_MASTER_PORT"] = str(used_port)
                connector = Connector(version=__version__)
                raw_msg = connector.receive_raw_msg()
                raw_msg["payload"]["timestamp"] = 1617027818000
            parsed_msg = connector.parse_raw_msg(raw_msg=raw_msg)
            payload = parsed_msg["payload"]
            actual_values = payload["parsed_message"][modbus_function]["0"]

            assert actual_values == expected_values

    def test_read_bits(self):
        """
        Verify that int values are read and parsed as expected.
        """
        expected_values = {
            "0": True,
            "1": True,
            "2": True,
            "3": False,
            "4": True,
        }
        test_cases = [
            # byteorder, wordorder, used modbus function
            [Endian.Big, Endian.Big, "read_coils"],
            [Endian.Little, Endian.Little, "read_coils"],
            [Endian.Big, Endian.Big, "read_discrete_inputs"],
            [Endian.Little, Endian.Little, "read_discrete_inputs"],
        ]
        for test_case in test_cases:
            byteorder = test_case[0]
            wordorder = test_case[1]
            modbus_function = test_case[2]

            print("running test case: %s" % test_case)
            # Configure the expected_values for the temporary modbus server.
            builder = BinaryPayloadBuilder(
                byteorder=byteorder,
                wordorder=wordorder,
            )
            bits = []
            for addr in sorted(expected_values):
                bits.append(int(expected_values[addr]))
            # The bits must be ordered like Bit7, Bit6, ... , Bit0
            # Also add zero padding for the same reason.
            builder.add_bits((bits+[0, 0, 0])[::-1])
            msc = {}
            if modbus_function == "read_coils":
                msc["co"] = ModbusSequentialDataBlock(1, builder.to_coils())
            if modbus_function == "read_discrete_inputs":
                msc["di"] = ModbusSequentialDataBlock(1, builder.to_coils())
            modbus_slave_context_kwargs = msc

            # Compute the matching configuration for the modbus-tcp-connector.
            test_modbus_config = {
                modbus_function: [
                    {
                        "address": 0,
                        "count": 5,
                        "unit": 1,
                    },
                ],
            }
            os.environ["MODBUS_CONFIG"] = json.dumps(test_modbus_config)

            with ModbusTestServer(
                modbus_slave_context_kwargs=modbus_slave_context_kwargs
            ) as used_port:
                os.environ["MODBUS_MASTER_PORT"] = str(used_port)
                connector = Connector(version=__version__)
                raw_msg = connector.receive_raw_msg()
                print(raw_msg)
                raw_msg["payload"]["timestamp"] = 1617027818000
            parsed_msg = connector.parse_raw_msg(raw_msg=raw_msg)
            payload = parsed_msg["payload"]
            actual_values = payload["parsed_message"][modbus_function]["1"]

            assert actual_values == expected_values


class TestParseRawMsg(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Define test config.
        test_modbus_config = {
            "read_input_registers": [
                {
                    "address": 19000,
                    "count": 20,
                    "unit": 1,
                    "datatypes": ">ffffffffff",
                },
                {
                    "address": 20000,
                    "count": 4,
                    "unit": 1,
                    "datatypes": ">ff",
                    "scaling_factors": {
                        20000: 0.1,
                        20002: 10,
                    }
                },
            ],
        }

        # Prepare everything so we can init the class.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        os.environ["MODBUS_MASTER_PORT"] = "502"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "5"
        os.environ["MODBUS_CONFIG"] = json.dumps(test_modbus_config)
        cls.connector = Connector(version=__version__)

        # This is an actual returned raw message object received with the config
        # above, corresponding to ten 32 bit float values received from a
        # electric meter.
        cls.test_raw_msg_registers = {
            "payload": {
                "raw_message": {
                    "read_input_registers": {
                        0: [
                            17258,
                            34800,
                            17258,
                            2888,
                            17258,
                            56736,
                            17354,
                            44618,
                            17355,
                            15044,
                            17355,
                            18738,
                            16384,
                            33878,
                            16417,
                            33474,
                            16405,
                            36910,
                            16087,
                            18778
                        ]
                    }
                }
            }
        }

    def test_read_input_registers_parsed_correctly(self):
        """
        Verify that registers are parsed correctly.

        This uses an actual returned raw_msg received with the above
        from a real device.
        """
        test_raw_msg = {
            "payload": {
                "raw_message": {
                    "read_input_registers": {
                        0: [
                            17259,
                            1512,
                            17258,
                            31341,
                            17259,
                            18065,
                            17355,
                            7316,
                            17355,
                            37386,
                            17355,
                            44004,
                            16383,
                            62906,
                            16420,
                            36584,
                            16406,
                            52624,
                            16096,
                            45866
                        ]
                    }
                },
                "timestamp": 1612969083914
            }
        }
        expected_parsed_msg = {
            "payload": {
                "parsed_message": {
                    "read_input_registers": {
                        "1" : {
                            "19000": 235.0230712890625,
                            "19002": 234.4782257080078,
                            "19004": 235.27565002441406,
                            "19006": 406.2232666015625,
                            "19008": 407.14093017578125,
                            "19010": 407.3428955078125,
                            "19012": 1.9996864795684814,
                            "19014": 2.5712223052978516,
                            "19016": 2.3562965393066406,
                            "19018": 0.43886691331863403
                        }
                    }
                },
                "timestamp": 1612969083914
            }
        }

        # Overload the modbus_addresses attribute to ensure that
        # this test doesn't fail because of errors in the
        # compute_addresses method.
        self.connector.modbus_addresses = {
            "read_input_registers": {
                0: [
                    19000,
                    19002,
                    19004,
                    19006,
                    19008,
                    19010,
                    19012,
                    19014,
                    19016,
                    19018,
                ],
            },
        }

        actual_parsed_msg = self.connector.parse_raw_msg(raw_msg=test_raw_msg)
        assert actual_parsed_msg == expected_parsed_msg

    def test_read_scaling_factors_applied(self):
        """
        Verify that the scaling factors are applied as expected.
        """
        test_raw_msg = {
            "payload": {
                "raw_message": {
                    "read_input_registers": {
                        1: [
                            17259,
                            1512,
                            17258,
                            31341,
                        ]
                    }
                },
                "timestamp": 1612969083914
            }
        }
        expected_parsed_msg = {
            "payload": {
                "parsed_message": {
                    "read_input_registers": {
                        "1" : {
                            "20000": 23.502307128906253,
                            "20002": 2344.782257080078,
                        }
                    }
                },
                "timestamp": 1612969083914
            }
        }

        # Overload the modbus_addresses attribute to ensure that
        # this test doesn't fail because of errors in the
        # compute_addresses method.
        self.connector.modbus_addresses = {
            "read_input_registers": {
                1: [
                    20000,
                    20002,
                ],
            },
        }

        actual_parsed_msg = self.connector.parse_raw_msg(raw_msg=test_raw_msg)
        assert actual_parsed_msg == expected_parsed_msg


class TestSendCommand(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def expose_caplog(self, caplog):
        self.caplog = caplog

    @classmethod
    def setUpClass(cls):
        # Define test config.
        cls.test_modbus_config = {
            "write_coil": [
                {
                    "address": 19,
                    "example_value": True,
                    "unit": 1
                },
            ],
            "write_register": [
                {
                    "address": 21,
                    "unit": 2,
                    "example_value": 12,
                    "datatypes": "<H",
                },
            ],
            "write_registers": [
                {
                    "address": 23,
                    "unit": 3,
                    "example_value": 22.1,
                    "datatypes": ">f",
                },
            ],
        }

        class FakeResponse():
            """
            A mock for the response value of the modbus methods that does
            not trigger the retry loop.
            """
            def isError(self):
                return False
        cls.fake_response = FakeResponse()

        # Prepare everything so we can init the class.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        os.environ["MODBUS_MASTER_PORT"] = "502"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "6"
        os.environ["MODBUS_CONFIG"] = json.dumps(cls.test_modbus_config)

    def test_modbus_command_args_correct_for_coil(self):
        """
        Verify that for a coil datapoint send_command triggers write_coil
        with the appropriate arguments.
        """
        test_value_msgs = [
            {
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": True,
            },
            {
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": False,
            },
        ]

        cn = Connector(version=__version__)
        cn.modbus_connection = MagicMock()
        cn.modbus_connection.write_coil = MagicMock(
            return_value=self.fake_response
        )
        modbus_method_mock = cn.modbus_connection.write_coil
        for test_value_msg in test_value_msgs:
            cn.send_command(**test_value_msg)

            expeceted_kwargs = {
                "address": 19,
                "value": test_value_msg["datapoint_value"],
                "unit": 1
            }
            modbus_method_mock = cn.modbus_connection.write_coil
            actual_kwargs = modbus_method_mock.call_args.kwargs

            assert actual_kwargs == expeceted_kwargs

    def test_modbus_command_args_correct_for_register(self):
        """
        Verify that for a register datapoint send_command triggers
        write_register with the appropriate arguments.
        """
        test_value_msgs = [
            {
                "datapoint_key": "write_register__2__21",
                "datapoint_value": 13,
            },
            {
                "datapoint_key": "write_register__2__21",
                "datapoint_value": 158,
            },
        ]

        cn = Connector(version=__version__)
        cn.modbus_connection = MagicMock()
        cn.modbus_connection.write_register = MagicMock(
            return_value=self.fake_response
        )
        modbus_method_mock = cn.modbus_connection.write_register
        for test_value_msg in test_value_msgs:
            cn.send_command(**test_value_msg)

            # Build the binary representation using the PyModbus
            # provided tools, assuming these are correct.
            builder = BinaryPayloadBuilder(byteorder="<", wordorder="<")
            # 16bit_uint corresponds to struct type 'H'
            builder.add_16bit_uint(test_value_msg["datapoint_value"])
            registers = builder.build()

            expeceted_kwargs = {
                "address": 21,
                "value": registers[0],
                "unit": 2,
                "skip_encode": True,
            }
            modbus_method_mock = cn.modbus_connection.write_register
            actual_kwargs = modbus_method_mock.call_args.kwargs

            assert actual_kwargs == expeceted_kwargs

    def test_modbus_command_args_correct_for_multiple_registers(self):
        """
        Verify that for a datapoint spanning multiple registers send_command
        triggers write_registers with the appropriate arguments.
        """
        test_value_msgs = [
            {
                "datapoint_key": "write_registers__3__23",
                "datapoint_value": 12.0,
            },
            {
                "datapoint_key": "write_registers__3__23",
                "datapoint_value": -999.88,
            },
        ]

        cn = Connector(version=__version__)
        cn.modbus_connection = MagicMock()
        cn.modbus_connection.write_registers = MagicMock(
            return_value=self.fake_response
        )
        modbus_method_mock = cn.modbus_connection.write_registers
        for test_value_msg in test_value_msgs:
            cn.send_command(**test_value_msg)

            # Build the binary representation using the PyModbus
            # provided tools, assuming these are correct.
            builder = BinaryPayloadBuilder(byteorder=">", wordorder=">")
            # 16bit_uint corresponds to struct type 'f'
            builder.add_32bit_float(test_value_msg["datapoint_value"])
            registers = builder.build()

            expeceted_kwargs = {
                "address": 23,
                "value": registers,
                "unit": 3,
                "skip_encode": True,
            }

            actual_kwargs = modbus_method_mock.call_args.kwargs

            assert actual_kwargs == expeceted_kwargs

    def test_send_command_only_works_for_known_datapoints(self):
        """
        For safeties sake, the Modbus connector should only be able
        to send data to datapoints that have been specified in MODBUS_CONFIG.
        """
        test_value_msgs = [
            {
                # Same register but different unit.
                "datapoint_key": "write_coil__5__19",
                "datapoint_value": True,
            },
            {
                # Same unit but different register
                "datapoint_key": "write_register__2__799",
                "datapoint_value": 12.0,
            },
            {
                "datapoint_key": "write_registers__12__1",
                "datapoint_value": -999.88,
            },
        ]

        cn = Connector(version=__version__)
        cn.modbus_connection = MagicMock(return_value=True)
        self.caplog.clear()
        self.caplog.set_level(logging.WARNING)
        for test_value_msg in test_value_msgs:
            cn.send_command(**test_value_msg)

            # Verify that nothing has been send out.
            modbus_method_name = test_value_msg["datapoint_key"].split("__")[0]
            modbus_method_mock = getattr(
                cn.modbus_connection, modbus_method_name
            )
            assert modbus_method_mock.called == False

            # Also check that warning messages have been logged.
            record = self.caplog.records[-1]
            assert record.levelname == "WARNING"
            assert test_value_msg["datapoint_key"] in record.message

    def test_send_command_logs_error_for_coil_with_non_bool_value(self):
        """
        Coils can only be set to True or False. We expect datapoint_value
        thus to be a bool and log an error if that is not the case.
        """
        # It's rather interesting to search for the True versions of the
        # The strings because these will actually evaluate to True.
        # BEMCom value messages can either be String, Bool, Float or None.
        test_value_msgs = [
            {
                # This is unparsed JSON
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": "true",
            },
            {
                # This is bash environment variable convetion
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": "TRUE",
            },
            {
                # This is a Python string representation of a bool
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": "True",
            },
            # { # This one evaluates to True, i.e. 1.0 == True
            #     "datapoint_key": "write_coil__1__19",
            #     "datapoint_value": 1.0,
            # },
            # { # This one evaluates to True, i.e. 1 == True
            #     "datapoint_key": "write_coil__1__19",
            #     "datapoint_value": 1,
            # },
            {
                # This has been implemented as True value up to
                # version 0.3.1 of the connector.
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": "1",
            },
            {
                "datapoint_key": "write_coil__1__19",
                "datapoint_value": None,
            },
        ]

        cn = Connector(version=__version__)
        cn.modbus_connection = MagicMock()
        self.caplog.clear()
        self.caplog.set_level(logging.WARNING)
        for test_value_msg in test_value_msgs:
            cn.send_command(**test_value_msg)

            # Verify that nothing has been send out.
            modbus_method_mock = cn.modbus_connection.write_coil
            assert modbus_method_mock.called == False

            # Also check that warning messages have been logged.
            record =self.caplog.records[-1]
            assert record.levelname == "WARNING"
            assert test_value_msg["datapoint_key"] in record.message


class TestComputeAvailableActuatorDatapoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Define test config.
        cls.test_modbus_config = {
            "write_coil": [
                {
                    "address": 19,
                    "example_value": True,
                    "unit": 1,
                },
            ],
            "write_register": [
                {
                    "address": 21,
                    "unit": 2,
                    "example_value": 21.3,
                    "datatypes": ">H",
                },
            ],
        }

        # Prepare everything so we can init the class.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        os.environ["MODBUS_MASTER_PORT"] = "502"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "6"
        os.environ["MODBUS_CONFIG"] = json.dumps(cls.test_modbus_config)

    def test_actuator_datapoints_computed_correctly(self):
        """
        Verify that the actuator entries in available_datapoints are
        computed correctly from the MODBUS_CONFIG.
        """
        expected_available_datapoints = {
            "write_coil__1__19": True,
            "write_register__2__21": 21.3
        }
        expected_write_config_per_dp = {
            "write_coil__1__19": {
                "address": 19,
                "example_value": True,
                "unit": 1,
                "write_method_name": "write_coil",
            },
            "write_register__2__21": {
                "address": 21,
                "unit": 2,
                "example_value": 21.3,
                "datatypes": ">H",
                "write_method_name": "write_register",
            },
        }


        cn = Connector(version=__version__)
        rtn = cn.compute_available_actuator_datapoints(
            modbus_config=self.test_modbus_config,
        )
        actual_available_datapoints, actual_write_config_per_dp = rtn
        assert actual_available_datapoints == expected_available_datapoints
        assert actual_write_config_per_dp == expected_write_config_per_dp

    def test_actuator_datapoints_included(self):
        """
        Verify that  actuator entries in available_datapoints are exposed
        to the connector.
        """
        expected_available_datapoints = {
            "sensor": {},
            "actuator":{
                "write_coil__1__19": True,
                "write_register__2__21": 21.3
            }
        }
        cn = Connector(version=__version__)
        actual_available_datapoints = cn._initial_available_datapoints
        assert actual_available_datapoints == expected_available_datapoints


class TestParseModbusConfig(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def expose_caplog(self, caplog):
        self.caplog = caplog

    def test_parse_read_functions(self):
        """
        Verify that the config string is parsed as expected for reading
        function calls.
        """
        expected_config = {
            "read_coils": [],
            "read_discrete_inputs": [],
            "read_holding_registers": [],
            "read_input_registers": [
                {
                    "address": 19000,
                    "count": 20,
                    "unit": 1,
                    "datatypes": ">ffffffffff",
                },
            ],
            "write_coil": [],
            "write_register": [],
            "write_registers": [],
        }

        config_json_str = json.dumps(expected_config)
        actual_config = Connector.parse_modbus_config(config_json_str)

        assert actual_config == expected_config

    def test_warning_on_not_expected_config_key(self):

        test_config = {
            "read_coils": [],
            "read_discrete_inputs": [],
            "read_holding_registers": [],
            "read_input_registers": [],
            "write_coil": [],
            "write_register": [],
            "write_registers": [],
            "not_expected_keyword": [
                {
                    "address": 19000,
                    "count": 20,
                }
            ],
        }

        self.caplog.clear()
        self.caplog.set_level(logging.WARNING)
        config_json_str = json.dumps(test_config)
        _ = Connector.parse_modbus_config(config_json_str)

        # We expect exactly one warning message about the unexecpted key.
        assert len(self.caplog.records) == 1
        record = self.caplog.records[0]
        assert record.levelname == "WARNING"
        assert "not_expected_keyword" in record.message
        assert '"address": 19000' in record.message

    def test_not_expected_config_key_removed(self):

        test_config = {
            "read_coils": [],
            "read_discrete_inputs": [],
            "read_holding_registers": [],
            "read_input_registers": [],
            "write_coil": [],
            "write_register": [],
            "write_registers": [],
            "not_expected_keyword": [],
        }

        self.caplog.clear()
        self.caplog.set_level(logging.WARNING)
        config_json_str = json.dumps(test_config)
        actual_config = Connector.parse_modbus_config(config_json_str)

        assert "not_expected_keyword" not in actual_config

    def test_write_register_checked_for_multi_register_types(self):
        """
        By definition writer_register can only send a value to single
        register. Hence, we check during parsing the config that the
        binary output is less or equal 16 bit.
        """
        test_config = {
            "write_register": [
                {
                    "address": 21,
                    "unit": 2,
                    "example_value": 2.2,
                    "datatypes": ">f", # this is two registers long.
                },
            ],
        }

        self.caplog.clear()
        self.caplog.set_level(logging.WARNING)
        config_json_str = json.dumps(test_config)
        with pytest.raises(ValueError):
            _ = Connector.parse_modbus_config(config_json_str)

        # We expect exactly one warning message about the unexecpted key.
        assert len(self.caplog.records) == 1
        record = self.caplog.records[0]
        assert record.levelname == "ERROR"
        assert "Datatype >f implied" in record.message
        assert "sending 2 registers"  in record.message
        assert '"address": 21' in record.message
        assert '"unit": 2' in record.message


class TestComputeAddresses(unittest.TestCase):

    def test_for_32bit_floats(self):
        """
        Simple test to begin with, inspired by the data used by the tests above.
        """
        test_config = {
            "read_input_registers": [
                {
                    "address": 19000,
                    "count": 20,
                    "unit": 1,
                    "datatypes": ">ffffffffff",
                },
            ],
        }
        expected_register_addresses = {
            "read_input_registers": {
                0: [
                    19000,
                    19002,
                    19004,
                    19006,
                    19008,
                    19010,
                    19012,
                    19014,
                    19016,
                    19018,
                ],
            },
        }

        actual_register_addresses = Connector.compute_addresses(
            modbus_config=test_config
        )

        assert actual_register_addresses == expected_register_addresses

    def test_for_all_value_types(self):
        """
        Test for an arbitrary datatype string that contains all values.

        The last entry in datatypes is doubled as the register size of it
        would thus not be used in computation of the addresses.
        """
        test_config = {
            "read_holding_registers": [
                {
                    "address": 1,
                    "count": 34,
                    "unit": 1,
                    "datatypes": "<cbB?hHiIlLqQefdd"

                },
            ],
        }
        expected_register_addresses = {
            "read_holding_registers": {
                0: [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    9,
                    11,
                    13,
                    15,
                    19,
                    23,
                    24,
                    26,
                    30,
                ],
            },
        }

        actual_register_addresses = Connector.compute_addresses(
            modbus_config=test_config
        )

        assert actual_register_addresses == expected_register_addresses

    def test_for_coils(self):
        """
        Verify that coil addresses are computet correctly too.
        """
        for method_name in ["read_coils", "read_discrete_inputs"]:
            test_config = {
                method_name: [
                    {
                        "address": 1,
                        "count": 5,
                        "unit": 1,
                    },
                    {
                        "address": 10,
                        "count": 6,
                        "unit": 1,
                    },
                ],
            }
            expected_addresses = {
                method_name: {
                    0: [ 1, 2, 3, 4, 5 ],
                    1: [ 10, 11, 12, 13, 14, 15 ],
                },
            }

            actual_addresses = Connector.compute_addresses(
                modbus_config=test_config
            )

            assert actual_addresses == expected_addresses
