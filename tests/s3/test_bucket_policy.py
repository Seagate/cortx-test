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

"""This file contains test related to Bucket Policy."""

import os
import json
import uuid
import time
import logging
import pytest

from datetime import date
from datetime import datetime
from datetime import timedelta
from commons import error_messages as errmsg
from commons.constants import S3_ENGINE_RGW
from commons.params import TEST_DATA_FOLDER
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils import system_utils
from config.s3 import S3_BKT_TST as BKT_POLICY_CONF
from config import S3_CFG, CMN_CFG
from libs.s3 import s3_bucket_policy_test_lib
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib
from libs.s3 import s3_tagging_test_lib
from libs.s3 import s3_multipart_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


class TestBucketPolicy:
    """Bucket Policy test suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Setup method.

        Description: This function will be invoked prior to each test case. It will perform all
        prerequisite test steps if any. Initializing common variable which will be used in test and
        teardown for cleanup.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Test setup operations.")
        self.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.iam_obj = iam_test_lib.IamTestLib(endpoint_url=S3_CFG["iam_url"])
        self.acl_obj = s3_acl_test_lib.S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        self.no_auth_obj = s3_test_lib.S3LibNoAuth(endpoint_url=S3_CFG["s3_url"])
        self.s3_tag_obj = s3_tagging_test_lib.S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_mp_obj = s3_multipart_test_lib.S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_bkt_policy_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.account_list = []
        self.iam_obj_list = []
        self.s3t_obj_list = []
        self.obj_name_prefix = "obj_policy"
        self.acc_name_prefix = "acc1policy"
        self.user_name = "userpolicy_user_{}".format(time.perf_counter_ns())
        self.bucket_name = "bktpolicy-{}".format(time.perf_counter_ns())
        self.object_name = "objpolicy-{}".format(time.perf_counter_ns())
        self.account_name = "accpolicy_{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.account_name_1 = "accpolicy_one{}".format(time.perf_counter_ns())
        self.email_id_1 = "{}@seagate.com".format(self.account_name_1)
        self.account_name_2 = "accpolicy_two{}".format(time.perf_counter_ns())
        self.email_id_2 = "{}@seagate.com".format(self.account_name_2)
        self.rest_obj = S3AccountOperations()
        self.s3test_obj_1 = None
        self.folder_path = os.path.join(TEST_DATA_FOLDER, "TestBucketPolicy")
        if not system_utils.path_exists(self.folder_path):
            system_utils.make_dirs(self.folder_path)
        self.log.info("Test data path: %s", self.folder_path)
        self.file_path = os.path.join(
            self.folder_path, "bkt_policy{}.txt".format(time.perf_counter_ns()))
        self.file_path_1 = os.path.join(
            self.folder_path, "bkt1_policy{}.txt".format(time.perf_counter_ns()))
        self.file_path_2 = os.path.join(
            self.folder_path, "bkt2_policy{}.txt".format(time.perf_counter_ns()))
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.log.info("ENDED: Test setup operations.")
        yield
        self.log.info("STARTED: Test teardown operations.")
        self.s3t_obj_list.append(self.s3test_obj_1)  # To remove the resources created in tests.
        for fpath in [self.file_path, self.file_path_1, self.file_path_2]:
            if system_utils.path_exists(fpath):
                system_utils.remove_file(fpath)
        self.log.info("Deleting all buckets/objects created during TC execution.")
        self.delete_bucket_and_verify()
        bucket_list = self.s3_obj.bucket_list()[1]
        if self.bucket_name in bucket_list:
            self.acl_obj.put_bucket_acl(self.bucket_name, acl="private")
            resp = self.s3_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("All the buckets/objects deleted successfully")
        self.delete_accounts(self.account_list)
        del self.rest_obj
        self.log.info("ENDED: Test teardown operations.")

    def delete_accounts(self, accounts):
        """It will clean up resources which are getting created during test suite setup."""
        for iam in self.iam_obj_list:
            iam_users = [user["UserName"] for user in iam.list_users()[1]]
            self.log.info("Deleting iam users '%s' and access keys", iam_users)
            resp = iam.delete_users_with_access_key(iam_users)
            assert_utils.assert_true(resp, f"Failed to delete iam useres: {iam_users}")
        iam_users = [user["UserName"] for user in self.iam_obj.list_users(
        )[1] if self.user_name in user["UserName"]]
        if iam_users:
            self.log.info("Deleting iam users %s", iam_users)
            resp = self.iam_obj.delete_users_with_access_key(iam_users)
            assert_utils.assert_true(resp, f"Failed to delete iam useres: {iam_users}")
        self.log.debug("S3 account lists: %s", accounts)
        for acc in accounts:
            self.log.debug("Deleting %s account", acc)
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Deleted %s account successfully", acc)

    def delete_bucket_and_verify(self):
        """Delete bucket and all objects."""
        for s3t_obj in self.s3t_obj_list:
            if s3t_obj:
                bktlist = s3t_obj.bucket_list()[1]
                for bkt in bktlist:
                    resp = s3t_obj.delete_bucket(bkt, force=True)
                    assert resp[0], resp[1]
                    self.log.info("Removed bucket: %s", bkt)

    def create_bucket_put_objects(
            self,
            bucket_name: str,
            object_count: int,
            obj_name_prefix: str,
            obj_lst=None) -> None:
        """
        Method will create specified bucket and upload given numbers of objects into it.

        :param bucket_name: Name of s3 bucket
        :param object_count: Number of object to upload
        :param obj_name_prefix: Object prefix used while uploading an object to bucket
        :param obj_lst: Empty list for adding newly created objects if not passed explicitly
        """
        self.log.info("Creating buckets and uploading objects")
        if obj_lst is None:
            obj_lst = []
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.log.info(
            "Creating a bucket with name %s and uploading %d objects",
            bucket_name, object_count)
        resp = self.s3_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        for i in range(object_count):
            obj_name = "{}{}{}".format(
                obj_name_prefix, str(int(time.time())), i)
            resp = self.s3_obj.put_object(
                bucket_name,
                obj_name,
                self.file_path)
            assert resp[0], resp[1]
            self.log.info("Created object %s", obj_name)
            obj_lst.append(obj_name)
        self.log.info("Created a bucket and uploaded %s objects", object_count)

    def create_s3_account(
            self,
            account_name: str,
            email_id: str,
            password: str) -> tuple:
        """
        function will create IAM accounts with specified account name and email-id.

        :param account_name: Name of account to be created
        :param email_id: Email id for account creation
        :param password: Password for the account
        :return: It returns account details such as canonical_id, access_key, secret_key,
        account_id and s3 objects which will be required to perform further operations.
        """
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            account_name, email_id)
        create_account = self.rest_obj.create_s3_account(
            acc_name=account_name, email_id=email_id, passwd=password)
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        canonical_id = create_account[1]["canonical_id"]
        account_id = create_account[1]["account_id"]
        self.log.info("Step Successfully created the cortxcli account")
        s3_obj = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        acl_obj = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        s3_bkt_policy_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key, secret_key=secret_key)
        s3_bkt_tag_obj = s3_tagging_test_lib.S3TaggingTestLib(
            access_key=access_key, secret_key=secret_key)
        s3_multipart_obj = s3_multipart_test_lib.S3MultipartTestLib(
            access_key=access_key, secret_key=secret_key)
        self.account_list.append(account_name)

        return canonical_id, s3_obj, acl_obj, s3_bkt_policy_obj, \
            access_key, secret_key, account_id, s3_bkt_tag_obj, s3_multipart_obj

    def delete_bucket_policy_with_err_msg(self,
                                          bucket_name: str,
                                          s3_obj_one: object,
                                          acl_obj_one: object,
                                          s3_bkt_policy_obj_one: object,
                                          s3_bkt_policy_obj_two: object,
                                          test_config: dict) -> None:
        """
        Method will delete a bucket policy applied to the specified bucket.

        It will also handle exceptions occurred while deleting a bucket policy, if any.
        :param bucket_name: s3 bucket
        :param s3_obj_one: s3 test object of account one
        :param acl_obj_one: s3 acl test lib object of account one
        :param s3_bkt_policy_obj_one: s3 bucket policy class object of account 1
        :param s3_bkt_policy_obj_two: s3 bucket policy class object of account 2
        :param test_config: test-case yaml config values
        """
        self.log.info("Retrieving bucket acl attributes")
        resp = acl_obj_one.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Bucket ACL was verified")
        self.log.info("Apply put bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_config["bucket_policy"])
        resp = s3_bkt_policy_obj_one.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Bucket policy was applied on the bucket")
        self.log.info(
            "Verify the bucket policy from Bucket owner account")
        resp = s3_bkt_policy_obj_one.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 4: Bucket policy was verified")
        self.log.info(
            "Login to account2 and delete bucket policy for the bucket "
            "which is present in account1")
        try:
            s3_bkt_policy_obj_two.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        resp = acl_obj_one.put_bucket_acl(
            bucket_name, acl="private")
        assert resp[0], resp[1]
        resp = s3_obj_one.delete_bucket(bucket_name, force=True)
        assert resp[0], resp[1]
        self.log.info(
            "Delete bucket policy should through error message %s",
            errmsg.ACCESS_DENIED_ERR_KEY)

    def create_bucket_put_obj_with_dir(
            self,
            bucket_name: str,
            obj_name_1: str,
            obj_name_2: str) -> None:
        """
        Function will create a bucket and upload objects from a directory to a bucket.

        :param bucket_name: Name of bucket to be created
        :param obj_name_1: Name of an object to be put to the bucket
        :param obj_name_2: Name of an object from a dir which is getting uploaded
        """
        self.log.info("Creating a bucket with name %s", bucket_name)
        resp = self.s3_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", bucket_name)
        self.log.info(
            "Uploading an object %s to a bucket %s", obj_name_1, bucket_name)
        resp = system_utils.create_file(
            self.file_path_1,
            10)
        assert resp[0], resp[1]
        resp = self.s3_obj.put_object(
            bucket_name,
            obj_name_1,
            self.file_path_1)
        assert resp[0], resp[1]
        self.log.info("An object is uploaded to a bucket")
        self.log.info(
            "Uploading an object %s from a dir to a bucket %s",
            obj_name_2,
            bucket_name)
        resp = system_utils.create_file(
            self.file_path_2,
            10)
        assert resp[0], resp[1]
        resp = self.s3_obj.put_object(
            bucket_name,
            obj_name_2,
            self.file_path_2)
        assert resp[0], resp[1]
        self.log.info(
            "Uploaded an object %s from a dir to a bucket %s",
            obj_name_2, bucket_name)

    def create_bucket_validate(self, bucket_name: str) -> None:
        """
        Create a new bucket and validate it.

        :param bucket_name: Name of bucket to be created
        """
        self.log.info("Step 1 : Creating a bucket with name %s", bucket_name)
        resp = self.s3_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        self.log.info("Step 1 : Bucket is created with name %s", bucket_name)

    def put_bucket_policy_with_err(
            self,
            bucket_name: str,
            test_bckt_cfg: dict,
            s3_bkt_policy_obj_2: object) -> None:
        """
        Method will apply bucket policy on the specified bucket.

        It will also handle exceptions occurred while updating bucket policy, if any.
        :param  bucket_name: Name of the s3 bucket
        :param  test_bckt_cfg: test-case yaml config values
        :param  s3_bkt_policy_obj_2: s3 acl test bucket policy of account two
        """
        self.log.info("Getting the bucket acl")
        resp = self.acl_obj.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1][1][0]["Permission"],
                                   test_bckt_cfg["bucket_permission"], resp[1])
        self.log.info("Bucket ACL was verified successfully")
        self.log.info(
            "Apply put bucket policy on the bucket using account second account")
        bkt_json_policy = json.dumps(test_bckt_cfg["bucket_policy"])
        try:
            s3_bkt_policy_obj_2.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Put Bucket policy from second account will result into"
            "failure with error : %s", errmsg.ACCESS_DENIED_ERR_KEY)
        resp = self.acl_obj.put_bucket_acl(
            bucket_name, acl="private")
        assert resp[0], resp[1]

    def put_get_bkt_policy(self, bucket_name: str, bucket_policy: str) -> None:
        """
        Method applies bucket policy to an bucket and retrieves the policy of a same bucket.

        :param  bucket_name: The name of the bucket
        :param  bucket_policy: The bucket policy as a JSON document
        """
        self.log.info("Applying policy to a bucket %s", bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        self.log.info("Policy is applied to a bucket %s", bucket_name)
        self.log.info("Retrieving policy of a bucket %s", bucket_name)
        resp = self.s3_bkt_policy_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        self.log.debug(resp[1]["Policy"])
        assert_utils.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        self.log.info("Retrieved policy of a bucket %s", bucket_name)

    def put_invalid_policy(
            self,
            bucket_name: str,
            bucket_policy: str,
            msg: str) -> None:
        """
        Method applies invalid policy on a bucket and validate the expected error.

        :param bucket_name: Name of the bucket to be created
        :param bucket_policy: The bucket policy as a JSON document
        :param msg: Error message to be validate
        """
        self.log.info("Applying invalid policy on a bucket %s", bucket_name)
        bkt_json_policy = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(bucket_name,
                                                     bkt_json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert msg in error.message, error.message
            self.log.info(
                "Applying invalid policy on a bucket is failed with error %s",
                error.message)

    def put_bkt_policy_with_date_format(
            self,
            account_id: str,
            date_time: str,
            effect: str,
            s3_test_ob: object,
            test_config: dict):
        """
        Set the bucket policy.

        Method will set the bucket policy using date format condition and retrieves the policy of
        a bucket and validates it. It will also upload an object to a bucket using another account
        and handle exceptions occurred while uploading.
        :param  account_id: account-id of the second account
        :param  date_time: datetime for date condition
        :param  effect: Policy element "Effect" either (Allow/Deny)
        :param  s3_test_ob: s3 test class object of another account
        :param  test_config: test-case yaml config values
        """
        bkt_json_policy = eval(json.dumps(test_config["bucket_policy"]))
        dt_condition = bkt_json_policy["Statement"][0]["Condition"]
        condition_key = list(
            dt_condition[test_config["date_condition"]].keys())[0]
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        bkt_json_policy["Statement"][0]["Condition"][test_config["date_condition"]
                                                     ][condition_key] = date_time
        bkt_json_policy["Statement"][0]["Effect"] = effect
        bkt_json_policy["Statement"][0]["Resource"] = \
            bkt_json_policy["Statement"][0]["Resource"].format(self.bucket_name)
        self.log.info("Bucket name: %s", self.bucket_name)
        bkt_list = self.s3_obj.bucket_list()[1]
        if self.bucket_name not in bkt_list:
            resp = self.s3_obj.create_bucket(self.bucket_name)
            self.log.info(resp)
            assert resp[0], resp[1]
        self.put_get_bkt_policy(self.bucket_name, bkt_json_policy)
        self.log.info("Uploading object to s3 bucket with second account")
        try:
            s3_test_ob.put_object(
                self.bucket_name,
                self.object_name,
                self.file_path)
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Uploading object to bucket with second account failed with error %s",
                error.message)

    def list_obj_with_max_keys_and_diff_acnt(
            self,
            bucket_name: str,
            s3t_obj: object,
            max_keys: int,
            err_message: str = None) -> None:
        """
        List objects.

        Function will list objects of a specified bucket with specified max keys using given s3
        test object. It will also handle an exception occurred during list object operation.
        :param  bucket_name: Name of a bucket
        :param  s3t_obj: s3 test class object of other IAM account
        :param  max_keys: Maximum no of keys to be listed
        :param  err_message: An error message returned on ListObject operation failure
        """
        self.log.info(
            "Listing objects of a bucket %s with %d max keys and specified account",
            bucket_name,
            max_keys)
        if err_message:
            try:
                s3t_obj.list_objects_with_prefix(
                    bucket_name, maxkeys=max_keys)
            except CTException as error:
                self.log.error(error.message)
                assert err_message in error.message, error.message
                self.log.info(
                    "Listing objects with %d max keys and specified account is failed with"
                    " error %s", max_keys, err_message)
        else:
            resp = s3t_obj.list_objects_with_prefix(
                bucket_name, maxkeys=max_keys)
            assert resp[0], resp[1]
            self.log.info(
                "Listed objects with %d max keys and specified account successfully",
                max_keys)

    def list_objects_with_diff_acnt(
            self,
            bucket_name: str,
            s3t_obj: object,
            err_message: str = None) -> None:
        """
        Function will list objects of specified bucket using specified s3 test class object.

        It will also handle an exception occurred during list object operation.
        :param bucket_name: Name of bucket
        :param s3t_obj: s3 test class object of other IAM account
        :param: err_message: An error message returned on ListObject operation failure
        """
        self.log.info("Listing an objects of bucket %s", bucket_name)
        if err_message:
            try:
                s3t_obj.object_list(bucket_name)
            except CTException as error:
                self.log.error(error.message)
                assert err_message in error.message, error.message
                self.log.info(
                    "Listing an objects of bucket %s failed with %s",
                    bucket_name, err_message)
        else:
            resp = s3t_obj.object_list(bucket_name)
            assert resp[0], resp[1]
            self.log.info("Listed objects of bucket %s successfully",
                          bucket_name)

    def put_object_with_acl_cross_acnt(
            self,
            bucket_name: str,
            s3t_obj: object,
            obj_name: str,
            acl: str = None,
            grant_full_control: str = None,
            grant_read: str = None,
            grant_read_acp: str = None,
            grant_write_acp: str = None,
            err_message: str = None) -> None:
        """
        Function will put object to specified bucket using specified s3 test class object with acl.

        if given. It will also handle an exception occurred during put object operation.
        :param bucket_name: Name of bucket
        :param s3t_obj: s3 test class object of other IAM account
        :param obj_name: name for an object
        :param acl: acl permission to set while putting an obj
        :param grant_full_control: To set a grant full control permission for given object.
        :param grant_read: To set a grant read permission for given object.
        :param grant_read_acp: To set a grant read ACP permission for given object.
        :param grant_write_acp: To set a grant write ACP permission for given object.
        :param err_message: An error message returned on PutObject operation failure.
        """
        self.log.info("Put an object to bucket %s", bucket_name)
        system_utils.create_file(
            self.file_path_2,
            10)
        if err_message:
            try:
                if acl or grant_read or grant_full_control or grant_read_acp or grant_write_acp:
                    s3t_obj.put_object_with_acl(
                        bucket_name=bucket_name,
                        key=obj_name,
                        file_path=self.file_path_2,
                        acl=acl,
                        grant_full_control=grant_full_control,
                        grant_read=grant_read,
                        grant_read_acp=grant_read_acp,
                        grant_write_acp=grant_write_acp)
                else:
                    s3t_obj.put_object(
                        bucket_name,
                        obj_name,
                        self.file_path_2)
            except CTException as error:
                self.log.error(error.message)
                assert err_message in error.message, error.message
                self.log.info(
                    "Putting an object into bucket %s failed with %s",
                    bucket_name, err_message)
        else:
            if acl or grant_read or grant_full_control or grant_read_acp or grant_write_acp:
                resp = s3t_obj.put_object_with_acl(
                    bucket_name=bucket_name,
                    key=obj_name,
                    file_path=self.file_path_2,
                    acl=acl,
                    grant_full_control=grant_full_control,
                    grant_read=grant_read,
                    grant_read_acp=grant_read_acp,
                    grant_write_acp=grant_write_acp)
            else:
                resp = s3t_obj.put_object(
                    bucket_name, obj_name, self.file_path_2)
            assert resp[0], resp[1]
            self.log.info(
                "Put object into bucket %s successfully",
                bucket_name)

    def list_obj_with_prefix_using_diff_accnt(
            self,
            bucket_name: str,
            s3t_obj: object,
            obj_name_prefix: str,
            err_message: str = None) -> None:
        """
        Function will list objects with given prefix, of specified bucket.

        It will also handle an exception occurred during list object operation.
        :param str bucket_name: Name of a bucket
        :param object s3t_obj: s3 test class object of other IAM account.
        :param str obj_name_prefix: Object Name prefix.
        :param str err_message: An error message returned on ListObject operation failure.
        """
        self.log.info(
            "Listing objects of a bucket %s with %s prefix",
            bucket_name, obj_name_prefix)
        if err_message:
            try:
                s3t_obj.list_objects_with_prefix(
                    bucket_name, prefix=obj_name_prefix)
            except CTException as error:
                self.log.error(error.message)
                assert err_message in error.message, error.message
                self.log.info(
                    "Listing objects with %s prefix from another account is failed with error %s",
                    obj_name_prefix,
                    err_message)
        else:
            resp = s3t_obj.list_objects_with_prefix(
                bucket_name, prefix=obj_name_prefix)
            assert resp[0], resp[1]
            self.log.info(
                "Listed objects with %s prefix successfully", obj_name_prefix)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6102")
    @CTFailOn(error_handler)
    def test_254(self):
        """create bucket and get-bucket-policy for that bucket."""
        self.log.info(
            "STARTED: create bucket and get-bucket-policy for that bucket")
        self.create_bucket_validate(self.bucket_name)
        self.log.info(
            "Step 2 : Retrieving policy of a bucket %s",
            self.bucket_name)
        try:
            self.s3_bkt_policy_obj.get_bucket_policy(
                self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_NO_SUCH_ERR in error.message, error.message
        self.log.info(
            "Step 2 : Retrieving policy of a bucket %s is failed",
            self.bucket_name)
        self.log.info(
            "ENDED: create bucket and get-bucket-policy for that bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6101")
    @CTFailOn(error_handler)
    def test_260(self):
        """verify get-bucket-policy for the bucket which is not present."""
        self.log.info(
            "STARTED: verify get-bucket-policy for the bucket which is not present")
        self.log.info(
            "Step 1 : Retrieving policy of non existing bucket")
        try:
            self.s3_bkt_policy_obj.get_bucket_policy(
                self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 1 : Retrieving policy of a bucket %s is failed",
            self.bucket_name)
        self.log.info(
            "ENDED: verify get-bucket-policy for the bucket which is not present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6100")
    @CTFailOn(error_handler)
    def test_261(self):
        """check get-bucket-policy for the bucket which is having policy for that bucket."""
        self.log.info(
            "STARTED: check get-bucket-policy for the "
            "bucket which is having policy for that bucket")
        self.log.info("Step 1 : Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1],
                                   self.bucket_name,
                                   resp[1])
        self.log.info("Step 1 : Bucket is created with name %s",
                      self.bucket_name)
        bucket_policy = BKT_POLICY_CONF["test_261"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        bkt_json_policy = json.dumps(bucket_policy)
        self.log.info(
            "Step 2 : Performing put bucket policy on bucket %s",
            self.bucket_name)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2 : Performed put bucket policy operation on bucket %s",
            self.bucket_name)
        self.log.info(
            "Step 3 : Retrieving policy of a bucket %s",
            self.bucket_name)
        resp = self.s3_bkt_policy_obj.get_bucket_policy(
            self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1]["Policy"], bkt_json_policy, resp[1])
        self.log.info("Step 3 : Retrieved policy of a bucket %s",
                      self.bucket_name)
        self.log.info(
            "ENDED: check get-bucket-policy for the bucket which is having policy for that bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6099")
    @CTFailOn(error_handler)
    def test_262(self):
        """
        Verify get-bucket-policy for the bucket from account2.

        Do not apply any ACL permissions or canned ACL to account2 and verify get-bucket-policy.
        """
        self.log.info(
            "STARTED: verify get-bucket-policy for the bucket from account2."
            "Do not apply any ACL permissions or "
            "canned ACL to account2 and verify get-bucket-policy")
        self.log.info("Step 1 : Creating a  bucket with name %s",
                      self.bucket_name)
        resp = self.s3_obj.create_bucket(
            self.bucket_name)
        assert_utils.assert_equals(
            resp[1],
            self.bucket_name,
            resp[1])
        assert resp[0], resp[1]
        self.log.info("Step 1 : Created a bucket with name %s",
                      self.bucket_name)
        bucket_policy = BKT_POLICY_CONF["test_262"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        bkt_json_policy = json.dumps(bucket_policy)
        self.log.info(
            "Step 2 : Performing put bucket policy on  bucket %s",
            self.bucket_name)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2 : Performed put bucket policy operation on bucket %s",
            self.bucket_name)
        self.log.info(
            "Step 3 : Login to another account to perform get bucket policy")
        self.log.info(
            "Creating another account with name %s and email %s",
            self.account_name,
            self.email_id)
        resp = self.rest_obj.create_s3_account(
            acc_name=self.account_name,
            email_id=self.email_id,
            passwd=self.s3acc_passwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.account_list.append(self.account_name)
        s3_obj_2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key,
            secret_key=secret_key)
        self.log.info(
            "Getting bucket policy using another account %s",
            self.account_name)
        try:
            s3_obj_2.get_bucket_policy(
                self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 3 : Get bucket policy with another account is failed")
        self.log.info(
            "ENDED: verify get-bucket-policy for the bucket from account2."
            "Do not apply any ACL permissions or "
            "canned ACL to account2 and verify get-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6079")
    @CTFailOn(error_handler)
    def test_642(self):
        """Test resource arn combination with bucket name and all objects."""
        self.log.info(
            "STARTED: Test resource arn combination with bucket name and all objects.")
        bucket_policy = BKT_POLICY_CONF["test_642"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        self.s3t_obj_list.append(s3_obj)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey642_2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 1: Retrieving objects from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj.get_object(
            self.bucket_name,
            "obj_policy")
        assert resp[0], resp[1]
        resp = s3_obj.get_object(
            self.bucket_name,
            "objkey642_2")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved objects from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)

        time.sleep(S3_CFG["sync_delay"])
        self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test resource arn combination with bucket name and all objects.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6077")
    @CTFailOn(error_handler)
    def test_644(self):
        """Test resource arn combination with bucket name and no object name."""
        self.log.info(
            "STARTED: Test resource arn combination with bucket name and all objects.")
        bucket_policy = BKT_POLICY_CONF["test_644"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey644_2")
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test resource arn combination with bucket name and all objects.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6075")
    @CTFailOn(error_handler)
    def test_646(self):
        """Test resource arn combination without mentioning bucket name."""
        self.log.info(
            "STARTED: Test resource arn combination without mentioning bucket name")
        bucket_policy = BKT_POLICY_CONF["test_646"]["bucket_policy"]
        bucket_policy["Statement"][1]["Resource"] = bucket_policy["Statement"][1][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey646_2")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test resource arn combination without mentioning bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6073")
    @CTFailOn(error_handler)
    def test_658(self):
        """Test resource arn combination with not present bucket name."""
        self.log.info(
            "STARTED: Test resource arn combination with not present bucket name")
        bucket_policy = BKT_POLICY_CONF["test_658"]["bucket_policy"]
        bucket_policy["Statement"][1]["Resource"] = bucket_policy["Statement"][1][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey658_2")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test resource arn combination with not present bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6071")
    @CTFailOn(error_handler)
    def test_659(self):
        """Test resource arn combination with object name."""
        self.log.info(
            "STARTED: Test resource arn combination with object name")
        bucket_policy = BKT_POLICY_CONF["test_659"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        self.s3t_obj_list.append(s3_obj)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey659_2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 1: Retrieving object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj.get_object(
            self.bucket_name,
            "obj_policy")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        self.log.info(
            "ENDED: Test resource arn combination with object name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6069")
    @CTFailOn(error_handler)
    def test_679(self):
        """Test resource arn combination with object name inside folder."""
        self.log.info(
            "STARTED: Test resource arn combination with object name inside folder")
        bucket_policy = BKT_POLICY_CONF["test_679"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        self.s3t_obj_list.append(s3_obj)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "policy/objkey679_2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 1: Retrieving object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj.get_object(self.bucket_name, "policy/objkey679_2")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        self.log.info(
            "ENDED: Test resource arn combination with object name inside folder")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6067")
    @CTFailOn(error_handler)
    def test_680(self):
        """Test resource arn combination mentioning IAM details."""
        self.log.info(
            "STARTED: Test resource arn combination mentioning IAM details")
        bucket_policy = BKT_POLICY_CONF["test_680"]["bucket_policy"]
        bucket_policy["Statement"][1]["Resource"] = bucket_policy["Statement"][1][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey680_2")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test resource arn combination mentioning IAM details")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6065")
    @CTFailOn(error_handler)
    def test_682(self):
        """Test resource arn combination with missing required component/value as per arn format."""
        self.log.info(
            "STARTED: Test resource arn combination "
            "with missing required component/value as per arn format")
        bucket_policy = BKT_POLICY_CONF["test_682"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey682_2")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test resource arn combination with "
            "missing required component/value as per arn format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6063")
    @CTFailOn(error_handler)
    def test_688(self):
        """Test resource arn combination with multiple arns."""
        self.log.info(
            "STARTED: Test resource arn combination with multiple arns")
        bucket_policy = BKT_POLICY_CONF["test_688"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][0]["Resource"]["AWS"][i] = bucket_policy["Statement"][0][
                "Resource"]["AWS"][i].format(self.bucket_name)
        bucket_policy["Statement"][1]["Resource"] = bucket_policy["Statement"][1][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey688_2")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test resource arn combination with multiple arns")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6061")
    @CTFailOn(error_handler)
    def test_689(self):
        """Test resource arn combination with wildcard * for bucket."""
        self.log.info(
            "STARTED: Test resource arn combination with wildcard * for bucket")
        bucket_policy = BKT_POLICY_CONF["test_689"]["bucket_policy"]
        bucket_policy["Statement"][1]["Resource"] = bucket_policy["Statement"][1][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey689_2")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_RESOURCE_ERR)
        self.log.info("Put bucket policy on a bucket is failed")
        self.log.info(
            "ENDED: Test resource arn combination with wildcard * for bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6059")
    @CTFailOn(error_handler)
    def test_690(self):
        """Test resource arn specifying wildcard * for specifying part of object name."""
        self.log.info(
            "STARTED: Test resource arn specifying wildcard * for specifying part of object name")
        bucket_policy = BKT_POLICY_CONF["test_690"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        self.s3t_obj_list.append(s3_obj)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey690_2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 1: Retrieving object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj.get_object(
            self.bucket_name,
            "obj_policy")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        self.log.info(
            "ENDED: Test resource arn specifying wildcard * for specifying part of object name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6005")
    @CTFailOn(error_handler)
    def test_1300(self):
        """Create Bucket Policy using NumericLessThan Condition Operator."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThan Condition Operator")
        bucket_policy = BKT_POLICY_CONF["test_1300"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            10,
            "obj_policy")
        self.log.info(
            "Step 1 : Create a json for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        bkt_json_policy = json.dumps(bucket_policy)
        self.log.info(
            "Step 1 : Created a json for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        self.log.info(
            "Step 2: Apply the bucket policy on the bucket and check the output")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy on the bucket was applied")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericGreaterThan",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThan Condition Operator")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6003")
    @CTFailOn(error_handler)
    def test_1303(self):
        """Create Bucket Policy using NumericLessThanEquals Condition Operator."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThanEquals Condition Operator")
        bucket_policy = BKT_POLICY_CONF["test_1303"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            10,
            "obj_policy")
        self.log.info(
            "Step 1 : Create a json for bucket policy specifying using "
            "NumericLessThanEquals Condition Operator")
        bkt_json_policy = json.dumps(bucket_policy)
        self.log.info(
            "Step 1 : Created a json for bucket policy specifying using "
            "NumericLessThanEquals Condition Operator")
        self.log.info(
            "Step 2: Apply the bucket policy on the bucket and check the output")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy on the bucket was applied")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericLessThan",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThanEquals Condition Operator")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6000")
    @CTFailOn(error_handler)
    def test_1307(self):
        """Create Bucket Policy using NumericGreaterThan Condition Operator."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThan Condition Operator")
        bucket_policy = BKT_POLICY_CONF["test_1307"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            10,
            "obj_policy")
        self.log.info(
            "Step 1: Create a json for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        bkt_json_policy = json.dumps(bucket_policy)
        self.log.info(
            "Step 1: Created a json for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        self.log.info(
            "Step 2: Apply the bucket policy on the bucket and check the output")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericGreaterThan")
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThan Condition Operator")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5998")
    @CTFailOn(error_handler)
    def test_1308(self):
        """Create Bucket Policy using NumericGreaterThanEquals Condition Operator."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")
        bucket_policy = BKT_POLICY_CONF["test_1308"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            10,
            "obj_policy")
        self.log.info("Step 1: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 1: Bucket policy was applied successfully")
        self.log.info("Step 2: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(bucket_policy[0],
                                   "NumericGreaterThanEquals",
                                   resp[1])
        self.log.info("Step 2: Bucket policy was verified successfully")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6010")
    @CTFailOn(error_handler)
    def test_1294(self):
        """Create Bucket Policy using StringNotEquals Condition Operator and Allow Action_string."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringEquals Condition Operator and Allow Action")
        bucket_policy = BKT_POLICY_CONF["test_1294"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 1: Bucket policy was applied successfully")
        self.log.info("Step 2: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])
                             ["Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "StringEquals",
            resp[1])
        self.log.info("Step 2: Bucket policy was verified successfully")
        self.log.info(
            "Step 3: Verify the Bucket Policy with prefix and from Bucket owner account")
        resp = self.s3_obj.list_objects_with_prefix(
            self.bucket_name, "obj")
        prefix_obj_lst = list(resp[1])
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            prefix_obj_lst.sort(),
            object_lst.sort(),
            resp[1])
        self.log.info("Step 3: Verified the Bucket Policy with prefix")
        self.log.info(
            "ENDED: Create Bucket Policy using StringEquals Condition Operator and Allow Action")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6007")
    @CTFailOn(error_handler)
    def test_1296(self):
        """Create Bucket Policy using NumericGreaterThanEquals Condition Operator_string."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")
        bucket_policy = BKT_POLICY_CONF["test_1296"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 1: Bucket policy was applied successfully")
        self.log.info("Step 2: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])
                             ["Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "StringNotEquals",
            resp[1])
        self.log.info("Step 2: Bucket policy was verified successfully")
        self.log.info(
            "Step 3: Verify the Bucket Policy with prefix and from Bucket owner account")
        resp = self.s3_obj.list_objects_with_prefix(
            self.bucket_name, "obj")
        prefix_obj_lst = list(resp[1])
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            prefix_obj_lst.sort(),
            object_lst.sort(),
            resp[1])
        self.log.info("Step 3: Verified the Bucket Policy with prefix")
        self.log.info(
            "Step 4: Verify the Bucket Policy without prefix from Bucket owner")
        resp = self.s3_obj.object_list(self.bucket_name)
        prefix_obj_lst = list(resp[1])
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            prefix_obj_lst.sort(),
            object_lst.sort(),
            resp[1])
        self.log.info("Step 4: Verified the Bucket Policy without prefix")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6098")
    @CTFailOn(error_handler)
    def test_558(self):
        """Apply Delete-bucket-policy on existing bucket."""
        self.log.info("STARTED: Apply Delete-bucket-policy on existing bucket")
        bucket_policy = BKT_POLICY_CONF["test_558"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info("Step 4: Delete bucket policy")
        resp = self.s3_bkt_policy_obj.delete_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 4: Bucket policy was deleted successfully")
        try:
            self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            assert errmsg.S3_BKT_POLICY_NO_SUCH_ERR in error.message, error.message
        self.log.info("ENDED: Apply Delete-bucket-policy on existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6097")
    @CTFailOn(error_handler)
    def test_560(self):
        """Apply Delete-bucket-policy on non existing bucket."""
        self.log.info(
            "STARTED: Apply Delete-bucket-policy on non existing bucket")
        self.log.info(
            "Step 1: Delete bucket policy for the bucket which is not there")
        try:
            self.s3_bkt_policy_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 1: Delete bucket policy should through error message %s",
            errmsg.NO_BUCKET_OBJ_ERR_KEY)
        self.log.info("ENDED: Apply Delete-bucket-policy on non existing bucket.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6096")
    @CTFailOn(error_handler)
    def test_562(self):
        """Apply Delete-bucket-policy without specifying bucket name."""
        self.log.info(
            "STARTED: Apply Delete-bucket-policy without specifying bucket name")
        bucket_policy = BKT_POLICY_CONF["test_562"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Delete bucket policy without giving any bucket name")
        try:
            bucket_name = None
            self.s3_bkt_policy_obj.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert "expected string" in error.message, error.message
        self.log.info(
            "Step 4: Deleting the bucket without bucket "
            "name was handled with error message %s",
            "expected string")
        self.log.info(
            "ENDED: Apply Delete-bucket-policy without specifying bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6095")
    @CTFailOn(error_handler)
    def test_563(self):
        """Apply Delete-bucket-policy without specifying policy."""
        self.log.info(
            "STARTED: Apply Delete-bucket-policy without specifying policy.")
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 2: List all the bucket")
        resp = self.s3_obj.bucket_list()
        assert resp[0], resp[1]
        self.log.info("Step 2: All the bucket listed")
        self.log.info("Step 3: Delete bucket policy")
        try:
            self.s3_bkt_policy_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            assert errmsg.S3_BKT_POLICY_NO_SUCH_ERR in error.message, error.message
        self.log.info(
            "Step 3: Delete bucket policy should through error message %s",
            errmsg.S3_BKT_POLICY_NO_SUCH_ERR)
        self.log.info(
            "ENDED: Apply Delete-bucket-policy without specifying policy.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6093")
    @CTFailOn(error_handler)
    def test_566(self):
        """Apply Delete-bucket-policy from another account given read permission on bucket."""
        self.log.info("STARTED: Apply Delete-bucket-policy from another account given read"
                      " permission on bucket")
        test_566_cfg = BKT_POLICY_CONF["test_566"]
        for i in range(2):
            test_566_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_566_cfg["bucket_policy"]["Statement"][i]["Resource"].format(self.bucket_name)
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1, acl_obj_1, s3_bkt_policy_obj_1 = result_1[
            0], result_1[2], result_1[3]
        self.s3t_obj_list.append(result_1[1])
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2, s3_bkt_policy_obj_2 = result_2[0], result_2[3]
        self.log.info(
            "Step 1 : Create a new bucket and give grant_read permissions to account 2")
        resp = acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket was created with grant_read permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            self.bucket_name,
            result_1[1],
            acl_obj_1,
            s3_bkt_policy_obj_1,
            s3_bkt_policy_obj_2,
            test_566_cfg)
        self.log.info(
            "ENDED: Apply Delete-bucket-policy from another account given read permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6091")
    @CTFailOn(error_handler)
    def test_569(self):
        """Apply Delete-bucket-policy from another account given write permission on bucket."""
        self.log.info("STARTED: Apply Delete-bucket-policy from another account given write "
                      "permission on bucket")
        test_569_cfg = BKT_POLICY_CONF["test_569"]
        for i in range(2):
            test_569_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_569_cfg["bucket_policy"]["Statement"][i]["Resource"].format(self.bucket_name)
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        s3_bkt_policy_obj_1 = result_1[3]
        acl_obj_1 = result_1[2]
        self.s3t_obj_list.append(result_1[1])
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2 = result_2[0]
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info("Step 1 : Create a new bucket and give write permissions to account 2")
        resp = acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created with write permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            self.bucket_name,
            result_1[1],
            acl_obj_1,
            s3_bkt_policy_obj_1,
            s3_bkt_policy_obj_2,
            test_569_cfg)
        self.log.info(
            "ENDED: Apply Delete-bucket-policy from another account given write permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6089")
    @CTFailOn(error_handler)
    def test_570(self):
        """Apply Delete-bucket-policy from another account given read-acp permission on bucket."""
        self.log.info("STARTED: Apply Delete-bucket-policy from another account given read-acp "
                      "permission on bucket")
        test_570_cfg = BKT_POLICY_CONF["test_570"]
        for i in range(2):
            test_570_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_570_cfg["bucket_policy"]["Statement"][i]["Resource"].format(self.bucket_name)
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        s3_bkt_policy_obj_1 = result_1[3]
        acl_obj_1 = result_1[2]
        self.s3t_obj_list.append(result_1[1])
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2 = result_2[0]
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info(
            "Step 1 : Create a new bucket and give write-acp permissions to account 2")
        resp = acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read_acp="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket was created with write-acp permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            self.bucket_name,
            result_1[1],
            acl_obj_1,
            s3_bkt_policy_obj_1,
            s3_bkt_policy_obj_2,
            test_570_cfg)
        self.log.info("ENDED: Apply Delete-bucket-policy from another account given read-acp "
                      "permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6087")
    @CTFailOn(error_handler)
    def test_574(self):
        """Apply Delete-bucket-policy from another account given write-acp permission on bucket."""
        self.log.info("STARTED: Apply Delete-bucket-policy from another account given write-acp "
                      "permission on bucket")
        test_574_cfg = BKT_POLICY_CONF["test_574"]
        for i in range(2):
            test_574_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_574_cfg["bucket_policy"]["Statement"][i]["Resource"].format(self.bucket_name)
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        s3_bkt_policy_obj_1 = result_1[3]
        acl_obj_1 = result_1[2]
        self.s3t_obj_list.append(result_1[1])
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2 = result_2[0]
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info(
            "Step 1 : Create a new bucket and give write-acp permissions to account 2")
        resp = acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write_acp="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket was created with write-acp permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            self.bucket_name,
            result_1[1],
            acl_obj_1,
            s3_bkt_policy_obj_1,
            s3_bkt_policy_obj_2,
            test_574_cfg)
        self.log.info(
            "ENDED: Apply Delete-bucket-policy from "
            "another account given write-acp permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6085")
    @CTFailOn(error_handler)
    def test_582(self):
        """Test Apply Delete-bucket-policy from another account given full-control permission on bucket."""
        self.log.info(
            "STARTED: Apply Delete-bucket-policy "
            "from another account given full-control permission on bucket")
        test_582_cfg = BKT_POLICY_CONF["test_582"]
        for i in range(2):
            test_582_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_582_cfg["bucket_policy"]["Statement"][i]["Resource"].format(self.bucket_name)
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        s3_bkt_policy_obj_1 = result_1[3]
        acl_obj_1 = result_1[2]
        self.s3t_obj_list.append(result_1[1])
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2 = result_2[0]
        s3_bkt_policy_obj_2 = result_2[3]
        self.s3t_obj_list.append(result_2[1])
        self.log.info(
            "Step 1 : Create a new bucket and give full-control permissions to account 2")
        resp = acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket was created with full-control permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            self.bucket_name,
            result_1[1],
            acl_obj_1,
            s3_bkt_policy_obj_1,
            s3_bkt_policy_obj_2,
            test_582_cfg)
        self.log.info(
            "ENDED: Apply Delete-bucket-policy from "
            "another account given full-control permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6083")
    @CTFailOn(error_handler)
    def test_583(self):
        """Apply Delete-bucket-policy from another account with no permissions."""
        self.log.info(
            "STARTED: Apply Delete-bucket-policy from another account with no permissions")
        bucket_policy = BKT_POLICY_CONF["test_583"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info("Step 1 : Create a new bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created")
        self.log.info("Step 2: Get bucket acl")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket ACL was verified")
        self.log.info("Step 3: Apply put bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 3: Bucket policy was applied on the bucket")
        self.log.info(
            "Step 4: Verify the bucket policy from Bucket owner account")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 4: Bucket policy was verified")
        self.log.info(
            "Step 5: Login to account2 and delete bucket policy for the bucket "
            "which is present in account1")
        try:
            s3_bkt_policy_obj_2.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 5: Delete bucket policy should through error message")
        self.log.info(
            "ENDED: Apply Delete-bucket-policy from another account with no permissions")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6081")
    @CTFailOn(error_handler)
    def test_584(self):
        """Apply Delete-bucket-policy from another account with authenticated-read permission on bucket."""
        self.log.info(
            "STARTED: Apply Delete-bucket-policy from another account"
            " with authenticated-read permission on bucket")
        bucket_policy = BKT_POLICY_CONF["test_584"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info(
            "Step 1 : Create a new bucket with authenticated read permission")
        resp = self.acl_obj.create_bucket_with_acl(
            bucket_name=self.bucket_name, acl="authenticated-read")
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created")
        self.log.info("Step 2: Retrieving bucket acl attributes")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket ACL was verified")
        self.log.info("Step 3: Apply put bucket policy on the bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info("Step 3: Bucket policy was applied on the bucket")
        self.log.info(
            "Step 4: Verify the bucket policy from Bucket owner account")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 4: Bucket policy was verified")
        self.log.info(
            "Step 5: Login to account2 and delete bucket policy for the bucket "
            "which is present in account1")
        try:
            s3_bkt_policy_obj_2.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 5: Delete bucket policy should through error message")
        self.log.info(
            "ENDED: Apply Delete-bucket-policy from another account with"
            " authenticated-read permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6053")
    @CTFailOn(error_handler)
    def test_693(self):
        """Test principal arn combination with invalid account-id."""
        self.log.info(
            "STARTED: Test principal arn combination with invalid account-id")
        bucket_policy = BKT_POLICY_CONF["test_693"]["bucket_policy"]
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        self.log.info("Creating a user with name %s", self.user_name)
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey693_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(self.user_name)
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn combination with invalid account-id")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6051")
    @CTFailOn(error_handler)
    def test_694(self):
        """Test principal arn combination with invalid user name."""
        self.log.info(
            "STARTED: Test principal arn combination with invalid user name")
        bucket_policy = BKT_POLICY_CONF["test_694"]["bucket_policy"]
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey694_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = bucket_policy["Statement"][0][
            "Principal"]["AWS"].format(account_id)
        bkt_json_policy = bucket_policy
        self.put_invalid_policy(self.bucket_name,
                                bkt_json_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn combination with invalid user name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6049")
    @CTFailOn(error_handler)
    def test_716(self):
        """Test principal arn combination with valid accountid and valid user but of different account."""
        self.log.info(
            "STARTED: Test principal arn combination with "
            "valid accountid and valid user but of different account")
        bucket_policy = BKT_POLICY_CONF["test_716"]["bucket_policy"]
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        self.log.info(
            "Creating a user %s from another account", self.user_name)
        resp = self.iam_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey716_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, self.user_name)
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn combination with "
            "valid accountid and valid user but of different account")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6045")
    @CTFailOn(error_handler)
    def test_718(self):
        """Test principal arn combination with wildcard * for all accounts."""
        self.log.info(
            "STARTED: Test principal arn combination with wildcard * for all accounts.")
        bucket_policy = BKT_POLICY_CONF["test_718"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey718_2")
        self.log.info("Performing put bucket policy")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn combination with wildcard * for all accounts.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6043")
    @CTFailOn(error_handler)
    def test_719(self):
        """Test principal arn combination with wildcard * for all users in account."""
        self.log.info(
            "STARTED: Test principal arn combination with wildcard * for all users in account")
        bucket_policy = BKT_POLICY_CONF["test_719"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey719_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn combination with wildcard * for all users in account")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6041")
    @CTFailOn(error_handler)
    def test_720(self):
        """Test principal arn specifying wildcard in the portion of the ARN that specifies the resource type."""
        self.log.info(
            "STARTED: Test principal arn specifying wildcard "
            "in the portion of the ARN that specifies the resource type")
        bucket_policy = BKT_POLICY_CONF["test_720"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey720_2")
        self.log.info("Performing put bucket policy")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn specifying wildcard "
            "in the portion of the ARN that specifies the resource type")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6039")
    @CTFailOn(error_handler)
    def test_721(self):
        """Test arn specifying invalid text in place of arn."""
        self.log.info(
            "STARTED: Test arn specifying invalid text in place of arn")
        bucket_policy = BKT_POLICY_CONF["test_721"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info("Creating a user with name %s", self.user_name)
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey721_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, self.user_name)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test arn specifying invalid text in place of arn")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6037")
    @CTFailOn(error_handler)
    def test_722(self):
        """Test arn specifying invalid text for partition value."""
        self.log.info(
            "STARTED: Test arn specifying invalid text for partition value")
        bucket_policy = BKT_POLICY_CONF["test_722"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info("Creating a user with name %s", self.user_name)
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey722_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id,
                                                                     self.user_name)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test arn specifying invalid text for partition value")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6034")
    @CTFailOn(error_handler)
    def test_723(self):
        """Test arn specifying invalid text for service value."""
        self.log.info(
            "STARTED: Test arn specifying invalid text for service value.")
        bucket_policy = BKT_POLICY_CONF["test_723"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info("Creating a user with name %s", self.user_name)
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey723_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, self.user_name)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test arn specifying invalid text for service value.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6032")
    @CTFailOn(error_handler)
    def test_724(self):
        """Test arn specifying invalid text for region value."""
        self.log.info(
            "STARTED: Test arn specifying invalid text for region value .")
        bucket_policy = BKT_POLICY_CONF["test_724"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info("Creating a user with name %s", self.user_name)
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey724_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, self.user_name)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test arn specifying invalid text for region value .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6030")
    @CTFailOn(error_handler)
    def test_725(self):
        """Test arn specifying component/value as per arn format at inchanged position."""
        self.log.info(
            "STARTED: Test arn specifying component/value as per arn format at inchanged position.")
        bucket_policy = BKT_POLICY_CONF["test_725"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info("Creating a user with name %s", self.user_name)
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        self.log.info("User is created with name %s", self.user_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey725_2")
        self.log.info(
            "Performing put bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, self.user_name)
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test arn specifying component/value as per arn format at inchanged position")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6103")
    @CTFailOn(error_handler)
    def test_551(self):
        """Test missing key fields in bucket policy json."""
        self.log.info(
            "STARTED: Test extra spaces in key fields and values in bucket policy json")
        bucket_policy = BKT_POLICY_CONF["test_551"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 2,3 : Put Bucket policy with missing field")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_MISSING_FIELD_ERR)
        self.log.info(
            "ENDED: Test missing key fields in bucket policy json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6104")
    @CTFailOn(error_handler)
    def test_549(self):
        """Test invalid field in bucket policy json."""
        self.log.info(
            "STARTED: Test invalid field in bucket policy json")
        bucket_policy = BKT_POLICY_CONF["test_549"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 2,3 : Put Bucket policy with invalid field")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_UNKNOWN_FIELD_ERR)
        self.log.info(
            "ENDED: Test invalid field in bucket policy json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6105")
    @CTFailOn(error_handler)
    def test_545(self):
        """Test the case sensitivity of key fields in bucket policy json."""
        self.log.info(
            "STARTED: Test the case sensitivity of key fields in bucket policy json")
        bucket_policy = BKT_POLICY_CONF["test_545"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info(
            "Step 2,3 : Put Bucket policy with case sensitivity of key fields")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_UNKNOWN_FIELD_ERR)
        self.log.info(
            "ENDED: Test the case sensitivity of key fields in bucket policy json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6106")
    @CTFailOn(error_handler)
    def test_555(self):
        """Test invalid values in the key fields in bucket policy json."""
        self.log.info(
            "STARTED: Test invalid values in the key fields in bucket policy json")
        bucket_policy = BKT_POLICY_CONF["test_555"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 2,3 : Put Bucket policy with invalid values")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_INVALID_ACTION_ERR)
        self.log.info(
            "ENDED: Test invalid values in the key fields in bucket policy json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6108")
    @CTFailOn(error_handler)
    def test_553(self):
        """Test blank values for the key fields in bucket policy json."""
        self.log.info(
            "STARTED: Test blank values for the key fields in bucket policy json.")
        bucket_policy = BKT_POLICY_CONF["test_553"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info(
            "Step 2,3 : Put Bucket policy with blank values for the key fields")
        self.put_invalid_policy(self.bucket_name,
                                bucket_policy,
                                errmsg.S3_BKT_POLICY_EMPTY_ACTION_ERR)
        self.log.info(
            "ENDED: Test blank values for the key fields in bucket policy json.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6015")
    @CTFailOn(error_handler)
    def test_1080(self):
        """Test ? wildcard for part of s3 api in action field of statement of the json file."""
        self.log.info(
            "STARTED: Test ? wildcard for part of s3 "
            "api in action field of statement of the json file")
        bucket_policy = BKT_POLICY_CONF["test_1080"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey1080_2")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 1: Retrieving object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj.get_object(
            self.bucket_name,
            "objkey1080_2")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved object from a bucket %s", self.bucket_name)
        self.log.info(
            "ENDED: Test ? wildcard for part of s3 api in action field of statement of the json file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6017")
    @CTFailOn(error_handler)
    def test_1079(self):
        """Test * wildcard for part of s3 api in action field of statement of the json file."""
        self.log.info(
            "STARTED: Test * wildcard for part of s3 "
            "api in action field of statement of the json file")
        bucket_policy = BKT_POLICY_CONF["test_1079"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        s3_obj_acl = create_account[2]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey1079_2")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 1: Retrieving object acl from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj_acl.get_object_acl(
            self.bucket_name, "objkey1079_2")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved object acl from a bucket %s", self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object %s to a bucket %s",
            "obj_policy",
            self.bucket_name)
        system_utils.create_file(
            self.file_path,
            10)
        try:
            s3_obj.put_object(
                self.bucket_name,
                "obj_policy",
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 2: Uploading an object from another account is failed")
        self.log.info(
            "ENDED: Test * wildcard for part of s3 api "
            "in action field of statement of the json file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6020")
    @CTFailOn(error_handler)
    def test_1078(self):
        """Test * wildcard for all s3 apis in action field of statement of the json file."""
        self.log.info(
            "STARTED: Test * wildcard for all s3 apis "
            "in action field of statement of the json file")
        bucket_policy = BKT_POLICY_CONF["test_1078"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        acl_obj = create_account[2]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey1078_2")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 1: Retrieving object and acl of object from a "
            "bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        resp = s3_obj.get_object(
            self.bucket_name,
            "obj_policy")
        assert resp[0], resp[1]
        resp = acl_obj.get_object_acl(
            self.bucket_name, "objkey1078_2")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Retrieved object and acl of object from a bucket %s",
            self.bucket_name)
        self.log.info(
            "ENDED: Test * wildcard for all s3 apis in action field of statement of the json file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6022")
    @CTFailOn(error_handler)
    def test_1077(self):
        """Test * wildcard for all apis in action field of statement of the json file."""
        self.log.info(
            "STARTED: Test * wildcard for all apis in action field of statement of the json file")
        bucket_policy = BKT_POLICY_CONF["test_1077"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey1077_2")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 1: Uploading and retrieving object from a bucket %s using another account %s",
            self.bucket_name,
            self.account_name)
        system_utils.create_file(self.file_path, 10)
        resp = s3_obj.put_object(
            self.bucket_name,
            "objkey1077_3",
            self.file_path)
        assert resp[0], resp[1]
        resp = s3_obj.get_object(
            self.bucket_name,
            "objkey1077_3")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Uploaded an object and retrieved the same "
            "object from a bucket %s", self.bucket_name)
        self.log.info(
            "ENDED: Test * wildcard for all apis in action field of statement of the json file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6047")
    @CTFailOn(error_handler)
    def test_717(self):
        """Test principal arn combination with multiple arns."""
        self.log.info(
            "STARTED: Test principal arn combination with multiple arns")
        bucket_policy = BKT_POLICY_CONF["test_717"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        user_name_1 = "{0}{1}".format(
            "userpolicy_user", str(
                time.time()))
        user_name_2 = "{0}{1}".format(
            "userpolicy_user", str(
                time.time()))
        self.log.info(
            "Step 1: Creating a bucket and uploading objects using account 1")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey717_2")
        self.log.info(
            "Step 1: Created a bucket and objects are uploaded using account 1")
        self.log.info("Step 2: Creating multiple accounts")
        acc_detail = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_detail.append(resp)
            self.account_list.append(acc_name)
        acc_id_1 = acc_detail[0][1]["account_id"]
        access_key_1 = acc_detail[0][1]["access_key"]
        secret_key_1 = acc_detail[0][1]["secret_key"]
        acc_id_2 = acc_detail[1][1]["account_id"]
        access_key_2 = acc_detail[1][1]["access_key"]
        secret_key_2 = acc_detail[1][1]["secret_key"]
        self.log.info("Step 2: Multiple accounts are created")
        self.log.info("Step 3: Creating users in different accounts")
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key_1, secret_key=secret_key_1)
        iam_obj_acc_3 = iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = iam_obj_acc_2.create_user(user_name_1)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_obj_acc_2)
        resp = iam_obj_acc_3.create_user(user_name_2)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_obj_acc_3)
        self.log.info("Step 3: Users are created in different accounts")
        self.log.info(
            "Step 4: Creating a json with combination of multiple arns")
        bucket_policy["Statement"][0]["Principal"]["AWS"][0] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"][0]. \
            format(acc_id_1, user_name_1)
        bucket_policy["Statement"][0]["Principal"]["AWS"][1] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"][1]. \
            format(acc_id_2)
        self.log.info(
            "Step 4: json is created with combination of multiple arns")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 5: Retrieving object using user of account 2")
        resp = iam_obj_acc_2.create_access_key(user_name_1)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_2 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_2.get_object(
                self.bucket_name, "obj_policy")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 5: Retrieved object using user of account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 6: Retrieving object using account 3")
        s3_obj_acc_3 = s3_test_lib.S3TestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = s3_obj_acc_3.get_object(
            self.bucket_name, "obj_policy")
        assert resp[0], resp[1]
        self.log.info("Step 6: Retrieved object using account 3")
        self.log.info("Step 7: Retrieving object using user of account 3")
        resp = iam_obj_acc_3.create_access_key(user_name_2)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_3 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_3.get_object(
                self.bucket_name, "obj_policy")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 7: Retrieving object using user of account 3 is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Test principal arn combination with multiple arns")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6055")
    @CTFailOn(error_handler)
    def test_692(self):
        """Test principal arn combination with user name."""
        self.log.info(
            "STARTED: Test principal arn combination with user name")
        bucket_policy = BKT_POLICY_CONF["test_692"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1: Creating a bucket and uploading objects using account 1")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey692_2")
        self.log.info(
            "Step 1: Created a bucket and objects are uploaded using account 1")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info(
            "Step 2: Creating a user with name %s in account 2",
            self.user_name)
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_obj_acc_2.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_obj_acc_2)
        self.log.info(
            "Step 2: User is created with name %s in account 2",
            self.user_name)
        self.log.info("Step 3: Creating a json with user name of account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, self.user_name)
        self.log.info("Step 3: json is created with user name of account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 4: Retrieving object from a bucket using account 1")
        resp = self.s3_obj.get_object(
            self.bucket_name, "obj_policy")
        assert resp[0], resp[1]
        self.log.info("Step 4: Retrieved object from a bucket using account 1")
        self.log.info("Step 5: Retrieving object using user of account 2")
        resp = iam_obj_acc_2.create_access_key(self.user_name)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_2 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_2.get_object(
                self.bucket_name, "obj_policy")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 5: Retrieving object using user of account 2 is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Test principal arn combination with user name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6057")
    @CTFailOn(error_handler)
    def test_691(self):
        """Test principal arn combination with account-id."""
        self.log.info(
            "STARTED: Test principal arn combination with account-id")
        bucket_policy = BKT_POLICY_CONF["test_691"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1: Creating a bucket and uploading objects using account 1")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey691_2")
        self.log.info(
            "Step 1: Created a bucket and uploading objects using account 1")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_acc_2 = create_account[1]
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        self.log.info(
            "Step 2: Creating a user with name %s in account 2",
            self.user_name)
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_obj_acc_2.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_obj_acc_2)
        self.log.info(
            "Step 2: User is created with name %s in account 2",
            self.user_name)
        self.log.info("Step 3: Creating a json with combination of account id")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info("Step 3: json is created with combination of account id")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 4: Retrieving object using account 2")
        resp = s3_obj_acc_2.get_object(
            self.bucket_name, "obj_policy")
        assert resp[0], resp[1]
        self.log.info("Step 4: Retrieved object using account 2")
        self.log.info("Step 5: Retrieving object using user of account 2")
        resp = iam_obj_acc_2.create_access_key(self.user_name)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_2 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_2.get_object(
                self.bucket_name, "obj_policy")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 5: Retrieving object using user of account 2 is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Test principal arn combination with account-id")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5996")
    @CTFailOn(error_handler)
    def test_4134(self):
        """Create Bucket Policy using NumericLessThan Condition Operator, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThan Condition"
            " Operator,key s3:max-keys and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4134"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericLessThan",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        resp = s3_obj_2.list_objects_with_prefix(
            self.bucket_name, maxkeys=4)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Verified the object listing from the second account")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThan Condition"
            " Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5994")
    @CTFailOn(error_handler)
    def test_4136(self):
        """Create Bucket Policy using NumericLessThan Condition Operator, key s3:max-keys and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThan Condition Operator,"
            "key s3:max-keys and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4136"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericLessThan",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        try:
            s3_obj_2.list_objects_with_prefix(
                self.bucket_name, maxkeys=4)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Verified that listing of object from second account failing with error: %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThan Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5992")
    @CTFailOn(error_handler)
    def test_4143(self):
        """Create Bucket Policy using NumericGreaterThan Condition Operator, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThan Condition"
            " Operator,key s3:max-keys and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4143"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericGreaterThan",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        resp = s3_obj_2.list_objects_with_prefix(
            self.bucket_name, maxkeys=11)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Verified the object listing from the second account")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThan Condition"
            " Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5985")
    @CTFailOn(error_handler)
    def test_4144(self):
        """Create Bucket Policy using NumericGreaterThan Condition Operator, key s3:max-keys and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThan Condition Operator,"
            "key s3:max-keys and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4144"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericGreaterThan",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        try:
            s3_obj_2.list_objects_with_prefix(
                self.bucket_name, maxkeys=11)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4:Verified that listing of object from second account failing with error: %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThan Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5983")
    @CTFailOn(error_handler)
    def test_4145(self):
        """Create Bucket Policy using NumericEquals Condition Operator, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericEquals Condition"
            " Operator,key s3:max-keys and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4145"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericEquals Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericEquals Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericEquals",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        resp = s3_obj_2.list_objects_with_prefix(
            self.bucket_name, maxkeys=10)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Verified the object listing from the second account")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericEquals Condition"
            " Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5980")
    @CTFailOn(error_handler)
    def test_4146(self):
        """Create Bucket Policy using NumericNotEquals Condition Operator, key s3:max-keys and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericNotEquals Condition Operator,"
            "key s3:max-keys and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4146"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericNotEquals Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericNotEquals Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericNotEquals",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        try:
            s3_obj_2.list_objects_with_prefix(
                self.bucket_name, maxkeys=10)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Verified that listing of object from second account failing with error: %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericNotEquals Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5978")
    @CTFailOn(error_handler)
    def test_4147(self):
        """Create Bucket Policy using NumericLessThanEquals Condition Operator, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThanEquals "
            "Condition Operator,key s3:max-keys and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4147"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericEquals Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericLessThanEquals Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericLessThanEquals",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list object from another account")
        resp = s3_obj_2.list_objects_with_prefix(
            self.bucket_name, maxkeys=10)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Verified the object listing from the second account")
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThanEquals "
            "Condition Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5976")
    @CTFailOn(error_handler)
    def test_4148(self):
        """Create Bucket Policy using NumericGreaterThanEquals Condition Operator, key s3:max-keys and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator,"
            "key s3:max-keys and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4148"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            "obj_policy")
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        s3_obj_2 = create_account[1]
        self.log.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericGreaterThanEquals Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        self.log.debug("json string is : %s", bkt_json_policy)
        self.log.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericNotEquals Condition Operator")
        self.log.info("Step 2: Apply the bucket policy on the bucket")
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket policy was applied successfully")
        self.log.info("Step 3: Verify bucket policy")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        assert_utils.assert_equals(
            bucket_policy[0],
            "NumericGreaterThanEquals",
            resp[1])
        self.log.info("Step 3: Bucket policy was verified successfully")
        self.log.info(
            "Step 4: Verify the list of objects from another account")
        try:
            s3_obj_2.list_objects_with_prefix(
                self.bucket_name, maxkeys=10)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Verified that listing of object "
            "from second account failing with error: %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6109")
    @CTFailOn(error_handler)
    def test_1190(self):
        """Test bucket policy with Effect "Allow" and "Deny " using invalid user id."""
        self.log.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using invalid user id")
        bucket_policy = BKT_POLICY_CONF["test_1190"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        create_account = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = create_account[6]
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Applying bucket policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"][0] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"][0]. \
            format(account_id)
        bucket_policy["Statement"][1]["Principal"]["AWS"][0] = \
            bucket_policy["Statement"][1]["Principal"]["AWS"][0]. \
            format(account_id)
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR in error.message, error.message
            self.log.info(
                "Step 2 : Applying policy on a bucket is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using invalid user id")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6111")
    @CTFailOn(error_handler)
    def test_1180(self):
        """Test Bucket policy on action field with delete-bucket-policy where effect is
        Allow and verify user can delete-bucket-policy."""
        self.log.info(
            "STARTED: Test Bucket policy on action field with delete-bucket-policy "
            "where effect is Allow and verify user can delete-bucket-policy")
        bucket_policy = BKT_POLICY_CONF["test_1180"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info("Step 2: Deleting bucket policy with users credentials")
        resp = s3_policy_usr_obj.delete_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Bucket policy is deleted with users credentials")
        self.log.info(
            "Step 3: Verifying that bucket policy is deleted from a bucket %s",
            self.bucket_name)
        try:
            self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_NO_SUCH_ERR in error.message, error.message
        self.log.info(
            "Step 3: Verified that policy is deleted from a bucket %s",
            self.bucket_name)
        self.log.info(
            "ENDED: Test Bucket policy on action field with delete-bucket-policy where "
            "effect is Allow and verify user can delete-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6110")
    @CTFailOn(error_handler)
    def test_1191(self):
        """Test bucket policy with Effect "Allow" and "Deny " using invalid Account id."""
        self.log.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using invalid Account id")
        bucket_policy = BKT_POLICY_CONF["test_1191"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Applying policy on a bucket %s", self.bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR in error.message, error.message
            self.log.info("Step 2: Applying policy on a bucket is "
                          "failed with error %s", error.message)
        self.log.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using invalid Account id")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6112")
    @CTFailOn(error_handler)
    def test_1184(self):
        """Test bucket policy with Wildcard ? in action for delete bucket policy."""
        self.log.info(
            "Test bucket policy with Wildcard ? in action for delete bucket policy")
        bucket_policy = BKT_POLICY_CONF["test_1184"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Applying policy on a bucket %s", self.bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_INVALID_ACTION_ERR in error.message, error.message
            self.log.info("Step 2: Applying policy on a bucket is "
                          "failed with error %s", error.message)
        self.log.info(
            "ENDED: Test bucket policy with Wildcard ? in action for delete bucket policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6113")
    @CTFailOn(error_handler)
    def test_1171(self):
        """Test Bucket policy on action field with get-bucket-policy
         and verify other account can get-bucket-policy."""
        self.log.info(
            "STARTED: Test Bucket policy on action field with get-bucket-policy"
            " and verify other account can get-bucket-policy")
        bucket_policy = BKT_POLICY_CONF["test_1171"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        resp = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_bkt_policy = resp[3]
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 2: Retrieving policy of a bucket %s "
            "from another account %s", self.bucket_name, self.account_name)
        try:
            s3_bkt_policy.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 2: Retrieving policy of a bucket from another account "
                "is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test Bucket policy on action field with get-bucket-policy "
            "and verify other account can get-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6114")
    @CTFailOn(error_handler)
    def test_1182(self):
        """Test Bucket policy on action field with delete-bucket-policy where effect is
         Deny and verify user can delete-bucket-policy."""
        self.log.info(
            "STARTED: Test Bucket policy on action field with delete-bucket-policy where effect "
            "is Deny and verify user can delete-bucket-policy")
        bucket_policy = BKT_POLICY_CONF["test_1182"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info("Step 2: Deleting bucket policy with users credentials")
        try:
            s3_policy_usr_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info("Step 2: Deleting policy with users credential is "
                          "failed with error %s", error.message)
        self.log.info(
            "ENDED: Test Bucket policy on action field with delete-bucket-policy where effect "
            "is Deny and verify user can delete-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6115")
    @CTFailOn(error_handler)
    def test_1110(self):
        """Test bucket policy statement Effect "Deny" using json."""
        self.log.info(
            "STARTED: Test bucket policy statement Effect Deny using json")
        bucket_policy_1 = BKT_POLICY_CONF["test_1110"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_1110"]["bucket_policy_2"]
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy_1)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info(
            "Step 2: Applying policy on a bucket with users credentials")
        bkt_policy_json = json.dumps(bucket_policy_2)
        try:
            s3_policy_usr_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: Applying policy on a bucket with users credential is "
                "failed with error %s", error.message)
        self.log.info(
            "ENDED: Test bucket policy statement Effect Deny using json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6116")
    @CTFailOn(error_handler)
    def test_1187(self):
        """Test bucket policy with Effect "Allow " and "Deny" using user id."""
        self.log.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using user id")
        bucket_policy = BKT_POLICY_CONF["test_1187"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        resp = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3test_obj_1 = resp[1]
        s3_policy_obj = resp[3]
        access_key = resp[4]
        secret_key = resp[5]
        account_id = resp[6]
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3test_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating a new user with name %s and "
            "also creating credentials for the same user", self.user_name)
        resp = iam_new_obj.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_new_obj)
        resp = iam_new_obj.create_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info("Step 2: Created an user and credentials for that user")
        self.log.info(
            "Step 3: Applying policy on a bucket %s", self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"][0] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"][0].format(account_id,
                                                                        self.user_name)
        bucket_policy["Statement"][1]["Principal"]["AWS"][0] = \
            bucket_policy["Statement"][1]["Principal"]["AWS"][0].format(account_id,
                                                                        self.user_name)
        bkt_policy_json = json.dumps(bucket_policy)
        resp = s3_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Applied policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 4: Retrieving policy of a bucket %s", self.bucket_name)
        resp = s3_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        self.log.info(
            "Step 4: Retrieved policy of a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Retrieving policy of a bucket using users credentials")
        resp = s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        self.log.info(
            "Step 5: Retrieved policy of a bucket using users credentials")
        self.log.info(
            "Step 6: Deleting policy of a bucket using users credentials")
        try:
            s3_policy_usr_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 6: Deleting policy of a bucket is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using user id")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6117")
    @CTFailOn(error_handler)
    def test_1166(self):
        """Test * Wildcard for all s3apis in action field of statement of the json file with effect "Allow"."""
        self.log.info(
            "STARTED: Test * Wildcard for all s3apis in "
            "action field of statement of the json file with effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_1166"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info(
            "Step 2: Retrieving policy of a bucket using users cedentials")
        resp = s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Retrieved policy of a bucket using users credentials")
        self.log.info(
            "ENDED: Test * Wildcard for all s3apis in "
            "action field of statement of the json file with effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6118")
    @CTFailOn(error_handler)
    def test_1177(self):
        """Test Bucket policy on action field with delete-bucket-policy
        and verify other account can delete-bucket-policy."""
        self.log.info(
            "STARTED: Test Bucket policy on action field with "
            "delete-bucket-policy and verify other account can delete-bucket-policy")
        bucket_policy = BKT_POLICY_CONF["test_1177"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        resp = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_policy_obj = resp[3]
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 2: Deleting a bucket policy with another account %s",
            self.account_name)
        try:
            s3_policy_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 2: Deleting bucket policy is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Test Bucket policy on action field with delete-bucket-policy"
            " and verify other account can delete-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6119")
    @CTFailOn(error_handler)
    def test_360(self):
        """Apply put-bucket-policy on existing bucket."""
        self.log.info("STARTED: Apply put-bucket-policy on existing bucket")
        bucket_policy = BKT_POLICY_CONF["test_360"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Apply the bucket policy on the bucket with valid json string")
        bkt_json_policy = json.dumps(bucket_policy)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Bucket policy was successfully apply to the bucket : %s",
            self.bucket_name)
        self.log.info("ENDED: Apply put-bucket-policy on existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6120")
    @CTFailOn(error_handler)
    def test_362(self):
        """Apply put-bucket-policy on non existing bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy on non existing bucket")
        bucket_policy = BKT_POLICY_CONF["test_362"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 2: Apply the bucket policy on the non-existing bucket")
        bkt_json_policy = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 2: Put Bucket policy failed with error message : %s",
            "NoSuchBucket")
        self.log.info(
            "Step 2: Bucket policy was successfully apply to the bucket : %s",
            self.bucket_name)
        self.log.info("ENDED: Apply put-bucket-policy on non existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6121")
    @CTFailOn(error_handler)
    def test_363(self):
        """Apply put-bucket-policy without specifying bucket name."""
        self.log.info(
            "STARTED: Apply put-bucket-policy without specifying bucket name")
        bucket_policy = BKT_POLICY_CONF["test_363"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        bkt_json_policy = json.dumps(bucket_policy)
        self.log.info("Step 1: Put Bucket policy without bucket name")
        try:
            bucket_name = None
            self.s3_bkt_policy_obj.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert "expected string" in error.message, error.message
        self.log.info(
            "Step 1: Put Bucket policy failed with error message : %s",
            "expected string")
        self.log.info(
            "ENDED: Apply put-bucket-policy without specifying bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6122")
    @CTFailOn(error_handler)
    def test_364(self):
        """Test Apply put-bucket-policy without specifying policy."""
        self.log.info(
            "STARTED: Apply put-bucket-policy without specifying policy")
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Apply the bucket policy on the bucket with invalid json string")
        try:
            json_policy = None
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert "Parameter validation failed" in error.message, error.message
        self.log.info(
            "Step 2: Put Bucket policy operation failed with error message : %s",
            "Parameter validation failed")
        self.log.info(
            "ENDED: Apply put-bucket-policy without specifying policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6123")
    @CTFailOn(error_handler)
    def test_365(self):
        """Apply put-bucket-policy with specifying policy in non json format."""
        self.log.info(
            "STARTED: Apply put-bucket-policy with specifying policy in non json format")
        bucket_policy = BKT_POLICY_CONF["test_365"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1 : Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket is created with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Apply the bucket policy on the bucket with invalid json string")
        bkt_json_policy = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, json.loads(bkt_json_policy))
        except CTException as error:
            self.log.error(error.message)
            assert "Parameter validation failed" in error.message, error.message
        self.log.info(
            "Step 2: Put Bucket policy failed with error message : %s",
            "Parameter validation failed")
        self.log.info(
            "ENDED: Apply put-bucket-policy with specifying policy in non json format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6124")
    @CTFailOn(error_handler)
    def test_366(self):
        """Apply put-bucket-policy from another account given read permission on bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from another account given read permission on bucket")
        test_366_cfg = BKT_POLICY_CONF["test_366"]
        for i in range(2):
            test_366_cfg["bucket_policy"]["Statement"][i]["Resource"] = test_366_cfg[
                "bucket_policy"]["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        self.log.info(
            "Step 1 : Create a new bucket assign read bucket permission to account2")
        resp = self.acl_obj.create_bucket_with_acl(
            self.bucket_name,
            grant_read="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created with read permission")
        self.put_bucket_policy_with_err(
            self.bucket_name, test_366_cfg, s3_bkt_policy_obj_2)
        self.log.info(
            "ENDED: Apply put-bucket-policy from another account given read permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6125")
    @CTFailOn(error_handler)
    def test_367(self):
        """Apply put-bucket-policy from another account given write permission on bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from "
            "another account given write permission on bucket")
        test_367_cfg = BKT_POLICY_CONF["test_367"]
        for i in range(2):
            test_367_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_367_cfg["bucket_policy"]["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        self.log.info(
            "Step 1 : Create a new bucket assign write bucket permission to account2")
        resp = self.acl_obj.create_bucket_with_acl(
            self.bucket_name,
            grant_write="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created with write permission")
        self.put_bucket_policy_with_err(
            self.bucket_name, test_367_cfg, s3_bkt_policy_obj_2)
        self.log.info(
            "ENDED: Apply put-bucket-policy from another account given write permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6126")
    @CTFailOn(error_handler)
    def test_368(self):
        """Apply put-bucket-policy from another account given read-acp permission on bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from another account given read-acp permission on bucket")
        test_368_cfg = BKT_POLICY_CONF["test_368"]
        test_368_cfg["bucket_policy"]["Statement"][0]["Resource"] = \
            test_368_cfg["bucket_policy"]["Statement"][0][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        self.log.info(
            "Step 1 : Create a new bucket assign read-acp bucket permission to account2")
        resp = self.acl_obj.create_bucket_with_acl(
            self.bucket_name,
            grant_read_acp="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created with read-acp permission")
        self.put_bucket_policy_with_err(
            self.bucket_name, test_368_cfg, s3_bkt_policy_obj_2)
        self.log.info(
            "ENDED: Apply put-bucket-policy from "
            "another account given read-acp permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6127")
    @CTFailOn(error_handler)
    def test_369(self):
        """Apply put-bucket-policy from another account given write-acp permission on bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from "
            "another account given write-acp permission on bucket")
        test_369_cfg = BKT_POLICY_CONF["test_369"]
        for i in range(2):
            test_369_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_369_cfg["bucket_policy"]["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        self.log.info(
            "Step 1 : Create a new bucket assign write-acp bucket permission to account2")
        resp = self.acl_obj.create_bucket_with_acl(
            self.bucket_name,
            grant_write_acp="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created with write-acp permission")
        self.put_bucket_policy_with_err(
            self.bucket_name, test_369_cfg, s3_bkt_policy_obj_2)
        self.log.info(
            "ENDED: Apply put-bucket-policy from another "
            "account given write-acp permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6128")
    @CTFailOn(error_handler)
    def test_370(self):
        """Apply put-bucket-policy from another account given full-control permission on bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from another "
            "account given full-control permission on bucket")
        test_370_cfg = BKT_POLICY_CONF["test_370"]
        for i in range(2):
            test_370_cfg["bucket_policy"]["Statement"][i]["Resource"] = \
                test_370_cfg["bucket_policy"]["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        self.log.info(
            "Step 1 : Create a new bucket assign full-control bucket permission to account2")
        resp = self.acl_obj.create_bucket_with_acl(
            self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket was created with full-control permission")
        self.put_bucket_policy_with_err(
            self.bucket_name, test_370_cfg, s3_bkt_policy_obj_2)
        self.log.info(
            "ENDED: Apply put-bucket-policy from "
            "another account given full-control permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6129")
    @CTFailOn(error_handler)
    def test_371(self):
        """Apply put-bucket-policy from another account with no permissions."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from another account with no permissions.")
        bucket_policy = BKT_POLICY_CONF["test_371"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info("Step 1 : Create a new bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 1 : Bucket was created")
        self.log.info(
            "Step 2: Apply put bucket policy on the bucket using account 2")
        bkt_json_policy = json.dumps(bucket_policy)
        try:
            s3_bkt_policy_obj_2.put_bucket_policy(
                self.bucket_name, bkt_json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 2: Put Bucket policy from second account failing with error: %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="private")
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Apply put-bucket-policy from another account with no permissions.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6131")
    @CTFailOn(error_handler)
    def test_372(self):
        """Apply put-bucket-policy from another account with authenticated-read permission on bucket."""
        self.log.info(
            "STARTED: Apply put-bucket-policy from another "
            "account with authenticated-read permission on bucket")
        bucket_policy = BKT_POLICY_CONF["test_372"]["bucket_policy"]
        for _ in range(2):
            bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
                "Resource"].format(self.bucket_name)
        result_2 = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_bkt_policy_obj_2 = result_2[3]
        self.log.info("Step 1 : Create a new bucket assign"
                      " authenticated-read bucket permission to account2")
        resp = self.acl_obj.create_bucket_with_acl(
            self.bucket_name, acl="authenticated-read")
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Bucket was created with authenticated-read permission")
        self.log.info("Step 2: Get bucket acl")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket ACL was verified")
        self.log.info(
            "Step 2: Apply put bucket policy on the bucket using account 2")
        bkt_json_policy = json.dumps(bucket_policy)
        try:
            s3_bkt_policy_obj_2.put_bucket_policy(
                self.bucket_name, bkt_json_policy)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 2: Put Bucket policy from second account failing with error: %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="private")
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Apply put-bucket-policy from another account with "
            "authenticated-read permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6132")
    @CTFailOn(error_handler)
    def test_373(self):
        """Test Apply put-bucket-policy from public domain with public-read permission on bucket."""
        self.log.info(
            "STARTED: Test Apply put-bucket-policy from public"
            " domain with public-read permission on bucket")
        bucket_policy = BKT_POLICY_CONF["test_373"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 1: Applying public-read acl to a bucket")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="public-read")
        assert resp[0], resp[1]
        self.log.info("Step 1: Applied public-read acl to a bucket")
        self.log.info("Step 2: Retrieving acl of a bucket")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Retrieved acl of a bucket")
        self.log.info("Step 3: Applying policy on a bucket")
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.no_auth_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Applying policy on a bucket is failed with error %s",
                error.message)
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="private")
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Test Apply put-bucket-policy from public"
            " domain with public-read permission on bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6133")
    @CTFailOn(error_handler)
    def test_374(self):
        """Test Apply put-bucket-policy from public domain with public-read-write permission on bucket."""
        self.log.info(
            "STARTED: Test Apply put-bucket-policy from public "
            "domain with public-read-write permission on bucket")
        bucket_policy = BKT_POLICY_CONF["test_374"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info("Step 1. Applying public-read-write acl to a bucket")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="public-read-write")
        assert resp[0], resp[1]
        self.log.info("Step 1. Applied public-read-write acl to a bucket")
        self.log.info("Step 2: Retrieving acl of a bucket")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Retrieved acl of a bucket")
        self.log.info("Step 3: Applying policy on a bucket")
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.no_auth_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Applying policy on a bucket is failed with error %s",
                error.message)
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, acl="private")
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Test Apply put-bucket-policy from public "
            "domain with public-read-write permission on bucket.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6134")
    @CTFailOn(error_handler)
    def test_1188(self):
        """Test bucket policy with Effect "Allow " and "Deny" using account id and verify other account can delete-bucket-policy."""
        self.log.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using account id")
        bucket_policy = BKT_POLICY_CONF["test_1188"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        resp = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_policy_obj = resp[3]
        account_id = resp[6]
        self.create_bucket_validate(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][1]["Principal"]["AWS"] = \
            bucket_policy["Statement"][1]["Principal"]["AWS"].format(account_id)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 2: Retrieving bucket policy from another account %s",
            self.account_name)
        try:
            s3_policy_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 2:  Retrieving bucket policy from "
                "another account is failed with error %s", error.message)
        self.log.info(
            "Step 3: Deleting policy of a bucket with another account %s",
            self.account_name)
        try:
            s3_policy_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Deleting policy of a bucket "
                "with another account is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using account id")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6136")
    @CTFailOn(error_handler)
    def test_1174(self):
        """Test Bucket policy on action field with put-bucket-policy and verify other account can put-bucket-policy."""
        self.log.info(
            "STARTED: Test Bucket policy on action field with"
            "put-bucket-policy and verify other account can put-bucket-policy")
        bucket_policy = BKT_POLICY_CONF["test_1174"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        resp = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_policy_obj = resp[3]
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info(
            "Step 2: Applying bucket policy from another account %s",
            self.account_name)
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            s3_policy_obj.put_bucket_policy(self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 2: Applying bucket policy from another "
                "account is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test Bucket policy on action field with put-bucket-policy "
            "and verify other account can put-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6138")
    @CTFailOn(error_handler)
    def test_1185(self):
        """Test Wildcard * in action for delete bucket policy with effect is Deny."""
        self.log.info(
            "STARTED: Test Wildcard * in action for delete bucket policy with effect is Deny")
        bucket_policy = BKT_POLICY_CONF["test_1185"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info("Step 2: Deleting bucket policy with users credentials")
        try:
            s3_policy_usr_obj.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: Deleting bucket policy with users "
                "credentials is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test Wildcard * in action for delete bucket policy with effect is Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6140")
    @CTFailOn(error_handler)
    def test_1186(self):
        """Test Wildcard * in action where effect is Allow."""
        self.log.info(
            "STARTED: Test Wildcard * in action where effect is Allow")
        bucket_policy = BKT_POLICY_CONF["test_1186"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info("Step 2: Deleting bucket policy with users credentials")
        resp = s3_policy_usr_obj.delete_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Bucket policy is deleted with users credentials")
        self.log.info(
            "Step 3: Verifying that bucket policy is deleted from a bucket %s",
            self.bucket_name)
        try:
            self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_NO_SUCH_ERR in error.message, error.message
            self.log.info(
                "Step 3: Verified that policy is deleted from a bucket %s",
                self.bucket_name)
        self.log.info(
            "ENDED: Test Wildcard * in action where effect is Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6142")
    @CTFailOn(error_handler)
    def test_1114(self):
        """Test bucket policy statement Effect "Allow" and "Deny" combinations using json."""
        self.log.info(
            "STARTED: Test bucket policy statement Effect Allow and Deny combinations using json")
        bucket_policy = BKT_POLICY_CONF["test_1114"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info(
            "Step 2: Retrieving bucket policy with users credentials")
        resp = s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Bucket policy is retrieved with users credentials")
        self.log.info(
            "Step 3: Applying bucket policy with users credentials")
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            s3_policy_usr_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Applying bucket policy with users "
                "credentials is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test bucket policy statement Effect Allow and Deny combinations using json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6144")
    @CTFailOn(error_handler)
    def test_1169(self):
        """Test * Wildcard for all s3apis in action field of statement of the json file with combination effect "Allow" and "Deny"."""
        self.log.info(
            "STARTED: Test * Wildcard for all s3apis in action field of "
            "statement of the json file with combination effect Allow and Deny")
        bucket_policy = BKT_POLICY_CONF["test_1169"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info("Step 2: Applying bucket policy with users credentials")
        bkt_policy_json = json.dumps(bucket_policy)
        resp = s3_policy_usr_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Bucket policy is applied with users credentials")
        self.log.info(
            "Step 3: Retrieving bucket policy with users credentials")
        try:
            s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Retrieving bucket policy with users "
                "credentials is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test * Wildcard for all s3apis in action field of "
            "statement of the json file with combination effect Allow and Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6146")
    @CTFailOn(error_handler)
    def test_1167(self):
        """Test * Wildcard for all s3apis in action field of statement of the json file with effect "Deny"."""
        self.log.info(
            "STARTED: Test * Wildcard for all s3apis in action field "
            "of statement of the json file with effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_1167"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info(
            "Step 2: Retrieving bucket policy with users credentials")
        try:
            s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: Retrieving bucket policy with users "
                "credentials is failed with error %s", error.message)
        # Cleanup activity
        self.s3_bkt_policy_obj.delete_bucket_policy(self.bucket_name)
        self.log.info(
            "ENDED: Test * Wildcard for all s3apis in action field "
            "of statement of the json file with effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6147")
    @CTFailOn(error_handler)
    def test_1113(self):
        """Test bucket policy statement Effect "None" using json."""
        self.log.info(
            "STARTED: Test bucket policy statement Effect None using json")
        bucket_policy = BKT_POLICY_CONF["test_1113"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info(
            "Step 2: Applying policy on a bucket %s with effect none",
            self.bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert "Invalid effect" in error.message, error.message
            self.log.info(
                "Step 2: Applying policy on a bucket with "
                "effect none is failed with error %s", error.message)
        self.log.info(
            "ENDED: Test bucket policy statement Effect None using json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6148")
    @CTFailOn(error_handler)
    def test_1116(self):
        """Test bucket policy statement Effect "Allow", "Deny" and "None" combinations using json."""
        self.log.info(
            "STARTED: Test bucket policy statement Effect Allow, "
            "Deny and None combinations using json")
        bucket_policy = BKT_POLICY_CONF["test_1116"]["bucket_policy"]
        for i in range(3):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.log.info(
            "Step 2: Applying policy on a bucket %s", self.bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert "Invalid effect" in error.message, error.message
            self.log.info(
                "Step 2: Applying policy on a bucket is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: STARTED: Test bucket policy statement Effect Allow, "
            "Deny and None combinations using json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6012")
    @CTFailOn(error_handler)
    def test_1109(self):
        """Test bucket policy statement Effect "Allow" using json."""
        self.log.info(
            "STARTED: Test bucket policy statement Effect Allow using json")
        bucket_policy_1 = BKT_POLICY_CONF["test_1109"]["bucket_policy_1"]
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy_2 = BKT_POLICY_CONF["test_1109"]["bucket_policy_2"]
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy_1)
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        self.log.info(
            "Step 2: Applying bucket policy with users credentials")
        bkt_policy_json = json.dumps(bucket_policy_2)
        resp = s3_policy_usr_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Policy is applied to a bucket %s with users credentials",
            self.bucket_name)
        self.log.info(
            "Step 3: Retrieving policy of a bucket with users credentials")
        try:
            s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Retrieving bucket policy with users "
                "credentials is failed with error %s", error.message)
        self.log.info(
            "Step 4: Retrieving policy of a bucket with accounts credentials")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        self.log.info(
            "Step 4: Retrieved policy of a bucket with accounts credentials")
        self.log.info(
            "ENDED: Test bucket policy statement Effect Allow using json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7692")
    @CTFailOn(error_handler)
    def test_270(self):
        """verify get-bucket-policy for the bucket which is having read permissions for account2."""
        self.log.info(
            "STARTED: verify get-bucket-policy for the bucket which is having read permissions for account2")
        bucket_policy = BKT_POLICY_CONF["test_270"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.log.info(
            "Creating two account with name prefix as %s",
            self.account_name)
        acc_detail = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_detail.append(resp)
            self.account_list.append(acc_name)
        canonical_id_user_1 = acc_detail[0][1]["canonical_id"]
        access_key_u1 = acc_detail[0][1]["access_key"]
        secret_key_u1 = acc_detail[0][1]["secret_key"]
        canonical_id_user_2 = acc_detail[1][1]["canonical_id"]
        access_key_u2 = acc_detail[1][1]["access_key"]
        secret_key_u2 = acc_detail[1][1]["secret_key"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        s3acltest_obj_1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.s3test_obj_1 = s3_test_lib.S3TestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.log.info(
            "Created account2 with name %s", self.account_name)
        self.log.info("Step 1 : Creating bucket with name {} and setting read "
                      "permission to account2".format(self.bucket_name))
        resp = s3acltest_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1),
            grant_read="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Created bucket with name {} and set read "
                      "permission to account2".format(self.bucket_name))
        self.log.info(
            "Step 2: Verifying get bucket acl with account1")
        resp = s3acltest_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Verified get bucket acl for account1")
        self.log.info(
            "Step 3: Applying bucket policy: %s", bucket_policy)
        bkt_policy_json = json.dumps(bucket_policy)
        resp = s3_policy_usr_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Applied bucket policy to %s", self.bucket_name)
        self.log.info(
            "Step 4: Get bucket policy using account1")
        resp = s3_policy_usr_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Verified get bucket policy for account1")
        self.log.info(
            "Step 5: Get bucket policy using account2")
        s3_policy_usr2_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_u2, secret_key=secret_key_u2)
        try:
            s3_policy_usr2_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 5: Get bucket policy with account2 login is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: verify get-bucket-policy for the bucket which is having read permissions for account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7693")
    @CTFailOn(error_handler)
    def test_271(self):
        """Do not apply policy from account 1 and give read permission to account2 and verify get-bucket-policy."""
        self.log.info(
            "STARTED: Do not apply policy from account 1 and give read permission to account2"
            " and verify get-bucket-policy")
        self.log.info(
            "Creating two account with name prefix as %s",
            self.account_name)
        acc_detail = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_detail.append(resp)
            self.account_list.append(acc_name)
        canonical_id_user_1 = acc_detail[0][1]["canonical_id"]
        access_key_u1 = acc_detail[0][1]["access_key"]
        secret_key_u1 = acc_detail[0][1]["secret_key"]
        canonical_id_user_2 = acc_detail[1][1]["canonical_id"]
        access_key_u2 = acc_detail[1][1]["access_key"]
        secret_key_u2 = acc_detail[1][1]["secret_key"]
        s3acltest_obj_1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.s3test_obj_1 = s3_test_lib.S3TestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.log.info(
            "Created account2 with name %s", self.account_name)
        self.log.info("Step 1 : Creating bucket with name {} and setting read "
                      "permission to account2".format(self.bucket_name))
        resp = s3acltest_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1),
            grant_read="id={}".format(canonical_id_user_2))
        assert resp[0], resp[1]
        self.log.info("Step 1 : Created bucket with name {} and set read "
                      "permission to account2".format(self.bucket_name))
        self.log.info(
            "Step 2: Verifying get bucket acl with account1")
        resp = s3acltest_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Verified get bucket acl for account1")
        self.log.info(
            "Step 3: Get bucket policy using account2")
        s3_policy_usr2_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_u2, secret_key=secret_key_u2)
        try:
            s3_policy_usr2_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 3: Get bucket policy with account2 login is failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Do not apply policy from account 1 and give read permission to account2"
            " and verify get-bucket-policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5974")
    @CTFailOn(error_handler)
    def test_4156(self):
        """Create Bucket Policy using StringEquals Condition Operator, key "s3:prefix" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringEquals "
            "Condition Operator, key 's3:prefix' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4156"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = \
            bucket_policy["Statement"][0]["Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                self.bucket_name,
                self.obj_name_prefix)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Listing object with prefix using another account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using StringEquals "
            "Condition Operator, key 's3:prefix' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5972")
    @CTFailOn(error_handler)
    def test_4161(self):
        """Create Bucket Policy using StringNotEquals Condition
        Operator, key "s3:prefix" and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringNotEquals Condition Operator,"
            " key 's3:prefix' and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4161"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(
            policy_id)
        bucket_policy["Statement"][0]["Sid"] = \
            bucket_policy["Statement"][0]["Sid"].format(
                policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = bucket_policy[
            "Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                self.bucket_name,
                self.obj_name_prefix)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Listing object with prefix using another account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using StringNotEquals "
            "Condition Operator, key 's3:prefix' and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-5957")
    @CTFailOn(error_handler)
    def test_4173(self):
        """Create Bucket Policy using StringEquals Condition Operator, key "s3:prefix" and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringEquals"
            " Condition Operator, key 's3:prefix' and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4173"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(
            policy_id)
        bucket_policy["Statement"][0]["Sid"] = \
            bucket_policy["Statement"][0]["Sid"].format(
                policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = bucket_policy[
            "Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                self.bucket_name,
                self.obj_name_prefix)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Listing object with prefix using another account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using StringEquals "
            "Condition Operator, key 's3:prefix' and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5969")
    @CTFailOn(error_handler)
    def test_4170(self):
        """Create Bucket Policy using StringNotEquals
        Condition Operator, key "s3:prefix" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringNotEquals Condition Operator,"
            " key 's3:prefix' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4170"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(
            policy_id)
        bucket_policy["Statement"][0]["Sid"] = \
            bucket_policy["Statement"][0]["Sid"].format(
                policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = bucket_policy[
            "Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        self.log.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                self.bucket_name,
                self.obj_name_prefix)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Listing object with prefix using another account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Listing object using another account")
        try:
            s3_obj.object_list(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Listing object using another account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Create Bucket Policy using StringNotEquals Condition Operator,"
            " key 's3:prefix' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5955")
    @CTFailOn(error_handler)
    def test_4183(self):
        """Create Bucket Policy using "StringEquals" Condition Operator,
        key "s3:x-amz-grant-write",Effect Allow and Action "s3:ListBucket"."""
        self.log.info(
            "STARTED: Create Bucket Policy using 'StringEquals' Condition Operator,"
            " key 's3:x-amz-grant-write',Effect Allow and Action 's3:ListBucket'")
        bucket_policy = BKT_POLICY_CONF["test_4183"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info("s3_obj : %s", s3_obj)
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(
            policy_id)
        bucket_policy["Statement"][0]["Sid"] = \
            bucket_policy["Statement"][0][
                "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"][
            "s3:x-amz-grant-write"] = bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-write"].format(account_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.log.info(
            "Applying a policy to a bucket %s",
            self.bucket_name)
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_RESOURCE_ERR)
        self.log.info(
            "Applying a policy to a bucket %s failed with %s",
            self.bucket_name,
            errmsg.S3_BKT_POLICY_RESOURCE_ERR)
        self.log.info(
            "ENDED: Create Bucket Policy using 'StringEquals' Condition Operator,"
            " key 's3:x-amz-grant-write',Effect Allow and Action 's3:ListBucket'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6027")
    @CTFailOn(error_handler)
    def test_1069(self):
        """Test invalid Account ID in the bucket policy json."""
        self.log.info(
            "STARTED: Test invalid Account ID in the bucket policy json")
        bucket_policy = BKT_POLICY_CONF["test_1069"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey1069_2")
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test invalid Account ID in the bucket policy json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6025")
    @CTFailOn(error_handler)
    def test_1075(self):
        """Test invalid User name in the bucket policy json."""
        self.log.info(
            "STARTED: Test invalid User name in the bucket policy json")
        bucket_policy = BKT_POLICY_CONF["test_1075"]["bucket_policy"]
        for i in range(2):
            bucket_policy["Statement"][i]["Resource"] = bucket_policy["Statement"][i][
                "Resource"].format(self.bucket_name)
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "obj_policy",
            "objkey1075_2")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        bucket_policy["Statement"][0]["Principal"]["AWS"] = bucket_policy[
            "Statement"][0]["Principal"]["AWS"].format(account_id)
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test invalid User name in the bucket policy json")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7694")
    @CTFailOn(error_handler)
    def test_4502(self):
        """Test Bucket Policy using Condition Operator "DateEquals", key "aws:CurrentTime",
        Effect "Allow", Action "PutObject" and Date format._date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        test_4502_cfg = BKT_POLICY_CONF["test_4502"]
        date_time = date.today().strftime("%Y-%m-%d")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4502_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7695")
    @CTFailOn(error_handler)
    def test_4504(self):
        """Test Bucket Policy using Condition Operator 'DateNotEquals',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        test_4504_cfg = BKT_POLICY_CONF["test_4504"]
        test_4504_cfg["bucket_name"] = self.bucket_name
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4504_cfg)
            time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7696")
    @CTFailOn(error_handler)
    def test_4505(self):
        """Test Bucket Policy using Condition Operator 'DateLessThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        test_4505_cfg = BKT_POLICY_CONF["test_4505"]
        test_4505_cfg["bucket_name"] = self.bucket_name
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4505_cfg)
            time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7697")
    @CTFailOn(error_handler)
    def test_4506(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanEquals',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        test_4506_cfg = BKT_POLICY_CONF["test_4506"]
        test_4506_cfg["bucket_name"] = self.bucket_name
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(account_id, date_time, effect,
                                                 s3_obj_2, test_4506_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7698")
    @CTFailOn(error_handler)
    def test_4507(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        test_4507_cfg = BKT_POLICY_CONF["test_4507"]
        test_4507_cfg["bucket_name"] = self.bucket_name
        date_time = datetime.now().strftime("%Y-%m-%d")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4507_cfg)
            time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7699")
    @CTFailOn(error_handler)
    def test_4508(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        test_4508_cfg = BKT_POLICY_CONF["test_4508"]
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4508_cfg)
            time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7700")
    @CTFailOn(error_handler)
    def test_4509(self):
        """Test Bucket Policy using Condition Operator "DateEquals", key "aws:CurrentTime",
        Effect "Allow", Action "PutObject" and Date format._date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        test_cfg = BKT_POLICY_CONF["test_4509"]
        date_time = date.today().strftime("%Y")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7701")
    @CTFailOn(error_handler)
    def test_4510(self):
        """Test Bucket Policy using Condition Operator 'DateNotEquals',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        test_cfg = BKT_POLICY_CONF["test_4510"]
        date_time = date.today().strftime("%%Y-%m")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7702")
    @CTFailOn(error_handler)
    def test_4511(self):
        """Test Bucket Policy using Condition Operator 'DateLessThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        test_cfg = BKT_POLICY_CONF["test_4511"]
        date_time = date.today().strftime("%Y-%m-%d")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7703")
    @CTFailOn(error_handler)
    def test_4512(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        test_cfg = BKT_POLICY_CONF["test_4512"]
        date_time = date.today().strftime("%Y")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7704")
    @CTFailOn(error_handler)
    def test_4513(self):
        """Test Bucket Policy using Condition Operator 'DateNotEquals',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id = str(time.time())
        test_cfg = BKT_POLICY_CONF["test_4513"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, random_id, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7705")
    @CTFailOn(error_handler)
    def test_4514(self):
        """Test Bucket Policy using Condition Operator 'DateLessThan',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id = str(time.time())
        test_cfg = BKT_POLICY_CONF["test_4514"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, random_id, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7706")
    @CTFailOn(error_handler)
    def test_4515(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanEquals',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")
        date_time = str(time.time()).split(".")[0]
        test_cfg = BKT_POLICY_CONF["test_4515"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7707")
    @CTFailOn(error_handler)
    def test_4516(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThan',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format
_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id = str(time.time())
        test_cfg = BKT_POLICY_CONF["test_4507"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, random_id, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7708")
    @CTFailOn(error_handler)
    def test_4517(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
        "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format_date."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")
        date_time = time.time()
        test_cfg = BKT_POLICY_CONF["test_4508"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        for effect in ["Allow", "Deny"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6929")
    @CTFailOn(error_handler)
    def test_5770(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        test_cfg = BKT_POLICY_CONF["test_5770"]
        date_time = date.today().strftime("%Y-%m-%d")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6930")
    @CTFailOn(error_handler)
    def test_5831(self):
        """Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists',
        key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")
        date_time = str(time.time()).split(".")[0]
        test_cfg = BKT_POLICY_CONF["test_5831"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6931")
    @CTFailOn(error_handler)
    def test_5832(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanIfExists',
        key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")
        date_time = str(time.time()).split(".")[0]
        test_cfg = BKT_POLICY_CONF["test_5832"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6932")
    @CTFailOn(error_handler)
    def test_5778(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
        test_cfg = BKT_POLICY_CONF["test_5778"]
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Allow", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6933")
    @CTFailOn(error_handler)
    def test_5740(self):
        """Test Bucket Policy using Condition Operator 'DateEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
        test_cfg = BKT_POLICY_CONF["test_5740"]
        date_time = date.today().strftime("%Y-%m-%d")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Allow", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6934")
    @CTFailOn(error_handler)
    def test_5751(self):
        """Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        test_cfg = BKT_POLICY_CONF["test_5751"]
        date_time = date.today().strftime("%Y-%m-%dT%H:%M:%SZ")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6935")
    @CTFailOn(error_handler)
    def test_5773(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanIfExist',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanIfExist', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        test_cfg = BKT_POLICY_CONF["test_5773"]
        date_time = date.today().strftime("%Y-%m-%d")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanIfExist', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6938")
    @CTFailOn(error_handler)
    def test_5764(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
        bucket_policy = BKT_POLICY_CONF["test_5764"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        date_time_res = datetime.now() + timedelta(1)
        date_time = date_time_res.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]

        bkt_json_policy = eval(json.dumps(bucket_policy))
        dt_condition = bkt_json_policy["Statement"][0]["Condition"]
        condition_key = list(
            dt_condition["DateLessThanEqualsIfExists"].keys())[0]
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        bkt_json_policy["Statement"][0]["Condition"]["DateLessThanEqualsIfExists"
                                                     ][condition_key] = date_time
        bkt_json_policy["Statement"][0]["Resource"] = bkt_json_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.put_get_bkt_policy(self.bucket_name, bkt_json_policy)
        resp = s3_obj_2.put_object(
            self.bucket_name, self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Uploading object to s3 bucket with second account")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6939")
    @CTFailOn(error_handler)
    def test_5758(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanIfExists',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        test_cfg = BKT_POLICY_CONF["test_5758"]
        date_time = date.today().strftime("%Y-%m-%dT%H:%M:%S")
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6970")
    @CTFailOn(error_handler)
    def test_5925(self):
        """Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists',
        key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")
        date_time_res = datetime.now() + timedelta(1)
        date_time = int(date_time_res.timestamp())
        bucket_policy = BKT_POLICY_CONF["test_5925"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_validate(self.bucket_name)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        self.log.info(
            "Creating a json with DateLessThanEqualsIfExists condition")
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Condition"]["DateLessThanEqualsIfExists"]["aws:EpochTime"] = \
            bucket_policy["Statement"][0]["Condition"]["DateLessThanEqualsIfExists"][
                "aws:EpochTime"].format(date_time)
        self.log.info(
            "Created a json with DateLessThanEqualsIfExists condition")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Uploading an object from account 2")
        system_utils.create_file(self.file_path, 10)
        resp = s3_obj_2.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded from account 2")
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6971")
    @CTFailOn(error_handler)
    def test_5926(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject'."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject'.")
        date_time = str(time.time()).split(".")[0]
        test_cfg = BKT_POLICY_CONF["test_5926"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Deny", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject'.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6972")
    @CTFailOn(error_handler)
    def test_5937(self):
        """Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists',
        key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'."""
        self.log.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")
        date_time = str(time.time()).split(".")[0]
        test_cfg = BKT_POLICY_CONF["test_5937"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        account_id = result[6]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, "Allow", s3_obj_2, test_cfg)
        self.log.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7709")
    @CTFailOn(error_handler)
    def test_1902(self):
        """Create Bucket Policy using "StringEquals" Condition Operator,
        key "s3:x-amz-acl" and value "public-read"."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value public-read")
        bucket_policy = BKT_POLICY_CONF["test_1902"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        acl_obj_2 = result[2]
        account_id = result[6]
        resp = self.s3_obj.create_bucket_put_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            10)
        assert resp[0], resp[1]
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        bkt_json_policy["Statement"][0]["Resource"] = bkt_json_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.put_get_bkt_policy(self.bucket_name, bkt_json_policy)
        self.log.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp = acl_obj_2.put_object_with_acl(
            self.bucket_name,
            "objkey_test_2",
            self.file_path,
            acl="public-read")
        assert resp[0], resp[1]
        try:
            s3_obj_2.put_object(
                self.bucket_name,
                "objkey_test_2",
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: Uploading object to a bucket failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value public-read")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7710")
    @CTFailOn(error_handler)
    def test_1903(self):
        """Create Bucket Policy using "StringEquals" Condition Operator,
        key "s3:x-amz-acl" and value "bucket-owner-full-control"."""
        self.log.info(
            "STARTED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value bucket-owner-full-control")
        bucket_policy = BKT_POLICY_CONF["test_1903"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        acl_obj_2 = result[2]
        account_id = result[6]
        resp = self.s3_obj.create_bucket_put_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            10)
        assert resp[0], resp[1]
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        bkt_json_policy["Statement"][0]["Resource"] = bkt_json_policy["Statement"][0]["Resource"].format(
            self.bucket_name)
        self.put_get_bkt_policy(self.bucket_name, bkt_json_policy)
        self.log.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp = acl_obj_2.put_object_with_acl(
            self.bucket_name,
            "objkey_test_2",
            self.file_path,
            acl="bucket-owner-full-control")
        assert resp[0], resp[1]
        try:
            s3_obj_2.put_object(
                self.bucket_name,
                "objkey_test_2",
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: Uploading object to a bucket failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value bucket-owner-full-control")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7711")
    @CTFailOn(error_handler)
    def test_1904(self):
        """Create Bucket Policy using 'StringEquals' Condition Operator,
        key 's3:x-amz-grant-full-control'."""
        self.log.info(
            "STARTED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-full-control'")
        bucket_policy = BKT_POLICY_CONF["test_1904"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        acl_obj_2 = result[2]
        account_id_2 = result[6]
        canonical_id_2 = result[0]
        resp = self.s3_obj.create_bucket_put_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            10)
        assert resp[0], resp[1]
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id_2
        bkt_json_policy["Statement"][0]["Resource"] = bkt_json_policy["Statement"][0]["Resource"].format(
            self.bucket_name)
        bkt_json_policy["Statement"][0]["Condition"]["StringEquals"][
            "s3:x-amz-grant-full-control"] = bkt_json_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-full-control"].format(canonical_id_2)
        self.put_get_bkt_policy(self.bucket_name, bkt_json_policy)
        self.log.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp = acl_obj_2.put_object_with_acl(
            self.bucket_name,
            "objkey_test_2",
            self.file_path,
            grant_full_control="id={}".format(canonical_id_2))
        assert resp[0], resp[1]
        time.sleep(S3_CFG["sync_delay"])
        self.log.debug("Waiting for Policy to be synced for bucket")
        try:
            s3_obj_2.put_object(
                self.bucket_name,
                "objkey_test_2",
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: Uploading object to a bucket failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-full-control'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7712")
    @CTFailOn(error_handler)
    def test_1908(self):
        """Create Bucket Policy using 'StringEquals' Condition Operator,
        key 's3:x-amz-grant-write-acp''."""
        self.log.info(
            "STARTED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-write-acp'")
        bucket_policy = BKT_POLICY_CONF["test_1908"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        acl_obj_2 = result[2]
        account_id_2 = result[6]
        canonical_id_2 = result[0]
        resp = self.s3_obj.create_bucket_put_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            10)
        assert resp[0], resp[1]
        bkt_json_policy = eval(json.dumps(bucket_policy))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id_2
        bkt_json_policy["Statement"][0]["Resource"] = bkt_json_policy["Statement"][0]["Resource"].format(
            self.bucket_name)
        bkt_json_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-write-acp"] = bkt_json_policy[
            "Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-write-acp"].format(canonical_id_2)
        self.put_get_bkt_policy(self.bucket_name, bkt_json_policy)
        self.log.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp = acl_obj_2.put_object_with_acl(
            self.bucket_name,
            "objkey_test_2",
            self.file_path,
            grant_write_acp="id={}".format(canonical_id_2))
        assert resp[0], resp[1]
        try:
            s3_obj_2.put_object(
                self.bucket_name,
                "objkey_test_2",
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: Uploading object to a bucket failed with error %s",
                error.message)
        self.log.info(
            "ENDED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-write-acp'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6979")
    @CTFailOn(error_handler)
    def test_4937(self):
        """Create Bucket Policy using NumericLessThanIfExists Condition, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4937"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(self.bucket_name, s3_obj1)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[3])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6980")
    @CTFailOn(error_handler)
    def test_4939(self):
        """Create Bucket Policy using NumericLessThanIfExists Condition, key "s3:max-keys" and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4939"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name, 11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            self.bucket_name,
            bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[3])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6981")
    @CTFailOn(error_handler)
    def test_4940(self):
        """
        Bucket policy.

        Create Bucket Policy using NumericGreaterThanIfExists Condition, key "s3:max-keys"
        and Effect Allow.
        """
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4940"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[2], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[3])
        self.list_objects_with_diff_acnt(self.bucket_name, s3_obj1)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[3])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6982")
    @CTFailOn(error_handler)
    def test_4941(self):
        """Create Bucket Policy using NumericGreaterThanIfExists Condition, key "s3:max-keys" and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4941"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[3])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6983")
    @CTFailOn(error_handler)
    def test_4942(self):
        """Create Bucket Policy using NumericEquals Condition Operator, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericEquals"
            " Condition Operator, key 's3:max-keys' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4942"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[2])
        self.list_objects_with_diff_acnt(self.bucket_name, s3_obj1)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[2])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericEquals"
            " Condition Operator, key 's3:max-keys' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6984")
    @CTFailOn(error_handler)
    def test_4943(self):
        """Create Bucket Policy using NumericNotEqualsIfExists Condition,
         key "s3:max-keys" and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericNotEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4943"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[2])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericNotEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6985")
    @CTFailOn(error_handler)
    def test_4944(self):
        """Create Bucket Policy using NumericLessThanEqualsIfExists
         Condition, key "s3:max-keys" and Effect Allow."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericLessThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_4944"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[2])
        self.list_objects_with_diff_acnt(self.bucket_name, s3_obj1)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[2])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericLessThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6986")
    @CTFailOn(error_handler)
    def test_4945(self):
        """Create Bucket Policy using NumericGreaterThanEqualsIfExists Condition, key "s3:max-keys" and Effect Deny."""
        self.log.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_4945"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info("Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(bucket_policy)
        self.log.info("Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        max_key_list = [1, 2, 3, 4]
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj1, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, self.s3_obj, max_key_list[2])
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.log.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6973")
    @CTFailOn(error_handler)
    def test_5449(self):
        """Test Create Bucket Policy using StringEqualsIfExists Condition, key "s3:prefix" and Effect Allow."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition, key s3:prefix and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_5449"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        bucket_policy["Statement"][0]["Condition"]["StringEqualsIfExists"]["s3:prefix"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEqualsIfExists"][
                "s3:prefix"].format(self.obj_name_prefix)
        self.log.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, self.s3_obj, obj_prefix)
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, s3_obj1, obj_prefix)
        self.list_objects_with_diff_acnt(self.bucket_name, s3_obj1)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIfExists"
            " Condition, key s3:prefix and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6974")
    @CTFailOn(error_handler)
    def test_5471(self):
        """Test Create Bucket Policy using StringNotEqualsIfExists
        Condition Operator, key "s3:prefix" and Effect Deny."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_5471"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = \
            bucket_policy["Statement"][0][
                "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, self.s3_obj, obj_prefix)
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj1,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj1, err_message)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6975")
    @CTFailOn(error_handler)
    def test_5473(self):
        """Test Create Bucket Policy using StringNotEqualsIfExists
        Condition Operator, key "s3:prefix" and Effect Allow."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_5473"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.create_bucket_put_objects(
            self.bucket_name, 11, obj_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, self.s3_obj, obj_prefix)
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj1,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(self.bucket_name, s3_obj1)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6976")
    @CTFailOn(error_handler)
    def test_5481(self):
        """Test Create Bucket Policy using StringEqualsIfExists
        Condition Operator, key "s3:prefix" and Effect Deny."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")
        bucket_policy = BKT_POLICY_CONF["test_5481"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        self.create_bucket_put_objects(
            self.bucket_name, 11, obj_prefix)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account1_id = acc_details[0][1]["account_id"]
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[1][1]["access_key"],
            secret_key=acc_details[1][1]["secret_key"])
        self.log.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, self.s3_obj, obj_prefix)
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3_obj)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj1,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj1, err_message)
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            self.bucket_name, s3_obj2, err_message)
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-6977")
    @CTFailOn(error_handler)
    def test_5490(self):
        """Test Create Bucket Policy using "StringEqualsIfExists" Condition Operator,
        key "s3:x-amz-grant-write",Effect Allow and Action "s3:ListBucket"."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:x-amz-grant-write,Effect Allow and Action s3:ListBucket")
        bucket_policy = BKT_POLICY_CONF["test_5490"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            11,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        self.log.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringEqualsIfExists"]["s3:x-amz-grant-write"] =\
            bucket_policy["Statement"][0]["Condition"]["StringEqualsIfExists"][
                "s3:x-amz-grant-write"].format(account_id)
        self.log.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_RESOURCE_ERR)
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:x-amz-grant-write,Effect Allow and Action s3:ListBucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-18450")
    @CTFailOn(error_handler)
    def test_6550(self):
        """Test Bucket Policy having Single Condition with Single Key and Multiple Values."""
        self.log.info(
            "STARTED: Test Bucket Policy having Single Condition"
            " with Single Key and Multiple Values")
        bucket_policy = BKT_POLICY_CONF["test_6550"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        object_lst = []
        self.log.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            obj_prefix,
            object_lst)
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account1_id = resp[1]["account_id"]
        self.account_list.append(self.account_name)
        s3_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=resp[1]["access_key"],
            secret_key=resp[1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=resp[1]["access_key"],
            secret_key=resp[1]["secret_key"])
        self.log.info(
            "Step 2 : Create a json file for  a Bucket Policy having Single Condition "
            "with Multiple Keys and each Key having single Value. Action -")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy.")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.log.info("Step 4 : Verify the Bucket Policy from cross account")
        resp = s3_obj1.put_object_with_acl(
            self.bucket_name,
            object_lst[0],
            self.file_path,
            acl="bucket-owner-read")
        assert resp[0], resp[1]
        resp = s3_obj1.put_object_with_acl(
            self.bucket_name,
            object_lst[0],
            self.file_path,
            acl="bucket-owner-full-control")
        assert resp[0], resp[1]
        try:
            s3_obj1.put_object_with_acl(
                self.bucket_name,
                object_lst[0],
                self.file_path,
                acl="public-read")
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj2.put_object(
                self.bucket_name,
                object_lst[0],
                self.file_path)
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "ENDED: Test Bucket Policy having Single Condition"
            " with Single Key and Multiple Values")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-18451")
    @CTFailOn(error_handler)
    def test_6553(self):
        """Test Bucket Policy Single Condition, Multiple Keys having Single Value for each Key."""
        self.log.info(
            "STARTED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")
        bucket_policy = BKT_POLICY_CONF["test_6553"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        object_lst = []
        self.log.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            obj_prefix,
            object_lst)
        account_name2 = "{}{}".format(
            self.acc_name_prefix, int(
                time.perf_counter_ns()))
        email2 = "{}{}".format(account_name2, "@seagate.com")
        resp1 = self.rest_obj.create_s3_account(
            acc_name=account_name2,
            email_id=email2,
            passwd=self.s3acc_passwd)
        account_id2 = resp1[1]["account_id"]
        canonical_id_2 = resp1[1]["canonical_id"]
        self.account_list.append(account_name2)
        self.log.debug(
            "Account2 Id: %s, Cannonical_id_2: %s",
            account_id2,
            canonical_id_2)
        access_key = resp1[1]["access_key"]
        secret_key = resp1[1]["secret_key"]
        s3_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key,
            secret_key=secret_key)
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_key,
            secret_key=secret_key)
        account_name3 = "{}{}".format(
            self.acc_name_prefix, int(
                time.perf_counter_ns()))
        email3 = "{}{}".format(account_name3, "@seagate.com")
        resp2 = self.rest_obj.create_s3_account(
            acc_name=account_name3,
            email_id=email3,
            passwd=self.s3acc_passwd)
        canonical_id_3 = resp2[1]["canonical_id"]
        self.log.debug("Cannonical_id_3: %s", canonical_id_3)
        self.account_list.append(account_name3)
        self.log.info(
            "Step 2 : Create a json file for  a Bucket Policy having Single Condition with "
            "Multiple Keys and each Key having single Value")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id2)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-full-control"].format(canonical_id_2)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-read"].format(canonical_id_3)
        self.log.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy.")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Verify the Bucket Policy from cross account")
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.log.info("Step 4 : Verify the Bucket Policy from cross account")
        self.log.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp = self.acl_obj.put_object_with_acl2(self.bucket_name,
                                                 "{}{}".format(
                                                     object_lst[0], str(time.time())),
                                                 self.file_path,
                                                 grant_full_control="ID={}".format(
                                                     canonical_id_2),
                                                 grant_read="ID={}".format(canonical_id_3))
        assert resp[0], resp[1]
        try:
            s3_obj2.put_object(
                self.bucket_name,
                object_lst[0],
                self.file_path)
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(
                self.bucket_name,
                object_lst[0],
                self.file_path,
                grant_full_control="emailaddress={}".format(email2))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(
                self.bucket_name,
                object_lst[0],
                self.file_path,
                grant_read="emailaddress={}".format(email3))
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "ENDED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7516")
    @CTFailOn(error_handler)
    def test_6693(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-acl" and Value "True".
        Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'True'")
        bucket_policy = BKT_POLICY_CONF["test_6693"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket and put multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2:Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        acl_permission = "bucket-owner-read"
        self.log.info(
            "Case 1 put object with acl permission as {} with new account".format(acl_permission))
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            acl=acl_permission, err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 2 put object without acl permission with new account")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'True'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7517")
    @CTFailOn(error_handler)
    def test_6703(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-acl" and Value "False".
        Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'False'")
        bucket_policy = BKT_POLICY_CONF["test_6703"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket and put multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        acl_permission = "bucket-owner-read"
        self.log.info(
            "Case 1 put object with acl permission as {} with new account".format(acl_permission))
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            acl=acl_permission)
        self.log.info(
            "Case 2 put object without acl permission with new account")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name,
            self.s3_obj,
            self.obj_name_prefix,
            err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'False'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7518")
    @CTFailOn(error_handler)
    def test_6704(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-acl" and Values ["False", "True"].
        Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl'"
            " and Values ['False', 'True']")
        bucket_policy = BKT_POLICY_CONF["test_6704"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket and put multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from %s bucket",
            self.bucket_name)
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from %s bucket successful",
            self.bucket_name)
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        acl_permission = "bucket-owner-read"
        self.log.info(
            "Case 1 put object with acl permission as %s with new account",
            acl_permission)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            acl=acl_permission)
        self.log.info(
            "Case 2 put object without acl permission with new account")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl'"
            " and Values ['False', 'True']")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7519")
    @CTFailOn(error_handler)
    def test_6760(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read"
        and Values ["False", "True"]. Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read'"
            " and Values ['False', 'True']")
        bucket_policy = BKT_POLICY_CONF["test_6760"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        conanical_id = acc_details[0]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        grant_read = "ID={}".format(conanical_id)
        self.log.info(
            "Case 1 put object with grant permission for new account "
            "having id as %s", grant_read)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_read=grant_read)
        self.log.info("Case 2 put object without grant read permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read'"
            " and Values ['False', 'True']")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7520")
    @CTFailOn(error_handler)
    def test_6761(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write"
        and Values "True". Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values 'True'")
        bucket_policy = BKT_POLICY_CONF["test_6761"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values 'True'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7521")
    @CTFailOn(error_handler)
    def test_6763(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write"
        and Values ["False", "True" ]. Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values ['False', 'True']")
        bucket_policy = BKT_POLICY_CONF["test_6763"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values ['False', 'True']")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7522")
    @CTFailOn(error_handler)
    def test_6764(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read-acp"
        and Values "True". Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'True'")
        bucket_policy = BKT_POLICY_CONF["test_6764"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant read acp permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_read_acp="ID={}".format(canonical_id),
            err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'True'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7523")
    @CTFailOn(error_handler)
    def test_6765(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read-acp"
        and Values "False". Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'False'")
        bucket_policy = BKT_POLICY_CONF["test_6765"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant read acp permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_read_acp="ID={}".format(canonical_id))
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix,
            err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'False'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7524")
    @CTFailOn(error_handler)
    def test_6766(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read-acp"
        and Values ['False', 'True']. Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values ['False', 'True']")
        bucket_policy = BKT_POLICY_CONF["test_6766"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant read acp permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_read_acp="ID={}".format(canonical_id))
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values ['False', 'True']")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7525")
    @CTFailOn(error_handler)
    def test_6767(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write-acp"
        and Value 'True'. Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'True'")
        bucket_policy = BKT_POLICY_CONF["test_6767"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant write acp permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_write_acp="ID={}".format(canonical_id),
            err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'True'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7526")
    @CTFailOn(error_handler)
    def test_6768(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write-acp"
        and Value 'False'. Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'False'")
        bucket_policy = BKT_POLICY_CONF["test_6768"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant write acp permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_write_acp="ID={}".format(canonical_id))
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix,
            err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'False'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7527")
    @CTFailOn(error_handler)
    def test_6769(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write-acp"
        and Values ["False", "True"]. Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Values ['False', 'True']")
        bucket_policy = BKT_POLICY_CONF["test_6769"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket".format(
                self.bucket_name))
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(
                self.bucket_name))
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant write acp permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_write_acp="ID={}".format(canonical_id))
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Values ['False', 'True']")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7528")
    @CTFailOn(error_handler)
    def test_6770(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-full-control"
        and Value "True". Verify the result."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-full-control'"
            " and Value 'True'")
        bucket_policy = BKT_POLICY_CONF["test_6770"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            self.bucket_name,
            4,
            self.obj_name_prefix)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3test_acl_obj = acc_details[2]
        self.s3_obj = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator: %s",
            bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from %s bucket",
            self.bucket_name)
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Put and get bucket policy from %s bucket successful",
            self.bucket_name)
        self.log.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id = acc_details[0]
        self.log.info(
            "Case 1 put object with grant full control permission for new account "
            "having id as %s", canonical_id)
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, s3test_acl_obj, self.obj_name_prefix,
            grant_full_control="ID={}".format(canonical_id),
            err_message=errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            self.bucket_name, self.s3_obj, self.obj_name_prefix)
        self.log.info("Step 4: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-full-control'"
            " and Value 'True'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7611")
    @CTFailOn(error_handler)
    def test_5921(self):
        """Test when blank file is provided for put bucket policy."""
        self.log.info(
            "STARTED: Test when blank file is provided for put bucket policy")
        bucket_policy = BKT_POLICY_CONF["test_5921"]["bucket_policy"]
        self.create_bucket_validate(self.bucket_name)
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy,
            errmsg.S3_BKT_POLICY_INVALID_JSON_ERR)
        self.log.info(
            "ENDED: Test when blank file is provided for put bucket policy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7612")
    @CTFailOn(error_handler)
    def test_5211(self):
        """Test Give own user permission for PutBucketPolicy and
        from user deny its account for Get/PutBucketPolicy."""
        self.log.info(
            "STARTED: Test Give own user permission for PutBucketPolicy"
            " and from user deny its account for Get/PutBucketPolicy")
        bucket_policy_1 = BKT_POLICY_CONF["test_5211"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_5211"]["bucket_policy_2"]
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id = resp[1][0]["User"][1]["User"]["UserId"]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            self.obj_name_prefix,
            "objkey5211_2")
        self.log.info("Step 1: Creating bucket policy with user id")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"][
                "AWS"].format(user_id)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Created bucket policy with user id")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy_1)
        self.log.info(
            "Step 2: Creating another policy on a bucket for account 1 using account id")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(account_id)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        bkt_policy_json_2 = json.dumps(bucket_policy_2)
        self.log.info(
            "Step 2: Created policy for account 1 using account id")
        self.log.info("Step 3: Applying bucket policy using users credential")
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp = s3_policy_usr_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json_2)
        assert resp[0], resp[1]
        self.log.info("Step 3: Applied bucket policy using users credential")
        self.log.info(
            "Step 4: Applying bucket policy using account 1 credential")
        bkt_policy_json_1 = json.dumps(bucket_policy_1)
        resp = self.s3_bkt_policy_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json_1)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Applied policy of a bucket using account 1 credential")
        self.log.info(
            "Step 5: Retrieving policy of a bucket using account 1 credential")
        resp = self.s3_bkt_policy_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 5: Retrieved policy of a bucket using account 2 credential")
        self.log.info(
            "ENDED: Test Give own user permission for PutBucketPolicy "
            "and from user deny its account for Get/PutBucketPolicy")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7613")
    @CTFailOn(error_handler)
    def test_5210(self):
        """Test Give own and cross account user permission specifying userid in principal and allow GetBucketPolicy."""
        self.log.info(
            "STARTED: Test Give own and cross account user permission "
            "specifying userid in principal and allow GetBucketPolicy.")
        bucket_policy = BKT_POLICY_CONF["test_5210"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        user_name_1 = "{0}{1}".format(self.user_name, str(
            time.time()))
        user_name_2 = "{0}{1}".format(self.user_name, str(
            time.time()))
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key_2 = acc_details[4]
        secret_key_2 = acc_details[5]
        resp = self.iam_obj.create_user_access_key(user_name_1)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id_1 = resp[1][0]["User"][1]["User"]["UserId"]
        self.log.info("Step 1: Creating user using account 2 credential")
        s3_policy_acc2_obj = iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = s3_policy_acc2_obj.create_user(user_name_2)
        self.iam_obj_list.append(s3_policy_acc2_obj)
        assert resp[0], resp[1]
        user_id_2 = resp[1]["User"]["UserId"]
        self.log.info("Step 1: Created user using account 2 credential")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            self.obj_name_prefix,
            "objkey5210_2")
        self.log.info(
            "Step 2: Creating bucket policy on a bucket to account1 User and account2 User")
        bucket_policy["Statement"][0]["Principal"]["AWS"][0] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"][
                0].format(user_id_1)
        bucket_policy["Statement"][0]["Principal"]["AWS"][1] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"][
                1].format(user_id_2)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket to account1 User and account2 User")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3: Retrieving policy of a bucket using user of account 1")
        s3_policy_usr1_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp = s3_policy_usr1_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Retrieved policy of a bucket using user of account 1")
        self.log.info(
            "Step 4: Retrieving policy of a bucket using user of account 2")
        resp = s3_policy_acc2_obj.create_access_key(user_name_2)
        s3_bucket_usr2_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bucket_usr2_obj.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 4: Retrieving policy of a bucket using user of account 2 is failed with error"
                "MethodNotAllowed")
        self.log.info(
            "ENDED: Test Give own and cross account user permission "
            "specifying userid in principal and allow GetBucketPolicy.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7614")
    @CTFailOn(error_handler)
    def test_5206(self):
        """Test give own user permission specifying user id in principal and allow GetBucketPolicy."""
        self.log.info(
            "STARTED: Test give own user permission specifying user id in principal and allow GetBucketPolicy.")
        bucket_policy = BKT_POLICY_CONF["test_5206"]["bucket_policy"]
        user_name_1 = "{0}{1}".format(self.user_name, str(
            time.time()))
        resp = self.iam_obj.create_user_access_key(user_name_1)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id = resp[1][0]["User"][1]["User"]["UserId"]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            self.obj_name_prefix,
            "objkey5206_2")
        self.log.info(
            "Step 1: Creating bucket policy on a bucket to account1 user")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"][
                "AWS"].format(user_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1: Created bucket policy on a bucket to account1 User")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 2: Retrieving policy of a bucket using user of account 1")
        s3_policy_usr1_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp = s3_policy_usr1_obj.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Retrieved policy of a bucket using user of account 1")
        self.log.info(
            "ENDED: Test give own user permission specifying user id in principal and allow GetBucketPolicy.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7615")
    @CTFailOn(error_handler)
    def test_5212(self):
        """Test Give cross account user permission for Get/PutBucketPolicy
        and deny the bucket owner account for Get/PutBucketPolicy."""
        self.log.info(
            "STARTED: Test Give cross account user permission for "
            "Get/PutBucketPolicy and deny the bucket owner account for Get/PutBucketPolicy .")
        bucket_policy_1 = BKT_POLICY_CONF["test_5212"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_5212"]["bucket_policy_2"]
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        access_key_1 = acc_details[0][1]["access_key"]
        secret_key_1 = acc_details[0][1]["secret_key"]
        acc_id_1 = acc_details[0][1]["account_id"]
        access_key_2 = acc_details[1][1]["access_key"]
        secret_key_2 = acc_details[1][1]["secret_key"]
        self.log.info("Creating user in account 2")
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = iam_obj_acc_2.create_user(self.user_name)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_obj_acc_2)
        user_id_2 = resp[1]["User"]["UserId"]
        self.log.info("Created user in account 2")
        self.log.info(
            "Step 1: Creating a bucket and uploading objects in a bucket using account 1")
        s3_obj_acc_1 = s3_test_lib.S3TestLib(
            access_key=access_key_1, secret_key=secret_key_1)
        resp = s3_obj_acc_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.s3t_obj_list.append(s3_obj_acc_1)
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        system_utils.create_file(
            self.file_path,
            10)
        resp = s3_obj_acc_1.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        system_utils.create_file(
            self.file_path_2,
            10)
        resp = s3_obj_acc_1.put_object(
            self.bucket_name,
            "objkey5212_2",
            self.file_path_2)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Bucket was created and objects are uploaded in the bucket using account 1")
        self.log.info("Step 2: Creating json on a bucket to account 2 user")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"][
                "AWS"].format(user_id_2)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        bkt_policy_json_1 = json.dumps(bucket_policy_1)
        self.log.info("Step 2: Created json on a bucket to account 2 user")
        self.log.info(
            "Step 3: Applying policy on a bucket %s", self.bucket_name)
        s3_bkt_policy_acc1 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_1, secret_key=secret_key_1)
        resp = s3_bkt_policy_acc1.put_bucket_policy(
            self.bucket_name, bkt_policy_json_1)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Applied policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 4: Retrieving policy of a bucket %s", self.bucket_name)
        resp = s3_bkt_policy_acc1.get_bucket_policy(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1]["Policy"], bkt_policy_json_1, resp[1])
        self.log.info(
            "Step 4: Retrieved policy of a bucket %s", self.bucket_name)
        self.log.info("Step 5: Creating a json on a bucket to account 1")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(acc_id_1)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        bkt_policy_json_2 = json.dumps(bucket_policy_2)
        self.log.info("Step 5: Created json on a bucket to account 1")
        self.log.info(
            "Step 6: Applying the bucket policy using user of account 2")
        resp = iam_obj_acc_2.create_access_key(self.user_name)
        s3_bkt_policy_usr2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bkt_policy_usr2.put_bucket_policy(
                self.bucket_name, bkt_policy_json_2)
        except CTException as error:
            self.log.info(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 6: Applying the bucket policy using user of account 2 is failed with error"
                " MethodNotAllowed")
        self.log.info(
            "Step 7: Retrieving policy of a bucket using user of account 2")
        try:
            s3_bkt_policy_usr2.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 7: Retrieving policy of a bucket using user of account 2 is failed with error"
                " MethodNotAllowed")
        self.log.info(
            "ENDED: Test Give cross account user permission for "
            "Get/PutBucketPolicy and deny the bucket owner account for Get/PutBucketPolicy .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7616")
    @CTFailOn(error_handler)
    def test_5214(self):
        """Test Give user permission for PutBucketPolicy and from user allow
         Get/PutBucketPolicy,GetBucketAcl permission to cross account."""
        self.log.info(
            "STARTED: Test Give user permission for PutBucketPolicy and"
            " from user allow Get/PutBucketPolicy,GetBucketAcl permission to cross account")
        bucket_policy_1 = BKT_POLICY_CONF["test_5214"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_5214"]["bucket_policy_2"]
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_bkt_policy_2 = acc_details[3]
        s3_bkt_acl_2 = acc_details[2]
        resp = self.iam_obj.create_user_access_key(self.user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id = resp[1][0]["User"][1]["User"]["UserId"]
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            self.obj_name_prefix,
            "objkey5214_2")
        self.log.info("Step 1: Creating bucket policy with user id")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"][
                "AWS"].format(user_id)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Created bucket policy with user id")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy_1)
        self.log.info(
            "Step 2: Creating another policy on a bucket to account 2 using account id")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(account_id)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        bkt_policy_json_2 = json.dumps(bucket_policy_2)
        self.log.info(
            "Step 2: Created another policy on a bucket to account 2 using account id")
        self.log.info("Step 3: Applying bucket policy using users credential")
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp = s3_policy_usr_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json_2)
        assert resp[0], resp[1]
        self.log.info("Step 3: Applied bucket policy using users credential")
        self.log.info(
            "Step 4: Applying bucket policy using account 2 credential")
        bkt_policy_json_1 = json.dumps(bucket_policy_1)
        try:
            s3_bkt_policy_2.put_bucket_policy(
                self.bucket_name, bkt_policy_json_1)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 4: Applying bucket policy using account 2 credential is failed with error"
                "MethodNotAllowed")
        self.log.info(
            "Step 5: Retrieving policy of a bucket using account 2 credential")
        try:
            s3_bkt_policy_2.get_bucket_policy(self.bucket_name)
        except CTException as error:
            assert "MethodNotAllowed" in error.message, error.message
            self.log.error(error.message)
            self.log.info(
                "Step 5: Retrieving policy of a bucket using account 2 credential is failed "
                "with error MethodNotAllowed")
        self.log.info(
            "Step 6: Retrieving acl of a bucket using account 2 credential")
        resp = s3_bkt_acl_2.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 6: Retrieved acl of a bucket using account 2 credential")
        self.log.info(
            "ENDED: Test Give user permission for PutBucketPolicy and "
            "from user allow Get/PutBucketPolicy,GetBucketAcl permission to cross account")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7617")
    @CTFailOn(error_handler)
    def test_5215(self):
        """Test Give user permission for PutBucketPolicy and from user
        allow Get/PutBucketPolicy,PutBucketAcl permission to cross account user."""
        self.log.info(
            "STARTED: Test Give user permission for PutBucketPolicy and "
            "from user allow Get/PutBucketPolicy,PutBucketAcl permission to cross account user.")
        bucket_policy_1 = BKT_POLICY_CONF["test_5215"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_5215"]["bucket_policy_2"]
        user_name_1 = "{0}{1}".format(self.user_name, str(
            time.time()))
        user_name_2 = "{0}{1}".format(self.user_name, str(
            time.time()))
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        access_key_2 = acc_details[4]
        secret_key_2 = acc_details[5]
        can_id = acc_details[0]
        resp = self.iam_obj.create_user_access_key(user_name_1)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id_1 = resp[1][0]["User"][1]["User"]["UserId"]
        self.log.info("Step 1: Creating user using account 2 credential")
        iam_acc2_obj = iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = iam_acc2_obj.create_user(user_name_2)
        assert resp[0], resp[1]
        self.iam_obj_list.append(iam_acc2_obj)
        user_id_2 = resp[1]["User"]["UserId"]
        self.log.info("Step 1: Created user using account 2 credential")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            self.obj_name_prefix,
            "objkey5215_2")
        self.log.info(
            "Step 2: Creating a policy on a bucket to account 1 User")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"][
                "AWS"].format(user_id_1)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        bkt_policy_json_1 = json.dumps(bucket_policy_1)
        self.log.info("Step 2: Created a policy on a bucket to account 1 User")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy_1)
        self.log.info(
            "Step 3: Creating another policy on a bucket to account 2 user")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(user_id_2)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        bkt_policy_json_2 = json.dumps(bucket_policy_2)
        self.log.info(
            "Step 3: Created another policy on a bucket to account 2 user")
        self.log.info(
            "Step 4: Applying policy on a bucket using user of account 1")
        s3_policy_usr1_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp = s3_policy_usr1_obj.put_bucket_policy(
            self.bucket_name, bkt_policy_json_2)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Applied policy on a bucket using user of account 1")
        self.log.info(
            "Step 5: Applying policy on a bucket using user of account 2")
        resp = iam_acc2_obj.create_access_key(user_name_2)
        s3_bkt_policy_usr2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bkt_policy_usr2.put_bucket_policy(
                self.bucket_name, bkt_policy_json_1)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 5: Applying policy on a bucket using user of account 2  is failed with error"
                "MethodNotAllowed")
        self.log.info(
            "Step 6: Retrieving policy of a bucket using user of account 2")
        try:
            s3_bkt_policy_usr2.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 6: Retrieving policy of a bucket using user of account 2 is failed with error"
                "MethodNotAllowed")
        self.log.info(
            "Step 7: Applying read acp permission on a bucket %s",
            self.bucket_name)
        s3_bkt_acl_usr2 = s3_acl_test_lib.S3AclTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bkt_acl_usr2.put_bucket_acl(
                self.bucket_name,
                grant_read_acp="id={}".format(can_id))
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 7: Applying read acp permission on a bucket is failed with error %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Test Give user permission for PutBucketPolicy and "
            "from user allow Get/PutBucketPolicy,PutBucketAcl permission to cross account user.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7637")
    @CTFailOn(error_handler)
    def test_6771(self):
        """Test Bucket Policy having Null Condition operator
        Key "s3:x-amz-grant-full-control" and Value "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key "
            "s3:x-amz-grant-full-control and Value False")
        bucket_policy = BKT_POLICY_CONF["test_6771"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        canonical_id = acc_details[0]
        s3_bkt_acl_acc2 = acc_details[2]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading object with grant full control using account 2")
        resp = s3_bkt_acl_acc2.put_object_with_acl(
            self.bucket_name,
            "objkey_6771",
            self.file_path,
            grant_full_control="id={}".format(canonical_id))
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Uploaded object with grant full control using account 2")
        self.log.info("Case 2: Uploading object with account 2")
        try:
            s3_obj_acc2.put_object(
                self.bucket_name,
                "objkey_6771",
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Case 2: Uploading object with account 2 is failed with error %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key "
            "s3:x-amz-grant-full-control and Value False")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7638")
    @CTFailOn(error_handler)
    def test_6772(self):
        """Test Bucket Policy having Null Condition operator
        Key "s3:x-amz-grant-full-control" and Values ["False", "True"]."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator "
            "Key s3:x-amz-grant-full-control and Values [False, True]")
        bucket_policy = BKT_POLICY_CONF["test_6772"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        canonical_id = acc_details[0]
        s3_bkt_acl_acc2 = acc_details[2]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with grant full control using account 2")
        resp = s3_bkt_acl_acc2.put_object_with_acl(
            self.bucket_name,
            "objkey_6772",
            self.file_path,
            grant_full_control="id={}".format(canonical_id))
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Uploaded an object with grant full control using account 2")
        self.log.info("Case 2: Uploading an object using account 2")
        resp = s3_obj_acc2.put_object(
            self.bucket_name,
            "objkey_6772",
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Case 2: Uploaded an object using account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-grant-full-control and Values [False, True]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7639")
    @CTFailOn(error_handler)
    def test_6773(self):
        """Test Bucket Policy having Null Condition operator Key "s3:max-keys" and Value "True"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value True")
        bucket_policy = BKT_POLICY_CONF["test_6773"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc_2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info("Case 1: Listing objects with max keys from account 2")
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name,
            s3_obj_acc_2,
            2,
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Listing objects with max keys from account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2: Listing objects with account 2")
        resp = s3_obj_acc_2.object_list(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Case 2: Objects are listed from account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value True")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7640")
    @CTFailOn(error_handler)
    def test_6774(self):
        """Test Bucket Policy having Null Condition operator Key "s3:max-keys" and Value "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value False")
        bucket_policy = BKT_POLICY_CONF["test_6774"]["bucket_policy"]
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info("Case 1: Listing objects with max keys from account 2")
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj_acc2, 2)
        self.log.info(
            "Case 1: Objects are listed with max keys from account 2")
        self.log.info("Case 2: Listing objects with account 2")
        try:
            s3_obj_acc2.object_list(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Case 2: Listing objects from account 2 is failed with error %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value False")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7641")
    @CTFailOn(error_handler)
    def test_6775(self):
        """Test Bucket Policy having Null Condition operator Key "s3:max-keys" and Value ["False", "True"]."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value [False, True]")
        bucket_policy = BKT_POLICY_CONF["test_6775"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc_2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info("Case 1: Listing objects with max keys from account 2")
        self.list_obj_with_max_keys_and_diff_acnt(
            self.bucket_name, s3_obj_acc_2, 1)
        self.log.info(
            "Case 1: Objects are listed with max keys from account 2")
        self.log.info("Case 2: Listing objects with account 2")
        resp = s3_obj_acc_2.object_list(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Case 2: Objects are listed from account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value [False, True]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7642")
    @CTFailOn(error_handler)
    def test_6776(self):
        """Test Bucket Policy having Null Condition operator Key "s3:prefix" and Value "True"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value True")
        bucket_policy = BKT_POLICY_CONF["test_6776"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1: Creating a bucket and uploading objects to a bucket")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "/bkt_policy/policy1",
            "/bkt_policy/policy2")
        system_utils.create_file(
            self.file_path,
            10)
        resp = self.s3_obj.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created a bucket and objects are uploaded to a bucket")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc_2 = acc_details[1]
        self.log.info(
            "Step 2: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info("Case 1: Listing objects with prefix from account 2")
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name,
            s3_obj_acc_2,
            "bkt_policy",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Listing objects with prefix from account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2: Listing object using account 2")
        resp = s3_obj_acc_2.object_list(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Case 2: Objects are listed using account 2")
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value True")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7643")
    @CTFailOn(error_handler)
    def test_6777(self):
        """Test Bucket Policy having Null Condition operator Key "s3:prefix" and Value "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value False")
        bucket_policy = BKT_POLICY_CONF["test_6777"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1: Creating a bucket and uploading objects to a bucket")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "bktpolicy/policy1",
            "bktpolicy/policy2")
        system_utils.create_file(
            self.file_path,
            10)
        resp = self.s3_obj.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created a bucket and objects are uploaded to a bucket")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 2: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info("Case 1: Listing objects with prefix from account 2")
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, s3_obj_acc2, "bktpolicy")
        self.log.info("Case 1: Objects are listed with prefix from account 2")
        self.log.info("Case 2: Listing object using account 2")
        try:
            s3_obj_acc2.object_list(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Case 2: Listing objects from account 2 is failed with error %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value False")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7644")
    @CTFailOn(error_handler)
    def test_6779(self):
        """Test Bucket Policy having Null Condition operator Key "s3:prefix" and Values ["False", "True"]."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:prefix and Values [False, True]")
        bucket_policy = BKT_POLICY_CONF["test_6779"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 1: Creating a bucket and uploading objects to a bucket")
        self.create_bucket_put_obj_with_dir(
            self.bucket_name,
            "bktpolicy/policy1",
            "bktpolicy/policy2")
        system_utils.create_file(
            self.file_path,
            10)
        resp = self.s3_obj.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created a bucket and objects are uploaded to a bucket")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 2: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 2: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info("Case 1: Listing objects with prefix using account 2")
        self.list_obj_with_prefix_using_diff_accnt(
            self.bucket_name, s3_obj_acc2, "bktpolicy")
        self.log.info("Case 1: Objects are listed with prefix using account 2")
        self.log.info("Case 2: Listing object using account 2")
        resp = s3_obj_acc2.object_list(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Case 2: Objects are listed from account 2")
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:prefix and Values [False, True]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7645")
    @CTFailOn(error_handler)
    def test_6783(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-content-sha256" and Value "True"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:x-amz-content-sha256 and Value True")
        bucket_policy = BKT_POLICY_CONF["test_6783"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            3,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Uploading an object using account 2")
        try:
            s3_obj_acc2.put_object(
                self.bucket_name,
                self.obj_name_prefix,
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: Uploading object with account 2 is failed with error %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:x-amz-content-sha256 and Value True")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7646")
    @CTFailOn(error_handler)
    def test_6787(self):
        """Test Bucket Policy having Null Condition operator
        Key "s3:x-amz-content-sha256" and Value "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Value False")
        bucket_policy = BKT_POLICY_CONF["test_6787"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            3,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Uploading an object using account 2")
        resp = s3_obj_acc2.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Step 2: Uploaded an object with account 2")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Value False")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7648")
    @CTFailOn(error_handler)
    def test_6788(self):
        """Test Bucket Policy having Null Condition operator Key
        "s3:x-amz-content-sha256" and Values ["False", "True"]."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Values False,True")
        bucket_policy = BKT_POLICY_CONF["test_6788"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            3,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Uploading an object using account 2")
        resp = s3_obj_acc2.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Step 2: Uploaded an object with account 2")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Values False,True")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7650")
    @CTFailOn(error_handler)
    def test_6790(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-storage-class" and Value "True"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null "
            "Condition operator Key s3:x-amz-storage-class and Value True")
        bucket_policy = BKT_POLICY_CONF["test_6790"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            3,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with storage class STANDARD using account 2")
        try:
            s3_obj_acc2.put_object_with_storage_class(
                self.bucket_name,
                self.obj_name_prefix,
                self.file_path,
                "STANDARD")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Case 1: Uploading an object with storage class "
                "STANDARD using account 2 is failed with error %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2: Uploading an object with account 2")
        resp = s3_obj_acc2.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Case 2: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-storage-class and Value True")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7651")
    @CTFailOn(error_handler)
    def test_6791(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-storage-class" and Value "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-storage-class and Value False")
        bucket_policy = BKT_POLICY_CONF["test_6791"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            3,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with storage class STANDARD using account 2")
        resp = s3_obj_acc2.put_object_with_storage_class(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path,
            "STANDARD")
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Uploaded an object with storage class STANDARD using account 2")
        self.log.info("Case 2: Uploading an object with account 2")
        try:
            s3_obj_acc2.put_object(
                self.bucket_name,
                self.obj_name_prefix,
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 2: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-storage-class and Value False")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8044")
    @CTFailOn(error_handler)
    def test_6792(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-storage-class" and Values
        ["True", "False"]."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-storage-class"
            "' and Values ['True', 'False']")
        bucket_policy = BKT_POLICY_CONF["test_6792"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.create_bucket_put_objects(
            self.bucket_name,
            3,
            self.obj_name_prefix)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_obj_acc2 = acc_details[1]
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with storage class STANDARD using account 2")
        resp = s3_obj_acc2.put_object_with_storage_class(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path,
            "STANDARD")
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Uploaded an object with storage class STANDARD using account 2")
        self.log.info("Case 2: Uploading an object with account 2")
        resp = s3_obj_acc2.put_object(
            self.bucket_name,
            self.obj_name_prefix,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Case 2: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-storage-class'"
            " and Values ['True', 'False']")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8043")
    @CTFailOn(error_handler)
    def test_6762(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write" and Value
        "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Value 'False'")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_6762"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with storage class --grant-write using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                grant_write_acp="ID={}".format(canonical_id_user_1))
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Uploaded an object with storage class --grant-write using account 2")
        self.log.info("Case 2: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                self.bucket_name,
                object_names[0],
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 2: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Value 'False'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8041")
    @CTFailOn(error_handler)
    def test_6707(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read" and Value "True"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read'"
            " and Value 'True'")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_6707"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with storage class --grant-read using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                grant_read="ID={}".format(canonical_id_user_1))
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Uploaded an object with storage class --grant-read using account 2")
        self.log.info("Case 2: Uploading an object with account 2")
        resp = self.s3test_obj_1.put_object(
            self.bucket_name,
            object_names[0],
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Case 2: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'True'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8042")
    @CTFailOn(error_handler)
    def test_6708(self):
        """Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read" and Value "False"."""
        self.log.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'False'")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_6708"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with storage class --grant-read using account 2")
        resp = acl_obj_1.put_object_with_acl(
            self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read="ID={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Uploaded an object with storage class --grant-read using account 2")
        self.log.info("Case 2: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                self.bucket_name,
                object_names[0],
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 2: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'False'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8045")
    @CTFailOn(error_handler)
    def test_7051(self):
        """Test Verify Bucket Policy having Valid Condition Key and Invalid Value."""
        self.log.info(
            "STARTED: Test Verify Bucket Policy having Valid Condition Key and Invalid Value")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_7051"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("canonical_id_user_1 :%s", canonical_id_user_1)
        self.log.info("New account created")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-read using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="bucket-owner-read")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-read is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Uploaded an object with --acl bucket-owner-read using account 2")
        self.log.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="bucket-owner-full-control")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 2: Uploaded an object with --acl bucket-owner-full-control using account 2")
        self.log.info("Case 3: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                self.bucket_name,
                object_names[0],
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 3: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 3: Uploaded an object with account 2")
        self.log.info(
            "Case 4: Uploading an object with invalid value 'xyz' using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="xyz")
        except CTException as error:
            self.log.error(error.message)
            assert "BadRequest" in error.message, error.message
        self.log.info(
            "Case 4: Uploaded an object with invalid value 'xyz' using account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Verify Bucket Policy having Valid Condition Key and Invalid Value")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8046")
    @CTFailOn(error_handler)
    def test_7052(self):
        """Test Verify Bucket Policy having Invalid Condition Key."""
        self.log.info(
            "STARTED: Test Verify Bucket Policy having Invalid Condition Key")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_7052"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.log.info(
            "Step 2: Verifying the Put Bucket Policy from cross account")
        try:
            bkt_policy_json = json.dumps(bucket_policy)
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert "invalid condition key" in error.message, error.message
        self.log.info(
            "step 2: Put Bucket Policy is failed with error %s",
            "invalid condition key")
        self.log.info(
            "Step 2: Verified the Put Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Verify Bucket Policy having Invalid Condition Key")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8047")
    @CTFailOn(error_handler)
    def test_7054(self):
        """Test Verify Bucket Policy multiple conflicting Condition types(operators)."""
        self.log.info(
            "STARTED: Test Verify Bucket Policy multiple conflicting Condition types(operators)")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_7054"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-read using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="bucket-owner-read")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-read is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Uploaded an object with --acl bucket-owner-read using account 2")
        self.log.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="bucket-owner-full-control")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 2: Uploaded an object with --acl bucket-owner-full-control using account 2")
        self.log.info("Case 3: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                self.bucket_name,
                object_names[0],
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 3: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 3: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Verify Bucket Policy multiple conflicting Condition types(operators)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8048")
    @CTFailOn(error_handler)
    def test_7055(self):
        """Test Verify Bucket Policy Condition Values are case sensitive."""
        self.log.info(
            "STARTED: Test Verify Bucket Policy Condition Values are case sensitive")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_7055"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 2: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-read using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="bucket-owner-read")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-read is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Uploaded an object with --acl bucket-owner-read using account 2")
        self.log.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="public-read")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 2: Uploaded an object with --acl bucket-owner-full-control using account 2")
        self.log.info("Case 3: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                self.bucket_name,
                object_names[0],
                self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 3: Uploading an object with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Case 3: Uploaded an object with account 2")
        self.log.info("Step 2: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Verify Bucket Policy Condition Values are case sensitive")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8049")
    @CTFailOn(error_handler)
    def test_7056(self):
        """Test Create Bucket Policy using StringEqualsIgnoreCase Condition Operator, key "s3:prefix" and Effect Allow."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_7056"]["bucket_policy"]
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            "obj_policy")
        prefix_upper = "obj_policy".upper(
        )
        obj_name_upper = "{}/{}".format(prefix_upper, str(int(time.time())))
        resp = self.s3_obj.put_object(
            self.bucket_name,
            obj_name_upper,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 2: Create a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        bucket_policy["Statement"][0]["Condition"]["StringEqualsIgnoreCase"]["s3:prefix"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEqualsIgnoreCase"][
                "s3:prefix"].format("obj_policy")
        self.log.info(
            "Step 2: Created a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: List objects with prefix using account 2")
        resp = self.s3test_obj_1.list_objects_with_prefix(
            self.bucket_name,
            prefix="obj_policy")
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Listed objects with prefix using account 2")
        self.log.info(
            "Case 2: List objects with upper prefix using account 2")
        resp = self.s3test_obj_1.list_objects_with_prefix(
            self.bucket_name,
            prefix=prefix_upper)
        assert resp[0], resp[1]
        self.log.info(
            "Case 2: Listed objects with upper prefix using account 2")
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8050")
    @CTFailOn(error_handler)
    def test_7057(self):
        """Test Create Bucket Policy using StringNotEqualsIgnoreCase Condition Operator, key "s3:prefix" and Effect Allow."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringNotEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")
        bucket_policy = BKT_POLICY_CONF["test_7057"]["bucket_policy"]
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        self.create_bucket_put_objects(
            self.bucket_name,
            1,
            "obj_policy")
        prefix_upper = "obj_policy".upper(
        )
        obj_name_upper = "{}/{}".format(prefix_upper, str(int(time.time())))
        resp = self.s3_obj.put_object(
            self.bucket_name,
            obj_name_upper,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 2: Create a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        bucket_policy["Statement"][0]["Condition"]["StringNotEqualsIgnoreCase"]["s3:prefix"] = \
            bucket_policy["Statement"][0]["Condition"]["StringNotEqualsIgnoreCase"][
                "s3:prefix"].format("obj_policy")
        self.log.info(
            "Step 2: Created a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: List objects with prefix using account 2")
        try:
            self.s3test_obj_1.list_objects_with_prefix(
                self.bucket_name,
                prefix="obj_policy")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: List objects with account 2 is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Listed objects with prefix using account 2")
        self.log.info(
            "Case 2: List objects with upper prefix using account 2")
        try:
            self.s3test_obj_1.list_objects_with_prefix(
                self.bucket_name,
                prefix=prefix_upper)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 2: List objects with upper prefix is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 2: Listed objects with upper prefix using account 2")
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringNotEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8051")
    @CTFailOn(error_handler)
    def test_7058(self):
        """Test Create Bucket Policy using StringLike Condition Operator, key "s3:x-amz-acl"."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringLike Condition Operator, key 's3:x-amz-acl'")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_7058"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 2: Create a json file for bucket policy specifying StringLike Condition Operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 2: Created a json file for bucket policy specifying StringLike Condition Operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-full-control using account 2")
        resp = acl_obj_1.put_object_with_acl(
            self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            acl="bucket-owner-full-control")
        assert resp[0], resp[1]
        self.log.info(
            "Case 1: Uploaded an object with --acl bucket-owner-full-control using account 2")
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringLike Condition Operator, key 's3:x-amz-acl'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8052")
    @CTFailOn(error_handler)
    def test_7059(self):
        """Test Create Bucket Policy using StringNotLike Condition Operator, key "s3:x-amz-acl"."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringNotLike Condition Operator, key 's3:x-amz-acl'")
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_7059"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        object_names = []
        assert resp[0], resp[1]
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        self.log.info(
            "Step 2: Create a json file for bucket policy specifying StringLike Condition Operator")
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(
            "Step 2: Created a json file for bucket policy specifying StringLike Condition Operator")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Verifying the Bucket Policy from cross account")
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                acl="bucket-owner-full-control")
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Case 1: Put objects is failed with error %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info(
            "Case 1: Uploading an object with --acl bucket-owner-full-control using account 2")
        self.log.info("Step 3: Verified the Bucket Policy from cross account")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringNotLike Condition Operator, key 's3:x-amz-acl'")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8037")
    @CTFailOn(error_handler)
    def test_5134(self):
        """Test apply allow PutObjectAcl api on object in policy and READ_ACP ACL on the object."""
        self.log.info(
            "STARTED: Test apply allow PutObjectAcl api on object in policy and READ_ACP ACL on the object."
        )
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_5134"]["bucket_policy"]
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow PutObjectACL api on object in the policy "
            "to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(
            "Step 2: Created a policy json and Allow PutObjectACL api on bucket in the policy "
            "to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Apply READ_ACP ACL on the object to account2. - run from default")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Applied READ_ACP ACL on the object to account2. - run from default")
        self.log.info(
            "Step 7: Check the object ACL to verify the applied ACL.  - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 7: Checked the object ACL to verify the applied ACL.  - run from default")
        self.log.info("Step 8: Put object ACL. - run from default")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info("Step 8: Put object ACL. - run from default")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow PutObjectAcl api on object in policy and READ_ACP ACL on the object."
        )

    # Bug reported EOS-7215: Test is failing, need to revisit after bug is
    # fixed.
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-10359")
    @CTFailOn(error_handler)
    def test_7053(self):
        """Verify Bucket Policy Condition Keys are case insensitive."""
        self.log.info(
            "STARTED: Verify Bucket Policy Condition Keys are case insensitive")
        bucket_policy = BKT_POLICY_CONF["test_7053"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        object_lst = []
        self.log.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            obj_prefix,
            object_lst)
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account1_id = resp[1]["account_id"]
        self.account_list.append(self.account_name)
        s3_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=resp[1]["access_key"],
            secret_key=resp[1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=resp[1]["access_key"],
            secret_key=resp[1]["secret_key"])
        self.log.info(
            "Step 2:Create a json file for a Bucket Policy having Valid Condition")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account1_id)
        self.log.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 4 : Verify the Bucket Policy from cross account")
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        resp = s3_obj1.put_object_with_acl(
            self.bucket_name,
            object_lst[0],
            self.file_path,
            acl="bucket-owner-read")
        assert resp[0], resp[1]
        try:
            s3_obj1.put_object_with_acl(
                self.bucket_name,
                object_lst[0],
                self.file_path,
                acl="bucket-owner-full-control")
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj2.put_object(
                self.bucket_name,
                object_lst[0],
                self.file_path)
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "ENDED: Verify Bucket Policy Condition Keys are case insensitive")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-18452")
    @CTFailOn(error_handler)
    def test_6554(self):
        """Test Bucket Policy Single Condition, Multiple Keys having Single Value for each Key."""
        self.log.info(
            "STARTED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")
        bucket_policy = BKT_POLICY_CONF["test_6554"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        object_lst = []
        self.log.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            obj_prefix,
            object_lst)
        acc_details = []
        for i in range(5):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account2_id = acc_details[0][1]["account_id"]
        account2_cid = acc_details[0][1]["canonical_id"]
        account3_cid = acc_details[1][1]["canonical_id"]
        account4_cid = acc_details[2][1]["canonical_id"]
        account5_cid = acc_details[3][1]["canonical_id"]

        s3_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])

        self.log.info(
            "Step 2 : Create a json file for  a Bucket Policy having Single Condition with "
            "Multiple Keys and each Key having Multiple Values. Action - Put Object and Effect - Allow.")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account2_id)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-full-control"].format([account2_cid, account3_cid])
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-read"].format([account4_cid, account5_cid])
        self.log.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step  4: Verify the Bucket Policy from cross account")
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.log.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp = self.acl_obj.put_object_with_acl2(self.bucket_name,
                                                 "{}{}".format(
                                                     object_lst[0], str(time.time())),
                                                 self.file_path,
                                                 grant_full_control="id={}".format(
                                                     account3_cid),
                                                 grant_read="id={}".format(account5_cid))
        assert resp[0], resp[1]
        self.log.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp = self.acl_obj.put_object_with_acl2(self.bucket_name,
                                                 "{}{}".format(
                                                     object_lst[0], str(time.time())),
                                                 self.file_path,
                                                 grant_full_control="id={}".format(
                                                     account2_cid),
                                                 grant_read="id={}".format(account4_cid))
        assert resp[0], resp[1]
        try:
            self.log.info(
                "Put object with ACL : grant_full_control and grant_read")
            s3_obj1.put_object_with_acl2(self.bucket_name,
                                         "{}{}".format(object_lst[0], str(time.time())),
                                         self.file_path,
                                         grant_full_control="id={}".format(account5_cid),
                                         grant_read="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl2(self.bucket_name,
                                         "{}{}".format(object_lst[0], str(time.time())),
                                         self.file_path,
                                         grant_full_control="id={}".format(account5_cid),
                                         grant_read="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(self.bucket_name,
                                        "{}{}".format(object_lst[0], str(time.time())),
                                        self.file_path,
                                        grant_full_control="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(self.bucket_name, "{}{}".format(object_lst[0], str(
                time.time())), self.file_path, grant_read="id={}".format(account5_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj2.put_object(
                self.bucket_name,
                object_lst[0],
                self.file_path)
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "ENDED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8038")
    @CTFailOn(error_handler)
    def test_5136(self):
        """Test apply allow GetObject api on object in policy and READ_ACP ACL on the object."""
        self.log.info(
            "STARTED: Test apply allow GetObject api on object in policy and READ_ACP ACL on the object ."
        )
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_5136"]["bucket_policy"]
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created. with %s", acl_obj_1)
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow GetObject api on object in the policy to "
            "account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(
            "Step 2: Created a policy json and Allow GetObject api on bucket in the policy to "
            "account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object. - run from account1")
        resp = self.s3test_obj_1.object_download(
            self.bucket_name,
            object_names[0],
            "test1_d.txt")
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object. - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Apply READ_ACP ACL on the object to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 7 & 8: Account switch"
            "Applied READ_ACP ACL on the object to account2. - run from default account")
        self.log.info(
            "Step 9: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 9: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info(
            "Step 10 & 11: Account switch"
            "Get object. - run from account1")
        resp = self.s3test_obj_1.object_download(
            self.bucket_name,
            object_names[0],
            "test1_d.txt")
        assert resp[0], resp[1]
        self.log.info(
            "Step 10 & 11: Account switch"
            "Get object. - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow GetObject api on object in policy and READ_ACP ACL on the object ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-18453")
    @CTFailOn(error_handler)
    def test_6555(self):
        """Test Bucket Policy Multiple Conditions each Condition with Multiple Keys and Multiple Values."""
        self.log.info(
            "STARTED: Test Bucket Policy Multiple Conditions "
            "each Condition with Multiple Keys and Multiple Values")
        bucket_policy = BKT_POLICY_CONF["test_6555"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = errmsg.ACCESS_DENIED_ERR_KEY
        object_lst = []
        self.log.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            obj_prefix,
            object_lst)

        acc_details = []
        for i in range(8):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account2_id = acc_details[0][1]["account_id"]
        account2_cid = acc_details[0][1]["canonical_id"]
        account3_cid = acc_details[1][1]["canonical_id"]
        account4_cid = acc_details[2][1]["canonical_id"]
        account5_cid = acc_details[3][1]["canonical_id"]
        account6_cid = acc_details[4][1]["canonical_id"]
        account7_cid = acc_details[5][1]["canonical_id"]
        account8_cid = acc_details[6][1]["canonical_id"]
        account9_cid = acc_details[7][1]["canonical_id"]
        s3_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=acc_details[0][1]["access_key"],
            secret_key=acc_details[0][1]["secret_key"])

        self.log.info(
            "Step 2:Create a json file for  a Bucket Policy having Multiple Conditions with Multiple Keys "
            "and each Key having Multiple Values. Action - Put Object and Effect - Allow")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account2_id)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-full-control"].format([account2_cid, account3_cid])
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-read"].format([account4_cid, account5_cid])
        bucket_policy["Statement"][0]["Condition"]["StringLike"]["s3:x-amz-grant-full-control"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-full-control"].format([account6_cid, account7_cid])
        bucket_policy["Statement"][0]["Condition"]["StringLike"]["s3:x-amz-grant-read"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-read"].format([account8_cid, account9_cid])
        self.log.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 4 : Verify the Bucket Policy from cross account")
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        self.log.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp = self.acl_obj.put_object_with_acl2(self.bucket_name,
                                                 "{}{}".format(
                                                     object_lst[0], str(time.time())),
                                                 self.file_path,
                                                 grant_full_control="id={}".format(
                                                     account2_cid),
                                                 grant_read="id={}".format(account4_cid))
        assert resp[0], resp[1]
        resp = self.acl_obj.put_object_with_acl2(self.bucket_name,
                                                 "{}{}".format(
                                                     object_lst[0], str(time.time())),
                                                 self.file_path,
                                                 grant_full_control="id={}".format(
                                                     account3_cid),
                                                 grant_read="id={}".format(account5_cid))
        assert resp[0], resp[1]
        try:
            s3_obj1.put_object_with_acl2(self.bucket_name,
                                         "{}{}".format(object_lst[0], str(time.time())),
                                         self.file_path,
                                         grant_full_control="id={}".format(account6_cid),
                                         grant_read="id={}".format(account4_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl2(self.bucket_name,
                                         "{}{}".format(object_lst[0], str(time.time())),
                                         self.file_path,
                                         grant_full_control="id={}".format(account2_cid),
                                         grant_read="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(self.bucket_name,
                                        "{}{}".format(object_lst[0], str(time.time())),
                                        self.file_path,
                                        grant_full_control="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(self.bucket_name, "{}{}".format(object_lst[0], str(
                time.time())), self.file_path, grant_read="id={}".format(account5_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(self.bucket_name,
                                        "{}{}".format(object_lst[0], str(time.time())),
                                        self.file_path,
                                        grant_full_control="id={}".format(account4_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj1.put_object_with_acl(self.bucket_name, "{}{}".format(object_lst[0], str(
                time.time())), self.file_path, grant_read="id={}".format(account2_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            s3_obj2.put_object(
                self.bucket_name,
                object_lst[0],
                self.file_path)
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "ENDED: Bucket Policy Multiple Conditions each "
            "Condition with Multiple Keys and Multiple Values")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8040")
    @CTFailOn(error_handler)
    def test_5138(self):
        """Test apply allow GetobjectAcl api on object in policy and WRITE_ACP ACL on the object."""
        self.log.info(
            "STARTED: Test apply allow GetobjectAcl api on object in policy and WRITE_ACP ACL on the object."
        )
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_5138"]["bucket_policy"]
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow GetObjectAcl api on object in the policy "
            "to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(
            "Step 2: Created a policy json and Allow GetObjectAcl api on bucket in the policy "
            "to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Apply WRITE_ACP ACL on the object to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_write_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 7 & 8: Account switch"
            "Applied WRITE_ACP ACL on the object to account2. - run from default account")
        self.log.info(
            "Step 9: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 9: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow GetobjectAcl api on object in policy and WRITE_ACP ACL on the object."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8039")
    @CTFailOn(error_handler)
    def test_5121(self):
        """Test apply WRITE_ACP ACL on the object and deny PutobjectAcl on object api in policy."""
        self.log.info(
            "STARTED: Test apply WRITE_ACP ACL on the object and deny PutobjectAcl on object api in policy ."
        )
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_5121"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply WRITE_ACP ACL on the object to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_write_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Apply WRITE_ACP ACL on the object to account2. - run from default account")
        self.log.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch"
                      "Put object ACL. - run from account1")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_write_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info("Step 4 & 5: Put object ACL. - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch"
            " Create a policy json and Deny PutObjectAcl api on object in policy to account2."
            "- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Created a policy json and Deny PutObjectAcl api on object in policy "
            "to account2.- run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch"
                      "Put object ACL - run from account1")
        try:
            acl_obj_1.put_object_with_acl(
                bucket_name=self.bucket_name,
                key=object_names[0],
                file_path=self.file_path,
                grant_write_acp="id={}".format(canonical_id_user_1))
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 10 & 11: Account switch "
                      "put object ACL - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply WRITE_ACP ACL on the object and deny PutobjectAcl "
            "on object api in policy .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-18454")
    @CTFailOn(error_handler)
    def test_6557(self):
        """Test Bucket Policy Multiple Conditions having one Invalid Condition."""
        self.log.info(
            "STARTED: Test Bucket Policy Multiple Conditions having one Invalid Condition")
        bucket_policy = BKT_POLICY_CONF["test_6555"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        err_message = "MalformedPolicy"
        object_lst = []
        self.log.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            obj_prefix,
            object_lst)
        acc_details = []
        for i in range(2):
            acc_name = "{0}{1}".format(self.account_name, i)
            email_id = "{0}{1}".format(acc_name, "@seagate.com")
            resp = self.rest_obj.create_s3_account(
                acc_name, email_id, self.s3acc_passwd)
            acc_details.append(resp)
            self.account_list.append(acc_name)
        account2_id = acc_details[0][1]["account_id"]
        account2_cid = acc_details[0][1]["canonical_id"]
        account3_cid = acc_details[1][1]["canonical_id"]
        self.log.info(
            "Step 2 : Create a json file for  a Bucket Policy having one Invalid Condition. "
            "Action - Put Object and Effect - Allow.")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account2_id)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"] = \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"][
                "s3:x-amz-grant-full-control"].format([account2_cid, account3_cid])
        self.log.info("Applying policy to a bucket %s", self.bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        self.log.info(
            "Step 3 : Put policy on the bucket")
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "ENDED: Test Bucket Policy Multiple Conditions having one Invalid Condition")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8036")
    @CTFailOn(error_handler)
    def test_5118(self):
        """Test apply READ ACL on the object and deny GetObject api on object in policy."""
        self.log.info(
            "STARTED: Test apply READ ACL on the object and deny GetObject api on object in policy ."
        )
        random_id = str(time.time())
        bucket_policy = BKT_POLICY_CONF["test_5118"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        self.s3test_obj_1 = result_1[1]
        acl_obj_1 = result_1[2]
        self.log.info("New account created with %s", acl_obj_1)
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply READ ACL on the object to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied READ ACL on the object to account2. - run from default account")
        self.log.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch "
                      "Get object. - run from account1")
        resp = self.s3test_obj_1.object_download(
            self.bucket_name,
            object_names[0],
            "test1_d.txt")
        assert resp[0], resp[1]
        self.log.info("Step 4 & 5: Account switch"
                      " Get object. - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny GetObject api on object in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch"
            " Created a policy json and Deny GetObject api on object in the policy to account2.- run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch"
                      "Get object. - run from account1")
        try:
            self.s3test_obj_1.object_download(
                self.bucket_name,
                object_names[0],
                "test1_d.txt")
        except CTException as error:
            self.log.error(error.message)
            assert "Forbidden" in error.message, error.message
        self.log.info("Step 10 & 11: Account switch"
                      "Get object.  - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply READ ACL on the object and deny GetObject api on object in policy ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7939")
    @CTFailOn(error_handler)
    def test_5115(self):
        """Test apply READ_ACP ACL on the bucket and deny GetBucketAcl on bucket api in policy."""
        self.log.info(
            "STARTED: Test apply READ_ACP ACL on the bucket and deny GetBucketAcl on bucket api in policy."
        )
        bucket_policy = BKT_POLICY_CONF["test_5115"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch"
                      "Get ACL of the bucket . - run from account1")
        resp = acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4 & 5: Got ACL of the bucket . - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny GetBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Created a policy json and Deny GetBucketAcl api on bucket in the policy to account2.- run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch "
                      "Get ACL of the bucket -run from account1")
        try:
            acl_obj_1.get_bucket_acl(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 10 & 11: Get ACL of the bucket  -run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply READ_ACP ACL on the bucket and deny GetBucketAcl on bucket api in policy."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7938")
    @CTFailOn(error_handler)
    def test_5114(self):
        """Test apply WRITE ACL on the bucket and deny PutObject api on bucket in policy."""
        self.log.info(
            "STARTED: Test apply WRITE ACL on the bucket and deny PutObject api on bucket in policy."
        )
        bucket_policy = BKT_POLICY_CONF["test_5114"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch"
                      "Put object in the bucket . - run from account1")
        resp = self.s3test_obj_1.put_object(
            self.bucket_name, self.object_name, self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4 & 5: Put object in the bucket . - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny PutObject api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch "
            "Created a policy json and Deny PutObject api on bucket in the policy to account2.- run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch "
                      "Put object in the bucket -run from account1")
        try:
            self.s3test_obj_1.put_object(
                self.bucket_name, self.object_name, self.file_path)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 10 & 11: Put object in the bucket  -run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply WRITE ACL on the bucket and deny PutObject api on bucket in policy."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7937")
    @CTFailOn(error_handler)
    def test_5110(self):
        """Test apply READ ACL on the bucket and deny ListBucket api on bucket in policy."""
        self.log.info(
            "STARTED: Test apply READ ACL on the bucket and deny ListBucket api on bucket in policy."
        )
        bucket_policy = BKT_POLICY_CONF["test_5110"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch "
                      "List object in the bucket . - run from account1")
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3test_obj_1)
        self.log.info("Step 4 & 5: "
                      "Listed object in the bucket . - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny ListBucket api on bucket in the policy to account2.-"
            " run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch"
            "Created a policy json and Deny ListBucket api on bucket in the policy to account2.-"
            " run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch"
                      "List objects from the bucket -run from account1")
        try:
            self.s3test_obj_1.object_list(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 10 & 11: Account switch "
                      "List objects from the bucket  -run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply READ ACL on the bucket and deny ListBucket api on bucket in policy."
        )

    # Commented this test case as it is failing in current build and a bug was
    # already raised for this - EOS-7062
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7940")
    @CTFailOn(error_handler)
    def test_5116(self):
        """Test apply WRITE_ACP ACL on the bucket and deny PutBucketAcl on bucket api in policy."""
        self.log.info(
            "STARTED: Test apply WRITE_ACP ACL on the bucket and deny PutBucketAcl on bucket api in policy ."
        )
        bucket_policy = BKT_POLICY_CONF["test_5116"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch"
                      "Put ACL on the bucket . - run from account1")
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info("Step 4 & 5: Account switch "
                      "Put ACL on the bucket . - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny PutBucketAcl api on bucket in the policy to account2."
            "- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal']['CanonicalUser'].format(
                str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch "
            "Created a policy json and Deny PutBucketAcl api on bucket in the policy to account2."
            "- run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch"
                      "Put ACL of the bucket -run from account1")
        try:
            acl_obj_1.put_bucket_acl(
                bucket_name=self.bucket_name,
                grant_write_acp="id={}".format(canonical_id_user_1))
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 10 & 11: Account switch"
                      "Put ACL of the bucket  -run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply WRITE_ACP ACL on the bucket and deny PutBucketAcl on bucket api in policy."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7941")
    @CTFailOn(error_handler)
    def test_5117(self):
        """Test apply FULL_CONTROL ACL on the bucket and deny GetBucketAcl on bucket api in policy."""
        self.log.info(
            "STARTED: Test apply FULL_CONTROL ACL on the bucket and deny GetBucketAcl on bucket api in policy ."
        )
        bucket_policy = BKT_POLICY_CONF["test_5117"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply FULL_CONTROL ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied FULL_CONTROL ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch "
                      "Get ACL of the bucket . - run from account1")
        resp = acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 4 & 5: Account switch"
                      "Get ACL of the bucket . - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny GetBucketAcl api on bucket in the policy to account2."
            "- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch "
            "Created a policy json and Deny GetBucketAcl api on bucket in the policy to account2."
            "- run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch "
                      "Get ACL of the bucket - run from account1")
        try:
            acl_obj_1.get_bucket_acl(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 10 & 11: Account switch "
                      "Get ACL of the bucket  - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply FULL_CONTROL ACL on the bucket and deny GetBucketAcl on bucket api in policy ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7943")
    @CTFailOn(error_handler)
    def test_5120(self):
        """Test apply READ_ACP ACL on the object and deny GetobjectAcl on object api in policy."""
        self.log.info(
            "STARTED: Test apply READ_ACP ACL on the object and deny GetobjectAcl on object api in policy ."
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_5120"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch"
                      "Get object ACL. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info("Step 4 & 5: Account switch "
                      "Get object ACL. - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny GetObjectAcl api on object in policy to account2.-"
            " run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch"
            " Created a policy json and Deny GetObjectAcl api on object in policy to account2.-"
            " run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch "
                      "Get object ACL - run from account1")
        try:
            acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                     object_key=object_names[0])
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 10 & 11: Account switch"
                      "Get object ACL - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply READ_ACP ACL on the object and deny GetobjectAcl on object api"
            " in policy .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7945")
    @CTFailOn(error_handler)
    def test_5122(self):
        """Test apply FULL_CONTROL ACL on the object and deny GetobjectAcl on object api in policy."""
        self.log.info(
            "STARTED: Test apply FULL_CONTROL ACL on the object and deny GetobjectAcl on object api in policy ."
        )
        bucket_policy = BKT_POLICY_CONF["test_5122"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Apply FULL_CONTROL ACL on the object to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_full_control="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Apply FULL_CONTROL ACL on the object to account2. - run from default account")
        self.log.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info("Step 4 & 5: Account switch "
                      "Get object ACL. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info("Step 4 & 5: Account switch"
                      "Get object ACL. - run from account1")
        self.log.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny GetObjectAcl api on object in policy to account2.-"
            " run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 6 & 7: Account switch"
            "Created a policy json and Denid GetObjectAcl api on object in policy to account2.-"
            " run from default account")
        self.log.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 10 & 11: Account switch "
                      "Get object ACL - run from account1")
        try:
            acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                     object_key=object_names[0])
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 10 & 11: Account switch "
                      "Get object ACL - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply FULL_CONTROL ACL on the object and deny GetobjectAcl on object "
            "api in policy .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7946")
    @CTFailOn(error_handler)
    def test_5123(self):
        """Test apply allow ListBucket api on bucket in policy and WRITE ACL on the bucket."""
        self.log.info(
            "STARTED: Test apply allow ListBucket api on bucket in policy and WRITE ACL on the bucket."
        )
        bucket_policy = BKT_POLICY_CONF["test_5123"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and allow ListBucket api on bucket in the policy "
            "to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 2: Created a policy json and allow ListBucket api on bucket in the policy "
            "to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 5 & 6: Account switch"
                      "List objects in the bucket - run from account1")
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3test_obj_1)
        self.log.info("Step 5 & 6: Account switch "
                      "List objects in the bucket - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Apply WRITE ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 7 & 8: Account switch"
            "Applied WRITE ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 9: Check the bucket ACL to verify and applied ACL. - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 9: Check the bucket ACL to verify and applied ACL. - run from default account")
        self.log.info("Step 10 & 11: Account switch "
                      "List objects from the bucket - run from account1")
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3test_obj_1)
        self.log.info("Step 10 & 11: Account switch"
                      "List objects from the bucket - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow ListBucket api on bucket in policy and WRITE ACL on the bucket."
        )

    # Commented this test case as it is failing in current build and a bug was
    # already raised for this - EOS-7062
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7947")
    @CTFailOn(error_handler)
    def test_5126(self):
        """Test apply allow PutBucketAcl api on bucket in policy and READ_ACP ACL on the bucket."""
        self.log.info(
            "STARTED: Test apply allow PutBucketAcl api on bucket in policy and READ_ACP ACL on the bucket."
        )
        bucket_policy = BKT_POLICY_CONF["test_5126"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        s3_bkt_policy_obj_1 = result_1[3]
        self.log.info("New account created with %s ", s3_bkt_policy_obj_1)
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and allow PutBucketAcl api on bucket in the policy "
            "to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal']['CanonicalUser'].format(
                str(canonical_id_user_1))
        self.log.info(
            "Step 2: Create a policy json and allow PutBucketAcl api on bucket in the policy "
            "to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Apply READ_ACP ACL on the bucket to account2. - run from account1")
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch "
            "Applied READ_ACP ACL on the bucket to account2. - run from account1")
        self.log.info(
            "Step 7: Check the bucket ACL to verify and applied ACL. - run from account1")
        resp = acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 7: Check the bucket ACL to verify and applied ACL. - run from account1")
        self.log.info("Step 8: Put bucket ACL - run from account1")
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info("Step 8: Put bucket ACL - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow PutBucketAcl api on bucket in policy and READ_ACP ACL on the bucket."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7936")
    @CTFailOn(error_handler)
    def test_5124(self):
        """Test apply allow PutObject api on bucket in policy and READ ACL on the bucket."""
        self.log.info(
            "STARTED: Test apply allow PutObject api on bucket in policy and READ ACL on the bucket."
        )
        bucket_policy = BKT_POLICY_CONF["test_5124"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created with %s ", acl_obj_1)
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow PutObject api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 2: Created a policy json and Allow PutObject api on bucket in the policy to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "upload new objects in the bucket. - run from account1")
        resp = self.s3test_obj_1.put_object(
            self.bucket_name, self.object_name, self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "uploaded new object in the bucket. - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Apply READ ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 7 & 8: Account switch"
            "Applied READ ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        self.log.info("Step 10 & 11: Account switch"
                      "Put object in the bucket . - run from account1")
        resp = self.s3test_obj_1.put_object(
            self.bucket_name, self.object_name, self.file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 10 & 11: Put object in the bucket . - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow PutObject api on bucket in policy and READ ACL on the bucket."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7944")
    @CTFailOn(error_handler)
    def test_5125(self):
        """Test apply allow GetBucketAcl api on bucket in policy and WRITE_ACP ACL on the bucket."""
        self.log.info(
            "STARTED: Test apply allow GetBucketAcl api on bucket in policy and WRITE_ACP ACL on the bucket."
        )
        bucket_policy = BKT_POLICY_CONF["test_5125"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_prefix = self.obj_name_prefix
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow GetBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        self.log.info(
            "Step 2: Created a policy json and Allow GetBucketAcl api on bucket in the policy to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get ACL's of the bucket - run from account1")
        resp = acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get ACL's of the bucket - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Apply WRITE_ACP ACL on the bucket to account2. - run from default account")
        resp = self.acl_obj.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write_acp="id={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 7 & 8: Account switch"
            "Applied WRITE_ACP ACL on the bucket to account2. - run from default account")
        self.log.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        self.log.info("Step 10 & 11: Account switch"
                      "Get bucket ACL. - run from account1")
        resp = acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 10 & 11:  Account switch"
            "Get bucket ACL - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow GetBucketAcl api on bucket in policy and WRITE_ACP ACL on the bucket."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-7942")
    @CTFailOn(error_handler)
    def test_5137(self):
        """Test apply allow GetobjectAcl api on object in policy and READ ACL on the object."""
        self.log.info(
            "STARTED: Test apply allow GetobjectAcl api on object in policy and READ ACL on the object ."
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_5137"]["bucket_policy"]
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result_1[0]
        acl_obj_1 = result_1[2]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow GetObjectAcl api on object in the policy"
            " to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser'] = \
            bucket_policy['Statement'][0]['Principal'][
                'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(
            "Step 2: Created a policy json and Allow GetObjectAcl api on bucket in the policy"
            " to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Apply READ ACL on the object to account2. - run from default account")
        resp = self.acl_obj.put_object_with_acl(
            bucket_name=self.bucket_name,
            key=object_names[0],
            file_path=self.file_path,
            grant_read="ID={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info(
            "Step 7 & 8: Account switch"
            "Applied READ ACL on the object to account2. - run from default account")
        self.log.info(
            "Step 9: Check the object ACL to verify the applied ACL.  - run from default account")
        resp = self.acl_obj.get_object_acl(bucket=self.bucket_name,
                                           object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 9: Checked the object ACL to verify the applied ACL.  - run from default account")
        self.log.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test apply allow GetobjectAcl api on object in policy and READ ACL on the object."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9031")
    @CTFailOn(error_handler)
    def test_6967(self):
        """Test bucket policy authorization on bucket with API ListBucket."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API ListBucket"
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6967"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 5 & 6: Account switch "
                      "List object in the bucket . - run from account1")
        self.list_objects_with_diff_acnt(self.bucket_name, self.s3test_obj_1)
        self.log.info("Step 5 & 6: "
                      "Listed object in the bucket . - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API ListBucket"
        )

    # Defect raised for this test cases - EOS-7062
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9033")
    @CTFailOn(error_handler)
    def test_6969(self):
        """Test bucket policy authorization on bucket with API PutBucketAcl."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API PutBucketAcl ."
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6969"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj_1 = result_1[2]
        account_id_1 = result_1[6]
        canonical_id_user_1 = result_1[0]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 5 & 6: Account switch"
                      "Put ACL on account1 bucket . - run from account1")
        resp = acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_read_acp="ID={}".format(canonical_id_user_1))
        assert resp[0], resp[1]
        self.log.info("Step 5 & 6: Account switch "
                      "Put ACL on account1 bucket . - run from account1")
        self.log.info("Step 7: Get acl of bucket - run from account1")
        resp = acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 7: Get acl of bucket - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API PutBucketAcl ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9038")
    @CTFailOn(error_handler)
    def test_6991(self):
        """Test bucket policy authorization on bucket with API PutBucketPolicy."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API PutBucketPolicy"
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6991"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        s3_bkt_policy_obj_1 = result_1[3]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        try:
            s3_bkt_policy_obj_1.put_bucket_policy(
                self.bucket_name, bucket_policy)
        except CTException as error:
            self.log.error(error.message)
            assert "validation failed" in error.message, error.message
            self.log.info(
                "Step 6: Applying policy on a bucket using user of account 2 is failed with error %s",
                "validation failed")
        self.log.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API PutBucketPolicy"
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9039")
    @CTFailOn(error_handler)
    def test_6992(self):
        """Test bucket policy authorization on bucket with API GetBucketPolicy."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketPolicy."
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6992"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        s3_bkt_policy_obj_1 = result_1[3]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        try:
            s3_bkt_policy_obj_1.get_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 6: Applying policy on a bucket using user of account 2 is failed with error"
                "MethodNotAllowed")
        self.log.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketPolicy."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9041")
    @CTFailOn(error_handler)
    def test_6999(self):
        """Test bucket policy authorization on object with API GetObject."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API GetObject ."
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6999"]["bucket_policy"]
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json and Allow GetObjectAcl api on object in the policy"
            " to account2.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json and Allow GetObjectAcl api on bucket in the policy"
            " to account2.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object of default account bucket. - run from account1")
        resp = self.s3test_obj_1.object_download(
            self.bucket_name,
            object_names[0],
            "test1_d.txt")
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object of default account bucket - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API GetObject ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9042")
    @CTFailOn(error_handler)
    def test_7000(self):
        """Test bucket policy authorization on object with API GetObjectAcl."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API GetObjectAcl ."
        )
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_7000"]["bucket_policy"]
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        acl_obj_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object acl of default account bucket. - run from account1")
        resp = acl_obj_1.get_object_acl(bucket=self.bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get object acl of default account bucket - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API GetObjectAcl ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9032")
    @CTFailOn(error_handler)
    def test_6968(self):
        """Test bucket policy authorization on bucket with API ListBucketMultipartUploads."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API ListBucketMultipartUploads."
        )
        random_id = str(time.time())
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6968"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.s3_mp_obj_1 = result_1[8]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket - run from default account")
        obj_name = "{0}{1}".format(obj_prefix, random_id)
        self.log.info(
            "Step 2: Create a multipart upload on the bucket - run from default account")
        resp = self.s3_mp_obj.create_multipart_upload(
            self.bucket_name, obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Created a multipart upload on the bucket - run from default account")
        self.log.info(
            "Step 3: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 3: Created a policy json.- run from default account")
        self.log.info(
            "Step 4 & 5: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 4 & 5: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 6 & 7: Account switch"
            "List bucket multipart - run from account1")
        resp = self.s3_mp_obj_1.list_multipart_uploads(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 6 & 7: Account switch"
            "Listed bucket multipart - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API ListBucketMultipartUploads."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9034")
    @CTFailOn(error_handler)
    def test_6978(self):
        """Test bucket policy authorization on bucket with API GetBucketTagging."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketTagging."
        )
        bucket_policy = BKT_POLICY_CONF["test_6978"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        s3_bkt_tag_obj_1 = result_1[7]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket - run from default account")
        self.log.info(
            "Step 2: Put bucket tagging - run from default account")
        resp = self.s3_tag_obj.set_bucket_tag(self.bucket_name,
                                              key="organization",
                                              value="marketing")
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Put bucket tagging - run from default account")
        self.log.info(
            "Step 3: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 3: Created a policy json.- run from default account")
        self.log.info(
            "Step 4 & 5: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 4 & 5: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 6 & 7: Account switch"
            "Get bucket tagging - run from account1")
        resp = s3_bkt_tag_obj_1.get_bucket_tagging(self.bucket_name)
        assert resp["TagSet"][0][
            "Key"] == "organization0", resp
        assert resp["TagSet"][0][
            "Value"] == "marketing0", resp
        self.log.info(
            "Step 6 & 7: Account switch"
            "Get bucket tagging - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketTagging."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9035")
    @CTFailOn(error_handler)
    def test_6987(self):
        """Test bucket policy authorization on bucket with API GetBucketLocation."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketLocation."
        )
        bucket_policy = BKT_POLICY_CONF["test_6987"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        s3_bkt_tag_obj_1 = result_1[7]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket - run from default account")
        self.log.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get bucket location - run from account1")
        resp = s3_bkt_tag_obj_1.bucket_location(self.bucket_name)
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            assert resp["LocationConstraint"] == "default", resp
        else:
            assert resp["LocationConstraint"] == "us-west-2", resp
        self.log.info(
            "Step 5 & 6: Account switch"
            "Get bucket location - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketLocation."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9036")
    @CTFailOn(error_handler)
    def test_6988(self):
        """Test bucket policy authorization on bucket with API PutBucketTagging."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API PutBucketTagging ."
        )
        bucket_policy = BKT_POLICY_CONF["test_6988"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        s3_bkt_tag_obj_1 = result_1[7]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket - run from default account")
        self.log.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Put bucket tagging - run from account1")
        resp = s3_bkt_tag_obj_1.set_bucket_tag(self.bucket_name,
                                               key="organization",
                                               value="marketing")
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: Account switch"
            "Put bucket tagging - run from account1")
        self.log.info(
            "Step 7 & 8: Account switch"
            "Get bucket tagging - run from default")
        resp = self.s3_tag_obj.get_bucket_tagging(self.bucket_name)
        assert resp["TagSet"][0][
            "Key"] == "organization0", resp
        assert resp["TagSet"][0][
            "Value"] == "marketing0", resp
        self.log.info(
            "Step 7 & 8: Account switch"
            "Get bucket tagging - run from default")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API PutBucketTagging ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9037")
    @CTFailOn(error_handler)
    def test_6990(self):
        """Test bucket policy authorization on bucket with API DeleteBucketPolicy."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API DeleteBucketPolicy."
        )
        bucket_policy = BKT_POLICY_CONF["test_6990"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        s3_bkt_policy_obj_1 = result_1[3]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket - run from default account")
        self.log.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json.- run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Delete bucket policy - run from account1")
        try:
            s3_bkt_policy_obj_1.delete_bucket_policy(self.bucket_name)
        except CTException as error:
            self.log.error(error.message)
            assert "MethodNotAllowed" in error.message, error.message
            self.log.info(
                "Step 6: Delete bucket policy is failed with error"
                "MethodNotAllowed")
        self.log.info(
            "Step 5 & 6: Account switch"
            "Delete bucket policy - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API DeleteBucketPolicy."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9040")
    @CTFailOn(error_handler)
    def test_6997(self):
        """Test bucket policy authorization on object with API DeleteObject."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API DeleteObject ."
        )
        random_id = str(time.time())
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6997"]["bucket_policy"]
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        resp = system_utils.create_file(
            self.file_path,
            10)
        assert resp[0], resp[1]
        object_names = []
        for i in range(2):
            obj_name = "{0}{1}{2}".format(obj_prefix, random_id, str(i))
            resp = self.s3_obj.put_object(
                self.bucket_name, obj_name, self.file_path)
            assert resp[0], resp[1]
            object_names.append(obj_name)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        bucket_policy['Statement'][0]['Resource'] = bucket_policy['Statement'][0][
            'Resource'].format(self.bucket_name, object_names[0])
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 5 & 6: Account switch "
                      "Delete object - run from account1")
        resp = self.s3test_obj_1.delete_object(
            self.bucket_name,
            object_names[0])
        assert resp[0], resp[1]
        self.log.info("Step 5 & 6: Account switch "
                      "Delete object - run from account1")
        self.log.info("Step 7 & 8: Account switch "
                      "List object - run from default")
        resp = self.s3_obj.list_objects_with_prefix(
            self.bucket_name, prefix="obj_policy")
        assert resp[0], resp[1]
        self.log.info("Step 7 & 8: Account switch "
                      "List object - run from default")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown.")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API DeleteObject ."
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8721")
    @CTFailOn(error_handler)
    def test_1295(self):
        """Test Create Bucket Policy using StringNotEquals Condition Operator and Deny Action."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringNotEquals Condition Operator and Deny Action")
        bucket_policy = BKT_POLICY_CONF["test_1295"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating a bucket and uploading objects to it")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        self.log.info("Step 1: Created a bucket and uploaded objects to it")
        self.log.info("Step 2: Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringNotEquals"]["s3:prefix"] = \
            bucket_policy["Statement"][
                0]["Condition"]["StringNotEquals"]["s3:prefix"].format(self.obj_name_prefix)
        self.log.info(bucket_policy)
        self.log.info("Step 2: Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Listing objects of bucket with prefix")
        try:
            resp = self.s3_obj.list_objects_with_prefix(
                self.bucket_name, prefix=self.obj_name_prefix)
            assert resp[0], resp[1]
            self.log.info(
                "Step 3: Listed objects of bucket with prefix successfully")
            self.log.info("Step 4: Listing objects of bucket without prefix")
            try:
                self.s3_obj.object_list(self.bucket_name)
            except CTException as error:
                self.log.error(error.message)
                assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 4: Listing objects of bucket without prefix failed with %s",
                errmsg.ACCESS_DENIED_ERR_KEY)
        except CTException as error:
            self.log.error(error.message)
        finally:
            self.log.info(
                "Step 5: Deleting a bucket policy for bucket %s",
                self.bucket_name)
            resp = self.s3_bkt_policy_obj.delete_bucket_policy(
                self.bucket_name)
            assert resp[0], resp[1]
            time.sleep(S3_CFG["sync_delay"])
            self.log.debug("Waiting for Policy to be synced for bucket")
            self.log.info(
                "Step 5: Deleted a bucket policy for bucket %s",
                self.bucket_name)
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringNotEquals Condition Operator and Deny Action")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8722")
    @CTFailOn(error_handler)
    def test_1297(self):
        """Test Create Bucket Policy using StringEquals Condition Operator and Deny Action."""
        self.log.info(
            "STARTED: Test Create Bucket Policy using StringEquals Condition Operator and Deny Action")
        bucket_policy = BKT_POLICY_CONF["test_1297"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Step 1: Creating a bucket and uploading objects to it")
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix)
        self.log.info("Step 1: Created a bucket and uploaded objects to it")
        self.log.info("Step 2: Creating a json for bucket policy")
        policy_id = f"Policy{uuid.uuid4()}"
        policy_sid = f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"] = bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"] = bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:prefix"] = \
            bucket_policy["Statement"][
                0]["Condition"]["StringEquals"]["s3:prefix"].format(self.obj_name_prefix)
        self.log.info(bucket_policy)
        self.log.info("Step 2: Created a json for bucket policy")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Listing objects of bucket with prefix")
        try:
            self.s3_obj.list_objects_with_prefix(
                self.bucket_name, prefix=self.obj_name_prefix)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 3: Listed objects of bucket with prefix failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        self.log.info("Step 4: Listing objects of bucket without prefix")
        resp = self.s3_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Listing objects of bucket without prefix successfully")
        self.log.info(
            "ENDED: Test Create Bucket Policy using StringEquals Condition Operator and Deny Action")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8720")
    @CTFailOn(error_handler)
    def test_4598(self):
        """Test principal arn combination with account-id and user as root."""
        self.log.info(
            "STARTED: Test principal arn combination with account-id and user as root.")
        bucket_policy = BKT_POLICY_CONF["test_4598"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        obj_count = 2
        self.log.info("Step 1: Creating a bucket and uploading objects to it")
        self.create_bucket_put_objects(
            self.bucket_name, obj_count, self.obj_name_prefix)
        self.log.info("Step 1: Created a bucket and uploaded objects to it")
        resp = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = resp[6]
        self.log.info("Step 2: Creating a json for bucket policy")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.log.info(bucket_policy)
        self.log.info("Step 2: Created a json for bucket policy")
        self.log.info("Step 3: Applying bucket policy on a bucket")
        bkt_policy_json = json.dumps(bucket_policy)
        try:
            self.s3_bkt_policy_obj.put_bucket_policy(
                self.bucket_name, bkt_policy_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR in error.message, error.message
        self.log.info(
            "Step 3: Applying bucket policy on a bucket failed with %s",
            errmsg.S3_BKT_POLICY_INVALID_PRINCIPAL_ERR)
        self.log.info(
            "ENDED: Test principal arn combination with account-id and user as root.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8702")
    @CTFailOn(error_handler)
    def test_7001(self):
        """Test bucket policy authorization on object with API PutObject"""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API PutObject")
        bucket_policy = BKT_POLICY_CONF["test_7001"]["bucket_policy"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_acc2 = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Creating a json to allow PutObject for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 2: Created a json to allow PutObject for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Uploading an object using account 2")
        resp = s3_obj_acc2.put_object(
            self.bucket_name, object_lst[0], self.file_path)
        assert resp[0], resp[1]
        self.log.info("Step 3: Uploaded an object using account 2")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API PutObject")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8703")
    @CTFailOn(error_handler)
    def test_7002(self):
        """Test bucket policy authorization on object with API PutObjectAcl."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API PutObjectAcl")
        bucket_policy = BKT_POLICY_CONF["test_7002"]["bucket_policy"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.acl_obj_acc2 = acc_details[2]
        account_id = acc_details[6]
        canonical_id = acc_details[0]
        self.log.info(
            "Step 2: Creating a json to allow PutObjectAcl for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 2: Created a json to allow PutObjectAcl for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Give grant_read_acp permissions to account 2")
        resp = self.acl_obj_acc2.put_object_canned_acl(
            self.bucket_name,
            object_lst[0],
            grant_read_acp="id={0}".format(canonical_id))
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: grant_read_acp permission has been given to account 2")
        self.log.info("Step 4: Retrieving object acl using account 2")
        resp = self.acl_obj_acc2.get_object_acl(
            self.bucket_name, object_lst[0])
        assert resp[0], resp[1]
        self.log.info("Step 4: Retrieved object acl using account 2")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API PutObjectAcl")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8704")
    @CTFailOn(error_handler)
    def test_7009(self):
        """Test bucket policy authorization on object with API PutObjectTagging."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API PutObjectTagging")
        bucket_policy = BKT_POLICY_CONF["test_7009"]["bucket_policy"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3_tag_obj_acc2 = acc_details[7]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Creating a json to allow PutObjectTagging for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 2: Created a json to allow PutObjectTagging for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Setting tag to an object from account 2")
        resp = self.s3_tag_obj_acc2.set_object_tag(
            self.bucket_name, object_lst[0], "testkey", "testvalue")
        assert resp[0], resp[1]
        self.log.info("Step 3: Tag was set to an object from account 2")
        self.log.info("Step 4: Retrieving tag of an object using account 1")
        resp = self.s3_tag_obj.get_object_tags(self.bucket_name, object_lst[0])
        assert resp[0], resp[1]
        self.log.info("Step 4: Retrieved tag of an object using account 1")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API PutObjectTagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8705")
    @CTFailOn(error_handler)
    def test_7014(self):
        """Test bucket policy authorization on object with API GetObjectTagging."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API GetObjectTagging")
        bucket_policy = BKT_POLICY_CONF["test_7014"]["bucket_policy"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3_tag_obj_acc2 = acc_details[7]
        account_id = acc_details[6]
        self.log.info("Step 2: Setting tag to an object")
        resp = self.s3_tag_obj.set_object_tag(
            self.bucket_name,
            object_lst[0],
            "testkey",
            "testvalue")
        assert resp[0], resp[1]
        self.log.info("Step 2: Tag was set to an object")
        self.log.info(
            "Step 3: Creating a json to allow GetObjectTagging for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 3: Created a json to allow GetObjectTagging for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 4: Retrieving tag of an object using account 2")
        resp = self.s3_tag_obj_acc2.get_object_tags(
            self.bucket_name, object_lst[0])
        assert resp[0], resp[1]
        self.log.info("Step 4: Retrieved tag of an object using account 2")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API GetObjectTagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-8706")
    @CTFailOn(error_handler)
    def test_7015(self):
        """Test bucket policy authorization on object with API ListMultipartUploadParts."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API ListMultipartUploadParts")
        bucket_policy = BKT_POLICY_CONF["test_7015"]["bucket_policy"]
        self.create_bucket_validate(self.bucket_name)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_mp_obj_acc2 = acc_details[8]
        self.log.info("Step 1: Initiating multipart upload")
        res = self.s3_mp_obj.create_multipart_upload(
            self.bucket_name, "testobj_7015")
        assert res[0], res[1]
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Step 1: Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Step 2: Uploading parts into bucket")
        resp = self.s3_mp_obj.upload_parts(
            mpu_id,
            self.bucket_name,
            "testobj_7015",
            10,
            total_parts=1,
            multipart_obj_path=self.file_path)
        assert resp[0], resp[1]
        assert_utils.assert_equals(len(resp[1]), 1, resp[1])
        parts = res[1]
        self.log.info("Step 2: Uploaded parts into bucket: %s", parts)
        self.log.info(
            "Step 3: Creating a json to allow ListMultipartUploadParts for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, "testobj_7015")
        self.log.info(
            "Step 3: Created a json to allow ListMultipartUploadParts for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 4: Listing parts of multipart upload using account 2")
        resp = s3_mp_obj_acc2.list_parts(
            mpu_id,
            self.bucket_name,
            "testobj_7015")
        assert resp[0], resp[1]
        assert_utils.assert_equals(len(resp[1]["Parts"]),
                                   1, resp[1])
        self.log.info(
            "Step 4: Listed parts of multipart upload: %s using account 2",
            res[1])
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API ListMultipartUploadParts")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8707")
    @CTFailOn(error_handler)
    def test_7016(self):
        """Test bucket policy authorization on object with API AbortMultipartUpload."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API AbortMultipartUpload")
        bucket_policy = BKT_POLICY_CONF["test_7016"]["bucket_policy"]
        self.create_bucket_validate(self.bucket_name)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        account_id = acc_details[6]
        s3_mp_obj_acc2 = acc_details[8]
        self.log.info("Step 1: Initiating multipart upload")
        res = self.s3_mp_obj.create_multipart_upload(
            self.bucket_name, "testobj_7016")
        assert res[0], res[1]
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Step 1: Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info(
            "Step 2: Creating a json to allow AbortMultipartUpload for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, "testobj_7016")
        self.log.info(
            "Step 2: Created a json to allow AbortMultipartUpload for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Aborting multipart upload using account 2")
        res = s3_mp_obj_acc2.abort_multipart_upload(
            self.bucket_name, "testobj_7016", mpu_id)
        assert res[0], res[1]
        self.log.info("Step 3: Aborted multipart upload using account 2")
        self.log.info(
            "Step 4: Verifying multipart got aborted by listing multipart upload using account 1")
        resp = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert mpu_id not in resp[1], resp[1]
        self.log.info("Step 4: Verified that multipart got aborted")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API AbortMultipartUpload")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8708")
    @CTFailOn(error_handler)
    def test_7849(self):
        """Test bucket policy authorization on bucket with API Headbucket."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API HeadBucket")
        bucket_policy_1 = BKT_POLICY_CONF["test_7849"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_7849"]["bucket_policy_2"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_acc2 = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Creating a json to allow HeadBucket for account 2")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 2: Created a json to allow HeadBucket for account 2")
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy_1,
            errmsg.S3_BKT_POLICY_INVALID_ACTION_ERR)
        self.log.info(
            "Step 3: Creating a json to allow ListBucket for account 2")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(account_id)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 3: Created a json to allow ListBucket for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy_2)
        self.log.info(
            "Step 4: Performing head bucket on a bucket %s using account 2",
            self.bucket_name)
        resp = s3_obj_acc2.head_bucket(self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1]["BucketName"], self.bucket_name, resp)
        self.log.info(
            "Step 4: Performed head bucket on a bucket %s using account 2",
            self.bucket_name)
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API HeadBucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-8709")
    @CTFailOn(error_handler)
    def test_7850(self):
        """Test bucket policy authorization on object with API HeadObject."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API HeadObject")
        bucket_policy_1 = BKT_POLICY_CONF["test_7850"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_7850"]["bucket_policy_2"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_acc2 = acc_details[1]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Creating a json to allow HeadObject for account 2")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 2: Created a json to allow HeadBucket for account 2")
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy_1,
            errmsg.S3_BKT_POLICY_INVALID_ACTION_ERR)
        self.log.info(
            "Step 3: Creating a json to allow GetObject for account 2")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(account_id)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 3: Created a json to allow GetObject for account 2")

        self.put_get_bkt_policy(self.bucket_name, bucket_policy_2)
        self.log.info("Step 4: Performing head object using account 2")
        resp = s3_obj_acc2.object_info(self.bucket_name, object_lst[0])
        assert resp[0], resp[1]
        self.log.info("Step 4: Performed head object using account 2")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API HeadObject`")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-8710")
    @CTFailOn(error_handler)
    def test_7851(self):
        """Test bucket policy authorization on bucket with API DeleteBucketTagging."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API DeleteBucketTagging")
        bucket_policy_1 = BKT_POLICY_CONF["test_7851"]["bucket_policy_1"]
        bucket_policy_2 = BKT_POLICY_CONF["test_7851"]["bucket_policy_2"]
        self.create_bucket_validate(self.bucket_name)
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3_tag_obj_acc2 = acc_details[7]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Creating a json to allow DeleteBucketTagging for account 2")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_1["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy_1["Statement"][0]["Resource"] = bucket_policy_1["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 2: Created a json to allow DeleteBucketTagging for account 2")
        self.put_invalid_policy(
            self.bucket_name,
            bucket_policy_1,
            errmsg.S3_BKT_POLICY_INVALID_ACTION_ERR)
        self.log.info(
            "Step 3: Creating a json to allow PutBucketTagging for account 2")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy_2["Statement"][0]["Principal"][
                "AWS"].format(account_id)
        bucket_policy_2["Statement"][0]["Resource"] = bucket_policy_2["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info(
            "Step 3: Created a json to allow PutBucketTagging for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy_2)
        self.log.info(
            "Step 4: Set bucket tagging to a bucket %s", self.bucket_name)
        resp = self.s3_tag_obj.set_bucket_tag(
            self.bucket_name, "testkey", "valuekey")
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Tag was set to a bucket %s", self.bucket_name)
        self.log.info("Step 5: Deleting bucket tagging using account 2")
        resp = self.s3_tag_obj_acc2.delete_bucket_tagging(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 5: Deleted bucket tagging using account 2")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API DeleteBucketTagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-8711")
    @CTFailOn(error_handler)
    def test_7852(self):
        """Test bucket policy authorization on object with API DeleteObjectTagging."""
        self.log.info(
            "STARTED: Test bucket policy authorization on object with API DeleteObjectTagging")
        bucket_policy = BKT_POLICY_CONF["test_7852"]["bucket_policy"]
        self.log.info("Step 1: Creating bucket and put multiple objects")
        object_lst = []
        self.create_bucket_put_objects(
            self.bucket_name,
            2,
            self.obj_name_prefix,
            object_lst)
        self.log.info("Step 1: Created bucket with multiple objects")
        acc_details = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        self.s3_tag_obj_acc2 = acc_details[7]
        account_id = acc_details[6]
        self.log.info(
            "Step 2: Creating a json to allow DeleteObjectTagging for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id)
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name, object_lst[0])
        self.log.info(
            "Step 2: Created a json to allow DeleteObjectTagging for account 2")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info("Step 3: Setting tag to an object")
        resp = self.s3_tag_obj.set_object_tag(
            self.bucket_name,
            object_lst[0],
            "testkey",
            "valuekey")
        assert resp[0], resp[1]
        self.log.info("Step 3: Tag was set to an object")
        self.log.info("Step 4: Deleting tag of an object using account 2")
        resp = self.s3_tag_obj_acc2.delete_object_tagging(
            self.bucket_name, object_lst[0])
        assert resp[0], resp[1]
        self.log.info("Step 4: Deleted tag of an object using account 2")
        self.log.info(
            "ENDED: Test bucket policy authorization on object with API DeleteObjectTagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.tags("TEST-9661")
    @CTFailOn(error_handler)
    def test_6966(self):
        """Test bucket policy authorization on bucket with API DeleteBucket."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API DeleteBucket")
        bucket_policy = BKT_POLICY_CONF["test_6966"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Creating a bucket  - run from default account")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created bucket - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 5 & 6: Account switch "
                      "Delete the bucket . - run from account1")
        self.s3test_obj_1.delete_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 5 & 6: "
                      "Bucket deleted successfully. - run from account1")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API DeleteBucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_policy
    @pytest.mark.regression
    @pytest.mark.tags("TEST-9662")
    @CTFailOn(error_handler)
    def test_6923(self):
        """Test bucket policy authorization on bucket with API GetBucketAcl."""
        self.log.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketAcl")
        obj_prefix = self.obj_name_prefix
        bucket_policy = BKT_POLICY_CONF["test_6923"]["bucket_policy"]
        bucket_policy["Statement"][0]["Resource"] = bucket_policy["Statement"][0][
            "Resource"].format(self.bucket_name)
        self.log.info("Create new account.")
        result_1 = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        account_id_1 = result_1[6]
        self.s3test_obj_1 = result_1[1]
        self.s3_obj_acl_1 = result_1[2]
        self.log.info("New account created.")
        self.log.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            self.bucket_name, 2, obj_prefix)
        self.log.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        self.log.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"] = \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(account_id_1)
        self.log.info(bucket_policy)
        self.log.info(
            "Step 2: Created a policy json - run from default account")
        self.log.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(self.bucket_name, bucket_policy)
        self.log.info(
            "Step 3 & 4: Applied the  policy on the bucket. Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        self.log.info("Step 5 & 6: Account switch "
                      "Get bucket ACL. - run from account1")
        resp = self.s3_obj_acl_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 5 & 6: "
            "Get bucket ACL response was success. - run from account1")
        self.log.info("set put_bucket_acl to private as part of teardown")
        self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("set put_bucket_acl to private as part of teardown")
        self.log.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketAcl")
