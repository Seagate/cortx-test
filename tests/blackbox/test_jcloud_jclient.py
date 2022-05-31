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

"""
Note: The pre-requisite of this testfile require two jar files.

'jclient.jar' and 'jcloudclient.jar' to be placed the specific location
These files has to be placed to the following directory of this repository
'cortx-test/scripts/jcloud'
"""

import os
import time
import logging
import pytest

from commons.params import TEST_DATA_FOLDER
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import system_utils
from commons.utils import assert_utils
from config.s3 import S3_CFG
from config.s3 import S3_BLKBOX_CFG
from libs.s3 import s3_test_lib
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_blackbox_test_lib import JCloudClient


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestJcloudAndJclient:
    """Blaclbox jcloud and jclient Testsuite."""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup suite level operation.")
        cls.jc_obj = JCloudClient()
        cls.log.info("setup jClientCloud on runner.")
        res_ls = system_utils.execute_cmd("ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = cls.jc_obj.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"]
            )
            cls.log.info(res)
            assert_utils.assert_true(
                res, "Error: jcloudclient.jar or jclient.jar file does not exists")
        resp = cls.jc_obj.update_jclient_jcloud_properties()
        assert_utils.assert_true(resp, resp)

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log.info("STARTED: Setup operations.")
        self.s3_test_obj = s3_test_lib.S3TestLib()
        self.random_id = str(time.time())
        self.access_key = ACCESS_KEY
        self.secret_key = SECRET_KEY
        self.file_path_lst = []
        self.root_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestJcloudAndJclient")
        if not system_utils.path_exists(self.root_path):
            system_utils.make_dirs(self.root_path)
            self.log.info("Created path: %s", self.root_path)
        self.bucket_name = f"jcloudjclientbucket-{time.perf_counter_ns()}"
        self.obj_name = f"objkey{time.perf_counter_ns()}"
        self.test_file = f"testfile{time.perf_counter_ns()}.txt"
        self.file_path = os.path.join(self.root_path, self.test_file)
        self.jcloud_bucket_list = []
        self.log.info("Test file path: %s", self.file_path)
        self.log.info("ENDED: Setup operations.")

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
        for bucket_name in self.jcloud_bucket_list:
            resp = self.s3_test_obj.delete_bucket(bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("The bucket and all objects deleted successfully")
        self.log.info("Deleting the file created locally for object")
        if os.path.exists(self.file_path):
            resp = system_utils.remove_file(self.file_path)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Teardown Operations")

    def create_cmd_format(self, bucket, operation, jtool=None):
        """
        Function forms a command to perform specified operation.

        using given bucket name and returns a single line command.
        :param str bucket: Name of the s3 bucket
        :param str operation: type of operation to be performed on s3
        :param str jtool: Name of the java jar tool
        :return: str command: cli command to be executed
        """

        return self.jc_obj.create_cmd_format(bucket, operation, jtool)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7094")
    @CTFailOn(error_handler)
    def test_create_bucket_2368(self):
        """create bucket using Jcloudclient."""
        self.log.info("STARTED: create bucket using Jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "mb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        self.log.info("command: %s", command)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("ENDED: create bucket using Jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7095")
    @CTFailOn(error_handler)
    def test_delete_bucket_2370(self):
        """Delete bucket using jcloudclient."""
        self.log.info("STARTED: delete bucket using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "mb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Deleting buckets %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "rb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Bucket deleted successfully", resp[1][:-1], resp[1])
        if not resp[0]:
            self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Bucket %s was deleted successfully", self.bucket_name)
        self.log.info("ENDED: delete bucket using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7096")
    @CTFailOn(error_handler)
    def test_put_object_2373(self):
        """Put object using jcloudclient."""
        self.log.info("STARTED: put object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "mb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Put object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 10)
        self.file_path_lst.append(self.file_path)
        put_cmd_str = f"put {self.file_path}"
        command = self.create_cmd_format(self.bucket_name, put_cmd_str,
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Put object to a bucket %s was successful", self.bucket_name)
        self.log.info("ENDED: get object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7097")
    @CTFailOn(error_handler)
    def test_get_object_2374(self):
        """Get object using jcloudclient."""
        self.log.info("STARTED: get object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "mb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 10)
        self.file_path_lst.append(os.path.join(self.file_path))
        put_cmd_str = f"put {self.file_path}"
        command = self.create_cmd_format(self.bucket_name, put_cmd_str,
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Put object to a bucket %s was successful", self.bucket_name)
        self.log.info("STEP: 3 Get object from bucket %s", self.bucket_name)
        file_path = self.file_path.split("/")[-1]
        self.file_path_lst.append(file_path)
        bucket_str = f"{self.bucket_name}/{file_path} {file_path}"
        command = self.create_cmd_format(bucket_str, "get",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object download successfully", resp[1][:-1], resp)
        self.log.info("STEP: 3 Object was downloaded successfully")
        self.log.info("ENDED: put object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7098")
    @CTFailOn(error_handler)
    def test_delete_object_2375(self):
        """Delete object using jcloudclient."""
        self.log.info("STARTED: delete object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "mb")
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path, 10)
        self.file_path_lst.append(self.file_path)
        put_cmd_str = f"put {self.file_path}"
        command = self.create_cmd_format(self.bucket_name, put_cmd_str,
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Put object to a bucket %s was successful", self.bucket_name)
        self.log.info("STEP: 3 Deleting object from bucket %s", self.bucket_name)
        file_name = self.file_path.split("/")[-1]
        bucket_str = f"{self.bucket_name}/{file_name} {file_name}"
        command = self.create_cmd_format(bucket_str, "del",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object deleted successfully", resp[1][:-1], resp)
        self.log.info("STEP: 3 Object was deleted successfully")
        self.log.info("ENDED: delete object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7099")
    @CTFailOn(error_handler)
    def test_del_multiple_objects_2376(self):
        """Delete multiple objects using jcloudclient."""
        self.log.info("STARTED: delete multiple objects using jcloudclient")
        self.log.info("STEP: 1 Creating bucket and uploading multiple objects")
        obj_lst = ["object2376-1.txt", "object2376-2.txt"]
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        for obj_name in obj_lst:
            file_p = os.path.join(self.root_path, obj_name)
            system_utils.create_file(file_p, 10)
            self.file_path_lst.append(file_p)
            self.s3_test_obj.put_object(self.bucket_name, obj_name, file_p)
        self.log.info("STEP: 1 Creating a bucket and uploading multiple objects was successful")
        self.log.info("STEP: 2 Deleting multiple objects from bucket %s", self.bucket_name)
        objects_str = " ".join(obj_lst)
        bucket_str = f"{self.bucket_name} {objects_str}"
        command = self.create_cmd_format(bucket_str, "multidel",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Objects deleted successfully", resp[1][:-1], resp)
        self.log.info("STEP: 2 Successfully deleted all objects")
        self.log.info("ENDED: delete multiple objects using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7100")
    @CTFailOn(error_handler)
    def test_head_object_2377(self):
        """Head object using jcloudclient."""
        self.log.info("STARTED: head object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket and uploading object in bucket %s", self.bucket_name)
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get head object")
        bucket_str = f"{self.bucket_name}/{self.obj_name}"
        command = self.create_cmd_format(bucket_str, "head",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        output_objname = resp[1].split("\\n")[1].split("-")[1].strip()
        assert_utils.assert_equal(output_objname, self.obj_name, resp)
        self.log.info("STEP: 2 Get head object was successful")
        self.log.info("ENDED: head object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7101")
    @CTFailOn(error_handler)
    def test_check_obj_exists_2379(self):
        """object exists using jcloudclient."""
        self.log.info("STARTED: object exists using jcloudclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Check object exists in the bucket %s", self.bucket_name)
        bucket_str = f"{self.bucket_name}/{self.obj_name}"
        command = self.create_cmd_format(bucket_str, "exists",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        success_msg = f"Object {self.obj_name} exists"
        assert_utils.assert_in(success_msg, resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Object exists in the bucket %s", self.bucket_name)
        self.log.info("ENDED: object exists using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7102")
    @CTFailOn(error_handler)
    def test_remove_empty_bucket_2380(self):
        """Remove bucket if empty."""
        self.log.info("STARTED: Remove bucket if empty")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Trying to remove bucket: %s if empty", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "rbifempty",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Bucket deleted successfully", resp[1][:-1], resp)
        if not resp[0]:
            self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Bucket was successfully removed")
        self.log.info("ENDED: Remove bucket if empty")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7103")
    @CTFailOn(error_handler)
    def test_create_bucket_2381(self):
        """create bucket using jclient."""
        self.log.info("STARTED: create bucket using jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "mb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("ENDED: create bucket using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7104")
    @CTFailOn(error_handler)
    def test_list_bucket_2382(self):
        """list bucket using jclient."""
        self.log.info("STARTED: list bucket using jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Listing all the bucket created")
        java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_cmd"]
        aws_keys_str = f"--access_key {self.access_key} --secret_key {self.secret_key}"
        command = f"{java_cmd} ls {aws_keys_str}"
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        bkt_lst = resp[1][9:].strip().split("\\n")
        self.log.info("Bucket List %s", bkt_lst)
        assert_utils.assert_in(self.bucket_name, bkt_lst, resp)
        self.log.info("STEP: 2 All buckets were listed")
        self.log.info("ENDED: list bucket using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7105")
    @CTFailOn(error_handler)
    def test_delete_bucket_2384(self):
        """delete bucket using jclient."""
        self.log.info("STARTED: delete bucket using jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Trying to delete a bucket: %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "rb",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Bucket deleted successfully", resp[1][:-1], resp[1])
        if not resp[0]:
            self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Bucket was successfully deleted")
        self.log.info("ENDED: delete bucket using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7106")
    @CTFailOn(error_handler)
    def test_list_object_2385(self):
        """list object using jclient."""
        self.log.info("STARTED: list object using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Listing all the objects from buckets %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "ls",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Object List %s", resp[1])
        assert_utils.assert_in(self.obj_name, resp[1], resp)
        self.log.info("STEP: 2 All objects were listed of bucket")
        self.log.info("ENDED: list object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7107")
    @CTFailOn(error_handler)
    def test_delete_object_2386(self):
        """delete object using jclient."""
        self.log.info("STARTED: delete object using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Deleting object from bucket %s", self.bucket_name)
        bucket_str = f"{self.bucket_name}/{self.obj_name}"
        command = self.create_cmd_format(bucket_str, "del",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object deleted successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Object was deleted successfully")
        self.log.info("ENDED: delete object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7108")
    @CTFailOn(error_handler)
    def test_head_object_2388(self):
        """head object using jclient."""
        self.log.info("STARTED: head object using jclient")
        self.log.info("STEP: 1 Creating bucket and upload object")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get head object")
        bucket_str = f"{self.bucket_name}/{self.obj_name}"
        command = self.create_cmd_format(bucket_str, "head",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        output_objname = resp[1].split("\\n")[1].split("-")[1].strip()
        assert_utils.assert_equal(output_objname, self.obj_name, resp)
        self.log.info("STEP: 2 Get head object was successful")
        self.log.info("ENDED: head object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7109")
    @CTFailOn(error_handler)
    def test_put_obj_2389(self):
        """put object using jclient."""
        self.log.info("STARTED: put object using jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Uploading an object to a bucket %s", self.bucket_name)
        file_path = f"{self.root_path}/{self.obj_name}"
        system_utils.create_file(file_path, 10)
        self.file_path_lst.append(file_path)
        put_cmd = f"put {file_path}"
        command = self.create_cmd_format(self.bucket_name, put_cmd,
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 2Put object to a bucket %s was successful", self.bucket_name)
        self.log.info("ENDED: put object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7110")
    @CTFailOn(error_handler)
    def test_get_object_2390(self):
        """get object using jclient."""
        self.log.info("STARTED: get object using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.file_path_lst.append(os.path.join(os.getcwd(), self.obj_name))
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get object from bucket %s", self.bucket_name)
        bucket_str = f"{self.bucket_name}/{self.obj_name} {self.obj_name}"
        command = self.create_cmd_format(bucket_str, "get",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object download successfully", resp[1][:-1], resp)
        self.log.info("STEP: 2 Object was downloaded successfully")
        self.log.info("ENDED: put object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7111")
    @CTFailOn(error_handler)
    def test_bucket_exists_2391(self):
        """Bucket exists using Jclient."""
        self.log.info("STARTED: Bucket exists using Jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Check bucket %s exists on s3 server", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "exists",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        success_msg = f"Bucket {self.bucket_name} exists"
        assert_utils.assert_in(success_msg, resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Bucket %s exists on s3 server", self.bucket_name)
        self.log.info("ENDED: Bucket exists using Jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7112")
    @CTFailOn(error_handler)
    def test_check_obj_exists_2392(self):
        """object exists using jclient."""
        self.log.info("STARTED: object exists using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading objects")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Check object exists in the bucket %s", self.bucket_name)
        bucket_str = f"{self.bucket_name}/{self.obj_name}"
        command = self.create_cmd_format(bucket_str, "exists",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object exists", resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Object exists in the bucket %s", self.bucket_name)
        self.log.info("ENDED: object exists using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7529")
    @CTFailOn(error_handler)
    def test_list_buckets_2369(self):
        """list buckets using jcloudclient."""
        self.log.info("STARTED: list buckets using jcloudclient")
        common_cfg = S3_BLKBOX_CFG["jcloud_cfg"]
        self.log.info("STEP 1: Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP 1: Bucket was created %s", self.bucket_name)
        self.log.info("STEP 2: Listing all the buckets")
        keys_str = f"--access-key {self.access_key} --secret-key {self.secret_key}"
        command = "{} {} {}".format(common_cfg["jcloud_cmd"], "ls", keys_str)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        bucket_lst = [bkt.strip() for bkt in resp[1].split("\\n")]
        assert_utils.assert_in(self.bucket_name, bucket_lst, resp)
        self.log.info("STEP 2: All the s3 bucket listed")
        self.log.info("ENDED: list buckets using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7531")
    @CTFailOn(error_handler)
    def test_max_bucket_2371(self):
        """max no of buckets supported using jcloudclient."""
        self.log.info("STARTED: max no of buckets supported using jcloudclient")
        common_cfg = S3_BLKBOX_CFG["jcloud_cfg"]
        self.log.info("Step 1 : Delete all existing buckets for the user")
        resp = self.s3_test_obj.delete_all_buckets()
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1 : Deleted all existing buckets for the user")
        self.log.info("STEP 2: Creating n buckets")
        for bkt in range(1000):
            bkt_name_str = f"{self.bucket_name}-{bkt}"
            self.log.info("Creating bucket with name : %s", bkt_name_str)
            command = self.create_cmd_format(bkt_name_str, "mb", jtool=common_cfg["jcloud_tool"])
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            self.jcloud_bucket_list.append(bkt_name_str)
            assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp)
            self.log.info(
                "Bucket %s was created successfully", bkt_name_str)
        self.log.info("STEP 2: n buckets were created successfully")
        bkt_lst = self.jcloud_bucket_list
        self.log.info("STEP 3: Verifying all the buckets")
        resp = self.s3_test_obj.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        s3_bkt_lst = [bkt for bkt in resp[1] if self.bucket_name in bkt]
        assert_utils.assert_equal(bkt_lst.sort(), s3_bkt_lst.sort(), resp)
        self.log.info("STEP 3: All the s3 buckets created were verified")
        self.log.info("ENDED: max no of buckets supported using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7532")
    @CTFailOn(error_handler)
    def test_list_objects_2372(self):
        """list objects using jcloudclient."""
        self.log.info("STARTED: list objects using jcloudclient")
        self.log.info("STEP 1: Creating bucket and uploading object")
        file_path = f"{self.root_path}/{self.obj_name}"
        self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name, file_path, 10)
        self.log.info("STEP 1: Creating a bucket and uploading object was successful")
        self.jcloud_bucket_list.append(self.bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("STEP 2: Listing all the objects from buckets %s", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "ls",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.obj_name, resp[1], resp)
        self.log.info("STEP 2: All objects were listed of bucket")
        self.log.info("ENDED: list objects using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7533")
    @CTFailOn(error_handler)
    def test_check_bucket_exist_2378(self):
        """Bucket exists using jcloudclient."""
        self.log.info("STARTED: Bucket exists using jcloudclient")
        self.log.info("STEP 1: Creating bucket %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        self.log.info("STEP 1: Bucket was created %s", self.bucket_name)
        self.log.info("STEP 2: Check bucket %s exists on s3 server", self.bucket_name)
        command = self.create_cmd_format(self.bucket_name, "exists",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        success_msg = f"Bucket {self.bucket_name} exists"
        assert_utils.assert_in(success_msg, resp[1][:-1], resp[1])
        self.log.info("STEP 2: Bucket %s exists on s3 server", self.bucket_name)
        self.log.info("ENDED: Bucket exists using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7534")
    @CTFailOn(error_handler)
    def test_max_bucket_support_2383(self):
        """max no of buckets supported using Jclient."""
        self.log.info("STARTED: max no of buckets supported using Jclient")
        common_cfg = S3_BLKBOX_CFG["jcloud_cfg"]
        self.log.info("Step 1 : Delete all existing buckets for the user")
        resp = self.s3_test_obj.delete_all_buckets()
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1 : Deleted all existing buckets for the user")
        self.log.info("STEP 2: Creating n buckets")
        for bkt in range(1000):
            bkt_name_str = f"{self.bucket_name}-{bkt}"
            self.log.info("Creating bucket with name : %s", bkt_name_str)
            command = self.create_cmd_format(bkt_name_str, "mb", jtool=common_cfg["jclient_tool"])
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            self.jcloud_bucket_list.append(bkt_name_str)
            assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
            self.log.info("Bucket %s was created successfully", bkt_name_str)
        self.log.info("STEP 2: n buckets were created successfully")
        bkt_lst = self.jcloud_bucket_list
        self.log.info("STEP 3: Verifying all the buckets")
        resp = self.s3_test_obj.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        s3_bkt_lst = [bkt for bkt in resp[1] if self.bucket_name in bkt]
        assert_utils.assert_equal(bkt_lst.sort(), s3_bkt_lst.sort(), resp)
        self.log.info("STEP 3: All the s3 buckets created were verified")
        self.log.info("ENDED: max no of buckets supported using Jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7535")
    @CTFailOn(error_handler)
    def test_del_multiple_object_2387(self):
        """delete multiple objects using jclient."""
        self.log.info("STARTED: delete multiple objects using jclient")
        self.log.info("STEP 1: Creating bucket and uploading multiple objects")
        obj_lst = ["object2387-1.txt", "object2387-2.txt"]
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.jcloud_bucket_list.append(self.bucket_name)
        for obj_name in obj_lst:
            file_p = os.path.join(self.root_path, obj_name)
            self.file_path_lst.append(file_p)
            system_utils.create_file(file_p, 10)
            self.s3_test_obj.put_object(self.bucket_name, obj_name, file_p)
        self.log.info("STEP 1: Creating a bucket and uploading multiple objects was successful")
        self.log.info("STEP 2: Deleting multiple objects from bucket %s", self.bucket_name)
        objects_str = " ".join(obj_lst)
        bucket_str = f"{self.bucket_name} {objects_str}"
        command = self.create_cmd_format(bucket_str, "multidel",
                                         jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Objects deleted successfully", resp[1][:-1], resp[1])
        self.log.info("STEP 2: Successfully deleted multiple objects")
        self.log.info("ENDED: delete multiple objects using jclient")
