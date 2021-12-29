#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

"""GET Object test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.cortxcli_test_lib import CSMAccountOperations


class TestGetBucketVersioning:
    """Test Get Object API with Object Versioning"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_obj = CSMAccountOperations()
        self.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.account_name = "s3getbucketversioning_user"
        self.email_id = f"{self.account_name}_email@seagate.com"

        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestGetBucketVersioning")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        """
        self.log.info("STARTED: Teardown operations")
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in res[1] if each_bucket.startswith("ver-bkt")]
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    def create_s3account(self):
        """Create s3 account"""
        resp = self.s3_obj.csm_user_create_s3account(
            self.account_name, self.email_id, self.s3acc_password)
        assert resp[0], resp[1]
        access_key = resp[1]['access_key']
        secret_key = resp[1]['secret_key']
        return access_key, secret_key

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32715')
    @CTFailOn(error_handler)
    def test_get_object_unversioned_32715(self):
        """Verify bucket owner received 200 ok when versioning is not enabled

        Create bucket.
        Perform GET Bucket Versioning on created bucket
        """
        self.log.info("STARTED: Verify bucket owner received 200 ok when versioning is not enabled")
        self.log.info("Step 1: GET Bucket Versioning on created bucket")
        res = self.s3_ver_test_obj.get_bucket_versioning(
            bucket_name=self.bucket_name)
        assert_utils.assert_equal(200, res[1]['ResponseMetadata']['HTTPStatusCode'])
        assert_utils.assert_not_in('Status', res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32716')
    @CTFailOn(error_handler)
    def test_get_object_enabled_suspended_32716(self):
        """Verify that bucket versioning status is not returned to non-owner user.

        Create bucket.
        PUT Bucket Versioning with status=Enabled
        Perform GET Bucket Versioning API by non bucket owner/user.
        PUT Bucket Versioning with status=Suspended
        Perform GET Bucket Versioning API by non bucket owner/user.
        """
        self.log.info("STARTED : Verify bucket versioning status is not returned to non-owner user")
        self.log.info("Prerequisite: New S3 account creation for non-owner user actions")
        access_key, secret_key = self.create_s3account()
        s3_new_test_obj = S3VersioningTestLib(
            access_key=access_key, secret_key=secret_key, endpoint_url=S3_CFG["s3_url"])
        err_message = "AccessDenied"
        self.log.info("Step 1: PUT Bucket Versioning with status=Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: GET Bucket Versioning by non bucket owner/user")
        try:
            res = s3_new_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
            self.log.info(res)
            assert_utils.assert_not_in('Status', res[1])
        except CTException as error:
            self.log.debug(res)
            assert err_message in error.message, error.message
        self.log.info("Step 3: PUT Bucket Versioning with status=Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 4: GET Bucket Versioning by non bucket owner/user")
        try:
            res = s3_new_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
            self.log.info(res)
            assert_utils.assert_not_in('Status', res[1])
        except CTException as error:
            self.log.debug(error.message)
            assert err_message in error.message, error.message
        self.log.info("ENDED : Delete newly added S3 Test account")
        resp = self.s3_obj.csm_user_delete_s3account(self.account_name)
        assert resp[0], resp[1]
