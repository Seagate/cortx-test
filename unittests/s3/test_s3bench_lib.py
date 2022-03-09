#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""Unit tests for s3bench library."""

import json
import sys
import unittest
from io import StringIO

from unittest import mock

from src.io.tools.s3bench import S3bench


class S3benchTestCase(unittest.TestCase):
    """S3bench library tests"""
    @mock.patch("src.s3.tools.s3bench.S3bench.install_s3bench")
    def test_check_log_file_error_report(self, mock_install_s3bench):
        """Test with Error Count in report file"""
        mock_install_s3bench.return_value = True
        s3bench = S3bench("Access", "Secret", "https://s3.seagate.com", "test-12", 1, 2, 1, 40, 10)
        s3bench_run_report = {"Parameters": {"copies": 0},
                              "Tests": [{"Errors Count": 1, "Operation": "HeadObj"}]}
        with mock.patch("builtins.open", mock.mock_open(
                read_data=json.dumps(s3bench_run_report))) as _:
            self.assertEqual(s3bench.check_log_file_error("", ""),
                             (False, {'Write Errors': 0, 'HeadObj Errors': 1,
                                      'Validate Errors': 0, 'Read Errors': 0}))

    @mock.patch("src.s3.tools.s3bench.S3bench.install_s3bench")
    def test_check_log_file_error_cli(self, mock_install_s3bench):
        """Test with error no report file, with error strings"""
        mock_install_s3bench.return_value = True
        s3bench = S3bench("Access", "Secret", "https://s3.seagate.com", "test-12", 1, 2, 1, 40, 10)
        s3bench_run_report = {"Parameters": {"copies": 0},
                              "Tests": [{"Errors Count": 6, "Operation": "Write"}]}
        with mock.patch("builtins.open", mock.mock_open()) as mock_open:
            mock_open.side_effect = [StringIO(json.dumps(s3bench_run_report) + "corrupt"),
                                     StringIO(r"^MWrite | 0/400 (0.00%) | time 0s eta 0s | errors 0"
                                              r"                               ^MWrite | 1/400 (0.2"
                                              r"5%) | time 1s eta 6m48s | errors 0                 "
                                              r"           ^MWrite | 2/400 (0.50%) | time 1s eta 3m"
                                              r"24s | errors 0                            ^MWrite |"
                                              r" 3/400 (0.75%) | time 1s eta 2m19s | errors 0      "
                                              r"                      ^MWrite | 4/400 (1.00%) | tim"
                                              r"e 1s eta 1m44s | errors 0                          "
                                              r"  ^MWrite | 5/400 (1.25%) | time 1s eta 1m28s | err"
                                              r"ors 0                            ^MWrite | 6/400 (1"
                                              r".50%) | time 1s eta 2m3s | errors 0                "
                                              r"             ^MWrite | 7/400 (1.75%) | time 1s eta "
                                              r"1m45s | errors 1                            ^MWrite"
                                              r" | 8/400 (2.00%) | time 1s eta 1m33s | errors 2    "
                                              r"                        ^MWrite | 9/400 (2.25%) | t"
                                              r"ime 1s eta 1m25s | errors 3                        "
                                              r"    ^MWrite | 10/400 (2.50%) | time 2s eta 1m21s | "
                                              r"errors 4                           ^MWrite | 11/400"
                                              r" (2.75%) | time 2s eta 1m34s | errors 5            "
                                              r"              ^MWrite | 12/400 (3.00%) | time 3s et"
                                              r"a 1m44s | errors 6  ")]
            self.assertEqual(s3bench.check_log_file_error("", ""),
                             (False, {'Write Errors': 6, 'HeadObj Errors': 0,
                                      'Validate Errors': 0, 'Read Errors': 0}))

    @mock.patch("src.s3.tools.s3bench.S3bench.install_s3bench")
    def test_check_log_file_error(self, mock_install_s3bench):
        """Test with error in report file"""
        mock_install_s3bench.return_value = True
        s3bench = S3bench("Access", "Secret", "https://s3.seagate.com", "test-12", 1, 2, 1, 40, 10)
        s3bench_run_report = {"Parameters": {"copies": 0},
                              "Tests": [{"Errors Count": 0, "Operation": "Write"},
                                        {"Errors Count": 1, "Operation": "Read"}]}
        with mock.patch("builtins.open", mock.mock_open(
                read_data=json.dumps(s3bench_run_report))) as _:
            captured_output = StringIO()
            sys.stdout = captured_output
            ret = s3bench.check_log_file_error("", "")
            self.assertIn(captured_output.getvalue(), "Read operation failed with 1 errors")
            self.assertEqual(ret, (False, {'Write Errors': 0, 'HeadObj Errors': 0,
                                           'Validate Errors': 0, 'Read Errors': 1}))


if __name__ == '__main__':
    unittest.main()
