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

"""Bucket Workflow Operations Test Module."""

import logging
import os
import random
import time
import secrets

import pytest

from commons import error_messages as errmsg
from commons.constants import S3_ENGINE_RGW
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.s3_utils import assert_s3_err_msg
from config import S3_CFG, CMN_CFG
from libs.s3 import s3_acl_test_lib
from libs.s3 import s3_test_lib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


# pylint: disable=too-many-instance-attributes
# pylint: disable-msg=too-many-public-methods
class TestBucketWorkflowOperations:
    """Bucket Workflow Operations Test suite."""

    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup(self):
        """Function to perform the setup ops for each test."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup test operations.")
        self.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.acl_obj = s3_acl_test_lib.S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        self.bucket_name = "bktwrkflow1-{}".format(time.perf_counter_ns())
        self.account_name = "bktwrkflowaccnt{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.folder_path = os.path.join(TEST_DATA_FOLDER, "TestBucketWorkflowOperations")
        self.filename = "bkt_workflow{}.txt".format(time.perf_counter_ns())
        self.file_path = os.path.join(self.folder_path, self.filename)
        if not system_utils.path_exists(self.folder_path):
            system_utils.make_dirs(self.folder_path)
        self.rest_obj = S3AccountOperations()
        self.system_random = secrets.SystemRandom()
        self.account_list = []
        self.bucket_list = []
        self.log.info("ENDED: Setup test operations")
        yield
        self.log.info("STARTED: Cleanup test operations.")
        bucket_list = self.s3_test_obj.bucket_list()[1]
        for bucket_name in self.bucket_list:
            if bucket_name in bucket_list:
                resp = self.s3_test_obj.delete_bucket(bucket_name, force=True)
                assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Account list: %s", self.account_list)
        for acc in self.account_list:
            self.rest_obj.delete_s3_account(acc)
        self.log.info("ENDED: Setup test operations.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5463")
    @CTFailOn(error_handler)
    def test_name_lowercase_letters_1975(self):
        """Bucket names must start with a lowercase letter or number."""
        self.log.info(
            "STARTED: Bucket names must start with a lowercase letter or number")
        bkt_name_list = ["bktworkflow", "8535-bktworkflow"]
        for bkt_name in bkt_name_list:
            self.log.info(
                "Creating a bucket with lowercase letter or starts with number  is %s",
                bkt_name)
            resp = self.s3_test_obj.create_bucket(
                bkt_name)
            assert resp[0], resp[1]
            assert resp[1] == bkt_name, resp[1]
            self.log.info(
                "Bucket is created with lowercase letter or starts with number: %s",
                bkt_name)
            self.bucket_list.append(bkt_name)
        self.log.info(
            "ENDED: Bucket names must start with a lowercase letter or number")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5469")
    @CTFailOn(error_handler)
    def test_name_constains_alphanumeric_1976(self):
        """Bucket name can contain only lower-case characters, numbers, periods and dashes."""
        self.log.info(
            "STARTED: Bucket name can contain only lower-case chars, numbers, periods and dashes")
        self.log.info(
            "Creating a bucket with lower case, number, periods, dashes")
        bkt_name = "bktworkflow-8536.bkt"
        resp = self.s3_test_obj.create_bucket(
            bkt_name)
        assert resp[0], resp[1]
        assert resp[1] == bkt_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            bkt_name)
        self.bucket_list.append(bkt_name)
        self.log.info(
            "ENDED: Bucket name can contain only lower-case characters, "
            "numbers, periods and dashes")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5467")
    @CTFailOn(error_handler)
    def test_bucketname_2to63_chars_long_1977(self):
        """Bucket names must be at least 3 and no more than 63 characters long."""
        self.log.info(
            "STARTED: Bucket names must be at least 3 and no more than 63 characters long")
        bkt_name3 = "bkt"
        bkt_name63 = "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbuckets"
        self.log.info(
            "Creating a bucket with at least 3 characters is : %s",
            bkt_name3)
        resp = self.s3_test_obj.create_bucket(
            bkt_name3)
        assert resp[0], resp[1]
        assert resp[1] == bkt_name3, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            bkt_name3)
        self.log.info(
            "Creating a bucket with name  63 chars long is : %s",
            bkt_name63)
        resp = self.s3_test_obj.create_bucket(
            bkt_name63)
        assert resp[0], resp[1]
        assert resp[1] == bkt_name63, resp[1]
        self.log.info(
            "Created a bucket with name 63 characters long is : %s",
            bkt_name63)
        self.log.info("Cleanup activity")
        self.bucket_list.append(bkt_name3)
        self.bucket_list.append(bkt_name63)
        self.log.info(
            "ENDED: Bucket names must be at least 3 and no more than 63 characters long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5468")
    @CTFailOn(error_handler)
    def test_name_lessthan3chars_morethan63chars_1978(self):
        """Bucket name with less than 3 characters and more than 63 characters."""
        self.log.info(
            "STARTED: Bucket name with less than 3 characters and more than 63 characters")
        self.log.info(
            "Creating buckets with name less than 3 and more than 63 character length")
        bkt_name2_64 = [
            "a2",
            "bktworkflow-seagateeosbucket-8537-bktworkflow-seagateeosbucketsbktworkflow"
            "-seagateeosbucket"]
        for each_bucket in bkt_name2_64:
            try:
                resp = self.s3_test_obj.create_bucket(each_bucket)
                assert_utils.assert_false(resp[0], resp[1])
                self.bucket_list.append(each_bucket)
            except CTException as error:
                self.log.info(error.message)
                assert errmsg.S3_BKT_INVALID_NAME_ERR in error.message, error.message
        self.log.info(
            "Creating buckets with name less than 3 and more than 63 characters length is failed")
        self.log.info(
            "ENDED: Bucket name with less than 3 characters and more than 63 characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5464")
    @CTFailOn(error_handler)
    def test_name_nouppercase_1979(self):
        """Bucket names must not contain uppercase characters."""
        self.log.info(
            "STARTED: Bucket names must not contain uppercase characters")
        bkt_upper = "BKTWORKFLOW"
        self.log.info(
            "Creating a bucket with name : %s",
            bkt_upper)
        try:
            resp = self.s3_test_obj.create_bucket(bkt_upper)
            assert_utils.assert_false(resp[0], resp[1])
            self.bucket_list.append(bkt_upper)
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.S3_BKT_INVALID_NAME_ERR in error.message, error.message
        self.log.info("Creating a bucket with uppercase letters is failed")
        self.log.info(
            "ENDED: Bucket names must not contain uppercase characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5465")
    @CTFailOn(error_handler)
    def test_name_with_underscores_1980(self):
        """Bucket names must not contain underscores."""
        self.log.info("STARTED: Bucket names must not contain underscores")
        bkt_name = "bktworkflow_8540{}".format(time.perf_counter_ns())
        self.log.info(
            "Creating a bucket with underscore is : %s",
            bkt_name)
        try:
            resp = self.s3_test_obj.create_bucket(bkt_name)
            assert_utils.assert_false(resp[0], resp[1])
            self.account_list.append(bkt_name)
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.S3_BKT_INVALID_NAME_ERR in error.message, error.message
        self.log.info("Creating a bucket with underscore is failed")
        self.log.info("ENDED: Bucket names must not contain underscores")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5462")
    @CTFailOn(error_handler)
    def test_name_special_characters_1981(self):
        """Bucket names with special characters."""
        self.log.info("STARTED: Bucket names with special characters")
        count_limit = self.system_random.randrange(4,10)
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
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
            self.account_list.append(bucket_name)
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.S3_BKT_SPECIAL_CHARACTER_ERR in error.message, error.message
        self.log.info("Creating a bucket with special characters is failed")
        self.log.info("ENDED: Bucket names with special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5466")
    @CTFailOn(error_handler)
    def test_name_formatting_1982(self):
        """Bucket names must not be formatted as an IP address (for example, 192.168.5.4)."""
        self.log.info(
            "STARTED: Bucket names must not be formatted as an IP address(for eg., 192.168.5.4)")
        bkt_name_ip = "192.168.10.20"
        self.log.info("Creating a bucket with name : %s",
                      bkt_name_ip)
        try:
            resp = self.s3_test_obj.create_bucket(bkt_name_ip)
            assert_utils.assert_false(resp[0], resp[1])
            self.account_list.append(bkt_name_ip)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_INVALID_NAME_ERR in error.message, error.message
        self.log.info("Creating a bucket with an IP address format is failed")
        self.log.info(
            "ENDED: Bucket names must not be formatted as an IP address "
            "(for example, 192.168.5.4)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5459")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2039(self):
        """Create single bucket."""
        self.log.info("STARTED: Create single bucket")
        self.log.info(
            "Creating single Bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Verifying that bucket is created")
        resp = self.s3_test_obj.bucket_list()
        assert resp[0], resp[1]
        assert self.bucket_name in resp[1]
        self.bucket_list.append(self.bucket_name)
        self.log.info("Verified that bucket is created")
        self.log.info("ENDED: Creating single Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5460")
    @CTFailOn(error_handler)
    def test_create_multiple_buckets_2040(self):
        """Create 10 multiple buckets."""
        self.log.info("STARTED: Create 10 multiple buckets")
        self.log.info("Creating multiple buckets")
        bucket_list = []
        for each in range(10):
            bucket_name = "{0}{1}".format(
                "bktworkflow-8639", each)
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Created multiple buckets")
        self.log.info("Verifying that buckets are created")
        resp = self.s3_test_obj.bucket_list()
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
            self.bucket_list.append(each_bucket)
        self.log.info("Verified that buckets are created")
        self.log.info("ENDED: Create 10 multiple buckets")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5461")
    @CTFailOn(error_handler)
    def test_duplicate_name_2043(self):
        """Create bucket with same bucket name already present."""
        self.log.info(
            "STARTED: Create bucket with same bucket name already present")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Creating a bucket with existing bucket name")
        try:
            resp = self.s3_test_obj.create_bucket(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error.message)
            assert_s3_err_msg(errmsg.RGW_ERR_DUPLICATE_BKT_NAME,
                              errmsg.CORTX_ERR_DUPLICATE_BKT_NAME,
                              CMN_CFG["s3_engine"], error)
        self.log.info("Creating a bucket with existing bucket name is failed")
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Create bucket with same bucket name already present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5447")
    @CTFailOn(error_handler)
    def test_max_bucket_creation_2044(self):
        """Verification of max. 100 no. of buckets user can create."""
        self.log.info(
            "STARTED: Verification of max. 100 no. of buckets user can create")
        self.log.info("Creating 100 max buckets")
        resp1 = self.s3_test_obj.bucket_count()
        self.log.info(resp1)
        bkt_list = []
        for each in range(100):
            bucket_name = "{0}{1}".format("bktworkflow-8643-", each)
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            bkt_list.append(bucket_name)
        self.log.info("Created 100 buckets")
        self.log.info("Verifying that bucket is created")
        resp = self.s3_test_obj.bucket_count()
        self.log.info(resp)
        assert resp[0], resp[1]
        assert_utils.assert_equal(
            len(bkt_list), 100, "failed to create 100 buckets")
        resp = self.s3_test_obj.delete_multiple_buckets(bkt_list)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp1[1])
        self.log.info("Verified that buckets are created")
        self.log.info(
            "ENDED: Verification of max. 100 no. of buckets user can create")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5457")
    @CTFailOn(error_handler)
    def test_delete_bucket_with_objects_2045(self):
        """Delete bucket which has objects."""
        self.log.info("STARTED: Delete bucket which has objects")
        self.log.info(
            "Creating a Bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading an objects to a bucket")
        for i in range(5):
            objname = "{0}{1}".format(
                "object", i)
            resp = self.s3_test_obj.object_upload(
                self.bucket_name,
                objname,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Objects are uploaded to a bucket")
        self.log.info("Deleting a bucket having objects")
        try:
            resp = self.s3_test_obj.delete_bucket(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.S3_BKT_NOT_EMPTY_ERR in error.message, error.message
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Delete bucket which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5458")
    @CTFailOn(error_handler)
    def test_forcefully_delete_objects_2046(self):
        """Delete bucket forcefully which has objects."""
        self.log.info("STARTED: Delete bucket forcefully which has objects")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading multiple objects to a bucket")
        for obj_cnt in range(5):
            objname = "obj{}".format(obj_cnt)
            resp = self.s3_test_obj.object_upload(
                self.bucket_name,
                objname,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Multiple objects are uploaded to a bucket")
        self.log.info("Forcefully deleting bucket having object")
        resp = self.s3_test_obj.delete_bucket(
            self.bucket_name, force=True)
        assert resp[0], resp[1]
        self.log.info("Forcefully deleted a bucket")
        self.log.info("ENDED: Delete bucket forcefully which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5455")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2047(self):
        """Delete empty bucket."""
        self.log.info("STARTED: Delete empty bucket")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Deleting a bucket")
        retv = self.s3_test_obj.delete_bucket(
            self.bucket_name)
        assert retv[0], retv[1]
        self.log.info("Bucket is deleted")
        self.log.info("ENDED: Delete empty bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5454")
    @CTFailOn(error_handler)
    def test_delete_multiple_buckets_2048(self):
        """Delete multiple empty buckets."""
        self.log.info("STARTED: Delete multiple empty buckets")
        self.log.info("Creating multiple buckets")
        bucket_list = []
        for count in range(10):
            bucket_name = "{0}{1}".format(
                "bktworkflow-8647-", str(count))
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        assert_utils.assert_equal(
            len(bucket_list),
            10,
            "Failed to create 10 bucket: {}".format(bucket_list))
        self.log.info("Multiple buckets are created")
        self.log.info("Deleting multiple buckets")
        resp = self.s3_test_obj.delete_multiple_buckets(bucket_list)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Multiple buckets are deleted")
        self.log.info("ENDED: Delete multiple empty buckets")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5456")
    @CTFailOn(error_handler)
    def test_delete_non_existing_bucket_2049(self):
        """Delete bucket when Bucket does not exists."""
        self.log.info("STARTED: Delete bucket when Bucket does not exists")
        self.log.info("Deleting bucket which does not exists on s3 server")
        try:
            resp = self.s3_test_obj.delete_bucket(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in error.message, error.message
        self.log.info("Deleting bucket which does not exists on s3 server is failed")
        self.log.info("ENDED: Delete bucket which does not exists on s3 server")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5452")
    @CTFailOn(error_handler)
    def test_list_all_buckets_2050(self):
        """List all objects in a bucket."""
        self.log.info("STARTED: List all objects in a bucket")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading multiple objects to a bucket")
        object_list = []
        for count in range(5):
            objname = "obj2050{}".format(count)
            resp = self.s3_test_obj.object_upload(
                self.bucket_name,
                objname,
                self.file_path)
            assert resp[0], resp[1]
            object_list.append(objname)
        self.log.info("Multiple objects are uploaded")
        self.log.info("Listing all objects")
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.log.info("All objects are listed")
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: List all objects in a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5448")
    @CTFailOn(error_handler)
    def test_disk_usages_verification_2051(self):
        """Verification of disk usage by bucket."""
        self.log.info("STARTED: Verification of disk usage by bucket")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        system_utils.create_file(
            self.file_path,
            10)
        self.log.info("Uploading multiple objects to a bucket")
        for count in range(5):
            objname = "obj2051{}".format(count)
            retv = self.s3_test_obj.object_upload(
                self.bucket_name,
                objname,
                self.file_path)
            assert retv[0], retv[1]
        self.log.info("Multiple objects are uploaded")
        self.log.info("Retrieving bucket size")
        resp = self.s3_test_obj.get_bucket_size(
            self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved bucket size")
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Verification of disk usage by bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5453")
    @CTFailOn(error_handler)
    def test_head_non_existing_bucket_2055(self):
        """HEAD bucket when Bucket does not exists."""
        self.log.info("STARTED: HEAD bucket when Bucket does not exists")
        self.log.info("Performing head bucket on non existing bucket")
        try:
            resp = self.s3_test_obj.head_bucket(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
            self.bucket_list.append(self.bucket_name)
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.NOT_FOUND_ERR in error.message, error.message
        self.log.info("Head bucket on non existing bucket is failed")
        self.log.info("ENDED: HEAD bucket when Bucket does not exists")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5445")
    @CTFailOn(error_handler)
    def test_verify_head_bucket_2056(self):
        """Verify HEAD bucket."""
        self.log.info("STARTED: Verify HEAD bucket")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info(
            "Performing head bucket on a bucket %s",
            self.bucket_name)
        resp = self.s3_test_obj.head_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1]["BucketName"] == self.bucket_name, resp
        self.log.info(
            "Performed head bucket on a bucket %s",
            self.bucket_name)
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Verify HEAD bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
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
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        self.log.info("Multiple buckets are created")
        self.log.info("Listing buckets")
        resp = self.s3_test_obj.bucket_list()
        assert resp[0], resp[1]
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        self.log.info("Buckets are listed")
        resp = self.s3_test_obj.delete_multiple_buckets(bucket_list)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Verify 'LIST buckets' command")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-5450")
    @CTFailOn(error_handler)
    def test_bucket_location_verification_2059(self):
        """Verification of bucket location."""
        self.log.info("STARTED: Verification of bucket location")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        resp = self.s3_test_obj.bucket_location(
            self.bucket_name)
        assert resp[0], resp[1]
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            assert resp[1]["LocationConstraint"] == "default", resp[1]
        else:
            assert resp[1]["LocationConstraint"] == "us-west-2", resp[1]
        self.bucket_list.append(self.bucket_name)
        self.log.info("ENDED: Verification of bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-8031")
    @CTFailOn(error_handler)
    def test_delete_multiobjects_432(self):
        """Delete multiobjects which are present in bucket."""
        self.log.info(
            "STARTED: Delete multiobjects which are present in bucket")
        self.log.info("Step 1: Creating a bucket and putting object")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert res[1] == self.bucket_name, res[1]
        system_utils.create_file(self.file_path,
                                 10)
        obj_lst = []
        for i in range(10):
            obj = "{}{}".format("testobj432", str(i))
            res = self.s3_test_obj.put_object(
                self.bucket_name, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info("Step 1: Created bucket and object uploaded")
        self.log.info("Step 2: Listing all the objects")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed")
        self.log.info("Step 3: Deleting all the object")
        resp = self.s3_test_obj.delete_multiple_objects(self.bucket_name, obj_lst)
        assert resp[0], resp[1]
        self.log.info("Step 3: All the objects deleted")
        self.log.info("Step 4: Check bucket is empty")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.log.info("Step 4: Verified that bucket was empty")
        self.bucket_list.append(self.bucket_name)
        self.log.info(
            "ENDED: Delete multiobjects which are present in bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-8032")
    @CTFailOn(error_handler)
    def test_delete_non_existing_multibuckets_433(self):
        """Delete multiobjects where the bucket is not present."""
        self.log.info("STARTED: Delete multiobjects where the bucket is not present")
        obj_lst = ["obj1", "obj2"]
        self.log.info("Step 1: Deleting the objects for non-existing bucket")
        try:
            resp = self.s3_test_obj.delete_multiple_objects(
                self.bucket_name, obj_lst)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: objects delete operation failed with error %s",
                "NoSuchBucket")
        self.log.info("Step 2: List objects for non-existing bucket")
        try:
            resp = self.s3_test_obj.object_list(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: List objects for non-existing bucket failed with "
                "error %s", "NoSuchBucket")
        self.log.info(
            "ENDED: Delete multiobjects where the bucket is not present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-8033")
    @CTFailOn(error_handler)
    def test_delete_object_without_permission_434(self):
        """
        create bucket and upload objects from account1.

         and dont give any permissions to account2 and delete multiple objects from account2
        """
        self.log.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        self.log.info("Step : Creating account with name %s and email_id %s",
            self.account_name, self.email_id)
        create_account = self.rest_obj.create_s3_account(
            acc_name=self.account_name,
            email_id=self.email_id,
            passwd=self.s3acc_password)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.account_list.append(self.account_name)
        self.log.info("Step Successfully created the cortxcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert res[1] == self.bucket_name, res[1]
        system_utils.create_file(self.file_path,
                                 10)
        obj_lst = []
        for i in range(10):
            obj = "{}{}".format("testobj434", str(i))
            res = self.s3_test_obj.put_object(
                self.bucket_name, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.log.info("Step 2: Listing all the objects using account 1")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed using account 1")
        try:
            self.log.info("Step 3: Deleting all the object using account 2")
            resp = s3_obj_2.delete_multiple_objects(self.bucket_name, obj_lst)
            assert_utils.assert_false(resp[0], res[1])
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: deleting objects using account 2 failed with error %s",
                "AccessDenied")
        self.account_list.append(self.account_name)
        self.log.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_ops
    @pytest.mark.tags("TEST-8035")
    @CTFailOn(error_handler)
    def test_delete_multiple_objects_without_permission_435(self):
        """
        create bucket and upload objects from account1.

        and don't give any permissions to
        account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        self.log.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            self.account_name, self.email_id)
        create_account = self.rest_obj.create_s3_account(
            acc_name=self.account_name,
            email_id=self.email_id,
            passwd=self.s3acc_password)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.account_list.append(self.account_name)
        self.log.info("Step Successfully created the cortxcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert res[1] == self.bucket_name, res[1]
        system_utils.create_file(self.file_path,
                                 10)
        obj_lst = []
        for i in range(10):
            obj = "{}{}".format("testobj435", str(i))
            res = self.s3_test_obj.put_object(
                self.bucket_name, obj, self.file_path)
            assert res[0], res[1]
            obj_lst.append(obj)
        self.log.info(
            "Step 1: Created bucket and object uploaded in account 1")
        self.log.info("Step 2: Listing all the objects using account 1")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        self.log.info("Step 2: All the objects listed using account 1")
        self.log.info(
            "Step 3: give full-control permissions for account2 for the bucket")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, grant_full_control="id={}".format(
                create_account[1]["canonical_id"]))
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Full-control permission was successfully assigned to account 2")
        self.log.info("Step 4: Deleting all the object using account 2")
        resp = s3_obj_2.delete_multiple_objects(self.bucket_name, obj_lst)
        assert resp[0], resp[1]
        self.log.info("Step 4: All the objects deleted")
        self.log.info("Step 5: Check bucket is empty")
        self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="private")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        self.log.info("Step 5: Verified that bucket was empty")
        resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
        assert resp[0], resp[1]
        self.account_list.append(self.account_name)
        self.log.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
