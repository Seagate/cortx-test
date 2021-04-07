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

"""Bucket Workflow Operations Test Module."""

import os
import time
import random
import logging
import pytest

from commons.params import TEST_DATA_FOLDER
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils import system_utils
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD


S3_TEST_OBJ = s3_test_lib.S3TestLib()
IAM_OBJ = iam_test_lib.IamTestLib()
ACL_OBJ = s3_acl_test_lib.S3AclTestLib()


class TestBucketWorkflowOperations:
    """Bucket Workflow Operations Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup suite operations")
        cls.random_id = str(time.time())
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.account_name = "bktwrkflowaccnt"
        cls.folder_path = os.path.join(TEST_DATA_FOLDER, "TestBucketWorkflowOperations")
        if not system_utils.path_exists(cls.folder_path):
            system_utils.make_dir(cls.folder_path)
        cls.file_path = os.path.join(cls.folder_path, "bkt_workflow.txt")
        cls.log.info("ENDED: Setup suite operations")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if system_utils.path_exists(cls.folder_path):
            system_utils.remove_dirs(cls.folder_path)
        cls.log.info("Cleanup test directory: %s", cls.folder_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                "bktworkflow")]
        for bktname in pref_list:
            ACL_OBJ.put_bucket_acl(
                bktname, acl="private")
        if pref_list:
            resp = S3_TEST_OBJ.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleting IAM accounts")
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        self.log.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        self.log.info(all_acc)
        for acc_name in all_acc:
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        self.log.info("Deleted IAM accounts successfully")
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5463")
    @CTFailOn(error_handler)
    def test_name_lowercase_letters_1975(self):
        """Bucket names must start with a lowercase letter or number."""
        self.log.info(
            "STARTED: Bucket names must start with a lowercase letter or number")
        self.log.info(
            "Creating a bucket with lowercase letter is %s",
            "bktworkflow")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow", resp[1]
        self.log.info(
            "Bucket is created with lowercase letter : %s",
            "bktworkflow")
        self.log.info(
            "Creating a bucket name which starts with number %s",
            "8535-bktworkflow")
        resp = S3_TEST_OBJ.create_bucket(
            "8535-bktworkflow")
        assert resp[0], resp[1]
        assert resp[1] == "8535-bktworkflow", resp[1]
        self.log.info(
            "Bucket is created with number : %s",
            "8535-bktworkflow")
        self.log.info("Cleanup activity")
        resp = S3_TEST_OBJ.delete_bucket(
            "8535-bktworkflow", force=True)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Bucket names must start with a lowercase letter or number")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5469")
    @CTFailOn(error_handler)
    def test_name_constains_alphanumeric_1976(self):
        """Bucket name can contain only lower-case characters, numbers, periods and dashes."""
        self.log.info(
            "STARTED: Bucket name can contain only lower-case chars, numbers, periods and dashes")
        self.log.info(
            "Creating a bucket with lower case, number, periods, dashes")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8536.bkt")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8536.bkt", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8536.bkt")
        self.log.info(
            "ENDED: Bucket name can contain only lower-case characters, "
            "numbers, periods and dashes")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5467")
    @CTFailOn(error_handler)
    def test_bucketname_2to63_chars_long_1977(self):
        """Bucket names must be at least 3 and no more than 63 characters long."""
        self.log.info(
            "STARTED: Bucket names must be at least 3 and no more than 63 characters long")
        self.log.info(
            "Creating a bucket with at least 3 characters is : %s",
            "bkt")
        resp = S3_TEST_OBJ.create_bucket(
            "bkt")
        assert resp[0], resp[1]
        assert resp[1] == "bkt", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bkt")
        self.log.info(
            "Creating a bucket with name  63 chars long is : %s",
            "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbuckets")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbuckets")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbuckets", resp[1]
        self.log.info(
            "Created a bucket with name 63 characters long is : %s",
            "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbuckets")
        self.log.info("Cleanup activity")
        resp = S3_TEST_OBJ.delete_bucket(
            "bkt", force=True)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Bucket names must be at least 3 and no more than 63 characters long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5468")
    @CTFailOn(error_handler)
    def test_name_lessthan3chars_morethan63chars_1978(self):
        """Bucket name with less than 3 characters and more than 63 characters."""
        self.log.info(
            "STARTED: Bucket name with less than 3 characters and more than 63 characters")
        self.log.info(
            "Creating buckets with name less than 3 and more than 63 character length")
        for each_bucket in ["a2", "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbucketsbktworkflow-seagateeosbucket"]:
            try:
                S3_TEST_OBJ.create_bucket(each_bucket)
            except CTException as error:
                self.log.error(error.message)
                assert "InvalidBucketName" in error.message, error.message
        self.log.info(
            "Creating buckets with name less than 3 and more than 63 characters length is failed")
        self.log.info(
            "ENDED: Bucket name with less than 3 characters and more than 63 characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5464")
    @CTFailOn(error_handler)
    def test_name_nouppercase_1979(self):
        """Bucket names must not contain uppercase characters."""
        self.log.info(
            "STARTED: Bucket names must not contain uppercase characters")
        self.log.info(
            "Creating a bucket with name : %s",
            "BKTWORKFLOW")
        try:
            S3_TEST_OBJ.create_bucket("BKTWORKFLOW")
        except CTException as error:
            self.log.error(error.message)
            assert "InvalidBucketName" in error.message, error.message
        self.log.info("Creating a bucket with uppercase letters is failed")
        self.log.info(
            "ENDED: Bucket names must not contain uppercase characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5465")
    @CTFailOn(error_handler)
    def test_name_without_underscores_1980(self):
        """Bucket names must not contain underscores."""
        self.log.info("STARTED: Bucket names must not contain underscores")
        self.log.info(
            "Creating a bucket with underscore is : %s",
            "bktworkflow_8540")
        try:
            S3_TEST_OBJ.create_bucket("bktworkflow_8540")
        except CTException as error:
            self.log.error(error.message)
            assert "InvalidBucketName" in error.message, error.message
        self.log.info("Creating a bucket with underscore is failed")
        self.log.info("ENDED: Bucket names must not contain underscores")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5462")
    @CTFailOn(error_handler)
    def test_name_special_characters_1981(self):
        """Bucket names with special characters."""
        self.log.info("STARTED: Bucket names with special characters")
        count_limit = random.choice(
            range(
                4,
                10))
        special_chars_list = ["!", "*", "(", ")", "%", "$"]
        special_chars = "".join(
            random.choices(
                special_chars_list,
                k=2))
        chars_name = "".join(
            random.choices(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                k=count_limit))
        bucket_name = "{0}{1}".format(chars_name, special_chars)
        self.log.info(
            "Creating a bucket with special chars is : %s", bucket_name)
        try:
            S3_TEST_OBJ.create_bucket(bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "Parameter validation failed" in error.message, error.message
        self.log.info("Creating a bucket with special characters is failed")
        self.log.info("ENDED: Bucket names with special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5466")
    @CTFailOn(error_handler)
    def test_name_formatting_1982(self):
        """Bucket names must not be formatted as an IP address (for example, 192.168.5.4)."""
        self.log.info(
            "STARTED: Bucket names must not be formatted as an IP address(for eg., 192.168.5.4)")
        self.log.info("Creating a bucket with name : %s",
                         "192.168.10.20")
        try:
            S3_TEST_OBJ.create_bucket("192.168.10.20")
        except CTException as error:
            self.log.error(error.message)
            assert "InvalidBucketName" in error.message, error.message
        self.log.info(
            "Creating a bucket with an IP address format is failed")
        self.log.info(
            "ENDED: Bucket names must not be formatted as an IP address (for example, 192.168.5.4)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5459")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2039(self):
        """Create single bucket."""
        self.log.info("STARTED: Create single bucket")
        self.log.info(
            "Creating single Bucket with name %s",
            "bktworkflow-8638")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8638")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8638", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8638")
        self.log.info("Verifying that bucket is created")
        resp = S3_TEST_OBJ.bucket_list()
        assert resp[0], resp[1]
        assert "bktworkflow-8638" in resp[1]
        self.log.info("Verified that bucket is created")
        self.log.info("ENDED: Creating single Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5460")
    @CTFailOn(error_handler)
    def test_create_multiple_buckets_2040(self):
        """Create multiple buckets."""
        self.log.info("STARTED: Create multiple buckets")
        self.log.info("Creating multiple buckets")
        bucket_list = []
        for each in range(10):
            bucket_name = "{0}{1}".format(
                "bktworkflow-8639", each)
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Created multiple buckets")
        self.log.info("Verifying that buckets are created")
        resp = S3_TEST_OBJ.bucket_list()
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        self.log.info("Verified that buckets are created")
        self.log.info("ENDED: Create multiple buckets")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5461")
    @CTFailOn(error_handler)
    def test_duplicate_name_2043(self):
        """Create bucket with same bucket name already present."""
        self.log.info(
            "STARTED: Create bucket with same bucket name already present")
        self.log.info("Creating a bucket with name %s",
                         "bktworkflow-8642")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8642")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8642", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8642")
        self.log.info("Creating a bucket with existing bucket name")
        try:
            S3_TEST_OBJ.create_bucket("bktworkflow-8642")
        except CTException as error:
            self.log.error(error.message)
            assert "BucketAlreadyOwnedByYou" in error.message, error.message
        self.log.info(
            "Creating a bucket with existing bucket name is failed")
        self.log.info(
            "ENDED: Create bucket with same bucket name already present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5447")
    @CTFailOn(error_handler)
    def test_max_bucket_creation_2044(self):
        """Verification of max. no. of buckets user can create."""
        self.log.info(
            "STARTED: Verification of max. no. of buckets user can create")
        self.log.info("Creating 100 max buckets")
        for each in range(100):
            bucket_name = "{0}{1}".format(
                "bktworkflow-8643", each)
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
        self.log.info("Created 100 buckets")
        self.log.info("Verifying that bucket is created")
        resp = S3_TEST_OBJ.bucket_count()
        assert resp[0], resp[1]
        self.log.info("Verified that buckets are created")
        self.log.info(
            "ENDED: Verification of max. no. of buckets user can create")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5457")
    @CTFailOn(error_handler)
    def test_delete_bucket_with_objects_2045(self):
        """Delete bucket which has objects."""
        self.log.info("STARTED: Delete bucket which has objects")
        self.log.info(
            "Creating a Bucket with name %s",
            "bktworkflow-8644")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8644")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8644", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8644")
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading an objects to a bucket")
        for i in range(5):
            objname = "{0}{1}".format(
                "object", i)
            resp = S3_TEST_OBJ.object_upload(
                "bktworkflow-8644",
                objname,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Objects are uploaded to a bucket")
        self.log.info("Deleting a bucket having objects")
        try:
            S3_TEST_OBJ.delete_bucket("bktworkflow-8644")
        except CTException as error:
            self.log.error(error.message)
            assert "BucketNotEmpty" in error.message, error.message
        self.log.info("ENDED: Delete bucket which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5458")
    @CTFailOn(error_handler)
    def test_forcefully_delete_objects_2046(self):
        """Delete bucket forcefully which has objects."""
        self.log.info("STARTED: Delete bucket forcefully which has objects")
        self.log.info(
            "Creating a bucket with name %s",
            "bktworkflow-8645")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8645")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8645", resp[1]
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading multiple objects to a bucket")
        for obj_cnt in range(5):
            objname = "{0}{1}".format(
                "bktworkflow-8645", str(obj_cnt))
            resp = S3_TEST_OBJ.object_upload(
                "bktworkflow-8645",
                objname,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Multiple objects are uploaded to a bucket")
        self.log.info("Forcefully deleting bucket having object")
        resp = S3_TEST_OBJ.delete_bucket(
            "bktworkflow-8645", force=True)
        assert resp[0], resp[1]
        self.log.info("Forcefully deleted a bucket")
        self.log.info("ENDED: Delete bucket forcefully which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5455")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2047(self):
        """Delete empty bucket."""
        self.log.info("STARTED: Delete empty bucket")
        self.log.info(
            "Creating a bucket with name %s",
            "bktworkflow-8646")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8646")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8646", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8646")
        self.log.info("Deleting a bucket")
        retv = S3_TEST_OBJ.delete_bucket(
            "bktworkflow-8646")
        assert retv[0], retv[1]
        self.log.info("Bucket is deleted")
        self.log.info("ENDED: Delete empty bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5454")
    @CTFailOn(error_handler)
    def test_delete_multiple_buckets_2048(self):
        """Delete multiple empty buckets."""
        self.log.info("STARTED: Delete multiple empty buckets")
        self.log.info("Creating multiple buckets")
        bucket_list = []
        for count in range(10):
            bucket_name = "{0}{1}".format(
                "bktworkflow-8647", str(count))
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Multiple buckets are created")
        self.log.info("Deleting multiple buckets")
        resp = S3_TEST_OBJ.delete_multiple_buckets(bucket_list)
        assert resp[0], resp[1]
        self.log.info("Multiple buckets are deleted")
        self.log.info("ENDED: Delete multiple empty buckets")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5456")
    @CTFailOn(error_handler)
    def test_delete_non_existing_bucket_2049(self):
        """Delete bucket when Bucket does not exists."""
        self.log.info("STARTED: Delete bucket when Bucket does not exists")
        self.log.info(
            "Deleting bucket which does not exists on s3 server")
        try:
            S3_TEST_OBJ.delete_bucket("bktworkflow-8648")
        except CTException as error:
            self.log.error(error.message)
            assert "NoSuchBucket" in error.message, error.message
        self.log.info(
            "Deleting bucket which does not exists on s3 server is failed")
        self.log.info(
            "ENDED: Delete bucket which does not exists on s3 server")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5452")
    @CTFailOn(error_handler)
    def test_list_all_buckets_2050(self):
        """List all objects in a bucket."""
        self.log.info("STARTED: List all objects in a bucket")
        self.log.info(
            "Creating a bucket with name %s",
            "bktworkflow-8649")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8649")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8649", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8649")
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading multiple objects to a bucket")
        object_list = []
        for count in range(5):
            objname = "{0}{1}".format(
                "bktworkflow-8649", str(count))
            resp = S3_TEST_OBJ.object_upload(
                "bktworkflow-8649",
                objname,
                self.file_path)
            assert resp[0], resp[1]
            object_list.append(objname)
        self.log.info("Multiple objects are uploaded")
        self.log.info("Listing all objects")
        resp = S3_TEST_OBJ.object_list(
            "bktworkflow-8649")
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.log.info("All objects are listed")
        self.log.info("ENDED: List all objects in a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5448")
    @CTFailOn(error_handler)
    def test_disk_usages_verification_2051(self):
        """Verification of disk usage by bucket."""
        self.log.info("STARTED: Verification of disk usage by bucket")
        self.log.info(
            "Creating a bucket with name %s",
            "bktworkflow-8650")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8650")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8650", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8650")
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading multiple objects to a bucket")
        for count in range(5):
            objname = "{0}{1}".format(
                "bktworkflow-8650", str(count))
            retv = S3_TEST_OBJ.object_upload(
                "bktworkflow-8650",
                objname,
                self.file_path)
            assert retv[0], retv[1]
        self.log.info("Multiple objects are uploaded")
        self.log.info("Retrieving bucket size")
        resp = S3_TEST_OBJ.get_bucket_size(
            "bktworkflow-8650")
        assert resp[0], resp[1]
        self.log.info("Retrieved bucket size")
        self.log.info("ENDED: Verification of disk usage by bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5453")
    @CTFailOn(error_handler)
    def test_head_non_existing_bucket_2055(self):
        """HEAD bucket when Bucket does not exists."""
        self.log.info("STARTED: HEAD bucket when Bucket does not exists")
        self.log.info("Performing head bucket on non existing bucket")
        try:
            S3_TEST_OBJ.head_bucket("bktworkflow-8654")
        except CTException as error:
            self.log.error(error.message)
            assert "Not Found" in error.message, error.message
        self.log.info("Head bucket on non existing bucket is failed")
        self.log.info("ENDED: HEAD bucket when Bucket does not exists")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5445")
    @CTFailOn(error_handler)
    def test_verify_head_bucket_2056(self):
        """Verify HEAD bucket."""
        self.log.info("STARTED: Verify HEAD bucket")
        self.log.info(
            "Creating a bucket with name %s",
            "bktworkflow-8655")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8655")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8655", resp[1]
        self.log.info(
            "Bucket is created with name %s",
            "bktworkflow-8655")
        self.log.info(
            "Performing head bucket on a bucket %s",
            "bktworkflow-8655")
        resp = S3_TEST_OBJ.head_bucket(
            "bktworkflow-8655")
        assert resp[0], resp[1]
        assert resp[1]["BucketName"] == "bktworkflow-8655", resp
        self.log.info(
            "Performed head bucket on a bucket %s",
            "bktworkflow-8655")
        self.log.info("ENDED: Verify HEAD bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5446")
    @CTFailOn(error_handler)
    def test_verify_list_bucket_2057(self):
        """Verify 'LIST buckets' command."""
        self.log.info("STARTED: Verify 'LIST buckets' command")
        self.log.info("Creating multiple buckets")
        bucket_list = []
        for count in range(10):
            bucket_name = "{0}{1}".format(
                "bktworkflow-8656", str(count))
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Multiple buckets are created")
        self.log.info("Listing buckets")
        resp = S3_TEST_OBJ.bucket_list()
        assert resp[0], resp[1]
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        self.log.info("Buckets are listed")
        self.log.info("ENDED: Verify 'LIST buckets' command")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5450")
    @CTFailOn(error_handler)
    def test_bucket_location_verification_2059(self):
        """Verification of bucket location."""
        self.log.info("STARTED: Verification of bucket location")
        self.log.info(
            "Creating a bucket with name %s",
            "bktworkflow-8658")
        resp = S3_TEST_OBJ.create_bucket(
            "bktworkflow-8658")
        assert resp[0], resp[1]
        assert resp[1] == "bktworkflow-8658", resp[1]
        resp = S3_TEST_OBJ.bucket_location(
            "bktworkflow-8658")
        assert resp[0], resp[1]
        assert resp[1]["LocationConstraint"] == \
            "us-west-2", resp[1]
        self.log.info("ENDED: Verification of bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8031")
    @CTFailOn(error_handler)
    def test_delete_multiobjects_432(self):
        """Delete multiobjects which are present in bucket."""
        self.log.info(
            "STARTED: Delete multiobjects which are present in bucket")
        bktname = "bktworkflow-432-{}".format(self.random_id)
        obj_cnt = 10
        self.log.info("Step 1: Creating a bucket and putting object")
        res = S3_TEST_OBJ.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        system_utils.create_file(self.file_path,
                    10)
        obj_lst = []
        for i in range(obj_cnt):
            obj = "{}{}".format("testobj", str(i))
            res = S3_TEST_OBJ.put_object(
                bktname, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info("Step 1: Created bucket and object uploaded")
        self.log.info("Step 2: Listing all the objects")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed")
        self.log.info("Step 3: Deleting all the object")
        resp = S3_TEST_OBJ.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        self.log.info("Step 3: All the objects deleted")
        self.log.info("Step 4: Check bucket is empty")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.log.info("Step 4: Verified that bucket was empty")
        self.log.info(
            "ENDED: Delete multiobjects which are present in bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8032")
    @CTFailOn(error_handler)
    def test_delete_non_existing_multibuckets_433(self):
        """Delete multiobjects where the bucket is not present."""
        self.log.info(
            "STARTED: Delete multiobjects where the bucket is not present")
        bktname = "bktworkflow-433-{}".format(self.random_id)
        obj_lst = ["obj1", "obj2"]
        self.log.info(
            "Step 1: Deleting the objects for non-existing bucket")
        try:
            S3_TEST_OBJ.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            self.log.error(error.message)
            assert "NoSuchBucket" in error.message, error.message
            self.log.info(
                "Step 1: objects delete operation failed with error %s",
                "NoSuchBucket")
        self.log.info("Step 2: List objects for non-existing bucket")
        try:
            S3_TEST_OBJ.object_list(bktname)
        except CTException as error:
            self.log.error(error.message)
            assert "NoSuchBucket" in error.message, error.message
            self.log.info(
                "Step 2: List objects for non-existing bucket failed with error %s",
                "NoSuchBucket")
        self.log.info(
            "ENDED: Delete multiobjects where the bucket is not present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8033")
    @CTFailOn(error_handler)
    def test_delete_object_without_permission_434(self):
        """
        create bucket and upload objects from account1.

         and dont give any permissions to account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        self.log.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        bktname = "bktworkflow-434-{}".format(self.random_id)
        acc_name_2 = "bktwrkflowaccnt434_{}".format(self.random_id)
        emailid_2 = "acltestaccnt434_{}@seagate.com".format(self.random_id)
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            acc_name_2, emailid_2)
        create_account = IAM_OBJ.create_account_s3iamcli(
            acc_name_2,
            emailid_2,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = S3_TEST_OBJ.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        system_utils.create_file(self.file_path,
                    10)
        obj_lst = []
        for i in range(10):
            obj = "{}{}".format("testobj", str(i))
            res = S3_TEST_OBJ.put_object(
                bktname, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.log.info("Step 2: Listing all the objects using account 1")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed using account 1")
        try:
            self.log.info("Step 3: Deleting all the object using account 2")
            s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            self.log.error(error.message)
            assert "AccessDenied" in error.message, error.message
            self.log.info(
                "Step 3: deleting objects using account 2 failed with error %s",
                "AccessDenied")
        self.log.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8035")
    @CTFailOn(error_handler)
    def test_delete_multiple_objects_without_permission_435(self):
        """
        create bucket and upload objects from account1.

        and dont give any permissions to
        account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        self.log.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        bktname = "bktworkflow-435-{}".format(self.random_id)
        acc_name_2 = "bktwrkflowaccnt435_{}".format(self.random_id)
        emailid_2 = "acltestaccnt435_{}@seagate.com".format(self.random_id)
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            acc_name_2, emailid_2)
        create_account = IAM_OBJ.create_account_s3iamcli(
            acc_name_2,
            emailid_2,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = S3_TEST_OBJ.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        system_utils.create_file(self.file_path,
                    10)
        obj_lst = []
        for i in range(10):
            obj = "{}{}".format("testobj", str(i))
            res = S3_TEST_OBJ.put_object(
                bktname, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.log.info("Step 2: Listing all the objects using account 1")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed using account 1")
        self.log.info(
            "Step 3: give full-control permissions for account2 for the bucket")
        resp = ACL_OBJ.put_bucket_acl(
            bktname, grant_full_control="id={}".format(
                create_account[1]["canonical_id"]))
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Full-control permission was successfully assigned to account 2")
        self.log.info("Step 4: Deleting all the object using account 2")
        resp = s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        self.log.info("Step 4: All the objects deleted")
        self.log.info("Step 5: Check bucket is empty")
        ACL_OBJ.put_bucket_acl(
            bktname, acl="private")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.log.info("Step 5: Verified that bucket was empty")
        resp = S3_TEST_OBJ.delete_bucket(bktname, force=True)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
