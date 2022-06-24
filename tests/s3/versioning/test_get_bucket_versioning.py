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
#

"""GET Bucket Versioning test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons.ct_fail_on import CTFailOn
from commons import error_messages as errmsg
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import create_s3_user_get_s3lib_object
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket

class TestGetBucketVersioning:
    """Test GET Bucket Versioning API"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """Function to perform setup prior to each test."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.rest_obj = S3AccountOperationsRestAPI()
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.user_name = "s3getbucketver-user-{}".format(time.perf_counter_ns())
        self.email_id = f"{self.user_name}_email@seagate.com"

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
        """Function to perform teardown after each test."""
        self.log.info("STARTED: Teardown operations")
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = []
        for bucket_name in res[1]:
            if bucket_name.startswith("ver-bkt"):
                empty_versioned_bucket(self.s3_ver_test_obj, bucket_name)
                pref_list.append(bucket_name)
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32715')
    @CTFailOn(error_handler)
    def test_get_bucket_versioning_unversioned_32715(self):
        """Verify bucket owner receives 200 OK when versioning is not enabled."""
        self.log.info("STARTED: Verify bucket owner response in unversioned bucket")
        self.log.info("Step 1: GET Bucket Versioning on created bucket")
        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_equal(200, res[1]['ResponseMetadata']['HTTPStatusCode'])
        assert_utils.assert_not_in('Status', res[1])
        self.log.info("ENDED: Verify bucket owner response in unversioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32716')
    @CTFailOn(error_handler)
    def test_get_bucket_versioning_enabled_suspended_32716(self):
        """Verify that bucket versioning status is not returned to non-owner user."""
        self.log.info("STARTED: Verify bucket versioning status is not returned to non-owner user")
        self.log.info("Prerequisite: New S3 account creation for non-owner user actions")
        s3_new_test_obj, _, _ = create_s3_user_get_s3lib_object(user_name=self.user_name,
                                                                email_id=self.email_id,
                                                                password=self.s3acc_password)
        self.log.info("Step 1: PUT Bucket Versioning with status=Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: GET Bucket Versioning by non bucket owner/user")
        try:
            res = s3_new_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
            assert_utils.assert_not_in('Status', res[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message, error.message)
        self.log.info("Step 3: PUT Bucket Versioning with status=Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 4: GET Bucket Versioning by non bucket owner/user")
        try:
            res = s3_new_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
            assert_utils.assert_not_in('Status', res[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message, error.message)
        self.log.info("Delete newly added user")
        resp = self.rest_obj.delete_s3_account(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Verify bucket versioning status is not returned to non-owner user")
