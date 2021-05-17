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

"""S3 FaultTolerance test module."""

import os
from time import perf_counter_ns

import logging
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.constants import const
from commons.params import TEST_DATA_FOLDER
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib

S3_OBJ = s3_test_lib.S3TestLib()


class TestS3Faulttoelrance:
    """S3 FaultTolerance test class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Fixture: perform test setup and teardown."""
        self.log = logging.getLogger(__name__)
        self.fault_flg = False
        self.bucket_name = "bkt-faulttolerance-{}".format(perf_counter_ns())
        self.object_name = "obj-faulttolerance-{}".format(perf_counter_ns())
        self.test_directory = os.path.join(
            TEST_DATA_FOLDER, "TestS3Faulttoelrance")
        if not system_utils.path_exists(self.test_directory):
            system_utils.make_dirs(self.test_directory)
        self.test_file_path = os.path.join(
            self.test_directory, self.object_name)
        self.log.info(
            "S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE value in s3config.yaml should be "
            "set to more than 1.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE", value=2)
        assert_utils.assert_true(status, response)
        yield
        self.log.info(
            "S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE value in s3config.yaml should be "
            "set to 1.")
        resp = S3H_OBJ.update_s3config(
            parameter="S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE", value=response[-1])
        assert_utils.assert_true(resp[0], resp[1])
        bucket_list = S3_OBJ.bucket_list()[1]
        if bucket_list:
            resp = S3_OBJ.delete_multiple_buckets(bucket_list)
            assert_utils.assert_true(resp[0], resp[1])
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        if self.fault_flg:
            resp = S3H_OBJ.s3server_inject_faulttolerance(enable=False)
            assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-18838")
    @pytest.mark.parametrize("object_size", ["50k"])
    def test_18838(self, object_size):
        """
        S3 FaultTolerance.

        Verify post put object write failure of 50k file size, new object fragment is created.
        """
        self.log.info(
            "STARTED: Verify post put object write failure of %s file size, new object"
            " fragment is created.", object_size)
        self.log.info("Step 1: Create a 50k file using fallocate cmd.")
        resp = system_utils.create_file_fallocate(
            self.test_file_path, size=object_size)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Create a new bucket.")
        resp = S3_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = S3_OBJ.bucket_list()
        assert_utils.assert_in(self.bucket_name, bktlist)
        self.log.info(
            "Step 3: Using curl ,inject fault injection so that upload of object fails"
            " and results in motr failure.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.fault_flg = True
        self.log.info(
            "Step 4: Upload the %s file to the bucket created.",
            object_size)
        resp = S3_OBJ.object_upload(
            self.bucket_name,
            self.object_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1])
        self.log.info(
            "Step 5: Verify the Validate that object list index contains extended entries"
            " using m0kv. Verify in m0kv output. Main object size and fragment size. No of"
            " fragments in json value of main object.")
        resp = S3H_OBJ.verify_and_validate_created_object_fragement(
            self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Verify post put object write failure of 50k file size, new object"
            " fragment is created.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-18839")
    @pytest.mark.parametrize("object_size", ["33k"])
    def test_18839(self, object_size):
        """
        S3 FaultTolerance.

        Verify post put object write failure of 33k file size, new object fragment is created.
        """
        self.test_18838(object_size)
        self.log.info(
            "ENDED: Verify post put object write failure of 33k file size, new object"
            " fragment is created.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-18840")
    @pytest.mark.parametrize("object_size", ["4MB"])
    def test_18840(self, object_size):
        """
        S3 FaultTolerance.

        Verify post put object write failure of 4mb file size, new object fragment is created.
        """
        self.test_18838(object_size)

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-18841")
    @pytest.mark.parametrize("object_size", ["6MB"])
    def test_18841(self, object_size):
        """
        S3 FaultTolerance.

        Verify post put object write failure of 6mb file size, new object fragment is created.
        """
        self.test_18838(object_size)

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-18842")
    @CTFailOn(error_handler)
    def test_18842(self):
        """
        S3 FaultTolerance.

        Verify if normal putobject works fine with faultinjection disabled.
        """
        self.log.info(
            "STARTED: Verify if normal putobject works fine with faultinjection disabled.")
        self.log.info("Step 1. Create a 4MB file using fallocate cmd.")
        resp = system_utils.create_file_fallocate(self.test_file_path, "4MB")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2. Create a new bucket.")
        resp = S3_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = S3_OBJ.object_list(self.bucket_name)
        assert_utils.assert_in(self.bucket_name, bktlist)
        self.log.info(
            "Step 3. Using curl, Disable fault injection so that upload of object is "
            "successfully and does not result in amy motr error.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.fault_flg = True
        self.log.info("Step 4. Upload the 6MB file to the bucket created.")
        resp = S3_OBJ.object_upload(
            self.bucket_name,
            self.object_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1])
        self.log.info(
            "Step 5. Verify the Validate that object list index contains extended entries"
            " using m0kv")
        resp = S3H_OBJ.verify_and_validate_created_object_fragement(
            self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Verify if normal putobject works fine with faultinjection disabled.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-18843")
    @CTFailOn(error_handler)
    def test_18843(self):
        """
        S3 FaultTolerance.

        Verify if more than 4 fragments gets created if S3_MAX_EXT value is set to 4 in s3config.
        """
        self.log.info(
            "STARTED: Verify if more than 4 fragments gets created if S3_MAX_EXT value is set to "
            "4 in s3config.")
        self.log.info("Step 1. Change the value to 6 in s3config.yaml for "
                      "S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE parameter.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE", value=4)
        assert_utils.assert_true(status, response)
        self.log.info(
            "Step 2. Restart the s3services for changes to take effect.")
        for service in [const.SLAPD, const.HAPROXY, const.S3AUTHSERVER]:
            resp = S3H_OBJ.self.restart_s3server_service(service)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3. Using curl ,inject fault injection so that upload of object fails "
            "and results in motr failure.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4. Upload a 6MB filesize object to a bucket.")
        resp = S3_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file_fallocate(self.test_file_path, "6MB")
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.object_upload(
            self.bucket_name,
            self.object_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, resp[1])
        resp = S3H_OBJ.update_s3config(
            parameter="S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE", value=response[-1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Verify if more than 4 fragments gets created if S3_MAX_EXT value is set to "
            "4 in s3config.")
