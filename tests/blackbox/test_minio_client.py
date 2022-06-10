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

"""Minio Client test module."""

import logging
import os
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import config_utils
from commons.utils import system_utils
from config.s3 import S3_BLKBOX_CFG
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3 import s3_test_lib
from libs.s3.s3_blackbox_test_lib import MinIOClient


# pylint: disable=too-many-instance-attributes
class TestMinioClient:
    """Black box minio client Testsuite."""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup suite level operation.")
        cls.minio_obj = MinIOClient()
        resp = MinIOClient.configre_minio_cloud(
            minio_repo=S3_CFG["minio_repo"],
            endpoint_url=S3_CFG["s3_url"],
            s3_cert_path=S3_CFG["s3_cert_path"],
            minio_cert_path_list=S3_CFG["minio_crt_path_list"],
            access=ACCESS_KEY,
            secret=SECRET_KEY)
        assert_utils.assert_true(resp, f"failed to setup minio: {resp}")
        resp = system_utils.path_exists(S3_CFG["minio_path"])
        assert_utils.assert_true(
            resp, "minio config not exists: {}".format(S3_CFG["minio_path"]))
        minio_dict = config_utils.read_content_json(S3_CFG["minio_path"], mode='rb')
        cls.log.info(minio_dict)
        if (ACCESS_KEY != minio_dict["aliases"]["s3"]["accessKey"]
                or SECRET_KEY != minio_dict["aliases"]["s3"]["secretKey"]):
            resp = MinIOClient.configure_minio(ACCESS_KEY, SECRET_KEY)
            assert_utils.assert_true(resp, f'Failed to update keys in {S3_CFG["minio_path"]}')
        cls.log.info("ENDED: Setup suite level operation.")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite steps if any.
        Initializing common variable which will be used in test
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3t_obj = s3_test_lib.S3TestLib()
        self.root_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestMinioClient")
        if not system_utils.path_exists(self.root_path):
            system_utils.make_dirs(self.root_path)
            self.log.info("Created path: %s", self.root_path)

        self.bucket_name = f"min-bkt-{time.perf_counter_ns()}"
        self.test_file = f"minio_client{time.perf_counter_ns()}.txt"
        self.file_path = os.path.join(self.root_path, self.test_file)
        self.minio_cnf = S3_BLKBOX_CFG["minio_cfg"]
        self.minio_bucket_list = []
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
        for bucket_name in self.minio_bucket_list:
            resp = self.s3t_obj.delete_bucket(bucket_name, force=True)
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
        self.minio_obj.create_bucket(bucket_name)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7536")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2345(self):
        """Create single bucket using Minio Client."""
        self.log.info("STARTED: Create single bucket using Minio Client")
        self.create_bucket(self.bucket_name)
        self.log.info("Step 2: Verifying that %s bucket is created", self.bucket_name)
        resp = self.s3t_obj.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.bucket_name, resp[1], resp[1])
        self.log.info("Step 2: Verified that %s bucket was created", self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
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
        cmd = self.minio_cnf["cr_two_bkt_cmd"].format(
                bucket_name_1, bucket_name_2) + self.minio_obj.validate_cert
        resp = system_utils.run_local_cmd(cmd=cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created two buckets simultaneously")
        self.log.info("Step 2: Verifying buckets are created")
        resp = self.s3t_obj.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(bucket_name_1, resp[1])
        assert_utils.assert_in(bucket_name_2, resp[1])
        status, resp = self.s3t_obj.delete_multiple_buckets(
            bucket_list=[bucket_name_1, bucket_name_2])
        if not status:
            self.log.info("Buckets are not deleted because: %s", resp)
            self.minio_bucket_list = [bucket_name_1, bucket_name_2]
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
        self.minio_bucket_list.append(self.bucket_name)
        cmd = self.minio_cnf["lst_bkt_cmd"] + self.minio_obj.validate_cert
        self.log.info("Step 2: Listing buckets")
        resp = system_utils.run_local_cmd(cmd=cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.bucket_name, resp[1], resp)
        self.log.info("Step 2: Buckets are listed")
        self.log.info("Ended: List buckets using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7544")
    @CTFailOn(error_handler)
    def test_max_bucket_2348(self):
        """Max no of buckets supported using Minion Client."""
        self.log.info("STARTED: Max no of buckets supported using Minion Client")
        self.log.info("Step 1 : Delete all existing buckets for the user")
        resp = self.s3t_obj.delete_all_buckets()
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1 : Deleted all existing buckets for the user")
        self.log.info("Step 2: Creating %s buckets using minio", self.minio_cnf["no_of_buckets"])
        for cnt in range(self.minio_cnf["no_of_buckets"]):
            bkt_name = f"{self.bucket_name}{str(cnt)}"
            cmd = self.minio_cnf["create_bkt_cmd"].format(bkt_name) + self.minio_obj.validate_cert
            resp = system_utils.run_local_cmd(cmd=cmd)
            assert_utils.assert_true(resp[0], resp[1])
            self.minio_bucket_list.append(bkt_name)
        self.log.info("Step 2: Created %s buckets using minio", self.minio_cnf["no_of_buckets"])
        self.log.info("Step 3: Verifying buckets are created")
        bucket_list = self.s3t_obj.bucket_list()[1]
        for each_bucket in self.minio_bucket_list:
            assert_utils.assert_in(each_bucket, bucket_list)
        self.log.info("Cleanup: Deleting created buckets")
        resp, output = self.s3t_obj.delete_multiple_buckets(bucket_list=self.minio_bucket_list)
        if resp:
            self.minio_bucket_list = []
        else:
            self.log.info("Buckets are not deleted: %s", output)
        self.log.info("Step 3: Verified that buckets are created")
        self.log.info("ENDED: Max no of buckets supported using Minion Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7548")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2349(self):
        """Delete empty bucket using Minion client."""
        self.log.info("STARTED: Delete empty bucket using Minion client")
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Deleting bucket with name %s", self.bucket_name)
        cmd = self.minio_cnf["dlt_bkt_cmd"].format(self.bucket_name) + self.minio_obj.validate_cert
        resp = system_utils.run_local_cmd(cmd=cmd)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Bucket is deleted with name %s", self.bucket_name)
        self.log.info("Step 3: Verifying that %s bucket is deleted", self.bucket_name)
        resp = self.s3t_obj.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_not_in(self.bucket_name, resp[1])
        self.minio_bucket_list = []
        self.log.info("Step 3: Verified that %s bucket is deleted", self.bucket_name)
        self.log.info("ENDED: Delete empty bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7547")
    @CTFailOn(error_handler)
    def test_delete_bucket_has_obj_2350(self):
        """Delete bucket which has objects using Minion Client."""
        self.log.info("STARTED: delete bucket which has objects using Minion Client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) + \
            self.minio_obj.validate_cert
        dlt_bkt_cmd = self.minio_cnf["dlt_bkt_cmd"].format(self.bucket_name) + \
            self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 1: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 2: Listing object from a bucket %s", self.bucket_name)
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 2: Listed object from a bucket %s", self.bucket_name)
        self.log.info("Step 3: Deleting bucket which has a object")
        resp = system_utils.run_local_cmd(dlt_bkt_cmd)
        assert_utils.assert_false(resp[0], resp)
        self.minio_bucket_list = []
        self.log.info("Step 1: Bucket is deleted with name %s", self.bucket_name)
        self.log.info("ENDED: delete bucket which has objects using Minion Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7546")
    @CTFailOn(error_handler)
    def test_create_bucket_existing_name_2351(self):
        """Create bucket using existing bucket name using Minion client."""
        self.log.info(
            "STARTED: Create bucket using existing bucket name using Minion client")
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Creating a bucket with existing name")
        cmd = self.minio_cnf["create_bkt_cmd"].format(self.bucket_name) + \
            self.minio_obj.validate_cert
        resp = system_utils.run_local_cmd(cmd=cmd)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in("Unable to make bucket", resp[1], resp[1])
        self.log.info(
            "Step 1: Creating a bucket with existing name is failed with error %s",
            "Unable to make bucket")
        self.log.info("ENDED: Create bucket using existing bucket name using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7543")
    @CTFailOn(error_handler)
    def test_list_obj_inside_bucket_2352(self):
        """To list objects inside bucket using Minion client."""
        self.log.info("STARTED: To list objects inside bucket using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) + \
            self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Listing object from a bucket %s", self.bucket_name)
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 3: Listed object from a bucket %s", self.bucket_name)
        self.log.info("ENDED: To list objects inside bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7541")
    @CTFailOn(error_handler)
    def test_del_obj_from_bucket_2353(self):
        """Delete an object from bucket using Minion client."""
        self.log.info(
            "STARTED: Delete an object from bucket using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) + \
            self.minio_obj.validate_cert
        dlt_obj_cmd = self.minio_cnf["dlt_obj"].format(
            self.bucket_name, self.file_path.split("/")[-1]) + self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Object is uploaded to a bucket %s", self.bucket_name)
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
        self.log.info("ENDED: Delete an object from bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7542")
    @CTFailOn(error_handler)
    def test_copy_obj_from_bucket_2354(self):
        """Copy object from bucket using Minion client."""
        self.log.info("STARTED: copy object from bucket using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) \
            + self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Verifying that object is copied from a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 3: Verified that object is uploaded to a bucket")
        self.log.info("ENDED: copy object from bucket using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7538")
    @CTFailOn(error_handler)
    def test_upload_large_obj_2355(self):
        """Upload object of large size of(5gb) using Minion Client."""
        self.log.info("STARTED: upload object of large size of(5gb) using Minion Client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) \
            + self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Creating a file of size 5GB")
        system_utils.create_file(self.file_path, 5024)
        self.log.info("Step 2: Created a file of size 5GB")
        self.log.info("Step 3: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 4: Verifying that object is uploaded to a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 4: Verified that object is uploaded to a bucket")
        self.log.info("ENDED: upload object of large size of(5gb) using Minion Client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7540")
    @CTFailOn(error_handler)
    def test_display_file_content_2357(self):
        """Display the contents of a text file using Minion client."""
        self.log.info(
            "STARTED: Display the contents of a text file using Minion client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        display_content = self.minio_cnf["display_cont"].format(
            self.bucket_name, self.file_path.split("/")[-1]) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) \
            + self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
        self.log.info("Step 2: Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 5)
        resp = system_utils.run_local_cmd(upload_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Object is uploaded to a bucket %s", self.bucket_name)
        self.log.info("Step 3: Listing object from a bucket")
        resp = system_utils.run_local_cmd(list_obj_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(os.path.basename(self.file_path), resp[1].split(" ")[-1], resp[1])
        self.log.info("Step 2: Verified that object is listed from a bucket")
        self.log.info("Step 3: Displaying content of a text file")
        resp = system_utils.run_local_cmd(display_content)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp[1])
        self.log.info("Step 3: Displayed content of a text file")
        self.log.info("ENDED: Display the contents of a text file using Minion client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7539")
    @CTFailOn(error_handler)
    def test_display_few_lines_2358(self):
        """Display the first few lines of a text file using Minion Client."""
        self.log.info(
            "STARTED: Display the first few lines of a text file using Minion Client")
        upload_obj_cmd = self.minio_cnf["upload_obj_cmd"].format(
            self.file_path, self.bucket_name) + self.minio_obj.validate_cert
        list_obj_cmd = self.minio_cnf["list_obj_cmd"].format(self.bucket_name) \
            + self.minio_obj.validate_cert
        head_obj_cmd = self.minio_cnf["head_obj"].format(
            self.bucket_name, self.file_path.split("/")[-1]) + self.minio_obj.validate_cert
        self.create_bucket(self.bucket_name)
        self.minio_bucket_list.append(self.bucket_name)
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
        self.log.info("Head object output : %s", resp[1])
        assert_utils.assert_in(self.minio_cnf["upload_data"][10], resp[1], resp[1])
        self.log.info("Step 4: Performed head object")
        self.log.info("ENDED: Display the first few lines of a text file using Minion Client")
