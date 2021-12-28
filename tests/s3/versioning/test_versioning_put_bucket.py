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

"""PUT bucket versioning test module for bucket Versioning."""

import logging
import os
import time
from collections import defaultdict
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from botocore.exceptions import ClientError
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib



class TestVersioningPutBucket:
    """Test PUT bucket versioning for Enabled/Suspended state."""

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningPutBucket")####
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        # file_name = "{0}{1}".format("ver_put_obj", time.perf_counter_ns())
        # self.file_path = os.path.join(self.test_dir_path, file_name)
        # create_file(fpath=self.file_path, count=1)
        # self.log.info("Created file: %s", self.file_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        #self.object_name = "ver-obj-{}".format(time.perf_counter_ns())
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
        self.log.info("Clean : %s", self.test_dir_path)
        if path_exists(self.file_path):
            res = remove_file(self.file_path)
            self.log.info("cleaned path: %s, res: %s", self.file_path, res)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in res[1] if each_bucket.startswith("ver-bkt")]
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32631')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled_32631(self):
        """
        Test PUT bucket versioning API for Enabling bucket versioning.

        Create bucket.
        Perform PUT bucket versioning API with status set to Enabled.
        Perform GET bucket versioning on bucket1.
        """
        self.log.info("STARTED: Test PUT bucket versioning API for Enabling bucket versioning")
        versions = defaultdict(list)
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Get bucket versioning status")
        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        http_code, status = res[1]['ResponseMetadata']['HTTPStatusCode'], res[1]['Status']
        self.log.info("HTTP status code: %s bucket versioning status: %s", http_code, status)
        assert_utils.assert_equal(http_code, 200)
        assert_utils.assert_equal(status, "Enabled")


    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32713')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_suspended_32713(self):
        """
        Test PUT Suspended bucket versioning.

        Create bucket.
        Perform PUT API to suspend the bucket versioning.
        Perform Get bucket versioning and validate the suspended versioning state of the bucket.
        """
        self.log.info("STARTED: Test PUT Suspended bucket versioning.")
        versions = defaultdict(list)
        self.log.info("Step 1: Suspend the bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Get bucket versioning status")
        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        http_code, status = res[1]['ResponseMetadata']['HTTPStatusCode'], res[1]['Status']
        self.log.info("HTTP status code: %s bucket versioning status: %s", http_code, status)
        assert_utils.assert_equal(http_code, 200)
        assert_utils.assert_equal(status, "Suspended")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32718')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_non_bucket_owner_32718(self):
        """
        Test PUT Enabled/Suspended bucket versioning by non bucket owner.

        Create bucket.
        Perform PUT API to Enable/Suspend the bucket versioning.
        Verify the response HTTP status 403 and error message: Access Denied.
        """
        self.log.info("STARTED: Creating new account.")
        versions = defaultdict(list)
        self.rest_obj = S3AccountOperations()
        account_name = "s3acc300-{}".format(time.perf_counter_ns())
        email_id = "s3acc300{}@gmail.com".format(time.perf_counter_ns())
        self.log.info("Step : Creating account with name %s and email_id %s",account_name, email_id)
        create_account = self.rest_obj.create_s3_account(
            account_name, email_id, "Cortxadmin@123")
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the account")
        self.s3_new_ver_test_obj = S3VersioningTestLib(access_key, secret_key, endpoint_url=S3_CFG["s3_url"], s3_cert_path=S3_CFG["s3_cert_path"],
            region=S3_CFG["region"])
        self.log.info("STARTED: PUT Enabled bucket versioning by non bucket owner.")
        res_code = self.s3_new_ver_test_obj.put_bucket_versioning_403(bucket_name=self.bucket_name, status="Enabled")
        assert_utils.assert_equal(res_code[1], 403)
        self.log.info("STARTED: PUT Suspended bucket versioning by non bucket owner.")
        res_code = self.s3_new_ver_test_obj.put_bucket_versioning_403(bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_equal(res_code[1], 403)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32719')
    @CTFailOn(error_handler)
    def test_put_invalid_bucket_versioning_32719(self):
        """
        Test PUT Disable bucket versioning.

        Create bucket.
        Perform PUT API to Disabled the bucket versioning.
        Verify the response HTTP status 400 and error message: Bad request.
        """
        self.log.info("STARTED: PUT Disabled bucket versioning.")
        versions = defaultdict(list)
        self.log.info("Step 1: Disable bucket versioning")
        try:
            self.s3_ver_test_obj.put_bucket_versioning(
                bucket_name=self.bucket_name, status="Disabled")
            #assert_utils.assert_equal(res_code[1], 400)
        except (ClientError, Exception) as error:
            self.log.info("Http error raised:::::: %s", error)
            self.log.info("response returned : %s", error.response)
            httpCode = error.response['ResponseMetadata']['HTTPStatusCode']
            self.log.info("HTTP status code returned : %s", httpCode)
            if httpCode == 400:
                self.log.info("Bad request, MalformedXML")
                pass
            else:
                self.log.error("Error in %s: %s",
                             S3VersioningTestLib.put_bucket_versioning.__name__,
                             error)
                raise CTException(err.S3_CLIENT_ERROR, error.args[0])




    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32747')
    @CTFailOn(error_handler)
    def test_put_unversioned_bucket_versioning_unversioned_bucket_32747(self):
        """
        Test PUT Unversion/Disable bucket versioning when versioning not set.

        Create bucket.
        Perform PUT API to Disabled/Unversioning the bucket versioning by non bucket owner.
        Perform PUT API to Disable/Unversioning the bucket versioning by bucket owner.
        """
        self.log.info("STARTED: Creating new account.")
        versions = defaultdict(list)
        self.rest_obj = S3AccountOperations()
        account_name = "s3acc300-{}".format(time.perf_counter_ns())
        email_id = "s3acc300{}@gmail.com".format(time.perf_counter_ns())
        self.log.info("Step : Creating account with name %s and email_id %s", account_name, email_id)
        create_account = self.rest_obj.create_s3_account(
            account_name, email_id, "Cortxadmin@123")
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the account")
        self.s3_new_ver_test_obj = S3VersioningTestLib(access_key, secret_key, endpoint_url=S3_CFG["s3_url"],
                                                       s3_cert_path=S3_CFG["s3_cert_path"],
                                                       region=S3_CFG["region"])
        self.log.info("STARTED: PUT Disabled bucket versioning by non bucket owner.")
        res_code = self.s3_new_ver_test_obj.put_bucket_versioning_403(bucket_name=self.bucket_name, status="Disabled")
        self.log.info(res_code[1])
        assert_utils.assert_equal(res_code[1], 403)
        self.log.info("STARTED: PUT Unversioned bucket versioning by  bucket owner.")
        res_code_new = self.s3_ver_test_obj.put_bucket_versioning_400(bucket_name=self.bucket_name, status="Unversioned")
        assert_utils.assert_equal(res_code_new[1], 400)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32749')
    @CTFailOn(error_handler)
    def test_put_unversioned_bucket_versioning_versioned_bucket_32749(self):
        """
        Test PUT Unversioned/Disable bucket versioning when versioning set Enabed/Suspended.

        Create bucket.
        Perform PUT Bucket Versioning API with status set to Enabled.
        Perform PUT bucket versioning API with status set to 'Unversioned/Disable' by non bucket owner/user.
        PUT Bucket Versioning with status=Unversioned/Disable as bucket owner.
        """
        self.log.info("STARTED: PUT Unversioned/Disable bucket versioning when versioning set Enabed/Suspended.")
        versions = defaultdict(list)
        self.log.info("Step 1: Perform PUT Bucket Versioning API with status set to Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("STARTED: Creating new account.")
        versions = defaultdict(list)
        self.rest_obj = S3AccountOperations()
        account_name = "s3acc300-{}".format(time.perf_counter_ns())
        email_id = "s3acc300{}@gmail.com".format(time.perf_counter_ns())
        self.log.info("Step : Creating account with name %s and email_id %s", account_name, email_id)
        create_account = self.rest_obj.create_s3_account(
            account_name, email_id, "Cortxadmin@123")
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.log.info("Step Successfully created the account")
        self.s3_new_ver_test_obj = S3VersioningTestLib(access_key, secret_key, endpoint_url=S3_CFG["s3_url"],
                                                       s3_cert_path=S3_CFG["s3_cert_path"],
                                                       region=S3_CFG["region"])
        self.log.info("STARTED: PUT Disabled bucket versioning by non bucket owner.")
        res_code = self.s3_new_ver_test_obj.put_bucket_versioning_403(bucket_name=self.bucket_name, status="Disabled")
        self.log.info(res_code[1])
        assert_utils.assert_equal(res_code[1], 403)
        self.log.info("STARTED: PUT Unversioned bucket versioning by  bucket owner.")
        res_code_new = self.s3_ver_test_obj.put_bucket_versioning_400(bucket_name=self.bucket_name,
                                                                      status="Unversioned")
        assert_utils.assert_equal(res_code_new[1], 400)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-33514')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled_deleted_bucket_33514(self):
        """
        Test PUT Enabled/Suspended bucket versioning when bucket is deleted.

        Create bucket.
        DELETE bucket bucket1.
        Perform PUT Bucket Versioning API with status set to 'Enabled/Suspended' by bucket owner.
        """
        self.log.info("STARTED: PUT Enabled/Suspended bucket versioning when bucket is deleted.")
        versions = defaultdict(list)

        self.log.info("Cleanup bucket test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in res[1] if each_bucket.startswith("ver-bkt")]
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

        self.log.info("Step 2: Perform PUT Bucket Versioning API with status set to Enabled")
        res_code = self.s3_ver_test_obj.put_bucket_versioning_404(bucket_name=self.bucket_name)
        assert_utils.assert_equal(res_code[1], 404)

        self.log.info("Step 2: Perform PUT Bucket Versioning API with status set to Suspended")
        res_code_new = self.s3_ver_test_obj.put_bucket_versioning_404(bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_equal(res_code_new[1], 404)
