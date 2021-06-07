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

"""Minio Client test module."""

import os
import time
import logging
import pytest

from commons.params import TEST_DATA_FOLDER
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.configmanager import get_config_wrapper
from commons.utils import config_utils
from commons.utils import system_utils
from commons.utils import assert_utils
from libs.s3 import s3_test_lib
from libs.s3 import S3H_OBJ, ACCESS_KEY, SECRET_KEY
from config import S3_CFG

S3T_OBJ = s3_test_lib.S3TestLib()
MINIO_CFG = get_config_wrapper(fpath="config/blackbox/test_blackbox.yaml")


class TestMinioClient:
    """Black box minio client Testsuite."""

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite steps if any.
        Initializing common variable which will be used in test
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        resp = system_utils.configre_minio_cloud(
            minio_repo=S3_CFG["minio_repo"],
            endpoint_url=S3_CFG["s3_url"],
            s3_cert_path=S3_CFG["s3_cert_path"],
            minio_cert_path_list=S3_CFG["minio_crt_path_list"],
            access=ACCESS_KEY,
            secret=SECRET_KEY)
        assert_utils.assert_true(
            resp, "failed to setup minio: {}".format(resp))
        resp = system_utils.path_exists(S3_CFG["minio_path"])
        assert_utils.assert_true(
            resp, "minio config not exists: {}".format(
                S3_CFG["minio_path"]))
        minio_dict = config_utils.read_content_json(
            S3_CFG["minio_path"], mode='rb')
        self.log.info(minio_dict)
        if (ACCESS_KEY != minio_dict["aliases"]["s3"]["accessKey"]
                or SECRET_KEY != minio_dict["aliases"]["s3"]["secretKey"]):
            resp = S3H_OBJ.configure_minio(ACCESS_KEY, SECRET_KEY)
            assert_utils.assert_true(
                resp, f'Failed to update keys in {S3_CFG["minio_path"]}')
        self.root_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestMinioClient")
        if not system_utils.path_exists(self.root_path):
            system_utils.make_dirs(self.root_path)
            self.log.info("Created path: %s", self.root_path)

        self.bucket_name = "min-bkt-{}".format(time.perf_counter_ns())
        self.test_file = "minio_client{}.txt".format(time.perf_counter_ns())
        self.file_path = os.path.join(self.root_path, self.test_file)
        self.minio_cnf = MINIO_CFG["minio_cfg"]
        self.buckets_list = list()
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
        # bucket_list = S3T_OBJ.bucket_list()[1]
        for bucket_name in self.buckets_list:
            resp = S3T_OBJ.delete_bucket(bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("The bucket and objects deleted successfully")
        self.log.info("Deleting files created locally for object")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
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
        resp = system_utils.run_local_cmd(
            self.minio_cnf["create_bkt_cmd"].format(bucket_name))
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_in("Bucket created successfully", resp[1], resp[1])
        self.log.info(
            "Step 1: Bucket is created with name %s", bucket_name)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7536")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2345(self):
        """Create single bucket using Minio Client."""
        self.log.info("STARTED: Create single bucket using Minio Client")
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Verifying that %s bucket is created",
            self.bucket_name)
        resp = S3T_OBJ.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.bucket_name, resp[1], resp[1])
        self.log.info(
            "Step 2: Verified that %s bucket was created",
            self.bucket_name)
        self.buckets_list.append(self.bucket_name)
        self.log.info("ENDED: Create single bucket using Minio Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7537")
    @CTFailOn(error_handler)
    def test_create_multiple_bucket_2346(self):
        """Create multiple buckets using Minion client."""
        self.log.info("STARTED: Create multiple buckets using Minion client")
        bucket_name_1 = f"{self.bucket_name}-1"
        bucket_name_2 = f"{self.bucket_name}-2"
        self.log.info("Step 1: Creating two buckets simultaneously")
        resp = system_utils.run_local_cmd(
            self.minio_cnf["cr_two_bkt_cmd"].format(
                bucket_name_1, bucket_name_2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created two buckets simultaneously")
        self.log.info("Step 2: Verifying buckets are created")
        resp = S3T_OBJ.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(bucket_name_1, resp[1])
        assert_utils.assert_in(bucket_name_2, resp[1])
        S3T_OBJ.delete_multiple_buckets(
            bucket_list=[bucket_name_1, bucket_name_2])
        self.log.info("Step 2: Verified that buckets are created")
        self.log.info("ENDED: Create multiple buckets using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7545")
    @CTFailOn(error_handler)
    def test_list_bucket_2347(self):
        """List buckets using Minion client."""
        self.log.info("Started: List buckets using Minion client")
        self.create_bucket(self.bucket_name)
        self.log.info("Step 2: Listing buckets")
        resp = system_utils.run_local_cmd(self.minio_cnf["lst_bkt_cmd"])
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.bucket_name, resp[1], resp)
        self.log.info("Step 2: Buckets are listed")
        self.buckets_list.append(self.bucket_name)
        self.log.info("Ended: List buckets using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7544")
    @CTFailOn(error_handler)
    def test_max_bucket_2348(self):
        """Max no of buckets supported using Minion Client."""
        self.log.info(
            "STARTED: Max no of buckets supported using Minion Client")
        self.log.info(
            "Step 1: Creating %s buckets using minio",
            self.minio_cnf["no_of_buckets"])
        pref_list = list()
        for cnt in range(self.minio_cnf["no_of_buckets"]):
            bkt_name = "{0}{1}".format(self.bucket_name, str(cnt))
            cmd = self.minio_cnf["create_bkt_cmd"].format(bkt_name)
            resp = system_utils.run_local_cmd(cmd)
            assert_utils.assert_true(resp[0], resp[1])
            pref_list.append(bkt_name)
        self.log.info(
            "Step 1: Created %s buckets using minio",
            self.minio_cnf["no_of_buckets"])
        self.log.info("Step 2: Verifying buckets are created")
        bucket_list = S3T_OBJ.bucket_list()[1]
        for each_bucket in pref_list:
            assert_utils.assert_in(each_bucket, bucket_list)
        self.log.info("Cleanup: Deleting created buckets")
        S3T_OBJ.delete_multiple_buckets(
            bucket_list=pref_list)
        self.log.info("Step 2: Verified that buckets are created")
        self.log.info("ENDED: Max no of buckets supported using Minion Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7548")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2349(self):
        """Delete empty bucket using Minion client."""
        self.log.info("STARTED: Delete empty bucket using Minion client")
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Deleting bucket with name %s", self.bucket_name)
        resp = system_utils.run_local_cmd(
            self.minio_cnf["dlt_bkt_cmd"].format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Step 2: Bucket is deleted with name %s", self.bucket_name)
        self.log.info(
            "Step 3: Verifying that %s bucket is deleted",
            self.bucket_name)
        resp = S3T_OBJ.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_not_in(
            self.bucket_name,
            resp[1])
        self.log.info(
            "Step 3: Verified that %s bucket is deleted",
            self.bucket_name)
        self.log.info("ENDED: Delete empty bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7547")
    @CTFailOn(error_handler)
    def test_delete_bucket_has_obj_2350(self):
        """Delete bucket which has objects using Minion Client."""
        self.log.info(
            "STARTED: delete bucket which has objects using Minion Client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        dlt_bkt_cmd = self.minio_cnf["dlt_bkt_cmd"].format(self.bucket_name)
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Uploading an object to a bucket %s",
            self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info(
            "Step 2: Listing object from a bucket %s", self.bucket_name)
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("aa %s", resp)
        assert_utils.assert_in(os.path.basename(
            self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info(
            "Step 2: Listed object from a bucket %s", self.bucket_name)
        self.log.info("Step 3: Deleting bucket which has a object")
        resp = system_utils.run_local_cmd(dlt_bkt_cmd)
        assert_utils.assert_false(resp[0], resp)
        self.log.info(
            "Step 1: Bucket is deleted with name %s", self.bucket_name)
        self.log.info(
            "ENDED: delete bucket which has objects using Minion Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7546")
    @CTFailOn(error_handler)
    def test_create_bucket_existing_name_2351(self):
        """Create bucket using existing bucket name using Minion client."""
        self.log.info(
            "STARTED: Create bucket using existing bucket name using Minion client")
        self.create_bucket(self.bucket_name)
        self.log.info("Step 2: Creating a bucket with existing name")
        resp = system_utils.run_local_cmd(
            self.minio_cnf["create_bkt_cmd"].format(self.bucket_name))
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in("Unable to make bucket", resp[1], resp[1])
        self.log.info(
            "Step 1: Creating a bucket with existing name is failed with error %s",
            "Unable to make bucket")
        self.buckets_list.append(self.bucket_name)
        self.log.info(
            "ENDED: Create bucket using existing bucket name using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7543")
    @CTFailOn(error_handler)
    def test_list_obj_inside_bucket_2352(self):
        """To list objects inside bucket using Minion client."""
        self.log.info(
            "STARTED: To list objects inside bucket using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info(
            "Step 3: Listing object from a bucket %s", self.bucket_name)
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(
            self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info(
            "Step 3: Listed object from a bucket %s", self.bucket_name)
        self.buckets_list.append(self.bucket_name)
        self.log.info(
            "ENDED: To list objects inside bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7541")
    @CTFailOn(error_handler)
    def test_del_obj_from_bucket_2353(self):
        """Delete an object from bucket using Minion client."""
        self.log.info(
            "STARTED: Delete an object from bucket using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        dlt_obj_cmd = self.minio_cnf["dlt_obj"].format(
            self.bucket_name, self.file_path.split("/")[-1])
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Deleting an object from a bucket")
        resp = system_utils.run_local_cmd(dlt_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Object is deleted from a bucket")
        self.log.info("Step 4: Verifying that object is deleted from a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(0, len(resp[1].strip("b''")), resp[1])
        self.log.info("Step 4: Verified that object is deleted from a bucket")
        self.buckets_list.append(self.bucket_name)
        self.log.info(
            "ENDED: Delete an object from bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7542")
    @CTFailOn(error_handler)
    def test_copy_obj_from_bucket_2354(self):
        """Copy object from bucket using Minion client."""
        self.log.info("STARTED: copy object from bucket using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Verifying that object is copied from a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(
            self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 3: Verified that object is uploaded to a bucket")
        self.buckets_list.append(self.bucket_name)
        self.log.info("ENDED: copy object from bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7538")
    @CTFailOn(error_handler)
    def test_upload_large_obj_2355(self):
        """Upload object of large size of(5gb) using Minion Client."""
        self.log.info(
            "STARTED: upload object of large size of(5gb) using Minion Client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        self.create_bucket(self.bucket_name)
        self.log.info("Step 2: Creating a file of size 5GB")
        system_utils.create_file(self.file_path, 5024)
        self.log.info("Step 2: Created a file of size 5GB")
        self.log.info(
            "Step 3: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 4: Verifying that object is uploaded to a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(
            self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 4: Verified that object is uploaded to a bucket")
        self.buckets_list.append(self.bucket_name)
        self.log.info(
            "ENDED: upload object of large size of(5gb) using Minion Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7540")
    @CTFailOn(error_handler)
    def test_display_file_content_2357(self):
        """Display the contents of a text file using Minion client."""
        self.log.info(
            "STARTED: Display the contents of a text file using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        display_content = self.minio_cnf["display_cont"].format(
            self.bucket_name, self.file_path.split("/")[-1])
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Listing object from a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(
            self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 2: Verified that object is listed from a bucket")
        self.log.info("Step 3: Displaying content of a text file")
        resp = system_utils.run_local_cmd(display_content)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp[1])
        self.log.info("Step 3: Displayed content of a text file")
        self.buckets_list.append(self.bucket_name)
        self.log.info(
            "ENDED: Display the contents of a text file using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7539")
    @CTFailOn(error_handler)
    def test_display_few_lines_2358(self):
        """Display the first few lines of a text file using Minion Client."""
        self.log.info(
            "STARTED: Display the first few lines of a text file using Minion Client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name)
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name)
        head_obj_cmd = self.minio_cnf["head_obj"].format(
            2, self.bucket_name, self.file_path.split("/")[-1])
        self.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object to a bucket %s", self.bucket_name)
        # Creating a text file to upload as a object
        if os.path.exists(self.file_path):
            system_utils.remove_file(self.file_path)
        with open(self.file_path, "w") as file_ptr:
            file_ptr.write(self.minio_cnf["upload_data"])
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Listing object from a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(
            self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 3: Verified that object is listed from a bucket")
        self.log.info("Step 4: Performing head object")
        resp = system_utils.run_local_cmd(head_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Displaying first few lines of a text file : %s",
            resp[1])
        self.log.info("Step 4: Performed head object")
        self.buckets_list.append(self.bucket_name)
        self.log.info(
            "ENDED: Display the first few lines of a text file using Minion Client")
