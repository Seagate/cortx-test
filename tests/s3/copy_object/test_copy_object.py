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

"""S3 copy object test module."""

# pylint: disable=too-many-lines

import os
import json
from time import perf_counter_ns
from datetime import timedelta
from multiprocessing import Process

import logging
import pytest
from commons import error_messages as errmsg
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils.s3_utils import assert_s3_err_msg
from config.s3 import S3_CFG
from config import CMN_CFG
from config.s3 import S3_BKT_TST as BKT_POLICY_CONF
from scripts.s3_bench import s3bench
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3 import s3_bucket_policy_test_lib
from libs.s3.s3_cmd_test_lib import S3CmdTestLib
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_common_test_lib import copy_obj_di_check
from libs.s3.s3_common_test_lib import upload_mpu_copy_obj

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class TestCopyObjects:
    """S3 copy object class."""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable-msg=too-many-statements
    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-locals

    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked test before and after yield part each test case execution.

        1. Create bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        LOGGER.info("STARTED: test setup.")
        self.s3_obj = s3_test_lib.S3TestLib()
        self.s3mp_test_obj = S3MultipartTestLib()
        self.s3_cmd_obj = S3CmdTestLib()
        LOGGER.info("Check s3 bench tool installed.")
        assert_utils.assert_true(system_utils.path_exists(s3bench.S3_BENCH_PATH),
                                 f"S3bench tool is not installed: {s3bench.S3_BENCH_PATH}")
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestS3CopyObject")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", self.test_dir_path)
        self.rest_obj = S3AccountOperations()
        self.account_list = []
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
        status, self.response1 = self.create_s3cortxiam_acc(
            self.account_name1, "{}@seagate.com".format(self.account_name1), self.s3acc_passwd)
        assert_utils.assert_true(status, self.response1)
        status, self.response2 = self.create_s3cortxiam_acc(
            self.account_name2, "{}@seagate.com".format(
                self.account_name2), self.s3acc_passwd)
        assert_utils.assert_true(status, self.response2)
        self.parallel_ios = None
        LOGGER.info("ENDED: test setup.")
        yield
        LOGGER.info("STARTED: test teardown.")
        LOGGER.info("Deleting all buckets/objects created during TC execution")
        if self.parallel_ios:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
        bucket_list = self.s3_obj.bucket_list()[1]
        pref_list = [each_bucket for each_bucket in bucket_list if each_bucket in [
                self.bucket_name1, self.io_bucket_name, self.bucket_name2]]
        if pref_list:
            resp = self.s3_obj.delete_multiple_buckets(pref_list)
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
        LOGGER.info("Account list: %s", self.account_list)
        for acc in self.account_list:
            self.rest_obj.delete_s3_account(acc)
            LOGGER.info("Deleted %s account successfully", acc)
        LOGGER.info("ENDED: test teardown.")

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
        LOGGER.info("STARTED: s3 io's operations.")
        bucket = bucket if bucket else self.io_bucket_name
        resp = self.s3_obj.create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = S3H_OBJ.get_local_keys()
        resp = s3bench.s3bench(access_key, secret_key, bucket=bucket, end_point=S3_CFG["s3_url"],
                               num_clients=kwargs["num_clients"], num_sample=kwargs["num_sample"],
                               obj_name_pref=kwargs["obj_name_pref"], obj_size=obj_size,
                               duration=duration, log_file_prefix=log_file_prefix,
                               validate_certs=S3_CFG["validate_certs"])
        LOGGER.info(resp)
        assert_utils.assert_true(os.path.exists(resp[1]), f"failed to generate log: {resp[1]}")
        LOGGER.info("ENDED: s3 io's operations.")

    def start_stop_validate_parallel_s3ios(self, ios=None, log_prefix=None, duration="0h2m"):
        """Start/stop parallel s3 io's and validate io's worked successfully."""
        if ios == "Start":
            self.parallel_ios = Process(target=self.s3_ios,
                                        args=(self.io_bucket_name, log_prefix, duration))
            if not self.parallel_ios.is_alive():
                self.parallel_ios.start()
            LOGGER.info("Parallel IOs started: %s for duration: %s",
                        self.parallel_ios.is_alive(), duration)
        if ios == "Stop":
            if self.parallel_ios.is_alive():
                resp = self.s3_obj.object_list(self.io_bucket_name)
                LOGGER.info(resp)
                self.parallel_ios.join()
                LOGGER.info("Parallel IOs stopped: %s", not self.parallel_ios.is_alive())
            if log_prefix:
                resp = system_utils.validate_s3bench_parallel_execution(s3bench.LOG_DIR, log_prefix)
                assert_utils.assert_true(resp[0], resp[1])

    @staticmethod
    def create_bucket_put_object(s3_test_obj=None, bucket_name=None, object_name=None,
                                 file_path=None, **kwargs):
        """Create bucket and put object to bucket and return ETag."""
        LOGGER.info("Create bucket and put object.")
        resp = s3_test_obj.create_bucket(bucket_name)
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = s3_test_obj.bucket_list()
        LOGGER.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(bucket_name, bktlist, f"failed to create bucket {bucket_name}")
        put_resp = s3_test_obj.put_object(bucket_name=bucket_name, object_name=object_name,
                                          file_path=file_path, **kwargs)
        LOGGER.info("put object response: %s", put_resp)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        resp = s3_test_obj.object_list(bucket_name)
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(object_name, resp[1], f"failed to put object {object_name}")

        return True, put_resp[1]["ETag"]

    def create_s3cortxiam_acc(
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
        LOGGER.info("Step : Creating account with name %s and email_id %s", account_name, email_id)
        create_account = self.rest_obj.create_s3_account(account_name, email_id, password)
        assert_utils.assert_true(create_account[0], create_account[1])
        self.account_list.append(account_name)
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        canonical_id = create_account[1]["canonical_id"]
        LOGGER.info("Step Successfully created the account")
        s3_obj = s3_test_lib.S3TestLib(access_key, secret_key, endpoint_url=S3_CFG["s3_url"],
                                       s3_cert_path=S3_CFG["s3_cert_path"], region=S3_CFG["region"])
        s3_acl_obj = S3AclTestLib(access_key=access_key, secret_key=secret_key)
        response = (canonical_id, s3_obj, s3_acl_obj, access_key, secret_key)

        return True, response

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19841")
    @CTFailOn(error_handler)
    def test_19841(self):
        """
        Copy object to same bucket while S3 IOs are in progress.

        TEST-19841: Copy object to same bucket with different object name and check acl, metadata.
        """
        LOGGER.info("STARTED: Copy object to same bucket with different object name, check ACL and "
                    "metadata while S3 IOs are in progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19841_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("Step 2: Create bucket and put object in it.")
        s3_obj, s3_acl_obj = self.response1[1:3]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path,
            metadata={"City": "Pune", "State": "Maharashtra"})
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 3: Copy object to same bucket with different object.")
        status, response = s3_obj.copy_object(self.bucket_name1, self.object_name1,
                                              self.bucket_name1, self.object_name2)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Copy object ETag: %s", copy_etag)
        LOGGER.info("Step 4: Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag,
                                  f"Failed to match ETag: {put_etag}, {copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("Step 5: Get metadata of the destination object and check metadata is same as "
                    "source object.")
        resp_meta1 = s3_obj.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj.object_info(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"], resp_meta2[1]["Metadata"])
        LOGGER.info(
            "Step 6: Get Object ACL of the destination object and Check that ACL is set"
            " to private for the user making the request.")
        resp_acl = s3_acl_obj.get_object_acl(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(resp_acl[0], resp_acl[1])
        assert_utils.assert_equal(resp_acl[1]["Grants"][0]["Grantee"]["ID"], self.response1[0])
        assert_utils.assert_equal(resp_acl[1]["Grants"][0]["Permission"], "FULL_CONTROL")
        LOGGER.info("Step 7: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19841_s3bench_ios")
        LOGGER.info("ENDED: Copy object to same bucket with different object name, check ACL and "
                    "metadata while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-19842")
    @CTFailOn(error_handler)
    def test_19842(self):
        """
        Copy object while S3 IOs are in progress.

        TEST-19842: Copy object to same account different bucket and check metadata & acl.
        """
        LOGGER.info("STARTED: Copy object to same account different bucket while S3 IOs are in "
                    "progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19842_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("Step 2: Create bucket and put object in it.")
        s3_obj, s3_acl_obj = self.response1[1:3]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(
            s3_obj, self.bucket_name1, self.object_name1, self.file_path,
            metadata={"City": "Pune", "Country": "India"})
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info(
            "Step 3: Copy object to different bucket with different object name.")
        resp = s3_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, response = s3_obj.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Copy object ETag: %s", copy_etag)
        LOGGER.info(
            "Step 4: Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        LOGGER.info(
            "Step 5: Get metadata of the destination object and check metadata is same"
            " as source object.")
        resp_meta1 = s3_obj.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj.object_info(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"],
                                       resp_meta2[1]["Metadata"])
        LOGGER.info(
            "Step 6: Get Object ACL of the destination object and Check that ACL is set"
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
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("Step 7: Stop and validate S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19842_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object to same account different bucket while S3 IOs"
            " are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-19843")
    @CTFailOn(error_handler)
    def test_19843(self):
        """
        Copy object while IOs are in progress.

        TEST-19843: Copy object to cross account buckets and check for metadata.
        """
        LOGGER.info(
            "STARTED: Copy object to cross account buckets while S3 IOs are in progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19843_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("Step 2: Create a bucket in Account1 and upload object in it.")
        canonical_id1, s3_obj1 = self.response1[:2]
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path,
            metadata={"Name": "Vishal", "City": "Pune", "Country": "India"})
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 3: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1], f"Failed to create bucket: "
                                                           "{self.bucket_name2}")
        LOGGER.info("Step 4: From Account2 on bucket2 grant Write ACL to Account1 and full control "
                    "to account2.")
        resp = s3_acl_obj2.put_bucket_multiple_permission(bucket_name=self.bucket_name2,
                                                          grant_full_control=\
                                                          "id={}".format(canonical_id2),
                                                          grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 7:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag}, "
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("Step 8: From Account1 Get metadata of the destination object and check"
                    " for metadata is same as source object .")
        resp_meta1 = s3_obj1.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj1.object_info(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"], resp_meta2[1]["Metadata"])
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19843_s3bench_ios")
        LOGGER.info("ENDED: Copy object to cross account buckets while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19844")
    @pytest.mark.parametrize("object_size", ["5GB", "2GB"])
    def test_19844(self, object_size):
        """
        Copy large object while IOs are in progress.

        Copy object of object size equal to and less than 5GB while S3 IOs are in progress.
        Bug: https://jts.seagate.com/browse/EOS-16032
        """
        LOGGER.info("STARTED: Copy object of object size %s while S3 IOs are in progress.",
                    object_size)
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19844_s3bench_ios",
                                                duration="0h3m")
        LOGGER.info("Step 2: Create and upload object of size %s to the bucket.", object_size)
        object_size = "533M" if object_size == "5GB" else "224M"
        resp = system_utils.create_file(fpath=self.file_path, count=9, b_size=object_size)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.create_bucket(self.bucket_name1)
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = self.s3_obj.bucket_list()
        LOGGER.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(self.bucket_name1, bktlist, f"failed to create bucket"
                                                           f" {self.bucket_name1}")
        LOGGER.info("Uploading objects to bucket using awscli")
        resp = self.s3_cmd_obj.object_upload_cli(self.bucket_name1, self.object_name1,
                                                 self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        status, objlist = self.s3_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(status, objlist)
        assert_utils.assert_in(self.object_name1, objlist)
        response = self.s3_obj.list_objects_details(self.bucket_name1)
        put_etag = None
        for objl in response[1]["Contents"]:
            if objl["Key"] == self.object_name1:
                put_etag = objl["ETag"]
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 3: Copy object to different bucket with different object.")
        resp = self.s3_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        status, response = self.s3_obj.copy_object(self.bucket_name1, self.object_name1,
                                                   self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Copy object ETag: %s", copy_etag)
        LOGGER.info("Step 4: Compare ETag of source and destination object for data Integrity.")
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("Step 5: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19844_s3bench_ios")
        LOGGER.info("ENDED: Copy object of object size %s while S3 IOs are in progress.",
                    object_size)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19846")
    @CTFailOn(error_handler)
    def test_19846(self):
        """Copy object of object size greater than 5GB while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object of object size greater than 5GB while S3 IOs are in "
                    "progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19846_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("Step 2: Create and upload object of size greater than 5GB to the bucket.")
        resp = system_utils.create_file(fpath=self.file_path, count=11, b_size="512M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.create_bucket(self.bucket_name1)
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp, bktlist = self.s3_obj.bucket_list()
        LOGGER.info("Bucket list: %s", bktlist)
        assert_utils.assert_in(self.bucket_name1, bktlist, f"failed to create bucket"
                                                           f" {self.bucket_name1}")
        LOGGER.info("Uploading objects to bucket using awscli")
        resp = self.s3_cmd_obj.object_upload_cli(self.bucket_name1, self.object_name1,
                                                 self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        status, objlist = self.s3_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(status, objlist)
        assert_utils.assert_in(self.object_name1, objlist)
        LOGGER.info("Step 3: create second bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Copy object from bucket1 to bucket2 .Check for error message.")
        try:
            status, response = self.s3_obj.copy_object(self.bucket_name1, self.object_name1,
                                                       self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, f"copied object greater than 5GB: {response}")
        except CTException as error:
            LOGGER.info(error.message)
            assert_s3_err_msg(errmsg.RGW_ERR_COPY_OBJ, errmsg.CORTX_ERR_COPY_OBJ,
                              CMN_CFG["s3_engine"], error)
        LOGGER.info("Step 5: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19846_s3bench_ios")
        LOGGER.info("ENDED: Copy object of object size greater than 5GB while S3 IOs are in "
                    "progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19847")
    @CTFailOn(error_handler)
    def test_19847(self):
        """
        Copy object.

        Copy object to different account with write access on destination bucket and check
        ACL while S3 IOs are in progress.
        """
        LOGGER.info("STARTED: Copy object to different account with write access on destination "
                    "bucket and check ACL while S3 IOs are in progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19847_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("Step 2: Create a bucket in Account1.")
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        LOGGER.info("Step 3: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1], f"Failed to create bucket: "
                                                           f"{self.bucket_name2}")
        LOGGER.info("Step 4: From Account2 on bucket2 grant Write ACL to Account1 and full control "
                    "to account2")
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: From Account1 copy object from bucket1 to bucket2 .")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 7:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("Step 8: Get Object ACL of the destination bucket from Account2.")
        try:
            resp = s3_acl_obj2.get_object_acl(self.bucket_name1, self.object_name1)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            LOGGER.info(error.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,error.message, error)
        LOGGER.info("Step 9: Get Object ACL of the destination bucket from Account1.")
        resp = s3_acl_obj1.get_bucket_acl(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19847_s3bench_ios")
        LOGGER.info("ENDED: Copy object to different account with write access on destination "
                    "bucket and check ACL while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19848")
    @CTFailOn(error_handler)
    def test_19848(self):
        """
        Copy object.

        Copy object to different account with read access on source object and check ACL
        while S3 IOs are in progress.
        """
        LOGGER.info("STARTED: Copy object to different account with read access on source object"
                    " and check ACL while S3 IOs are in progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19848_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("Step 2: Create a bucket in Account1.")
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 3: Get the source object ACL. Capture the output .")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1], f"Failed to create bucket:"
                                                           f" {self.bucket_name2}")
        LOGGER.info("Step 5: From Account1 grant Read Access to Account2 on source object.")
        resp = s3_acl_obj1.put_object_canned_acl(self.bucket_name1, self.object_name1,
                                                 grant_read="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: From Account1 check the applied ACL on the source-object in above "
                    "step.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: From Account2 copy object from bucket1 to bucket2.")
        status, response = s3_obj2.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 8: Get Object ACL of the destination object from Account1.")
        try:
            resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
            assert_utils.assert_false(resp[0], resp)
        except CTException as error:
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,error.message, error)
        LOGGER.info("Step 9: Get Object ACL of the destination object from Account2.")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("Step 11: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19848_s3bench_ios")
        LOGGER.info("ENDED: Copy object to different account with read access on source object"
                    " and check ACL while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-19849")
    @CTFailOn(error_handler)
    def test_19849(self):
        """Copy object to different account and check for metadata while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object to different account and check for metadata while S3"
                    " IOs are in progress")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19849_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("Step 2: Create a bucket in Account1.")
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path,
            metadata={"City": "Pune", "Hub": "IT"})
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 3: Get the source object ACL. Capture the output .")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1], f"Failed to create bucket: "
                                                           f"{self.bucket_name2}")
        LOGGER.info("Step 5: From Account2 grant Write ACL to Account1 on bucket2 .")
        resp = s3_acl_obj2.put_bucket_acl(self.bucket_name2,
                                          grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 8: From Account1 Get metadata of the destination object. Check for "
                    "metadata is same as source object.")
        resp_meta1 = s3_obj1.object_info(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp_meta1[0], resp_meta1[1])
        resp_meta2 = s3_obj1.object_info(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp_meta2[0], resp_meta2[1])
        assert_utils.assert_dict_equal(resp_meta1[1]["Metadata"],
                                       resp_meta2[1]["Metadata"])
        LOGGER.info("Step 9:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19849_s3bench_ios")
        LOGGER.info("ENDED: Copy object to different account and check for metadata while"
                    " S3 IOs are in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19850")
    @CTFailOn(error_handler)
    def test_19850(self):
        """Copy object applying canned ACL public-read-write while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object applying canned ACL public-read-write while S3 IOs"
                    " are in progress")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19850_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("2. Create 2 buckets in same accounts and upload object to the above bucket1.")
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("3. Copy object from bucket1 to bucket2 specifying canned ACL as "
                    "public-read-write.")
        resp = s3_acl_obj1.copy_object_acl(self.bucket_name1, self.object_name1,self.bucket_name2,
                                           self.object_name2, acl="public-read-write")
        assert_utils.assert_true(resp[0], resp)
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info("Step 4:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                         f" {copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("5. Get Object ACL of the destination object. Validate that ACL is having"
                    " public-read-write permission.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19850_s3bench_ios")
        LOGGER.info("ENDED: Copy object applying canned ACL public-read-write while S3 IOs"
                    " are in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-19851")
    @CTFailOn(error_handler)
    def test_19851(self):
        """Copy object applying canned ACL bucket-owner-read while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object applying canned ACL bucket-owner-read while S3 "
                    "IOs are in progress.")
        LOGGER.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19851_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("Step 2. Create a bucket in Account1 and upload object to the above bucket1.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                       self.object_name1, self.file_path)
        LOGGER.info("Step 4. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3. From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4. From Account2 grant Write ACL to Account1 on bucket2.")
        resp = s3_acl_obj2.put_bucket_acl(self.bucket_name2,
                                          grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5. From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6. From Account1 copy object from bucket1 to bucket2 specifying canned "
                    "ACL bucket-owner-read.")
        resp = s3_acl_obj1.copy_object_acl(self.bucket_name1, self.object_name1, self.bucket_name2,
                                           self.object_name2, acl="bucket-owner-read")
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info("Step 7. Get Object ACL of the destination object from Account1.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f" {copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19851_s3bench_ios")
        LOGGER.info("ENDED: Copy object applying canned ACL bucket-owner-read while S3 "
                    "IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.regression
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19891")
    @CTFailOn(error_handler)
    def test_19891(self):
        """
        Copy object test 19891.

        Copy object applying canned ACL bucket-owner-full-control while S3 IOs are in progress.
        """
        LOGGER.info("STARTED: Copy object applying canned ACL bucket-owner-full-control"
                    " while S3 IOs are in progress")
        LOGGER.info("1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19891_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("2. Create a bucket in Account1 and upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                       self.object_name1, self.file_path)
        LOGGER.info("3. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("4. From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("4. From Account2 grant Write ACL to Account1 on bucket2.")
        resp = s3_acl_obj2.put_bucket_acl(self.bucket_name2,
                                          grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("5. From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("6. From Account1 copy object from bucket1 to bucket2 specifying canned ACL "
                    "bucket-owner-full-control.")
        resp = s3_acl_obj1.copy_object_acl(self.bucket_name1, self.object_name1, self.bucket_name2,
                                           self.object_name2, acl="bucket-owner-full-control")
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info("7. Get Object ACL of the destination object from Account1.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag,
                                  f"Failed to match ETag: {put_etag}, {copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        resp = s3_acl_obj2.put_bucket_acl(bucket_name=self.bucket_name2,
                                          grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19891_s3bench_ios")
        LOGGER.info("ENDED: Copy object applying canned ACL bucket-owner-full-control while S3"
                    " IOs are in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19892")
    @CTFailOn(error_handler)
    def test_19892(self):
        """Copy object applying full control access while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object applying full control access while S3 IOs are in "
                    "progress.")
        LOGGER.info("1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19892_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("2. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                       self.object_name1, self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        LOGGER.info("3. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        LOGGER.info("4. Copy object from bucket1 to bucket2 specifying full control access to "
                    "Account2.")
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        resp = s3_obj1.copy_object(self.bucket_name1, self.object_name1, self.bucket_name2,
                                   self.object_name2,
                                   GrantFullControl="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info("5. Get Object ACL of the destination object from Account1. Validate the "
                    "permission.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("6. Get Object ACL of the destination object from Account2. Validate the "
                    "permission.")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19892_s3bench_ios")
        LOGGER.info("ENDED: Copy object applying full control access while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19893")
    @CTFailOn(error_handler)
    def test_19893(self):
        """Copy object applying read access while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object applying read access while S3 IOs are in progress.")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19893_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("2. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                       self.object_name1, self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        LOGGER.info("3. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        LOGGER.info("4. Copy object from bucket1 to bucket2 specifying read access to Account2.")
        canonical_id2, s3_obj2, s3_acl_obj2 = self.response2[:3]
        resp = s3_obj1.copy_object(self.bucket_name1, self.object_name1, self.bucket_name2,
                                   self.object_name2, GrantRead="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info("5. Get Object ACL of the destination object from Account1. Validate the "
                    "permission")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("6. Get Object ACL of the destination object from Account2. Validate the "
                    "permission")
        try:
            resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,error.message, error)
        LOGGER.info("Step 7:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("8. Get/download destination object from Account2.")
        resp = s3_obj2.object_download(self.bucket_name2, self.object_name2, self.download_path)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_true(system_utils.path_exists(self.download_path), resp)
        LOGGER.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19893_s3bench_ios")
        LOGGER.info("ENDED: Copy object applying read access while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19894")
    @CTFailOn(error_handler)
    def test_19894(self):
        """Copy object applying Read ACL access while S3 IOs are in progress."""
        LOGGER.info("STARTED: Copy object applying Read ACL access while S3 IOs are in progress.")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-19894_s3bench_ios",
                                                duration="0h2m")
        LOGGER.info("2. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                       self.object_name1, self.file_path)
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        LOGGER.info("3. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        LOGGER.info("4. Copy object from bucket1 to bucket2 specifying read acp access to Account2")
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        resp = s3_obj1.copy_object(self.bucket_name1, self.object_name1, self.bucket_name2,
                                   self.object_name2, GrantReadACP="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info("5. Get Object ACL of the destination object from Account1. Validate the "
                    "permission")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("6. Get Object ACL of the destination object from Account2. Validate the "
                    "permission")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match ETag: {put_etag},"
                                                       f"{copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-19894_s3bench_ios")
        LOGGER.info("ENDED: Copy object applying Read ACL access while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.regression
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19895")
    @CTFailOn(error_handler)
    def test_19895(self):
        """
        Copy object negative test.

        Copy object applying Write ACL access while S3 IOs are in progress.
        """
        LOGGER.info(
            "STARTED: Copy object applying Write ACL access while S3 IOs are in progress")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-19895_s3bench_ios", duration="0h2m")
        LOGGER.info(
            "2. Create 2 buckets in same accounts upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
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
        LOGGER.info("4. List object for the bucket1.")
        resp = s3_obj1.object_list(self.bucket_name1)
        assert_utils.assert_in(self.object_name1, resp[1], resp)
        LOGGER.info(
            "3. Copy object from bucket1 to bucket2 specifying write acp access to Account2")
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        resp = s3_obj1.copy_object(
            self.bucket_name1,
            self.object_name1,
            self.bucket_name2,
            self.object_name2,
            GrantWriteACP="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        LOGGER.info(
            "4. Get Object ACL of the destination object from Account1. Validate the permission.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "5. Get Object ACL of the destination object from Account2. Validate the permission.")
        try:
            resp = s3_acl_obj2.get_object_acl(
                self.bucket_name2, self.object_name2)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,error.message, error)
        LOGGER.info(
            "Step 6:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("7. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19895_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object applying Write ACL access while S3 IOs are in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19896")
    @CTFailOn(error_handler)
    def test_19896(self):
        """
        Copy object negative test.

        Copy object specifying multiple ACL while S3 IOs are in progress.
        """
        LOGGER.info(
            "STARTED: Copy object specifying multiple ACL while S3 IOs are in progress")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-19896_s3bench_ios", duration="0h2m")
        LOGGER.info(
            "2. Create a 2 bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        resp, put_etag = self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        resp = s3_obj1.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("3. From Account1 check buckets created.")
        resp = s3_obj1.bucket_list()
        assert_utils.assert_in(self.bucket_name1, resp[1], resp)
        assert_utils.assert_in(self.bucket_name2, resp[1], resp)
        canonical_id2, s3_acl_obj2 = self.response2[0], self.response2[2]
        LOGGER.info(
            "4. Copy object from bucket1 to bucket2 specifying read and read acp access to "
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
        LOGGER.info(
            "5. Get Object ACL of the destination object from Account1. Validate the permission")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "6. Get Object ACL of the destination object from Account2. Validate the permission")
        resp = s3_acl_obj2.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 7:  Compare ETag of source and destination object for data Integrity.")
        LOGGER.info("ETags: Put: %s, copy: %s", put_etag, copy_etag)
        assert_utils.assert_equal(
            put_etag,
            copy_etag,
            f"Failed to match ETag: {put_etag}, {copy_etag}")
        LOGGER.info("Matched ETag: %s, %s", put_etag, copy_etag)
        LOGGER.info("8. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19896_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object specifying multiple ACL while S3 IOs are in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19897")
    @CTFailOn(error_handler)
    def test_19897(self):
        """Copy object with no read access to source bucket while S3 IOs are in progress."""
        LOGGER.info(
            "STARTED: Copy object with no read access to source bucket while S3 IOs are"
            " in progress.")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-19897_s3bench_ios", duration="0h2m")
        LOGGER.info(
            "2. Create a bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        LOGGER.info("3. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("4. From Account2 create a bucket. Referred as bucket2.")
        s3_obj2 = self.response2[1]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("5. From Account2 copy object from bucket1 to bucket2.")
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
            assert_s3_err_msg(errmsg.RGW_ERR_GET_OBJ_ACCESS,
                              errmsg.CORTX_ERR_GET_OBJ_ACCESS,
                              CMN_CFG["s3_engine"], error)
        LOGGER.info("6. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19897_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object with no read access to source bucket while S3 IOs are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19898")
    @CTFailOn(error_handler)
    def test_19898(self):
        """
        Copy object negative test.

        Copy object with no write access to destination bucket while S3 IOs are in progress.
        """
        LOGGER.info(
            "STARTED: Copy object with no write access to destination bucket while S3 IOs"
            " are in progress")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-19898_s3bench_ios", duration="0h1m")
        LOGGER.info(
            "2. Create a bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        s3_obj1, s3_acl_obj1 = self.response1[1:3]
        self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        LOGGER.info("3. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("4. From Account2 create a bucket. Referred as bucket2.")
        s3_obj2 = self.response2[1]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("5. From Account1 copy object from bucket1 to bucket2 .")
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
            assert_s3_err_msg(errmsg.RGW_ERR_GET_OBJ_ACCESS,
                              errmsg.CORTX_ERR_GET_OBJ_ACCESS,
                              CMN_CFG["s3_engine"], error)
        LOGGER.info("6. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19898_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object with no write access to destination bucket while S3 IOs are"
            " in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-19899")
    @CTFailOn(error_handler)
    def test_19899(self):
        """
        Copy object negative test.

        Copy object with no access to source object and destination bucket present in different
        account having full access to the source bucket during S3 IOs.
        """
        LOGGER.info(
            "STARTED: Copy object with no access to source object and destination bucket"
            " present in different account having full access to the source bucket"
            " during S3 IOs")
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-19899_s3bench_ios", duration="0h1m")
        LOGGER.info(
            "2. Create a bucket in Account1 and upload object in it.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        self.create_bucket_put_object(
            s3_obj1,
            self.bucket_name1,
            self.object_name1,
            self.file_path)
        LOGGER.info("3. Get the source object ACL. Capture the output.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "4. From Account2 create a bucket. Referred as bucket2.")
        canonical_id2, s3_obj2 = self.response2[:2]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "5. Put bucket ACL on source bucket and grant Full control to Account2.")
        resp = s3_acl_obj1.put_bucket_acl(
            self.bucket_name1,
            grant_full_control="id={}".format(canonical_id2))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("6. From Account2 copy object from bucket1 to bucket2.")
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
            assert_s3_err_msg(errmsg.RGW_ERR_GET_OBJ_ACCESS,
                              errmsg.CORTX_ERR_GET_OBJ_ACCESS,
                              CMN_CFG["s3_engine"], error)
        resp = s3_acl_obj1.put_bucket_acl(
            bucket_name=self.bucket_name1,
            grant_full_control="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("7. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19899_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object with no access to source object and destination bucket"
            " present in different account having full access to the source bucket"
            " during S3 IOs")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-19900")
    @pytest.mark.parametrize("object_name", ["new% (1234) ::#$$^**", "cp-object"])
    def test_19900(self, object_name):
        """
        Copy object while S3 IOs are in progress.

        Copy object specifying bucket name and object under folders with special character
        or string in object name.
        """
        LOGGER.info(
            "STARTED: Copy object specifying bucket name and object under folders while"
            " S3 IOs are in progress")
        dpath = "sub/sub2/sub3/sub4/sub5/sub6/sub7/sub8/sub9/"
        LOGGER.info("1. Start S3 IO")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-19900_s3bench_ios", duration="0h2m")
        LOGGER.info("2. Create 2 buckets in same accounts .")
        resp = self.s3_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.bucket_list()
        assert_utils.assert_in(
            self.bucket_name1,
            resp[1],
            f"Failed to create {self.bucket_name1}")
        assert_utils.assert_in(
            self.bucket_name2,
            resp[1],
            f"Failed to create {self.bucket_name2}")
        LOGGER.info(
            "3. Create object inside multiple folders and upload object to the above bucket1.")
        resp = system_utils.create_file(
            fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.put_object(
            self.bucket_name1,
            f"{dpath}{object_name}",
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]["ETag"]
        LOGGER.info("4. List object for the bucket1.")
        resp = self.s3_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(any(object_name in obj for obj in resp[1]),
                                 f"{object_name} not present in {resp[1]}")
        LOGGER.info("5. Copy object from bucket1 to bucket2.")
        resp = self.s3_obj.copy_object(
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
        LOGGER.info(
            "6. List Objects from bucket2, Check object is present and of same size as source"
            " object.")
        resp = self.s3_obj.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name2, resp[1],
                               f"{self.object_name2} not present in {resp[1]}")
        LOGGER.info(
            "7. Copy object from bucket1 to bucket2 specifying folder structure for destination"
            " object.")
        resp = self.s3_obj.copy_object(
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
        LOGGER.info(
            "8. List Objects from bucket2, Check object is present and of same size and folder"
            " structure as source object.")
        resp = self.s3_obj.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(any(self.object_name2 in obj for obj in resp[1]),
                                 f"{self.object_name2} not present in {resp[1]}")
        LOGGER.info("9. Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-19900_s3bench_ios")
        LOGGER.info(
            "ENDED: Copy object specifying bucket name and object under folders while S3 IOs"
            " are in progress")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-16899")
    @CTFailOn(error_handler)
    def test_16899(self):
        """
        Copy object negative test.

        Copy object to same bucket with same object name while S3 IO's are in progress.
        """
        LOGGER.info("STARTED: Copy object to same bucket with same object name while S3 IO's are in"
                    " progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-16899_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("Step 2: Create bucket and put object in it.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 3: Copy object to same bucket with same name.")
        try:
            status, response = self.s3_obj.copy_object(self.bucket_name1, self.object_name1,
                                                       self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_s3_err_msg(errmsg.RGW_ERR_COPY_OBJ_METADATA, errmsg.CORTX_ERR_COPY_OBJ_METADATA,
                              CMN_CFG["s3_engine"], error)
        LOGGER.info("Step 4: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-16899_s3bench_ios")
        LOGGER.info("ENDED: Copy object to same bucket with same object name while S3 IO's are in "
                    "progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-17110")
    @CTFailOn(error_handler)
    def test_17110(self):
        """
        Copy object negative test.

        Copy object specifying bucket name and object using wildcard while S3 IO's are in progress.
        """
        LOGGER.info("STARTED: Copy object specifying bucket name and object using wildcard while"
                    " S3 IO's are in progress.")
        LOGGER.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="TEST-17110_s3bench_ios",
                                                duration="0h1m")
        LOGGER.info("Step 2: Create bucket and put object in it.")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 3: Copy object to same bucket using wildcard * for source-object.")
        try:
            status, response = self.s3_obj.copy_object(self.bucket_name1, "*", self.bucket_name1,
                                                       self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_in(errmsg.NO_SUCH_KEY_ERR, error.message, error)
        LOGGER.info("Step 4: Copy object from bucket1 to bucket2 using wildcard * for part of "
                    "source-object name.")
        try:
            status, response = self.s3_obj.copy_object(self.bucket_name1, f"{self.object_name1}*",
                                                       self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_in(errmsg.NO_SUCH_KEY_ERR, error.message, error)
        LOGGER.info("Step 5: Copy object from bucket1 to bucket2 using wildcard ? for a character "
                    "of source-object name.")
        try:
            status, response = self.s3_obj.copy_object(self.bucket_name1, f"{self.object_name1}?",
                                                       self.bucket_name1, self.object_name1)
            assert_utils.assert_false(status, response)
        except CTException as error:
            assert_utils.assert_in(errmsg.NO_SUCH_KEY_ERR, error.message, error)
        LOGGER.info("Step 6: Stop and validate parallel S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-17110_s3bench_ios")
        LOGGER.info("ENDED: Copy object specifying bucket name and object using wildcard while"
                    " S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-22283")
    @CTFailOn(error_handler)
    def test_22283(self):
        """Use bucket policy to allow copy object to another account."""
        LOGGER.info("STARTED: Use bucket policy to allow copy object to another account.")
        bucket_policy = BKT_POLICY_CONF["test_22283"]["bucket_policy"]
        LOGGER.info("Step 1: Create a bucket in Account1. Create, upload & check object uploaded "
                    "to the above bucket.")
        canonical_id1, s3_obj1 = self.response1[:2]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 2: From Account2 create a bucket and check bucket got created.")
        s3_obj2 = self.response2[1]
        access_key2, secret_key2 = self.response2[-2:]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1],
                               f"Failed to create bucket: {self.bucket_name2}")
        LOGGER.info("Step 3: From Account1 copy object from bucket1 to bucket2.")
        try:
            status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                                   self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, response)
        except CTException as err:
            LOGGER.error(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("Step 4: Using bucket policy Allow PutObject access to Account1 on "
                    "bucket2 of Account2.")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id1))
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name2)
        bucket_policy = json.dumps(bucket_policy)
        s3_policy_usr_obj2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(access_key=access_key2,
                                                                             secret_key=secret_key2)
        resp = s3_policy_usr_obj2.put_bucket_policy(self.bucket_name2, bucket_policy)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy, resp[1])
        LOGGER.info("Step 6: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 7: From Account2 List Objects from bucket2. Check object is present "
                    "and of same size as source object.")
        status, response = s3_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(status, response)
        assert_utils.assert_in(self.object_name2, response,
                               f"Failed to copy object {self.object_name2}")
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match put etag: '{put_etag}' "
                                  f"with copy etag: {copy_etag}")
        LOGGER.info("ENDED: Use bucket policy to allow copy object to another account.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-22287")
    @CTFailOn(error_handler)
    def test_22287(self):
        """Use bucket policy to deny copy object to another account and allow through ACLs."""
        LOGGER.info("STARTED: Use bucket policy to deny copy object to another account and "
                    "allow through ACLs.")
        bucket_policy = BKT_POLICY_CONF["test_22287"]["bucket_policy"]
        LOGGER.info("Step 1: Create a bucket in Account1. Create, upload & check object uploaded "
                    "to the above bucket.")
        canonical_id1, s3_obj1 = self.response1[:2]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 2: From Account2 create a bucket and check bucket got created.")
        canonical_id2, s3_obj2, s3_acl_obj2, access_key2, secret_key2 = self.response2
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1],
                               f"Failed to create bucket: {self.bucket_name2}")
        LOGGER.info("Step 3: From Account1 copy object from bucket1 to bucket2.")
        try:
            status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                                   self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, response)
        except CTException as err:
            LOGGER.error(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("Step 4: From Account2 on bucket2 grant Write ACL to Account1 and full control "
                    "to account2.")
        resp = s3_acl_obj2.put_bucket_multiple_permission(bucket_name=self.bucket_name2,
                                                          grant_full_control=\
                                                          "id={}".format(canonical_id2),
                                                          grant_write="id={}".format(canonical_id1))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: From Account2 check the applied ACL in above step.")
        resp = s3_acl_obj2.get_bucket_acl(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(
            self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 7: From Account2 List Objects from bucket2 .Check object is present and"
                    " of same size as source object.")
        status, response = s3_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(status, response)
        assert_utils.assert_in(self.object_name2, response,
                               f"Failed to copy object {self.object_name2}")
        assert_utils.assert_equal(put_etag, copy_etag,
                                  f"Failed to match put etag: '{put_etag}' with "
                                  f"copy etag: {copy_etag}")
        LOGGER.info("Step 8: Using bucket policy Deny PutObject access to Account1 on"
                    " bucket2 of Account2.")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id1))
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name2)
        bucket_policy = json.dumps(bucket_policy)
        s3_policy_usr_obj2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key2, secret_key=secret_key2)
        resp = s3_policy_usr_obj2.put_bucket_policy(
            self.bucket_name2, bucket_policy)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy, resp[1])
        LOGGER.info("Step 10: From Account1 copy object from bucket1 to bucket2.")
        try:
            status, response = s3_obj1.copy_object(
                self.bucket_name1, self.object_name1, self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, response)
        except CTException as err:
            LOGGER.error(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("ENDED: Use bucket policy to deny copy object to another account and "
                    "allow through ACLs.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-22292")
    @CTFailOn(error_handler)
    def test_22292(self):
        """Use bucket policy to allow copy object with object contain tagging."""
        bucket_policy1 = BKT_POLICY_CONF["test_22283"]["bucket_policy"]
        bucket_policy2 = BKT_POLICY_CONF["test_22292"]["bucket_policy"]
        LOGGER.info("Step 1: Create a bucket in Account1. Create, upload & check object uploaded"
                    " to the above bucket.")
        canonical_id1, s3_obj1 = self.response1[:2]
        access_key1, secret_key1 = self.response1[-2:]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 2: From Account2 create a bucket and check bucket got created.")
        s3_obj2 = self.response2[1]
        access_key2, secret_key2 = self.response2[-2:]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2,resp[1],
                               f"Failed to create bucket: {self.bucket_name2}")
        LOGGER.info("Step 3: From Account1 copy object from bucket1 to bucket2.")
        try:
            status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                                   self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, response)
        except CTException as err:
            LOGGER.error(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("Step 4: Using bucket policy Allow PutObject access to Account1 on "
                    "bucket2 of Account2.")
        bucket_policy1['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy1['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id1))
        bucket_policy1['Statement'][0]['Resource'] = bucket_policy1['Statement'][0][
            'Resource'].format(self.bucket_name2)
        s3_policy_usr_obj2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(access_key=access_key2,
                                                                             secret_key=secret_key2)
        bucket_policy1 = json.dumps(bucket_policy1)
        resp = s3_policy_usr_obj2.put_bucket_policy(self.bucket_name2, bucket_policy1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy1, resp[1])
        LOGGER.info("Step 6: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 7: From Account2 List Objects from bucket2. Check object is present and "
                    "of same size as source object.")
        status, response = s3_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(status, response)
        assert_utils.assert_in(self.object_name2, response,
                               f"Failed to copy object {self.object_name2}")
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match put etag: '{put_etag}' "
                                  f"with copy etag: {copy_etag}")
        LOGGER.info("Step 8: Put object tagging to the object1 of Account1 .")
        s3_tagging_usr_obj1 = S3TaggingTestLib(access_key=access_key1, secret_key=secret_key1)
        resp = s3_tagging_usr_obj1.set_object_tag(self.bucket_name1, self.object_name1,
                                                  key="designation", value="confidential")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Get Object Tagging and check the tags are added .")
        resp = s3_tagging_usr_obj1.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][0]["Key"], f"designation{0}", resp[1])
        assert_utils.assert_equal(resp[1][0]["Value"], f"confidential{0}", resp[1])
        LOGGER.info("Step 10: From Account1 copy object from bucket1 to bucket2.")
        try:
            status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                                   self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, response)
        except CTException as err:
            LOGGER.error(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("Step 11: Using bucket policy Allow PutObject and PutObjectTagging access to "
                    "Account1 on bucket2 of Account2.")
        bucket_policy2['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy2['Statement'][0]['Principal']['CanonicalUser'].format(str(canonical_id1))
        bucket_policy2['Statement'][0]['Resource'] = \
            bucket_policy2['Statement'][0]['Resource'].format(self.bucket_name2)
        bucket_policy2 = json.dumps(bucket_policy2)
        resp = s3_policy_usr_obj2.put_bucket_policy(self.bucket_name2, bucket_policy2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 12: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy2, resp[1])
        LOGGER.info("Step 13: From Account1 copy object from bucket1 to bucket2 .")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 14: From Account2 List Objects from bucket2. Check object is present and"
                    " of same size as source object.")
        status, response = s3_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(status, response)
        assert_utils.assert_in(self.object_name2, response,
                               f"Failed to copy object {self.object_name2}")
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match put etag: '{put_etag}' "
                                  f"with copy etag: {copy_etag}")
        LOGGER.info("ENDED: Use bucket policy to allow copy object with object contain tagging.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-22299")
    @CTFailOn(error_handler)
    def test_22299(self):
        """Use bucket policy to validate copy object with applied ACL."""
        LOGGER.info("STARTED: Use bucket policy to validate copy object with applied ACL.")
        bucket_policy1 = BKT_POLICY_CONF["test_22283"]["bucket_policy"]
        bucket_policy2 = BKT_POLICY_CONF["test_22299"]["bucket_policy_1"]
        bucket_policy3 = BKT_POLICY_CONF["test_22299"]["bucket_policy_2"]
        LOGGER.info("Step 1: Create a bucket in Account1. Create, upload & check object "
                    "uploaded to the above bucket.")
        canonical_id1, s3_obj1, s3_acl_obj1 = self.response1[:3]
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(s3_obj1, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        LOGGER.info("Put object ETag: %s", put_etag)
        LOGGER.info("Step 2: From Account2 create a bucket and check bucket got created.")
        s3_obj2 = self.response2[1]
        access_key2, secret_key2 = self.response2[-2:]
        resp = s3_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj2.bucket_list()
        assert_utils.assert_in(self.bucket_name2, resp[1],
                               f"Failed to create bucket: {self.bucket_name2}")
        LOGGER.info("Step 3: From Account1 copy object from bucket1 to bucket2.")
        try:
            status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                                   self.bucket_name2, self.object_name2)
            assert_utils.assert_false(status, response)
        except CTException as err:
            LOGGER.error(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("Step 4: Using bucket policy Allow PutObject access to Account1 on "
                    "bucket2 of Account2.")
        bucket_policy1['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy1['Statement'][0]['Principal']['CanonicalUser'].format(str(canonical_id1))
        bucket_policy1['Statement'][0]['Resource'] = bucket_policy1['Statement'][0][
            'Resource'].format(self.bucket_name2)
        bucket_policy1 = json.dumps(bucket_policy1)
        s3_policy_usr_obj2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(access_key=access_key2,
                                                                             secret_key=secret_key2)
        resp = s3_policy_usr_obj2.put_bucket_policy(self.bucket_name2, bucket_policy1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy1, resp[1])
        LOGGER.info("Step 6: From Account1 copy object from bucket1 to bucket2.")
        status, response = s3_obj1.copy_object(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        LOGGER.info("Step 7: From Account2 List Objects from bucket2. Check object is present"
                    " and of same size as source object.")
        status, response = s3_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(status, response)
        assert_utils.assert_in(self.object_name2, response,
                               f"Failed to copy object {self.object_name2}")
        assert_utils.assert_equal(put_etag, copy_etag, f"Failed to match put etag: '{put_etag}' "
                                  f"with copy etag: {copy_etag}")
        LOGGER.info("Step 8: Using bucket policy Allow PutObject and PutObjectAcl access "
                    "to Account1 on bucket2 of Account2.")
        bucket_policy2['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy2['Statement'][0]['Principal']['CanonicalUser'].format(str(canonical_id1))
        bucket_policy2['Statement'][0]['Resource'] = bucket_policy2['Statement'][0][
            'Resource'].format(self.bucket_name2)
        bucket_policy2['Statement'][1]['Principal']['CanonicalUser'] = \
            bucket_policy2['Statement'][1]['Principal']['CanonicalUser'].format(str(canonical_id1))
        bucket_policy2['Statement'][1]['Resource'] = bucket_policy2['Statement'][1][
            'Resource'].format(self.bucket_name2)
        bucket_policy2 = json.dumps(bucket_policy2)
        resp = s3_policy_usr_obj2.put_bucket_policy(self.bucket_name2, bucket_policy2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy2, resp[1])
        LOGGER.info("Step 10: From Account1 copy object from bucket1 to bucket2 with applying "
                    "ACL's .")
        resp = s3_acl_obj1.copy_object_acl(self.bucket_name1, self.object_name1, self.bucket_name2,
                                           self.object_name2, acl="bucket-owner-full-control")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 11: Get bucket ACLs and check the ACL's got added.")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 12: Using bucket policy Allow PutObject and Deny PutObjectAcl access "
                    "to Account1 on bucket2 of Account2.")
        bucket_policy3['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy3['Statement'][0]['Principal']['CanonicalUser'].format(str(canonical_id1))
        bucket_policy3['Statement'][0]['Resource'] = bucket_policy3['Statement'][0][
            'Resource'].format(self.bucket_name2)
        bucket_policy3['Statement'][1]['Principal']['CanonicalUser'] = \
            bucket_policy3['Statement'][1]['Principal']['CanonicalUser'].format(str(canonical_id1))
        bucket_policy3['Statement'][1]['Resource'] = bucket_policy3['Statement'][1][
            'Resource'].format(self.bucket_name2)
        bucket_policy3 = json.dumps(bucket_policy3)
        resp = s3_policy_usr_obj2.put_bucket_policy(self.bucket_name2, bucket_policy3)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 13: From Account2 check the applied Bucket Policy in above step.")
        resp = s3_policy_usr_obj2.get_bucket_policy(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["Policy"], bucket_policy3, resp[1])
        LOGGER.info("Step 14: From Account1 copy object from bucket1 to bucket2 along with applying"
                    " ACL's.")
        try:
            resp = s3_acl_obj1.copy_object_acl(self.bucket_name1, self.object_name1,
                                               self.bucket_name2, self.object_name2,
                                               acl="bucket-owner-full-control")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as err:
            LOGGER.info(err.message)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY,err.message, err)
        LOGGER.info("ENDED: Use bucket policy to validate copy object with applied ACL.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44750")
    @CTFailOn(error_handler)
    def test_44750(self):
        """
        Copy object Conditional params: All true for simple object copy"""
        LOGGER.info("STARTED: Copy simple object with all conditional headers as true")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        obj_list = []
        LOGGER.info("Step 2: Copy object to different bucket")
        obj_list.append(self.object_name2)
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2,self.object_name2)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im", is_expect_err=False, is_match=etag)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_im", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_im")
        LOGGER.info("Step 4: Copy object to different bucket with condition"
                    "x-amz-copy-source-if-none-match (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inm", is_expect_err=False, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_inm", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_inm")
        LOGGER.info("Step 5: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-modified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_ims", is_expect_err=False, is_modified=pre_date)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_ims", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_ims")
        LOGGER.info("Step 6: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_iums", is_expect_err=False, is_unmodified=post_date)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_iums", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_iums")
        status, response = self.s3_obj.object_list(self.bucket_name2)
        assert_utils.assert_list_equal(obj_list, response)
        LOGGER.info("ENDED: Copy simple object with all conditional headers as true")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44752")
    @CTFailOn(error_handler)
    def test_44752(self):
        """
        Copy object Conditional params: All true for multipart object copy"""
        LOGGER.info("STARTED: Copy multipart object with all conditional headers as true")
        response = self.s3_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(response[0], response[1])
        LOGGER.info("Step 2: Upload multipart object to source bucket")
        _ = self.s3mp_test_obj.complete_multipart_upload_with_di(self.bucket_name1,
                                                                   self.object_name1,
                                                                   self.file_path, total_parts=2,
                                                                   file_size=10)
        obj_list = []
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2, self.object_name2)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im", is_expect_err=False, is_match=etag)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_im", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_im")
        LOGGER.info("Step 4: Copy object to different bucket with condition"
                    "x-amz-copy-source-if-none-match (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inm", is_expect_err=False, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_inm", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_inm")
        LOGGER.info("Step 5: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-modified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_ims", is_expect_err=False, is_modified=pre_date)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_ims", s3_testobj=self.s3_obj)
        obj_list.append(self.object_name2+"_ims")
        LOGGER.info("Step 6: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_iums", is_expect_err=False, is_unmodified=post_date)
        obj_list.append(self.object_name2+"_iums")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_iums", s3_testobj=self.s3_obj)
        status, response = self.s3_obj.object_list(self.bucket_name2)
        assert_utils.assert_list_equal(obj_list, response)
        LOGGER.info("ENDED: Copy multipart object with all conditional headers as true")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44753")
    @CTFailOn(error_handler)
    def test_44753(self):
        """
        Copy object Conditional params: All false for simple object copy"""
        LOGGER.info("STARTED: Copy simple object with all conditional headers as false")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2, self.object_name2)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "                             
                    "x-amz-copy-source-if-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im", is_expect_err=True, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 4: Copy object to different bucket with condition"                              
                    "x-amz-copy-source-if-none-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inm", is_expect_err=True, is_none_match=etag,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 5: Copy object to different bucket with condition "                             
                    "x-amz-copy-source-if-modified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_ims", is_expect_err=True, is_modified=post_date,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 6: Copy object to different bucket with condition "                             
                    "x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_iums", is_expect_err=True, is_unmodified=pre_date,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Copy simple object with all conditional headers as false")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44754")
    @CTFailOn(error_handler)
    def test_44754(self):
        """
        Copy object Conditional params: All false for multipart object copy"""
        LOGGER.info("STARTED: Copy multipart object with all conditional headers as true")
        _, response = self.s3_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(response[0], response[1])
        _, response = self.s3_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(response[0], response[1])
        LOGGER.info("Step 2: Upload multipart object to source bucket")
        etag, pre_date, post_date = upload_mpu_copy_obj(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        fpath=self.file_path, total_parts=2,
                                                        file_size=10, s3_testobj=self.s3_obj,
                                                        s3_mp_testobj=self.s3mp_test_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im", is_expect_err=True, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 4: Copy object to different bucket with condition"
                    "x-amz-copy-source-if-none-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inm", is_expect_err=True, is_none_match=etag,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 5: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-modified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_ims", is_expect_err=True, is_modified=post_date,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 6: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_iums", is_expect_err=True, is_unmodified=pre_date,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Copy multipart object with all conditional headers as false")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44755")
    @CTFailOn(error_handler)
    def test_44755(self):
        """ Copy object Conditional params: exceptions per aws for simple and multipart copy """
        LOGGER.info("STARTED: Test to check exceptions for certain conditions  to copy simple and "
                    "multipart objects")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, _ = self.handle_copy(self.bucket_name1, self.object_name1,
                                             self.bucket_name2, self.object_name2,
                                             is_expect_err=False)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-unmodified-since ("
                    "False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im_us", is_expect_err=False, is_match=etag,
                         is_unmodified=pre_date)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_im_us", s3_testobj=self.s3_obj)
        LOGGER.info("Step 4: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "modified-since (True) and x-amz-copy-source-if-none-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_ims_nm", is_expect_err=True, is_none_match=etag,
                         is_modified=pre_date, errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 5: Upload multipart object to bucket")
        etag, pre_date, _ = upload_mpu_copy_obj(self.bucket_name1, self.object_name1+"mpu",
                                                self.bucket_name2, self.object_name2+"mpu1",
                                                fpath=self.file_path, total_parts=2, file_size=10,
                                                s3_testobj=self.s3_obj,
                                                s3_mp_testobj=self.s3mp_test_obj)
        LOGGER.info("Step 6: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-unmodified-since ("
                    "False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_im_us", is_expect_err=False, is_match=etag,
                         is_unmodified=pre_date)
        copy_obj_di_check(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                          self.object_name2+"mpu_im_us", s3_testobj=self.s3_obj)
        LOGGER.info("Step 7: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "modified-since (True) and x-amz-copy-source-if-none-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_ims_nm", is_expect_err=True, is_none_match=etag,
                         is_modified=pre_date, errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Test to check exceptions for certain conditions  to copy simple and "
                    "multipart objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44756")
    @CTFailOn(error_handler)
    def test_44756(self):
        """ Copy object Conditional params: x-amz-copy-source-if-match and x-amz-copy-source-if-
        modified-since """
        LOGGER.info("STARTED: Test to check exceptions for certain conditions  to copy simple and "
                    "multipart objects")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2, self.object_name2,
                                                     is_expect_err=False)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-modified-since ("
                    "True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im_ms", is_expect_err=False,
                         is_modified=pre_date, is_match=etag)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_im_ms", s3_testobj=self.s3_obj)
        LOGGER.info("Step 4: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "modified-since (False) and x-amz-copy-source-if-match (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_im_msf", is_expect_err=True, is_modified=post_date,
                         is_match=etag, errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 5: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "modified-since (True) and x-amz-copy-source-if-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_imf_msf", is_expect_err=True, is_modified=pre_date,
                         is_match=etag+"_", errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 6: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "modified-since (False) and x-amz-copy-source-if-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_imsf_mf", is_expect_err=True, is_modified=post_date,
                         is_match=etag+"_", errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 7: Upload multipart object to bucket")
        etag, pre_date, _ = upload_mpu_copy_obj(self.bucket_name1, self.object_name1+"mpu",
                                                self.bucket_name2, self.object_name2+"mpu1",
                                                fpath=self.file_path, total_parts=2,
                                                file_size=10, s3_testobj=self.s3_obj,
                                                s3_mp_testobj=self.s3mp_test_obj)
        LOGGER.info("Step 8: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-modified-since ("
                    "True)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_im_ms", is_expect_err=False,
                         is_modified=pre_date, is_match=etag)
        copy_obj_di_check(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                          self.object_name2+"mpu_im_ms", s3_testobj=self.s3_obj)
        LOGGER.info("Step 9: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-modified-since ("
                    "False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_im_msf", is_expect_err=True, is_modified=post_date,
                         is_match=etag, errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 10: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "modified-since (True) and x-amz-copy-source-if-match (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_im_mst", is_expect_err=True,
                         is_modified=pre_date, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Test to check exceptions for certain conditions  to copy simple and "
                    "multipart objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44757")
    @CTFailOn(error_handler)
    def test_44757(self):
        """ Copy object Conditional params: x-amz-copy-source-if-match and
        x-amz-copy-source-if-unmodified-since"""
        LOGGER.info("STARTED: Test to validate the combinations of conditions with "
                    "x-amz-copy-source-if-match and x-amz-copy-source-if-unmodified-since for "
                    "copying simple and multipart object")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2, self.object_name2)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-unmodified-since ("
                    "True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_imt_umst", is_expect_err=False,
                         is_unmodified=post_date, is_match=etag)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_imt_umst", s3_testobj=self.s3_obj)
        LOGGER.info("Step 4: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "match (False) and x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_imf_umst", is_expect_err=True,
                         is_unmodified=pre_date, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 5: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "match (False) and x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_imf_umsf", is_expect_err=True,
                         is_unmodified=post_date, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 6: Upload multipart object to bucket")
        etag, pre_date, post_date = upload_mpu_copy_obj(self.bucket_name1, self.object_name1+"mpu",
                                                        self.bucket_name2, self.object_name2+"mpu1",
                                                        fpath=self.file_path, total_parts=2,
                                                        file_size=10, s3_testobj=self.s3_obj,
                                                        s3_mp_testobj=self.s3mp_test_obj)
        LOGGER.info("Step 7: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-match (True) and x-amz-copy-source-if-unmodified-since ("
                    "True)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_imt_umst", is_expect_err=False,
                         is_unmodified=post_date, is_match=etag)
        copy_obj_di_check(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                          self.object_name2+"mpu_imt_umst", s3_testobj=self.s3_obj)
        LOGGER.info("Step 8: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "match (False) and x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_imf_umst", is_expect_err=True,
                         is_unmodified=pre_date, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 9: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "match (False) and x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_imf_umsf", is_expect_err=True,
                         is_unmodified=post_date, is_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Test to validate the combinations of conditions with "
                    "x-amz-copy-source-if-match and x-amz-copy-source-if-unmodified-since for "
                    "copying simple and multipart object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44758")
    @CTFailOn(error_handler)
    def test_44758(self):
        """ Copy object Conditional params: x-amz-copy-source-if-none-match and
        x-amz-copy-source-if-modified-since """
        LOGGER.info("STARTED: Test to validate the combinations of conditions with "
                    "x-amz-copy-source-if-none-match and x-amz-copy-source-if-modified-since for "
                    "copying simple and multipart object")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2, self.object_name2)
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, s3_testobj=self.s3_obj)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-none-match (True) and "
                    "x-amz-copy-source-if-modified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmt_mst", is_expect_err=False,
                         is_modified=pre_date, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_inmt_mst", s3_testobj=self.s3_obj)
        LOGGER.info("Step 4: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (True) and x-amz-copy-source-if-modified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmt_msf", is_expect_err=False,
                         is_modified=post_date, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_inmt_msf", s3_testobj=self.s3_obj)
        LOGGER.info("Step 5: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "match (False) and x-amz-copy-source-if-modified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmf_msf", is_expect_err=True, is_modified=post_date,
                         is_none_match=etag, errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 6: Upload multipart object to bucket")
        etag, pre_date, post_date = upload_mpu_copy_obj(self.bucket_name1, self.object_name1+"mpu",
                                                        self.bucket_name2, self.object_name2+"mpu1",
                                                        fpath=self.file_path, total_parts=2,
                                                        file_size=10, s3_testobj=self.s3_obj,
                                                        s3_mp_testobj=self.s3mp_test_obj)
        LOGGER.info("Step 7: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-none-match (True) and "
                    "x-amz-copy-source-if-modified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"_inmt_mst", is_expect_err=False,
                         is_modified=pre_date, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                          self.object_name2+"_inmt_mst", s3_testobj=self.s3_obj)
        LOGGER.info("Step 8: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (True) and x-amz-copy-source-if-modified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"_inmt_msf", is_expect_err=False,
                         is_modified=post_date, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                          self.object_name2+"_inmt_msf", s3_testobj=self.s3_obj)
        LOGGER.info("Step 9: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "match (False) and x-amz-copy-source-if-modified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"_inmf_msf", is_expect_err=True, is_modified=post_date,
                         is_none_match=etag, errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Test to validate the combinations of conditions with "
                    "x-amz-copy-source-if-match and x-amz-copy-source-if-unmodified-since for "
                    "copying simple and multipart object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44767")
    @CTFailOn(error_handler)
    def test_44767(self):
        """ Copy object Conditional params: x-amz-copy-source-if-none-match and
        x-amz-copy-source-if-unmodified-since"""
        LOGGER.info("STARTED: Test to validate the combinations of conditions with "
                    "x-amz-copy-source-if-none-match and x-amz-copy-source-if-unmodified-since for "
                    "copying simple and multipart object")
        LOGGER.info("Step 1: Upload simple object to source bucket")
        resp = system_utils.create_file(fpath=self.file_path, count=10, b_size="1M")
        LOGGER.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        status, put_etag = self.create_bucket_put_object(self.s3_obj, self.bucket_name1,
                                                         self.object_name1, self.file_path)
        assert_utils.assert_true(status, put_etag)
        LOGGER.info("Step 2: Copy object to different bucket")
        etag, pre_date, post_date = self.handle_copy(self.bucket_name1, self.object_name1,
                                                     self.bucket_name2, self.object_name2)
        LOGGER.info("Step 3: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-none-match (True) and "
                    "x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmt_umst", is_expect_err=False,
                         is_unmodified=post_date, is_none_match=etag+"_")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2+"_inmt_umst", s3_testobj=self.s3_obj)
        LOGGER.info("Step 4: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (True) and x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmt_umsf", is_expect_err=True,
                         is_unmodified=pre_date, is_none_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 5: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (False) and x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmf_umst", is_expect_err=True,
                         is_unmodified=post_date, is_none_match=etag,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 6: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (False) and x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1, self.bucket_name2,
                         self.object_name2+"_inmf_umsf", is_expect_err = True,
                         is_unmodified=pre_date, is_none_match=etag,
                         errmsg = errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 7: Upload multipart object to bucket")
        etag, pre_date, post_date = upload_mpu_copy_obj(self.bucket_name1, self.object_name1+"mpu",
                                                        self.bucket_name2, self.object_name2+"mpu1",
                                                        fpath=self.file_path, total_parts=2,
                                                        file_size=10, s3_testobj=self.s3_obj,
                                                        s3_mp_testobj=self.s3mp_test_obj)
        LOGGER.info("Step 8: Copy object to different bucket with condition "
                    "x-amz-copy-source-if-none-match (True) and "
                    "x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_inmt_umst", is_expect_err=False,
                         is_unmodified=post_date, is_none_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 9: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (True) and x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_inmt_umsf", is_expect_err=True,
                         is_unmodified=pre_date, is_none_match=etag+"_",
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 10: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (False) and x-amz-copy-source-if-unmodified-since (True)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_inmf_umst", is_expect_err=True,
                         is_unmodified=post_date, is_none_match=etag,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("Step 11: Copy object to different bucket with condition x-amz-copy-source-if-"
                    "none-match (False) and x-amz-copy-source-if-unmodified-since (False)")
        self.handle_copy(self.bucket_name1, self.object_name1+"mpu", self.bucket_name2,
                         self.object_name2+"mpu_inmf_umsf", is_expect_err=True,
                         is_unmodified=pre_date, is_none_match=etag,
                         errmsg=errmsg.RGW_ERR_CPY_IF_COND_FALSE)
        LOGGER.info("ENDED: Test to validate the combinations of conditions with "
                    "x-amz-copy-source-if-none-match and x-amz-copy-source-if-unmodified-since for "
                    "copying simple and multipart object")

    def handle_copy(self, src_bucket, src_obj, dest_bucket, dest_obj, **kwargs):
        """ handling copy operation depending on conditional params passed
        :param src_bucket: The name of the source bucket.
        :param src_obj: The name of the source object.
        :param dest_bucket: The name of the destination bucket.
        :param dest_obj: The name of the destination object."""
        unmodified = kwargs.get("is_unmodified", None)
        modified = kwargs.get("is_modified", None)
        match = kwargs.get("is_match", None)
        nonematch = kwargs.get("is_none_match", None)
        is_expect_err = kwargs.get("is_expect_err", False)
        err_msg = kwargs.get ("errmsg", None)
        c_response = None
        try:
            if match is not None:
                if modified is not None:
                    status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                                 dest_obj,
                                                                 CopySourceIfModifiedSince=modified,
                                                                 CopySourceIfMatch=match)
                if unmodified is not None:
                    status, response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                               dest_obj, CopySourceIfMatch=match,
                                                               CopySourceIfUnmodifiedSince=\
                                                                   unmodified)
                else:
                    status, response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                               dest_obj, CopySourceIfMatch=match)
            elif nonematch is not None:
                if modified is not None:
                    status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                                 dest_obj,
                                                                 CopySourceIfModifiedSince=modified,
                                                                 CopySourceIfNoneMatch=nonematch)
                if unmodified is not None:
                    status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                                 dest_obj,
                                                                 CopySourceIfUnmodifiedSince=\
                                                                     unmodified,
                                                                 CopySourceIfNoneMatch=nonematch)
                else:
                    status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                                 dest_obj,
                                                                 CopySourceIfNoneMatch=nonematch)
            elif modified is not None:
                status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                             dest_obj,
                                                             CopySourceIfModifiedSince=modified)
            elif unmodified is not None:
                status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                             dest_obj,
                                                             CopySourceIfUnmodifiedSince=unmodified)
            else:
                response = self.s3_obj.create_bucket(self.bucket_name2)
                assert_utils.assert_true(response[0], response[1])
                status, c_response = self.s3_obj.copy_object(src_bucket, src_obj, dest_bucket,
                                                             dest_obj)
                assert_utils.assert_true(status, c_response)
                date1 = c_response["CopyObjectResult"]["LastModified"]
                pre_date = date1 - timedelta(days=1)
                post_date = date1 + timedelta(days=1)
                etag = c_response["CopyObjectResult"]["ETag"]
                if is_expect_err:
                    assert_utils.assert_false(status, c_response)
                else:
                    assert_utils.assert_true(status, c_response)
                return etag, pre_date, post_date
            if is_expect_err:
                assert_utils.assert_false(status, c_response)
            else:
                assert_utils.assert_true(status, c_response)
        except CTException as error:
            LOGGER.error(error.message)
            if is_expect_err:
                assert_utils.assert_in(err_msg, error.message, error)
