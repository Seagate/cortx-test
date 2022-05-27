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
from libs.s3 import s3_multipart_test_lib


class TestS3FaultTolerance:
    """S3 FaultTolerance test class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Fixture: perform test setup and teardown."""
        self.log = logging.getLogger(__name__)
        self.s3_obj = s3_test_lib.S3TestLib()
        self.s3_m_obj = s3_multipart_test_lib.S3MultipartTestLib()
        self.fault_flg = False
        self.bucket_name = f"bkt-faulttolerance-{perf_counter_ns()}"
        self.object_name = f"obj-faulttolerance-{perf_counter_ns()}"
        self.test_directory = os.path.join(TEST_DATA_FOLDER, "TestS3FaultTolerance")
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
        bucket_list = self.s3_obj.bucket_list()[1]
        if bucket_list:
            resp = self.s3_obj.delete_multiple_buckets(bucket_list)
            assert_utils.assert_true(resp[0], resp[1])
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        if self.fault_flg:
            resp = S3H_OBJ.s3server_inject_faulttolerance(enable=False)
            assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
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
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = self.s3_obj.bucket_list()
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
        resp = self.s3_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.object_list(self.bucket_name)
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
    @pytest.mark.s3_faulttolerance
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
    @pytest.mark.s3_faulttolerance
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
    @pytest.mark.s3_faulttolerance
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
    @pytest.mark.s3_faulttolerance
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
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = self.s3_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.bucket_name, bktlist)
        self.log.info(
            "Step 3. Using curl, Disable fault injection so that upload of object is "
            "successfully and does not result in amy motr error.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.fault_flg = True
        self.log.info("Step 4. Upload the 6MB file to the bucket created.")
        resp = self.s3_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.object_list(self.bucket_name)
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
    @pytest.mark.s3_faulttolerance
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
            resp = S3H_OBJ.restart_s3server_service(service)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3. Using curl ,inject fault injection so that upload of object fails "
            "and results in motr failure.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4. Upload a 6MB file size object to a bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file_fallocate(self.test_file_path, "6MB")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, resp[1])
        resp = S3H_OBJ.update_s3config(
            parameter="S3_MAX_EXTENDED_OBJECTS_IN_FAULT_MODE", value=response[-1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Verify if more than 4 fragments gets created if S3_MAX_EXT value is set to "
            "4 in s3config.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
    @pytest.mark.tags("TEST-19497")
    @pytest.mark.parametrize("object_size", ["50k"])
    def test_19497(self, object_size):
        """Test to verify getobject api when object is fragmented with file size 50k."""
        self.log.info("STARTED: Getobject api when object is fragmented with file size %s",
                      object_size)
        self.log.info("STEP 1: Create a  file using fallocate cmd. %s", self.test_file_path)
        resp = system_utils.create_file_fallocate(
            self.test_file_path, size=object_size)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 1: Created a %s file using fallocate cmd", object_size)

        self.log.info("STEP 2: Create a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = self.s3_obj.bucket_list()
        assert_utils.assert_in(self.bucket_name, bktlist)
        self.log.info("STEP 2: Created a bucket with name %s", self.bucket_name)

        self.log.info("STEP 3: Using curl ,inject fault injection so that "
                      "upload of object fails and results in motr failure.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.fault_flg = True
        self.log.info(
            "STEP 3: fault injection Injected so that "
            "upload of object fails and results in motr failure.")

        self.log.info("STEP 4: Uploading an object %s to a bucket %s",
                      self.object_name, self.bucket_name)
        resp = self.s3_obj.object_upload(self.bucket_name, self.object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 4: Uploaded an object to a bucket")

        self.log.info("Verifying object is successfully uploaded")
        resp = self.s3_obj.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1])
        self.log.info("Verified that object is uploaded successfully")

        self.log.info(
            "Step 5: Verify the Validate that object list index contains extended entries"
            " using m0kv. Verify in m0kv output. Main object size and fragment size. No of"
            " fragments in json value of main object.")
        resp = S3H_OBJ.verify_and_validate_created_object_fragement(self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 5: Verified and Validated that object "
                      "list index contains extended entries using m0kv")

        self.log.info("STEP 6: Verify getobject and getobject with "
                      "read range and verify the size and range ouput")
        resp = self.s3_obj.get_object(self.bucket_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("STEP 6: Verify getobject and getobject with "
                      "read range and verify the size and range ouput")

        self.log.info("ENDED: Getobject api when object is fragmented with file size 50k.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
    @pytest.mark.tags("TEST-19499")
    @pytest.mark.parametrize("object_size", ["33k"])
    def test_19499(self, object_size):
        """Test getobject api when object is fragmented with file size 33k."""
        self.test_19497(object_size)
        self.log.info("ENDED: getobject api when object is fragmented with file size 33k.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
    @pytest.mark.tags("TEST-19501")
    @pytest.mark.parametrize("object_size", ["4MB"])
    def test_19501(self, object_size):
        """Test to verify getobject api when object is fragmented with file size 4MB."""
        self.test_19497(object_size)
        self.log.info("ENDED: Getobject api when object is fragmented with file size 4MB.")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
    @pytest.mark.tags("TEST-19504")
    @pytest.mark.parametrize("object_size", ["8MB"])
    def test_19504(self, object_size):
        """Test to verify getobject api when object is fragmented with file size 8MB."""
        self.test_19497(object_size)
        self.log.info("ENDED: Copying an s3 object to a local file")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
    @pytest.mark.tags("TEST-19505")
    @pytest.mark.parametrize("object_size", ["4MB"])
    def test_19505(self, object_size):
        """Test to verify if normal getobject works fine with faultinjection disabled."""
        self.log.info("STARTED: getobject works fine with faultinjection disabled")

        self.log.info("STEP 1: Create a 4MB file using fallocate cmd.")
        resp = system_utils.create_file_fallocate(
            self.test_file_path, size=object_size)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 1: Created a 4MB file using fallocate cmd.")

        self.log.info("SETP 2: Create a New Bucket %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = self.s3_obj.bucket_list()
        assert_utils.assert_in(self.bucket_name, bktlist)
        self.log.info("STEP 2: New bucket created %s", self.bucket_name)

        self.log.info("STEP 3: Disable Fault Injection")
        resp = S3H_OBJ.s3server_inject_faulttolerance()
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 3: Fault Injection Disabled")

        self.log.info("STEP 4: Upload the 4MB file to the bucket %s", self.bucket_name)
        resp = self.s3_obj.object_upload(self.bucket_name, self.object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 4: Uploaded the 4MB file to the bucket %s", self.bucket_name)

        self.log.info("STEP 5: Verify object list index contains extended entries using m0kv ")
        resp = S3H_OBJ.verify_and_validate_created_object_fragement(self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 5: Verified that No fragmented entries should be listed")

        self.log.info("STEP 6: Run getobject and check the output.")
        resp = self.s3_obj.get_object(self.bucket_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("STEP 6: Verified getobject output")

        self.log.info("ENDED: getobject works fine with faultinjection disabled")

    @pytest.mark.skip(reason="F-24A feature under development.")
    @pytest.mark.s3_ops
    @pytest.mark.s3_faulttolerance
    @pytest.mark.tags("TEST-19506")
    @pytest.mark.parametrize("object_size", ["33k"])
    def test_19506(self, object_size):
        """Test to verify if error is thrown with getobjectapi with invalid readrange."""
        self.log.info("STARTED: getobjectapi with invalid readrange.")

        self.log.info("STEP 1: Create a 33k file using fallocate cmd.")
        resp = system_utils.create_file_fallocate(
            self.test_file_path, size=object_size)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 1: 33k file using fallocate cmd is created.")

        self.log.info("SETP 2: Create a New Bucket %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        bktlist = self.s3_obj.bucket_list()
        assert_utils.assert_in(self.bucket_name, bktlist)
        self.log.info("STEP 2: New bucket created %s", self.bucket_name)

        self.log.info("STEP 3: Using curl ,inject fault injection so that "
                      "upload of object fails and results in motr failure.")
        resp = S3H_OBJ.s3server_inject_faulttolerance(enable=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.fault_flg = True
        self.log.info("STEP 3: fault injection Injected so that upload of "
                      "object fails and results in motr failure.")

        self.log.info("STEP 4: Upload the 33k file to the bucket %s", self.bucket_name)
        resp = self.s3_obj.object_upload(self.bucket_name, self.object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 4: Uploaded the 33k file to the bucket %s", self.bucket_name)

        self.log.info(
            "Step 5: Verify the Validate that object list index contains extended entries"
            " using m0kv. Verify in m0kv output. Main object size and fragment size. No of"
            " fragments in json value of main object.")
        resp = S3H_OBJ.verify_and_validate_created_object_fragement(self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 5: Verified and Validated that "
                      "object list index contains extended entries using m0kv")

        self.log.info("STEP 6: Run getobject and check the output.")
        resp = self.s3_obj.get_object(self.bucket_name, self.test_file_path)
        assert resp[0], resp[1]
        resp = self.s3_m_obj.get_object(self.bucket_name,
                                        self.test_file_path,
                                        ranges="1048576-3145728")
        assert resp[0], resp[1]
        self.log.info("STEP 6: Verified getobject output")

        self.log.info("ENDED: getobjectapi with invalid readrange.")
