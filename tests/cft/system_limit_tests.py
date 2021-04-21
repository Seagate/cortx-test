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

import logging
import time

import pytest

from commons import configmanager
from commons.constants import Rest as Const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from config import CSM_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_bucket import RestS3BucketPolicy
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib

S3_TEST_OBJ = S3TestLib()
S3_MP_TEST_OBJ = S3MultipartTestLib()


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

    def create_csm_accounts(self, count):
        """
        Create new CSM user with Manager role
        :param count:
        :return:
        """
        csm_users = []
        for _ in range(count):
            self.log.info("Creating new CSM user...")
            res = self.csm_user_obj.create_and_verify_csm_user_creation(
                user_type="valid",
                user_role="manage",
                expect_status_code=Const.SUCCESS_STATUS_FOR_POST,
            )
            assert res, "Unable to create CSM account"
            self.log.info(f"Response : {self.csm_user_obj.recently_created_csm_user}")
            csm_users.append(self.csm_user_obj.recently_created_csm_user)
            self.log.info("CSM Manage user created ...")
        self.log.info(f"CSM Users created: {csm_users}")
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
            assert res.status_code == Const.SUCCESS_STATUS, \
                f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got {res.status_code}"
            s3_data = res.json()
            s3_block = {"account_name": s3_data["account_name"],
                        "access_key": s3_data["access_key"],
                        "secret_key": s3_data["secret_key"],
                        "canonical_id": s3_data["canonical_id"]}
            s3_users.append(s3_block)
            self.log.info("New S3 account created ... {}".format(s3_users))
        self.log.info("S3 Accounts created: {}".format(s3_users))
        return s3_users

    def create_iam_per_s3_account(self, count):
        """
        Create given number of IAMs per s3 account
        :param count: IAM counts
        :return: list of IAMs created
        """
        iam_users = []
        for s3_acc in self.created_s3_users:
            self.log.info(f"creating {count} IAMs for {s3_acc} s3 user")
            for _ in range(count):
                iam_user = self.iam_user_prefix + str(int(time.time()))
                password = self.s3_original_password
                self.log.info(f"Creating new iam user {iam_user}")
                # pylint: disable=C0302
                res = self.iam_user_obj.create_iam_user_under_given_account(
                    iam_user=iam_user, iam_password=password,
                    account_name=s3_acc["account_name"],
                    login_as={
                        "username": s3_acc["account_name"],
                        "password": password
                    })
                assert res.status_code == Const.SUCCESS_STATUS, \
                    f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got " \
                    f"{res.status_code}"
                iam_data = res.json()
                assert iam_data["user_name"] == iam_user, \
                    f"IM user name mismatch, expected {0} and got {1}".format(iam_user,
                                                                              iam_data["user_name"])

                iam_users.append(iam_data["user_name"])
        self.log.info(f"Total IAM Users created: {iam_users}")
        return iam_users

    def create_bucket_per_s3_account(self, count):
        """
        Create given number of buckets per s3 account
        :param count: bucket count
        :return: list of buckets created
        """
        buckets = []
        for s3_acc in self.created_s3_users:
            for _ in range(count):
                bucket_name = self.bucket_prefix + str(int(time.time()))
                self.log.info("Creating new S3 bucket...")
                res = self.s3_bucket_obj.create_s3_bucket_for_given_account(
                    bucket_name,
                    account_name=s3_acc["account_name"],
                    account_password=self.s3_original_password,
                )
                assert res.status_code == Const.SUCCESS_STATUS, \
                    f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got " \
                    f"{res.status_code}"
                bucket_data = res.json()
                buckets.append(bucket_data["bucket_name"])
        self.log.info(f"S3 Buckets created: {buckets}")
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
        assert len(self.created_csm_users) == csm_count, f"Created csm user count not matching"
        self.created_s3_users = self.create_s3_accounts(s3_count)
        assert len(self.created_s3_users) == s3_count, f"Created s3 user count not matching"
        self.created_iam_users = self.create_iam_per_s3_account(iam_count)
        assert len(
            self.created_iam_users) == iam_count * s3_count, f"Created iamuser count not matching"
        self.created_buckets = self.create_bucket_per_s3_account(bucket_count)
        assert len(
            self.created_buckets) == bucket_count * s3_count, f"Created bucket count not matching"

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
            if each['username'].startswith("test"):
                created_csm_users.append(each['username'])
        self.log.info(
            f"Total CSM accounts listed {len(created_csm_users)} : {created_csm_users}")
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
        self.log.info(
            f"Total S3 accounts listed {len(created_s3users)} :\n {created_s3users}")
        return created_s3users

    def get_iam_accounts(self, s3_account, s3_password):
        """
        Get list of IAM accounts for given s3 account
        :return: list of IAM account usernames
        """
        # pylint: disable=C0302
        response = self.iam_user_obj.list_iam_users_for_given_s3_user(
            user=s3_account,
            login_as={
                "username": s3_account,
                "password": s3_password
            })
        response = response.json()
        created_iam_users = []
        for each in response['iam_users']:
            if each['user_name'].startswith("test"):
                created_iam_users.append(each['user_name'])
        self.log.info(
            f"Total IAM accounts listed {len(created_iam_users)} : {created_iam_users}")
        return created_iam_users

    def get_buckets(self, s3_account, s3_password):
        """Get buckets for given s3 account"""
        # pylint: disable=C0302
        res = self.s3_bucket_obj.list_buckets_under_given_account(
            account_name=s3_account,
            login_as={
                "username": s3_account,
                "password": s3_password
            })
        buckets_in_s3 = []
        bucket_data = res.json()
        for buc in bucket_data["buckets"]:
            buckets_in_s3.append(buc["name"])

        self.log.info("Buckets of this S3 : {}".format(buckets_in_s3))
        return buckets_in_s3

    def destroy(self, s3_password):
        """
        Delete all csm, s3, IAM accounts and buckets
        """
        created_s3users = self.created_s3_users

        for s3_acc in created_s3users:
            s3 = s3_acc["account_name"]
            # Get all IAMs under S3 account
            iam_user_in_s3 = self.get_iam_accounts(s3, s3_password)

            # Get all buckets under S3 account
            buckets_in_s3 = self.get_buckets(s3, s3_password)

            # Delete all iam users from S3 account
            for iam in iam_user_in_s3:
                self.log.info("Deleting IMA user {}...".format(iam))
                # pylint: disable=C0302
                self.iam_user_obj.delete_iam_user_under_given_account(
                    iam_user=iam, account_name=s3,
                    login_as={
                        "username": s3,
                        "password": s3_password
                    })
            # Delete all buckets from S3 account
            for bucket in buckets_in_s3:
                self.log.info("Deleting S3 bucket {}...".format(bucket))
                # pylint: disable=C0302
                self.s3_bucket_obj.delete_given_s3_bucket(
                    bucket_name=bucket, account_name=s3,
                    login_as={
                        "username": s3,
                        "password": s3_password
                    })

            # Delete S3 account
            self.log.info(f"Deleting S3 account {s3}")
            # pylint: disable=C0302, E1123
            res = self.s3_account_obj.delete_s3_account_user(
                username=s3,
                login_as={
                    "username": s3,
                    "password": s3_password
                })
            assert res.status_code == Const.SUCCESS_STATUS, \
                f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got {res.status_code}"

        created_csm_users = self.created_csm_users
        for csm in created_csm_users:
            self.log.info("Deleting CSM user : {}".format(csm["username"]))
            res = self.csm_user_obj.delete_csm_user(csm["username"])
            assert res.status_code == Const.SUCCESS_STATUS, \
                f"Status code mismatch, expected {Const.SUCCESS_STATUS} and got {res.status_code}"
            self.log.info("CSM user with manage role {} deleted".format(csm["username"]))

        self.created_csm_users = []
        self.created_s3_users = []
        self.created_iam_users = []
        self.created_buckets = []
        return True

    def crud_operations_on_bucket(self, password, test):
        """
        Do CRUD operations on buckets
        """
        # List buckets for all s3 users
        created_s3users = self.created_s3_users
        assert len(created_s3users) >= self.cft_test_cfg[test]["s3_count"],\
            f"Created s3 user count != listed s3 user count "

        for s3_acc in created_s3users:
            s3 = s3_acc["account_name"]
            self.log.info(f"Listing new S3 buckets under {s3}")
            res = self.s3_bucket_obj.list_buckets_under_given_account(
                account_name=s3,
                login_as={
                    "username": s3,
                    "password": password
                })

            assert res.status_code == Const.SUCCESS_STATUS, \
                f"Status code mismatch while listing buckets, " \
                f"expected {Const.SUCCESS_STATUS} and got {res.status_code}"

            bucket_data = res.json()
            listed_buckets = bucket_data["buckets"]
            self.log.info(f"List of all S3 buckets under {s3} account is {listed_buckets}")

            assert len(listed_buckets) >= self.cft_test_cfg[test]["bucket_count"], \
                f"Created bucket count != listed bucket count for s3 user {s3}"

            for bucket in listed_buckets:
                s3_bucket_policy_obj = RestS3BucketPolicy(bucket["name"])
                # Create bucket policy for newly created bucket
                self.log.info("Creating new bucket policy...")
                # pylint: disable=C0302
                s3_bucket_policy_obj.create_bucket_policy_under_given_account(
                    account_name=s3,
                    login_as={
                        "username": s3,
                        "password": password
                    })

                # List bucket policy for newly created buckets
                self.log.info("Listing all bucket policy...")
                # pylint: disable=C0302
                s3_bucket_policy_obj.get_bucket_policy_under_given_account(
                    account_name=s3,
                    login_as={
                        "username": s3,
                        "password": password
                    })

                # Delete bucket policy for newly created buckets
                self.log.info("Deleting bucket policy...")
                # pylint: disable=C0302
                s3_bucket_policy_obj.delete_bucket_policy_under_given_name(
                    account_name=s3,
                    login_as={
                        "username": s3,
                        "password": password
                    })

    @pytest.mark.tags("TEST-13693")
    def test_13693(self):
        """
        For system limit of 498 s3 account
        Create 0 csm account, 498 s3 account,
        1 IAM user per s3 account, 1 bucket per s3 account
        """
        test = "test_13693"
        self.create(test)

        # list 498 s3 account
        created_s3users = self.get_created_s3_users()
        assert len(created_s3users) >= self.cft_test_cfg[test]["s3_count"],\
            f"Created s3 user count != listed s3 user count "

        # update 498 s3 account
        for s3_acc in self.created_s3_users:
            s3 = s3_acc["account_name"]
            self.log.info(f"Updating passwords for {s3} s3 accounts")
            # pylint: disable=C0302, E1123
            self.s3_account_obj.update_s3_user_password(
                username=s3, old_password=self.s3_original_password,
                new_password=self.new_password,
                login_as={
                    "username": s3,
                    "password": self.s3_original_password
                })
        # Delete everything
        self.destroy(s3_password=self.new_password)

    @pytest.mark.tags("TEST-16009")
    def test_16009(self):
        """
        For system limit of 500 IAM users per s3 account
        Create 0 csm account, 1 s3 account,
        500 IAM accounts per s3 account, 50 buckets per s3 account
        """
        test = "test_16009"
        self.create(test)

        # List a s3 accounts
        s3_accounts = self.created_s3_users
        assert len(s3_accounts) >= self.cft_test_cfg[test]["s3_count"], \
            f"Created s3 user count != listed s3 user count"

        for each_s3 in s3_accounts:
            s3 = each_s3["account_name"]
            self.log.info(f"Getting IAMs for {s3}")
            iam_account = self.get_iam_accounts(s3, self.s3_original_password)
            assert len(iam_account) >= self.cft_test_cfg[test]["iam_count"],\
                f"Created iam user count != listed iam user count for s3 user {s3}"

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.tags("TEST-16908")
    def test_16908(self):
        """
        For system limit of 1000 buckets per s3 account
        Create 0 csm account, 1 s3 account,
        5 IAM accounts per s3 account, 1000 buckets per s3 account
        """
        test = "test_16908"
        self.create(test)

        # Create, list and delete bucket policy
        self.crud_operations_on_bucket(password=self.s3_original_password, test=test)

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.tags("TEST-16909")
    def test_16909(self):
        """
        For system limit of 10k buckets
        Create 0 csm account, 100 s3 account,
        1 IAM accounts per s3 account, 100 buckets per s3 account
        """
        test = "test_16909"
        self.create(test)

        # Create, list and delete bucket policy
        self.crud_operations_on_bucket(password=self.s3_original_password, test=test)

        # Delete everything
        self.destroy(s3_password=self.s3_original_password)

    @pytest.mark.tags("TEST-16910")
    def test_16910(self):
        """
        For system limit of 1000 CSM users
        Create 1000 csm accounts
        """
        test = "test_16910"
        self.create(test)

        # List and update 1000 csm account
        created_csm_users = self.get_created_csm_users()
        assert len(created_csm_users) >= self.cft_test_cfg[test][
            "csm_count"], f"Created CSM user count != listed CSM user count "

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

    @pytest.mark.tags("TEST-16911")
    def test_16911(self):
        """
        Maximum number of Concurrent Management Users (100) logged in at given time
        """
        test = "test_16911"
        self.create(test)
        csm_users = self.get_created_csm_users()
        assert len(csm_users) >= self.cft_test_cfg[test]["csm_count"], \
            f"Created CSM user count != listed CSM user count "

        csm_user_headers = []

        # Login to 100 CSM users and collect authentication headers
        for csm_user in self.created_csm_users:
            csm = csm_user["username"]
            self.log.info(f"Getting authentication for {csm}")
            header = self.cms_rest_test_obj.get_headers(
                csm, self.csm_original_password)
            csm_user_headers.append(header)

        # Using authentication collected above, do management operation
        responses = []
        self.log.info("Logging in users")
        start = time.time()
        for i, header in enumerate(csm_user_headers):
            self.log.info(
                f"Operation for user #{i + 1} username {csm_users[i]} using {header}")
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
                self.log.error("List s3 user request failed.\n"
                               f"Response code : {response.status_code}")
                self.log.error(f"Response content: {response.content}")
                self.log.error(f"Request headers : {response.request.headers}\n"
                               f"Request body : {response.request.body}")

        assert failed_count == 0, "Unable to login into few accounts, see above errors."
        elapsed = end - start
        self.log.info(f"100 CSM requests took {elapsed} seconds")

        # Delete everything
        self.destroy(s3_password=self.csm_original_password)

    @pytest.mark.tags('TEST-20274')
    @CTFailOn(error_handler)
    def test_list_multipart_upload_20274(self):
        """List 1000 Multipart uploads."""
        test = "test_20274"
        bucket_name = "mp-bkt-test20274"
        object_name = "mp-obj-test20274"
        test_config = self.cft_test_cfg[test]
        self.log.info("Creating a bucket with name : %s", bucket_name)
        res = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)
        self.log.info("Initiating multipart uploads")
        mpu_ids = []
        for i in range(test_config["list_multipart_uploads_limit"]):
            res = S3_MP_TEST_OBJ.create_multipart_upload(bucket_name,
                                                         object_name+str(i))
            assert_utils.assert_true(res[0], res[1])
            mpu_id = res[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            mpu_ids.append(mpu_id)
        self.log.info("Listing multipart uploads")
        res = S3_MP_TEST_OBJ.list_multipart_uploads(bucket_name)
        for mpu_id in mpu_ids:
            assert_utils.assert_in(mpu_id, str(res[1]),
                                   f"mpu ID {mpu_id} is not present in {res[1]}")
        self.log.info("Test cleanup")
        self.log.info("Aborting multipart uploads")
        for i in range(test_config["list_multipart_uploads_limit"]):
            mpu_id = mpu_ids[i]
            res = S3_MP_TEST_OBJ.abort_multipart_upload(bucket_name,
                                                        object_name+str(i), mpu_id)
            assert_utils.assert_true(res[0], res[1])
        self.log.info("Aborted multipart upload")
        self.log.info("Deleting Bucket")
        resp = S3_TEST_OBJ.delete_bucket(bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted Bucket")
