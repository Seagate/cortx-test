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
#

"""Test S3 utility library module."""

import os
import time
import logging
from random import shuffle
from hashlib import md5

import pytest

from commons.utils import s3_utils
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER


class TestS3Utils:
    """Test S3 utility library class."""

    def setup_method(self):
        """Function will be invoked prior to each test case."""
        self.log = logging.getLogger(__name__)
        self.dpath = os.path.join(TEST_DATA_FOLDER, "TestS3Utils")
        self.fpath = os.path.join(self.dpath, "s3utils-{}".format(time.perf_counter_ns()))
        if not system_utils.path_exists(self.dpath):
            system_utils.make_dirs(self.dpath)

    def teardown_method(self):
        """Function will be invoked after each test case."""
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
        parts = list()
        num_list = list(range(1, 11))
        for i in num_list:
            parts.append({"PartNumber": i, "ETag": md5(os.urandom(10)).hexdigest()})
        resp = s3_utils.create_multipart_json(json_path, parts)
        assert_utils.assert_true(resp[0], resp)
        shuffle(num_list)
        parts = list()
        for i in num_list:
            parts.append({"PartNumber": i, "ETag": md5(os.urandom(10)).hexdigest()})
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
