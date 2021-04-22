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
from scripts.s3_bench import s3bench

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
        self.account_name = "acc-copyobject-{}".format(perf_counter_ns())
        self.io_bucket_name = "iobkt-copyobject-{}".format(perf_counter_ns())
        self.bucket_name = "bkt-copyobject-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-copyobject-{}".format(perf_counter_ns())
        self.object_name = "copyobject-{}".format(perf_counter_ns())
        self.object_name2 = "copyobject2-{}".format(perf_counter_ns())
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
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
        if self.parallel_ios.is_alive():
            self.parallel_ios.join()
        bucket_list = S3_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket in [
                self.bucket_name,
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
            "STARTED: Check cluster status, all services are running.")
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
        self.log.info("ENDED: Check cluster status, all services are running.")

    def s3_ios(self,
               bucket=None,
               log_file_prefix="parallel_io",
               num_clients=5,
               num_sample=20,
               obj_name_pref="loadgen_",
               obj_size="4Kb",
               duration="0h2m",
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

    def validate_paralle_execution(self, log_prifix=None):
        """Check parallel execution failure."""
        logflist = system_utils.list_dir(s3bench.LOG_DIR)
        log_path = None
        for filename in logflist:
            if filename.startswith(log_prifix):
                log_path = os.path.join(s3bench.LOG_DIR, filename)
        self.log.info("IO log path: %s", log_path)
        assert_utils.assert_is_not_none(
            log_path, f"failed to generate logs for parallel IOs log.")
        lines = open(log_path).readlines()
        resp_filtered = [
            line for line in lines if 'Errors Count:' in line and "reportFormat" not in line]
        self.log.info("'Error count' filtered list: %s", resp_filtered)
        for response in resp_filtered:
            assert_utils.assert_equal(
                int(response.split(":")[1].strip()), 0, response)
        for error in ["with error ", "panic", "status code"]:
            assert_utils.assert_not_equal(
                error, ",".join(lines), f"Parallel IOs failed.")
        # if os.path.exists(log_path):
        #     os.remove(log_path)

    def create_bucket_put_object(self,
                                 s3_test_obj=None,
                                 bucket_name=None,
                                 object_name=None,
                                 file_path=None,
                                 count=10,
                                 size="1M"):
        """Create bucket and put object to bucket and return ETag."""
        self.log.info("Create bucket and put object.")
        resp = s3_test_obj.create_bucket(bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = s3_test_obj.bucket_list()
        self.log.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(bucket_name, bktlist,
                               f"failed to create bucket {bucket_name}")
        resp = system_utils.create_file(
            fpath=file_path, count=count, b_size=size)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        put_resp = s3_test_obj.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=file_path)
        self.log.info("put object response: %s", put_resp)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        resp = s3_test_obj.object_list(bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(object_name, resp[1],
                               f"failed to put object {object_name}")

        return True, put_resp[1]["ETag"].strip('"')

    def copy_object_to_bucket(
            self,
            s3_test_obj,
            src_bucket,
            src_object,
            dest_bucket,
            dest_object):
        """Copy object to bucket and return ETag."""
        copy_resp = s3_test_obj.copy_object(
            source_bucket=src_bucket,
            source_object=src_object,
            dest_bucket=dest_bucket,
            dest_object=dest_object)
        self.log.info("copy object resp: %s", copy_resp)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        resp = s3_test_obj.object_list(dest_bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(dest_object, resp[1],
                               f"failed to copy object {dest_object}")

        return True, copy_resp[1]['CopyObjectResult']['ETag']

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
        self.parallel_ios = Process(
            target=self.s3_ios, args=(
                self.io_bucket_name, "test_19841_ios"))
        if not self.parallel_ios.is_alive():
            self.parallel_ios.start()
        self.log.info("Parallel IOs started: %s", self.parallel_ios.is_alive())
        self.log.info("Step 3: Create bucket and put object in it.")
        status, PutETag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name, self.object_name, self.file_path)
        self.log.info("Put object ETag: %s", PutETag)
        self.log.info(
            "Step 4: Copy object to same bucket with different object.")
        status, CopyETag = self.copy_object_to_bucket(
            S3_OBJ, self.bucket_name, self.object_name, self.bucket_name, self.object_name2)
        self.log.info("Copy object ETag: %s", CopyETag)
        self.log.info(
            "Steps 5: compare the compare Etag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 6: Stop S3 IOs")
        resp = S3_OBJ.object_list(self.io_bucket_name)
        self.log.info(resp)
        if self.parallel_ios.is_alive():
            self.parallel_ios.join()
        self.log.info(
            "Steps 7: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Steps 8: Validate S3 parallel IO executions.")
        self.validate_paralle_execution(log_prifix="test_19841_ios")
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
        self.parallel_ios = Process(
            target=self.s3_ios, args=(
                self.io_bucket_name, "test_19842_ios"))
        if not self.parallel_ios.is_alive():
            self.parallel_ios.start()
        self.log.info("Parallel IOs started: %s", self.parallel_ios.is_alive())
        self.log.info("Step 3: Create bucket and put object in it.")
        status, PutETag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name, self.object_name, self.file_path)
        self.log.info("Put object ETag: %s", PutETag)
        self.log.info(
            "Step 4: Copy object to different bucket with different object.")
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, CopyETag = self.copy_object_to_bucket(
            S3_OBJ, self.bucket_name, self.object_name, self.bucket_name2, self.object_name2)
        self.log.info("Copy object ETag: %s", CopyETag)
        self.log.info(
            "Steps 5: compare the compare ETag of source and destination object.")
        self.log.info("ETags: Put: %s, copy: %s", PutETag, CopyETag)
        assert_utils.assert_equal(
            PutETag,
            CopyETag,
            f"Failed to match ETag: {PutETag}, {CopyETag}")
        self.log.info("Matched ETag: %s, %s", PutETag, CopyETag)
        self.log.info("Steps 6: Stop S3 IOs")
        resp = S3_OBJ.object_list(self.io_bucket_name)
        self.log.info(resp)
        if self.parallel_ios.is_alive():
            self.parallel_ios.join()
        self.log.info(
            "Steps 7: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Steps 8: Validate S3 parallel IO executions.")
        self.validate_paralle_execution(log_prifix="test_19842_ios")
        self.log.info(
            "ENDED: Copy object to same bucket with different object name while S3 IOs"
            " are in progress.")
