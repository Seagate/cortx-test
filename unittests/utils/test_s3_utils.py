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
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""Test S3 utility library module."""

import logging
import os
from hashlib import md5
from random import shuffle
from time import perf_counter_ns

import pytest

from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import s3_utils
from commons.utils import system_utils


class TestS3Utils:
    """Test S3 utility library class."""

    @classmethod
    def setup_class(cls):
        """Initialize variables."""
        cls.log = logging.getLogger(__name__)
        cls.dpath = os.path.join(TEST_DATA_FOLDER, "TestS3Utils")
        cls.fpath = None

    def setup_method(self):
        """Pre-requisite will be invoked prior to each test case."""
        self.fpath = os.path.join(self.dpath, f"s3utils-{perf_counter_ns()}")
        if not system_utils.path_exists(self.dpath):
            system_utils.make_dirs(self.dpath)

    def teardown_method(self):
        """Teardown will be invoked after each test case."""
        if system_utils.path_exists(self.dpath):
            system_utils.remove_dirs(self.dpath)

    def test_calc_checksum(self):
        """Test calculating an checksum using encryption algorithm."""
        self.log.info("STARTED: Test calculate checksum.")
        self.log.info("Create file %s with 10MB size", self.fpath)
        resp = system_utils.create_file(self.fpath, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Calculate checksum with part size 1024 bytes.")
        checksum1 = s3_utils.calc_checksum(self.fpath, 1024)
        self.log.info("checksum1: %s", checksum1)
        self.log.info("Calculate checksum without part size.")
        checksum2 = s3_utils.calc_checksum(self.fpath)
        self.log.info("checksum2: %s", checksum2)
        assert_utils.assert_not_equal(checksum1, checksum2, "Error: Checksum matched.")
        self.log.info("Create file %s with 20MB size", self.fpath)
        resp = system_utils.create_file(self.fpath, count=20)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Calculate checksum without part size.")
        checksum3 = s3_utils.calc_checksum(self.fpath)
        self.log.info("checksum3: %s", checksum3)
        assert_utils.assert_not_equal(checksum1, checksum3, "Error: Checksum matched.")
        checksum4 = s3_utils.calc_checksum(self.fpath)
        self.log.info("checksum4: %s", checksum4)
        assert_utils.assert_equal(checksum3, checksum4, "Failed to match checksum.")
        self.log.info("ENDED: Test calculate checksum.")

    def test_create_multipart_json(self):
        """Test create multipart json."""
        json_path = os.path.join(self.dpath, "sample.json")
        parts = []
        num_list = list(range(1, 11))
        for i in num_list:
            parts.append({"PartNumber": i, "ETag": md5(os.urandom(10)).hexdigest()})  # nosec
        resp = s3_utils.create_multipart_json(json_path, parts)
        assert_utils.assert_true(resp[0], resp)
        shuffle(num_list)
        parts = []
        for j in num_list:
            parts.append({"PartNumber": j, "ETag": md5(os.urandom(10)).hexdigest()})  # nosec
        resp = s3_utils.create_multipart_json(json_path, parts)
        assert_utils.assert_true(resp[0], resp)

    @pytest.mark.parametrize("total_parts", [1, 10, 20, 100])
    @pytest.mark.parametrize("count", [1000, 3000])
    def test_get_aligned_parts(self, total_parts, count):
        """Test get aligned parts."""
        self.log.info("STARTED: get aligned parts.")
        resp = system_utils.create_file(self.fpath, count=count)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_utils.get_aligned_parts(self.fpath, total_parts=total_parts)
        self.log.info(resp.keys())
        resp = s3_utils.get_aligned_parts(self.fpath, total_parts=total_parts, random=True)
        self.log.info(resp.keys())
        self.log.info("ENDED: get aligned parts.")

    @pytest.mark.parametrize("total_parts", [1, 10, 20, 100])
    @pytest.mark.parametrize("count", [1000, 3000])
    def test_get_unaligned_parts(self, total_parts, count):
        """Test get unaligned parts."""
        self.log.info("STARTED: get aligned parts.")
        resp = system_utils.create_file(self.fpath, count=count)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_utils.get_unaligned_parts(self.fpath, total_parts=total_parts)
        self.log.info(resp.keys())
        resp = s3_utils.get_unaligned_parts(self.fpath, total_parts=total_parts, random=True)
        self.log.info(resp.keys())
        self.log.info("ENDED: get aligned parts.")
