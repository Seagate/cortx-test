#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
"""This file contains s3 Object test scenario for io stability."""

import hashlib
import os
import unittest
from io import BytesIO
from unittest import mock
from unittest.mock import patch

from libs.io.s3api.s3_object_ops import S3Object

KIB = 1024
MIB = KIB * KIB


class S3ObjectTestCase(unittest.TestCase):
    """Tests suite for generic methods"""

    @staticmethod
    def read_part(content, offset, size):
        """Return size bytes' data from offset"""
        return content[offset:offset + size]

    @patch('os.path.getsize')
    def test_checksum_part_file_positive_less_1mib(self, mock_getsize):
        """Calculate check of less than 1 MB chunk"""
        file_size = 10 * MIB
        offset = 10
        read_size = KIB
        data = os.urandom(file_size)
        expected_logs = [
            f'DEBUG:libs.io.s3api.s3_object_ops:Reading less than {1 * MIB}',
            f'DEBUG:libs.io.s3api.s3_object_ops:Reading {KIB} from starting offset {offset}']
        mock_getsize.return_value = file_size
        with self.assertLogs('libs.io.s3api.s3_object_ops', level='DEBUG') as logs:
            with mock.patch("builtins.open", mock.mock_open()) as mock_open:
                mock_open.side_effect = [BytesIO(data)]
                ret = S3Object.checksum_part_file("file_path", offset, read_size)
                file_hash = hashlib.sha256(self.read_part(data, offset, read_size))
                self.assertEqual(ret, file_hash.hexdigest())
            self.assertEqual(logs.output, expected_logs)

    @patch('os.path.getsize')
    def test_checksum_part_file_positive_more_1mib(self, mock_getsize):
        """Calculate check of more than 1 MB chunk"""
        file_size = 10 * MIB
        offset = 10
        read_size = (2 * MIB) + 10
        data = os.urandom(file_size)
        expected_logs = [
            f'DEBUG:libs.io.s3api.s3_object_ops:Reading more than {1 * MIB}',
            f'DEBUG:libs.io.s3api.s3_object_ops:Reading {MIB} from starting offset {offset}',
            f'DEBUG:libs.io.s3api.s3_object_ops:Reading {MIB} from starting offset {10 + MIB}',
            f'DEBUG:libs.io.s3api.s3_object_ops:Reading {10} from starting offset {10 + (MIB * 2)}']
        mock_getsize.return_value = file_size
        with self.assertLogs('libs.io.s3api.s3_object_ops', level='DEBUG') as logs:
            with mock.patch("builtins.open", mock.mock_open()) as mock_open:
                mock_open.side_effect = [BytesIO(data)]
                ret = S3Object.checksum_part_file("file_path", offset, read_size)
                file_hash = hashlib.sha256(self.read_part(data, offset, read_size))
                self.assertEqual(ret, file_hash.hexdigest())
            self.assertEqual(logs.output, expected_logs)

    @patch('os.path.getsize')
    def test_checksum_part_file_negative_1(self, mock_getsize):
        """Calculate checksum when requested size is more than actual file size"""
        file_size = 10 * MIB
        offset = 10
        read_size = MIB
        mock_getsize.return_value = file_size
        with self.assertRaises(IOError) as context:
            S3Object.checksum_part_file("file_path", offset, read_size)
            self.assertTrue(f"is less than file size {file_size}" in context.exception)


if __name__ == '__main__':
    unittest.main()
