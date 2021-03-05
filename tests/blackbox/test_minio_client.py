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

"""Miniio Client test module."""

import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml, read_content_json
from commons.utils.system_utils import execute_cmd, create_file, remove_file
from commons.utils.assert_utils import \
    assert_true, assert_false, assert_in, assert_not_in, assert_equal
from libs.s3 import s3_test_lib
from libs.s3 import S3H_OBJ, ACCESS_KEY, SECRET_KEY
s3_test_obj = s3_test_lib.S3TestLib()
blackbox_cnf = read_yaml("config/blackbox/test_minio_client.yaml")[1]
CM_CFG = read_yaml("config/common_config.yaml")[1]


class TestMinioClient:
    """Black box minio client Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.minio_cnf = blackbox_cnf["minio_cfg"]
        cls.file_path = cls.minio_cnf["file_path"]
        cls.file_size = cls.minio_cnf["file_size"]
        cls.timestamp = str(time.time())

    @CTFailOn(error_handler)
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite steps if any.
        Initializing common variable which will be used in test
        """
        self.log.info("STARTED: Setup operations")
        access, secret = ACCESS_KEY, SECRET_KEY
        path = CM_CFG["minio_path"]
        if access != read_content_json(path)["hosts"]["s3"]["accessKey"]:
            S3H_OBJ.configure_minio(access, secret)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform all cleanup operations.
        This function will delete buckets and objects uploaded to that bucket.
        It will also delete the local files.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info(
            "Deleting all buckets/objects created during TC execution")
        bucket_list = s3_test_obj.bucket_list()[1]
        if bucket_list:
            pref_list = [
                each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                    self.minio_cnf["bkt_name_prefix"])]
            s3_test_obj.delete_multiple_buckets(pref_list)
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("Deleting files created locally for object")
        if self.minio_cnf["file_path"]:
            remove_file(self.minio_cnf["file_path"])
        self.log.info("Local file was deleted")
        self.log.info("ENDED: Teardown Operations")

    def create_bucket(self, bucket_name):
        """
        Creating a new bucket.

        :param str bucket_name: Name of bucket to be created
        :return: None
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", bucket_name)
        resp = execute_cmd(
            self.minio_cnf["create_bkt_cmd"].format(bucket_name), remote=False)
        assert_true(resp[0], resp)
        assert_in(self.minio_cnf["success_msg"], resp[1], resp[1])
        self.log.info(
            "Step 1: Bucket is created with name %s", bucket_name)

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2345(self):
        """Create single bucket using Minio Client."""
        self.log.info("STARTED: Create single bucket using Minio Client")
        test_cfg = blackbox_cnf["test_2345"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Verifying that %s bucket is created",
            bucket_name)
        resp = s3_test_obj.bucket_list()
        assert_true(resp[0], resp[1])
        assert_in(bucket_name, resp[1], resp[1])
        self.log.info(
            "Step 2: Verified that %s bucket was created",
            bucket_name)
        self.log.info("ENDED: Create single bucket using Minio Client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7537 ")
    @CTFailOn(error_handler)
    def test_create_multiple_bucket_2346(self):
        """Create multiple buckets using Minion client."""
        self.log.info("STARTED: Create multiple buckets using Minion client")
        test_cfg = blackbox_cnf["test_2346"]
        bucket_name_1 = test_cfg["bucket_name_1"].format(self.timestamp)
        bucket_name_2 = test_cfg["bucket_name_2"].format(self.timestamp)
        self.log.info("Step 1: Creating two buckets simultaneously")
        resp = execute_cmd(
            test_cfg["cr_two_bkt_cmd"].format(
                bucket_name_1, bucket_name_2), remote=False)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created two buckets simultaneously")
        self.log.info("Step 2: Verifying buckets are created")
        resp = s3_test_obj.bucket_list()
        assert_true(resp[0], resp[1])
        assert_in(bucket_name_1, resp[1])
        assert_in(bucket_name_2, resp[1])
        self.log.info("Step 2: Verified that buckets are created")
        self.log.info("ENDED: Create multiple buckets using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7545 ")
    @CTFailOn(error_handler)
    def test_list_bucket_2347(self):
        """List buckets using Minion client."""
        self.log.info("Started: List buckets using Minion client")
        test_cfg = blackbox_cnf["test_2347"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        self.create_bucket(bucket_name)
        self.log.info("Step 2: Listing buckets")
        resp = execute_cmd(test_cfg["lst_bkt_cmd"], remote=False)
        assert_true(resp[0], resp[1])
        assert_in(bucket_name, resp[1], resp)
        self.log.info("Step 2: Buckets are listed")
        self.log.info("Ended: List buckets using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7544")
    @CTFailOn(error_handler)
    def test_max_bucket_2348(self):
        """Max no of buckets supported using Minion Client."""
        self.log.info(
            "STARTED: Max no of buckets supported using Minion Client")
        test_cfg = blackbox_cnf["test_2348"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        self.log.info(
            "Step 1: Creating %s buckets using minio",
            test_cfg["no_of_buckets"])
        for cnt in range(test_cfg["no_of_buckets"]):
            bkt_name = "{0}{1}".format(bucket_name, str(cnt))
            cmd = self.minio_cnf["create_bkt_cmd"].format(bkt_name)
            resp = execute_cmd(cmd, remote=False)
            assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created %s buckets using minio",
            test_cfg["no_of_buckets"])
        self.log.info("Step 2: Verifying buckets are created")
        bucket_list = s3_test_obj.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.minio_cnf["bkt_name_prefix"])]
        for each_bucket in pref_list:
            assert_in(each_bucket, bucket_list)
        self.log.info("Step 2: Verified that buckets are created")
        self.log.info("ENDED: Max no of buckets supported using Minion Client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7548")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2349(self):
        """Delete empty bucket using Minion client."""
        self.log.info("STARTED: Delete empty bucket using Minion client")
        test_cfg = blackbox_cnf["test_2349"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Deleting bucket with name %s", bucket_name)
        resp = execute_cmd(
            test_cfg["dlt_bkt_cmd"].format(bucket_name), remote=False)
        assert_true(resp[0], resp)
        self.log.info(
            "Step 2: Bucket is deleted with name %s", bucket_name)
        self.log.info(
            "Step 3: Verifying that %s bucket is deleted",
            bucket_name)
        resp = s3_test_obj.bucket_list()
        assert_true(resp[0], resp[1])
        assert_not_in(
            bucket_name,
            resp[1])
        self.log.info(
            "Step 3: Verified that %s bucket is deleted",
            bucket_name)
        self.log.info("ENDED: Delete empty bucket using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7547")
    @CTFailOn(error_handler)
    def test_delete_bucket_has_obj_2350(self):
        """Delete bucket which has objects using Minion Client."""
        self.log.info(
            "STARTED: delete bucket which has objects using Minion Client")
        test_cfg = blackbox_cnf["test_2350"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        dlt_bkt_cmd = test_cfg["dlt_bkt_cmd"].format(bucket_name)
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 1: Uploading an object to a bucket %s",
            bucket_name)
        create_file(self.file_path, self.file_size)
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Object is uploaded to a bucket %s", bucket_name)
        self.log.info(
            "Step 2: Listing object from a bucket %s", bucket_name)
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info("aa %s", resp)
        assert_equal(self.file_path.split(
            "/")[-1], resp[1].split(" ")[-1].split("/")[-1], resp[1])
        self.log.info(
            "Step 2: Listed object from a bucket %s", bucket_name)
        self.log.info("Step 3: Deleting bucket which has a object")
        resp = execute_cmd(dlt_bkt_cmd, remote=False)
        assert_false(resp[0], resp)
        self.log.info(
            "Step 1: Bucket is deleted with name %s", bucket_name)
        self.log.info(
            "ENDED: delete bucket which has objects using Minion Client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7546")
    @CTFailOn(error_handler)
    def test_create_bucket_existing_name_2351(self):
        """Create bucket using existing bucket name using Minion client."""
        self.log.info(
            "STARTED: Create bucket using existing bucket name using Minion client")
        test_cfg = blackbox_cnf["test_2351"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        self.create_bucket(bucket_name)
        self.log.info("Step 2: Creating a bucket with existing name")
        resp = execute_cmd(
            self.minio_cnf["create_bkt_cmd"].format(bucket_name), remote=False)
        assert_false(resp[0], resp[1])
        assert_in(test_cfg["error_message"], resp[1], resp[1])
        self.log.info(
            "Step 1: Creating a bucket with existing name is failed with error %s",
            test_cfg["error_message"])
        self.log.info(
            "ENDED: Create bucket using existing bucket name using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_list_obj_inside_bucket_2352(self):
        """To list objects inside bucket using Minion client."""
        self.log.info(
            "STARTED: To list objects inside bucket using Minion client")
        test_cfg = blackbox_cnf["test_2352"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", bucket_name)
        create_file(self.file_path, self.file_size)
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", bucket_name)
        self.log.info(
            "Step 3: Listing object from a bucket %s", bucket_name)
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        assert_equal(self.file_path.split(
            "/")[-1], resp[1].split(" ")[-1].split("/")[-1], resp[1])
        self.log.info(
            "Step 3: Listed object from a bucket %s", bucket_name)
        self.log.info(
            "ENDED: To list objects inside bucket using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7541")
    @CTFailOn(error_handler)
    def test_del_obj_from_bucket_2353(self):
        """Delete an object from bucket using Minion client."""
        self.log.info(
            "STARTED: Delete an object from bucket using Minion client")
        test_cfg = blackbox_cnf["test_2353"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        dlt_obj_cmd = test_cfg["dlt_obj"].format(
            bucket_name, self.file_path.split("/")[-1])
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", bucket_name)
        create_file(self.file_path, self.file_size)
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", bucket_name)
        self.log.info("Step 3: Deleting an object from a bucket")
        resp = execute_cmd(dlt_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Object is deleted from a bucket")
        self.log.info("Step 4: Verifying that object is deleted from a bucket")
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        assert_equal(test_cfg["str_length"], len(resp[1]), resp[1])
        self.log.info("Step 4: Verified that object is deleted from a bucket")
        self.log.info(
            "ENDED: Delete an object from bucket using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7542")
    @CTFailOn(error_handler)
    def test_copy_obj_from_bucket_2354(self):
        """Copy object from bucket using Minion client."""
        self.log.info("STARTED: copy object from bucket using Minion client")
        test_cfg = blackbox_cnf["test_2354"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", bucket_name)
        create_file(self.file_path, self.file_size)
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", bucket_name)
        self.log.info("Step 3: Verifying that object is copied from a bucket")
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        assert_equal(self.file_path.split(
            "/")[-1], resp[1].split(" ")[-1].split("/")[-1], resp[1])
        self.log.info("Step 3: Verified that object is uploaded to a bucket")
        self.log.info("ENDED: copy object from bucket using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7538")
    @CTFailOn(error_handler)
    def test_upload_large_obj_2355(self):
        """Upload object of large size of(5gb) using Minion Client."""
        self.log.info(
            "STARTED: upload object of large size of(5gb) using Minion Client")
        test_cfg = blackbox_cnf["test_2355"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        self.create_bucket(bucket_name)
        self.log.info("Step 2: Creating a file of size 5GB")
        create_file(self.file_path, test_cfg["file_size"])
        self.log.info("Step 2: Created a file of size 5GB")
        self.log.info(
            "Step 3: Uploading an object to a bucket %s", bucket_name)
        create_file(self.file_path, self.file_size)
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Object is uploaded to a bucket %s", bucket_name)
        self.log.info("Step 4: Verifying that object is uploaded to a bucket")
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        assert_equal(self.file_path.split(
            "/")[-1], resp[1].split(" ")[-1].split("/")[-1], resp[1])
        self.log.info("Step 4: Verified that object is uploaded to a bucket")
        self.log.info(
            "ENDED: upload object of large size of(5gb) using Minion Client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7540")
    @CTFailOn(error_handler)
    def test_display_file_content_2357(self):
        """Display the contents of a text file using Minion client."""
        self.log.info(
            "STARTED: Display the contents of a text file using Minion client")
        test_cfg = blackbox_cnf["test_2357"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        display_content = test_cfg["display_cont"].format(
            bucket_name, self.file_path.split("/")[-1])
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", bucket_name)
        create_file(self.file_path, self.file_size)
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", bucket_name)
        self.log.info("Step 3: Listing object from a bucket")
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        assert_equal(self.file_path.split(
            "/")[-1], resp[1].split(" ")[-1].split("/")[-1], resp[1])
        self.log.info("Step 2: Verified that object is listed from a bucket")
        self.log.info("Step 3: Displaying content of a text file")
        resp = execute_cmd(display_content, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(resp[1])
        self.log.info("Step 3: Displayed content of a text file")
        self.log.info(
            "ENDED: Display the contents of a text file using Minion client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7539")
    @CTFailOn(error_handler)
    def test_display_few_lines_2358(self):
        """Display the first few lines of a text file using Minion Client."""
        self.log.info(
            "STARTED: Display the first few lines of a text file using Minion Client")
        test_cfg = blackbox_cnf["test_2358"]
        bucket_name = test_cfg["bucket_name"].format(self.timestamp)
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(bucket_name)
        head_obj_cmd = test_cfg["head_obj"].format(
            test_cfg["no_of_lines"], bucket_name, self.file_path.split("/")[-1])
        self.create_bucket(bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", bucket_name)
        # Creating a text file to upload as a object
        if os.path.exists(self.file_path):
            remove_file(self.file_path)
        with open(self.file_path, test_cfg["mode"]) as file_ptr:
            file_ptr.write(test_cfg["upload_data"])
        resp = execute_cmd(upload_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", bucket_name)
        self.log.info("Step 3: Listing object from a bucket")
        resp = execute_cmd(list_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        assert_equal(self.file_path.split(
            "/")[-1], resp[1].split(" ")[-1].split("/")[-1], resp[1])
        self.log.info("Step 3: Verified that object is listed from a bucket")
        self.log.info("Step 4: Performing head object")
        resp = execute_cmd(head_obj_cmd, remote=False)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Displaying first few lines of a text file : %s",
            resp[1])
        self.log.info("Step 4: Performed head object")
        self.log.info(
            "ENDED: Display the first few lines of a text file using Minion Client")
