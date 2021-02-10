import os
import json
import logging
import unittest

import pytest

from ..main import Connector

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
            ],
        }

        # Prepare everything so we can init the class.
        os.environ["MODBUS_MASTER_IP"] = "localhost"
        os.environ["MODBUS_MASTER_PORT"] = "502"
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

        # Overload the modbus_register_addresses attribute to ensure that
        # this test doesn't fail because of errors in the
        # compute_register_addresses method.
        self.connector.modbus_register_addresses = {
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


class TestComputeRegisterAddresses(unittest.TestCase):

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

        actual_register_addresses = Connector.compute_register_addresses(
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

        actual_register_addresses = Connector.compute_register_addresses(
            modbus_config=test_config
        )

        assert actual_register_addresses == expected_register_addresses
