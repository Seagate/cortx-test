#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""Unit tests for yaml parser."""

import datetime
import json
import unittest
from unittest import mock

from libs.io import yaml_parser

KIB = 1024
MIB = KIB ** 2
GIB = KIB ** 3
TIB = KIB ** 4


class YAMLParserTestCase(unittest.TestCase):
    """Yaml parser tests"""
    def test_yaml_parser(self):
        """Test yaml parser with fixed part & variable part size and object size"""
        test_plan_1 = {
            "test_1": {"TEST_ID": "", "object_size": "100Kib", "result_duration": "1h",
                       "sessions_per_node": 1, "tool": "s3api"},
            "test_2": {"TEST_ID": "", "object_size": "100Kb", "result_duration": "1h",
                       "sessions_per_node": 1, "tool": "s3api"},
            "test_3": {"TEST_ID": "", "object_size": {"start": "50Mib", "end": "100MIB"},
                       "part_size": "5MIB", "result_duration": "1h",
                       "sessions_per_node": 1, "tool": "s3api"},
            "test_4": {"TEST_ID": "", "object_size": "4GIB",
                       "part_size": {"start": "5MIB", "end": "10Mib"}, "result_duration": "2h",
                       "sessions": 5, "tool": "s3bench"}
        }
        with mock.patch("builtins.open", mock.mock_open(
                read_data=json.dumps(test_plan_1))) as _:
            ret = yaml_parser.test_parser("")
            self.assertEqual(100 * KIB, ret["test_1"]["object_size"]["start"])
            self.assertEqual((100 * KIB) + 1, ret["test_1"]["object_size"]["end"])
            self.assertEqual(0, ret["test_1"]["part_size"]["start"])
            self.assertEqual(0, ret["test_1"]["part_size"]["end"])
            self.assertEqual(datetime.timedelta(hours=0), ret["test_1"]["start_time"])
            self.assertEqual(datetime.timedelta(hours=1), ret["test_1"]["result_duration"])

            self.assertEqual(100000, ret["test_2"]["object_size"]["start"])
            self.assertEqual(100001, ret["test_2"]["object_size"]["end"])
            self.assertEqual(0, ret["test_2"]["part_size"]["start"])
            self.assertEqual(0, ret["test_2"]["part_size"]["end"])
            self.assertEqual(datetime.timedelta(hours=1), ret["test_2"]["start_time"])
            self.assertEqual(datetime.timedelta(hours=1), ret["test_2"]["result_duration"])

            self.assertEqual(0, ret["test_3"]["object_size"]["start"])
            self.assertEqual(10 * KIB, ret["test_3"]["object_size"]["end"])
            self.assertEqual(5 * MIB, ret["test_3"]["part_size"]["start"])
            self.assertEqual((5 * MIB) + 1, ret["test_3"]["part_size"]["end"])
            self.assertEqual(datetime.timedelta(hours=2), ret["test_3"]["start_time"])
            self.assertEqual(datetime.timedelta(hours=1), ret["test_3"]["result_duration"])

            self.assertEqual(4 * GIB, ret["test_4"]["object_size"]["start"])
            self.assertEqual((4 * GIB) + 1, ret["test_4"]["object_size"]["end"])
            self.assertEqual(5 * MIB, ret["test_4"]["part_size"]["start"])
            self.assertEqual(10 * MIB, ret["test_4"]["part_size"]["end"])
            self.assertEqual(datetime.timedelta(hours=3), ret["test_4"]["start_time"])
            self.assertEqual(datetime.timedelta(hours=2), ret["test_4"]["result_duration"])


if __name__ == '__main__':
    unittest.main()
