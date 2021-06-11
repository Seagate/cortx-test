#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates.
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
from commons.exceptions import CTException
from commons.errorcodes import error_handler, S3_CLIENT_ERROR
from commons.configmanager import config_utils
from commons.configmanager import get_config_wrapper
from commons.utils import system_utils
from commons.utils import assert_utils
from config import S3_CFG
from libs.s3 import s3_test_lib
from libs.s3 import ACCESS_KEY, SECRET_KEY

S3_TEST_OBJ = s3_test_lib.S3TestLib()
BLACKBOX_CONF = get_config_wrapper(fpath="config/blackbox/test_blackbox.yaml")


class TestJcloudAndJclient:
    """Blaclbox jcloud and jclient Testsuite."""

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations.")
        self.random_id = str(time.time())
        self.access_key = ACCESS_KEY
        self.secret_key = SECRET_KEY
        self.file_path_lst = []
        self.root_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestJcloudAndJclient")
        if not system_utils.path_exists(self.root_path):
            system_utils.make_dirs(self.root_path)
            self.log.info("Created path: %s", self.root_path)
        self.log.info("setup jClientCloud on runner.")
        res_ls = system_utils.execute_cmd(
            "ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = system_utils.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"]
            )
            self.log.info(res)
            if not res:
                raise CTException(
                    S3_CLIENT_ERROR,
                    "Error: jcloudclient.jar or jclient.jar file does not exists")
        self.s3_url = S3_CFG['s3_url'].replace("https://", "").replace("http://", "")
        self.s3_iam = S3_CFG['iam_url'].strip("https://").strip("http://").strip(":9443")
        resp = self.update_jclient_jcloud_properties()
        assert_utils.assert_true(resp, resp)

        self.bucket_name = "jcloudjclientbucket-{}".format(time.perf_counter_ns())
        self.obj_name = "objkey{}".format(time.perf_counter_ns())
        self.test_file = "testfile{}.txt".format(time.perf_counter_ns())
        self.file_path = os.path.join(self.root_path, self.test_file)
        self.bucket_list = list()
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
        if self.bucket_name in self.bucket_list:
            resp = S3_TEST_OBJ.delete_bucket(self.bucket_name, force=True)
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
        if jtool == BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"]:
            java_cmd = BLACKBOX_CONF["jcloud_cfg"]["jcloud_cmd"]
            aws_keys_str = "--access-key {} --secret-key {}".format(
                self.access_key, self.secret_key)
        else:
            java_cmd = BLACKBOX_CONF["jcloud_cfg"]["jclient_cmd"]
            aws_keys_str = "--access_key {} --secret_key {}".format(
                self.access_key, self.secret_key)
        bucket_url = "s3://{}".format(bucket)
        cmd = "{} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                      aws_keys_str, "-p")
        self.log.info("jcloud command: %s", cmd)

        return cmd

    def update_jclient_jcloud_properties(self):
        """
        Update jclient, jcloud properties with correct s3, iam endpoint.

        :return: True
        """
        resp = False
        for prop_path in [BLACKBOX_CONF["jcloud_cfg"]["jclient_properties_path"],
                          BLACKBOX_CONF["jcloud_cfg"]["jcloud_properties_path"]]:
            self.log.info("Updating: %s", prop_path)
            prop_dict = config_utils.read_properties_file(prop_path)
            if prop_dict:
                if prop_dict['iam_endpoint'] != self.s3_iam:
                    prop_dict['iam_endpoint'] = self.s3_iam
                if prop_dict['s3_endpoint'] != self.s3_url:
                    prop_dict['s3_endpoint'] = self.s3_url
                resp = config_utils.write_properties_file(prop_path, prop_dict)

        return resp

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7094")
    @CTFailOn(error_handler)
    def test_create_bucket_2368(self):
        """create bucket using Jcloudclient."""
        self.log.info("STARTED: create bucket using Jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "mb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        self.log.info("command: %s", command)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.bucket_list.append(self.bucket_name)
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
        command = self.create_cmd_format(
            self.bucket_name,
            "mb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Deleting buckets %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "rb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket deleted successfully", resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Bucket %s was deleted successfully", self.bucket_name)
        self.log.info("ENDED: delete bucket using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7096")
    @CTFailOn(error_handler)
    def test_put_object_2373(self):
        """Put object using jcloudclient."""
        self.log.info("STARTED: put object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "mb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Put object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path,
                                 10)
        put_cmd_str = "{} {}".format("put",
                                     self.file_path)
        command = self.create_cmd_format(
            self.bucket_name,
            put_cmd_str,
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Object put successfully", resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Put object to a bucket %s was successful", self.bucket_name)
        self.file_path_lst.append(self.file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: get object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7097")
    @CTFailOn(error_handler)
    def test_get_object_2374(self):
        """Get object using jcloudclient."""
        self.log.info("STARTED: get object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "mb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket created successfully", resp[1][:-1], resp[1])
        self.bucket_list.append(self.bucket_name)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP: 2 Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path,
                                 10)
        put_cmd_str = "{} {}".format("put",
                                     self.file_path)
        command = self.create_cmd_format(
            self.bucket_name,
            put_cmd_str,
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Put object to a bucket %s was successful", self.bucket_name)
        self.log.info("STEP: 3 Get object from bucket %s", self.bucket_name)
        file_path = self.file_path.split("/")[-1]
        self.file_path_lst.append(file_path)
        bucket_str = "{0}/{1} {1}".format(self.bucket_name, file_path)
        command = self.create_cmd_format(
            bucket_str,
            "get",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object download successfully", resp[1][:-1], resp)
        self.log.info("STEP: 3 Object was downloaded successfully")
        self.file_path_lst.append(os.path.join(
            self.file_path))
        self.log.info("ENDED: put object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7098")
    @CTFailOn(error_handler)
    def test_delete_object_2375(self):
        """Delete object using jcloudclient."""
        self.log.info("STARTED: delete object using jcloudclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name, "mb")
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket created successfully", resp[1][:-1], resp[1])
        self.bucket_list.append(self.bucket_name)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP: 2 Uploading an object to a bucket %s", self.bucket_name)
        system_utils.create_file(self.file_path,
                                 10)
        put_cmd_str = "{} {}".format("put",
                                     self.file_path)
        command = self.create_cmd_format(
            self.bucket_name,
            put_cmd_str,
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Put object to a bucket %s was successful", self.bucket_name)
        self.log.info(
            "STEP: 3 Deleting object from bucket %s", self.bucket_name)
        file_name = self.file_path.split("/")[-1]
        bucket_str = "{0}/{1} {1}".format(self.bucket_name, file_name)
        command = self.create_cmd_format(
            bucket_str,
            "del",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object deleted successfully", resp[1][:-1], resp)
        self.log.info("STEP: 3 Object was deleted successfully")
        self.file_path_lst.append(self.file_path)
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
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for obj_name in obj_lst:
            file_p = os.path.join(self.root_path,
                                  obj_name)
            self.file_path_lst.append(file_p)
            system_utils.create_file(file_p,
                                     10)
            S3_TEST_OBJ.put_object(self.bucket_name, obj_name, file_p)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading multiple objects was successful")
        self.log.info(
            "STEP: 2 Deleting multiple objects from bucket %s", self.bucket_name)
        objects_str = " ".join(obj_lst)
        bucket_str = "{} {}".format(self.bucket_name, objects_str)
        command = self.create_cmd_format(
            bucket_str,
            "multidel",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Objects deleted successfully", resp[1][:-1], resp)
        self.bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Successfully deleted all objects")
        self.log.info("ENDED: delete multiple objects using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7100")
    @CTFailOn(error_handler)
    def test_head_object_2377(self):
        """Head object using jcloudclient."""
        self.log.info("STARTED: head object using jcloudclient")
        self.log.info(
            "STEP: 1 Creating bucket and uploading object in bucket %s",
            self.bucket_name)
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get head object")
        bucket_str = "{}/{}".format(self.bucket_name, self.obj_name)
        command = self.create_cmd_format(
            bucket_str,
            "head",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        output_objname = resp[1].split("\\n")[1].split("-")[1].strip()
        assert_utils.assert_equal(output_objname, self.obj_name, resp)
        self.log.info("STEP: 2 Get head object was successful")
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: head object using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7101")
    @CTFailOn(error_handler)
    def test_check_obj_exists_2379(self):
        """object exists using jcloudclient."""
        self.log.info("STARTED: object exists using jcloudclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Check object exists in the bucket %s", self.bucket_name)
        bucket_str = "{}/{}".format(self.bucket_name, self.obj_name)
        command = self.create_cmd_format(
            bucket_str,
            "exists",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        success_msg = "Object {} exists".format(self.obj_name)
        assert_utils.assert_in(success_msg, resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Object exists in the bucket %s", self.bucket_name)
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: object exists using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7102")
    @CTFailOn(error_handler)
    def test_remove_empty_bucket_2380(self):
        """Remove bucket if empty."""
        self.log.info("STARTED: Remove bucket if empty")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP: 2 Trying to remove bucket: %s if empty", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "rbifempty",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Bucket deleted successfully", resp[1][:-1], resp)
        if not resp[0]:
            self.bucket_list.append(self.bucket_name)
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
        command = self.create_cmd_format(
            self.bucket_name,
            "mb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: create bucket using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7104")
    @CTFailOn(error_handler)
    def test_list_bucket_2382(self):
        """list bucket using jclient."""
        self.log.info("STARTED: list bucket using jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Listing all the bucket created")
        java_cmd = BLACKBOX_CONF["jcloud_cfg"]["jclient_cmd"]
        aws_keys_str = "--access_key {} --secret_key {}".format(
            self.access_key, self.secret_key)
        command = "{} {} {}".format(
            java_cmd, "ls", aws_keys_str)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        bkt_lst = resp[1][9:].strip().split("\\n")
        self.log.info("Bucket List %s", bkt_lst)
        assert_utils.assert_in(self.bucket_name, bkt_lst, resp)
        self.bucket_list.append(self.bucket_name)
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
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP: 2 Trying to delete a bucket: %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "rb",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Bucket deleted successfully", resp[1][:-1], resp[1])
        if not resp[0]:
            self.bucket_list.append(self.bucket_name)
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
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Listing all the objects from buckets %s", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "ls",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Object List %s", resp[1])
        assert_utils.assert_in(self.obj_name, resp[1], resp)
        self.log.info("STEP: 2 All objects were listed of bucket")
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: list object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7107")
    @CTFailOn(error_handler)
    def test_delete_object_2386(self):
        """delete object using jclient."""
        self.log.info("STARTED: delete object using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Deleting object from bucket %s", self.bucket_name)
        bucket_str = "{}/{}".format(self.bucket_name, self.obj_name)
        command = self.create_cmd_format(
            bucket_str,
            "del",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Object deleted successfully", resp[1][:-1], resp[1])
        self.log.info("STEP: 2 Object was deleted successfully")
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: delete object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7108")
    @CTFailOn(error_handler)
    def test_head_object_2388(self):
        """head object using jclient."""
        self.log.info("STARTED: head object using jclient")
        self.log.info("STEP: 1 Creating bucket and upload object")
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get head object")
        bucket_str = "{}/{}".format(self.bucket_name, self.obj_name)
        command = self.create_cmd_format(
            bucket_str,
            "head",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        output_objname = resp[1].split("\\n")[1].split("-")[1].strip()
        assert_utils.assert_equal(output_objname, self.obj_name, resp)
        self.log.info("STEP: 2 Get head object was successful")
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: head object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7109")
    @CTFailOn(error_handler)
    def test_put_obj_2389(self):
        """put object using jclient."""
        self.log.info("STARTED: put object using jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP: 2 Uploading an object to a bucket %s", self.bucket_name)
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        system_utils.create_file(file_path,
                                 10)
        put_cmd = "{} {}".format("put", file_path)
        command = self.create_cmd_format(
            self.bucket_name, put_cmd, jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Object put successfully", resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2Put object to a bucket %s was successful", self.bucket_name)
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: put object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7110")
    @CTFailOn(error_handler)
    def test_get_object_2390(self):
        """get object using jclient."""
        self.log.info("STARTED: get object using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading object")
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get object from bucket %s", self.bucket_name)
        bucket_str = "{0}/{1} {1}".format(self.bucket_name, self.obj_name)
        command = self.create_cmd_format(
            bucket_str,
            "get",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object download successfully", resp[1][:-1], resp)
        self.log.info("STEP: 2 Object was downloaded successfully")
        self.file_path_lst.append(file_path)
        self.file_path_lst.append(os.path.join(os.getcwd(), self.obj_name))
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: put object using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7111")
    @CTFailOn(error_handler)
    def test_bucket_exists_2391(self):
        """Bucket exists using Jclient."""
        self.log.info("STARTED: Bucket exists using Jclient")
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP: 2 Check bucket %s exists on s3 server", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "exists",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        success_msg = "Bucket {} exists".format(self.bucket_name)
        assert_utils.assert_in(success_msg, resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Bucket %s exists on s3 server", self.bucket_name)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Bucket exists using Jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7112")
    @CTFailOn(error_handler)
    def test_check_obj_exists_2392(self):
        """object exists using jclient."""
        self.log.info("STARTED: object exists using jclient")
        self.log.info("STEP: 1 Creating bucket and uploading objects")
        file_path = "{}/{}".format(self.root_path, self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Check object exists in the bucket %s", self.bucket_name)
        bucket_str = "{}/{}".format(self.bucket_name, self.obj_name)
        command = self.create_cmd_format(
            bucket_str,
            "exists",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object exists", resp[1][:-1], resp[1])
        self.log.info(
            "STEP: 2 Object exists in the bucket %s", self.bucket_name)
        self.file_path_lst.append(file_path)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: object exists using jclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7529")
    @CTFailOn(error_handler)
    def test_list_buckets_2369(self):
        """list buckets using jcloudclient."""
        self.log.info("STARTED: list buckets using jcloudclient")
        common_cfg = BLACKBOX_CONF["jcloud_cfg"]
        self.log.info("STEP 1: Creating bucket %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 1: Bucket was created %s", self.bucket_name)
        self.log.info("STEP 2: Listing all the buckets")
        keys_str = "--access-key {} --secret-key {}".format(
            self.access_key, self.secret_key)
        command = "{} {} {}".format(common_cfg["jcloud_cmd"],
                                    "ls", keys_str)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        bucket_lst = [bkt.strip() for bkt in resp[1].split("\\n")]
        assert_utils.assert_in(self.bucket_name, bucket_lst, resp)
        self.bucket_list.append(self.bucket_name)
        self.log.info("STEP 2: All the s3 bucket listed")
        self.log.info("ENDED: list buckets using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7531")
    @CTFailOn(error_handler)
    def test_max_bucket_2371(self):
        """max no of buckets supported using jcloudclient."""
        self.log.info(
            "STARTED: max no of buckets supported using jcloudclient")
        common_cfg = BLACKBOX_CONF["jcloud_cfg"]
        bkt_lst = []
        self.log.info("STEP 1: Creating n buckets")
        for bkt in range(1000):
            bkt_name_str = "{}-{}".format(self.bucket_name, bkt)
            self.log.info(
                "Creating bucket with name : %s", bkt_name_str)
            command = self.create_cmd_format(
                bkt_name_str,
                "mb",
                jtool=common_cfg["jcloud_tool"])
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            bkt_lst.append(bkt_name_str)
            assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp)
            self.log.info(
                "Bucket %s was created successfully", bkt_name_str)
        self.log.info("STEP 1: n buckets were created successfully")
        self.bucket_list = bkt_lst
        self.log.info("STEP 2: Verifying all the buckets")
        resp = S3_TEST_OBJ.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        s3_bkt_lst = [bkt for bkt in resp[1] if self.bucket_name in bkt]
        assert_utils.assert_equal(bkt_lst.sort(), s3_bkt_lst.sort(), resp)
        self.log.info("STEP 2: All the s3 buckets created were verified")
        self.log.info("ENDED: max no of buckets supported using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7532")
    @CTFailOn(error_handler)
    def test_list_objects_2372(self):
        """list objects using jcloudclient."""
        self.log.info("STARTED: list objects using jcloudclient")
        self.log.info("STEP 1: Creating bucket and uploading object")
        file_path = "{}/{}".format(
            self.root_path,
            self.obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            file_path,
            10)
        self.log.info(
            "STEP 1: Creating a bucket and uploading object was successful")
        self.bucket_list.append(self.bucket_name)
        self.log.info(
            "STEP 2: Listing all the objects from buckets %s",
            self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "ls",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.obj_name, resp[1], resp)
        self.log.info("STEP 2: All objects were listed of bucket")
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: list objects using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7533")
    @CTFailOn(error_handler)
    def test_check_bucket_exist_2378(self):
        """Bucket exists using jcloudclient."""
        self.log.info("STARTED: Bucket exists using jcloudclient")
        self.log.info("STEP 1: Creating bucket %s", self.bucket_name)
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 1: Bucket was created %s", self.bucket_name)
        self.log.info(
            "STEP 2: Check bucket %s exists on s3 server", self.bucket_name)
        command = self.create_cmd_format(
            self.bucket_name,
            "exists",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        success_msg = "Bucket {} exists".format(self.bucket_name)
        assert_utils.assert_in(success_msg, resp[1][:-1], resp[1])
        self.log.info(
            "STEP 2: Bucket %s exists on s3 server", self.bucket_name)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Bucket exists using jcloudclient")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7534")
    @CTFailOn(error_handler)
    def test_max_bucket_support_2383(self):
        """max no of buckets supported using Jclient."""
        self.log.info("STARTED: max no of buckets supported using Jclient")
        common_cfg = BLACKBOX_CONF["jcloud_cfg"]
        bkt_lst = []
        self.log.info("STEP 1: Creating n buckets")
        for bkt in range(1000):
            bkt_name_str = "{}-{}".format(self.bucket_name, bkt)
            self.log.info(
                "Creating bucket with name : %s", bkt_name_str)
            command = self.create_cmd_format(bkt_name_str,
                                             "mb",
                                             jtool=common_cfg["jclient_tool"])
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            bkt_lst.append(bkt_name_str)
            assert_utils.assert_in(
                "Bucket created successfully", resp[1][:-1], resp[1])
            self.log.info(
                "Bucket %s was created successfully", bkt_name_str)
        self.log.info("STEP 1: n buckets were created successfully")
        self.bucket_list = bkt_lst
        self.log.info("STEP 2: Verifying all the buckets")
        resp = S3_TEST_OBJ.bucket_list()
        assert_utils.assert_true(resp[0], resp[1])
        s3_bkt_lst = [bkt for bkt in resp[1] if self.bucket_name in bkt]
        assert_utils.assert_equal(bkt_lst.sort(), s3_bkt_lst.sort(), resp)
        self.log.info("STEP 2: All the s3 buckets created were verified")
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
        resp = S3_TEST_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for obj_name in obj_lst:
            file_p = os.path.join(self.root_path,
                                  obj_name)
            self.file_path_lst.append(file_p)
            system_utils.create_file(file_p,
                                     10)
            S3_TEST_OBJ.put_object(self.bucket_name, obj_name, file_p)
        self.log.info(
            "STEP 1: Creating a bucket and uploading multiple objects was successful")
        self.log.info(
            "STEP 2: Deleting multiple objects from bucket %s", self.bucket_name)
        objects_str = " ".join(obj_lst)
        bucket_str = "{} {}".format(self.bucket_name, objects_str)
        command = self.create_cmd_format(
            bucket_str,
            "multidel",
            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            "Objects deleted successfully", resp[1][:-1], resp[1])
        self.bucket_list.append(self.bucket_name)
        self.log.info("STEP 2: Successfully deleted multiple objects")
        self.log.info("ENDED: delete multiple objects using jclient")
