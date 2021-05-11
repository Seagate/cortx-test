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
from multiprocessing import Process

import logging
import pytest
from commons import commands
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER
from config import CMN_CFG
from config import S3_CFG
from scripts.s3_bench import s3bench
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.cortxcli_test_lib import CortxCliTestLib

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
        self.cortx_test_obj = CortxCliTestLib()
        self.account_name1 = "acc1-copyobject-{}".format(perf_counter_ns())
        self.account_name2 = "acc2-copyobject-{}".format(perf_counter_ns())
        self.io_bucket_name = "iobkt1-copyobject-{}".format(perf_counter_ns())
        self.bucket_name1 = "bkt1-copyobject-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-copyobject-{}".format(perf_counter_ns())
        self.object_name1 = "obj1-copyobject-{}".format(perf_counter_ns())
        self.object_name2 = "obj2-copyobject-{}".format(perf_counter_ns())
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.file_path = os.path.join(self.test_dir_path, self.object_name1)
        self.download_path = os.path.join(
            self.test_dir_path, self.object_name2)
        status, self.response1 = self.create_s3cortxcli_acc(
            self.account_name1, "{}@seagate.com".format(
                self.account_name1), self.s3acc_passwd)
        assert_utils.assert_true(status, self.response1)
        status, self.response2 = self.create_s3cortxcli_acc(
            self.account_name2, "{}@seagate.com".format(
                self.account_name2), self.s3acc_passwd)
        assert_utils.assert_true(status, self.response2)
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
        if self.parallel_ios:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
        bucket_list = S3_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket in [
                self.bucket_name1,
                self.io_bucket_name,
                self.bucket_name2]]
        if pref_list:
            resp = S3_OBJ.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        for fpath in [self.file_path, self.download_path]:
            if system_utils.path_exists(fpath):
                system_utils.remove_file(fpath)
        for response in [self.response1, self.response2]:
            if response:
                bucket_list = response[1].bucket_list()[1]
                if bucket_list:
                    resp = response[1].delete_multiple_buckets(bucket_list)
                    assert_utils.assert_true(resp[0], resp[1])
        accounts = self.cortx_test_obj.list_accounts_cortxcli()
        all_accounts = [acc["account_name"] for acc in accounts]
        self.log.info("setup %s", all_accounts)
        for acc in [self.account_name1, self.account_name2]:
            if acc in all_accounts:
                self.cortx_test_obj.delete_account_cortxcli(
                    account_name=acc, password=self.s3acc_passwd)
                self.log.info("Deleted %s account successfully", acc)
        del self.cortx_test_obj
        self.log.info("ENDED: test teardown method.")

    def check_cluster_health(self):
        """Check the cluster health."""
        self.log.info(
            "Check cluster status, all services are running.")
        nodes = CMN_CFG["nodes"]
        self.log.info(nodes)
        for _, node in enumerate(nodes):
            health_obj = Health(hostname=node["hostname"],
                                username=node["username"],
                                password=node["password"])
            resp = health_obj.check_node_health()
            self.log.info(resp)
            assert_utils.assert_true(resp[0], resp[1])
            health_obj.disconnect()
        self.log.info("Checked cluster status, all services are running.")

    def s3_ios(self,
               bucket=None,
               log_file_prefix="parallel_io",
               duration="0h3m",
               obj_size="24Kb",
               **kwargs):
        """
        Perform io's for specific durations.

        1. Create bucket.
        2. perform io's for specified durations.
        3. Check executions successful.
        """
        kwargs.setdefault("num_clients", 5)
        kwargs.setdefault("num_sample", 20)
        kwargs.setdefault("obj_name_pref", "loadgen_")
        kwargs.setdefault("end_point", S3_CFG["s3_url"])
        self.log.info("STARTED: s3 io's operations.")
        bucket = bucket if bucket else self.io_bucket_name
        resp = S3_OBJ.create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = S3H_OBJ.get_local_keys()
        resp = s3bench.s3bench(
            access_key,
            secret_key,
            bucket=bucket,
            end_point=kwargs["end_point"],
            num_clients=kwargs["num_clients"],
            num_sample=kwargs["num_sample"],
            obj_name_pref=kwargs["obj_name_pref"],
            obj_size=obj_size,
            duration=duration,
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
            log_path, "failed to generate logs for parallel S3 IO.")
        lines = open(log_path).readlines()
        resp_filtered = [
            line for line in lines if 'Errors Count:' in line and "reportFormat" not in line]
        self.log.info("'Error count' filtered list: %s", resp_filtered)
        for response in resp_filtered:
            assert_utils.assert_equal(
                int(response.split(":")[1].strip()), 0, response)
        self.log.info("Observed no Error count in io log.")
        error_kws = ["with error ", "panic", "status code", "exit status 2"]
        for error in error_kws:
            assert_utils.assert_not_equal(
                error, ",".join(lines), f"{error} Found in S3Bench Run.")
        self.log.info("Observed no Error keyword '%s' in io log.", error_kws)
        self.log.info("S3 parallel ios log validation completed.")

    def start_stop_validate_parallel_s3ios(
            self, ios=None, log_prefix=None, duration="0h2m"):
        """Start/stop parallel s3 io's and validate io's worked successfully."""
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
                self.log.info(
                    "Parallel IOs stopped: %s",
                    not self.parallel_ios.is_alive())
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

        return True, put_resp[1]["ETag"]

    def create_s3cortxcli_acc(
            self,
            account_name: str = None,
            email_id: str = None,
            password: str = None) -> tuple:
        """
        Function will create IAM accounts with specified account name and email-id.

        :param password: account password.
        :param str account_name: Name of account to be created.
        :param str email_id: Email id for account creation.
        :return tuple: It returns multiple values such as canonical_id, access_key,
        secret_key and s3 objects which required to perform further operations.
        :return tuple
        """
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            account_name,
            email_id)
        create_account = self.cortx_test_obj.create_account_cortxcli(
            account_name, email_id, password)
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        canonical_id = create_account[1]["canonical_id"]
        self.log.info("Step Successfully created the s3iamcli account")
        s3_obj = s3_test_lib.S3TestLib(
            access_key,
            secret_key,
            endpoint_url=S3_CFG["s3_url"],
            s3_cert_path=S3_CFG["s3_cert_path"],
            region=S3_CFG["region"])
        s3_acl_obj = S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        response = (
            canonical_id,
            s3_obj,
            s3_acl_obj,
            access_key,
            secret_key)

        return True, response

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19841")
    @CTFailOn(error_handler)
    def test_19841(self):
        """
        Copy object to same bucket while S3 IOs are in progress.

        TEST-19841: Copy object to same bucket with different object name.
        TEST-16941: Copy object to same bucket and check ACL.
        TEST-17064: Copy object to same bucket and check metadata.
        """
        self.log.info(
            "STARTED: Copy object to same bucket with different object name, check ACL and metadata"
            " while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19841_ios", duration="0h4m")
        self.log.info("Step 3: Create bucket and put object in it.")
        s3_obj, s3_acl_obj = self.response1[1:3]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj, self.bucket_name1, self.object_name1, self.file_path,
            metadata={"City": "Pune", "State": "Maharashtra"})
        assert_utils.assert_true(status, put_etag)
        self.log.info("Put object ETag: %s", put_etag)
        self.log.info(
            "Step 4: Copy object to same bucket with different object.")
        status, response = s3_obj.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name1, self.object_name2)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Copy object ETag: %s", copy_etag)
        self.log.info(
            "Step 5: Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info(
            "Step 6: Get metadata of the destination object and check metadata is same"
            " as source object.")
        resp_meta1 = s3_obj.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj.object_info(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"],
                                       resp_meta2[1]["Metadata"])
        self.log.info(
            "Step 7: Get Object ACL of the destination object and Check that ACL is set"
            " to private for the user making the request.")
        resp_acl = s3_acl_obj.get_object_acl(
            self.bucket_name1, self.object_name2)
        assert_utils.assert_true(resp_acl[0], resp_acl[1])
        assert_utils.assert_equal(
            resp_acl[1]["Grants"][0]["Grantee"]["ID"],
            self.response1[0])
        assert_utils.assert_equal(
            resp_acl[1]["Grants"][0]["Permission"],
            "FULL_CONTROL")
        self.log.info("Step 8: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19841_ios")
        self.log.info(
            "Step 9: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to same bucket with different object name, check ACL and metadata"
            " while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19842")
    @CTFailOn(error_handler)
    def test_19842(self):
        """
        Copy object while S3 IOs are in progress.

        TEST-19842: Copy object to same account different bucket while S3 IOs are in progress.
        TEST-17066: Copy object to different buckets and check metadata.
        TEST-16985: Copy object to different bucket and check ACL.
        """
        self.log.info(
            "STARTED: Copy object to same account different bucket while S3 IOs"
            " are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19842_ios", duration="0h4m")
        self.log.info("Step 3: Create bucket and put object in it.")
        s3_obj, s3_acl_obj = self.response1[1:3]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj, self.bucket_name1, self.object_name1, self.file_path,
            metadata={"City": "Pune", "Country": "India"})
        assert_utils.assert_true(status, put_etag)
        self.log.info("Put object ETag: %s", put_etag)
        self.log.info(
            "Step 4: Copy object to different bucket with different object name.")
        resp = s3_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, response = s3_obj.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Copy object ETag: %s", copy_etag)
        self.log.info(
            "Step 5: Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info(
            "Step 6: Get metadata of the destination object and check metadata is same"
            " as source object.")
        resp_meta1 = s3_obj.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj.object_info(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"],
                                       resp_meta2[1]["Metadata"])
        self.log.info(
            "Step 7: Get Object ACL of the destination object and Check that ACL is set"
            " to private for the user making the request.")
        resp_acl = s3_acl_obj.get_object_acl(
            self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_acl[0], resp_acl[1])
        assert_utils.assert_equal(
            resp_acl[1]["Grants"][0]["Grantee"]["ID"],
            self.response1[0])
        assert_utils.assert_equal(
            resp_acl[1]["Grants"][0]["Permission"],
            "FULL_CONTROL")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("Step 8: Stop and validate S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19842_ios")
        self.log.info(
            "Step 9: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to same account different bucket while S3 IOs"
            " are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19843")
    @CTFailOn(error_handler)
    def test_19843(self):
        """
        Copy object while IOs are in progress.

        TEST-19843: Copy object to cross account buckets while S3 IOs are in progress.
        TEST-17067: Copy object to different account and check for metadata.
        """
        self.log.info(
            "STARTED: Copy object to cross account buckets while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19843_ios", duration="0h4m")
        self.log.info(
            "Step 3: Create a bucket in Account1 and upload object in it.")
        canonical_id1, s3_obj1 = self.response1[:2]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path,
            metadata={"Name": "Vishal", "City": "Pune", "Country": "India"})
        assert_utils.assert_true(status, put_etag)
        self.log.info(
            "Step 4: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
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
            "Step 7: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info(
            "Step 9: From Account1 Get metadata of the destination object and check"
            " for metadata is same as source object .")
        resp_meta1 = s3_obj1.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj1.object_info(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"],
                                       resp_meta2[1]["Metadata"])
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19843_ios")
        self.log.info(
            "Step 11: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to cross account buckets while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19844")
    @pytest.mark.parametrize("object_size", ["5GB", "2GB"])
    def test_19844(self, object_size):
        """
        Copy large object while IOs are in progress.

        TEST-19844: Copy object of object size equal to 5GB while S3 IOs are in progress.
        TEST-16915: Copy object of bigger size and less than 5GB while S3 IOs are in progress.
        Bug: https://jts.seagate.com/browse/EOS-16032
        """
        self.log.info(
            "STARTED: Copy object of object size %s while S3 IOs are in progress.",
            object_size)
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19844_ios", duration="0h6m")
        self.log.info(
            "Step 3: Create and upload object of size %s to the bucket.",
            object_size)
        object_size = "533M" if object_size == "5GB" else "224M"
        resp = system_utils.create_file(
            fpath=self.file_path, count=9, b_size=object_size)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.create_bucket(self.bucket_name1)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = S3_OBJ.bucket_list()
        self.log.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(self.bucket_name1, bktlist,
                               f"failed to create bucket {self.bucket_name1}")
        self.log.info("Uploading objects to bucket using awscli")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name1,
                self.object_name1))
        assert_utils.assert_true(resp[0], resp[1])
        status, objlist = S3_OBJ.object_list(self.bucket_name1)
        assert_utils.assert_true(status, objlist)
        assert_utils.assert_in(self.object_name1, objlist)
        response = S3_OBJ.list_objects_details(self.bucket_name1)
        put_etag = None
        for objl in response[1]["Contents"]:
            if objl["Key"] == self.object_name1:
                put_etag = objl["ETag"]
        self.log.info("Put object ETag: %s", put_etag)
        self.log.info(
            "Step 4: Copy object to different bucket with different object.")
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, response = S3_OBJ.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Copy object ETag: %s", copy_etag)
        self.log.info(
            "Step 5: Compare ETag of source and destination object for data Integrity.")
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("Step 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19844_ios")
        self.log.info(
            "Step 7: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object of object size %s while S3 IOs are in progress.",
            object_size)

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
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19846_ios", duration="0h6m")
        self.log.info(
            "Step 3: Create and upload object of size greater than 5GB to the bucket.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=11, b_size="512M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.create_bucket(self.bucket_name1)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = S3_OBJ.bucket_list()
        self.log.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(self.bucket_name1, bktlist,
                               f"failed to create bucket {self.bucket_name1}")
        self.log.info("Uploading objects to bucket using awscli")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name1,
                self.object_name1))
        assert_utils.assert_true(resp[0], resp[1])
        status, objlist = S3_OBJ.object_list(self.bucket_name1)
        assert_utils.assert_true(status, objlist)
        assert_utils.assert_in(self.object_name1, objlist)
        self.log.info(
            "Step 4: create second bucket.")
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Step 5: Copy object from bucket1 to bucket2 .Check for error message.")
        try:
            status, response = S3_OBJ.copy_object(
                self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
            assert_utils.assert_false(
                status, f"copied object greater than 5GB: {response}")
        except CTException as error:
            self.log.info(error.message)
            assert_utils.assert_equal(
                "An error occurred (InvalidRequest) when calling the CopyObject operation:"
                " The specified copy source is larger than the maximum allowable size for a"
                " copy source: 5368709120", error.message, error)
        self.log.info("Step 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19846_ios")
        self.log.info(
            "Step 8: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object of object size greater than 5GB while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19847")
    @CTFailOn(error_handler)
    def test_19847(self):
        """
        Copy object.

        Copy object to different account with write access on destination bucket and check
        ACL while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object to different account with write access on destination bucket"
            " and check ACL while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19847_ios", duration="0h4m")
        self.log.info("Step 3: Create a bucket in Account1.")
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        self.log.info(
            "Step 4: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info(
            "Step 5: From Account2 on bucket2 grant Write ACL to Account1 and"
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
            "Step 7: From Account1 copy object from bucket1 to bucket2 .")
        status, response = s3_obj1.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info(
            "Step 9: Get Object ACL of the destination bucket from Account2.")
        try:
            resp = s3_acl_obj2.get_object_acl(
                self.bucket_name1, self.object_name1)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the "
                "GetObjectAcl operation: Access Denied", error.message, error)
        self.log.info(
            "Step 10: Get Object ACL of the destination bucket from Account1.")
        resp = s3_acl_obj1.get_bucket_acl(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 11: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19847_ios")
        self.log.info(
            "Step 12: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to different account with write access on destination bucket"
            " and check ACL while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19848")
    @CTFailOn(error_handler)
    def test_19848(self):
        """
        Copy object.

        Copy object to different account with read access on source object and check ACL
        while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object to different account with read access on source object"
            " and check ACL while S3 IOs are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19848_ios", duration="0h4m")
        self.log.info("Step 3: Create a bucket in Account1.")
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info(
            "Step 4: Get the source object ACL. Capture the output .")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 5: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info(
            "Step 6: From Account1 grant Read Access to Account2 on source object.")
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name1,
            self.object_name1,
            grant_read="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 7: From Account1 check the applied ACL on the source-object in above step.")
        resp = s3_acl_obj1.get_object_acl(
            self.bucket_name1,
            self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 8: From Account2 copy object from bucket1 to bucket2.")
        status, response = s3_obj2.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 9: Get Object ACL of the destination object from Account1.")
        try:
            resp = s3_acl_obj1.get_object_acl(
                self.bucket_name2, self.object_name2)
            assert_utils.assert_false(resp[0], resp)
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the GetObjectAcl operation:"
                " Access Denied", error.message, error)
        self.log.info(
            "Step 10: Get Object ACL of the destination object from Account2.")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 11:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("Step 12: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19848_ios")
        self.log.info(
            "Step 14: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to different account with read access on source object"
            " and check ACL while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19849")
    @CTFailOn(error_handler)
    def test_19849(self):
        """Copy object to different account and check for metadata while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object to different account and check for metadata while S3"
            " IOs are in progress")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19849_ios", duration="0h4m")
        self.log.info("Step 3: Create a bucket in Account1.")
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path,
            metadata={"City": "Pune", "Hub": "IT"})
        assert_utils.assert_true(status, put_etag)
        self.log.info(
            "Step 4: Get the source object ACL. Capture the output .")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 5: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create bucket: {self.bucket_name2}")
        self.log.info(
            "Step 6: From Account2 grant Write ACL to Account1 on bucket2 .")
        resp = s3_acl_obj2.put_bucket_acl(
            self.bucket_name2,
            grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 7: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(
            self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 8: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info(
            "Step 9: From Account1 Get metadata of the destination object. Check for metadata"
            " is same as source object.")
        resp_meta1 = s3_obj1.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj1.object_info(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"],
                                       resp_meta2[1]["Metadata"])
        self.log.info(
            "Step 10:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 11: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19849_ios")
        self.log.info(
            "Step 12: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to different account and check for metadata while"
            " S3 IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19850")
    @CTFailOn(error_handler)
    def test_19850(self):
        """Copy object applying canned ACL public-read-write while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object applying canned ACL public-read-write while S3 IOs"
            " are in progress")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19850_ios", duration="0h4m")
        self.log.info(
            "3. Create 2 buckets in same accounts and upload object to the above bucket1.")
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj1, self.bucket_name1, self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info(
            "4. Copy object from bucket1 to bucket2 specifying canned ACL as"
            " public-read-write.")
        resp = s3_acl_obj1.copy_object_acl(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            acl="public-read-write")
        assert_utils.assert_true(resp[0], resp)
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "Step 5:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info(
            "7. Get Object ACL of the destination object. Validate that ACL is having"
            " public-read-write permission.")
        resp = s3_acl_obj1.get_object_acl(
            self.bucket_name2,
            self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19850_ios")
        self.log.info(
            "Step 13: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying canned ACL public-read-write while S3 IOs"
            " are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19851")
    @CTFailOn(error_handler)
    def test_19851(self):
        """Copy object applying canned ACL bucket-owner-read while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object applying canned ACL bucket-owner-read while S3 "
            "IOs are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19851_ios", duration="0h4m")
        self.log.info(
            "Step 3. Create a bucket in Account1 and upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        self.log.info("Step 4. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 5. From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 6. From Account2 grant Write ACL to Account1 on bucket2.")
        resp = s3_acl_obj2.put_bucket_acl(
            self.bucket_name2,
            grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Step 7. From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Step 8. From Account1 copy object from bucket1 to bucket2 specifying canned ACL"
            " bucket-owner-read.")
        resp = s3_acl_obj1.copy_object_acl(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            acl="bucket-owner-read")
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "Step 9. Get Object ACL of the destination object from Account1.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Step 10:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("11. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19851_ios")
        self.log.info(
            "setup 12. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying canned ACL bucket-owner-read while S3 "
            "IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19891")
    @CTFailOn(error_handler)
    def test_19891(self):
        """
        Copy object test 19891.

        Copy object applying canned ACL bucket-owner-full-control while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object applying canned ACL bucket-owner-full-control"
            " while S3 IOs are in progress")
        self.log.info(
            "1. Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19891_ios", duration="0h4m")
        self.log.info(
            "3. Create a bucket in Account1 and upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        self.log.info("4. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("5. From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "6. From Account2 grant Write ACL to Account1 on bucket2.")
        resp = s3_acl_obj2.put_bucket_acl(
            self.bucket_name2,
            grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp)
        self.log.info("7. From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "8. From Account1 copy object from bucket1 to bucket2 specifying canned ACL "
            "bucket-owner-full-control.")
        resp = s3_acl_obj1.copy_object_acl(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            acl="bucket-owner-full-control")
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "9. Get Object ACL of the destination object from Account1.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info(
            "Step 10:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        resp = s3_acl_obj2.put_bucket_acl(
            bucket_name=self.bucket_name2,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("11. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19891_ios")
        self.log.info(
            "12. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying canned ACL bucket-owner-full-control while S3"
            " IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19892")
    @CTFailOn(error_handler)
    def test_19892(self):
        """Copy object applying full control access while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object applying full control access while S3 IOs are in progress.")
        self.log.info(
            "1. Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19892_ios", duration="0h4m")
        self.log.info(
            "3. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        self.log.info("4. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        self.log.info(
            "5. Copy object from bucket1 to bucket2 specifying full control access to Account2.")
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        resp = s3_obj1.copy_object(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            GrantFullControl="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "6. Get Object ACL of the destination object from Account1. Validate the permission.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "7. Get Object ACL of the destination object from Account2. Validate the permission.")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19892_ios")
        self.log.info(
            "10. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying full control access while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19893")
    @CTFailOn(error_handler)
    def test_19893(self):
        """Copy object applying read access while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object applying read access while S3 IOs are in progress.")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19893_ios", duration="0h4m")
        self.log.info(
            "3. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        self.log.info("4. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        self.log.info(
            "5. Copy object from bucket1 to bucket2 specifying read access to Account2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj1.copy_object(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            GrantRead="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "6. Get Object ACL of the destination object from Account1. Validate the permission")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "7. Get Object ACL of the destination object from Account2. Validate the permission")
        try:
            resp = s3_acl_obj2.get_object_acl(
                self.bucket_name2, self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the GetObjectAcl operation: "
                "Access Denied", error.message, error)
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("9. Get/download destination object from Account2.")
        resp = s3_obj2.object_download(
            self.bucket_name2,
            self.object_name2,
            self.download_path)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_true(
            system_utils.path_exists(
                self.download_path), resp)
        self.log.info("10. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19893_ios")
        self.log.info(
            "11. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying read access while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19894")
    @CTFailOn(error_handler)
    def test_19894(self):
        """Copy object applying Read ACL access while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object applying Read ACL access while S3 IOs are in progress.")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19894_ios", duration="0h4m")
        self.log.info(
            "3. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        self.log.info("4. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        self.log.info(
            "5. Copy object from bucket1 to bucket2 specifying read acp access to Account2")
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        resp = s3_obj1.copy_object(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            GrantReadACP="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "6. Get Object ACL of the destination object from Account1. Validate the permission")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "7. Get Object ACL of the destination object from Account2. Validate the permission")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19894_ios")
        self.log.info(
            "10. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying Read ACL access while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19895")
    @CTFailOn(error_handler)
    def test_19895(self):
        """
        Copy object negative test.

        Copy object applying Write ACL access while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object applying Write ACL access while S3 IOs are in progress")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19895_ios", duration="0h4m")
        self.log.info(
            "3. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        self.log.info("4. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        self.log.info(
            "5. Copy object from bucket1 to bucket2 specifying write acp access to Account2")
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        resp = s3_obj1.copy_object(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            GrantWriteACP="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info(
            "6. Get Object ACL of the destination object from Account1. Validate the permission.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "7. Get Object ACL of the destination object from Account2. Validate the permission.")
        try:
            resp = s3_acl_obj2.get_object_acl(
                self.bucket_name2, self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the GetObjectAcl operation: "
                "Access Denied", error.message, error)
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19895_ios")
        self.log.info(
            "10. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object applying Write ACL access while S3 IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19896")
    @CTFailOn(error_handler)
    def test_19896(self):
        """
        Copy object negative test.

        Copy object specifying multiple ACL while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object specifying multiple ACL while S3 IOs are in progress")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19896_ios", duration="0h4m")
        self.log.info(
            "3. Create a 2 bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("4. From Account1 check buckets created.")
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        self.log.info(
            "5. Copy object from bucket1 to bucket2 specifying read and read acp access to "
            "Account2")
        resp = s3_obj1.copy_object(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            GrantRead="id={}".format(canonical_id2),
            GrantReadACP="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        resp = s3_obj1.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "6. Get Object ACL of the destination object from Account1. Validate the permission")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "7. Get Object ACL of the destination object from Account2. Validate the permission")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 8:  Compare ETag of source and destination object for data Integrity.")
        self.log.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        self.log.info("Matched ETag: %s, %s", put_etag, copy_etag)
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19896_ios")
        self.log.info(
            "10. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object specifying multiple ACL while S3 IOs are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19897")
    @CTFailOn(error_handler)
    def test_19897(self):
        """Copy object with no read access to source bucket while S3 IOs are in progress."""
        self.log.info(
            "STARTED: Copy object with no read access to source bucket while S3 IOs are"
            " in progress.")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19897_ios", duration="0h4m")
        self.log.info(
            "3. Create a bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        self.log.info("4. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("6. From Account2 create a bucket. Referred as bucket2.")
        s3_obj2 = self.response2[1]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("7. From Account2 copy object from bucket1 to bucket2.")
        try:
            resp = s3_obj2.copy_object(
                self.bucket_name1,
                self.object_name1,
                self.bucket_name2,
                self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
            resp = s3_obj2.object_list(self.bucket_name2)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_not_in(
                self.object_name2,
                resp[1],
                f"copied object {self.object_name2}")
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the CopyObject operation: "
                "Access Denied", error.message, error)
        self.log.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19897_ios")
        self.log.info(
            "9. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object with no read access to source bucket while S3 IOs are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19898")
    @CTFailOn(error_handler)
    def test_19898(self):
        """
        Copy object negative test.

        Copy object with no write access to destination bucket while S3 IOs are in progress.
        """
        self.log.info(
            "STARTED: Copy object with no write access to destination bucket while S3 IOs"
            " are in progress")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19898_ios", duration="0h4m")
        self.log.info(
            "3. Create a bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        self.log.info("4. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("6. From Account2 create a bucket. Referred as bucket2.")
        s3_obj2 = self.response2[1]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("7. From Account1 copy object from bucket1 to bucket2 .")
        try:
            resp = s3_obj1.copy_object(
                self.bucket_name1,
                self.object_name1,
                self.bucket_name2,
                self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
            resp = s3_obj1.object_list(self.bucket_name2)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_not_in(
                self.object_name2,
                resp[1],
                f"copied object {self.object_name2}")
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the CopyObject operation: "
                "Access Denied", error.message, error)
        self.log.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19898_ios")
        self.log.info(
            "9. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object with no write access to destination bucket while S3 IOs are"
            " in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19899")
    @CTFailOn(error_handler)
    def test_19899(self):
        """
        Copy object negative test.

        Copy object with no access to source object and destination bucket present in different
        account having full access to the source bucket during S3 IOs.
        """
        self.log.info(
            "STARTED: Copy object with no access to source object and destination bucket"
            " present in different account having full access to the source bucket"
            " during S3 IOs")
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19899_ios", duration="0h4m")
        self.log.info(
            "3. Create a bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        self.log.info("4. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "7. From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2 = self.response2[:2]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "6. Put bucket ACL on source bucket and grant Full control to Account2.")
        resp = s3_acl_obj1.put_bucket_acl(
            self.bucket_name1,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("8. From Account2 copy object from bucket1 to bucket2.")
        try:
            resp = s3_obj2.copy_object(
                self.bucket_name1,
                self.object_name1,
                self.bucket_name2,
                self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
            resp = s3_obj2.object_list(self.bucket_name2)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_not_in(
                self.object_name2,
                resp[1],
                f"copied object {self.object_name2}")
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (AccessDenied) when calling the CopyObject operation: "
                "Access Denied", error.message, error)
        resp = s3_acl_obj1.put_bucket_acl(
            bucket_name=self.bucket_name1,
            grant_full_control="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19899_ios")
        self.log.info(
            "10. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object with no access to source object and destination bucket"
            " present in different account having full access to the source bucket"
            " during S3 IOs")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-19900")
    @pytest.mark.parametrize("object_name", ["new% (1234) ::#$$^**", "cp-object"])
    def test_19900(self, object_name):
        """
        Copy object Test 19900, Test 19240.

        Copy object specifying bucket name and object under folders while S3 IOs are in progress.
        Copy object with special character in object name under folders while S3 IOs are in progress
        """
        self.log.info(
            "STARTED: Copy object specifying bucket name and object under folders while"
            " S3 IOs are in progress")
        dpath = "sub/sub2/sub3/sub4/sub5/sub6/sub7/sub8/sub9/"
        self.log.info(
            "1. Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("2. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19900_ios", duration="0h4m")
        self.log.info("3. Create 2 buckets in same accounts .")
        resp = S3_OBJ.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.bucket_list()
        assert_utils.assert_in(
            self.bucket_name1,
            resp[1],
            f"Failed to create {self.bucket_name1}")
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create {self.bucket_name2}")
        self.log.info(
            "4. Create object inside multiple folders and upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3_OBJ.put_object(
            self.bucket_name1,
            f"{dpath}{object_name}",
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]["ETag"]
        self.log.info("5. List object for the bucket1.")
        resp = S3_OBJ.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(any([object_name in obj for obj in resp[1]]),
                                 f"{object_name} not present in {resp[1]}")
        self.log.info("6. Copy object from bucket1 to bucket2.")
        resp = S3_OBJ.copy_object(
            self.bucket_name1,
            f"{dpath}{object_name}",
            self.bucket_name2,
            self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag1 = resp[1]['CopyObjectResult']['ETag']
        assert_utils.assert_equal(
            put_etag,
            copy_etag1,
            f"Failed to match object ETag: {put_etag}, {copy_etag1}")
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
        resp = S3_OBJ.copy_object(
            self.bucket_name1,
            f"{dpath}{object_name}",
            self.bucket_name2,
            f"{dpath}{self.object_name2}")
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag2 = resp[1]['CopyObjectResult']['ETag']
        assert_utils.assert_equal(
            put_etag,
            copy_etag2,
            f"Failed to match object ETag: {put_etag}, {copy_etag2}")
        self.log.info(
            "9. List Objects from bucket2, Check object is present and of same size and folder"
            " structure as source object.")
        resp = S3_OBJ.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(any([self.object_name2 in obj for obj in resp[1]]),
                                 f"{self.object_name2} not present in {resp[1]}")
        self.log.info("10. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19900_ios")
        self.log.info(
            "11. Check cluster status, all services are running after completing test")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object specifying bucket name and object under folders while S3 IOs"
            " are in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-16899")
    @CTFailOn(error_handler)
    def test_16899(self):
        """
        Copy object negative test.

        Copy object to same bucket with same object name while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Copy object to same bucket with same object name while S3 IO's"
            " are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_16899_ios", duration="0h3m")
        self.log.info("Step 3: Create bucket and put object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name1, self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info("Put object ETag: %s", put_etag)
        self.log.info(
            "Step 4: Copy object to same bucket with same name.")
        try:
            status, response = S3_OBJ.copy_object(
                self.bucket_name1, self.object_name1, self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (InvalidRequest) when calling the "
                "CopyObject operation: This copy request is illegal because "
                "it is trying to copy an object to itself without changing "
                "the object's metadata, storage class, website redirect "
                "location or encryption attributes.", error.message, error.message)
        self.log.info("Step 5: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_16899_ios")
        self.log.info(
            "Step 6: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object to same bucket with same object name while S3 IO's"
            " are in progress.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-17110")
    @CTFailOn(error_handler)
    def test_17110(self):
        """
        Copy object negative test.

        Copy object specifying bucket name and object using wildcard while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Copy object specifying bucket name and object using wildcard while"
            " S3 IO's are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_17110_ios", duration="0h3m")
        self.log.info("Step 3: Create bucket and put object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            S3_OBJ, self.bucket_name1, self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info("Put object ETag: %s", put_etag)
        self.log.info(
            "Step 4: Copy object from bucket1 to bucket2 using wildcard * for source-object.")
        try:
            status, response = S3_OBJ.copy_object(
                self.bucket_name1, "*", self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (NoSuchKey) when calling the CopyObject operation:"
                " The specified key does not exist.", error.message, error.message)
        self.log.info(
            "Step 5: Copy object from bucket1 to bucket2 using wildcard * for part of "
            "source-object name.")
        try:
            status, response = S3_OBJ.copy_object(
                self.bucket_name1, f"{self.object_name1}*", self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (NoSuchKey) when calling the CopyObject operation:"
                " The specified key does not exist.", error.message, error.message)
        self.log.info(
            "Step 6: Copy object from bucket1 to bucket2 using wildcard ? for a character of "
            "source-object name.")
        try:
            status, response = S3_OBJ.copy_object(
                self.bucket_name1, f"{self.object_name1}?", self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_equal(
                "An error occurred (NoSuchKey) when calling the CopyObject operation:"
                " The specified key does not exist.", error.message, error.message)
        self.log.info("Step 7: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_17110_ios")
        self.log.info(
            "Step 8: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info(
            "ENDED: Copy object specifying bucket name and object using wildcard while"
            " S3 IO's are in progress.")
