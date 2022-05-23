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
"""System limit test suit."""

import json
import logging
import os
import random
import time
from datetime import datetime

import pytest

from commons import configmanager, Globals
from commons.constants import Rest as Const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_PATH, S3_BKT_TEST_CONFIG
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.assert_utils import assert_true
from config import CSM_CFG, CMN_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.s3 import iam_test_lib
from libs.s3.s3_bucket_policy_test_lib import S3BucketPolicyTestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib
from robot_gui.utils.call_robot_test import trigger_robot


# pylint: disable-msg=too-many-public-methods
class TestS3IOSystemLimits:
    """Class for system limit testing"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("System Limits  Test setup started...")

        cls.csm_conf = CSM_CFG
        cls.config = CSMConfigsCheck()
        cls.s3_original_password = cls.csm_conf["Restcall"]["test_s3account_password"]
        cls.csm_original_password = cls.csm_conf["Restcall"]["test_csmuser_password"]

        test_config = "config/cft/test_system_limit_tests.yaml"
        cls.cft_test_cfg = configmanager.get_config_wrapper(fpath=test_config)
        cls.S3_TEST_OBJ = S3TestLib()
        cls.S3_MP_TEST_OBJ = S3MultipartTestLib()

        cls.iam_user_prefix = cls.cft_test_cfg["system_limit_common"]["iam_user_prefix"]
        cls.bucket_prefix = cls.cft_test_cfg["system_limit_common"]["bucket_prefix"]
        cls.new_password = cls.cft_test_cfg["system_limit_common"]["new_password"]

        cls.created_csm_users = []
        cls.created_s3_users = []
        cls.created_iam_users = []
        cls.created_buckets = []
        cls.csm_user_obj = RestCsmUser()
        cls.s3_account_obj = RestS3user()
        cls.iam_user_obj = RestIamUser()
        cls.s3_bucket_obj = RestS3Bucket()
        cls.cms_rest_test_obj = RestTestLib()
        cls.test_dir_path = os.path.join(TEST_DATA_PATH, "LimitTest")
        cls.test_file = "testfile{}.txt"

        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.csm_url = "https://" + cls.mgmt_vip + "/#"
        cls.cwd = os.getcwd()
        cls.robot_gui_path = os.path.join(cls.cwd + '/robot_gui/')
        cls.robot_test_path = cls.robot_gui_path + 'testsuites/gui/.'
        cls.browser_type = 'chrome'
        cls.test_file_path = None

    def setup_method(self):
        """Create test data directory"""
        self.log.info("STARTED: Test Setup")
        if not system_utils.path_exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", resp)
        self.test_file_path = os.path.join(
            self.test_dir_path,
            self.test_file.format(str(int(time.time()))))

    def teardown_method(self):
        """Delete test data file"""
        self.log.info("STARTED: Test Teardown")
        if system_utils.path_exists(self.test_file_path):
            resp = system_utils.remove_file(self.test_file_path)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info(
                "removed path: %s, resp: %s",
                self.test_file_path,
                resp)

    def teardown_class(self):
        """Delete test data directory"""
        self.log.info("STARTED: Class Teardown")
        if system_utils.path_exists(self.test_dir_path):
            resp = system_utils.remove_dirs(self.test_dir_path)
            assert_utils.assert_true(resp, f"Unable to remove {self.test_dir_path}")
            self.log.info(
                "removed path: %s, resp: %s",
                self.test_dir_path,
                resp)

    def create_csm_accounts(self, count):
        """
        Create new CSM user with Manager role
        :param count:
        :return:
        """
        csm_users = []
        for _ in range(count):
            self.log.info("Creating new CSM user...")
            time.sleep(1)
            response = self.csm_user_obj.create_csm_user(user_type="valid", user_role="manage")
            self.log.info("Verifying if user was created successfully")
            assert response.status_code == Const.SUCCESS_STATUS_FOR_POST, \
                "Unable to create CSM account"
            self.log.info("Response : %s", self.csm_user_obj.recently_created_csm_user)
            csm_users.append(self.csm_user_obj.recently_created_csm_user)
            self.log.info("CSM Manage user created ...")
        self.log.info("CSM Users created: %s", csm_users)
        return csm_users

    def create_s3_accounts(self, count):
        """
        Create given number of S3 accounts
        :param count: S3 account count
        :return: list of S3 accounts created
        """
        s3_users = []
        for _ in range(count):
            self.log.info("Creating new S3 account...")
            res = self.s3_account_obj.create_s3_account()
            assert res.status_code == Const.SUCCESS_STATUS_FOR_POST, \
                f"Status code mismatch, expected {Const.SUCCESS_STATUS_FOR_POST} and " \
                f"got {res.status_code} "
            s3_data = res.json()
            s3_block = {"account_name": s3_data["account_name"],
                        "access_key": s3_data["access_key"],
                        "secret_key": s3_data["secret_key"],
                        "canonical_id": s3_data["canonical_id"]}
            s3_users.append(s3_block)
            self.log.info("New S3 account created ... %s", s3_users)
        self.log.info("S3 Accounts created: %s", s3_users)
        return s3_users

    def create_iam_per_s3_account(self, count):
        """
        Create given number of IAMs per s3 account
        :param count: IAM counts
        :return: list of IAMs created
        """
        iam_users = []
        for s3_acc in self.created_s3_users:
            self.log.info("creating %s IAMs for %s s3 user", count, s3_acc)
            for _ in range(count):
                iam_user = self.iam_user_prefix + str(int(time.time()))
                self.log.info("Creating new iam user %s", iam_user)
                iam_obj = iam_test_lib.IamTestLib(
                    access_key=s3_acc["access_key"],
                    secret_key=s3_acc["secret_key"])
                resp = iam_obj.create_user(iam_user)
                assert_true(resp[0], resp[1])
                iam_users.append(iam_user)
        self.log.info("Total IAM Users created: %s", iam_users)
        return iam_users

    def create_bucket_per_s3_account(self, count):
        """
        Create given number of buckets per s3 account
        :param count: bucket count
        :return: list of buckets created
        """
        buckets = []
        for s3_acc in self.created_s3_users:
            user = s3_acc['account_name']
            access = s3_acc['access_key']
            secret = s3_acc['secret_key']
            for num in range(count):
                s3_test_l = S3TestLib(access_key=access, secret_key=secret)
                bucket_name = f"{self.bucket_prefix}-{user}-{str(num)}"
                self.log.info("Creating new S3 bucket...")
                resp = s3_test_l.create_bucket(bucket_name)
                assert_utils.assert_true(resp[0], resp[1])
                buckets.append(resp[1])
                del s3_test_l
        self.log.info("S3 Buckets created: %s", buckets)
        return buckets

    def create(self, test):
        """
        Create given number of accounts and buckets
        :param test: test string from yaml file
        """
        test_cfg = self.cft_test_cfg[test]
        csm_count = test_cfg['csm_count']
        s3_count = test_cfg['s3_count']
        iam_count = test_cfg['iam_count']
        bucket_count = test_cfg['bucket_count']
        self.created_csm_users = self.create_csm_accounts(csm_count)
        assert len(self.created_csm_users) == csm_count, "Created csm user count not matching"
        self.created_s3_users = self.create_s3_accounts(s3_count)
        assert len(self.created_s3_users) == s3_count, "Created s3 user count not matching"
        self.created_iam_users = self.create_iam_per_s3_account(iam_count)
        assert len(
            self.created_iam_users) == iam_count * s3_count, "Created iamuser count not matching"
        self.created_buckets = self.create_bucket_per_s3_account(bucket_count)
        assert len(
            self.created_buckets) == bucket_count * s3_count, "Created bucket count not matching"

    def get_created_csm_users(self):
        """
        Get all csm users list whose name starts with test
        :return: list of users
        """
        rep = self.csm_user_obj.list_csm_users(
            expect_status_code=Const.SUCCESS_STATUS,
            return_actual_response=True)
        assert rep, f"Could not get list of CSM users from REST APIs {rep}"
        response = rep.json()
        created_csm_users = []
        for each in response['users']:
            if each['username'].startswith("csm"):
                created_csm_users.append(each['username'])
        self.log.info("Total CSM accounts listed %s : %s",
                      len(created_csm_users), created_csm_users)
        return created_csm_users

    def get_created_s3_users(self):
        """
        Get all S3 users list whose name starts with test
        :return: list of s3 users
        """
        response = self.s3_account_obj.list_all_created_s3account()
        assert response.status_code == Const.SUCCESS_STATUS, f"List account Response is " \
                                                             f"{response.status_code}. Expected " \
                                                             f"it to be {Const.SUCCESS_STATUS}"
        response = response.json()
        created_s3users = []
        for each in response['s3_accounts']:
            if each['account_name'].startswith("test"):
                created_s3users.append(each['account_name'])
        self.log.info("Total S3 accounts listed %s :\n %s", len(created_s3users), created_s3users)
        return created_s3users

    def get_iam_accounts(self, access, secret):
        """
        Get list of IAM accounts for given s3 account
        :return: list of IAM account usernames
        """
        iam_obj = iam_test_lib.IamTestLib(
            access_key=access,
            secret_key=secret)
        all_users = iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        created_iam_users = [user["UserName"]
                             for user in all_users if
                             "test" in user["UserName"]]
        self.log.info("Total IAM accounts listed %s : %s",
                      len(created_iam_users), created_iam_users)
        return created_iam_users

    def get_buckets(self, access, secret):
        """Get buckets for given s3 account"""
        s3_test_lib = S3TestLib(access_key=access, secret_key=secret)
        resp = s3_test_lib.bucket_list()
        buckets_in_s3 = []
        for bucket_name in resp[1]:
            buckets_in_s3.append(bucket_name)
        del s3_test_lib
        self.log.info("Buckets of this S3 : %s", buckets_in_s3)
        return buckets_in_s3

    def destroy(self, s3_password):
        """
        Delete all csm, s3, IAM accounts and buckets
        """
        created_s3users = self.created_s3_users

        for s3_acc in created_s3users:
            s3_name = s3_acc["account_name"]
            access = s3_acc["access_key"]
            secret = s3_acc["secret_key"]
            # Get all IAMs under S3 account
            iam_user_in_s3 = self.get_iam_accounts(access, secret)

            # Get all buckets under S3 account
            buckets_in_s3 = self.get_buckets(access, secret)

            # Delete all iam users from S3 account
            for iam in iam_user_in_s3:
                self.log.info("Deleting IMA user %s...", iam)
                iam_obj = iam_test_lib.IamTestLib(
                    access_key=s3_acc["access_key"],
                    secret_key=s3_acc["secret_key"])
                iam_obj.delete_user(iam)
                del iam_obj

            # Delete all buckets from S3 account
            s3_test_l = S3TestLib(access_key=access, secret_key=secret)
            s3_test_l.delete_multiple_buckets(buckets_in_s3)

            # Delete S3 account
            self.log.info("Deleting S3 account %s", s3_name)
            # pylint: disable=C0302, E1123
            res = self.s3_account_obj.delete_s3_account_user(
                username=s3_name,
                login_as={
                    "username": s3_name,
                    "password": s3_password
                })
            assert res.status_code == Const.SUCCESS_STATUS, \
                f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got {res.status_code}"

        created_csm_users = self.created_csm_users
        for csm in created_csm_users:
            self.log.info("Deleting CSM user : %s", csm["username"])
            res = self.csm_user_obj.delete_csm_user(csm["username"])
            assert res.status_code == Const.SUCCESS_STATUS, \
                f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got {res.status_code}"
            self.log.info("CSM user with manage role %s deleted", csm["username"])

        self.created_csm_users = []
        self.created_s3_users = []
        self.created_iam_users = []
        self.created_buckets = []
        return True

    def crud_operations_on_bucket(self, test):
        """
        Do CRUD operations on buckets
        """
        # List buckets for all s3 users
        created_s3users = self.created_s3_users
        assert len(created_s3users) >= self.cft_test_cfg[test]["s3_count"], \
            "Created s3 user count != listed s3 user count "

        for s3_acc in created_s3users:
            s3_name = s3_acc["account_name"]
            access = s3_acc["access_key"]
            secret = s3_acc["secret_key"]
            self.log.info("Listing new S3 buckets under %s", s3_name)
            # Get all buckets under S3 account
            listed_buckets = self.get_buckets(access, secret)

            self.log.info("List of all S3 buckets under %s account is %s", s3_name, listed_buckets)

            assert len(listed_buckets) >= self.cft_test_cfg[test]["bucket_count"], \
                f"Created bucket count != listed bucket count for s3 user {s3_name}"

            for bucket in listed_buckets:
                # Create bucket policy for newly created bucket
                self.log.info("Creating new bucket policy for bucket %s...", bucket)
                bkt_policy_conf = configmanager.get_config_wrapper(fpath=S3_BKT_TEST_CONFIG)
                bucket_policy = bkt_policy_conf["test_1182"]["bucket_policy"]
                self.log.debug("Original bucket_policy %s...", bucket_policy)
                bucket_policy["Statement"][0]["Resource"] = \
                    bucket_policy["Statement"][0]["Resource"].format(bucket)
                self.log.debug("Modified bucket_policy %s...", bucket_policy)
                s3_bkt_policy = S3BucketPolicyTestLib(access, secret)
                bkt_policy_json = json.dumps(bucket_policy)
                self.log.info("Applying json policy %s", bkt_policy_json)
                # Apply bucket policy
                self.log.info("Applying policy to a bucket %s", bucket)
                resp = s3_bkt_policy.put_bucket_policy(bucket, bkt_policy_json)
                assert resp[0], resp[1]
                self.log.info("Policy is applied to a bucket %s", bucket)
                # Retrieving bucket policy
                self.log.info("Retrieving policy of a bucket %s", bucket)
                resp = s3_bkt_policy.get_bucket_policy(bucket)
                assert_utils.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
                self.log.info("Retrieved policy of a bucket %s", bucket)
                # Delete bucket policy
                self.log.info("Deleting bucket policy...")
                s3_bkt_policy.delete_bucket_policy(bucket)

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-13693")
    def test_13693(self):
        """
        For system limit of s3 account
        Create 0 csm account, max s3 account,
        1 IAM user per s3 account, 1 bucket per s3 account
        """
        test = "test_13693"

        response = self.s3_account_obj.list_all_created_s3account()
        assert response.status_code == Const.SUCCESS_STATUS, f"List account Response is " \
                                                             f"{response.status_code}. Expected " \
                                                             f"it to be {Const.SUCCESS_STATUS}"
        s3_accounts = response.json()['s3_accounts']
        assert len(s3_accounts) == 0, f"The system already has s3 accounts present: {s3_accounts}"

        self.create(test)

        # ToDo: Create one extra S3 account and verify limit response is 403
        # https://seagate-systems.atlassian.net/wiki/spaces/PRIVATECOR/pages/238485708/S3+Accounts+and+IAM+User+Management

        # list all s3 account
        created_s3users = self.get_created_s3_users()
        assert len(created_s3users) >= self.cft_test_cfg[test]["s3_count"], \
            "Created s3 user count != listed s3 user count "

        # update all s3 account
        for s3_acc in self.created_s3_users:
            s3_name = s3_acc["account_name"]
            self.log.info("Updating passwords for %s s3 accounts", s3_name)
            # pylint: disable=C0302, E1123
            self.s3_account_obj.update_s3_user_password(
                username=s3_name, old_password=self.s3_original_password,
                new_password=self.new_password,
                login_as={
                    "username": s3_name,
                    "password": self.s3_original_password
                })
        # Delete everything
        self.destroy(s3_password=self.new_password)

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-16009")
    def test_16009(self):
        """
        For system limit of max IAM users per s3 account
        Create 0 csm account, 1 s3 account,
        max IAM accounts per s3 account, 50 buckets per s3 account
        """
        test = "test_16009"
        self.create(test)

        # ToDo: Create one extra IAM user and verify limit response is 403
        # https://seagate-systems.atlassian.net/wiki/spaces/PRIVATECOR/pages/238485708/S3+Accounts+and+IAM+User+Management

        # List a s3 accounts
        s3_accounts = self.created_s3_users
        assert len(s3_accounts) >= self.cft_test_cfg[test]["s3_count"], \
            "Created s3 user count != listed s3 user count"

        for each_s3 in s3_accounts:
            s3_name = each_s3["account_name"]
            access = each_s3["access_key"]
            secret = each_s3["secret_key"]
            self.log.info("Getting IAMs for %s", s3_name)
            iam_account = self.get_iam_accounts(access, secret)
            assert len(iam_account) >= self.cft_test_cfg[test]["iam_count"], \
                f"Created iam user count != listed iam user count for s3 user {s3_name}"

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-16908")
    def test_16908(self):
        """
        For system limit of max buckets per s3 account
        Create 0 csm account, 1 s3 account,
        5 IAM accounts per s3 account, max buckets per s3 account
        """
        test = "test_16908"
        self.create(test)

        # Create, list and delete bucket policy
        self.crud_operations_on_bucket(test=test)

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-16909")
    def test_16909(self):
        """
        For system limit of max buckets
        Create 0 csm account, 100 s3 account,
        1 IAM accounts per s3 account, 100 buckets per s3 account
        """
        test = "test_16909"
        self.create(test)

        # Create, list and delete bucket policy
        self.crud_operations_on_bucket(test=test)

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-16910")
    def test_16910(self):
        """
        For system limit of max CSM users
        Create max csm accounts
        """
        test = "test_16910"
        self.create(test)

        # List and update max csm account
        created_csm_users = self.get_created_csm_users()
        assert len(created_csm_users) >= self.cft_test_cfg[test]["csm_count"], \
            "Created CSM user count != listed CSM user count "

        for account_name in self.created_csm_users:
            csm = account_name["username"]
            # pylint: disable=C0302
            self.csm_user_obj.update_csm_account_password(
                username=csm, old_password=self.csm_original_password,
                new_password=self.new_password,
                login_as={
                    "username": csm,
                    "password": self.csm_original_password
                })

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-16911")
    def test_16911(self):
        """
        Maximum number of Concurrent Management Users (100) logged in at given time
        """
        test = "test_16911"
        self.create(test)
        csm_users = self.get_created_csm_users()
        assert len(csm_users) >= self.cft_test_cfg[test]["csm_count"], \
            "Created CSM user count != listed CSM user count "

        csm_user_headers = []

        # Login to 100 CSM users and collect authentication headers
        for csm_user in self.created_csm_users:
            csm = csm_user["username"]
            self.log.info("Getting authentication for %s", csm)
            header = self.cms_rest_test_obj.get_headers(
                csm, self.csm_original_password)
            csm_user_headers.append(header)

        # Using authentication collected above, do management operation
        responses = []
        self.log.info("Logging in users")
        start = time.time()
        for i, header in enumerate(csm_user_headers):
            self.log.info("Operation for user %s username %s using %s", i + 1, csm_users[i], header)
            response = self.csm_user_obj.restapi.rest_call(
                request_type="get",
                endpoint=self.csm_conf["Restcall"]["s3accounts_endpoint"],
                headers=header)
            responses.append(response)
        end = time.time()

        # Verify responses from server
        failed_count = 0
        for response in responses:
            if Const.SUCCESS_STATUS != response.status_code:
                failed_count += 1
                self.log.error("List s3 user request failed.\nResponse code : %s",
                               response.status_code)
                self.log.error("Response content: %s", response.content)
                self.log.error("Request headers : %s\n Request body : %s",
                               response.request.headers, response.request.body)

        assert failed_count == 0, "Unable to login into few accounts, see above errors."
        elapsed = end - start
        self.log.info("100 CSM requests took %s seconds", elapsed)

        # Delete everything
        self.destroy(s3_password=self.csm_original_password)

    @pytest.mark.scalability
    @pytest.mark.tags('TEST-20274')
    @CTFailOn(error_handler)
    def test_list_multipart_upload_20274(self):
        """List 1000 Multipart uploads."""
        test = "test_20274"
        bucket_name = "mp-bkt-test20274"
        object_name = "mp-obj-test20274"
        test_config = self.cft_test_cfg[test]
        self.log.info("Creating a bucket with name : %s", bucket_name)
        res = self.S3_TEST_OBJ.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)
        self.log.info("Initiating multipart uploads")
        mpu_ids = []
        for i in range(test_config["list_multipart_uploads_limit"]):
            res = self.S3_MP_TEST_OBJ.create_multipart_upload(bucket_name,
                                                              object_name + str(i))
            assert_utils.assert_true(res[0], res[1])
            mpu_id = res[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            mpu_ids.append(mpu_id)
        self.log.info("Listing multipart uploads")
        res = self.S3_MP_TEST_OBJ.list_multipart_uploads(bucket_name)
        for mpu_id in mpu_ids:
            assert_utils.assert_in(mpu_id, str(res[1]),
                                   f"mpu ID {mpu_id} is not present in {res[1]}")
        self.log.info("Test cleanup")
        self.log.info("Aborting multipart uploads")
        for i in range(test_config["list_multipart_uploads_limit"]):
            mpu_id = mpu_ids[i]
            res = self.S3_MP_TEST_OBJ.abort_multipart_upload(bucket_name,
                                                             object_name + str(i), mpu_id)
            assert_utils.assert_true(res[0], res[1])
        self.log.info("Aborted multipart upload")
        self.log.info("Deleting Bucket")
        resp = self.S3_TEST_OBJ.delete_bucket(bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted Bucket")

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-20271")
    @CTFailOn(error_handler)
    def test_object_user_metadata_limit_20271(self):
        """Tests user metadata limit for an object"""
        test = "test_20271"
        test_config = self.cft_test_cfg[test]
        bucket_name = f"mp-bkt-test{str(int(time.time()))}"
        metadata_limit = test_config["metadata_limit"]
        res = self.S3_TEST_OBJ.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Bucket is created: %s", bucket_name)

        metadata_size = [random.SystemRandom().randint(500, metadata_limit - 1),
                         metadata_limit,
                         random.SystemRandom().randint(metadata_limit + 1, 4000)]
        for metadata in metadata_size:
            object_name = f"mp-obj-test20271{metadata}"
            m_key = system_utils.random_string_generator(10)
            m_value = system_utils.random_string_generator(metadata - 10)

            obj_size = random.SystemRandom().randint(5, 20)

            self.log.info("Creating a object: %s size: %s", object_name, obj_size)
            self.log.info("Metadata m_key: %s m_value: %s", m_key, m_value)
            system_utils.create_file(self.test_file_path, obj_size)
            try:
                res = self.S3_TEST_OBJ.put_object(bucket_name, object_name, self.test_file_path,
                                                  m_key=m_key, m_value=m_value)
            except CTException as error:
                if metadata > metadata_limit:
                    self.log.info(error.message)
                    assert_utils.assert_in("MetadataTooLarge", error.message, error.message)
                else:
                    self.log.error("Unable to upload object even if metadata size is %s < %s",
                                   metadata, metadata_limit)
                    assert_utils.assert_true(False, res[1])
            else:
                if metadata <= metadata_limit:
                    assert_utils.assert_true(res[0], res[1])
                    self.log.info("Object is uploaded: %s", object_name)
                    self.log.info("Doing Head object: %s", object_name)
                    res = self.S3_TEST_OBJ.object_info(bucket_name, object_name)
                    assert_utils.assert_true(res[0], res[1])
                    assert_utils.assert_in("Metadata", res[1], res[1])
                    assert_utils.assert_in(m_key.lower(), res[1]["Metadata"], res[1]["Metadata"])
                    assert_utils.assert_equals(m_value,
                                               res[1]["Metadata"][m_key.lower()],
                                               res[1]["Metadata"][m_key.lower()])
                else:
                    self.log.error("Could not see exception while uploading object with metadata "
                                   "size of %s > %s", metadata, metadata_limit)
                    assert_utils.assert_true(False, res[1])

        self.log.info("Deleting bucket %s", bucket_name)
        res = self.S3_TEST_OBJ.delete_bucket(bucket_name, True)
        assert_utils.assert_true(res[0], res[1])

    def verify_max_part_limit(self, bucket, obj_name):
        """
        Verify max part size limit
            Initiate new multipart upload and get the upload ID.
            Create a file of 5.1GB
            Upload the file as first part and expect error EntityTooLarge
            Cancel multipart upload if present
        """
        self.log.info("Verifying maximum part size limit")
        self.log.info("Initiating multipart uploads")
        res = self.S3_MP_TEST_OBJ.create_multipart_upload(bucket, obj_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Creating a object: %s size > 5GiB", obj_name)
        system_utils.create_file(self.test_file_path, 5121, "/dev/urandom", '1M')
        with open(self.test_file_path, "rb") as file_pointer:
            data = file_pointer.read()
        self.log.info("Uploading part 1 of length %s", str(len(data)))
        try:
            response = self.S3_MP_TEST_OBJ.upload_part(
                data, bucket, obj_name, upload_id=mpu_id, part_number=1)
        except CTException as error:
            self.log.error("%s", error)
            assert_utils.assert_in("EntityTooLarge", error.message, error.message)
        else:
            self.log.error("Response = %s", response)
            assert_utils.assert_true(False, "Could not catch exception while uploading "
                                            "part of size > 5GiB")
        self.log.info("Aborting multipart upload")
        res = self.S3_MP_TEST_OBJ.abort_multipart_upload(bucket, obj_name, mpu_id)
        assert_utils.assert_true(res[0], res[1])

    def verify_min_part_limit(self, bucket, obj_name):
        """
        Verify min part size limit
            Initiate new multipart upload and get the upload ID.
            Create a file of 4MB, upload the file as first part
            Upload the same 4MB file as second part
            Complete multipart upload, and expect error EntityTooSmall
            Cancel multipart upload if present
        """
        self.log.info("Verifying minimum part size limit")
        self.log.info("Initiating multipart uploads")
        res = self.S3_MP_TEST_OBJ.create_multipart_upload(bucket, obj_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        parts = []
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Creating a object: %s size < 5MiB", obj_name)
        system_utils.create_file(self.test_file_path, 4, "/dev/urandom", '1M')
        with open(self.test_file_path, "rb") as file_pointer:
            data = file_pointer.read()
        self.log.info("Uploading part 1 of length %s", str(len(data)))
        response = self.S3_MP_TEST_OBJ.upload_part(
            data, bucket, obj_name, upload_id=mpu_id, part_number=1)
        assert_utils.assert_true(response[0], response[1])
        parts.append({"PartNumber": 1, "ETag": response[1]["ETag"]})
        self.log.info("Uploading part 2 of length %s", str(len(data)))
        response = self.S3_MP_TEST_OBJ.upload_part(
            data, bucket, obj_name, upload_id=mpu_id, part_number=2)
        assert_utils.assert_true(response[0], response[1])
        parts.append({"PartNumber": 2, "ETag": response[1]["ETag"]})
        try:
            response = self.S3_MP_TEST_OBJ.complete_multipart_upload(mpu_id, parts, bucket,
                                                                     obj_name)
        except CTException as error:
            self.log.info("error : %s", error)
            assert_utils.assert_in("EntityTooSmall", error.message, error.message)
        else:
            self.log.error("Response = %s", response)
            assert_utils.assert_true(False, "Could not catch exception while completing multipart "
                                            "upload with first part size of 4MB")
        self.log.info("Aborting multipart upload")
        res = self.S3_MP_TEST_OBJ.abort_multipart_upload(bucket, obj_name, mpu_id)
        assert_utils.assert_true(res[0], res[1])

    def verify_actual_limit(self, bucket, obj_name):
        """
        Verify actual part limits
            Create a file of 5GiB, upload the file as first part.
            Create a file of 5MiB, upload the file as second part.
            Complete multipart upload without any error.
        """
        parts = []
        self.log.info("Verifying actual part size limit")
        self.log.info("Initiating multipart uploads")
        res = self.S3_MP_TEST_OBJ.create_multipart_upload(bucket, obj_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Creating a object: %s size 5GiB", obj_name)
        system_utils.create_file(self.test_file_path, 5120, "/dev/urandom", '1M')
        with open(self.test_file_path, "rb") as file_pointer:
            data = file_pointer.read()
        self.log.info("Uploading part 1 of length %s", str(len(data)))
        response = self.S3_MP_TEST_OBJ.upload_part(
            data, bucket, obj_name, upload_id=mpu_id, part_number=1)
        assert_utils.assert_true(response[0], response[1])
        parts.append({"PartNumber": 1, "ETag": response[1]["ETag"]})
        self.log.info("Creating a object: %s size 5MiB", obj_name)
        system_utils.create_file(self.test_file_path, 5, "/dev/urandom", '1M')
        with open(self.test_file_path, "rb") as file_pointer:
            data = file_pointer.read()
        self.log.info("Uploading part 2 of length %s", str(len(data)))
        response = self.S3_MP_TEST_OBJ.upload_part(
            data, bucket, obj_name, upload_id=mpu_id, part_number=2)
        assert_utils.assert_true(response[0], response[1])
        parts.append({"PartNumber": 2, "ETag": response[1]["ETag"]})
        response = self.S3_MP_TEST_OBJ.complete_multipart_upload(mpu_id, parts,
                                                                 bucket, obj_name)
        assert_utils.assert_true(response[0], response[1])
        self.log.info("Multipart upload with part 1 of 5GiB and part 2 of 5MiB is successful.")

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-20273")
    @CTFailOn(error_handler)
    def test_max_min_part_limit_20273(self):
        """Test maximum and minimum part limit for multipart"""
        bucket_name = f"mp-bkt-test20273-{int(time.time())}"
        self.log.info("Creating a bucket with name : %s", bucket_name)
        res = self.S3_TEST_OBJ.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)

        # Verify maximum part size limit
        self.verify_max_part_limit(bucket_name, 'large')
        # Verify minimum part size limit
        self.verify_min_part_limit(bucket_name, 'small')
        # Verify actual part limits
        self.verify_actual_limit(bucket_name, 'large-object')

        self.log.info("Deleting bucket %s", bucket_name)
        res = self.S3_TEST_OBJ.delete_bucket(bucket_name, True)
        assert_utils.assert_true(res[0], res[1])

    @pytest.mark.csm_gui
    @pytest.mark.scalability
    @pytest.mark.tags("TEST-25351")
    @CTFailOn(error_handler)
    def test_csm_iam_limit(self):
        """Test CSM GUI for maximum number of IAM users"""
        test = "test_16009"
        self.create(test)
        s3_account = self.created_s3_users[0]["account_name"]

        # Create one extra IAM user and verify limit response is 403
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'create_last_iam_user_verify_popup_' + \
                               "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + str(s3_account),
                                'password:' + str(self.s3_original_password),
                                'RESOURCES:' + self.robot_gui_path]
        gui_dict['test'] = 'CREATE_LAST_IAM_USER_VERIFY_POPUP'
        gui_response = trigger_robot(gui_dict)
        assert_utils.assert_true(gui_response, 'GUI FAILED')

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)
