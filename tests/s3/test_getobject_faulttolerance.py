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

"""Object Workflow Operations Test Module."""

import os
import time
import logging
import shutil
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.helpers.host import Host
from config import S3_OBJ_TST, CMN_CFG
from libs.s3 import s3_test_lib, s3_cmd_test_lib, s3_multipart_test_lib
from commons.utils.system_utils import create_file, remove_file, path_exists, make_dirs, cleanup_dir

S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_CMD_OBJ = s3_cmd_test_lib.S3CmdTestLib()
S3_MP_OBJ = s3_multipart_test_lib.S3MultipartTestLib()



class TestGetObjectFaultTolerance:
    """Object Workflow Operations Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup suite method")
        cls.bkt_name_prefix= "faulttolerance_bkt"
        cls.obj_name_prefix= "faulttolerance_obj"
        cls.test_file = "testfile"
        cls.test_dir_path = os.path.join(os.getcwd(), "testdata")
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not os.path.exists(cls.test_dir_path):
            os.makedirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.host_ip = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.hobj = Host(
            hostname=cls.host_ip,
            username=cls.uname,
            password=cls.passwd)
        cls.hobj.connect()
        cls.log.info("Test file path: %s", cls.test_file_path)
        cls.log.info("ENDED: setup suite method")

    @classmethod
    def teardown_class(cls):
        """ """
        cls.hobj.disconnect()

    def setup_method(self):
        """Setup method."""
        self.log.info("STARTED: setup method")
        self.test_file_path = os.path.join(
            self.test_dir_path, self.test_file.format(str(int(time.perf_counter()))))
        self.bucket_name = "{}-{}".format(self.bkt_name_prefix,
                                          str(int(time.perf_counter())))
        self.obj_name = "{}-{}".format(self.obj_name_prefix,
                                          str(int(time.perf_counter())))
        self.log.info("ENDED: setup method")

    def teardown_method(self):
        """Teardown method."""
        self.log.info("STARTED: teardown method")
        self.log.info("Clean : %s", self.folder_path)
        if path_exists(self.folder_path):
            resp = cleanup_dir(self.folder_path)
            self.log.info(
                "cleaned path: %s, resp: %s",
                self.folder_path,
                resp)
        bucket_list = S3_TEST_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in bucket_list[1] if each_bucket.startswith(self.bkt_name_prefix)]
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        if os.path.exists(self.file_path):
            remove_file(self.file_path)
        if os.path.exists(self.folder_path):
            shutil.rmtree(self.folder_path)
        self.log.info("ENDED: teardown method")

    def create_file(self,filesize, filename):
        """ """
        CREATE_FILE_CMD = "fallocate -l {} {}".format(filesize, filename)
        self.hobj.execute_cmd(cmd=CREATE_FILE_CMD, read_lines=True)

    def inject_fault(self):
        """ """
        INJECT_FAULT_CMD = '''curl - i - H "x-seagate-faultinjection:enable,offnonm,motr_obj_write_fail,1,1" - X PUT http://127.0.0.1:28081'''
        resp = self.hobj.execute_cmd(cmd=INJECT_FAULT_CMD, read_lines=True)
        if '200 ok' in resp:
            result=True
        else:
            result = False

        return result, resp

    def create_bucket_put_objects(self, bucket_name, object_count):
        """
        Function will create a bucket with specified name and uploads.

        given no of objects to the bucket.
        :param str bucket_name: Name of a bucket to be created.
        :param int object_count: No of objects to be uploaded into the bucket.
        :return: List of objects uploaded to bucket.
        :rtype: list
        """
        obj_list = []
        self.log.info(
            "Step 1: Creating a bucket with name %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == bucket_name, resp[0]
        self.log.info(
            "Step 1: Created a bucket with name %s", bucket_name)
        self.log.info(
            "Step 2: Uploading %s objects to the bucket ",
            object_count)
        for cnt in range(object_count):
            obj_name = f"{self.obj_name_prefix}{cnt}"
            create_file(
                self.file_path,
                S3_OBJ_TST["s3_object"]["mb_count"])
            resp = S3_TEST_OBJ.put_object(
                bucket_name,
                obj_name,
                self.file_path)
            assert resp[0], resp[1]
            obj_list.append(obj_name)
        self.log.info(
            "Step 2: Uploaded %s objects to the bucket ", object_count)

        return obj_list

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_19497(self):
        """Copying/PUT a local file to s3."""
        self.log.info("STSRTED: Copying/PUT a local file to s3")
        self.log.info(
            "STEP1: Create a 50k file using fallocate cmd. %s", self.test_file_path)

        resp = self.create_file('50k', self.test_file_path)
        assert resp[0], resp[1]

        self.log.info(
            "STEP1: Created a 50k file using fallocate cmd. %s", '50kfile')

        self.log.info("STEP 2: Create a bucket with name %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[0]
        self.log.info("STEP 2: Created a bucket with name %s", self.bucket_name)

        self.log.info(
            "STEP 3: Using curl ,inject fault injection so that upload of object fails and results in motr failure.")
        resp = self.inject_fault()
        assert resp[0], resp[1]
        self.log.info(
            "STEP 3: fault injection Injected so that upload of object fails and results in motr failure.")

        self.log.info("STEP 4: Uploading an object %s to a bucket %s",self.obj_name,self.bucket_name)
        resp = S3_TEST_OBJ.put_object(self.obj_name, self.bucket_name, self.file_path)
        assert resp[0], resp[1]
        self.log.info("STEP 4: Uploaded an object to a bucket")

        self.log.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(self.bucket_name)
        assert resp[0], resp[1]
        assert self.obj_name in resp[1], resp[1]
        self.log.info("Verified that object is uploaded successfully")


        self.log.info("STEP 5: Verify the Validate that object list index contains extended entries using m0kv")

        self.log.info("STEP 5: Verified and Validated that object list index contains extended entries using m0kv")

        self.log.info("STEP 6: Verify in m0kv output : Main object size and fragment size No of fragments.")

        self.log.info("STEP 6: Verified in m0kv output : Main object size and fragment size No of fragments.")

        self.log.info("STEP 7: Verify getobject and getobject with read range and verify the size and range ouput")

        self.log.info("STEP 7: Verify getobject and getobject with read range and verify the size and range ouput")

        self.log.info("Cleanup activity")
        if os.path.exists(self.file_path):
            remove_file(self.file_path)

        self.log.info("ENDED:")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_19499(self):
        """Test getobject api when object is fragmented with file size 33k."""
        self.log.info(
            "STARTED: Copying file/object of different type & size to s3")

        self.log.info(
            "ENDED: Copying file/object of different type & size to s3")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_19501(self):
        """Recursively copying local files to s3."""
        self.log.info("STARTED: Recursively copying local files to s3")

        self.log.info("ENDED: Recursively copying local files to s3")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5502")
    def test_19504(self):
        """Add Object to non existing bucket."""
        self.log.info("STARTED: Add Object to non existing bucket")

        self.log.info("ENDED: Add Object to non existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_19504(self):
        """Copying an s3 object to a local file."""
        self.log.info("STARTED: Copying an s3 object to a local file")

        self.log.info("ENDED: Copying an s3 object to a local file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_19505(self):
        """
        Test to verify if normal getobject works fine
        with faultinjection disabled."""
        self.log.info(
            "STARTED: Recursively copying s3 objects to a local directory")

        self.log.info("STEP 1: Create a 4MB file using fallocate cmd.")
        self.log.info("STEP 1: Created a 4MB file using fallocate cmd.")

        self.log.info("SETP 2: Create a New Bucket %s", self.bucket_name)
        self.log.info("STEP 2: New bucket created %s", self.bucket_name)

        self.log.info("STEP 3: Disable Fault Injection")
        self.log.info("STEP 3: Fault Injection Disabled")

        self.log.info("STEP 4: Upload the 6MB file to the bucket %s", self.bucket_name)
        self.log.info("STEP 4: Uploaded the 6MB file to the bucket %s", self.bucket_name)

        self.log.info("STEP 5: Verify object list index contains extended entries using m0kv ")
        self.log.info("STEP 5: Verified that No fragmented entries should be listed")

        self.log.info("STEP 6: Run getobject and check the output.")
        self.log.info("STEP 6: Verified getobject output")


        self.log.info(
            "ENDED: Recursively copying s3 objects to a local directory")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_19506(self):
        """Test to verify if error is thrown with getobjectapi with invalid readrange."""
        self.log.info("STARTED: getobjectapi with invalid readrange.")

        self.log.info("ENDED: getobjectapi with invalid readrange.")
