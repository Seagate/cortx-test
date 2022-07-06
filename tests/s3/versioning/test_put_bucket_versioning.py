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

"""PUT Bucket Versioning test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons import error_messages as errmsg
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.cortxcli_test_lib import CSMAccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import create_s3_user_get_s3lib_object
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket

class TestPutBucketVersioning:
    """Test PUT Bucket Versioning API"""

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
        self.user_name = "s3putbucketver-user-{}".format(time.perf_counter_ns())
        self.email_id = f"{self.user_name}_email@seagate.com"

        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestPutBucketVersioning")
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
        self.log.info("Clean: %s", self.test_dir_path)
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

    @pytest.mark.sanity
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32631')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled_32631(self):
        """ Test PUT bucket versioning API for Enabling bucket versioning. """
        self.log.info("STARTED: Test PUT bucket versioning API for Enabling bucket versioning")
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Get bucket versioning status")
        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1]['Status'], "Enabled")
        self.log.info("ENDED: Test PUT bucket versioning API for Enabling bucket versioning")

    @pytest.mark.sanity
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32713')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_suspended_32713(self):
        """ Test PUT Suspended bucket versioning. """
        self.log.info("STARTED: Test PUT Suspended bucket versioning.")
        self.log.info("Step 1: Suspend the bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Get bucket versioning status")
        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1]['Status'], "Suspended")
        self.log.info("ENDED: Test PUT Suspended bucket versioning.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32718')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_non_bucket_owner_32718(self):
        """ Test PUT Enabled/Suspended bucket versioning by non bucket owner. """
        self.log.info("STARTED: PUT Enabled/Suspended bucket versioning by non bucket owner")
        s3_new_test_obj, _, _ = create_s3_user_get_s3lib_object(user_name=self.user_name,
                                                                email_id=self.email_id,
                                                                password=self.s3acc_password)
        try:
            self.log.info("Step 1: PUT Enabled bucket versioning by non bucket owner.")
            res = s3_new_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Enabled")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify Access Denied error with Enabled bucket versioning")
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Enabled")
        try:
            self.log.info("Step 2: PUT Suspended bucket versioning by non bucket owner.")
            res = s3_new_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Suspended")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify Access Denied error with Suspended bucket versioning")
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Suspended")
        self.log.info("ENDED: PUT Enabled/Suspended bucket versioning by non bucket owner")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32719')
    @CTFailOn(error_handler)
    def test_put_invalid_bucket_versioning_32719(self):
        """ Test PUT invalid(Disabled) bucket versioning. """
        try:
            self.log.info("STARTED: PUT Disabled bucket versioning.")
            self.log.info("Step 1: Disable bucket versioning")
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status="Disabled")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Step 2: Verify InvalidArgument error with Disabled bucket versioning")
            assert_utils.assert_in(errmsg.INVALID_ARG_ERR, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Disabled")
        self.log.info("ENDED: PUT Disabled bucket versioning.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32747')
    @CTFailOn(error_handler)
    def test_put_unversioned_bucket_versioning_unversioned_bucket_32747(self):
        """ Test PUT Unversioned/Disable bucket versioning when versioning not set. """
        self.log.info("STARTED: PUT Disabled bucket versioning by non bucket owner.")
        s3_new_test_obj, _, _ = create_s3_user_get_s3lib_object(user_name=self.user_name,
                                                                email_id=self.email_id,
                                                                password=self.s3acc_password)
        try:
            self.log.info("Step 1: PUT Disabled bucket versioning by non bucket owner.")
            res = s3_new_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Disabled")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify Access Denied error with Suspended bucket versioning")
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Disabled")
        try:
            self.log.info("Step 2: PUT Unversioned bucket versioning by bucket owner.")
            res = s3_new_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Unversioned")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify AccessDenied error with Unversioned bucket versioning")
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Unversioned by bucket owner")
        self.log.info("ENDED: PUT Disabled bucket versioning by non bucket owner.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32749')
    @CTFailOn(error_handler)
    def test_put_unversioned_bucket_versioning_versioned_bucket_32749(self):
        """
        Test PUT Unversioned/Disable bucket versioning when versioning set Enabed/Suspended.
        """
        self.log.info("STARTED: PUT Unversioned/Disabled bucket versioning when versioning set"
                      " Enabed/Suspended.")
        self.log.info("Step 1: Perform PUT Bucket Versioning API with status set to Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Creating new account.")
        s3_new_test_obj, _, _ = create_s3_user_get_s3lib_object(user_name=self.user_name,
                                                                email_id=self.email_id,
                                                                password=self.s3acc_password)
        try:
            self.log.info("Step 2: PUT Disabled bucket versioning by non bucket owner.")
            res = s3_new_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Disabled")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify Access Denied error with Disabled bucket versioning")
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Disabled by non "
                          "bucket owner")
        try:
            self.log.info("Step 3: PUT Unversioned bucket versioning by  bucket owner.")
            res = s3_new_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Unversioned")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify AccessDenied error with Unversioned bucket versioning")
            assert_utils.assert_in(errmsg.ACCESS_DENIED_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be "
                          "Unversioned by bucket owner")
        self.log.info("ENDED: PUT Unversioned/Disabled bucket versioning when versioning set "
                      "Enabed/Suspended.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-33514')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled_deleted_bucket_33514(self):
        """ Test PUT Enabled/Suspended bucket versioning when bucket is deleted. """
        self.log.info("STARTED: PUT Enabled/Suspended bucket versioning when bucket is deleted.")
        self.log.info("Step 1: Deleting bucket: %s", self.bucket_name)
        res = self.s3_test_obj.delete_bucket(self.bucket_name, True)
        assert_utils.assert_true(res[0], res[1])
        try:
            self.log.info("Step 2: Perform PUT Bucket Versioning API with status set to Enabled")
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify NoSuchBucket error with Enabled bucket versioning")
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Enabled for deleted bucket")
        try:
            self.log.info("Step 3: Perform PUT Bucket Versioning API with status set to Suspended")
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status="Suspended")
            assert_utils.assert_false(res[0], res[1])
        except CTException as error:
            self.log.info("Verify NoSuchBucket error with Suspended bucket versioning")
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, error.message)
            self.log.error("Error message: %s", error)
            self.log.info("Verified that bucket versioning can not be Suspended for deleted "
                          "bucket")
        self.log.info("ENDED: PUT Enabled/Suspended bucket versioning when bucket is deleted.")
