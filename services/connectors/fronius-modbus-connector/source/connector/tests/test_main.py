import os
import json
import time
import logging
import unittest
from multiprocessing import Process
from unittest.mock import MagicMock, Mock, call


import psutil
import pytest
from pymodbus.constants import Endian
from pymodbus.server.sync import StartTcpServer
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from ..main import Connector


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
        active_connections = [c for c in connections if c.status == "LISTEN"]
        used_port = active_connections[0].laddr.port
        return used_port

    def __exit__(self, exception_type, exception_value, traceback):
        # stop the process after we are done.
        self.modbus_server_process.terminate()
        self.modbus_server_process.join()
        self.modbus_server_process.close()


class TestReceiveRawMsg(unittest.TestCase):
    """
    Verify that we can read the expeceted values via Modbus.
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
        Verify that float values are read and parsed as epected.
        """
        expected_values = {
            "0": "12.34375",
            "1": "-12.34375",
            "2": "22.0",
            "4": "-22.0",
            "6": "123.45",
            "10": "-123.45"
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
                msc["hr"] = ModbusSequentialDataBlock(
                    1, builder.to_registers())
            if modbus_function == "read_input_registers":
                msc["ir"] = ModbusSequentialDataBlock(
                    1, builder.to_registers())
            modbus_slave_context_kwargs = msc

            # Compute the matching configuration for the modbus-tcp-connector.
            test_modbus_config = {
                modbus_function: [
                    {
                        "address": 0,
                        "count": 14,
                        "unit": 1,
                        "datatypes": "{}eeffdd".format(byteorder),
                    },
                ],
            }
            os.environ["MODBUS_CONFIG"] = json.dumps(test_modbus_config)

            with ModbusTestServer(
                modbus_slave_context_kwargs=modbus_slave_context_kwargs
            ) as used_port:
                os.environ["MODBUS_MASTER_PORT"] = str(used_port)
                connector = Connector()
                raw_msg = connector.receive_raw_msg()
                raw_msg["payload"]["timestamp"] = 1617027818000
            parsed_msg = connector.parse_raw_msg(raw_msg=raw_msg)
            payload = parsed_msg["payload"]
            actual_values = payload["parsed_message"][modbus_function]

            assert actual_values == expected_values

    def test_read_ints(self):
        """
        Verify that int values are read and parsed as epected.
        """
        expected_values = {
            "0": "42",  # Fits into 8bit int
            "1": "-42",  # Also fits into 8bit int, but only signed.
            "2": "42",  # Fits into 8bit unsigned int
            "3": "241",  # Also fits into 8bit int, but only ungsinged.
            "4": "30000",  # Fits into 16 bit int, but not 8 bit.
            "5": "-30000",  # and so on ...
            "6": "30000",
            "7": "60000",
            "8": "2111222333",
            "10": "-2111222333",
            "12": "2111222333",
            "14": "4111222333",
            "16": "9111222333444555666",
            "20": "-9111222333444555666",
            "24": "9111222333444555666",
            "28": "18111222333444555666",
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
                msc["hr"] = ModbusSequentialDataBlock(
                    1, builder.to_registers())
            if modbus_function == "read_input_registers":
                msc["ir"] = ModbusSequentialDataBlock(
                    1, builder.to_registers())
            modbus_slave_context_kwargs = msc

            # Compute the matching configuration for the modbus-tcp-connector.
            test_modbus_config = {
                modbus_function: [
                    {
                        "address": 0,
                        "count": 32,
                        "unit": 1,
                        "datatypes": "{}xbxbxBxBhhHHllLLqqQQ".format(byteorder),
                    },
                ],
            }
            os.environ["MODBUS_CONFIG"] = json.dumps(test_modbus_config)

            with ModbusTestServer(
                modbus_slave_context_kwargs=modbus_slave_context_kwargs
            ) as used_port:
                os.environ["MODBUS_MASTER_PORT"] = str(used_port)
                connector = Connector()
                raw_msg = connector.receive_raw_msg()
                raw_msg["payload"]["timestamp"] = 1617027818000
            parsed_msg = connector.parse_raw_msg(raw_msg=raw_msg)
            payload = parsed_msg["payload"]
            actual_values = payload["parsed_message"][modbus_function]

            assert actual_values == expected_values

    def test_read_bits(self):
        """
        Verify that int values are read and parsed as epected.
        """
        expected_values = {
            "0": "1",
            "1": "1",
            "2": "1",
            "3": "0",
            "4": "1",
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
            print(bits[::-1])
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
                connector = Connector()
                raw_msg = connector.receive_raw_msg()
                print(raw_msg)
                raw_msg["payload"]["timestamp"] = 1617027818000
            parsed_msg = connector.parse_raw_msg(raw_msg=raw_msg)
            payload = parsed_msg["payload"]
            actual_values = payload["parsed_message"][modbus_function]

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
        cls.connector = Connector()

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

    def test_read_input_registers_paresed_correctly(self):
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
                        "19000": "235.0230712890625",
                        "19002": "234.4782257080078",
                        "19004": "235.27565002441406",
                        "19006": "406.2232666015625",
                        "19008": "407.14093017578125",
                        "19010": "407.3428955078125",
                        "19012": "1.9996864795684814",
                        "19014": "2.5712223052978516",
                        "19016": "2.3562965393066406",
                        "19018": "0.43886691331863403"
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
                        "20000": "23.502307128906253",
                        "20002": "2344.782257080078",
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

    @classmethod
    def setUpClass(cls):
        # Define test config.
        cls.test_modbus_config = {
            "write_coil": [
                {
                    "address": 19,
                    "count": 20, 
                    "unit": 1
                }
            ],
            "write_register": [
            {
                "address": 21,
                "count": 20,
                "unit": 1,
                "datatypes": ">H",
                "scaling_factor": 100

            }
            ]
        }

        # Prepare everything so we can init the class.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        os.environ["MODBUS_MASTER_PORT"] = "502"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "6"
        os.environ["MODBUS_CONFIG"] = json.dumps(cls.test_modbus_config)

    def test_valid_commands_are_send(self):
        """
        Verify that valid value messages adressing implemented datapoints
        are send on socket.
        """
        # All these message should be valid.
        test_value_msgs = [
            # datapoint_key, datapoint_value
            ["write_coil__19__1",
             "0",
              call.write_coil(address=19, unit=1, value=False)
            ],
            ["write_register__21__1",
             "6",
              call.write_register(address=21, unit=1, value=600)
            ],
            ["write_register__21__1",
             "0",
              call.write_register(address=21, unit=1, value=0)
            ]
        ]

        cn = Connector()
        for datapoint_key, datapoint_value, expected_result in test_value_msgs:
            cn.modbus_connection = MagicMock()
            cn.send_command(
                datapoint_key=datapoint_key, datapoint_value=datapoint_value
            )
            

            actual_send_to_args = cn.modbus_connection.mock_calls
            assert expected_result==actual_send_to_args[-1]

class TestComputeActuatorDatapoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Define test config.
        cls.test_modbus_config = {
            "write_coil": [
                {
                    "address": 19,
                    "unit": 1
                }
            ],
            "write_register": [
            {
                "address": 21,
                "unit": 1,
                "datatypes": ">H",
                "scaling_factor": 100
            }
            ]
        }

        # Prepare everything so we can init the class.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        os.environ["MODBUS_MASTER_PORT"] = "502"
        os.environ["MQTT_BROKER_HOST"] = "localhost"
        os.environ["MQTT_BROKER_PORT"] = "1883"
        os.environ["POLL_SECONDS"] = "6"
        os.environ["MODBUS_CONFIG"] = json.dumps(cls.test_modbus_config)


    def test_actuator_datapoints_parsed_correctly(self):
        """
        Verify that registers are parsed correctly.

        This uses an actual returned raw_msg received with the above
        from a real device.
        """
        cn = Connector()
        expected_datapoints = {
            "write_coil__19__1": "0",
            "write_register__21__1": "0"
            }


        actual_datapoint = cn.compute_actuator_datapoints()
        assert actual_datapoint == expected_datapoints

    def test_actuator_method_ranges_parsed_correctly(self):
        """
        Verify that registers are parsed correctly.

        This uses an actual returned raw_msg received with the above
        from a real device.
        """
        cn = Connector()
        expected_method_ranges = {
            "write_coil": {"19":
                    {
                        "unit": 1
                    }
                },
            "write_register": {"21":
                    {
                        "unit": 1,
                        "datatypes": ">H",
                        "scaling_factor": 100

                    }
                }
                
            }


        actual_method_ranges = cn.compute_method_ranges()
        assert actual_method_ranges == expected_method_ranges

    def test_actuator_datapoints_included(self):
        expected_available_datapoints = {
            "sensor": {},
            "actuator":{
                "write_coil__19__1": "0",
                "write_register__21__1": "0"
            }
        }
        # cad_backup = Connector.computeActuatorDatapoints
        # Connector.computeActuatorDatapoints = MagicMock(
        #     return_value = expected_available_datapoints["actuator"]
        # )
        cn = Connector()
        actual_available_datapoints = cn._initial_available_datapoints
        # Connector.computeActuatorDatapoints = cad_backup
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
            "not_expected_keyword": [],
        }

        self.caplog.clear()
        self.caplog.set_level(logging.WARNING)
        config_json_str = json.dumps(test_config)
        actual_config = Connector.parse_modbus_config(config_json_str)

        assert "not_expected_keyword" not in actual_config


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
                    0: [1, 2, 3, 4, 5],
                    1: [10, 11, 12, 13, 14, 15],
                },
            }

            actual_addresses = Connector.compute_addresses(
                modbus_config=test_config
            )

            assert actual_addresses == expected_addresses
