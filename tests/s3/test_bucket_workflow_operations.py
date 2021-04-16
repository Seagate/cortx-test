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
import shutil
import random
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD, S3_CFG


BKT_OPS_CONF = read_yaml(
    "config/s3/test_bucket_workflow_operations.yaml")[1]


class TestBucketWorkflowOperations:
    """Bucket Workflow Operations Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.random_id = str(time.time())
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.account_name = BKT_OPS_CONF["bucket_workflow"]["acc_name_prefix"]
        cls.folder_path = os.path.join(os.getcwd(), "testdata")
        cls.file_path = os.path.join(cls.folder_path, "bkt_workflow.txt")

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        self.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.iam_obj = iam_test_lib.IamTestLib(endpoint_url=S3_CFG["iam_url"])
        self.acl_obj = s3_acl_test_lib.S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        if os.path.exists(self.folder_path):
            shutil.rmtree(self.folder_path)
        bucket_list = self.s3_obj.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                BKT_OPS_CONF["bucket_workflow"]["bkt_name_prefix"])]
        for bktname in pref_list:
            self.acl_obj.put_bucket_acl(
                bktname, acl=BKT_OPS_CONF["bucket_workflow"]["bkt_permission"])
        self.s3_obj.delete_multiple_buckets(pref_list)
        if os.path.exists(self.file_path):
            remove_file(
                self.file_path)
        self.log.info("Deleting IAM accounts")
        self.account_name = BKT_OPS_CONF["bucket_workflow"]["acc_name_prefix"]
        acc_list = self.iam_obj.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        self.log.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        self.log.info(all_acc)
        for acc_name in all_acc:
            self.iam_obj.reset_access_key_and_delete_account_s3iamcli(acc_name)
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
            BKT_OPS_CONF["test_8535"]["bucket_name_1"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8535"]["bucket_name_1"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8535"]["bucket_name_1"], resp[1]
        self.log.info(
            "Bucket is created with lowercase letter : %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_1"])
        self.log.info(
            "Creating a bucket name which starts with number %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_2"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8535"]["bucket_name_2"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8535"]["bucket_name_2"], resp[1]
        self.log.info(
            "Bucket is created with number : %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_2"])
        self.log.info("Cleanup activity")
        resp = self.s3_obj.delete_bucket(
            BKT_OPS_CONF["test_8535"]["bucket_name_2"], force=True)
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
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8536"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8536"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8536"]["bucket_name"])
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
            BKT_OPS_CONF["test_8537"]["bucket_name_1"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8537"]["bucket_name_1"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8537"]["bucket_name_1"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_1"])
        self.log.info(
            "Creating a bucket with name  63 chars long is : %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_2"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8537"]["bucket_name_2"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8537"]["bucket_name_2"], resp[1]
        self.log.info(
            "Created a bucket with name 63 characters long is : %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_2"])
        self.log.info("Cleanup activity")
        resp = self.s3_obj.delete_bucket(
            BKT_OPS_CONF["test_8537"]["bucket_name_1"], force=True)
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
        for each_bucket in BKT_OPS_CONF["test_8538"]["bucket_list"]:
            try:
                self.s3_obj.create_bucket(each_bucket)
            except CTException as error:
                self.log.error(error.message)
                assert BKT_OPS_CONF["test_8538"]["error_message"] in error.message, error.message
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
            BKT_OPS_CONF["test_8539"]["bucket_name"])
        try:
            self.s3_obj.create_bucket(BKT_OPS_CONF["test_8539"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8539"]["error_message"] in error.message, error.message
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
            BKT_OPS_CONF["test_8540"]["bucket_name"])
        try:
            self.s3_obj.create_bucket(BKT_OPS_CONF["test_8540"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8540"]["error_message"] in error.message, error.message
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
                BKT_OPS_CONF["test_8541"]["start_range"],
                BKT_OPS_CONF["test_8541"]["end_range"]))
        special_chars_list = BKT_OPS_CONF["test_8541"]["special_chars_list"]
        special_chars = "".join(
            random.choices(
                special_chars_list,
                k=BKT_OPS_CONF["test_8541"]["special_char_len"]))
        chars_name = "".join(
            random.choices(
                BKT_OPS_CONF["test_8541"]["bucket_name"],
                k=count_limit))
        bucket_name = "{0}{1}".format(chars_name, special_chars)
        self.log.info(
            "Creating a bucket with special chars is : %s", bucket_name)
        try:
            self.s3_obj.create_bucket(bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8541"]["error_message"] in error.message, error.message
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
                         BKT_OPS_CONF["test_8542"]["bucket_name"])
        try:
            self.s3_obj.create_bucket(BKT_OPS_CONF["test_8542"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8542"]["error_message"] in error.message, error.message
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
            BKT_OPS_CONF["test_8638"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8638"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8638"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8638"]["bucket_name"])
        self.log.info("Verifying that bucket is created")
        resp = self.s3_obj.bucket_list()
        assert resp[0], resp[1]
        assert BKT_OPS_CONF["test_8638"]["bucket_name"] in resp[1]
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
        for each in range(BKT_OPS_CONF["test_8639"]["range"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8639"]["bucket_str"], each)
            resp = self.s3_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Created multiple buckets")
        self.log.info("Verifying that buckets are created")
        resp = self.s3_obj.bucket_list()
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
                         BKT_OPS_CONF["test_8642"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8642"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8642"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8642"]["bucket_name"])
        self.log.info("Creating a bucket with existing bucket name")
        try:
            self.s3_obj.create_bucket(BKT_OPS_CONF["test_8642"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8642"]["error_message"] in error.message, error.message
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
        for each in range(BKT_OPS_CONF["test_8643"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8643"]["bucket_name"], each)
            resp = self.s3_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
        self.log.info("Created 100 buckets")
        self.log.info("Verifying that bucket is created")
        resp = self.s3_obj.bucket_count()
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
            BKT_OPS_CONF["test_8644"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8644"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8644"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8644"]["bucket_name"])
        create_file(
            self.file_path,
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.log.info("Uploading an objects to a bucket")
        for i in range(BKT_OPS_CONF["test_8644"]["object_count"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8644"]["object_str"], i)
            resp = self.s3_obj.object_upload(
                BKT_OPS_CONF["test_8644"]["bucket_name"],
                objname,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Objects are uploaded to a bucket")
        self.log.info("Deleting a bucket having objects")
        try:
            self.s3_obj.delete_bucket(BKT_OPS_CONF["test_8644"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8644"]["error_message"] in error.message, error.message
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
            BKT_OPS_CONF["test_8645"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8645"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8645"]["bucket_name"], resp[1]
        create_file(
            self.file_path,
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.log.info("Uploading multiple objects to a bucket")
        for obj_cnt in range(BKT_OPS_CONF["test_8645"]["range"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8645"]["bucket_name"], str(obj_cnt))
            resp = self.s3_obj.object_upload(
                BKT_OPS_CONF["test_8645"]["bucket_name"],
                objname,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Multiple objects are uploaded to a bucket")
        self.log.info("Forcefully deleting bucket having object")
        resp = self.s3_obj.delete_bucket(
            BKT_OPS_CONF["test_8645"]["bucket_name"], force=True)
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
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8646"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        self.log.info("Deleting a bucket")
        retv = self.s3_obj.delete_bucket(
            BKT_OPS_CONF["test_8646"]["bucket_name"])
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
        for count in range(BKT_OPS_CONF["test_8647"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8647"]["bucket_name"], str(count))
            resp = self.s3_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Multiple buckets are created")
        self.log.info("Deleting multiple buckets")
        resp = self.s3_obj.delete_multiple_buckets(bucket_list)
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
            self.s3_obj.delete_bucket(BKT_OPS_CONF["test_8648"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8648"]["error_message"] in error.message, error.message
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
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8649"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        create_file(
            self.file_path,
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.log.info("Uploading multiple objects to a bucket")
        object_list = []
        for count in range(BKT_OPS_CONF["test_8649"]["object_count"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8649"]["bucket_name"], str(count))
            resp = self.s3_obj.object_upload(
                BKT_OPS_CONF["test_8649"]["bucket_name"],
                objname,
                self.file_path)
            assert resp[0], resp[1]
            object_list.append(objname)
        self.log.info("Multiple objects are uploaded")
        self.log.info("Listing all objects")
        resp = self.s3_obj.object_list(
            BKT_OPS_CONF["test_8649"]["bucket_name"])
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
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8650"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        create_file(
            self.file_path,
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.log.info("Uploading multiple objects to a bucket")
        for count in range(BKT_OPS_CONF["test_8650"]["object_count"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8650"]["bucket_name"], str(count))
            retv = self.s3_obj.object_upload(
                BKT_OPS_CONF["test_8650"]["bucket_name"],
                objname,
                self.file_path)
            assert retv[0], retv[1]
        self.log.info("Multiple objects are uploaded")
        self.log.info("Retrieving bucket size")
        resp = self.s3_obj.get_bucket_size(
            BKT_OPS_CONF["test_8650"]["bucket_name"])
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
            self.s3_obj.head_bucket(BKT_OPS_CONF["test_8654"]["bucket_name"])
        except CTException as error:
            self.log.error(error.message)
            assert BKT_OPS_CONF["test_8654"]["error_message"] in error.message, error.message
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
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8655"]["bucket_name"], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        self.log.info(
            "Performing head bucket on a bucket %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        resp = self.s3_obj.head_bucket(
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1]["BucketName"] == BKT_OPS_CONF["test_8655"]["bucket_name"], resp
        self.log.info(
            "Performed head bucket on a bucket %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
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
        for count in range(BKT_OPS_CONF["test_8656"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8656"]["bucket_name"], str(count))
            resp = self.s3_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Multiple buckets are created")
        self.log.info("Listing buckets")
        resp = self.s3_obj.bucket_list()
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
            BKT_OPS_CONF["test_8658"]["bucket_name"])
        resp = self.s3_obj.create_bucket(
            BKT_OPS_CONF["test_8658"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8658"]["bucket_name"], resp[1]
        resp = self.s3_obj.bucket_location(
            BKT_OPS_CONF["test_8658"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1]["LocationConstraint"] == \
            BKT_OPS_CONF["test_8658"]["bucket_location"], resp[1]
        self.log.info("ENDED: Verification of bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8031")
    @CTFailOn(error_handler)
    def test_delete_multiobjects_432(self):
        """Delete multiobjects which are present in bucket."""
        self.log.info(
            "STARTED: Delete multiobjects which are present in bucket")
        test_cfg = BKT_OPS_CONF["test_432"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_cnt = test_cfg["range"]
        self.log.info("Step 1: Creating a bucket and putting object")
        res = self.s3_obj.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(self.file_path,
                    BKT_OPS_CONF["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(obj_cnt):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = self.s3_obj.put_object(
                bktname, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info("Step 1: Created bucket and object uploaded")
        self.log.info("Step 2: Listing all the objects")
        resp = self.s3_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed")
        self.log.info("Step 3: Deleting all the object")
        resp = self.s3_obj.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        self.log.info("Step 3: All the objects deleted")
        self.log.info("Step 4: Check bucket is empty")
        resp = self.s3_obj.object_list(bktname)
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
        test_cfg = BKT_OPS_CONF["test_433"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_lst = test_cfg["obj_lst"]
        self.log.info(
            "Step 1: Deleting the objects for non-existing bucket")
        try:
            self.s3_obj.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            self.log.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            self.log.info(
                "Step 1: objects delete operation failed with error %s",
                test_cfg["err_message"])
        self.log.info("Step 2: List objects for non-existing bucket")
        try:
            self.s3_obj.object_list(bktname)
        except CTException as error:
            self.log.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            self.log.info(
                "Step 2: List objects for non-existing bucket failed with error %s",
                test_cfg["err_message"])
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
        test_cfg = BKT_OPS_CONF["test_434"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            acc_name_2, emailid_2)
        create_account = self.iam_obj.create_account_s3iamcli(
            acc_name_2,
            emailid_2,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            endpoint_url=S3_CFG["s3_url"], access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = self.s3_obj.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(self.file_path,
                    BKT_OPS_CONF["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(test_cfg["range"]):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = self.s3_obj.put_object(
                bktname, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.log.info("Step 2: Listing all the objects using account 1")
        resp = self.s3_obj.object_list(bktname)
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
            assert test_cfg["err_message"] in error.message, error.message
            self.log.info(
                "Step 3: deleting objects using account 2 failed with error %s",
                test_cfg["err_message"])
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
        test_cfg = BKT_OPS_CONF["test_435"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            acc_name_2, emailid_2)
        create_account = self.iam_obj.create_account_s3iamcli(
            acc_name_2,
            emailid_2,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            endpoint_url=S3_CFG["s3_url"], access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = self.s3_obj.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(self.file_path,
                    BKT_OPS_CONF["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(test_cfg["range"]):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = self.s3_obj.put_object(
                bktname, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.log.info("Step 2: Listing all the objects using account 1")
        resp = self.s3_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed using account 1")
        self.log.info(
            "Step 3: give full-control permissions for account2 for the bucket")
        resp = self.acl_obj.put_bucket_acl(
            bktname, grant_full_control=test_cfg["id_str"].format(
                create_account[1]["canonical_id"]))
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Full-control permission was successfully assigned to account 2")
        self.log.info("Step 4: Deleting all the object using account 2")
        resp = s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        self.log.info("Step 4: All the objects deleted")
        self.log.info("Step 5: Check bucket is empty")
        self.acl_obj.put_bucket_acl(
            bktname, acl=BKT_OPS_CONF["bucket_workflow"]["bkt_permission"])
        resp = self.s3_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.log.info("Step 5: Verified that bucket was empty")
        resp = self.s3_obj.delete_bucket(bktname, force=True)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
