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

"""S3 Concurrency test module."""

import os
import time
from multiprocessing import Process, Manager

import logging
import pytest
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_cmd_test_lib import S3CmdTestLib

MANAGER = Manager()
S3T_OBJ = S3TestLib()
S3CMDT_OBJ = S3CmdTestLib()


class TestS3Concurrency:
    """S3 Concurrency Operations Test suite."""
    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """

        cls.log.info("STARTED: setup test suite operations.")
        cls.file_lst = []
        cls.s3cmd_cfg = {
            "common_cfg": {
                "s3cmd_tool": "s3cmd",
                "success_msg": "Bucket '{}/' create",
                "make_bucket": "mb",
                "put_bucket": "put",
                "remove_bucket": "rb",
                "force": "--force",
                "get": "get"}
        }
        cls.test_dir_path = os.path.join(
            os.getcwd(), "testdata", "TestS3Concurrency")
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if system_utils.path_exists(cls.test_dir_path):
            system_utils.remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        self.random_id = int(time.time())
        self.bkt_name_prefix = "concurrency"
        self.bucket_name = f"{self.bkt_name_prefix}-{self.random_id}"
        self.bucket_url = "s3://{}".format(self.bucket_name)
        self.obj_name = f"obj{self.random_id}.txt"
        self.resp_lst = MANAGER.list()
        self.log.info("File list: %s", self.file_lst)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info(
            "Deleting all buckets/objects created during TC execution")
        bucket_list = S3T_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.bkt_name_prefix)]
        if pref_list:
            resp = S3T_OBJ.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("Deleting the directory created locally for object")
        for file in self.file_lst:
            if system_utils.path_exists(file):
                system_utils.remove_file(file)
        self.log.info("Local directory was deleted")
        self.log.info("ENDED: Teardown Operations")

    def create_bucket_thread(self, bkt_name, resp_lst):
        """
        Creating s3 Bucket using aws/boto functionality.

        :param str bkt_name: Name of the bucket
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        resp = S3T_OBJ.create_bucket(bkt_name)
        self.log.info(resp)
        resp_lst.append(resp)

    def create_bucket_s3cmd_thread(self, bucket_url, resp_lst):
        """
        Creating s3 Bucket using s3cmd command tool.

        :param str bucket_url: URL containing bucket name
        :param lst resp_lst: shared object for maintaining operation response
        :return: None
        """
        cmd_arguments = [bucket_url]

        command = S3CMDT_OBJ.command_formatter(
            self.s3cmd_cfg, self.s3cmd_cfg["common_cfg"]["make_bucket"], cmd_arguments)
        self.log.info("Command is : %s", command)
        resp = system_utils.run_local_cmd(command)
        resp_lst.append(resp)

    def put_object_thread(self, bkt_name, obj_name, file_path, resp_lst):
        """
        Putting Object to the s3 Bucket using aws/boto functionality.

        :param str bkt_name: Name of s3 bucket
        :param str obj_name: Name of the object
        :param str file_path: Path to the object file
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        resp = S3T_OBJ.put_object(bkt_name, obj_name, file_path)
        self.log.info(resp)
        resp_lst.append(resp)

    def upload_object_thread(self, bkt_name, obj_name, file_path, resp_lst):
        """
        Uploading Object to the Bucket using aws/boto functionality.

        :param str bkt_name: Name of s3 bucket
        :param str obj_name: Name of the object
        :param str file_path: Path to the object file
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        resp = S3T_OBJ.object_upload(bkt_name, obj_name, file_path)
        self.log.info(resp)
        resp_lst.append(resp)

    def put_object_s3cmd_thread(
            self,
            bucket_url,
            file_path,
            resp_lst):
        """
        Putting Object to the s3 Bucket using s3cmd command tool.

        :param str bucket_url: URL path containing the bucket name
        :param str file_path: Path to the object file
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        cmd_arguments = [file_path, bucket_url]
        command = S3CMDT_OBJ.command_formatter(
            self.s3cmd_cfg, self.s3cmd_cfg["common_cfg"]["put_bucket"], cmd_arguments)
        self.log.info("Command is : %s", command)
        resp = system_utils.run_local_cmd(command)
        resp_lst.append(resp)

    def del_object_thread(self, bkt_name, obj_name, resp_lst):
        """
        Function deletes the object from s3 bucket using aws/boto functionality.

        :param str bkt_name: Name of s3 bucket
        :param str obj_name: Name of the object
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        resp = S3T_OBJ.delete_object(bkt_name, obj_name)
        self.log.info(resp)
        resp_lst.append(resp)

    def del_bucket_thread(self, bkt_name, resp_lst):
        """
        Delete buckets.

        Function deletes the empty bucket or deleting the buckets along with objects stored in it
        :param str bkt_name: Name of s3 bucket
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        resp = S3T_OBJ.delete_bucket(bkt_name, force=True)
        self.log.info(resp)
        resp_lst.append(resp)

    def get_obj_s3cmd_thread(self, bucket_url, filename, resp_lst):
        """
        Retrieve object from specified S3 bucket using the s3cmd command tool.

        :param str bucket_url: URL path containing the bucket name
        :param str filename: Path to the object file
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        cmd_arguments = ["/".join([bucket_url, filename]),
                         self.s3cmd_cfg["common_cfg"]["force"]]
        command = S3CMDT_OBJ.command_formatter(
            self.s3cmd_cfg, self.s3cmd_cfg["common_cfg"]["get"], cmd_arguments)
        self.log.info("Command is : %s", command)
        resp = system_utils.run_local_cmd(command)
        resp_lst.append(resp)

    def del_object_s3cmd_thread(
            self,
            bucket_url,
            filename,
            del_cmd,
            resp_lst):
        """
        Function deletes the object from s3 bucket using s3cmd command tool.

        :param str bucket_url: URL path containing the bucket name
        :param str filename: Path to the object file
        :param str del_cmd: delete s3cmd command option
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        cmd_arguments = ["/".join([bucket_url, filename])]
        command = S3CMDT_OBJ.command_formatter(
            self.s3cmd_cfg, del_cmd, cmd_arguments)
        self.log.info("Command is : %s", command)
        resp = system_utils.run_local_cmd(command)
        resp_lst.append(resp)

    def del_bucket_s3cmd_thread(
            self,
            bucket_url,
            rem_cmd,
            resp_lst):
        """
        Function deletes the empty bucket or deleting the buckets along with objects stored in it.

        :param str bucket_url: URL path containing the bucket name
        :param str rem_cmd: remove bucket s3cmd command option
        :param list resp_lst: shared object for maintaining operation response
        :return: None
        """
        cmd_arguments = [bucket_url]
        command = S3CMDT_OBJ.command_formatter(
            self.s3cmd_cfg, rem_cmd, cmd_arguments)
        self.log.info("Command is : %s", command)
        resp = system_utils.run_local_cmd(command)
        resp_lst.append(resp)

    def start_concurrent_clients(self, process_lst, resp_lst, all_true=None):
        """
        Start concurrent clients process parallel and validate the process response result.

        :param list process_lst: list containing the client process of aws and s3cmd
        :param list resp_lst: shared object for maintaining thread communication
        :param boolean all_true: flag to check all clients returning success or
        either success/failure result
        :return: None
        """
        for process in process_lst:
            process.start()
        for process in process_lst:
            process.join()
        resp = all([resp_lst[0][1], resp_lst[1][0]]) if all_true else any(
            [resp_lst[0][1], resp_lst[1][0]])
        self.log.info(resp)
        assert_utils.assert_true(resp, resp_lst)

    def create_bkt_put_obj_list_obj(self, bucket: str, obj_name: str, file_path: str,
                                    obj_size: int = 10):
        """
        Helper function to create bucket, put object and list object.

        :param bucket: Bucket name
        :param obj_name: An object name
        :param file_path: Path to the file
        :param obj_size: Size of an object
        :return:
        """
        resp = S3T_OBJ.create_bucket_put_object(
            bucket, obj_name, file_path, obj_size)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: List objects of bucket: %s", bucket)
        resp = S3T_OBJ.object_list(bucket)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: All the objects listed")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7954")
    @CTFailOn(error_handler)
    def test_existing_objects_being_overwritten_by_multiple_client_2128(self):
        """Existing Object is being overwritten by multiple client."""
        self.log.info(
            "STARTED: Existing Object is being overwritten by multiple client")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        self.create_bkt_put_obj_list_obj(self.bucket_name, self.obj_name, file_path)
        self.log.info("Step 2: Put the same object in the bucket with 2 "
                      "different s3 clients at the same time")
        helpers = (self.put_object_thread, self.put_object_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.obj_name, file_path, self.resp_lst),
                        (self.bucket_url, file_path, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst, all_true=True)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Put object operation from both the s3 clients got passed successfully")
        self.log.info(
            "ENDED: Existing Object is being overwritten by multiple client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7962")
    @CTFailOn(error_handler)
    def test_obj_download_triggered_from_client_and_delete_triggered_from_other_client_2129(
            self):
        """
        Delete object when download is in progress.

        Object download is in progress on one s3 client and delete object triggered from
        other s3 client.
        """
        self.log.info(
            "STARTED: Object download is in progress on one s3 client "
            "and delete object triggered from other s3 client")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        self.create_bkt_put_obj_list_obj(self.bucket_name, self.obj_name, file_path)
        self.log.info(
            "Step 2: Initiate Get object from s3cmd client and now parallels trigger "
            "the object delete operation from awscli client")
        helpers = (self.get_obj_s3cmd_thread, self.del_object_thread)
        helpers_args = ((self.bucket_url, self.obj_name, self.resp_lst),
                        (self.bucket_name, self.obj_name, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Get object and delete object from both the s3 clients")
        self.log.info("ENDED: Object download is in progress on one s3 client "
                      "and delete object triggered from other s3 client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7956")
    @CTFailOn(error_handler)
    def test_object_download_in_progress_on_one_client_delete_bucket_triggered_from_other_2130(
            self):
        """
        Delete bucket on Object download.

        Object download in progress on one client and delete bucket
        (in which the object exits) is triggered from the other s3 client
        """
        self.log.info(
            "STARTED: Object download in progress on one client and delete bucket "
            "(in which the object exits) is triggered from the other s3 client")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        self.create_bkt_put_obj_list_obj(self.bucket_name, self.obj_name, file_path)
        self.log.info(
            "Step 2: Initiate Get object from s3cmd client and in "
            "Parallel trigger the delete bucket operation from awscli client ")
        helpers = (self.put_object_s3cmd_thread, self.del_bucket_thread)
        helpers_args = ((self.bucket_url, file_path, self.resp_lst),
                        (self.bucket_name, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Delete bucket operation will get passed and Get object operation"
            " will fail in between")
        self.log.info(
            "ENDED: Object download in progress on one client and delete bucket "
            "(in which the object exits) is triggered from the other s3 client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7957")
    @CTFailOn(error_handler)
    def test_parallel_bucket_creation_of_same_name_from_two_different_clients_2131(
            self):
        """Parallel bucket creation of same name from 2 different clients."""
        self.log.info(
            "STARTED: Parallel bucket creation of same name from 2 different clients")
        self.log.info("Step 1: Create bucket from s3cmd and aws parallely")
        helpers = (self.create_bucket_thread, self.create_bucket_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.resp_lst),
                        (self.bucket_url, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst)
        self.log.info(
            "Step 2: With parallel execution either of the operation from s3cmd or awscli will "
            "get passed and other will fail with 'bucket exist' error.")
        self.log.info(
            "ENDED: Parallel bucket creation of same name from 2 different clients")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7958")
    @CTFailOn(error_handler)
    def test_parallel_deletion_of_same_object_from_two_different_clients_2132(
            self):
        """Parallel deletion of same object from 2 different clients."""
        self.log.info(
            "STARTED: Parallel deletion of same object from 2 different clients")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        self.create_bkt_put_obj_list_obj(self.bucket_name, self.obj_name, file_path)
        self.log.info(
            "Step 2: Parallel initiate delete of same object from both s3cmd and awscli")
        helpers = (self.del_object_thread, self.del_object_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.obj_name, self.resp_lst),
                        (self.bucket_url, self.obj_name, "del", self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst, all_true=True)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: On parallel execution of deletion of object from awscli and"
            " s3cmd client ,both got executed successfully without any error")
        self.log.info(
            "ENDED: Parallel deletion of same object from 2 different clients")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7959")
    @CTFailOn(error_handler)
    def test_upload_object_to_bucket_from_one_client_and_parallel_delete_bkt_from_other_client_2133(
            self):
        """
        Upload objects.

        Upload an object to the bucket from one s3 client and in parallel
        try to delete the same bucket from other s3 client
        """
        self.log.info(
            "STARTED: Upload an object to the bucket from one s3 client and in parallel"
            "try to delete the same bucket from other s3 client")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        system_utils.create_file(file_path, 100)
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket was created")
        self.log.info(
            "Step 2: Initiate Get object from s3cmd client and in "
            "Parallel trigger the delete bucket operation from awscli client ")
        helpers = (self.del_bucket_thread, self.put_object_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.resp_lst),
                        (self.bucket_url, file_path, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Delete bucket operation will get passed and Get object operation"
            " will fail in between")
        self.log.info(
            "ENDED: Upload an object to the bucket from one s3 client and in parallel "
            "try to delete the same bucket from other s3 client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7960")
    @CTFailOn(error_handler)
    def test_parallel_deletion_of_bucket_from_two_different_clients_2134(self):
        """Parallel deletion of bucket from 2 different clients."""
        self.log.info(
            "STARTED: Parallel deletion of bucket from 2 different clients")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        self.create_bkt_put_obj_list_obj(self.bucket_name, self.obj_name, file_path, 100)
        self.log.info(
            "Step 2: Remove the bucket simultaneously using aws and s3cmd clients.")
        helpers = (self.del_bucket_thread, self.del_bucket_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.resp_lst),
                        (self.bucket_url, "rb", self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Delete bucket operation will get completed successfully on one of the "
            "s3 client and on other s3 client will failed saying bucket doesn't exist")
        self.log.info(
            "ENDED: Parallel deletion of bucket from 2 different clients")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7961")
    @CTFailOn(error_handler)
    def test_put_object_through_one_s3_client_try_deleting_it_from_other_client_2135(
            self):
        """Put object through one s3 client and try deleting it from other s3 client."""
        self.log.info(
            "STARTED: Put object through one s3 client and try deleting it from other s3 client")
        file_path = os.path.join(self.test_dir_path, self.obj_name)
        self.log.info("Step 1: Creating a bucket%s", self.bucket_name)
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket was created")
        self.log.info(
            "Step 2: Upload an object from s3cmd client and in parallely "
            "try removing the same object from awscli client ")
        helpers = (self.del_bucket_thread, self.put_object_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.resp_lst),
                        (self.bucket_url, file_path, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst)
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Remove object operation get run successfully if called after put else fail"
            "and put object operation will also get passed")
        self.log.info(
            "ENDED: Put object through one s3 client and try deleting it from other s3 client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7963")
    @CTFailOn(error_handler)
    def test_download_an_already_existing_obj_from_one_client_parallel_overwrite_it_2136(
            self):
        """
        Download existing objects.

        Download an already existing object from one client and in parallel
        overwrite the same object from other s3 client
        """
        self.log.info(
            "STARTED: Download an already existing object from one client and in parallel "
            "overwrite the same object from other s3 client")
        file_path = os.path.join("/tmp", self.obj_name)
        resp = S3T_OBJ.create_bucket_put_object(
            self.bucket_name, self.obj_name, file_path, 10)
        assert_utils.assert_true(resp[0], resp[1])
        self.file_lst.append(file_path)
        self.log.info(
            "Step 2: Initiate get object from awscli and simultaneously "
            "initiate upload object with same name from s3cmd in same bucket")
        helpers = (self.upload_object_thread, self.get_obj_s3cmd_thread)
        helpers_args = ((self.bucket_name, self.obj_name, file_path, self.resp_lst),
                        (self.bucket_url, self.obj_name, self.resp_lst))
        client_lst = list()
        for helper, h_arg in zip(helpers, helpers_args):
            self.log.debug("Calling %s with args %s", helper, h_arg)
            client_lst.append(
                Process(
                    target=helper, args=h_arg)
            )
        self.start_concurrent_clients(client_lst, self.resp_lst, all_true=True)
        self.file_lst.append(os.path.join(self.test_dir_path, self.obj_name))
        self.log.info(
            "Step 2: Operations on both s3 clients when triggered in parallel "
            "got executed successfully without error")
        self.log.info(
            "ENDED: Download an already existing object from one client and in parallel "
            "overwrite the same object from other s3 client")
