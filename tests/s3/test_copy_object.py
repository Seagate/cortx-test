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

"""S3 copy object test module."""

import os
from time import perf_counter_ns
from multiprocessing import Process, Manager

import logging
import pytest
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER
from config import CMN_CFG
from config import S3_CFG
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib
from scripts.s3_bench import s3bench

IAM_OBJ = iam_test_lib.IamTestLib()
S3_OBJ = s3_test_lib.S3TestLib()


class TestCopyObjects:
    """S3 copy object class."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.log.info("Setup s3 bench tool")
        res = s3bench.setup_s3bench()
        assert_utils.assert_true(res, res)
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestS3CopyObject")
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

        1. Create bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        self.log.info("STARTED: test setup method.")
        self.account_name1 = "acc-copyobject-{}".format(perf_counter_ns())
        self.email_id = "{}@seagate.com"
        self.account_name2 = "acc-copyobject-{}".format(perf_counter_ns())
        self.io_bucket_name = "iobkt-copyobject-{}".format(perf_counter_ns())
        self.bucket_name1 = "bkt-copyobject-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-copyobject-{}".format(perf_counter_ns())
        self.object_name1 = "copyobject-{}".format(perf_counter_ns())
        self.object_name2 = "copyobject2-{}".format(perf_counter_ns())
        self.file_path = os.path.join(self.test_dir_path, self.object_name1)
        self.parallel_ios = None
        self.log.info("ENDED: test setup method.")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        1. Delete bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        self.log.info("STARTED: test teardown method.")
        self.log.info(
            "Deleting all buckets/objects created during TC execution")
        self.start_stop_validate_parallel_s3ios(ios="Stop")
        bucket_list = S3_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket in [
                self.bucket_name1,
                self.io_bucket_name,
                self.bucket_name2]]
        if pref_list:
            resp = S3_OBJ.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        self.log.info("ENDED: test teardown method.")

    def check_cluster_health(self):
        """Check the cluster health."""
        self.log.info(
            "Check cluster status, all services are running.")
        nodes = CMN_CFG["nodes"]
        self.log.info(nodes)
        for i in range(len(nodes)):
            health_obj = Health(hostname=nodes[i]["hostname"],
                                username=nodes[i]["username"],
                                password=nodes[i]["password"])
            resp = health_obj.check_node_health()
            self.log.info(resp)
            assert_utils.assert_true(resp[0], resp[1])
            health_obj.disconnect()
        self.log.info("Checked cluster status, all services are running.")

    def s3_ios(self,
               bucket=None,
               log_file_prefix="parallel_io",
               duration="0h3m",
               obj_size="2Mb",
               num_clients=5,
               num_sample=20,
               obj_name_pref="loadgen_",
               end_point=S3_CFG["s3_url"]):
        """
        Perform io's for specific durations.

        1. Create bucket.
        2. perform io's for specified durations.
        3. Check executions successful.
        """
        self.log.info("STARTED: s3 io's operations.")
        bucket = bucket if bucket else self.io_bucket_name
        resp = S3_OBJ.create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = S3H_OBJ.get_local_keys()
        resp = s3bench.s3bench(
            access_key,
            secret_key,
            bucket=bucket,
            end_point=end_point,
            num_clients=num_clients,
            num_sample=num_sample,
            obj_name_pref=obj_name_pref,
            obj_size=obj_size,
            duration=duration,
            verbose=True,
            log_file_prefix=log_file_prefix)
        self.log.info(resp)
        assert_utils.assert_true(
            os.path.exists(
                resp[1]),
            f"failed to generate log: {resp[1]}")
        self.log.info("ENDED: s3 io's operations.")

    def validate_parallel_execution(self, log_prefix=None):
        """Check parallel execution failure."""
        self.log.info("S3 parallel ios log validation started.")
        logflist = system_utils.list_dir(s3bench.LOG_DIR)
        log_path = None
        for filename in logflist:
            if filename.startswith(log_prefix):
                log_path = os.path.join(s3bench.LOG_DIR, filename)
        self.log.info("IO log path: %s", log_path)
        assert_utils.assert_is_not_none(
            log_path, f"failed to generate logs for parallel S3 IO.")
        lines = open(log_path).readlines()
        resp_filtered = [
            line for line in lines if 'Errors Count:' in line and "reportFormat" not in line]
        self.log.info("'Error count' filtered list: %s", resp_filtered)
        for response in resp_filtered:
            assert_utils.assert_equal(
                int(response.split(":")[1].strip()), 0, response)
        self.log.info("Observed no Error count in io log.")
        error_kws = ["with error ", "panic", "status code"]
        for error in error_kws:
            assert_utils.assert_not_equal(
                error, ",".join(lines), f"Parallel IOs failed.")
        self.log.info("Observed no Error keyword '%s' in io log.", error_kws)
        self.log.info("S3 parallel ios log validation completed.")

    def start_stop_validate_parallel_s3ios(self, ios=None, log_prefix=None, duration="0h2m"):
        """
        Start/stop parallel s3 io's and validate io's worked successfully.  
        """
        if ios == "Start":
            self.parallel_ios = Process(
                target=self.s3_ios, args=(
                    self.io_bucket_name, log_prefix, duration))
            if not self.parallel_ios.is_alive():
                self.parallel_ios.start()
            self.log.info("Parallel IOs started: %s for duration: %s",
                          self.parallel_ios.is_alive(), duration)
        if ios == "Stop":
            if self.parallel_ios.is_alive():
                resp = S3_OBJ.object_list(self.io_bucket_name)
                self.log.info(resp)
                self.parallel_ios.join()
                self.log.info("Parallel IOs stopped: %s", not self.parallel_ios.is_alive())
            if log_prefix:
                self.validate_parallel_execution(log_prefix)

    def create_bucket_put_object(self,
                                 s3_test_obj=None,
                                 bucket_name=None,
                                 object_name=None,
                                 file_path=None,
                                 **kwargs):
        """Create bucket and put object to bucket and return ETag."""
        self.log.info("Create bucket and put object.")
        resp = s3_test_obj.create_bucket(bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = s3_test_obj.bucket_list()
        self.log.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(bucket_name, bktlist,
                               f"failed to create bucket {bucket_name}")
        put_resp = s3_test_obj.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=file_path,
            **kwargs)
        self.log.info("put object response: %s", put_resp)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        resp = s3_test_obj.object_list(bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(object_name, resp[1],
                               f"failed to put object {object_name}")

        return True, put_resp[1]["ETag"].strip('"')

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19841")
    @CTFailOn(error_handler)
    def test_19841(self):
        """Copy object to same bucket with different object name while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object to same bucket with different object name while S3 IOs"
            " are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19841_ios",
                                                duration="0h4m")
        self.log.info("Step 3: Create bucket and put object in it.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, PutETag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name1, self.object_name1, self.file_path)
        self.log.info("Put object ETag: %s", PutETag)
        self.log.info(
            "Step 4: Copy object to same bucket with different object.")
        status, response = S3_OBJ.copy_object(self.bucket_name1, self.object_name1,
                                              self.bucket_name1, self.object_name2)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info("Copy object ETag: %s", CopyETag)
        self.log.info(
            "Steps 5: Compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19841_ios")
        self.log.info(
            "Steps 8: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to same bucket with different object name while S3 IOs"
            " are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19842")
    @CTFailOn(error_handler)
    def test_19842(self):
        """Copy object to same account different bucket while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object to same bucket with different object name while S3 IOs"
            " are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19842_ios",
                                                duration="0h4m")
        self.log.info("Step 3: Create bucket and put object in it.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, PutETag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name1, self.object_name1, self.file_path)
        self.log.info("Put object ETag: %s", PutETag)
        self.log.info(
            "Step 4: Copy object to different bucket with different object.")
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, response = S3_OBJ.copy_object(self.bucket_name1, self.object_name1,
                                              self.bucket_name2, self.object_name2)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info("Copy object ETag: %s", CopyETag)
        self.log.info(
            "Steps 5: compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 6: Stop and validate S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19842_ios")
        self.log.info(
            "Steps 8: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to same bucket with different object name while S3 IOs"
            " are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19843")
    @CTFailOn(error_handler)
    def test_19843(self):
        """Copy object to cross account buckets while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object to cross account buckets while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19843_ios",
                                                duration="0h4m")
        self.log.info(
            "Step 3: Create a bucket in Account1 and upload object in it.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name1, self.email_id.format(self.account_name1))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id1, s3_obj1, s3_acl_obj1, access_key1, secret_key1 = response
        status, PutETag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        self.log.info(
            "Step 4: From Account2 create a bucket. Referred as bucket2.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name2, self.email_id.format(self.account_name2))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id2, s3_obj2, s3_acl_obj2, access_key2, secret_key2 = response
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info(
            "Step 5: From Account2 on bucket2 grant Write ACL to Account1 and"
            " full control to account2.")
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 6: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Steps 7: From Account1 copy object from bucket1 to bucket2 .")
        status, response = S3_OBJ.copy_object(self.bucket_name1, self.object_name1,
                                              self.bucket_name2, self.object_name2)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 8:  compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 9: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19843_ios")
        self.log.info(
            "Steps 10: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to cross account buckets while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19844")
    @CTFailOn(error_handler)
    def test_19844(self):
        """Copy object of object size equal to 5GB while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object of object size equal to 5GB while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19844_ios",
                                                duration="0h4m")
        self.log.info(
            "Step 3: Create and upload object of size equal to 5GiB to the bucket.")
        status, PutETag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name1, self.object_name1, self.file_path, count=10, size="500M")
        self.log.info("Put object ETag: %s", PutETag)
        self.log.info(
            "Step 4: Copy object to different bucket with different object.")
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, response = S3_OBJ.copy_object(self.bucket_name1, self.object_name1,
                                              self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info("Copy object ETag: %s", CopyETag)
        self.log.info(
            "Steps 5: compare the compare ETag of source and destination object.")
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19844_ios")
        self.log.info(
            "Steps 7: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object of object size equal to 5GB while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19846")
    @CTFailOn(error_handler)
    def test_19846(self):
        """Copy object of object size greater than 5GB while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object of object size greater than 5GB while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19846_ios",
                                                duration="0h4m")
        self.log.info(
            "Step 3: Create and upload object of size greater than 5GB to the bucket..")
        status, PutETag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name1, self.object_name1, self.file_path, count=11, size="512M")
        self.log.info("Put object ETag: %s", PutETag)
        self.log.info(
            "Step 4: create second bucket.")
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Steps 5: Copy object from bucket1 to bucket2 .Check for error message.")
        try:
            status, response = S3_OBJ.copy_object(self.bucket_name1, self.object_name1,
                                                  self.bucket_name2, self.object_name2)
            assert_utils.assert_false(
                status, "copied object greater than 5GB.")
            CopyETag = response['CopyObjectResult']['ETag']
            self.log.info("Copy object ETag: %s", CopyETag)
        except CTException as error:
            self.log.info(error.message)
            assert_utils.assert_equal(
                "An error occurred (InvalidRequest) when calling the CopyObject operation:"
                " The specified copy source is larger than the maximum allowable size for a"
                " copy source: 5368709120", error.message, error)
        self.log.info("Steps 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19846_ios")
        self.log.info(
            "Steps 8: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object of object size greater than 5GB while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19847")
    @CTFailOn(error_handler)
    def test_19847(self):
        """Copy object to different account with write access on destination bucket and check
        ACL while S3 IOs are in progress"""
        self.log.info(
            "STARTED: Copy object to different account with write access on destination bucket"
            " and check ACL while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19847_ios",
                                                duration="0h4m")
        self.log.info("Step 3: Create a bucket in Account1.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name1, self.email_id.format(self.account_name1))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id1, s3_obj1, s3_acl_obj1, access_key1, secret_key1 = response
        status, PutETag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        self.log.info(
            "Step 4: From Account2 create a bucket. Referred as bucket2.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name2, self.email_id.format(self.account_name2))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id2, s3_obj2, s3_acl_obj2, access_key2, secret_key2 = response
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info("Step 5: From Account2 on bucket2 grant Write ACL to Account1 and"
                      " full control to account2")
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 6: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Steps 7: From Account1 copy object from bucket1 to bucket2 .")
        status, response = s3_obj2.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 8:  compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Step 9: Get Object ACL of the destination bucket from Account2.")
        try:
            resp = s3_acl_obj2.get_object_acl(self.bucket_name1, self.object_name1)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert_utils.assert_equal("An error occurred (AccessDenied) when calling the "
                                      "GetObjectAcl operation: Access Denied", error.message,
                                      error)
        self.log.info("Step 10: Get Object ACL of the destination bucket from Account1.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Steps 11: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19847_ios")
        self.log.info(
            "Steps 12: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to different account with write access on destination bucket"
            " and check ACL while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19848")
    @CTFailOn(error_handler)
    def test_19848(self):
        """Copy object to different account with read access on source object and check ACL
        while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object to different account with read access on source object"
                      " and check ACL while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19848_ios",
                                                duration="0h4m")
        self.log.info("Step 3: Create a bucket in Account1.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name1, self.email_id.format(self.account_name1))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id1, s3_obj1, s3_acl_obj1, access_key1, secret_key1 = response
        status, PutETag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        assert_utils.assert_true(status, PutETag)
        self.log.info("Step 4: Get the source object ACL. Capture the output .")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: From Account2 create a bucket. Referred as bucket2.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name2, self.email_id.format(self.account_name2))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id2, s3_obj2, s3_acl_obj2, access_key2, secret_key2 = response
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info("Step 6: From Account1 grant Read Access to Account2 on source object.")
        resp = s3_acl_obj1.put_object_acl(
            bucket_name=self.bucket_name1,
            object_name=self.object_name1,
            grant_read="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 7: From Account1 check the applied ACL on the source-object in above step.")
        resp = s3_acl_obj1.get_object_acl(
            bucket_name=self.bucket_name1,
            object_name=self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Steps 8: From Account1 copy object from bucket1 to bucket2 .")
        status, response = s3_obj2.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 9:  compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19848_ios")
        self.log.info(
            "Steps 13: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object to different account with read access on source object"
                      " and check ACL while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19849")
    @CTFailOn(error_handler)
    def test_19849(self):
        """Copy object to different account and check for metadata while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object to different account and check for metadata while S3"
                      " IOs are in progress")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19849_ios",
                                                duration="0h4m")
        self.log.info("Step 3: Create a bucket in Account1.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name1, self.email_id.format(self.account_name1))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id1, s3_obj1, s3_acl_obj1, access_key1, secret_key1 = response
        status, PutETag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path,
            m_key="city", m_value="Pune")
        assert_utils.assert_true(status, PutETag)
        self.log.info("Step 4: Get the source object ACL. Capture the output .")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: From Account2 create a bucket. Referred as bucket2.")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name2, self.email_id.format(self.account_name2))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id2, s3_obj2, s3_acl_obj2, access_key2, secret_key2 = response
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info("Step 6: From Account1 grant Read Access to Account2 on source object.")
        resp = s3_acl_obj1.put_object_acl(
            bucket_name=self.bucket_name1,
            object_name=self.object_name1,
            grant_write="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 7: From Account1 check the applied ACL on the source-object in above step.")
        resp = s3_acl_obj1.get_object_acl(
            bucket_name=self.bucket_name1,
            object_name=self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Steps 8: From Account1 copy object from bucket1 to bucket2 .")
        status, response = s3_obj2.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 9:  compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19849_ios")
        self.log.info(
            "Steps 13: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object to different account and check for metadata while"
                      " S3 IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19850")
    @CTFailOn(error_handler)
    def test_19850(self):
        """Copy object applying canned ACL public-read-write while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object applying canned ACL public-read-write while S3 IOs"
                      " are in progress")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19850_ios",
                                                duration="0h4m")
        self.log.info(
            "3. Create 2 buckets in same accounts and upload object to the above bucket1..")
        status, response = IAM_OBJ.create_s3iamcli_acc(
            self.account_name1, self.email_id.format(self.account_name1))
        assert_utils.assert_true(status, response)
        self.log.info(response)
        canonical_id1, s3_obj1, s3_acl_obj1, access_key1, secret_key1 = response
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        status, PutETag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        assert_utils.assert_true(status, PutETag)
        self.log.info("4. Copy object from bucket1 to bucket2 specifying canned ACL as"
                      " public-read-write.")
        status, response = s3_acl_obj1.copy_object_acl(self.bucket_name1, self.object_name1,
                                                       self.bucket_name2, self.object_name2,
                                                       acl="public-read-write")
        assert_utils.assert_true(status, response)
        CopyETag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 5:  compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("7. Get Object ACL of the destination object. Validate that ACL is having"
                      " public-read-write permission.")
        resp = s3_acl_obj1.get_object_acl(
            bucket_name=self.bucket_name2,
            object_name=self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Steps 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19850_ios")
        self.log.info(
            "Steps 13: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object applying canned ACL public-read-write while S3 IOs"
                      " are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19851")
    @CTFailOn(error_handler)
    def test_19851(self):
        """Copy object applying canned ACL bucket-owner-read while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object applying canned ACL bucket-owner-read while S3 "
                      "IOs are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19851_ios",
                                                duration="0h4m")
        self.log.info("Step 3. Create a bucket in Account1 and referred as bucket1.")
        self.log.info("Step 4. Create and upload object to the above bucket1.")
        self.log.info("Step 5. Get the source object ACL. Capture the output.")
        self.log.info("Step 6. From Account2 create a bucket. Referred as bucket2.")
        self.log.info("Step 7. From Account2 grant Write ACL to Account1 on bucket2.")
        self.log.info("Step 8. From Account2 check the applied ACL in above step.")
        self.log.info(
            "Step 9. From Account1 copy object from bucket1 to bucket2 specifying canned ACL"
            " bucket-owner-read.")
        self.log.info("Step 10. Get Object ACL of the destination object from Account1.")
        self.log.info("11. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19851_ios")
        self.log.info(
            "setup 12. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object applying canned ACL bucket-owner-read while S3 "
                      "IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19891")
    @CTFailOn(error_handler)
    def test_19891(self):
        """
        Copy object test 19891.

        Copy object applying canned ACL bucket-owner-full-control while S3 IOs are in progress.
        """
        self.log.info("STARTED: Copy object applying canned ACL bucket-owner-full-control"
                      " while S3 IOs are in progress")
        self.log.info("1. Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19891_ios",
                                                duration="0h4m")
        self.log.info("3. Create a bucket in Account1. Referred as bucket1.")
        self.log.info("4. Create and upload object to the above bucket1.")
        self.log.info("5. Get the source object ACL. Capture the output.")
        self.log.info("6. From Account2 create a bucket. Referred as bucket2.")
        self.log.info("7. From Account2 grant Write ACL to Account1 on bucket2.")
        self.log.info("8. From Account2 check the applied ACL in above step.")
        self.log.info(
            "9. From Account1 copy object from bucket1 to bucket2 specifying canned ACL "
            "bucket-owner-full-control.")
        self.log.info("10. Get Object ACL of the destination object from Account1.")
        self.log.info("11. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19891_ios")
        self.log.info("12. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object applying canned ACL bucket-owner-full-control while S3"
                      " IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19892")
    @CTFailOn(error_handler)
    def test_19892(self):
        """Copy object applying full control access while S3 IOs are in progress"""
        self.log.info(
            "STARTED: Copy object applying full control access while S3 IOs are in progress.")
        self.log.info("1. Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19892_ios",
                                                duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts.")
        self.log.info("4. Create and upload object to the above bucket1.")
        self.log.info("5. List object for the bucket1.")
        self.log.info(
            "6. Copy object from bucket1 to bucket2 specifying full control access to Account2.")
        self.log.info(
            "7. Get Object ACL of the destination object from Account1. Validate the permission.")
        self.log.info(
            "8. Get Object ACL of the destination object from Account2. Validate the permission.")
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19892_ios")
        self.log.info("10. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying full control access while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19893")
    @CTFailOn(error_handler)
    def test_19893(self):
        """Copy object applying read access while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object applying read access while S3 IOs are in progress.")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19893_ios",
                                                duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts.")
        self.log.info("4. Create and upload object to the above bucket1.")
        self.log.info("5. List object for the bucket1.")
        self.log.info("6. Copy object from bucket1 to bucket2 specifying read access to Account2.")
        self.log.info(
            "7. Get Object ACL of the destination object from Account1. Validate the permission")
        self.log.info(
            "8. Get Object ACL of the destination object from Account2. Validate the permission")
        self.log.info("9. Get/download destination object from Account2.")
        self.log.info("10. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19893_ios")
        self.log.info("11. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object applying read access while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19894")
    @CTFailOn(error_handler)
    def test_19894(self):
        """Copy object applying Read ACL access while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object applying Read ACL access while S3 IOs are in progress.")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19894_ios",
                                                duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts .")
        self.log.info("4. Create and upload object to the above bucket1 .")
        self.log.info("5. List object for the bucket1.")
        self.log.info(
            "6. Copy object from bucket1 to bucket2 specifying read acp access to Account2")
        self.log.info(
            "7. Get Object ACL of the destination object from Account1. Validate the permission")
        self.log.info(
            "8. Get Object ACL of the destination object from Account2. Validate the permission")
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19894_ios")
        self.log.info("10. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object applying Read ACL access while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19895")
    @CTFailOn(error_handler)
    def test_19895(self):
        """Copy object applying Write ACL access while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object applying Write ACL access while S3 IOs are in progress")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19895_ios",
                                                duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts .")
        self.log.info("4. Create and upload object to the above bucket1 .")
        self.log.info("5. List object for the bucket1.")
        self.log.info(
            "6. Copy object from bucket1 to bucket2 specifying write acp access to Account2")
        self.log.info(
            "7. Get Object ACL of the destination object from Account1. Validate the permission.")
        self.log.info(
            "8. Get Object ACL of the destination object from Account2. Validate the permission.")
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19895_ios")
        self.log.info("10. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object applying Write ACL access while S3 IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19896")
    @CTFailOn(error_handler)
    def test_19896(self):
        """Copy object specifying multiple ACL while S3 IOs are in progress."""
        self.log.info("STARTED: Copy object specifying multiple ACL while S3 IOs are in progress")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19896_ios",
                                                duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts .")
        self.log.info("4. Create and upload object to the above bucket1 .")
        self.log.info("5. List object for the bucket1.")
        self.log.info(
            "6. Copy object from bucket1 to bucket2 specifying read and read acp access to Account2")
        self.log.info(
            "7. Get Object ACL of the destination object from Account1. Validate the permission")
        self.log.info(
            "8. Get Object ACL of the destination object from Account2. Validate the permission")
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19896_ios")
        self.log.info("10. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object specifying multiple ACL while S3 IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19897")
    @CTFailOn(error_handler)
    def test_19897(self):
        """Copy object with no read access to source bucket while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object with no read access to source bucket while S3 IOs are"
            " in progress.")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19897_ios",
                                                duration="0h4m")
        self.log.info("3. Create a bucket in Account1 .Referred as bucket1.")
        self.log.info("4. Create and upload object to the above bucket1 .")
        self.log.info("5. Get the source object ACL. Capture the output .")
        self.log.info("6. From Account2 create a bucket. Referred as bucket2 .")
        self.log.info("7. From Account2 copy object from bucket1 to bucket2 .")
        self.log.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19897_ios")
        self.log.info("9. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object with no read access to source bucket while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19898")
    @CTFailOn(error_handler)
    def test_19898(self):
        """Copy object with no write access to destination bucket while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object with no write access to destination bucket while S3 IOs"
            " are in progress")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19898_ios",
                                                duration="0h4m")
        self.log.info("3. Create a bucket in Account1 .Referred as bucket1.")
        self.log.info("4. Create and upload object to the above bucket1 .")
        self.log.info("5. Get the source object ACL. Capture the output .")
        self.log.info("6. From Account2 create a bucket. Referred as bucket2 .")
        self.log.info("7. From Account1 copy object from bucket1 to bucket2 .")
        self.log.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19898_ios")
        self.log.info("9. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object with no write access to destination bucket while S3 IOs are"
            " in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19899")
    @CTFailOn(error_handler)
    def test_19899(self):
        """
        Copy object.

         Copy object with no access to source object and destination bucket present in different
         account having full access to the source bucket during S3 IOs.
         """
        self.log.info("STARTED: Copy object with no access to source object and destination bucket"
                      " present in different account having full access to the source bucket"
                      " during S3 IOs")
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19899_ios",
                                                duration="0h4m")
        self.log.info("3. Create a bucket in Account1 .Referred as bucket1.")
        self.log.info("4. Create and upload object to the above bucket1 .")
        self.log.info("5. Get the source object ACL. Capture the output .")
        self.log.info("6. Put bucket ACL on source bucket and grant Full control to Account2 .")
        self.log.info("7. From Account2 create a bucket. Referred as bucket2 .")
        self.log.info("8. From Account2 copy object from bucket1 to bucket2 .")
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19899_ios")
        self.log.info("10. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info("ENDED: Copy object with no access to source object and destination bucket"
                      " present in different account having full access to the source bucket"
                      " during S3 IOs")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19900")
    @CTFailOn(error_handler)
    def test_19900(self):
        """
        Copy object Test 19900.

        Copy object specifying bucket name and object under folders while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object specifying bucket name and object under folders while"
            " S3 IOs are in progress")
        fpath = "sub/sub2/sub3/sub4/sub5/sub6/sub7/sub8/sub9/"
        self.log.info("1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_19900_ios",
                                                duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts .")
        resp = S3_OBJ.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], f"Failed to create {self.bucket_name1}")
        assert_utils.assert_in(self.bucket_name2, resp[1], f"Failed to create {self.bucket_name2}")
        self.log.info(
            "4. Create object inside multiple folders and upload object to the above bucket1.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.put_object(self.bucket_name1, f"{fpath}{self.object_name1}", self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        PutTag = resp[1]["ETag"].strip('"')
        self.log.info("5. List object for the bucket1.")
        resp = S3_OBJ.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(any([self.object_name1 in obj for obj in resp[1]]),
                                 f"{self.object_name1} not present in {resp[1]}")
        self.log.info("6. Copy object from bucket1 to bucket2.")
        resp = S3_OBJ.copy_object(self.bucket_name1, f"{fpath}{self.object_name1}",
                                  self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        CopyETag1 = resp[1]['CopyObjectResult']['ETag']
        assert_utils.assert_equal(PutTag, CopyETag1, f"Failed to match object ETag")
        self.log.info(
            "7. List Objects from bucket2, Check object is present and of same size as source"
            " object.")
        resp = S3_OBJ.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name2, resp[1],
                               f"{self.object_name2} not present in {resp[1]}")
        self.log.info(
            "8. Copy object from bucket1 to bucket2 specifying folder structure for destination"
            " object.")
        resp = S3_OBJ.copy_object(self.bucket_name1, f"{fpath}{self.object_name1}",
                                  self.bucket_name2, f"{fpath}{self.object_name2}")
        assert_utils.assert_true(resp[0], resp[1])
        CopyETag2 = resp[1]['CopyObjectResult']['ETag']
        assert_utils.assert_equal(PutTag, CopyETag2, f"Failed to match object ETag")
        self.log.info(
            "9. List Objects from bucket2, Check object is present and of same size and folder"
            " structure as source object.")
        resp = S3_OBJ.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(any([self.object_name2 in obj for obj in resp[1]]),
                                 f"{self.object_name2} not present in {resp[1]}")
        self.log.info("10. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_19900_ios")
        self.log.info("11. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object specifying bucket name and object under folders while S3 IOs"
            " are in progress")
