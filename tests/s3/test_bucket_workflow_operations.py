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

"""Bukcet Workflow Operations Test Module."""
import random
import os
import time
import logging
import pytest

from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib

from commons.utils.system_utils import create_file, remove_file
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons import const
from commons.utils.config_utils import read_yaml


S3_TEST_OBJ = s3_test_lib.S3TestLib()
IAM_OBJ = iam_test_lib.IamTestLib()
ACL_OBJ = s3_acl_test_lib.S3AclTestLib()

BKT_OPS_CONF = read_yaml(
    "config/s3/test_bucket_workflow_operations.yaml")
CMN_CONF = read_yaml("config/common_config.yaml")


class TestBucketWorkflowOperations:
    """Bucket Workflow Operations Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.LOGGER = logging.getLogger(__name__)
        cls.random_id = str(time.time())
        cls.ldap_user = const.S3_BUILD_VER[CMN_CONF["BUILD_VER_TYPE"]
                                           ]["ldap_creds"]["ldap_username"]
        cls.ldap_pwd = const.S3_BUILD_VER[CMN_CONF["BUILD_VER_TYPE"]
                                          ]["ldap_creds"]["ldap_passwd"]
        cls.account_name = BKT_OPS_CONF["bucket_workflow"]["acc_name_prefix"]

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any
        """
        self.LOGGER.info("STARTED: Setup operations")

        self.LOGGER.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.LOGGER.info("STARTED: Teardown operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                BKT_OPS_CONF["bucket_workflow"]["bkt_name_prefix"])]
        for bktname in pref_list:
            ACL_OBJ.put_bucket_acl(
                bktname, acl=BKT_OPS_CONF["bucket_workflow"]["bkt_permission"])
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        if os.path.exists(BKT_OPS_CONF["bucket_workflow"]["file_path"]):
            remove_file(
                BKT_OPS_CONF["bucket_workflow"]["file_path"])
        self.LOGGER.info("Deleting IAM accounts")
        self.account_name = BKT_OPS_CONF["bucket_workflow"]["acc_name_prefix"]
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        self.LOGGER.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        self.LOGGER.info(all_acc)
        for acc_name in all_acc:
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        self.LOGGER.info("Deleted IAM accounts successfully")
        self.LOGGER.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5463")
    @CTFailOn(error_handler)
    def test_1975(self):
        """Bucket names must start with a lowercase letter or number."""
        self.LOGGER.info(
            "STARTED: Bucket names must start with a lowercase letter or number")
        self.LOGGER.info(
            "Creating a bucket with lowercase letter is %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_1"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8535"]["bucket_name_1"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8535"]["bucket_name_1"], resp[1]
        self.LOGGER.info(
            "Bucket is created with lowercase letter : %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_1"])
        self.LOGGER.info(
            "Creating a bucket name which starts with number %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_2"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8535"]["bucket_name_2"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8535"]["bucket_name_2"], resp[1]
        self.LOGGER.info(
            "Bucket is created with number : %s",
            BKT_OPS_CONF["test_8535"]["bucket_name_2"])
        self.LOGGER.info("Cleanup activity")
        resp = S3_TEST_OBJ.delete_bucket(
            BKT_OPS_CONF["test_8535"]["bucket_name_2"], force=True)
        assert resp[0], resp[1]
        self.LOGGER.info(
            "ENDED: Bucket names must start with a lowercase letter or number")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5469")
    @CTFailOn(error_handler)
    def test_1976(self):
        """Bucket name can contain only lower-case characters, numbers, periods and dashes."""
        self.LOGGER.info(
            "STARTED: Bucket name can contain only lower-case chars, numbers, periods and dashes")
        self.LOGGER.info(
            "Creating a bucket with lower case, number, periods, dashes")
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8536"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8536"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8536"]["bucket_name"])
        self.LOGGER.info(
            "ENDED: Bucket name can contain only lower-case characters, "
            "numbers, periods and dashes")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5467")
    @CTFailOn(error_handler)
    def test_1977(self):
        """Bucket names must be at least 3 and no more than 63 characters long."""
        self.LOGGER.info(
            "STARTED: Bucket names must be at least 3 and no more than 63 characters long")
        self.LOGGER.info(
            "Creating a bucket with at least 3 characters is : %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_1"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8537"]["bucket_name_1"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8537"]["bucket_name_1"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_1"])
        self.LOGGER.info(
            "Creating a bucket with name  63 chars long is : %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_2"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8537"]["bucket_name_2"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8537"]["bucket_name_2"], resp[1]
        self.LOGGER.info(
            "Created a bucket with name 63 characters long is : %s",
            BKT_OPS_CONF["test_8537"]["bucket_name_2"])
        self.LOGGER.info("Cleanup activity")
        resp = S3_TEST_OBJ.delete_bucket(
            BKT_OPS_CONF["test_8537"]["bucket_name_1"], force=True)
        assert resp[0], resp[1]
        self.LOGGER.info(
            "ENDED: Bucket names must be at least 3 and no more than 63 characters long")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5468")
    def test_1978(self):
        """Bucket name with less than 3 characters and more than 63 characters."""
        self.LOGGER.info(
            "STARTED: Bucket name with less than 3 characters and more than 63 characters")
        self.LOGGER.info(
            "Creating buckets with name less than 3 and more than 63 character length")
        for each_bucket in BKT_OPS_CONF["test_8538"]["bucket_list"]:
            try:
                S3_TEST_OBJ.create_bucket(each_bucket)
            except CTException as error:
                self.LOGGER.error(error.message)
                assert BKT_OPS_CONF["test_8538"]["error_message"] in error.message, error.message
        self.LOGGER.info(
            "Creating buckets with name less than 3 and more than 63 characters length is failed")
        self.LOGGER.info(
            "ENDED: Bucket name with less than 3 characters and more than 63 characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5464")
    def test_1979(self):
        """Bucket names must not contain uppercase characters."""
        self.LOGGER.info(
            "STARTED: Bucket names must not contain uppercase characters")
        self.LOGGER.info(
            "Creating a bucket with name : %s",
            BKT_OPS_CONF["test_8539"]["bucket_name"])
        try:
            S3_TEST_OBJ.create_bucket(BKT_OPS_CONF["test_8539"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8539"]["error_message"] in error.message, error.message
        self.LOGGER.info("Creating a bucket with uppercase letters is failed")
        self.LOGGER.info(
            "ENDED: Bucket names must not contain uppercase characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5465")
    def test_1980(self):
        """Bucket names must not contain underscores."""
        self.LOGGER.info("STARTED: Bucket names must not contain underscores")
        self.LOGGER.info(
            "Creating a bucket with underscore is : %s",
            BKT_OPS_CONF["test_8540"]["bucket_name"])
        try:
            S3_TEST_OBJ.create_bucket(BKT_OPS_CONF["test_8540"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8540"]["error_message"] in error.message, error.message
        self.LOGGER.info("Creating a bucket with underscore is failed")
        self.LOGGER.info("ENDED: Bucket names must not contain underscores")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5462")
    def test_1981(self):
        """Bucket names with special characters."""
        self.LOGGER.info("STARTED: Bucket names with special characters")
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
        self.LOGGER.info(
            "Creating a bucket with special chars is : %s", bucket_name)
        try:
            S3_TEST_OBJ.create_bucket(bucket_name)
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8541"]["error_message"] in error.message, error.message
        self.LOGGER.info("Creating a bucket with special characters is failed")
        self.LOGGER.info("ENDED: Bucket names with special characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5466")
    def test_1982(self):
        """Bucket names must not be formatted as an IP address (for example, 192.168.5.4)."""
        self.LOGGER.info(
            "STARTED: Bucket names must not be formatted as an IP address(for eg., 192.168.5.4)")
        self.LOGGER.info("Creating a bucket with name : %s",
                         BKT_OPS_CONF["test_8542"]["bucket_name"])
        try:
            S3_TEST_OBJ.create_bucket(BKT_OPS_CONF["test_8542"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8542"]["error_message"] in error.message, error.message
        self.LOGGER.info(
            "Creating a bucket with an IP address format is failed")
        self.LOGGER.info(
            "ENDED: Bucket names must not be formatted as an IP address (for example, 192.168.5.4)")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5459")
    @CTFailOn(error_handler)
    def test_2039(self):
        """Create single bucket."""
        self.LOGGER.info("STARTED: Create single bucket")
        self.LOGGER.info(
            "Creating single Bucket with name %s",
            BKT_OPS_CONF["test_8638"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8638"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8638"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8638"]["bucket_name"])
        self.LOGGER.info("Verifying that bucket is created")
        resp = S3_TEST_OBJ.bucket_list()
        assert resp[0], resp[1]
        assert BKT_OPS_CONF["test_8638"]["bucket_name"] in resp[1]
        self.LOGGER.info("Verified that bucket is created")
        self.LOGGER.info("ENDED: Creating single Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5460")
    @CTFailOn(error_handler)
    def test_2040(self):
        """Create multiple buckets."""
        self.LOGGER.info("STARTED: Create multiple buckets")
        self.LOGGER.info("Creating multiple buckets")
        bucket_list = []
        for each in range(BKT_OPS_CONF["test_8639"]["range"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8639"]["bucket_str"], each)
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.LOGGER.info("Created multiple buckets")
        self.LOGGER.info("Verifying that buckets are created")
        resp = S3_TEST_OBJ.bucket_list()
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        self.LOGGER.info("Verified that buckets are created")
        self.LOGGER.info("ENDED: Create multiple buckets")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5461")
    def test_2043(self):
        """Create bucket with same bucket name already present."""
        self.LOGGER.info(
            "STARTED: Create bucket with same bucket name already present")
        self.LOGGER.info("Creating a bucket with name %s",
                         BKT_OPS_CONF["test_8642"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8642"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8642"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8642"]["bucket_name"])
        self.LOGGER.info("Creating a bucket with existing bucket name")
        try:
            S3_TEST_OBJ.create_bucket(BKT_OPS_CONF["test_8642"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8642"]["error_message"] in error.message, error.message
        self.LOGGER.info(
            "Creating a bucket with existing bucket name is failed")
        self.LOGGER.info(
            "ENDED: Create bucket with same bucket name already present")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5447")
    @CTFailOn(error_handler)
    def test_2044(self):
        """Verification of max. no. of buckets user can create."""
        self.LOGGER.info(
            "STARTED: Verification of max. no. of buckets user can create")
        self.LOGGER.info("Creating 100 max buckets")
        for each in range(BKT_OPS_CONF["test_8643"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8643"]["bucket_name"], each)
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
        self.LOGGER.info("Created 100 buckets")
        self.LOGGER.info("Verifying that bucket is created")
        resp = S3_TEST_OBJ.bucket_count()
        assert resp[0], resp[1]
        self.LOGGER.info("Verified that buckets are created")
        self.LOGGER.info(
            "ENDED: Verification of max. no. of buckets user can create")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5457")
    def test_2045(self):
        """Delete bucket which has objects."""
        self.LOGGER.info("STARTED: Delete bucket which has objects")
        self.LOGGER.info(
            "Creating a Bucket with name %s",
            BKT_OPS_CONF["test_8644"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8644"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8644"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8644"]["bucket_name"])
        create_file(
            BKT_OPS_CONF["bucket_workflow"]["file_path"],
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.LOGGER.info("Uploading an objects to a bucket")
        for i in range(BKT_OPS_CONF["test_8644"]["object_count"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8644"]["object_str"], i)
            resp = S3_TEST_OBJ.object_upload(
                BKT_OPS_CONF["test_8644"]["bucket_name"],
                objname,
                BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert resp[0], resp[1]
        self.LOGGER.info("Objects are uploaded to a bucket")
        self.LOGGER.info("Deleting a bucket having objects")
        try:
            S3_TEST_OBJ.delete_bucket(BKT_OPS_CONF["test_8644"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8644"]["error_message"] in error.message, error.message
        self.LOGGER.info("ENDED: Delete bucket which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5458")
    @CTFailOn(error_handler)
    def test_2046(self):
        """Delete bucket forcefully which has objects."""
        self.LOGGER.info("STARTED: Delete bucket forcefully which has objects")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            BKT_OPS_CONF["test_8645"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8645"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8645"]["bucket_name"], resp[1]
        create_file(
            BKT_OPS_CONF["bucket_workflow"]["file_path"],
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.LOGGER.info("Uploading multiple objects to a bucket")
        for obj_cnt in range(BKT_OPS_CONF["test_8645"]["range"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8645"]["bucket_name"], str(obj_cnt))
            resp = S3_TEST_OBJ.object_upload(
                BKT_OPS_CONF["test_8645"]["bucket_name"],
                objname,
                BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert resp[0], resp[1]
        self.LOGGER.info("Multiple objects are uploaded to a bucket")
        self.LOGGER.info("Forcefully deleting bucket having object")
        resp = S3_TEST_OBJ.delete_bucket(
            BKT_OPS_CONF["test_8645"]["bucket_name"], force=True)
        assert resp[0], resp[1]
        self.LOGGER.info("Forcefully deleted a bucket")
        self.LOGGER.info("ENDED: Delete bucket forcefully which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5455")
    @CTFailOn(error_handler)
    def test_2047(self):
        """Delete empty bucket."""
        self.LOGGER.info("STARTED: Delete empty bucket")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8646"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        self.LOGGER.info("Deleting a bucket")
        retv = S3_TEST_OBJ.delete_bucket(
            BKT_OPS_CONF["test_8646"]["bucket_name"])
        assert retv[0], retv[1]
        self.LOGGER.info("Bucket is deleted")
        self.LOGGER.info("ENDED: Delete empty bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5454")
    @CTFailOn(error_handler)
    def test_2048(self):
        """Delete multiple empty buckets."""
        self.LOGGER.info("STARTED: Delete multiple empty buckets")
        self.LOGGER.info("Creating multiple buckets")
        bucket_list = []
        for count in range(BKT_OPS_CONF["test_8647"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8647"]["bucket_name"], str(count))
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.LOGGER.info("Multiple buckets are created")
        self.LOGGER.info("Deleting multiple buckets")
        resp = S3_TEST_OBJ.delete_multiple_buckets(bucket_list)
        assert resp[0], resp[1]
        self.LOGGER.info("Multiple buckets are deleted")
        self.LOGGER.info("ENDED: Delete multiple empty buckets")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5456")
    def test_2049(self):
        """Delete bucket when Bucket does not exists."""
        self.LOGGER.info("STARTED: Delete bucket when Bucket does not exists")
        self.LOGGER.info(
            "Deleting bucket which does not exists on s3 server")
        try:
            S3_TEST_OBJ.delete_bucket(BKT_OPS_CONF["test_8648"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8648"]["error_message"] in error.message, error.message
        self.LOGGER.info(
            "Deleting bucket which does not exists on s3 server is failed")
        self.LOGGER.info(
            "ENDED: Delete bucket which does not exists on s3 server")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5452")
    @CTFailOn(error_handler)
    def test_2050(self):
        """List all objects in a bucket."""
        self.LOGGER.info("STARTED: List all objects in a bucket")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8649"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        create_file(
            BKT_OPS_CONF["bucket_workflow"]["file_path"],
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.LOGGER.info("Uploading multiple objects to a bucket")
        object_list = []
        for count in range(BKT_OPS_CONF["test_8649"]["object_count"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8649"]["bucket_name"], str(count))
            resp = S3_TEST_OBJ.object_upload(
                BKT_OPS_CONF["test_8649"]["bucket_name"],
                objname,
                BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert resp[0], resp[1]
            object_list.append(objname)
        self.LOGGER.info("Multiple objects are uploaded")
        self.LOGGER.info("Listing all objects")
        resp = S3_TEST_OBJ.object_list(
            BKT_OPS_CONF["test_8649"]["bucket_name"])
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.LOGGER.info("All objects are listed")
        self.LOGGER.info("ENDED: List all objects in a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5448")
    @CTFailOn(error_handler)
    def test_2051(self):
        """Verification of disk usage by bucket."""
        self.LOGGER.info("STARTED: Verification of disk usage by bucket")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8650"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        create_file(
            BKT_OPS_CONF["bucket_workflow"]["file_path"],
            BKT_OPS_CONF["bucket_workflow"]["file_size"])
        self.LOGGER.info("Uploading multiple objects to a bucket")
        for count in range(BKT_OPS_CONF["test_8650"]["object_count"]):
            objname = "{0}{1}".format(
                BKT_OPS_CONF["test_8650"]["bucket_name"], str(count))
            retv = S3_TEST_OBJ.object_upload(
                BKT_OPS_CONF["test_8650"]["bucket_name"],
                objname,
                BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert retv[0], retv[1]
        self.LOGGER.info("Multiple objects are uploaded")
        self.LOGGER.info("Retrieving bucket size")
        resp = S3_TEST_OBJ.get_bucket_size(
            BKT_OPS_CONF["test_8650"]["bucket_name"])
        assert resp[0], resp[1]
        self.LOGGER.info("Retrieved bucket size")
        self.LOGGER.info("ENDED: Verification of disk usage by bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5453")
    def test_2055(self):
        """HEAD bucket when Bucket does not exists."""
        self.LOGGER.info("STARTED: HEAD bucket when Bucket does not exists")
        self.LOGGER.info("Performing head bucket on non existing bucket")
        try:
            S3_TEST_OBJ.head_bucket(BKT_OPS_CONF["test_8654"]["bucket_name"])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert BKT_OPS_CONF["test_8654"]["error_message"] in error.message, error.message
        self.LOGGER.info("Head bucket on non existing bucket is failed")
        self.LOGGER.info("ENDED: HEAD bucket when Bucket does not exists")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5445")
    @CTFailOn(error_handler)
    def test_2056(self):
        """Verify HEAD bucket."""
        self.LOGGER.info("STARTED: Verify HEAD bucket")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8655"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Bucket is created with name %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        self.LOGGER.info(
            "Performing head bucket on a bucket %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        resp = S3_TEST_OBJ.head_bucket(
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1]["BucketName"] == BKT_OPS_CONF["test_8655"]["bucket_name"], resp
        self.LOGGER.info(
            "Performed head bucket on a bucket %s",
            BKT_OPS_CONF["test_8655"]["bucket_name"])
        self.LOGGER.info("ENDED: Verify HEAD bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5446")
    @CTFailOn(error_handler)
    def test_2057(self):
        """Verify 'LIST buckets' command."""
        self.LOGGER.info("STARTED: Verify 'LIST buckets' command")
        self.LOGGER.info("Creating multiple buckets")
        bucket_list = []
        for count in range(BKT_OPS_CONF["test_8656"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                BKT_OPS_CONF["test_8656"]["bucket_name"], str(count))
            resp = S3_TEST_OBJ.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.LOGGER.info("Multiple buckets are created")
        self.LOGGER.info("Listing buckets")
        resp = S3_TEST_OBJ.bucket_list()
        assert resp[0], resp[1]
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        self.LOGGER.info("Buckets are listed")
        self.LOGGER.info("ENDED: Verify 'LIST buckets' command")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5450")
    @CTFailOn(error_handler)
    def test_2059(self):
        """Verification of bucket location."""
        self.LOGGER.info("STARTED: Verification of bucket location")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            BKT_OPS_CONF["test_8658"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            BKT_OPS_CONF["test_8658"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == BKT_OPS_CONF["test_8658"]["bucket_name"], resp[1]
        resp = S3_TEST_OBJ.bucket_location(
            BKT_OPS_CONF["test_8658"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1]["LocationConstraint"] == \
            BKT_OPS_CONF["test_8658"]["bucket_location"], resp[1]
        self.LOGGER.info("ENDED: Verification of bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8031")
    @CTFailOn(error_handler)
    def test_432(self):
        """Delete multiobjects which are present in bucket."""
        self.LOGGER.info(
            "STARTED: Delete multiobjects which are present in bucket")
        test_cfg = BKT_OPS_CONF["test_432"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_cnt = test_cfg["range"]
        self.LOGGER.info("Step 1: Creating a bucket and putting object")
        res = S3_TEST_OBJ.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(BKT_OPS_CONF["bucket_workflow"]["file_path"],
                    BKT_OPS_CONF["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(obj_cnt):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = S3_TEST_OBJ.put_object(
                bktname, obj, BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert res[0], res[1]
            obj_lst.append(obj)
        self.LOGGER.info("Step 1: Created bucket and object uploaded")
        self.LOGGER.info("Step 2: Listing all the objects")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.LOGGER.info("Step 2: All the objects listed")
        self.LOGGER.info("Step 3: Deleting all the object")
        resp = S3_TEST_OBJ.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        self.LOGGER.info("Step 3: All the objects deleted")
        self.LOGGER.info("Step 4: Check bucket is empty")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.LOGGER.info("Step 4: Verified that bucket was empty")
        self.LOGGER.info(
            "ENDED: Delete multiobjects which are present in bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8032")
    def test_433(self):
        """Delete multiobjects where the bucket is not present."""
        self.LOGGER.info(
            "STARTED: Delete multiobjects where the bucket is not present")
        test_cfg = BKT_OPS_CONF["test_433"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_lst = test_cfg["obj_lst"]
        self.LOGGER.info(
            "Step 1: Deleting the objects for non-existing bucket")
        try:
            S3_TEST_OBJ.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            self.LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            self.LOGGER.info(
                "Step 1: objects delete operation failed with error %s",
                test_cfg["err_message"])
        self.LOGGER.info("Step 2: List objects for non-existing bucket")
        try:
            S3_TEST_OBJ.object_list(bktname)
        except CTException as error:
            self.LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            self.LOGGER.info(
                "Step 2: List objects for non-existing bucket failed with error %s",
                test_cfg["err_message"])
        self.LOGGER.info(
            "ENDED: Delete multiobjects where the bucket is not present")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8033")
    def test_434(self):
        """
        create bucket and upload objects from account1.

         and dont give any permissions to account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        self.LOGGER.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        test_cfg = BKT_OPS_CONF["test_434"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        self.LOGGER.info(
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
        self.LOGGER.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.LOGGER.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = S3_TEST_OBJ.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(BKT_OPS_CONF["bucket_workflow"]["file_path"],
                    BKT_OPS_CONF["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(test_cfg["range"]):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = S3_TEST_OBJ.put_object(
                bktname, obj, BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert res[0], res[1]
            obj_lst.append(obj)
        self.LOGGER.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.LOGGER.info("Step 2: Listing all the objects using account 1")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.LOGGER.info("Step 2: All the objects listed using account 1")
        try:
            self.LOGGER.info("Step 3: Deleting all the object using account 2")
            s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            self.LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            self.LOGGER.info(
                "Step 3: deleting objects using account 2 failed with error %s",
                test_cfg["err_message"])
        self.LOGGER.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8035")
    @CTFailOn(error_handler)
    def test_435(self):
        """
        create bucket and upload objects from account1.

        and dont give any permissions to
        account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        self.LOGGER.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        test_cfg = BKT_OPS_CONF["test_435"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        self.LOGGER.info(
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
        self.LOGGER.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.LOGGER.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = S3_TEST_OBJ.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(BKT_OPS_CONF["bucket_workflow"]["file_path"],
                    BKT_OPS_CONF["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(test_cfg["range"]):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = S3_TEST_OBJ.put_object(
                bktname, obj, BKT_OPS_CONF["bucket_workflow"]["file_path"])
            assert res[0], res[1]
            obj_lst.append(obj)
        self.LOGGER.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.LOGGER.info("Step 2: Listing all the objects using account 1")
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.LOGGER.info("Step 2: All the objects listed using account 1")
        self.LOGGER.info(
            "Step 3: give full-control permissions for account2 for the bucket")
        resp = ACL_OBJ.put_bucket_acl(
            bktname, grant_full_control=test_cfg["id_str"].format(
                create_account[1]["canonical_id"]))
        assert resp[0], resp[1]
        self.LOGGER.info(
            "Step 3: Full-control permission was successfully assigned to account 2")
        self.LOGGER.info("Step 4: Deleting all the object using account 2")
        resp = s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        self.LOGGER.info("Step 4: All the objects deleted")
        self.LOGGER.info("Step 5: Check bucket is empty")
        ACL_OBJ.put_bucket_acl(
            bktname, acl=BKT_OPS_CONF["bucket_workflow"]["bkt_permission"])
        resp = S3_TEST_OBJ.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.LOGGER.info("Step 5: Verified that bucket was empty")
        resp = S3_TEST_OBJ.delete_bucket(bktname, force=True)
        assert resp[0], resp[1]
        self.LOGGER.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
