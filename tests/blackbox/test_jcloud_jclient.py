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
'cortx-test/scripts/tools'
"""

import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler, S3_CLIENT_ERROR
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import execute_cmd, create_file, remove_file
from commons.utils.assert_utils import assert_true, assert_in, assert_equal
from libs.s3 import s3_test_lib
from libs.s3 import S3H_OBJ, ACCESS_KEY, SECRET_KEY

S3_TEST_OBJ = s3_test_lib.S3TestLib()
BLACKBOX_CONF = read_yaml("config/blackbox/test_jcloud_jclient.yaml")[1]


class TestJcloudAndJclient:
    """Blaclbox jcloud and jclient Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.random_id = str(time.time())
        cls.access_key = ACCESS_KEY
        cls.secret_key = SECRET_KEY
        cls.file_path_lst = []

    @CTFailOn(error_handler)
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log.info("STARTED: Setup operations.")
        res_ls = execute_cmd(
            BLACKBOX_CONF["common_cfg"]["ls_script_path_cmd"])[1]
        res = ".jar" in res_ls
        if not res:
            res = S3H_OBJ.configure_jclient_cloud()
            if not res:
                raise CTException(
                    S3_CLIENT_ERROR,
                    BLACKBOX_CONF["common_cfg"]["jar_skip_err"])

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
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        if bucket_list:
            pref_list = [
                each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                    BLACKBOX_CONF["common_cfg"]["bkt_prefix"])]
            S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("Deleting the directory created locally for object")
        if self.file_path_lst:
            for file_name in self.file_path_lst:
                if os.path.exists(file_name):
                    resp = remove_file(file_name)
                    assert_true(resp[0], resp[1])
        self.log.info("Local directory was deleted")
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
        if jtool == BLACKBOX_CONF["common_cfg"]["jcloud_tool"]:
            java_cmd = BLACKBOX_CONF["common_cfg"]["jcloud_cmd"]
            aws_keys_str = BLACKBOX_CONF["common_cfg"]["jcloud_format_keys"].format(
                self.access_key, self.secret_key)
        else:
            java_cmd = BLACKBOX_CONF["common_cfg"]["jclient_cmd"]
            aws_keys_str = BLACKBOX_CONF["common_cfg"]["jclient_format_keys"].format(
                self.access_key, self.secret_key)
        bucket_url = BLACKBOX_CONF["common_cfg"]["bkt_path_format"].format(
            bucket)

        path_style = BLACKBOX_CONF["common_cfg"]["path_style_opt"]
        cmd = "{} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                      aws_keys_str, path_style)

        return cmd

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7094")
    @CTFailOn(error_handler)
    def test_create_bucket_2368(self):
        """create bucket using Jcloudclient."""
        self.log.info("STARTED: create bucket using Jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2368"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            BLACKBOX_CONF["common_cfg"]["make_bucket"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["success_msg"], resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("ENDED: create bucket using Jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7095")
    @CTFailOn(error_handler)
    def test_delete_bucket_2370(self):
        """Delete bucket using jcloudclient."""
        self.log.info("STARTED: delete bucket using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2370"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            BLACKBOX_CONF["common_cfg"]["make_bucket"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["success_msg_create"], resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Deleting buckets %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["remove_bkt"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["success_msg_del"], resp)
        self.log.info(
            "STEP: 2 Bucket %s was deleted successfully", bucket_name)
        self.log.info("ENDED: delete bucket using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7096")
    @CTFailOn(error_handler)
    def test_put_object_2373(self):
        """Put object using jcloudclient."""
        self.log.info("STARTED: put object using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2373"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            BLACKBOX_CONF["common_cfg"]["make_bucket"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["create_success_msg"], resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Put object to a bucket %s", bucket_name)
        create_file(BLACKBOX_CONF["common_cfg"]["file_path"],
                    BLACKBOX_CONF["common_cfg"]["file_size"])
        put_cmd_str = "{} {}".format(test_cfg["put_cmd"],
                                     BLACKBOX_CONF["common_cfg"]["file_path"])
        command = self.create_cmd_format(
            bucket_name,
            put_cmd_str,
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["obj_success_msg"], resp)
        self.log.info(
            "STEP: 2 Put object to a bucket %s was successful", bucket_name)
        self.file_path_lst.append(BLACKBOX_CONF["common_cfg"]["file_path"])
        self.log.info("ENDED: get object using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7097")
    @CTFailOn(error_handler)
    def test_get_object_2374(self):
        """Get object using jcloudclient."""
        self.log.info("STARTED: get object using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2374"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            BLACKBOX_CONF["common_cfg"]["make_bucket"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["create_success_msg"], resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info(
            "STEP: 2 Uploading an object to a bucket %s", bucket_name)
        create_file(BLACKBOX_CONF["common_cfg"]["file_path"],
                    BLACKBOX_CONF["common_cfg"]["file_size"])
        put_cmd_str = "{} {}".format(test_cfg["put_cmd"],
                                     BLACKBOX_CONF["common_cfg"]["file_path"])
        command = self.create_cmd_format(
            bucket_name,
            put_cmd_str,
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["put_obj_msg"], resp)
        self.log.info(
            "STEP: 2 Put object to a bucket %s was successful", bucket_name)
        self.log.info("STEP: 3 Get object from bucket %s", bucket_name)
        file_path = BLACKBOX_CONF["common_cfg"]["file_path"].split("/")[-1]
        self.file_path_lst.append(file_path)
        bucket_str = "{0}/{1} {1}".format(bucket_name, file_path)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["get_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["get_obj_msg"], resp)
        self.log.info("STEP: 3 Object was downloaded successfully")
        self.file_path_lst.append(os.path.join(
            BLACKBOX_CONF["common_cfg"]["file_path"]))
        self.log.info("ENDED: put object using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7098")
    @CTFailOn(error_handler)
    def test_delete_object_2375(self):
        """Delete object using jcloudclient."""
        self.log.info("STARTED: delete object using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2375"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name, BLACKBOX_CONF["common_cfg"]["make_bucket"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["create_success_msg"], resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info(
            "STEP: 2 Uploading an object to a bucket %s", bucket_name)
        create_file(BLACKBOX_CONF["common_cfg"]["file_path"],
                    BLACKBOX_CONF["common_cfg"]["file_size"])
        put_cmd_str = "{} {}".format(test_cfg["put_cmd"],
                                     BLACKBOX_CONF["common_cfg"]["file_path"])
        command = self.create_cmd_format(
            bucket_name,
            put_cmd_str,
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["put_obj_msg"], resp)
        self.log.info(
            "STEP: 2 Put object to a bucket %s was successful", bucket_name)
        self.log.info(
            "STEP: 3 Deleting object from bucket %s", bucket_name)
        file_name = BLACKBOX_CONF["common_cfg"]["file_path"].split("/")[-1]
        bucket_str = "{0}/{1} {1}".format(bucket_name, file_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["del_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["get_obj_msg"], resp)
        self.log.info("STEP: 3 Object was deleted successfully")
        self.file_path_lst.append(BLACKBOX_CONF["common_cfg"]["file_path"])
        self.log.info("ENDED: delete object using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7099")
    @CTFailOn(error_handler)
    def test_del_multiple_objects_2376(self):
        """Delete multiple objects using jcloudclient."""
        self.log.info("STARTED: delete multiple objects using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2376"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and uploading multiple objects")
        obj_lst = test_cfg["obj_list"]
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        for obj_name in obj_lst:
            file_p = os.path.join(BLACKBOX_CONF["common_cfg"]["root_path"],
                                  obj_name)
            self.file_path_lst.append(file_p)
            create_file(file_p,
                        BLACKBOX_CONF["common_cfg"]["file_size"])
            S3_TEST_OBJ.put_object(bucket_name, obj_name, file_p)
        self.log.info(
            "STEP: 1 Creating a bucket and uploading multiple objects was successful")
        self.log.info(
            "STEP: 2 Deleting multiple objects from bucket %s", bucket_name)
        objects_str = " ".join(obj_lst)
        bucket_str = "{} {}".format(bucket_name, objects_str)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["multi_del"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["multi_del_msg"], resp)
        self.log.info("STEP: 2 Successfully deleted all objects")
        self.log.info("ENDED: delete multiple objects using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7100")
    @CTFailOn(error_handler)
    def test_head_object_2377(self):
        """Head object using jcloudclient."""
        self.log.info("STARTED: head object using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2377"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info(
            "STEP: 1 Creating bucket and uploading object in bucket %s",
            bucket_name)
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get head object")
        bucket_str = "{}/{}".format(bucket_name, obj_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["head_obj_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        output_objname = resp[1].split("\n")[1].split("-")[1].strip()
        assert_equal(output_objname, obj_name, resp)
        self.log.info("STEP: 2 Get head object was successful")
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: head object using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7101")
    @CTFailOn(error_handler)
    def test_check_obj_exists_2379(self):
        """object exists using jcloudclient."""
        self.log.info("STARTED: object exists using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2379"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and uploading object")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Check object exists in the bucket %s", bucket_name)
        bucket_str = "{}/{}".format(bucket_name, obj_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["exists_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        success_msg = test_cfg["exists_msg"].format(obj_name)
        assert_equal(resp[1][:-1], success_msg, resp)
        self.log.info(
            "STEP: 2 Object exists in the bucket %s", bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: object exists using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7102")
    @CTFailOn(error_handler)
    def test_remove_empty_bucket_2380(self):
        """Remove bucket if empty."""
        self.log.info("STARTED: Remove bucket if empty")
        test_cfg = BLACKBOX_CONF["test_2380"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info(
            "STEP: 2 Trying to remove bucket: %s if empty", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["rb_bkt_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["rb_bkt_msg"], resp)
        self.log.info("STEP: 2 Bucket was successfully removed")
        self.log.info("ENDED: Remove bucket if empty")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7103")
    @CTFailOn(error_handler)
    def test_create_bucket_2381(self):
        """create bucket using jclient."""
        self.log.info("STARTED: create bucket using jclient")
        test_cfg = BLACKBOX_CONF["test_2381"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            BLACKBOX_CONF["common_cfg"]["make_bucket"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["success_msg"], resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("ENDED: create bucket using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7104")
    @CTFailOn(error_handler)
    def test_list_bucket_2382(self):
        """list bucket using jclient."""
        self.log.info("STARTED: list bucket using jclient")
        test_cfg = BLACKBOX_CONF["test_2382"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Listing all the bucket created")
        java_cmd = BLACKBOX_CONF["common_cfg"]["jclient_cmd"]
        aws_keys_str = BLACKBOX_CONF["common_cfg"]["jclient_format_keys"].format(
            self.access_key, self.secret_key)
        command = "{} {} {}".format(
            java_cmd, test_cfg["lst_bkt_cmd"], aws_keys_str)
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        bkt_lst = resp[1][9:].strip().split("\n")
        self.log.info("Bucket List %s", bkt_lst)
        assert_in(bucket_name, bkt_lst, resp)
        self.log.info("STEP: 2 All buckets were listed")
        self.log.info("ENDED: list bucket using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7105")
    @CTFailOn(error_handler)
    def test_delete_bucket_2384(self):
        """delete bucket using jclient."""
        self.log.info("STARTED: delete bucket using jclient")
        test_cfg = BLACKBOX_CONF["test_2384"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info(
            "STEP: 2 Trying to delete a bucket: %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["remove_bkt"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["del_success_msg"], resp)
        self.log.info("STEP: 2 Bucket was successfully deleted")
        self.log.info("ENDED: delete bucket using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7106")
    @CTFailOn(error_handler)
    def test_list_object_2385(self):
        """list object using jclient."""
        self.log.info("STARTED: list object using jclient")
        test_cfg = BLACKBOX_CONF["test_2385"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and uploading object")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Listing all the objects from buckets %s", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["ls_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        self.log.info("Object List %s", resp[1])
        assert_in(obj_name, resp[1], resp)
        self.log.info("STEP: 2 All objects were listed of bucket")
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: list object using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7107")
    @CTFailOn(error_handler)
    def test_delete_object_2386(self):
        """delete object using jclient."""
        self.log.info("STARTED: delete object using jclient")
        test_cfg = BLACKBOX_CONF["test_2386"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and uploading object")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Deleting object from bucket %s", bucket_name)
        bucket_str = "{}/{}".format(bucket_name, obj_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["del_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["multi_del_msg"], resp)
        self.log.info("STEP: 2 Object was deleted successfully")
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: delete object using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7108")
    @CTFailOn(error_handler)
    def test_head_object_2388(self):
        """head object using jclient."""
        self.log.info("STARTED: head object using jclient")
        test_cfg = BLACKBOX_CONF["test_2388"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and upload object")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get head object")
        bucket_str = "{}/{}".format(bucket_name, obj_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["head_obj_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        output_objname = resp[1].split("\n")[1].split("-")[1].strip()
        assert_equal(output_objname, obj_name, resp)
        self.log.info("STEP: 2 Get head object was successful")
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: head object using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7109")
    @CTFailOn(error_handler)
    def test_put_obj_2389(self):
        """put object using jclient."""
        self.log.info("STARTED: put object using jclient")
        test_cfg = BLACKBOX_CONF["test_2389"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info(
            "STEP: 2 Uploading an object to a bucket %s", bucket_name)
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        create_file(file_path,
                    BLACKBOX_CONF["common_cfg"]["file_size"])
        put_cmd = "{} {}".format(test_cfg["put_cmd"], file_path)
        command = self.create_cmd_format(
            bucket_name, put_cmd, jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["obj_success_msg"], resp)
        self.log.info(
            "STEP: 2Put object to a bucket %s was successful", bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: put object using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7110")
    @CTFailOn(error_handler)
    def test_get_object_2390(self):
        """get object using jclient."""
        self.log.info("STARTED: get object using jclient")
        test_cfg = BLACKBOX_CONF["test_2390"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and uploading object")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info("STEP: 2 Get object from bucket %s", bucket_name)
        bucket_str = "{0}/{1} {1}".format(bucket_name, obj_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["get_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["get_obj_msg"], resp)
        self.log.info("STEP: 2 Object was downloaded successfully")
        self.file_path_lst.append(file_path)
        self.file_path_lst.append(os.path.join(os.getcwd(), obj_name))
        self.log.info("ENDED: put object using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7111")
    @CTFailOn(error_handler)
    def test_bucket_exists_2391(self):
        """Bucket exists using Jclient."""
        self.log.info("STARTED: Bucket exists using Jclient")
        test_cfg = BLACKBOX_CONF["test_2391"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info(
            "STEP: 2 Check bucket %s exists on s3 server", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["exists_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        success_msg = test_cfg["exists_msg"].format(bucket_name)
        assert_equal(resp[1][:-1], success_msg, resp)
        self.log.info(
            "STEP: 2 Bucket %s exists on s3 server", bucket_name)
        self.log.info("ENDED: Bucket exists using Jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7112")
    @CTFailOn(error_handler)
    def test_check_obj_exists_2392(self):
        """object exists using jclient."""
        self.log.info("STARTED: object exists using jclient")
        test_cfg = BLACKBOX_CONF["test_2392"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP: 1 Creating bucket and uploading objects")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(BLACKBOX_CONF["common_cfg"]
                                   ["root_path"], obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP: 1 Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP: 2 Check object exists in the bucket %s", bucket_name)
        bucket_str = "{}/{}".format(bucket_name, obj_name)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["exists_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["exists_msg"], resp)
        self.log.info(
            "STEP: 2 Object exists in the bucket %s", bucket_name)
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: object exists using jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7529")
    @CTFailOn(error_handler)
    def test_list_buckets_2369(self):
        """list buckets using jcloudclient."""
        self.log.info("STARTED: list buckets using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2369"]
        common_cfg = BLACKBOX_CONF["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP 1: Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP 1: Bucket was created %s", bucket_name)
        self.log.info("STEP 2: Listing all the buckets")
        keys_str = common_cfg["jcloud_format_keys"].format(
            self.access_key, self.secret_key)
        command = "{} {} {}".format(common_cfg["jcloud_cmd"],
                                    test_cfg["ls_bkt_cmd"], keys_str)
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        bucket_lst = [bkt.strip() for bkt in resp[1].split("\n")]
        assert_in(bucket_name, bucket_lst, resp)
        self.log.info("STEP 2: All the s3 bucket listed")
        self.log.info("ENDED: list buckets using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7531")
    @CTFailOn(error_handler)
    def test_max_bucket_2371(self):
        """max no of buckets supported using jcloudclient."""
        self.log.info(
            "STARTED: max no of buckets supported using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2371"]
        common_cfg = BLACKBOX_CONF["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        bkt_lst = []
        self.log.info("STEP 1: Creating n buckets")
        for bkt in range(test_cfg["bucket_count"]):
            bkt_name_str = "{}-{}".format(bucket_name, bkt)
            self.log.info(
                "Creating bucket with name : %s", bkt_name_str)
            command = self.create_cmd_format(
                bkt_name_str,
                common_cfg["make_bucket"],
                jtool=common_cfg["jcloud_tool"])
            resp = execute_cmd(command)
            assert_true(resp[0], resp[1])
            bkt_lst.append(bkt_name_str)
            assert_equal(resp[1][:-1], test_cfg["success_msg"], resp)
            self.log.info(
                "Bucket %s was created successfully", bkt_name_str)
        self.log.info("STEP 1: n buckets were created successfully")
        self.log.info("STEP 2: Verifying all the buckets")
        resp = S3_TEST_OBJ.bucket_list()
        assert_true(resp[0], resp[1])
        s3_bkt_lst = [bkt for bkt in resp[1] if bucket_name in bkt]
        assert_equal(bkt_lst.sort(), s3_bkt_lst.sort(), resp)
        self.log.info("STEP 2: All the s3 buckets created were verified")
        self.log.info("ENDED: max no of buckets supported using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7532")
    @CTFailOn(error_handler)
    def test_list_objects_2372(self):
        """list objects using jcloudclient."""
        self.log.info("STARTED: list objects using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2372"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP 1: Creating bucket and uploading object")
        obj_name = test_cfg["obj_name"]
        file_path = "{}/{}".format(
            BLACKBOX_CONF["common_cfg"]["root_path"],
            obj_name)
        S3_TEST_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            file_path,
            BLACKBOX_CONF["common_cfg"]["file_size"])
        self.log.info(
            "STEP 1: Creating a bucket and uploading object was successful")
        self.log.info(
            "STEP 2: Listing all the objects from buckets %s",
            bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["ls_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(obj_name, resp[1], resp)
        self.log.info("STEP 2: All objects were listed of bucket")
        self.file_path_lst.append(file_path)
        self.log.info("ENDED: list objects using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7533")
    @CTFailOn(error_handler)
    def test_check_bucket_exist_2378(self):
        """Bucket exists using jcloudclient."""
        self.log.info("STARTED: Bucket exists using jcloudclient")
        test_cfg = BLACKBOX_CONF["test_2378"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP 1: Creating bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("STEP 1: Bucket was created %s", bucket_name)
        self.log.info(
            "STEP 2: Check bucket %s exists on s3 server", bucket_name)
        command = self.create_cmd_format(
            bucket_name,
            test_cfg["exists_cmd"],
            jtool=BLACKBOX_CONF["common_cfg"]["jcloud_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        success_msg = test_cfg["exists_msg"].format(bucket_name)
        assert_equal(resp[1][:-1], success_msg, resp)
        self.log.info(
            "STEP 2: Bucket %s exists on s3 server", bucket_name)
        self.log.info("ENDED: Bucket exists using jcloudclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7534")
    @CTFailOn(error_handler)
    def test_max_bucket_support_2383(self):
        """max no of buckets supported using Jclient."""
        self.log.info("STARTED: max no of buckets supported using Jclient")
        test_cfg = BLACKBOX_CONF["test_2383"]
        common_cfg = BLACKBOX_CONF["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        bkt_lst = []
        self.log.info("STEP 1: Creating n buckets")
        for bkt in range(test_cfg["bucket_count"]):
            bkt_name_str = "{}-{}".format(bucket_name, bkt)
            self.log.info(
                "Creating bucket with name : %s", bkt_name_str)
            command = self.create_cmd_format(bkt_name_str,
                                             common_cfg["make_bucket"],
                                             jtool=common_cfg["jclient_tool"])
            resp = execute_cmd(command)
            assert_true(resp[0], resp[1])
            bkt_lst.append(bkt_name_str)
            assert_equal(resp[1][:-1], test_cfg["success_msg"], resp)
            self.log.info(
                "Bucket %s was created successfully", bkt_name_str)
        self.log.info("STEP 1: n buckets were created successfully")
        self.log.info("STEP 2: Verifying all the buckets")
        resp = S3_TEST_OBJ.bucket_list()
        assert_true(resp[0], resp[1])
        s3_bkt_lst = [bkt for bkt in resp[1] if bucket_name in bkt]
        assert_equal(bkt_lst.sort(), s3_bkt_lst.sort(), resp)
        self.log.info("STEP 2: All the s3 buckets created were verified")
        self.log.info("ENDED: max no of buckets supported using Jclient")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7535")
    @CTFailOn(error_handler)
    def test_del_multiple_object_2387(self):
        """delete multiple objects using jclient."""
        self.log.info("STARTED: delete multiple objects using jclient")
        test_cfg = BLACKBOX_CONF["test_2387"]
        bucket_name = test_cfg["bucket_name"].format(self.random_id)
        self.log.info("STEP 1: Creating bucket and uploading multiple objects")
        obj_lst = test_cfg["obj_list"]
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        for obj_name in obj_lst:
            file_p = os.path.join(BLACKBOX_CONF["common_cfg"]["root_path"],
                                  obj_name)
            self.file_path_lst.append(file_p)
            create_file(file_p,
                        BLACKBOX_CONF["common_cfg"]["file_size"])
            S3_TEST_OBJ.put_object(bucket_name, obj_name, file_p)
        self.log.info(
            "STEP 1: Creating a bucket and uploading multiple objects was successful")
        self.log.info(
            "STEP 2: Deleting multiple objects from bucket %s", bucket_name)
        objects_str = " ".join(obj_lst)
        bucket_str = "{} {}".format(bucket_name, objects_str)
        command = self.create_cmd_format(
            bucket_str,
            test_cfg["multi_del"],
            jtool=BLACKBOX_CONF["common_cfg"]["jclient_tool"])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1][:-1], test_cfg["multi_del_msg"], resp)
        self.log.info("STEP 2: Successfully deleted multiple objects")
        self.log.info("ENDED: delete multiple objects using jclient")
