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
"""This file contains test related to Bucket Policy."""
import json
import shutil
import os
import uuid
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils import assert_utils
from commons.utils.system_utils import create_file, remove_dir, remove_file
from libs.s3 import s3_bucket_policy_test_lib, s3_test_lib, iam_test_lib, s3_acl_test_lib, s3_tagging_test_lib, s3_multipart_test_lib
from datetime import datetime, date, timedelta

ASRTOBJ = assert_utils
S3_OBJ = s3_test_lib.S3TestLib()
IAM_OBJ = iam_test_lib.IamTestLib()
ACL_OBJ = s3_acl_test_lib.S3AclTestLib()
LOGGER = logging.getLogger(__name__)
NO_AUTH_OBJ = s3_test_lib.S3LibNoAuth()
S3_TAG_OBJ = s3_tagging_test_lib.S3TaggingTestLib()
S3_MULTIPART_OBJ = s3_multipart_test_lib.S3MultipartTestLib()
S3_BKT_POLICY_OBJ = s3_bucket_policy_test_lib.S3BucketPolicyTestLib()

BKT_POLICY_CONF = read_yaml("config/s3/test_bucket_policy.yaml")[1]
CMN_CONF = read_yaml("config/common_config.yaml")[1]


class TestBucketPolicy():
    """Bucket Policy Testsuite"""

    @CTFailOn(error_handler)
    def setup_method(self):
        """
        Summary: Setup method

        Description: This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        LOGGER.info("STARTED: Setup operations.")
        self.s3test_obj_1 = None
        self.timestamp = time.time()
        self.ldap_user = CMN_CONF["ldap_username"]
        self.ldap_pwd = CMN_CONF["ldap_passwd"]
        LOGGER.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        Summary: Teardown method

        Description: This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete iam accounts, buckets and objects uploaded to that bucket.
        """
        LOGGER.info("STARTED: Teardown operations")
        LOGGER.info(
            "Deleting all buckets/objects created during TC execution")
        if self.s3test_obj_1:
            res_bkt = self.s3test_obj_1.bucket_list()
            for bkt in res_bkt[1]:
                self.s3test_obj_1.delete_bucket(bkt)
        bucket_list = S3_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                BKT_POLICY_CONF["bucket_policy"]["bkt_name_prefix"])]
        S3_OBJ.delete_multiple_buckets(pref_list)
        LOGGER.info("All the buckets/objects deleted successfully")
        LOGGER.info("Deleting the IAM accounts and users")
        all_accounts = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user,
            self.ldap_pwd)[1]
        iam_accounts = [acc["AccountName"]
                        for acc in all_accounts if
                        BKT_POLICY_CONF["bucket_policy"]["acc_name_prefix"] in acc["AccountName"]]
        LOGGER.info(iam_accounts)
        if iam_accounts:
            for acc in iam_accounts:
                LOGGER.debug("Deleting %s account", acc)
                resp = IAM_OBJ.reset_account_access_key_s3iamcli(
                    acc,
                    self.ldap_user,
                    self.ldap_pwd)
                access_key = resp[1]["AccessKeyId"]
                secret_key = resp[1]["SecretKey"]
                s3_obj_temp = s3_test_lib.S3TestLib(access_key, secret_key)
                LOGGER.info("Deleting buckets in %s account if any", acc)
                bucket_list = s3_obj_temp.bucket_list()[1]
                LOGGER.info(bucket_list)
                s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
                    access_key, secret_key)
                for bucket in bucket_list:
                    s3_obj_acl.put_bucket_acl(bucket, acl="private")
                s3_obj_temp.delete_all_buckets()
                IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc)
                LOGGER.debug("Deleted %s account", acc)
        user_list = IAM_OBJ.list_users()[1]
        iam_users = [
            user["UserName"] for user in user_list if user["UserName"].startswith(
                BKT_POLICY_CONF["bucket_policy"]["user_name_prefix"])]
        if iam_users:
            LOGGER.info(
                "Deleting the IAM users and access keys from default account")
            IAM_OBJ.delete_users_with_access_key(iam_users)
            LOGGER.info(
                "Deleted the IAM users and access keys from default account")
        LOGGER.info("Deleting the file created locally for object")
        if os.path.exists(BKT_POLICY_CONF["bucket_policy"]["file_path"]):
            remove_file(
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        LOGGER.info("Local file was deleted")
        LOGGER.info("Deleting the directory created locally for object")
        if os.path.exists(BKT_POLICY_CONF["bucket_policy"]["folder_path"]):
            shutil.rmtree(BKT_POLICY_CONF["bucket_policy"]["folder_path"])
        LOGGER.info("Local directory was deleted")
        LOGGER.info("ENDED: Teardown Operations")

    def create_bucket_put_objects(
            self,
            bucket_name: str,
            object_count: int,
            obj_name_prefix: str,
            obj_lst=None) -> None:
        """
        This method will create specified bucket and upload given numbers of objects into it.

        :param bucket_name: Name of s3 bucket
        :param object_count: Number of object to upload
        :param obj_name_prefix: Object prefix used while uploading an object to bucket
        :param obj_lst: Empty list for adding newly created objects if not passed explicitly
        :return: None
        """
        LOGGER.info(
            "Creating buckets and uploading objects")
        if obj_lst is None:
            obj_lst = []
        resp = create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Creating a bucket with name %s and uploading %d objects",
                bucket_name, object_count)
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        for i in range(object_count):
            obj_name = "{}{}{}".format(
                obj_name_prefix, str(int(time.time())), i)
            resp = S3_OBJ.put_object(
                bucket_name,
                obj_name,
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
            assert resp[0], resp[1]
            LOGGER.info("Created object %s", obj_name)
            obj_lst.append(obj_name)
        LOGGER.info("Created a bucket and uploaded %s objects", object_count)

    def create_s3iamcli_acc(self, account_name: str, email_id: str) -> tuple:
        """
        This function will create IAM accounts with specified account name and email-id

        :param account_name: Name of account to be created
        :param email_id: Email id for account creation
        :return: It returns account details such as canonical_id, access_key, secret_key, account_id and
        s3 objects whcich will be required to perform further operations.
        :type: tuple
        """
        LOGGER.info(
            "Step : Creating account with name %s and email_id %s",
            account_name, email_id)
        create_account = IAM_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        canonical_id = create_account[1]["canonical_id"]
        account_id = create_account[1]["Account_Id"]
        LOGGER.info("Step Successfully created the s3iamcli account")
        s3_obj = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        ACL_OBJ = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        S3_BKT_POLICY_OBJ = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key, secret_key=secret_key)
        s3_bkt_tag_obj = s3_tagging_test_lib.S3TaggingTestLib(
            access_key=access_key, secret_key=secret_key)
        S3_MULTIPART_OBJ = s3_multipart_test_lib.S3MultipartTestLib(
            access_key=access_key, secret_key=secret_key)

        return canonical_id, s3_obj, ACL_OBJ, S3_BKT_POLICY_OBJ, \
            access_key, secret_key, account_id, s3_bkt_tag_obj, S3_MULTIPART_OBJ

    def delete_bucket_policy_with_err_msg(self, bucket_name: str,
                                          s3_obj_one: object,
                                          ACL_OBJ_one: object,
                                          S3_BKT_POLICY_OBJ_one: object,
                                          S3_BKT_POLICY_OBJ_two: object,
                                          test_config: dict) -> None:
        """
        This method will delete a bucket policy applied to the specified bucket.

        It will also handle exceptions occurred while deleting a bucket policy, if any.
        :param bucket_name: s3 bucket
        :param s3_obj_one: s3 test object of account one
        :param ACL_OBJ_one: s3 acl test lib object of account one
        :param S3_BKT_POLICY_OBJ_one: s3 bucket policy class object of account 1
        :param S3_BKT_POLICY_OBJ_two: s3 bucket policy class object of account 2
        :param test_config: test-case yaml config values
        :return: None
        """
        LOGGER.info("Retrieving bucket acl attributes")
        resp = ACL_OBJ_one.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Bucket ACL was verified")
        LOGGER.info("Apply put bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_config["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ_one.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Bucket policy was applied on the bucket")
        LOGGER.info(
            "Verify the bucket policy from Bucket owner account")
        resp = S3_BKT_POLICY_OBJ_one.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Bucket policy was verified")
        LOGGER.info(
            "Login to account2 and delete bucket policy for the bucket "
            "which is present in account1")
        try:
            S3_BKT_POLICY_OBJ_two.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert test_config["error_message"] in error.message, error.message
        resp = ACL_OBJ_one.put_bucket_acl(
            bucket_name, acl=BKT_POLICY_CONF["bucket_policy"]["acl_permission"])
        assert resp[0], resp[1]
        resp = s3_obj_one.delete_bucket(bucket_name, force=True)
        assert resp[0], resp[1]
        LOGGER.info(
            "Delete bucket policy should through error message %s",
                test_config["error_message"])

    def create_bucket_put_obj_with_dir(
            self,
            bucket_name: str,
            obj_name_1: str,
            obj_name_2: str) -> None:
        """
        This function will create a bucket and upload objects from a directory to a bucket.

        :param bucket_name: Name of bucket to be created
        :param obj_name_1: Name of an object to be put to the bucket
        :param obj_name_2: Name of an object from a dir which is getting uploaded
        :return: None
        """
        LOGGER.info("Creating a bucket with name %s", bucket_name)
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info("Bucket is created with name %s", bucket_name)
        LOGGER.info(
            "Uploading an object %s to a bucket %s", obj_name_1, bucket_name)
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        resp = S3_OBJ.put_object(
            bucket_name,
            obj_name_1,
            BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("An object is uploaded to a bucket")
        LOGGER.info(
            "Uploading an object %s from a dir to a bucket %s", obj_name_2, bucket_name)
        if os.path.exists(BKT_POLICY_CONF["bucket_policy"]["folder_path"]):
            shutil.rmtree(BKT_POLICY_CONF["bucket_policy"]["folder_path"])
        os.mkdir(BKT_POLICY_CONF["bucket_policy"]["folder_path"])
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path_2"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        resp = S3_OBJ.put_object(
            bucket_name,
            obj_name_2,
            BKT_POLICY_CONF["bucket_policy"]["file_path_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Uploaded an object %s from a dir to a bucket %s",
            obj_name_2, bucket_name)

    def create_bucket_validate(self, bucket_name: str) -> None:
        """
        Create a new bucket and validate it

        :param bucket_name: Name of bucket to be created
        :return: None
        """
        LOGGER.info("Step 1 : Creating a bucket with name %s", bucket_name)
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info("Step 1 : Bucket is created with name %s", bucket_name)

    def put_bucket_policy_with_err(
            self,
            bucket_name: str,
            test_bckt_cfg: dict,
            S3_BKT_POLICY_OBJ_2: object) -> None:
        """
        This method will apply bucket policy on the specified bucket.
        It will also handle exceptions occurred while updating bucket policy, if any.

        :param  bucket_name: Name of the s3 bucket
        :param  test_bckt_cfg: test-case yaml config values
        :param  S3_BKT_POLICY_OBJ_2: s3 acl test bucket policy of account two
        :return: None
        """
        LOGGER.info("Getting the bucket acl")
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1][1][0]["Permission"],
                         test_bckt_cfg["bucket_permission"], resp[1])
        LOGGER.info("Bucket ACL was verified successfully")
        LOGGER.info(
            "Apply put bucket policy on the bucket using account second account")
        bkt_json_policy = json.dumps(test_bckt_cfg["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ_2.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_bckt_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Put Bucket policy from second account will result into"
            "failure with error : %s", test_bckt_cfg["error_message"])
        resp = ACL_OBJ.put_bucket_acl(
            bucket_name, acl=BKT_POLICY_CONF["bucket_policy"]["acl_permission"])
        assert resp[0], resp[1]

    def put_get_bkt_policy(self, bucket_name: str, bucket_policy: str) -> None:
        """
        This method applies bucket policy to an bucket and retrieves the policy of a same bucket

        :param  bucket_name: The name of the bucket
        :param  bucket_policy: The bucket policy as a JSON document
        :return: None
        """
        LOGGER.info("Applying policy to a bucket %s", bucket_name)
        bkt_policy_json = json.dumps(bucket_policy)
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        LOGGER.info("Policy is applied to a bucket %s", bucket_name)
        LOGGER.info("Retrieving policy of a bucket %s", bucket_name)
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.debug(resp[1]["Policy"])
        ASRTOBJ.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        LOGGER.info("Retrieved policy of a bucket %s", bucket_name)

    def put_invalid_policy(
    self,
    bucket_name: str,
    bucket_policy: str,
     msg: str) -> None:
        """
        This method applies invalid policy on a bucket and validate the expected error

        :param bucket_name: Name of the bucket to be created
        :param bucket_policy: The bucket policy as a JSON document
        :param msg: Error message to be validate
        :return: None
        """
        LOGGER.info("Applying invalid policy on a bucket %s", bucket_name)
        bkt_json_policy = json.dumps(bucket_policy)
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name,
                                                bkt_json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert msg in error.message, error.message
            LOGGER.info(
                "Applying invalid policy on a bucket is failed with error %s",
                    error.message)

    def put_bkt_policy_with_date_format(self, account_id: str, date_time: str,
                                        effect: str, s3_test_ob: object, test_config: dict):
        """
        This method will set the bucket policy using date format condition and retrieves
        the policy of a bucket and validates it.
        It will also upload an object to a bucket using another account and handle exceptions
        occurred while uploading.

        :param  account_id: account-id of the second account
        :param  date_time: datetime for date condition
        :param  effect: Policy element "Effect" either (Allow/Deny)
        :param  s3_test_ob: s3 test class object of another account
        :param  test_config: test-case yaml config values
        :return: None
        """
        bkt_json_policy = eval(json.dumps(test_config["bucket_policy"]))
        dt_condition = bkt_json_policy["Statement"][0]["Condition"]
        condition_key = list(
            dt_condition[test_config["date_condition"]].keys())[0]
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        bkt_json_policy["Statement"][0]["Condition"][test_config["date_condition"]
                                                     ][condition_key] = date_time
        bkt_json_policy["Statement"][0]["Effect"] = effect
        bucket_name = "{}{}".format(test_config["bucket_name"], effect.lower())
        bkt_json_policy["Statement"][0]["Resource"] = \
            bkt_json_policy["Statement"][0]["Resource"].format(bucket_name)
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.put_get_bkt_policy(bucket_name, bkt_json_policy)
        LOGGER.info("Uploading object to s3 bucket with second account")
        try:
            s3_test_ob.put_object(
                bucket_name,
                test_config["object_name"],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_config["error_message"] in error.message, error.message
            LOGGER.info(
                "Uploading object to bucket with second account failed with error %s",
                    error.message)

    def list_obj_with_max_keys_and_diff_acnt(
            self,
            bucket_name: str,
            S3_OBJ: object,
            max_keys: int,
            err_message: str = None) -> None:
        """
        This function will list objects of a specified bucket with specified max keys using
        given s3 test object.

        It will also handle an exception occurred during list object operation.
        :param  bucket_name: Name of a bucket
        :param  S3_OBJ: s3 test class object of other IAM account
        :param  max_keys: Maximum no of keys to be listed
        :param  err_message: An error message returned on ListObject operation failure
        :return: None
        """
        LOGGER.info(
            "Listing objects of a bucket %s with %d max keys and specified account",
                bucket_name, max_keys)
        if err_message:
            try:
                S3_OBJ.list_objects_with_prefix(
                    bucket_name, maxkeys=max_keys)
            except CTException as error:
                LOGGER.error(error.message)
                assert err_message in error.message, error.message
                LOGGER.info(
                    "Listing objects with %d max keys and specified account is failed with error %s",
                        max_keys, err_message)
        else:
            resp = S3_OBJ.list_objects_with_prefix(
                bucket_name, maxkeys=max_keys)
            assert resp[0], resp[1]
            LOGGER.info(
                "Listed objects with %d max keys and specified account successfully", max_keys)

    def list_objects_with_diff_acnt(
            self,
            bucket_name: str,
            S3_OBJ: object,
            err_message : str=None) -> None:
        """
        This function will list objects of specified bucket using specified s3
        test class object

        It will also handle an exception occurred during list object operation.
        :param bucket_name: Name of bucket
        :param S3_OBJ: s3 test class object of other IAM account
        :param: err_message: An error message returned on ListObject operation failure
        :return: None
        """
        LOGGER.info("Listing an objects of bucket %s", bucket_name)
        if err_message:
            try:
                S3_OBJ.object_list(bucket_name)
            except CTException as error:
                LOGGER.error(error.message)
                assert err_message in error.message, error.message
                LOGGER.info(
                    "Listing an objects of bucket %s failed with %s",
                        bucket_name, err_message)
        else:
            resp = S3_OBJ.object_list(bucket_name)
            assert resp[0], resp[1]
            LOGGER.info("Listed objects of bucket %s successfully",
                        bucket_name)

    def put_object_with_acl_cross_acnt(
            self,
            bucket_name: str,
            S3_OBJ: object,
            obj_name: str,
            acl : str =None,
            grant_full_control : str =None,
            grant_read : str =None,
            grant_read_acp : str =None,
            grant_write_acp : str =None,
            err_message : str =None) -> None:
        """
        This function will put object to specified bucket using specified s3
        test class object with acl, if given.

        It will also handle an exception occurred during put object operation.
        :param bucket_name: Name of bucket
        :param S3_OBJ: s3 test class object of other IAM account
        :param obj_name: name for an object
        :param acl: acl permission to set while putting an obj
        :param grant_full_control: To set a grant full control permission for given object.
        :param grant_read: To set a grant read permission for given object.
        :param grant_read_acp: To set a grant read ACP permission for given object.
        :param grant_write_acp: To set a grant write ACP permission for given object.
        :param err_message: An error message returned on PutObject operation failure
        :return: None
        """
        LOGGER.info("Put an object to bucket %s", bucket_name)
        if os.path.exists(BKT_POLICY_CONF["bucket_policy"]["folder_path"]):
            shutil.rmtree(BKT_POLICY_CONF["bucket_policy"]["folder_path"])
        os.mkdir(BKT_POLICY_CONF["bucket_policy"]["folder_path"])
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path_2"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        if err_message:
            try:
                if acl or grant_read or grant_full_control or grant_read_acp or grant_write_acp:
                    S3_OBJ.put_object_with_acl(
                        bucket_name=bucket_name,
                        key=obj_name,
                        file_path=BKT_POLICY_CONF["bucket_policy"]["file_path_2"],
                        acl=acl,
                        grant_full_control=grant_full_control,
                        grant_read=grant_read,
                        grant_read_acp=grant_read_acp,
                        grant_write_acp=grant_write_acp)
                else:
                    S3_OBJ.put_object(
                        bucket_name,
                        obj_name,
                        BKT_POLICY_CONF["bucket_policy"]["file_path_2"])
            except CTException as error:
                LOGGER.error(error.message)
                assert err_message in error.message, error.message
                LOGGER.info(
                    "Putting an object into bucket %s failed with %s",
                        bucket_name, err_message)
        else:
            if acl or grant_read or grant_full_control or grant_read_acp or grant_write_acp:
                resp = S3_OBJ.put_object_with_acl(
                    bucket_name=bucket_name,
                    key=obj_name,
                    file_path=BKT_POLICY_CONF["bucket_policy"]["file_path_2"],
                    acl=acl,
                    grant_full_control=grant_full_control,
                    grant_read=grant_read,
                    grant_read_acp=grant_read_acp,
                    grant_write_acp=grant_write_acp)
            else:
                resp = S3_OBJ.put_object(
                    bucket_name, obj_name, BKT_POLICY_CONF["bucket_policy"]["file_path_2"])
            assert resp[0], resp[1]
            LOGGER.info("Put object into bucket %s successfully", bucket_name)

    def list_obj_with_prefix_using_diff_accnt(
            self,
            bucket_name: str,
            S3_OBJ: object,
            obj_name_prefix: str,
            err_message : str =None) -> None:
        """
        This function will list objects with given prefix, of specified bucket
        It will also handle an exception occurred during list object operation.
        :param str bucket_name: Name of a bucket
        :param object S3_OBJ: s3 test class object of other IAM account
        :param str obj_name_prefix: Object Name prefix
        :param str err_message: An error message returned on ListObject operation failure
        :return: None
        """
        LOGGER.info(
            "Listing objects of a bucket %s with %s prefix",
                bucket_name, obj_name_prefix)
        if err_message:
            try:
                S3_OBJ.list_objects_with_prefix(
                    bucket_name, prefix=obj_name_prefix)
            except CTException as error:
                LOGGER.error(error.message)
                assert err_message in error.message, error.message
                LOGGER.info(
                    "Listing objects with %s prefix from another account is failed with error %s",
                        obj_name_prefix, err_message)
        else:
            resp = S3_OBJ.list_objects_with_prefix(
                bucket_name, prefix=obj_name_prefix)
            assert resp[0], resp[1]
            LOGGER.info(
                "Listed objects with %s prefix successfully", obj_name_prefix)

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6102")
    @CTFailOn(error_handler)
    def test_254(self):
        """
        create bucket and get-bucket-policy for that bucket
        """
        LOGGER.info(
            "STARTED: create bucket and get-bucket-policy for that bucket")
        self.create_bucket_validate(BKT_POLICY_CONF["test_254"]["bucket_name"])
        LOGGER.info(
            "Step 2 : Retrieving policy of a bucket {0}".format(
                BKT_POLICY_CONF["test_254"]["bucket_name"]))
        try:
            S3_BKT_POLICY_OBJ.get_bucket_policy(
                BKT_POLICY_CONF["test_254"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert BKT_POLICY_CONF["test_254"]["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2 : Retrieving policy of a bucket {0} is failed".format(
                BKT_POLICY_CONF["test_254"]["bucket_name"]))
        LOGGER.info(
            "ENDED: create bucket and get-bucket-policy for that bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6101")
    @CTFailOn(error_handler)
    def test_260(self):
        """
        verify get-bucket-policy for the bucket which is not present
        """
        LOGGER.info(
            "STARTED: verify get-bucket-policy for the bucket which is not present")
        LOGGER.info(
            "Step 1 : Retrieving policy of non existing bucket")
        try:
            S3_BKT_POLICY_OBJ.get_bucket_policy(
                BKT_POLICY_CONF["test_260"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert BKT_POLICY_CONF["test_260"]["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 1 : Retrieving policy of a bucket {0} is failed".format(
                BKT_POLICY_CONF["test_254"]["bucket_name"]))
        LOGGER.info(
            "ENDED: verify get-bucket-policy for the bucket which is not present")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6100")
    @CTFailOn(error_handler)
    def test_261(self):
        """
        check get-bucket-policy for the bucket which is having policy for that bucket
        """
        LOGGER.info(
            "STARTED: check get-bucket-policy for the "
            "bucket which is having policy for that bucket")
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(
                BKT_POLICY_CONF["test_261"]["bucket_name"]))
        resp = S3_OBJ.create_bucket(
            BKT_POLICY_CONF["test_261"]["bucket_name"])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1],
                              BKT_POLICY_CONF["test_261"]["bucket_name"],
                              resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(
                BKT_POLICY_CONF["test_261"]["bucket_name"]))
        bucket_policy = BKT_POLICY_CONF["test_261"]["bucket_policy"]
        bkt_json_policy = json.dumps(bucket_policy)
        LOGGER.info(
            "Step 2 : Performing put bucket policy on bucket {0}".format(
                BKT_POLICY_CONF["test_261"]["bucket_name"]))
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            BKT_POLICY_CONF["test_261"]["bucket_name"], bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2 : Performed put bucket policy operation on bucket {0}".format(
                BKT_POLICY_CONF["test_261"]["bucket_name"]))
        LOGGER.info(
            "Step 3 : Retrieving policy of a bucket {0}".format(
                BKT_POLICY_CONF["test_261"]["bucket_name"]))
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(
            BKT_POLICY_CONF["test_261"]["bucket_name"])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["Policy"], bkt_json_policy, resp[1])
        LOGGER.info(
            "Step 3 : Retrieved policy of a bucket {0}".format(
                BKT_POLICY_CONF["test_261"]["bucket_name"]))
        LOGGER.info(
            "ENDED: check get-bucket-policy for the bucket which is having policy for that bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6099")
    @CTFailOn(error_handler)
    def test_262(self):
        """
        verify get-bucket-policy for the bucket from account2.Do not apply
        any ACL permissions or canned ACL to account2 and verify get-bucket-policy
        """
        LOGGER.info(
            "STARTED: verify get-bucket-policy for the bucket from account2."
            "Do not apply any ACL permissions or "
            "canned ACL to account2 and verify get-bucket-policy")
        LOGGER.info(
            "Step 1 : Creating a  bucket with name {0}".format(
                BKT_POLICY_CONF["test_262"]["bucket_name"]))
        resp = S3_OBJ.create_bucket(
            BKT_POLICY_CONF["test_262"]["bucket_name"])
        ASRTOBJ.assert_equals(
            resp[1],
            BKT_POLICY_CONF["test_262"]["bucket_name"],
            resp[1])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Created a bucket with name {0}".format(
                BKT_POLICY_CONF["test_262"]["bucket_name"]))
        bucket_policy = BKT_POLICY_CONF["test_262"]["bucket_policy"]
        bkt_json_policy = json.dumps(bucket_policy)
        LOGGER.info(
            "Step 2 : Performing put bucket policy on  bucket {0}".format(
                BKT_POLICY_CONF["test_262"]["bucket_name"]))
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            BKT_POLICY_CONF["test_262"]["bucket_name"], bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2 : Performed put bucket policy operation on bucket {0}".format(
                BKT_POLICY_CONF["test_262"]["bucket_name"]))
        LOGGER.info(
            "Step 3 : Login to another account to perform get bucket policy")
        account_name = "{}{}".format(
            BKT_POLICY_CONF["test_262"]["account_name"], str(
                time.time()))
        email_id = "{}{}".format(account_name,
                                 BKT_POLICY_CONF["test_262"]["email_id"])
        LOGGER.info(
            "Creating another account with name {0} and email {1}".format(
                account_name,
                email_id))
        resp = IAM_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_obj_2 = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key,
            secret_key=secret_key)
        LOGGER.info(
            "Getting bucket policy using another account {0}".format(
                account_name))
        try:
            s3_obj_2.get_bucket_policy(
                BKT_POLICY_CONF["test_262"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert BKT_POLICY_CONF["test_262"]["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 3 : Get bucket policy with another account is failed")
        # Cleanup activity
        LOGGER.info("Deleting an account {0}".format(
            account_name))
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key, force=True)
        assert resp[0], resp[1]
        LOGGER.info("Account {0} is deleted".format(
            account_name))
        LOGGER.info(
            "ENDED: verify get-bucket-policy for the bucket from account2."
            "Do not apply any ACL permissions or "
            "canned ACL to account2 and verify get-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6079")
    @CTFailOn(error_handler)
    def test_642(self):
        """
        Test resource arn combination with bucket name and all objects."""
        LOGGER.info(
            "STARTED: Test resource arn combination with bucket name and all objects.")
        bkt_cnf_642 = BKT_POLICY_CONF["test_642"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_642["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_642["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_642["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving objects from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.get_object(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        resp = s3_obj.get_object(bucket_name, bkt_cnf_642["object_name_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved objects from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        LOGGER.info(
            "ENDED: Test resource arn combination with bucket name and all objects.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6077")
    @CTFailOn(error_handler)
    def test_644(self):
        """
        Test resource arn combination with bucket name and no object name"""
        LOGGER.info(
            "STARTED: Test resource arn combination with bucket name and all objects.")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_644"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_644"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_644"]["bucket_name"],
                                BKT_POLICY_CONF["test_644"]["bucket_policy"],
                                BKT_POLICY_CONF["test_644"]["error_message"])
        LOGGER.info(
            "ENDED: Test resource arn combination with bucket name and all objects.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6075")
    @CTFailOn(error_handler)
    def test_646(self):
        """
        Test resource arn combination without mentioning bucket name"""
        LOGGER.info(
            "STARTED: Test resource arn combination without mentioning bucket name")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_646"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_646"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_646"]["bucket_name"],
                                BKT_POLICY_CONF["test_646"]["bucket_policy"],
                                BKT_POLICY_CONF["test_646"]["error_message"])
        LOGGER.info(
            "ENDED: Test resource arn combination without mentioning bucket name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6073")
    @CTFailOn(error_handler)
    def test_658(self):
        """
        Test resource arn combination with not present bucket name"""
        LOGGER.info(
            "STARTED: Test resource arn combination with not present bucket name")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_658"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_658"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_658"]["bucket_name"],
                                BKT_POLICY_CONF["test_658"]["bucket_policy"],
                                BKT_POLICY_CONF["test_658"]["error_message"])
        LOGGER.info(
            "ENDED: Test resource arn combination with not present bucket name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6071")
    @CTFailOn(error_handler)
    def test_659(self):
        """
        Test resource arn combination with object name"""
        LOGGER.info(
            "STARTED: Test resource arn combination with object name")
        bkt_cnf_659 = BKT_POLICY_CONF["test_659"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_659["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_659["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_659["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.get_object(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        LOGGER.info(
            "ENDED: Test resource arn combination with object name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6069")
    @CTFailOn(error_handler)
    def test_679(self):
        """
        Test resource arn combination with object name inside folder"""
        LOGGER.info(
            "STARTED: Test resource arn combination with object name inside folder")
        bkt_cnf_679 = BKT_POLICY_CONF["test_679"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_679["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_679["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_679["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.get_object(bucket_name, bkt_cnf_679["object_name_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        LOGGER.info(
            "ENDED: Test resource arn combination with object name inside folder")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6067")
    @CTFailOn(error_handler)
    def test_680(self):
        """
        Test resource arn combination mentioning IAM details"""
        LOGGER.info(
            "STARTED: Test resource arn combination mentioning IAM details")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_680"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_680"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_680"]["bucket_name"],
                                BKT_POLICY_CONF["test_680"]["bucket_policy"],
                                BKT_POLICY_CONF["test_680"]["error_message"])
        LOGGER.info(
            "ENDED: Test resource arn combination mentioning IAM details")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6065")
    @CTFailOn(error_handler)
    def test_682(self):
        """
        Test resource arn combination with missing required component/value as per arn format"""
        LOGGER.info(
            "STARTED: Test resource arn combination "
            "with missing required component/value as per arn format")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_682"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_682"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_682"]["bucket_name"],
                                BKT_POLICY_CONF["test_682"]["bucket_policy"],
                                BKT_POLICY_CONF["test_682"]["error_message"])
        LOGGER.info(
            "ENDED: Test resource arn combination with "
            "missing required component/value as per arn format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6063")
    @CTFailOn(error_handler)
    def test_688(self):
        """
        Test resource arn combination with multiple arns"""
        LOGGER.info(
            "STARTED: Test resource arn combination with multiple arns")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_688"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_688"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_688"]["bucket_name"],
                                BKT_POLICY_CONF["test_688"]["bucket_policy"],
                                BKT_POLICY_CONF["test_688"]["error_message"])
        LOGGER.info(
            "ENDED: Test resource arn combination with multiple arns")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6061")
    @CTFailOn(error_handler)
    def test_689(self):
        """
        Test resource arn combination with wildcard * for bucket"""
        LOGGER.info(
            "STARTED: Test resource arn combination with wildcard * for bucket")
        self.create_bucket_put_obj_with_dir(
            BKT_POLICY_CONF["test_689"]["bucket_name"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            BKT_POLICY_CONF["test_689"]["object_name_2"])
        self.put_invalid_policy(BKT_POLICY_CONF["test_689"]["bucket_name"],
                                BKT_POLICY_CONF["test_689"]["bucket_policy"],
                                BKT_POLICY_CONF["test_689"]["error_message"])
        LOGGER.info("Put bucket policy on a bucket is failed")
        LOGGER.info(
            "ENDED: Test resource arn combination with wildcard * for bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6059")
    @CTFailOn(error_handler)
    def test_690(self):
        """
        Test resource arn specifying wildcard * for specifying part of object name"""
        LOGGER.info(
            "STARTED: Test resource arn specifying wildcard * for specifying part of object name")
        bkt_cnf_690 = BKT_POLICY_CONF["test_690"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_690["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_690["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_690["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.get_object(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        LOGGER.info(
            "ENDED: Test resource arn specifying wildcard * for specifying part of object name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6005")
    @CTFailOn(error_handler)
    def test_1300(self):
        """
        Create Bucket Policy using NumericLessThan Condition Operator

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThan Condition Operator")
        test_1300_cfg = BKT_POLICY_CONF["test_1300"]
        bucket_name = test_1300_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_1300_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        LOGGER.info(
            "Step 1 : Create a json for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        bkt_json_policy = json.dumps(
            BKT_POLICY_CONF["test_1300"]["bucket_policy"])
        LOGGER.info(
            "Step 1 : Created a json for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        LOGGER.info(
            "Step 2: Apply the bucket policy on the bucket and check the output")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy on the bucket was applied")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_1300_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThan Condition Operator")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6003")
    @CTFailOn(error_handler)
    def test_1303(self):
        """
        Create Bucket Policy using NumericLessThanEquals Condition Operator

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThanEquals Condition Operator")
        test_1303_cfg = BKT_POLICY_CONF["test_1303"]
        bucket_name = test_1303_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_1303_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        LOGGER.info(
            "Step 1 : Create a json for bucket policy specifying using "
            "NumericLessThanEquals Condition Operator")
        bkt_json_policy = json.dumps(
            BKT_POLICY_CONF["test_1303"]["bucket_policy"])
        LOGGER.info(
            "Step 1 : Created a json for bucket policy specifying using "
            "NumericLessThanEquals Condition Operator")
        LOGGER.info(
            "Step 2: Apply the bucket policy on the bucket and check the output")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy on the bucket was applied")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_1303_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThanEquals Condition Operator")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6000")
    @CTFailOn(error_handler)
    def test_1307(self):
        """
        Create Bucket Policy using NumericGreaterThan Condition Operator

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThan Condition Operator")
        test_1307_cfg = BKT_POLICY_CONF["test_1307"]
        bucket_name = test_1307_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_1307_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        LOGGER.info(
            "Step 1: Create a json for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        bkt_json_policy = json.dumps(test_1307_cfg["bucket_policy"])
        LOGGER.info(
            "Step 1: Created a json for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        LOGGER.info(
            "Step 2: Apply the bucket policy on the bucket and check the output")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
    bucket_policy[0],
     test_1307_cfg["buc_policy_val"])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThan Condition Operator")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5998")
    @CTFailOn(error_handler)
    def test_1308(self):
        """
        Create Bucket Policy using NumericGreaterThanEquals Condition Operator

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")
        test_1308_cfg = BKT_POLICY_CONF["test_1308"]
        bucket_name = test_1308_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_1308_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        LOGGER.info("Step 1: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_1308_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Bucket policy was applied successfully")
        LOGGER.info("Step 2: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(bucket_policy[0],
                              test_1308_cfg["buc_policy_val"],
                              resp[1])
        LOGGER.info("Step 2: Bucket policy was verified successfully")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6010")
    @CTFailOn(error_handler)
    def test_1294(self):
        """
        Create Bucket Policy using StringNotEquals Condition Operator and Allow Action_string
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringEquals Condition Operator and Allow Action")
        test_1294_cfg = BKT_POLICY_CONF["test_1294"]
        bucket_name = test_1294_cfg["bucket_name"]
        object_lst = []
        self.create_bucket_put_objects(
            bucket_name,
            test_1294_cfg["obj_count"],
            test_1294_cfg["object_prefix"],
            object_lst)
        LOGGER.info("Step 1: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_1294_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Bucket policy was applied successfully")
        LOGGER.info("Step 2: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])
                             ["Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_1294_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 2: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 3: Verify the Bucket Policy with prefix and from Bucket owner account")
        resp = S3_OBJ.list_objects_with_prefix(
            bucket_name, test_1294_cfg["prefix"])
        prefix_obj_lst = list(resp[1])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
    prefix_obj_lst.sort(),
    object_lst.sort(),
     resp[1])
        LOGGER.info("Step 3: Verified the Bucket Policy with prefix")
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringEquals Condition Operator and Allow Action")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6007")
    @CTFailOn(error_handler)
    def test_1296(self):
        """
        Create Bucket Policy using NumericGreaterThanEquals Condition Operator_string
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")
        test_1296_cfg = BKT_POLICY_CONF["test_1294"]
        bucket_name = test_1296_cfg["bucket_name"]
        object_lst = []
        self.create_bucket_put_objects(
            bucket_name,
            test_1296_cfg["obj_count"],
            test_1296_cfg["object_prefix"],
            object_lst)
        LOGGER.info("Step 1: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_1296_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Bucket policy was applied successfully")
        LOGGER.info("Step 2: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])
                             ["Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_1296_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 2: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 3: Verify the Bucket Policy with prefix and from Bucket owner account")
        resp = S3_OBJ.list_objects_with_prefix(
            bucket_name, test_1296_cfg["prefix"])
        prefix_obj_lst = list(resp[1])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
    prefix_obj_lst.sort(),
    object_lst.sort(),
     resp[1])
        LOGGER.info("Step 3: Verified the Bucket Policy with prefix")
        LOGGER.info(
            "Step 4: Verify the Bucket Policy without prefix from Bucket owner")
        resp = S3_OBJ.object_list(bucket_name)
        prefix_obj_lst = list(resp[1])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
    prefix_obj_lst.sort(),
    object_lst.sort(),
     resp[1])
        LOGGER.info("Step 4: Verified the Bucket Policy without prefix")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6098")
    @CTFailOn(error_handler)
    def test_558(self):
        """
        Apply Delete-bucket-policy on existing bucket
        """
        LOGGER.info("STARTED: Apply Delete-bucket-policy on existing bucket")
        test_558_cfg = BKT_POLICY_CONF["test_558"]
        bucket_name = test_558_cfg["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_558_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info("Step 4: Delete bucket policy")
        resp = S3_BKT_POLICY_OBJ.delete_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Bucket policy was deleted successfully")
        try:
            S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        except CTException as error:
            assert test_558_cfg["error_message"] in error.message, error.message
        LOGGER.info("ENDED: Apply Delete-bucket-policy on existing bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6097")
    @CTFailOn(error_handler)
    def test_560(self):
        """
        Apply Delete-bucket-policy on non existing bucket
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy on non existing bucket")
        bucket_name = BKT_POLICY_CONF["test_560"]["bucket_name"]
        err_msg = BKT_POLICY_CONF["test_560"]["error_message"]
        LOGGER.info(
            "Step 1: Delete bucket policy for the bucket which is not there")
        try:
            S3_BKT_POLICY_OBJ.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert err_msg in error.message, error.message
        LOGGER.info(
            "Step 1: Delete bucket policy should through error message {}".format(err_msg))
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy on non existing bucket.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6096")
    @CTFailOn(error_handler)
    def test_562(self):
        """
        Apply Delete-bucket-policy without specifying bucket name
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy without specifying bucket name")
        test_562_cfg = BKT_POLICY_CONF["test_562"]
        bucket_name = test_562_cfg["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_562_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Delete bucket policy without giving any bucket name")
        try:
            bucket_name = None
            S3_BKT_POLICY_OBJ.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert test_562_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 4: Deleting the bucket without bucket "
            "name was handled with error message {}".format(
                test_562_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy without specifying bucket name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6095")
    @CTFailOn(error_handler)
    def test_563(self):
        """
        Apply Delete-bucket-policy without specifying policy.
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy without specifying policy.")
        bucket_name = BKT_POLICY_CONF["test_563"]["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info("Step 2: List all the bucket")
        resp = S3_OBJ.bucket_list()
        assert resp[0], resp[1]
        LOGGER.info("Step 2: All the bucket listed")
        LOGGER.info("Step 3: Delete bucket policy")
        try:
            S3_BKT_POLICY_OBJ.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert bkt_POLICY_CONF["test_563"]["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Delete bucket policy should through error message {}".format(
                BKT_POLICY_CONF["test_563"]["error_message"]))
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy without specifying policy.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6093 ")
    @CTFailOn(error_handler)
    def test_566(self):
        """
        Apply Delete-bucket-policy from another account given read permission on bucket
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy from another account given read permission on bucket")
        random_id = str(time.time())
        test_566_cfg = BKT_POLICY_CONF["test_566"]
        bucket_name = test_566_cfg["bucket_name"]
        account_name_1 = test_566_cfg["account_name_1"].format(random_id)
        email_id_1 = test_566_cfg["emailid_1"].format(random_id)
        result_1 = self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1 = result_1[0]
        ACL_OBJ_1 = result_1[2]
        S3_BKT_POLICY_OBJ_1 = result_1[3]
        account_name_2 = test_566_cfg["account_name_2"].format(random_id)
        email_id_2 = test_566_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        canonical_id_user_2 = result_2[0]
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info(
            "Step 1 : Create a new bucket and give grant_read permissions to account 2")
        resp = ACL_OBJ_1.create_bucket_with_acl(
            bucket_name=bucket_name,
            grant_full_control=test_566_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read=test_566_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with grant_read permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            bucket_name,
            result_1[1],
            ACL_OBJ_1,
            S3_BKT_POLICY_OBJ_1,
            S3_BKT_POLICY_OBJ_2,
            test_566_cfg)
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from another account given read permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6091")
    @CTFailOn(error_handler)
    def test_569(self):
        """
        Apply Delete-bucket-policy from another account given write permission on bucket
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy from another account given write permission on bucket")
        random_id = str(time.time())
        test_569_cfg = BKT_POLICY_CONF["test_569"]
        bucket_name = test_569_cfg["bucket_name"]
        account_name_1 = test_569_cfg["account_name_1"].format(random_id)
        email_id_1 = test_569_cfg["emailid_1"].format(random_id)
        result_1 = self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1 = result_1[0]
        S3_BKT_POLICY_OBJ_1 = result_1[3]
        ACL_OBJ_1 = result_1[2]
        account_name_2 = test_569_cfg["account_name_2"].format(random_id)
        email_id_2 = test_569_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        canonical_id_user_2 = result_2[0]
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info(
            "Step 1 : Create a new bucket and give write permissions to account 2")
        resp = ACL_OBJ_1.create_bucket_with_acl(
            bucket_name=bucket_name,
            grant_full_control=test_569_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write=test_569_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with write permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            bucket_name,
            result_1[1],
            ACL_OBJ_1,
            S3_BKT_POLICY_OBJ_1,
            S3_BKT_POLICY_OBJ_2,
            test_569_cfg)
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from another account given write permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6089")
    @CTFailOn(error_handler)
    def test_570(self):
        """
        Apply Delete-bucket-policy from another account given read-acp permission on bucket
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy from another account given read-acp permission on bucket")
        random_id = str(time.time())
        test_570_cfg = BKT_POLICY_CONF["test_570"]
        bucket_name = test_570_cfg["bucket_name"]
        account_name_1 = test_570_cfg["account_name_1"].format(random_id)
        email_id_1 = test_570_cfg["emailid_1"].format(random_id)
        result_1 = self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1 = result_1[0]
        S3_BKT_POLICY_OBJ_1 = result_1[3]
        ACL_OBJ_1 = result_1[2]
        account_name_2 = test_570_cfg["account_name_2"].format(random_id)
        email_id_2 = test_570_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        canonical_id_user_2 = result_2[0]
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info(
            "Step 1 : Create a new bucket and give write-acp permissions to account 2")
        resp = ACL_OBJ_1.create_bucket_with_acl(
            bucket_name=bucket_name,
            grant_full_control=test_570_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read_acp=test_570_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with write-acp permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            bucket_name,
            result_1[1],
            ACL_OBJ_1,
            S3_BKT_POLICY_OBJ_1,
            S3_BKT_POLICY_OBJ_2,
            test_570_cfg)
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from another account given read-acp permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6087")
    @CTFailOn(error_handler)
    def test_574(self):
        """
        Apply Delete-bucket-policy from another account given write-acp permission on bucket
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy from another account given write-acp permission on bucket")
        random_id = str(time.time())
        test_574_cfg = BKT_POLICY_CONF["test_574"]
        bucket_name = test_574_cfg["bucket_name"]
        account_name_1 = test_574_cfg["account_name_1"].format(random_id)
        email_id_1 = test_574_cfg["emailid_1"].format(random_id)
        result_1 = self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1 = result_1[0]
        S3_BKT_POLICY_OBJ_1 = result_1[3]
        ACL_OBJ_1 = result_1[2]
        account_name_2 = test_574_cfg["account_name_2"].format(random_id)
        email_id_2 = test_574_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        canonical_id_user_2 = result_2[0]
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info(
            "Step 1 : Create a new bucket and give write-acp permissions to account 2")
        resp = ACL_OBJ_1.create_bucket_with_acl(
            bucket_name=bucket_name,
            grant_full_control=test_574_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write_acp=test_574_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with write-acp permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            bucket_name,
            result_1[1],
            ACL_OBJ_1,
            S3_BKT_POLICY_OBJ_1,
            S3_BKT_POLICY_OBJ_2,
            test_574_cfg)
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from "
            "another account given write-acp permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6085")
    @CTFailOn(error_handler)
    def test_582(self):
        """
        Test Apply Delete-bucket-policy from another account given full-control permission on bucket.
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy "
            "from another account given full-control permission on bucket")
        random_id = str(time.time())
        test_582_cfg = BKT_POLICY_CONF["test_582"]
        bucket_name = test_582_cfg["bucket_name"]
        account_name_1 = test_582_cfg["account_name_1"].format(random_id)
        email_id_1 = test_582_cfg["emailid_1"].format(random_id)
        result_1 = self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1 = result_1[0]
        S3_BKT_POLICY_OBJ_1 = result_1[3]
        ACL_OBJ_1 = result_1[2]
        account_name_2 = test_582_cfg["account_name_2"].format(random_id)
        email_id_2 = test_582_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        canonical_id_user_2 = result_2[0]
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info(
            "Step 1 : Create a new bucket and give full-control permissions to account 2")
        resp = ACL_OBJ_1.create_bucket_with_acl(
            bucket_name=bucket_name,
            grant_full_control=test_582_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        resp = ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_full_control=test_582_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with full-control permission to the account 2")
        self.delete_bucket_policy_with_err_msg(
            bucket_name,
            result_1[1],
            ACL_OBJ_1,
            S3_BKT_POLICY_OBJ_1,
            S3_BKT_POLICY_OBJ_2,
            test_582_cfg)
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from "
            "another account given full-control permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6083")
    @CTFailOn(error_handler)
    def test_583(self):
        """
        Apply Delete-bucket-policy from another account with no permissions
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy from another account with no permissions")
        random_id = str(time.time())
        test_583_cfg = BKT_POLICY_CONF["test_583"]
        bucket_name = test_583_cfg["bucket_name"]
        account_name_2 = test_583_cfg["account_name_2"].format(random_id)
        email_id_2 = test_583_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info("Step 1 : Create a new bucket")
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created")
        LOGGER.info("Step 2: Get bucket acl")
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket ACL was verified")
        LOGGER.info("Step 3: Apply put bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_583_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Bucket policy was applied on the bucket")
        LOGGER.info(
            "Step 4: Verify the bucket policy from Bucket owner account")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Bucket policy was verified")
        LOGGER.info(
            "Step 5: Login to account2 and delete bucket policy for the bucket "
            "which is present in account1")
        try:
            S3_BKT_POLICY_OBJ_2.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert test_583_cfg["error_message"] in error.message, error.message
        S3_OBJ.delete_bucket(bucket_name)
        LOGGER.info(
            "Step 5: Delete bucket policy should through error message")
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from another account with no permissions")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6081")
    @CTFailOn(error_handler)
    def test_584(self):
        """
        Apply Delete-bucket-policy from another account with authenticated-read permission on bucket
        """
        LOGGER.info(
            "STARTED: Apply Delete-bucket-policy from another account"
            " with authenticated-read permission on bucket")
        random_id = str(time.time())
        test_584_cfg = BKT_POLICY_CONF["test_584"]
        bucket_name = test_584_cfg["bucket_name"]
        account_name_2 = test_584_cfg["account_name_2"].format(random_id)
        email_id_2 = test_584_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info(
            "Step 1 : Create a new bucket with authenticated read permission")
        resp = ACL_OBJ.create_bucket_with_acl(
            bucket_name=bucket_name, acl=test_584_cfg["acl_permission"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created")
        LOGGER.info("Step 2: Retrieving bucket acl attributes")
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket ACL was verified")
        LOGGER.info("Step 3: Apply put bucket policy on the bucket")
        bkt_json_policy = json.dumps(test_584_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Bucket policy was applied on the bucket")
        LOGGER.info(
            "Step 4: Verify the bucket policy from Bucket owner account")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Bucket policy was verified")
        LOGGER.info(
            "Step 5: Login to account2 and delete bucket policy for the bucket "
            "which is present in account1")
        try:
            S3_BKT_POLICY_OBJ_2.delete_bucket_policy(bucket_name)
        except CTException as error:
            assert test_584_cfg["error_message"] in error.message, error.message
        S3_OBJ.delete_bucket(bucket_name)
        LOGGER.info(
            "Step 5: Delete bucket policy should through error message")
        LOGGER.info(
            "ENDED: Apply Delete-bucket-policy from another account with"
            " authenticated-read permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6053")
    @CTFailOn(error_handler)
    def test_693(self):
        """
        Test principal arn combination with invalid account-id"""
        LOGGER.info(
            "STARTED: Test principal arn combination with invalid account-id")
        bkt_cnf_693 = BKT_POLICY_CONF["test_693"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))

        bucket_name = bkt_cnf_693["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        LOGGER.info("Creating a user with name {0}".format(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_693["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_693["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_693["bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(
                user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_693"]["bucket_name"],
                                bkt_cnf_693["bucket_policy"],
                                BKT_POLICY_CONF["test_693"]["error_message"])
        LOGGER.info(
            "ENDED: Test principal arn combination with invalid account-id")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6051")
    @CTFailOn(error_handler)
    def test_694(self):
        """
        Test principal arn combination with invalid user name"""
        LOGGER.info(
            "STARTED: Test principal arn combination with invalid user name")
        bkt_cnf_694 = BKT_POLICY_CONF["test_694"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_694["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_694["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_694["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = bkt_cnf_694[
            "bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(account_id)
        bkt_json_policy = bkt_cnf_694["bucket_policy"]
        self.put_invalid_policy(BKT_POLICY_CONF["test_694"]["bucket_name"],
                                bkt_json_policy,
                                BKT_POLICY_CONF["test_694"]["error_message"])
        LOGGER.info(
            "ENDED: Test principal arn combination with invalid user name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6049")
    @CTFailOn(error_handler)
    def test_716(self):
        """
        Test principal arn combination with valid accountid and valid user but of different account"""
        LOGGER.info(
            "STARTED: Test principal arn combination with "
            "valid accountid and valid user but of different account")
        bkt_cnf_716 = BKT_POLICY_CONF["test_716"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_716["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        LOGGER.info(
            "Creating a user {0} from another account".format(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_716["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_716["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_716["bucket_policy"]["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_716"]["bucket_name"],
                                bkt_cnf_716["bucket_policy"],
                                BKT_POLICY_CONF["test_716"]["error_message"])
        LOGGER.info(
            "ENDED: Test principal arn combination with "
            "valid accountid and valid user but of different account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6045")
    @CTFailOn(error_handler)
    def test_718(self):
        """
        Test principal arn combination with wildcard * for all accounts."""
        LOGGER.info(
            "STARTED: Test principal arn combination with wildcard * for all accounts.")
        bkt_cnf_718 = BKT_POLICY_CONF["test_718"]
        bucket_name = bkt_cnf_718["bucket_name"]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_718["object_name_2"])
        LOGGER.info("Performing put bucket policy")
        self.put_invalid_policy(BKT_POLICY_CONF["test_718"]["bucket_name"],
                                bkt_cnf_718["bucket_policy"],
                                BKT_POLICY_CONF["test_718"]["error_message"])
        LOGGER.info(
            "ENDED: Test principal arn combination with wildcard * for all accounts.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6043")
    @CTFailOn(error_handler)
    def test_719(self):
        """
        Test principal arn combination with wildcard * for all users in account"""
        LOGGER.info(
            "STARTED: Test principal arn combination with wildcard * for all users in account")
        bkt_cnf_719 = BKT_POLICY_CONF["test_719"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_719["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_719["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_719["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_719["bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        self.put_invalid_policy(BKT_POLICY_CONF["test_719"]["bucket_name"],
                                bkt_cnf_719["bucket_policy"],
                                BKT_POLICY_CONF["test_719"]["error_message"])
        LOGGER.info(
            "ENDED: Test principal arn combination with wildcard * for all users in account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6041")
    @CTFailOn(error_handler)
    def test_720(self):
        """
        Test principal arn specifying wildcard in
        the portion of the ARN that specifies the resource type"""
        LOGGER.info(
            "STARTED: Test principal arn specifying wildcard "
            "in the portion of the ARN that specifies the resource type")
        bkt_cnf_720 = BKT_POLICY_CONF["test_720"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_720["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_720["object_name_2"])
        LOGGER.info("Performing put bucket policy")

        bkt_cnf_720["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_720["bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        self.put_invalid_policy(BKT_POLICY_CONF["test_720"]["bucket_name"],
                                bkt_cnf_720["bucket_policy"],
                                BKT_POLICY_CONF["test_720"]["error_message"])
        LOGGER.info(
            "ENDED: Test principal arn specifying wildcard "
            "in the portion of the ARN that specifies the resource type")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6039")
    @CTFailOn(error_handler)
    def test_721(self):
        """
        Test arn specifying invalid text in place of arn"""
        LOGGER.info(
            "STARTED: Test arn specifying invalid text in place of arn")
        bkt_cnf_721 = BKT_POLICY_CONF["test_721"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_721["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info("Creating a user with name {0}".format(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_721["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_721["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_721["bucket_policy"]["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_721"]["bucket_name"],
                                bkt_cnf_721["bucket_policy"],
                                BKT_POLICY_CONF["test_721"]["error_message"])
        LOGGER.info(
            "ENDED: Test arn specifying invalid text in place of arn")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6037")
    @CTFailOn(error_handler)
    def test_722(self):
        """
        Test arn specifying invalid text for partition value"""
        LOGGER.info(
            "STARTED: Test arn specifying invalid text for partition value")
        bkt_cnf_722 = BKT_POLICY_CONF["test_722"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_722["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info("Creating a user with name {0}".format(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_722["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_722["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_722["bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(
                account_id, user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_722"]["bucket_name"],
                                bkt_cnf_722["bucket_policy"],
                                BKT_POLICY_CONF["test_722"]["error_message"])
        LOGGER.info(
            "ENDED: Test arn specifying invalid text for partition value")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6034")
    @CTFailOn(error_handler)
    def test_723(self):
        """
        Test arn specifying invalid text for service value"""
        LOGGER.info(
            "STARTED: Test arn specifying invalid text for service value.")
        bkt_cnf_723 = BKT_POLICY_CONF["test_723"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_723["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info("Creating a user with name {0}".format(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_723["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_723["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_723["bucket_policy"]["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_723"]["bucket_name"],
                                bkt_cnf_723["bucket_policy"],
                                BKT_POLICY_CONF["test_723"]["error_message"])
        LOGGER.info(
            "ENDED: Test arn specifying invalid text for service value.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6032")
    @CTFailOn(error_handler)
    def test_724(self):
        """
        Test arn specifying invalid text for region value ."""
        LOGGER.info(
            "STARTED: Test arn specifying invalid text for region value .")
        bkt_cnf_724 = BKT_POLICY_CONF["test_724"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_724["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info("Creating a user with name {0}".format(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_724["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_724["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_724["bucket_policy"]["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_724"]["bucket_name"],
                                bkt_cnf_724["bucket_policy"],
                                BKT_POLICY_CONF["test_724"]["error_message"])
        LOGGER.info(
            "ENDED: Test arn specifying invalid text for region value .")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6030")
    @CTFailOn(error_handler)
    def test_725(self):
        """
        Test arn specifying component/value as per arn format at inchanged position"""
        LOGGER.info(
            "STARTED: Test arn specifying component/value as per arn format at inchanged position.")
        bkt_cnf_725 = BKT_POLICY_CONF["test_725"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_725["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info("Creating a user with name {0}".format(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("User is created with name {0}".format(user_name))
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_725["object_name_2"])
        LOGGER.info(
            "Performing put bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_725["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_725["bucket_policy"]["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, user_name)
        self.put_invalid_policy(BKT_POLICY_CONF["test_725"]["bucket_name"],
                                bkt_cnf_725["bucket_policy"],
                                BKT_POLICY_CONF["test_725"]["error_message"])
        LOGGER.info(
            "ENDED: Test arn specifying component/value as per arn format at inchanged position")

    # Cannot be automated as unstructured JSON creation fails during YAML config parsing.
    # def test_552(self):
    #     """
    #     Test extra spaces in key fields and values in bucket policy json
    #     :avocado: tags=get_bucket_policy
    #     """

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6103")
    @CTFailOn(error_handler)
    def test_551(self):
        """
        Test missing key fields in bucket policy json
        """
        LOGGER.info(
            "STARTED: Test extra spaces in key fields and values in bucket policy json")
        self.create_bucket_validate(BKT_POLICY_CONF["test_551"]["bucket_name"])
        LOGGER.info("Step 2,3 : Put Bucket policy with missing field")
        self.put_invalid_policy(BKT_POLICY_CONF["test_551"]["bucket_name"],
                                BKT_POLICY_CONF["test_551"]["bucket_policy"],
                                BKT_POLICY_CONF["test_551"]["error_message"])
        LOGGER.info(
            "ENDED: Test missing key fields in bucket policy json")

    # Cannot be automated as unstructured JSON creation fails during YAML config parsing.
    # def test_550(self):
    #     """
    #     Test one of the key field out of the structure in bucket policy json
    #     :avocado: tags=get_bucket_policy
    #     """

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6104")
    @CTFailOn(error_handler)
    def test_549(self):
        """
        Test invalid field in bucket policy json
        """
        LOGGER.info(
            "STARTED: Test invalid field in bucket policy json")
        self.create_bucket_validate(BKT_POLICY_CONF["test_549"]["bucket_name"])
        LOGGER.info("Step 2,3 : Put Bucket policy with invalid field")
        self.put_invalid_policy(BKT_POLICY_CONF["test_549"]["bucket_name"],
                                BKT_POLICY_CONF["test_549"]["bucket_policy"],
                                BKT_POLICY_CONF["test_549"]["error_message"])
        LOGGER.info(
            "ENDED: Test invalid field in bucket policy json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6105")
    @CTFailOn(error_handler)
    def test_545(self):
        """
        Test the case sensitivity of key fields in bucket policy json
        """
        LOGGER.info(
            "STARTED: Test the case sensitivity of key fields in bucket policy json")
        self.create_bucket_validate(BKT_POLICY_CONF["test_545"]["bucket_name"])
        LOGGER.info(
            "Step 2,3 : Put Bucket policy with case sensitivity of key fields")
        self.put_invalid_policy(BKT_POLICY_CONF["test_545"]["bucket_name"],
                                BKT_POLICY_CONF["test_545"]["bucket_policy"],
                                BKT_POLICY_CONF["test_545"]["error_message"])
        LOGGER.info(
            "ENDED: Test the case sensitivity of key fields in bucket policy json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6106")
    @CTFailOn(error_handler)
    def test_555(self):
        """
        Test invalid values in the key fields in bucket policy json
        """
        LOGGER.info(
            "STARTED: Test invalid values in the key fields in bucket policy json")
        self.create_bucket_validate(BKT_POLICY_CONF["test_555"]["bucket_name"])
        LOGGER.info("Step 2,3 : Put Bucket policy with invalid values")
        self.put_invalid_policy(BKT_POLICY_CONF["test_555"]["bucket_name"],
                                BKT_POLICY_CONF["test_555"]["bucket_policy"],
                                BKT_POLICY_CONF["test_555"]["error_message"])
        LOGGER.info(
            "ENDED: Test invalid values in the key fields in bucket policy json")

    # This is invalid scenario as the JSON value contains two keys with same name
    # as JSON is a dictionary it cannot have two keys with same value. So marking this test-case
    # Cannot be automated
    # def test_554(self):
    #     """
    #     Test specifying duplicate key in same statement in bucket policy json
    #     :avocado: tags=get_bucket_policy
    #     """
    #     LOGGER.info(
    #         "STARTED: Test specifying duplicate key in same statement in bucket policy json")
    #     self.create_bucket_validate(BKT_POLICY_CONF["test_554"]["bucket_name"])
    #     LOGGER.info("Step 2,3 : Put Bucket policy with duplicate keys")
    #     self.put_invalid_policy(BKT_POLICY_CONF["test_554"]["bucket_name"],
    #                             BKT_POLICY_CONF["test_554"]["bucket_policy"],
    #                             BKT_POLICY_CONF["test_554"]["error_message"])
    #     LOGGER.info(
    #         "ENDED: Test specifying duplicate key in same statement in bucket policy json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6108")
    @CTFailOn(error_handler)
    def test_553(self):
        """
        Test blank values for the key fields in bucket policy json.
        """
        LOGGER.info(
            "STARTED: Test blank values for the key fields in bucket policy json.")
        self.create_bucket_validate(BKT_POLICY_CONF["test_553"]["bucket_name"])
        LOGGER.info(
            "Step 2,3 : Put Bucket policy with blank values for the key fields")
        self.put_invalid_policy(BKT_POLICY_CONF["test_553"]["bucket_name"],
                                BKT_POLICY_CONF["test_553"]["bucket_policy"],
                                BKT_POLICY_CONF["test_553"]["error_message"])
        LOGGER.info(
            "ENDED: Test blank values for the key fields in bucket policy json.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6015")
    @CTFailOn(error_handler)
    def test_1080(self):
        """
        Test ? wildcard for part of s3 api in action field of statement of the json file
        """
        LOGGER.info(
            "STARTED: Test ? wildcard for part of s3 "
            "api in action field of statement of the json file")
        bkt_cnf_1080 = BKT_POLICY_CONF["test_1080"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_1080["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_1080["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1080["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.get_object(bucket_name, bkt_cnf_1080["object_name_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved object from a bucket {0}".format(bucket_name))
        LOGGER.info(
            "ENDED: Test ? wildcard for part of s3 api in action field of statement of the json file")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6017")
    @CTFailOn(error_handler)
    def test_1079(self):
        """
        Test * wildcard for part of s3 api in action
        field of statement of the json file
        """
        LOGGER.info(
            "STARTED: Test * wildcard for part of s3 "
            "api in action field of statement of the json file")
        bkt_cnf_1079 = BKT_POLICY_CONF["test_1079"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_1079["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        s3_obj_acl = create_account[2]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_1079["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1079["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving object acl from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj_acl.get_object_acl(
            bucket_name, bkt_cnf_1079["object_name_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved object acl from a bucket {0}".format(bucket_name))
        LOGGER.info("Step 2: Uploading an object {0} to a bucket {1}".format(
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"], bucket_name))
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        try:
            s3_obj.put_object(
                bucket_name,
                BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1079["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2: Uploading an object from another account is failed")
        LOGGER.info(
            "ENDED: Test * wildcard for part of s3 api "
            "in action field of statement of the json file")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6020")
    @CTFailOn(error_handler)
    def test_1078(self):
        """
        Test * wildcard for all s3 apis in action field of statement of the json file
        """
        LOGGER.info(
            "STARTED: Test * wildcard for all s3 apis "
            "in action field of statement of the json file")
        bkt_cnf_1078 = BKT_POLICY_CONF["test_1078"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_1078["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        ACL_OBJ = create_account[2]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_1078["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1078["bucket_policy"])
        LOGGER.info(
            "Step 1: Retrieving object and acl of object from a "
            "bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.get_object(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_object_acl(
            bucket_name, bkt_cnf_1078["object_name_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Retrieved object and acl of object from a bucket {0}".format(bucket_name))
        LOGGER.info(
            "ENDED: Test * wildcard for all s3 apis in action field of statement of the json file")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6022")
    @CTFailOn(error_handler)
    def test_1077(self):
        """
        Test * wildcard for all apis in action field of statement of the json file
        """
        LOGGER.info(
            "STARTED: Test * wildcard for all apis in action field of statement of the json file")
        bkt_cnf_1077 = BKT_POLICY_CONF["test_1077"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_1077["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = create_account[1]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_1077["object_name_2"])
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1077["bucket_policy"])
        LOGGER.info(
            "Step 1: Uploading and retrieving object from a bucket {0} using another account {1}".format(
                bucket_name, account_name))
        resp = s3_obj.put_object(
            bucket_name,
            bkt_cnf_1077["object_name_3"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        resp = s3_obj.get_object(bucket_name, bkt_cnf_1077["object_name_3"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Uploaded an object and retrieved the same "
            "object from a bucket {0}".format(bucket_name))
        LOGGER.info(
            "ENDED: Test * wildcard for all apis in action field of statement of the json file")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6047")
    @CTFailOn(error_handler)
    def test_717(self):
        """
        Test principal arn combination with multiple arns"""
        LOGGER.info(
            "STARTED: Test principal arn combination with multiple arns")
        bkt_cnf_717 = BKT_POLICY_CONF["test_717"]
        bucket_name = bkt_cnf_717["bucket_name"]
        user_name_1 = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        user_name_2 = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects using account 1")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_717["object_name_2"])
        LOGGER.info(
            "Step 1: Created a bucket and objects are uploaded using account 1")
        LOGGER.info("Step 2: Creating multiple accounts")
        resp = IAM_OBJ.create_multiple_accounts(
            bkt_cnf_717["acc_count"],
            BKT_POLICY_CONF["bucket_policy"]["acc_name_prefix"])
        acc_id_1 = resp[1][0][1]["Account_Id"]
        access_key_1 = resp[1][0][1]["access_key"]
        secret_key_1 = resp[1][0][1]["secret_key"]

        acc_id_2 = resp[1][1][1]["Account_Id"]
        access_key_2 = resp[1][1][1]["access_key"]
        secret_key_2 = resp[1][1][1]["secret_key"]
        LOGGER.info("Step 2: Multiple accounts are created")
        LOGGER.info("Step 3: Creating users in different accounts")
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key_1, secret_key=secret_key_1)
        iam_obj_acc_3 = iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = iam_obj_acc_2.create_user_using_s3iamcli(
            user_name_1, access_key=access_key_1, secret_key=secret_key_1)
        assert resp[0], resp[1]
        resp = iam_obj_acc_3.create_user_using_s3iamcli(
            user_name_2, access_key=access_key_2, secret_key=secret_key_2)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Users are created in different accounts")
        LOGGER.info(
            "Step 4: Creating a json with combination of multiple arns")
        bkt_cnf_717["bucket_policy"]["Statement"][0]["Principal"]["AWS"][0] = \
            bkt_cnf_717["bucket_policy"]["Statement"][0]["Principal"]["AWS"][0]. \
            format(acc_id_1, user_name_1)
        bkt_cnf_717["bucket_policy"]["Statement"][0]["Principal"]["AWS"][1] = \
            bkt_cnf_717["bucket_policy"]["Statement"][0]["Principal"]["AWS"][1]. \
            format(acc_id_2)
        LOGGER.info(
            "Step 4: json is created with combination of multiple arns")
        self.put_get_bkt_policy(bucket_name, bkt_cnf_717["bucket_policy"])
        LOGGER.info("Step 5: Retrieving object using user of account 2")
        resp = iam_obj_acc_2.create_access_key(user_name_1)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_2 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_2.get_object(
                bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_717["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 5: Retrieved object using user of account 2 is failed with error {0}".format(
                bkt_cnf_717["error_message"]))
        LOGGER.info("Step 6: Retrieving object using account 3")
        s3_obj_acc_3 = s3_test_lib.S3TestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp = s3_obj_acc_3.get_object(
            bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info("Step 6: Retrieved object using account 3")
        LOGGER.info("Step 7: Retrieving object using user of account 3")
        resp = iam_obj_acc_3.create_access_key(user_name_2)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_3 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_3.get_object(
                bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_717["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 7: Retrieving object using user of account 3 is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test principal arn combination with multiple arns")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6055")
    @CTFailOn(error_handler)
    def test_692(self):
        """
        Test principal arn combination with user name"""
        LOGGER.info(
            "STARTED: Test principal arn combination with user name")
        bkt_cnf_692 = BKT_POLICY_CONF["test_692"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_692["bucket_name"]
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects using account 1")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_692["object_name_2"])
        LOGGER.info(
            "Step 1: Created a bucket and objects are uploaded using account 1")
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info(
            "Step 2: Creating a user with name {0} in account 2".format(user_name))
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_obj_acc_2.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: User is created with name {0} in account 2".format(user_name))
        LOGGER.info("Step 3: Creating a json with user name of account 2")
        bkt_cnf_692["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_692["bucket_policy"]["Statement"][0]["Principal"]["AWS"]. \
            format(account_id, user_name)
        LOGGER.info("Step 3: json is created with user name of account 2")
        self.put_get_bkt_policy(bucket_name, bkt_cnf_692["bucket_policy"])
        LOGGER.info(
            "Step 4: Retrieving object from a bucket using account 1")
        resp = S3_OBJ.get_object(
            bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Retrieved object from a bucket using account 1")
        LOGGER.info("Step 5: Retrieving object using user of account 2")
        resp = iam_obj_acc_2.create_access_key(user_name)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_2 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_2.get_object(
                bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_692["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 5: Retrieving object using user of account 2 is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test principal arn combination with user name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6075")
    @CTFailOn(error_handler)
    def test_691(self):
        """
        Test principal arn combination with account-id"""
        LOGGER.info(
            "STARTED: Test principal arn combination with account-id")
        bkt_cnf_691 = BKT_POLICY_CONF["test_691"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        bucket_name = bkt_cnf_691["bucket_name"]
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects using account 1")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_691["object_name_2"])
        LOGGER.info(
            "Step 1: Created a bucket and uploading objects using account 1")
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj_acc_2 = create_account[1]
        access_key = create_account[4]
        secret_key = create_account[5]
        account_id = create_account[6]
        LOGGER.info(
            "Step 2: Creating a user with name {0} in account 2".format(user_name))
        iam_obj_acc_2 = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_obj_acc_2.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: User is created with name {0} in account 2".format(user_name))
        LOGGER.info("Step 3: Creating a json with combination of account id")
        bkt_cnf_691["bucket_policy"]["Statement"][0]["Principal"]["AWS"] = \
            bkt_cnf_691["bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info("Step 3: json is created with combination of account id")
        self.put_get_bkt_policy(bucket_name, bkt_cnf_691["bucket_policy"])
        LOGGER.info("Step 4: Retrieving object using account 2")
        resp = s3_obj_acc_2.get_object(
            bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Retrieved object using account 2")
        LOGGER.info("Step 5: Retrieving object using user of account 2")
        resp = iam_obj_acc_2.create_access_key(user_name)
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_obj_usr_2 = s3_test_lib.S3TestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        try:
            s3_obj_usr_2.get_object(
                bucket_name, BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_691["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 5: Retrieving object using user of account 2 is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test principal arn combination with account-id")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5996")
    @CTFailOn(error_handler)
    def test_4134(self):
        """
        Create Bucket Policy using NumericLessThan Condition Operator, key "s3:max-keys" and Effect Allow"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThan Condition"
            " Operator,key s3:max-keys and Effect Allow")
        random_id = str(time.time())
        test_4134_cfg = BKT_POLICY_CONF["test_4134"]
        bucket_name = test_4134_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4134_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4134_cfg["account_name"].format(random_id)
        email_id = test_4134_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(test_4134_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4134_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        resp = S3_OBJ_2.list_objects_with_prefix(
            bucket_name, maxkeys=test_4134_cfg["maxkeys"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Verified the object listing from the second account")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThan Condition"
            " Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5994")
    @CTFailOn(error_handler)
    def test_4136(self):
        """
        Create Bucket Policy using NumericLessThan Condition Operator, key s3:max-keys and Effect Deny"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThan Condition Operator,"
            "key s3:max-keys and Effect Deny")
        random_id = str(time.time())
        test_4136_cfg = BKT_POLICY_CONF["test_4136"]
        bucket_name = test_4136_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4136_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4136_cfg["account_name"].format(random_id)
        email_id = test_4136_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(test_4136_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericLessThan Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4136_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        try:
            S3_OBJ_2.list_objects_with_prefix(
                bucket_name, maxkeys=test_4136_cfg["maxkeys"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4136_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 4: Verified that listing of object from second account failing with error: {}".format(
                test_4136_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThan Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5992")
    @CTFailOn(error_handler)
    def test_4143(self):
        """
        Create Bucket Policy using NumericGreaterThan Condition Operator, key "s3:max-keys" and Effect Allow"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThan Condition"
            " Operator,key s3:max-keys and Effect Allow")
        random_id = str(time.time())
        test_4143_cfg = BKT_POLICY_CONF["test_4143"]
        bucket_name = test_4143_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4143_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4143_cfg["account_name"].format(random_id)
        email_id = test_4143_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(test_4143_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4143_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        resp = S3_OBJ_2.list_objects_with_prefix(
            bucket_name, maxkeys=test_4143_cfg["maxkeys"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Verified the object listing from the second account")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThan Condition"
            " Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5985")
    @CTFailOn(error_handler)
    def test_4144(self):
        """
        Create Bucket Policy using NumericGreaterThan Condition Operator, key s3:max-keys and Effect Deny"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThan Condition Operator,"
            "key s3:max-keys and Effect Deny")
        random_id = str(time.time())
        test_4144_cfg = BKT_POLICY_CONF["test_4144"]
        bucket_name = test_4144_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4144_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4144_cfg["account_name"].format(random_id)
        email_id = test_4144_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(test_4144_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericGreaterThan Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4144_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        try:
            S3_OBJ_2.list_objects_with_prefix(
                bucket_name, maxkeys=test_4144_cfg["maxkeys"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4144_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 4:Verified that listing of object from second account failing with error: {}".format(
                test_4144_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThan Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5983")
    @CTFailOn(error_handler)
    def test_4145(self):
        """
        Create Bucket Policy using NumericEquals Condition Operator, key "s3:max-keys" and Effect Allow"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericEquals Condition"
            " Operator,key s3:max-keys and Effect Allow")
        random_id = str(time.time())
        test_4145_cfg = BKT_POLICY_CONF["test_4145"]
        bucket_name = test_4145_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4145_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4145_cfg["account_name"].format(random_id)
        email_id = test_4145_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericEquals Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(test_4145_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericEquals Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4145_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        resp = S3_OBJ_2.list_objects_with_prefix(
            bucket_name, maxkeys=test_4145_cfg["maxkeys"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Verified the object listing from the second account")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericEquals Condition"
            " Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5980")
    @CTFailOn(error_handler)
    def test_4146(self):
        """
        Create Bucket Policy using NumericNotEquals Condition Operator, key s3:max-keys and Effect Deny"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericNotEquals Condition Operator,"
            "key s3:max-keys and Effect Deny")
        random_id = str(time.time())
        test_4146_cfg = BKT_POLICY_CONF["test_4146"]
        bucket_name = test_4146_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4146_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4146_cfg["account_name"].format(random_id)
        email_id = test_4146_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericNotEquals Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(test_4146_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericNotEquals Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4146_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        try:
            S3_OBJ_2.list_objects_with_prefix(
                bucket_name, maxkeys=test_4146_cfg["maxkeys"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4146_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 4: Verified that listing of object from second account failing with error: {}".format(
                test_4146_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericNotEquals Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5978")
    @CTFailOn(error_handler)
    def test_4147(self):
        """
        Create Bucket Policy using NumericLessThanEquals Condition Operator, key "s3:max-keys" and Effect Allow"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThanEquals "
            "Condition Operator,key s3:max-keys and Effect Allow")
        random_id = str(time.time())
        test_4147_cfg = BKT_POLICY_CONF["test_4147"]
        bucket_name = test_4147_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4147_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4147_cfg["account_name"].format(random_id)
        email_id = test_4147_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericEquals Condition Operator Effect Allow")
        bkt_json_policy = eval(json.dumps(test_4147_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericLessThanEquals Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4147_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list object from another account")
        resp = S3_OBJ_2.list_objects_with_prefix(
            bucket_name, maxkeys=test_4147_cfg["maxkeys"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Verified the object listing from the second account")
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThanEquals "
            "Condition Operator,key s3:max-keys and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5976")
    @CTFailOn(error_handler)
    def test_4148(self):
        """
        Create Bucket Policy using NumericGreaterThanEquals
        Condition Operator, key s3:max-keys and Effect Deny"""
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator,"
            "key s3:max-keys and Effect Deny")
        random_id = str(time.time())
        test_4148_cfg = BKT_POLICY_CONF["test_4148"]
        bucket_name = test_4148_cfg["bucket_name"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4148_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        account_name = test_4148_cfg["account_name"].format(random_id)
        email_id = test_4148_cfg["emailid"].format(random_id)
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        S3_OBJ_2 = create_account[1]
        LOGGER.info(
            "Step 1 : Creating a json for bucket policy specifying using "
            "NumericGreaterThanEquals Condition Operator and Effect Deny")
        bkt_json_policy = eval(json.dumps(test_4148_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"] = account_id
        LOGGER.debug("json string is : {}".format(bkt_json_policy))
        LOGGER.info(
            "Step 1 : Created a json string for bucket policy specifying using "
            "NumericNotEquals Condition Operator")
        LOGGER.info("Step 2: Apply the bucket policy on the bucket")
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, json.dumps(bkt_json_policy))
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket policy was applied successfully")
        LOGGER.info("Step 3: Verify bucket policy")
        resp = S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        bucket_policy = list(eval(resp[1]["Policy"])[
            "Statement"][0]["Condition"].keys())
        ASRTOBJ.assert_equals(
            bucket_policy[0],
            test_4148_cfg["buc_policy_val"],
            resp[1])
        LOGGER.info("Step 3: Bucket policy was verified successfully")
        LOGGER.info(
            "Step 4: Verify the list of objects from another account")
        try:
            S3_OBJ_2.list_objects_with_prefix(
                bucket_name, maxkeys=test_4148_cfg["maxkeys"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4148_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 4: Verified that listing of object "
            "from second account failing with error: {}".format(
                test_4148_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEquals Condition Operator, "
            "key s3:max-keys and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6109")
    @CTFailOn(error_handler)
    def test_1190(self):
        """
        Test bucket policy with Effect "Allow" and "Deny " using invalid user id"""
        LOGGER.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using invalid user id")
        bkt_cnf_1190 = BKT_POLICY_CONF["test_1190"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_1190["bucket_name"]
        create_account = self.create_s3iamcli_acc(account_name, email_id)
        account_id = create_account[6]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Applying bucket policy on a bucket {0}".format(bucket_name))
        bkt_cnf_1190["bucket_policy"]["Statement"][0]["Principal"]["AWS"][0] = \
            bkt_cnf_1190["bucket_policy"]["Statement"][0]["Principal"]["AWS"][0]. \
            format(account_id)
        bkt_cnf_1190["bucket_policy"]["Statement"][1]["Principal"]["AWS"][0] = \
            bkt_cnf_1190["bucket_policy"]["Statement"][1]["Principal"]["AWS"][0]. \
            format(account_id)
        bkt_policy_json = json.dumps(bkt_cnf_1190["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1190["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2 : Applying policy on a bucket is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using invalid user id")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6111")
    @CTFailOn(error_handler)
    def test_1180(self):
        """
        Test Bucket policy on action field with delete-bucket-policy where effect is
        Allow and verify user can delete-bucket-policy"""
        LOGGER.info(
            "STARTED: Test Bucket policy on action field with delete-bucket-policy "
            "where effect is Allow and verify user can delete-bucket-policy")
        bkt_cnf_1180 = BKT_POLICY_CONF["test_1180"]
        bucket_name = bkt_cnf_1180["bucket_name"]
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1180["bucket_policy"])
        resp = IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info("Step 2: Deleting bucket policy with users credentials")
        resp = s3_policy_usr_obj.delete_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Bucket policy is deleted with users credentials")
        LOGGER.info(
            "Step 3: Verifying that bucket policy is deleted from a bucket {0}".format(bucket_name))
        try:
            S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1180["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Verified that policy is deleted from a bucket {0}".format(bucket_name))
        LOGGER.info(
            "ENDED: Test Bucket policy on action field with delete-bucket-policy where "
            "effect is Allow and verify user can delete-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6110")
    @CTFailOn(error_handler)
    def test_1191(self):
        """
        Test bucket policy with Effect "Allow" and "Deny " using invalid Account id"""
        LOGGER.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using invalid Account id")
        bkt_cnf_1191 = BKT_POLICY_CONF["test_1191"]
        bucket_name = bkt_cnf_1191["bucket_name"]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Applying policy on a bucket {0}".format(bucket_name))
        bkt_policy_json = json.dumps(bkt_cnf_1191["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1191["error_message"] in error.message, error.message
            LOGGER.info("Step 2: Applying policy on a bucket is "
                        "failed with error {0}".format(error.message))
        LOGGER.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using invalid Account id")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6112")
    @CTFailOn(error_handler)
    def test_1184(self):
        """
        Test bucket policy with Wildcard ? in action for delete bucket policy"""
        LOGGER.info(
            "Test bucket policy with Wildcard ? in action for delete bucket policy")
        bkt_cnf_1184 = BKT_POLICY_CONF["test_1184"]
        bucket_name = bkt_cnf_1184["bucket_name"]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Applying policy on a bucket {0}".format(bucket_name))
        bkt_policy_json = json.dumps(bkt_cnf_1184["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1184["error_message"] in error.message, error.message
            LOGGER.info("Step 2: Applying policy on a bucket is "
                        "failed with error {0}".format(error.message))
        LOGGER.info(
            "ENDED: Test bucket policy with Wildcard ? in action for delete bucket policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6113")
    @CTFailOn(error_handler)
    def test_1171(self):
        """
        Test Bucket policy on action field with get-bucket-policy
         and verify other account can get-bucket-policy"""
        LOGGER.info(
            "STARTED: Test Bucket policy on action field with get-bucket-policy"
            " and verify other account can get-bucket-policy")
        bkt_cnf_1171 = BKT_POLICY_CONF["test_1171"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        bucket_name = bkt_cnf_1171["bucket_name"]
        resp = self.create_s3iamcli_acc(account_name, email_id)
        s3_bkt_policy = resp[3]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1171["bucket_policy"])
        LOGGER.info(
            "Step 2: Retrieving policy of a bucket {0} "
            "from another account {0}".format(
                bucket_name, account_name))
        try:
            s3_bkt_policy.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1171["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Retrieving policy of a bucket from another account "
                "is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test Bucket policy on action field with get-bucket-policy "
            "and verify other account can get-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6114")
    @CTFailOn(error_handler)
    def test_1182(self):
        """
        Test Bucket policy on action field with delete-bucket-policy where effect is
         Deny and verify user can delete-bucket-policy"""
        LOGGER.info(
            "STARTED: Test Bucket policy on action field with delete-bucket-policy where effect "
            "is Deny and verify user can delete-bucket-policy")
        bkt_cnf_1182 = BKT_POLICY_CONF["test_1182"]
        bucket_name = bkt_cnf_1182["bucket_name"]
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1182["bucket_policy"])
        resp = IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info("Step 2: Deleting bucket policy with users credentials")
        try:
            s3_policy_usr_obj.delete_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1182["error_message"] in error.message, error.message
            LOGGER.info("Step 2: Deleting policy with users credential is "
                        "failed with error {0}".format(error.message))
        LOGGER.info(
            "ENDED: Test Bucket policy on action field with delete-bucket-policy where effect "
            "is Deny and verify user can delete-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6115")
    @CTFailOn(error_handler)
    def test_1110(self):
        """
        Test bucket policy statement Effect "Deny" using json"""
        LOGGER.info(
            "STARTED: Test bucket policy statement Effect Deny using json")
        bkt_cnf_1110 = BKT_POLICY_CONF["test_1110"]
        bucket_name = bkt_cnf_1110["bucket_name"]
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1110["bucket_policy_1"])
        resp = IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info(
            "Step 2: Applying policy on a bucket with users credentials")
        bkt_policy_json = json.dumps(bkt_cnf_1110["bucket_policy_2"])
        try:
            s3_policy_usr_obj.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1110["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Applying policy on a bucket with users credential is "
                "failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test bucket policy statement Effect Deny using json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6116")
    @CTFailOn(error_handler)
    def test_1187(self):
        """
        Test bucket policy with Effect "Allow " and "Deny" using user id"""
        LOGGER.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using user id")
        bkt_cnf_1187 = BKT_POLICY_CONF["test_1187"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        resp = self.create_s3iamcli_acc(account_name, email_id)
        s3_obj = resp[1]
        s3_policy_obj = resp[3]
        access_key = resp[4]
        secret_key = resp[5]
        account_id = resp[6]
        iam_new_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        bucket_name = bkt_cnf_1187["bucket_name"]
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = s3_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Creating a new user with name {0} and "
            "also creating credentials for the same user".format(user_name))
        resp = iam_new_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        resp = iam_new_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info("Step 2: Created an user and credentials for that user")
        LOGGER.info(
            "Step 3: Applying policy on a bucket {0}".format(bucket_name))
        bkt_cnf_1187["bucket_policy"]["Statement"][0]["Principal"]["AWS"][0] = \
            bkt_cnf_1187["bucket_policy"]["Statement"][0]["Principal"]["AWS"][0].format(
                account_id, user_name)
        bkt_cnf_1187["bucket_policy"]["Statement"][1]["Principal"]["AWS"][0] = \
            bkt_cnf_1187["bucket_policy"]["Statement"][1]["Principal"]["AWS"][0].format(
                account_id, user_name)
        bkt_policy_json = json.dumps(bkt_cnf_1187["bucket_policy"])
        resp = s3_policy_obj.put_bucket_policy(bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Applied policy on a bucket {0}".format(bucket_name))
        LOGGER.info(
            "Step 4: Retrieving policy of a bucket {0}".format(bucket_name))
        resp = s3_policy_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        LOGGER.info(
            "Step 4: Retrieved policy of a bucket {0}".format(bucket_name))
        LOGGER.info(
            "Step 5: Retrieving policy of a bucket using users credentials")
        resp = s3_policy_usr_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        LOGGER.info(
            "Step 5: Retrieved policy of a bucket using users credentials")
        LOGGER.info(
            "Step 6: Deleting policy of a bucket using users credentials")
        try:
            s3_policy_usr_obj.delete_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1187["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 6: Deleting policy of a bucket is failed with error {0}".format(
                    error.message))
        LOGGER.info("Cleanup activity")
        s3_obj.delete_bucket(bucket_name)
        iam_new_obj.delete_access_key(user_name, usr_access_key)
        LOGGER.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using user id")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6117")
    @CTFailOn(error_handler)
    def test_1166(self):
        """
        Test * Wildcard for all s3apis in action
        field of statement of the json file with effect "Allow"
        """
        LOGGER.info(
            "STARTED: Test * Wildcard for all s3apis in "
            "action field of statement of the json file with effect Allow")
        bkt_cnf_1166 = BKT_POLICY_CONF["test_1166"]
        bucket_name = bkt_cnf_1166["bucket_name"]
        user_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1166["bucket_policy"])
        resp = IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key = resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key = resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info(
            "Step 2: Retrieving policy of a bucket using users cedentials")
        resp = s3_policy_usr_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Retrieved policy of a bucket using users credentials")
        LOGGER.info(
            "ENDED: Test * Wildcard for all s3apis in "
            "action field of statement of the json file with effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6118")
    @CTFailOn(error_handler)
    def test_1177(self):
        """
        Test Bucket policy on action field with delete-bucket-policy
        and verify other account can delete-bucket-policy"""
        LOGGER.info(
            "STARTED: Test Bucket policy on action field with "
            "delete-bucket-policy and verify other account can delete-bucket-policy")
        bkt_cnf_1177 = BKT_POLICY_CONF["test_1177"]
        bucket_name = bkt_cnf_1177["bucket_name"]
        account_name = "{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id = "{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        resp = self.create_s3iamcli_acc(account_name, email_id)
        s3_policy_obj = resp[3]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1177["bucket_policy"])
        LOGGER.info(
            "Step 2: Deleting a bucket policy with another account {0}".format(account_name))
        try:
            s3_policy_obj.delete_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1177["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Deleting bucket policy is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test Bucket policy on action field with delete-bucket-policy"
            " and verify other account can delete-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6119")
    @CTFailOn(error_handler)
    def test_360(self):
        """
        Apply put-bucket-policy on existing bucket

        """
        LOGGER.info("STARTED: Apply put-bucket-policy on existing bucket")
        test_360_cfg = BKT_POLICY_CONF["test_360"]
        bucket_name = test_360_cfg["bucket_name"]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Apply the bucket policy on the bucket with valid json string")
        bkt_json_policy = json.dumps(test_360_cfg["bucket_policy"])
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_json_policy)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Bucket policy was successfully apply to the bucket : {}".format(bucket_name))
        LOGGER.info("ENDED: Apply put-bucket-policy on existing bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6120")
    @CTFailOn(error_handler)
    def test_362(self):
        """
        Apply put-bucket-policy on non existing bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy on non existing bucket")
        test_362_cfg = BKT_POLICY_CONF["test_362"]
        bucket_name = test_362_cfg["bucket_name"]
        LOGGER.info(
            "Step 2: Apply the bucket policy on the non-existing bucket")
        bkt_json_policy = json.dumps(test_362_cfg["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_362_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2: Put Bucket policy failed with error message : {}".format(
                test_362_cfg["error_message"]))
        LOGGER.info(
            "Step 2: Bucket policy was successfully apply to the bucket : {}".format(bucket_name))
        LOGGER.info("ENDED: Apply put-bucket-policy on non existing bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6121")
    @CTFailOn(error_handler)
    def test_363(self):
        """
        Apply put-bucket-policy without specifying bucket name

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy without specifying bucket name")
        test_363_cfg = BKT_POLICY_CONF["test_363"]
        bkt_json_policy = json.dumps(test_363_cfg["bucket_policy"])
        LOGGER.info("Step 1: Put Bucket policy without bucket name")
        try:
            bucket_name = None
            S3_BKT_POLICY_OBJ.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_363_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 1: Put Bucket policy failed with error message : {}".format(
                test_363_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Apply put-bucket-policy without specifying bucket name")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6122")
    @CTFailOn(error_handler)
    def test_364(self):
        """
        Test Apply put-bucket-policy without specifying policy

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy without specifying policy")
        test_364_cfg = BKT_POLICY_CONF["test_364"]
        bucket_name = test_364_cfg["bucket_name"]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Apply the bucket policy on the bucket with invalid json string")
        try:
            json_policy = None
            S3_BKT_POLICY_OBJ.put_bucket_policy(
                bucket_name, json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_364_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2: Put Bucket policy operation failed with error message : {}".format(
                test_364_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Apply put-bucket-policy without specifying policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6123")
    @CTFailOn(error_handler)
    def test_365(self):
        """
        Apply put-bucket-policy with specifying policy in non json format

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy with specifying policy in non json format")
        test_365_cfg = BKT_POLICY_CONF["test_365"]
        bucket_name = test_365_cfg["bucket_name"]
        LOGGER.info(
            "Step 1 : Creating a bucket with name {0}".format(bucket_name))
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket is created with name {0}".format(bucket_name))
        LOGGER.info(
            "Step 2: Apply the bucket policy on the bucket with invalid json string")
        bkt_json_policy = json.dumps(test_365_cfg["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(
                bucket_name, json.loads(bkt_json_policy))
        except CTException as error:
            LOGGER.error(error.message)
            assert test_365_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2: Put Bucket policy failed with error message : {}".format(
                test_365_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Apply put-bucket-policy with specifying policy in non json format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6124")
    @CTFailOn(error_handler)
    def test_366(self):
        """
        Apply put-bucket-policy from another account given read permission on bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from another account given read permission on bucket")

        random_id = str(time.time())
        test_366_cfg = BKT_POLICY_CONF["test_366"]
        bucket_name = test_366_cfg["bucket_name"]
        account_name_2 = test_366_cfg["account_name_2"].format(random_id)
        email_id_2 = test_366_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        LOGGER.info(
            "Step 1 : Create a new bucket assign read bucket permission to account2")
        resp = ACL_OBJ.create_bucket_with_acl(
            bucket_name, grant_read=test_366_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created with read permission")
        self.put_bucket_policy_with_err(
            bucket_name, test_366_cfg, S3_BKT_POLICY_OBJ_2)
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from another account given read permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6125")
    @CTFailOn(error_handler)
    def test_367(self):
        """
        Apply put-bucket-policy from another account given write permission on bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from "
            "another account given write permission on bucket")
        random_id = str(time.time())
        test_367_cfg = BKT_POLICY_CONF["test_367"]
        bucket_name = test_367_cfg["bucket_name"]
        account_name_2 = test_367_cfg["account_name_2"].format(random_id)
        email_id_2 = test_367_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        LOGGER.info(
            "Step 1 : Create a new bucket assign write bucket permission to account2")
        resp = ACL_OBJ.create_bucket_with_acl(
            bucket_name, grant_write=test_367_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created with write permission")
        self.put_bucket_policy_with_err(
            bucket_name, test_367_cfg, S3_BKT_POLICY_OBJ_2)
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from another account given write permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6126")
    @CTFailOn(error_handler)
    def test_368(self):
        """
        Apply put-bucket-policy from another account given read-acp permission on bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from another account given read-acp permission on bucket")
        random_id = str(time.time())
        test_368_cfg = BKT_POLICY_CONF["test_368"]
        bucket_name = test_368_cfg["bucket_name"]
        account_name_2 = test_368_cfg["account_name_2"].format(random_id)
        email_id_2 = test_368_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        LOGGER.info(
            "Step 1 : Create a new bucket assign read-acp bucket permission to account2")
        resp = ACL_OBJ.create_bucket_with_acl(
            bucket_name, grant_read_acp=test_368_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created with read-acp permission")
        self.put_bucket_policy_with_err(
            bucket_name, test_368_cfg, S3_BKT_POLICY_OBJ_2)
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from "
            "another account given read-acp permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6127")
    @CTFailOn(error_handler)
    def test_369(self):
        """
        Apply put-bucket-policy from another account given write-acp permission on bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from "
            "another account given write-acp permission on bucket")
        random_id = str(time.time())
        test_369_cfg = BKT_POLICY_CONF["test_369"]
        bucket_name = test_369_cfg["bucket_name"]
        account_name_2 = test_369_cfg["account_name_2"].format(random_id)
        email_id_2 = test_369_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        LOGGER.info(
            "Step 1 : Create a new bucket assign write-acp bucket permission to account2")
        resp = ACL_OBJ.create_bucket_with_acl(
            bucket_name, grant_write_acp=test_369_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created with write-acp permission")
        self.put_bucket_policy_with_err(
            bucket_name, test_369_cfg, S3_BKT_POLICY_OBJ_2)
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from another "
            "account given write-acp permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6128")
    @CTFailOn(error_handler)
    def test_370(self):
        """
        Apply put-bucket-policy from another account given full-control permission on bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from another "
            "account given full-control permission on bucket")
        random_id = str(time.time())
        test_370_cfg = BKT_POLICY_CONF["test_370"]
        bucket_name = test_370_cfg["bucket_name"]
        account_name_2 = test_370_cfg["account_name_2"].format(random_id)
        email_id_2 = test_370_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        canonical_id_user_2 = result_2[0]
        LOGGER.info(
            "Step 1 : Create a new bucket assign full-control bucket permission to account2")
        resp = ACL_OBJ.create_bucket_with_acl(
            bucket_name,
            grant_full_control=test_370_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with full-control permission")
        self.put_bucket_policy_with_err(
            bucket_name, test_370_cfg, S3_BKT_POLICY_OBJ_2)
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from "
            "another account given full-control permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6129")
    @CTFailOn(error_handler)
    def test_371(self):
        """
        Apply put-bucket-policy from another account with no permissions.

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from another account with no permissions.")
        random_id = str(time.time())
        test_371_cfg = BKT_POLICY_CONF["test_371"]
        bucket_name = test_371_cfg["bucket_name"]
        account_name_2 = test_371_cfg["account_name_2"].format(random_id)
        email_id_2 = test_371_cfg["emailid_2"].format(random_id)
        result_2 = self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2 = result_2[3]
        LOGGER.info("Step 1 : Create a new bucket")
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Bucket was created")
        LOGGER.info(
            "Step 2: Apply put bucket policy on the bucket using account 2")
        bkt_json_policy = json.dumps(test_371_cfg["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ_2.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_371_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2: Put Bucket policy from second account failing with error: {}".format(
                test_371_cfg["error_message"]))
        resp=ACL_OBJ.put_bucket_acl(
            bucket_name, acl = BKT_POLICY_CONF["bucket_policy"]["acl_permission"])
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from another account with no permissions.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6131")
    @CTFailOn(error_handler)
    def test_372(self):
        """
        Apply put-bucket-policy from another account with authenticated-read permission on bucket

        """
        LOGGER.info(
            "STARTED: Apply put-bucket-policy from another "
            "account with authenticated-read permission on bucket")
        random_id=str(time.time())
        test_372_cfg=BKT_POLICY_CONF["test_372"]
        bucket_name=test_372_cfg["bucket_name"]
        account_name_2=test_372_cfg["account_name_2"].format(random_id)
        email_id_2=test_372_cfg["emailid_2"].format(random_id)
        result_2=self.create_s3iamcli_acc(account_name_2, email_id_2)
        S3_BKT_POLICY_OBJ_2=result_2[3]
        LOGGER.info("Step 1 : Create a new bucket assign"
                    " authenticated-read bucket permission to account2")
        resp=ACL_OBJ.create_bucket_with_acl(
            bucket_name, acl = test_372_cfg["bucket_permission"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1 : Bucket was created with authenticated-read permission")
        LOGGER.info("Step 2: Get bucket acl")
        resp=ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket ACL was verified")
        LOGGER.info(
            "Step 2: Apply put bucket policy on the bucket using account 2")
        bkt_json_policy=json.dumps(test_372_cfg["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ_2.put_bucket_policy(
                bucket_name, bkt_json_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_372_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 2: Put Bucket policy from second account failing with error: {}".format(
                test_372_cfg["error_message"]))
        resp=ACL_OBJ.put_bucket_acl(
            bucket_name, acl=BKT_POLICY_CONF["bucket_policy"]["acl_permission"])
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Apply put-bucket-policy from another account with "
            "authenticated-read permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6132")
    @CTFailOn(error_handler)
    def test_373(self):
        """
        Test Apply put-bucket-policy from public domain with public-read permission on bucket.

        """
        LOGGER.info(
            "STARTED: Test Apply put-bucket-policy from public"
            " domain with public-read permission on bucket")
        test_373_cfg=BKT_POLICY_CONF["test_373"]
        bucket_name=test_373_cfg["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info("Step 1: Applying public-read acl to a bucket")
        resp=ACL_OBJ.put_bucket_acl(
            bucket_name, acl=test_373_cfg["bucket_permission"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Applied public-read acl to a bucket")
        LOGGER.info("Step 2: Retrieving acl of a bucket")
        resp=ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Retrieved acl of a bucket")
        LOGGER.info("Step 3: Applying policy on a bucket")
        bkt_policy_json=json.dumps(test_373_cfg["bucket_policy"])
        try:
            NO_AUTH_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_373_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Applying policy on a bucket is failed with error {0}".format(
                    error.message))
        resp=ACL_OBJ.put_bucket_acl(
            bucket_name, acl=BKT_POLICY_CONF["bucket_policy"]["acl_permission"])
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Test Apply put-bucket-policy from public"
            " domain with public-read permission on bucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6133")
    @CTFailOn(error_handler)
    def test_374(self):
        """
        Test Apply put-bucket-policy from public domain
         with public-read-write permission on bucket.

        """
        LOGGER.info(
            "STARTED: Test Apply put-bucket-policy from public "
            "domain with public-read-write permission on bucket")
        test_374_cfg=BKT_POLICY_CONF["test_374"]
        bucket_name=test_374_cfg["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info("Step 1. Applying public-read-write acl to a bucket")
        resp=ACL_OBJ.put_bucket_acl(
            bucket_name, acl=test_374_cfg["bucket_permission"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1. Applied public-read-write acl to a bucket")
        LOGGER.info("Step 2: Retrieving acl of a bucket")
        resp=ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Retrieved acl of a bucket")
        LOGGER.info("Step 3: Applying policy on a bucket")
        bkt_policy_json=json.dumps(test_374_cfg["bucket_policy"])
        try:
            NO_AUTH_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_374_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Applying policy on a bucket is failed with error {0}".format(
                    error.message))
        resp=ACL_OBJ.put_bucket_acl(
            bucket_name, acl=BKT_POLICY_CONF["bucket_policy"]["acl_permission"])
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Test Apply put-bucket-policy from public "
            "domain with public-read-write permission on bucket.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6134")
    @CTFailOn(error_handler)
    def test_1188(self):
        """
        Test bucket policy with Effect "Allow " and "Deny" using account id
        and verify other account can delete-bucket-policy"""
        LOGGER.info(
            "STARTED: Test bucket policy with Effect Allow and Deny using account id")
        bkt_cnf_1188=BKT_POLICY_CONF["test_1188"]
        bucket_name=bkt_cnf_1188["bucket_name"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        resp=self.create_s3iamcli_acc(account_name, email_id)
        s3_policy_obj=resp[3]
        account_id=resp[6]
        self.create_bucket_validate(bucket_name)
        bkt_cnf_1188["bucket_policy"]["Statement"][0]["Principal"]["AWS"]= \
            bkt_cnf_1188["bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        bkt_cnf_1188["bucket_policy"]["Statement"][1]["Principal"]["AWS"]= \
            bkt_cnf_1188["bucket_policy"]["Statement"][1]["Principal"]["AWS"].format(
                account_id)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1188["bucket_policy"])
        LOGGER.info(
            "Step 2: Retrieving bucket policy from another account {0}".format(account_name))
        try:
            s3_policy_obj.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1188["error_message_1"] in error.message, error.message
            LOGGER.info(
                "Step 2:  Retrieving bucket policy from "
                "another account is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "Step 3: Deleting policy of a bucket with another account {0}".format(account_name))
        try:
            s3_policy_obj.delete_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1188["error_message_2"] in error.message, error.message
            LOGGER.info(
                "Step 3: Deleting policy of a bucket "
                "with another account is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test bucket policy with Effect Allow and Deny using account id")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6136")
    @CTFailOn(error_handler)
    def test_1174(self):
        """
        Test Bucket policy on action field with put-bucket-policy
        and verify other account can put-bucket-policy"""
        LOGGER.info(
            "STARTED: Test Bucket policy on action field with"
            "put-bucket-policy and verify other account can put-bucket-policy")
        bkt_cnf_1174=BKT_POLICY_CONF["test_1174"]
        bucket_name=bkt_cnf_1174["bucket_name"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        resp=self.create_s3iamcli_acc(account_name, email_id)
        s3_policy_obj=resp[3]
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1174["bucket_policy"])
        LOGGER.info(
            "Step 2: Applying bucket policy from another account {0}".format(account_name))
        bkt_policy_json=json.dumps(bkt_cnf_1174["bucket_policy"])
        try:
            s3_policy_obj.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1174["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Applying bucket policy from another "
                "account is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test Bucket policy on action field with put-bucket-policy "
            "and verify other account can put-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6138")
    @CTFailOn(error_handler)
    def test_1185(self):
        """
        Test Wildcard * in action for delete bucket policy with effect is Deny"""
        LOGGER.info(
            "STARTED: Test Wildcard * in action for delete bucket policy with effect is Deny")
        bkt_cnf_1185=BKT_POLICY_CONF["test_1185"]
        bucket_name=bkt_cnf_1185["bucket_name"]
        user_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1185["bucket_policy"])
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info("Step 2: Deleting bucket policy with users credentials")
        try:
            s3_policy_usr_obj.delete_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1185["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Deleting bucket policy with users "
                "credentials is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test Wildcard * in action for delete bucket policy with effect is Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6140")
    @CTFailOn(error_handler)
    def test_1186(self):
        """
        Test Wildcard * in action where effect is Allow"""
        LOGGER.info(
            "STARTED: Test Wildcard * in action where effect is Allow")
        bkt_cnf_1186=BKT_POLICY_CONF["test_1186"]
        bucket_name=bkt_cnf_1186["bucket_name"]
        user_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1186["bucket_policy"])
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info("Step 2: Deleting bucket policy with users credentials")
        resp=s3_policy_usr_obj.delete_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Bucket policy is deleted with users credentials")
        LOGGER.info(
            "Step 3: Verifying that bucket policy is deleted from a bucket {0}".format(bucket_name))
        try:
            S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1186["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Verified that policy is deleted from a bucket {0}".format(bucket_name))
        LOGGER.info(
            "ENDED: Test Wildcard * in action where effect is Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6142")
    @CTFailOn(error_handler)
    def test_1114(self):
        """
        Test bucket policy statement Effect "Allow" and "Deny" combinations using json"""
        LOGGER.info(
            "STARTED: Test bucket policy statement Effect Allow and Deny combinations using json")
        bkt_cnf_1114=BKT_POLICY_CONF["test_1114"]
        bucket_name=bkt_cnf_1114["bucket_name"]
        user_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1114["bucket_policy"])
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info(
            "Step 2: Retrieving bucket policy with users credentials")
        resp=s3_policy_usr_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Bucket policy is retrieved with users credentials")
        LOGGER.info(
            "Step 3: Applying bucket policy with users credentials")
        bkt_policy_json=json.dumps(bkt_cnf_1114["bucket_policy"])
        try:
            s3_policy_usr_obj.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1114["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Applying bucket policy with users "
                "credentials is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test bucket policy statement Effect Allow and Deny combinations using json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6144")
    @CTFailOn(error_handler)
    def test_1169(self):
        """
        Test * Wildcard for all s3apis in action field of
        statement of the json file with combination effect "Allow" and "Deny"
        """
        LOGGER.info(
            "STARTED: Test * Wildcard for all s3apis in action field of "
            "statement of the json file with combination effect Allow and Deny")
        bkt_cnf_1169=BKT_POLICY_CONF["test_1169"]
        bucket_name=bkt_cnf_1169["bucket_name"]
        user_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1169["bucket_policy"])
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info("Step 2: Applying bucket policy with users credentials")
        bkt_policy_json=json.dumps(bkt_cnf_1169["bucket_policy"])
        resp=s3_policy_usr_obj.put_bucket_policy(
            bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Bucket policy is applied with users credentials")
        LOGGER.info(
            "Step 3: Retrieving bucket policy with users credentials")
        try:
            s3_policy_usr_obj.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1169["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Retrieving bucket policy with users "
                "credentials is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test * Wildcard for all s3apis in action field of "
            "statement of the json file with combination effect Allow and Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6146")
    @CTFailOn(error_handler)
    def test_1167(self):
        """
        Test * Wildcard for all s3apis in action
        field of statement of the json file with effect "Deny"
        """
        LOGGER.info(
            "STARTED: Test * Wildcard for all s3apis in action field "
            "of statement of the json file with effect Deny")
        bkt_cnf_1167=BKT_POLICY_CONF["test_1167"]
        bucket_name=bkt_cnf_1167["bucket_name"]
        user_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1167["bucket_policy"])
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info(
            "Step 2: Retrieving bucket policy with users credentials")
        try:
            s3_policy_usr_obj.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1167["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Retrieving bucket policy with users "
                "credentials is failed with error {0}".format(
                    error.message))
        # Cleanup activity
        S3_BKT_POLICY_OBJ.delete_bucket_policy(bucket_name)
        LOGGER.info(
            "ENDED: Test * Wildcard for all s3apis in action field "
            "of statement of the json file with effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6147")
    @CTFailOn(error_handler)
    def test_1113(self):
        """
        Test bucket policy statement Effect "None" using json"""
        LOGGER.info(
            "STARTED: Test bucket policy statement Effect None using json")
        bkt_cnf_1113=BKT_POLICY_CONF["test_1113"]
        bucket_name=bkt_cnf_1113["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info(
            "Step 2: Applying policy on a bucket {0} with effect none".format(bucket_name))
        bkt_policy_json=json.dumps(bkt_cnf_1113["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1113["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Applying policy on a bucket with "
                "effect none is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Test bucket policy statement Effect None using json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6148")
    @CTFailOn(error_handler)
    def test_1116(self):
        """
        Test bucket policy statement Effect "Allow" ,
        "Deny" and "None" combinations using json"""
        LOGGER.info(
            "STARTED: Test bucket policy statement Effect Allow, "
            "Deny and None combinations using json")
        bkt_cnf_1116=BKT_POLICY_CONF["test_1116"]
        bucket_name=bkt_cnf_1116["bucket_name"]
        self.create_bucket_validate(bucket_name)
        LOGGER.info(
            "Step 2: Applying policy on a bucket {0}".format(bucket_name))
        bkt_policy_json=json.dumps(bkt_cnf_1116["bucket_policy"])
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1116["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Applying policy on a bucket is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: STARTED: Test bucket policy statement Effect Allow, "
            "Deny and None combinations using json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6012")
    @CTFailOn(error_handler)
    def test_1109(self):
        """
        Test bucket policy statement Effect "Allow" using json"""
        LOGGER.info(
            "STARTED: Test bucket policy statement Effect Allow using json")
        bkt_cnf_1109=BKT_POLICY_CONF["test_1109"]
        bucket_name=bkt_cnf_1109["bucket_name"]
        user_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["user_name"], str(
                time.time()))
        self.create_bucket_validate(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_cnf_1109["bucket_policy_1"])
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        LOGGER.info(
            "Step 2: Applying bucket policy with users credentials")
        bkt_policy_json=json.dumps(bkt_cnf_1109["bucket_policy_2"])
        resp=s3_policy_usr_obj.put_bucket_policy(
            bucket_name, bkt_policy_json)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Policy is applied to a bucket {0} with users credentials".format(bucket_name))
        LOGGER.info(
            "Step 3: Retrieving policy of a bucket with users credentials")
        try:
            s3_policy_usr_obj.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_cnf_1109["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Retrieving bucket policy with users "
                "credentials is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "Step 4: Retrieving policy of a bucket with accounts credentials")
        resp=S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["Policy"], bkt_policy_json, resp[1])
        LOGGER.info(
            "Step 4: Retrieved policy of a bucket with accounts credentials")
        LOGGER.info(
            "ENDED: Test bucket policy statement Effect Allow using json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7692")
    @CTFailOn(error_handler)
    def test_270(self):
        """
        verify get-bucket-policy for the bucket which is having read permissions for account2
        """
        LOGGER.info(
            "STARTED: verify get-bucket-policy for the bucket which is having read permissions for account2")
        test_cfg=BKT_POLICY_CONF["test_270"]
        LOGGER.info(
            "Creating two account with name prefix as {}".format(
                test_cfg["account_name"]))
        resp=IAM_OBJ.create_multiple_accounts(
            test_cfg["acc_count"], test_cfg["account_name"])
        assert resp[0], resp[1]
        canonical_id_user_1=resp[1][0][1]["canonical_id"]
        access_key_u1=resp[1][0][1]["access_key"]
        secret_key_u1=resp[1][0][1]["secret_key"]
        canonical_id_user_2=resp[1][1][1]["canonical_id"]
        access_key_u2=resp[1][1][1]["access_key"]
        secret_key_u2=resp[1][1][1]["secret_key"]
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        s3acltest_obj_1=s3_acl_test_lib.S3AclTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.s3test_obj_1=s3_test_lib.S3TestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        LOGGER.info(
            "Created account2 with name {}".format(test_cfg["account_name"]))
        LOGGER.info("Step 1 : Creating bucket with name {} and setting read "
                    "permission to account2".format(test_cfg["bucket_name"]))
        resp=s3acltest_obj_1.create_bucket_with_acl(
            bucket_name=test_cfg["bucket_name"],
            grant_full_control=test_cfg["id_str"].format(canonical_id_user_1),
            grant_read=test_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Created bucket with name {} and set read "
                    "permission to account2".format(test_cfg["bucket_name"]))
        LOGGER.info(
            "Step 2: Verifying get bucket acl with account1")
        resp=s3acltest_obj_1.get_bucket_acl(test_cfg["bucket_name"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Verified get bucket acl for account1")
        LOGGER.info(
            "Step 3: Applying bucket policy: {}".format(
                test_cfg["bucket_policy"]))
        bkt_policy_json=json.dumps(test_cfg["bucket_policy"])
        resp=s3_policy_usr_obj.put_bucket_policy(
            test_cfg["bucket_name"], bkt_policy_json)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Applied bucket policy to {}".format(
                test_cfg["bucket_name"]))
        LOGGER.info(
            "Step 4: Get bucket policy using account1")
        resp=s3_policy_usr_obj.get_bucket_policy(test_cfg["bucket_name"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Verified get bucket policy for account1")
        LOGGER.info(
            "Step 5: Get bucket policy using account2")
        s3_policy_usr2_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_u2, secret_key=secret_key_u2)
        try:
            s3_policy_usr2_obj.get_bucket_policy(test_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 5: Get bucket policy with account2 login is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: verify get-bucket-policy for the bucket which is having read permissions for account2")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7693")
    @CTFailOn(error_handler)
    def test_271(self):
        """
        Do not apply policy from account 1 and give read permission to account2 and verify get-bucket-policy
        """
        LOGGER.info(
            "STARTED: Do not apply policy from account 1 and give read permission to account2"
            " and verify get-bucket-policy")
        test_cfg=BKT_POLICY_CONF["test_270"]
        LOGGER.info(
            "Creating two account with name prefix as {}".format(
                test_cfg["account_name"]))
        resp=IAM_OBJ.create_multiple_accounts(
            test_cfg["acc_count"], test_cfg["account_name"])
        assert resp[0], resp[1]
        canonical_id_user_1=resp[1][0][1]["canonical_id"]
        access_key_u1=resp[1][0][1]["access_key"]
        secret_key_u1=resp[1][0][1]["secret_key"]
        canonical_id_user_2=resp[1][1][1]["canonical_id"]
        access_key_u2=resp[1][1][1]["access_key"]
        secret_key_u2=resp[1][1][1]["secret_key"]
        s3acltest_obj_1=s3_acl_test_lib.S3AclTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.s3test_obj_1=s3_test_lib.S3TestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        LOGGER.info(
            "Created account2 with name {}".format(test_cfg["account_name"]))
        LOGGER.info("Step 1 : Creating bucket with name {} and setting read "
                    "permission to account2".format(test_cfg["bucket_name"]))
        resp=s3acltest_obj_1.create_bucket_with_acl(
            bucket_name=test_cfg["bucket_name"],
            grant_full_control=test_cfg["id_str"].format(canonical_id_user_1),
            grant_read=test_cfg["id_str"].format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Created bucket with name {} and set read "
                    "permission to account2".format(test_cfg["bucket_name"]))
        LOGGER.info(
            "Step 2: Verifying get bucket acl with account1")
        resp=s3acltest_obj_1.get_bucket_acl(test_cfg["bucket_name"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Verified get bucket acl for account1")
        LOGGER.info(
            "Step 3: Get bucket policy using account2")
        s3_policy_usr2_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_u2, secret_key=secret_key_u2)
        try:
            s3_policy_usr2_obj.get_bucket_policy(test_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: Get bucket policy with account2 login is failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Do not apply policy from account 1 and give read permission to account2"
            " and verify get-bucket-policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5974")
    @CTFailOn(error_handler)
    def test_4156(self):
        """
        Create Bucket Policy using StringEquals Condition Operator, key "s3:prefix" and Effect Allow
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringEquals "
            "Condition Operator, key 's3:prefix' and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4156_cfg=BKT_POLICY_CONF["test_4156"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        self.create_bucket_put_objects(
            test_4156_cfg["bucket_name"],
            test_4156_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3_obj=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        test_4156_cfg["bucket_policy"]["Id"]=test_4156_cfg["bucket_policy"]["Id"].format(
            policy_id)
        test_4156_cfg["bucket_policy"]["Statement"][0]["Sid"]= \
            test_4156_cfg["bucket_policy"]["Statement"][0]["Sid"].format(
                policy_sid)
        test_4156_cfg["bucket_policy"]["Statement"][0]["Principal"]["AWS"]=test_4156_cfg[
            "bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(account_id)
        LOGGER.info(test_4156_cfg["bucket_policy"])
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            test_4156_cfg["bucket_name"],
            test_4156_cfg["bucket_policy"])
        LOGGER.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                test_4156_cfg["bucket_name"],
                bkt_policy_cfg["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4156_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Listing object with prefix using another account failed with {0}".format(
                test_4156_cfg["err_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringEquals "
            "Condition Operator, key 's3:prefix' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5972")
    @CTFailOn(error_handler)
    def test_4161(self):
        """
        Create Bucket Policy using StringNotEquals Condition
        Operator, key "s3:prefix" and Effect Deny
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringNotEquals Condition Operator,"
            " key 's3:prefix' and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4161_cfg=BKT_POLICY_CONF["test_4161"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        self.create_bucket_put_objects(
            test_4161_cfg["bucket_name"],
            test_4161_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3_obj=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        test_4161_cfg["bucket_policy"]["Id"]=test_4161_cfg["bucket_policy"]["Id"].format(
            policy_id)
        test_4161_cfg["bucket_policy"]["Statement"][0]["Sid"]= \
            test_4161_cfg["bucket_policy"]["Statement"][0]["Sid"].format(
                policy_sid)
        test_4161_cfg["bucket_policy"]["Statement"][0]["Principal"]["AWS"]=test_4161_cfg[
            "bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(account_id)
        LOGGER.info(test_4161_cfg["bucket_policy"])
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            test_4161_cfg["bucket_name"],
            test_4161_cfg["bucket_policy"])
        LOGGER.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                test_4161_cfg["bucket_name"],
                bkt_policy_cfg["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4161_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Listing object with prefix using another account failed with {0}".format(
                test_4161_cfg["err_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringNotEquals "
            "Condition Operator, key 's3:prefix' and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5957")
    @CTFailOn(error_handler)
    def test_4173(self):
        """
        Create Bucket Policy using StringEquals Condition Operator, key "s3:prefix" and Effect Deny
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringEquals"
            " Condition Operator, key 's3:prefix' and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4173_cfg=BKT_POLICY_CONF["test_4173"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        self.create_bucket_put_objects(
            test_4173_cfg["bucket_name"],
            test_4173_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3_obj=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        test_4173_cfg["bucket_policy"]["Id"]=test_4173_cfg["bucket_policy"]["Id"].format(
            policy_id)
        test_4173_cfg["bucket_policy"]["Statement"][0]["Sid"]= \
            test_4173_cfg["bucket_policy"]["Statement"][0]["Sid"].format(
                policy_sid)
        test_4173_cfg["bucket_policy"]["Statement"][0]["Principal"]["AWS"]=test_4173_cfg[
            "bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(account_id)
        LOGGER.info(test_4173_cfg["bucket_policy"])
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            test_4173_cfg["bucket_name"],
            test_4173_cfg["bucket_policy"])
        LOGGER.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                test_4173_cfg["bucket_name"],
                bkt_policy_cfg["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4173_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Listing object with prefix using another account failed with {0}".format(
                test_4173_cfg["err_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringEquals "
            "Condition Operator, key 's3:prefix' and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5969")
    @CTFailOn(error_handler)
    def test_4170(self):
        """
        Create Bucket Policy using StringNotEquals
        Condition Operator, key "s3:prefix" and Effect Allow
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringNotEquals Condition Operator,"
            " key 's3:prefix' and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4170_cfg=BKT_POLICY_CONF["test_4170"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        self.create_bucket_put_objects(
            test_4170_cfg["bucket_name"],
            test_4170_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3_obj=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        test_4170_cfg["bucket_policy"]["Id"]=test_4170_cfg["bucket_policy"]["Id"].format(
            policy_id)
        test_4170_cfg["bucket_policy"]["Statement"][0]["Sid"]= \
            test_4170_cfg["bucket_policy"]["Statement"][0]["Sid"].format(
                policy_sid)
        test_4170_cfg["bucket_policy"]["Statement"][0]["Principal"]["AWS"]=test_4170_cfg[
            "bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(account_id)
        LOGGER.info(test_4170_cfg["bucket_policy"])
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            test_4170_cfg["bucket_name"],
            test_4170_cfg["bucket_policy"])
        LOGGER.info("Listing object with prefix using another account")
        try:
            s3_obj.list_objects_with_prefix(
                test_4170_cfg["bucket_name"],
                bkt_policy_cfg["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4170_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Listing object with prefix using another account failed with {0}".format(
                test_4170_cfg["err_message"]))
        LOGGER.info("Listing object using another account")
        try:
            s3_obj.object_list(test_4170_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4170_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Listing object using another account failed with {0}".format(
                test_4170_cfg["err_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringNotEquals Condition Operator,"
            " key 's3:prefix' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5955")
    @CTFailOn(error_handler)
    def test_4183(self):
        """
        Create Bucket Policy using "StringEquals" Condition Operator,
        key "s3:x-amz-grant-write",Effect Allow and Action "s3:ListBucket"
        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using 'StringEquals' Condition Operator,"
            " key 's3:x-amz-grant-write',Effect Allow and Action 's3:ListBucket'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4183_cfg=BKT_POLICY_CONF["test_4183"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        self.create_bucket_put_objects(
            test_4183_cfg["bucket_name"],
            test_4183_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3_obj=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        test_4183_cfg["bucket_policy"]["Id"]=test_4183_cfg["bucket_policy"]["Id"].format(
            policy_id)
        test_4183_cfg["bucket_policy"]["Statement"][0]["Sid"]=test_4183_cfg["bucket_policy"]["Statement"][0][
            "Sid"].format(
            policy_sid)
        test_4183_cfg["bucket_policy"]["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-write"]= \
            test_4183_cfg[
            "bucket_policy"]["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-write"].format(account_id)
        LOGGER.info(test_4183_cfg["bucket_policy"])
        LOGGER.info("Created a json for bucket policy")
        LOGGER.info(
            "Applying a policy to a bucket {0}".format(
                test_4183_cfg["bucket_name"]))
        self.put_invalid_policy(
            test_4183_cfg["bucket_name"],
            test_4183_cfg["bucket_policy"],
            test_4183_cfg["err_message"])
        LOGGER.info(
            "Applying a policy to a bucket {0} failed with {1}".format(
                test_4183_cfg["bucket_name"], test_4183_cfg["err_message"]))
        LOGGER.info(
            "ENDED: Create Bucket Policy using 'StringEquals' Condition Operator,"
            " key 's3:x-amz-grant-write',Effect Allow and Action 's3:ListBucket'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6027")
    @CTFailOn(error_handler)
    def test_1069(self):
        """
        Test invalid Account ID in the bucket policy json
        """
        LOGGER.info(
            "STARTED: Test invalid Account ID in the bucket policy json")
        bkt_cnf_1069=BKT_POLICY_CONF["test_1069"]
        bucket_name=bkt_cnf_1069["bucket_name"]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_1069["object_name_2"])
        self.put_invalid_policy(
            bucket_name,
            bkt_cnf_1069["bucket_policy"],
            bkt_cnf_1069["error_message"])
        LOGGER.info(
            "ENDED: Test invalid Account ID in the bucket policy json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6025")
    @CTFailOn(error_handler)
    def test_1075(self):
        """
        Test invalid User name in the bucket policy json
        """
        LOGGER.info(
            "STARTED: Test invalid User name in the bucket policy json")
        bkt_cnf_1075=BKT_POLICY_CONF["test_1075"]
        bucket_name=bkt_cnf_1075["bucket_name"]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"],
            bkt_cnf_1075["object_name_2"])
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        bkt_cnf_1075["bucket_policy"]["Statement"][0]["Principal"]["AWS"]=bkt_cnf_1075[
            "bucket_policy"]["Statement"][0]["Principal"]["AWS"].format(account_id)
        self.put_invalid_policy(
            bucket_name,
            bkt_cnf_1075["bucket_policy"],
            bkt_cnf_1075["error_message"])
        LOGGER.info(
            "ENDED: Test invalid User name in the bucket policy json")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7694")
    @CTFailOn(error_handler)
    def test_4502(self):
        """
        Test Bucket Policy using Condition Operator "DateEquals", key "aws:CurrentTime",
        Effect "Allow", Action "PutObject" and Date format._date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_4502_cfg=BKT_POLICY_CONF["test_4502"]
        date_time=date.today().strftime(test_4502_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_4502_cfg["account_name"].format(random_id),
            test_4502_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_4502_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4502_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7695")
    @CTFailOn(error_handler)
    def test_4504(self):
        """
        Test Bucket Policy using Condition Operator 'DateNotEquals',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_4504_cfg=BKT_POLICY_CONF["test_4504"]
        date_time=datetime.now().strftime(test_4504_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_4504_cfg["account_name"].format(random_id),
            test_4504_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_4504_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4504_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7696")
    @CTFailOn(error_handler)
    def test_4505(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_4505_cfg=BKT_POLICY_CONF["test_4505"]
        date_time=datetime.now().strftime(test_4505_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_4505_cfg["account_name"].format(random_id),
            test_4505_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_4505_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4505_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7697")
    @CTFailOn(error_handler)
    def test_4506(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanEquals',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_4506_cfg=BKT_POLICY_CONF["test_4506"]
        date_time=datetime.now().strftime(test_4506_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_4506_cfg["account_name"].format(random_id),
            test_4506_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_4506_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(account_id, date_time, effect,
                                                 s3_obj_2, test_4506_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7698")
    @CTFailOn(error_handler)
    def test_4507(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_4507_cfg=BKT_POLICY_CONF["test_4507"]
        date_time=datetime.now().strftime(test_4507_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_4507_cfg["account_name"].format(random_id),
            test_4507_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_4507_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4507_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7699")
    @CTFailOn(error_handler)
    def test_4508(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_4508_cfg=BKT_POLICY_CONF["test_4508"]
        date_time=datetime.now().strftime(test_4508_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_4508_cfg["account_name"].format(random_id),
            test_4508_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_4508_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_4508_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7700")
    @CTFailOn(error_handler)
    def test_4509(self):
        """
        Test Bucket Policy using Condition Operator "DateEquals", key "aws:CurrentTime",
        Effect "Allow", Action "PutObject" and Date format._date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4509"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateEquals', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7701")
    @CTFailOn(error_handler)
    def test_4510(self):
        """
        Test Bucket Policy using Condition Operator 'DateNotEquals',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4510"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7702")
    @CTFailOn(error_handler)
    def test_4511(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4511"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7703")
    @CTFailOn(error_handler)
    def test_4512(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThan',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4512"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7704")
    @CTFailOn(error_handler)
    def test_4513(self):
        """
        Test Bucket Policy using Condition Operator 'DateNotEquals',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4513"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, random_id, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEquals', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7705")
    @CTFailOn(error_handler)
    def test_4514(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThan',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4514"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, random_id, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7706")
    @CTFailOn(error_handler)
    def test_4515(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanEquals',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")
        random_id=str(time.time())
        date_time=str(time.time()).split(".")[0]
        test_cfg=BKT_POLICY_CONF["test_4515"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7707")
    @CTFailOn(error_handler)
    def test_4516(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThan',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format
_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_4507"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, random_id, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThan', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7708")
    @CTFailOn(error_handler)
    def test_4517(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
        "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format
_date
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")
        random_id=str(time.time())
        date_time=time.time()
        test_cfg=BKT_POLICY_CONF["test_4508"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        for effect in test_cfg["effect_lst"]:
            self.put_bkt_policy_with_date_format(
                account_id, date_time, effect, s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEquals', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject' and Date format")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6929")
    @CTFailOn(error_handler)
    def test_5770(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5770"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    # Commented as test is invalid in x-ray
    # def test_5781(self):
    #     """
    #     Test Bucket Policy using Condition Operator 'DateEqualsIfExists',
    #     key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.
    #     :avocado: tags=bucket_policy_date_if_exists
    #     """
    #     LOGGER.info(
    #         "STARTED: Test Bucket Policy using Condition Operator 'DateEqualsIfExists', "
    #         "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
    #     random_id = str(time.time())
    #     test_cfg = BKT_POLICY_CONF["test_5781"]
    #     date_time = date.today().strftime(test_cfg["date_format"])
    #     result = self.create_s3iamcli_acc(
    #         test_cfg["account_name"].format(random_id),
    #         test_cfg["email_id"].format(random_id))
    #     s3_obj_2 = result[1]
    #     account_id = result[6]
    #     resp = create_file(
    #         BKT_POLICY_CONF["bucket_policy"]["file_path"],
    #         BKT_POLICY_CONF["bucket_policy"]["file_size"])
    #     assert resp[0], resp[1]
    #     for effect in test_cfg["effect_lst"]:
    #         self.put_bkt_policy_with_date_format(
    #             account_id, date_time, effect, s3_obj_2, test_cfg)
    #     LOGGER.info(
    #         "ENDED: Test Bucket Policy using Condition Operator 'DateEqualsIfExists', "
    #         "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6930")
    @CTFailOn(error_handler)
    def test_5831(self):
        """
        Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists',
        key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")
        random_id=str(time.time())
        date_time=str(time.time()).split(".")[0]
        test_cfg=BKT_POLICY_CONF["test_5831"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6931")
    @CTFailOn(error_handler)
    def test_5832(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanIfExists',
        key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")
        random_id=str(time.time())
        date_time=str(time.time()).split(".")[0]
        test_cfg=BKT_POLICY_CONF["test_5832"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny' and Action 'PutObject'.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6932")
    @CTFailOn(error_handler)
    def test_5778(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5778"]
        date_time=datetime.now().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6933")
    @CTFailOn(error_handler)
    def test_5740(self):
        """
        Test Bucket Policy using Condition Operator 'DateEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5740"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6934")
    @CTFailOn(error_handler)
    def test_5751(self):
        """
        Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5751"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6935")
    @CTFailOn(error_handler)
    def test_5773(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanIfExist',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanIfExist', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5773"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanIfExist', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    # Commented as test is marked invalid in x-ray
    # def test_5796(self):
    #     """
    #     Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists',
    #     key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.
    #     :avocado: tags=bucket_policy_date_if_exists
    #     """
    #     LOGGER.info(
    #         "STARTED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
    #         "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
    #     random_id = str(time.time())
    #     test_cfg = BKT_POLICY_CONF["test_5796"]
    #     date_time = date.today().strftime(test_cfg["date_format"])
    #     result = self.create_s3iamcli_acc(
    #         test_cfg["account_name"].format(random_id),
    #         test_cfg["email_id"].format(random_id))
    #     s3_obj_2 = result[1]
    #     account_id = result[6]
    #     resp = create_file(
    #         BKT_POLICY_CONF["bucket_policy"]["file_path"],
    #         BKT_POLICY_CONF["bucket_policy"]["file_size"])
    #     assert resp[0], resp[1]
    #     for effect in test_cfg["effect_lst"]:
    #         self.put_bkt_policy_with_date_format(
    #             account_id, date_time, effect, s3_obj_2, test_cfg)
    #     LOGGER.info(
    #         "ENDED: Test Bucket Policy using Condition Operator 'DateNotEqualsIfExists', "
    #         "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6938")
    @CTFailOn(error_handler)
    def test_5764(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists',
        key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5764"]
        date_time_res=datetime.now() + timedelta(test_cfg["delta_time"])
        date_time=date_time_res.strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]

        bkt_json_policy=eval(json.dumps(test_cfg["bucket_policy"]))
        dt_condition=bkt_json_policy["Statement"][0]["Condition"]
        condition_key=list(
            dt_condition[test_cfg["date_condition"]].keys())[0]
        bkt_json_policy["Statement"][0]["Principal"]["AWS"]=account_id
        bkt_json_policy["Statement"][0]["Condition"][test_cfg["date_condition"]
                                                     ][condition_key]=date_time
        bucket_name=test_cfg["bucket_name"]
        bkt_json_policy["Statement"][0]["Resource"]=bkt_json_policy["Statement"][0]["Resource"].format(
            bucket_name)
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.put_get_bkt_policy(bucket_name, bkt_json_policy)
        resp=s3_obj_2.put_object(
            bucket_name, test_cfg["object_name"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Uploading object to s3 bucket with second account")
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    # Commented as test is marked invalid in x-ray
    #
    # def test_5830(self):
    #     """
    #     Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists',
    #     key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.
    #     :avocado: tags=bucket_policy_date_if_exists
    #     """
    #     LOGGER.info(
    #         "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
    #         "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")
    #     random_id = str(time.time())
    #     test_cfg = BKT_POLICY_CONF["test_5830"]
    #     date_time = date.today().strftime(test_cfg["date_format"])
    #     result = self.create_s3iamcli_acc(
    #         test_cfg["account_name"].format(random_id),
    #         test_cfg["email_id"].format(random_id))
    #     s3_obj_2 = result[1]
    #     account_id = result[6]
    #     resp = create_file(
    #         BKT_POLICY_CONF["bucket_policy"]["file_path"],
    #         BKT_POLICY_CONF["bucket_policy"]["file_size"])
    #     assert resp[0], resp[1]
    #     for effect in test_cfg["effect_lst"]:
    #         self.put_bkt_policy_with_date_format(
    #             account_id, date_time, effect, s3_obj_2, test_cfg)
    #     LOGGER.info(
    #         "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
    #         "key 'aws:CurrentTime', Effect 'Allow', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6939")
    @CTFailOn(error_handler)
    def test_5758(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanIfExists',
        key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5758"]
        date_time=date.today().strftime(test_cfg["date_format"])
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanIfExists', "
            "key 'aws:CurrentTime', Effect 'Deny', Action 'PutObject' and Date format.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6940")
    @CTFailOn(error_handler)
    def test_5925(self):
        """
        Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists',
        key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_5925"]
        date_time_res=datetime.now() + timedelta(test_cfg["year"])
        date_time=int(date_time_res.timestamp())
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        self.create_bucket_validate(bucket_name)
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        LOGGER.info(
            "Creating a json with DateLessThanEqualsIfExists condition")
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Condition"]["DateLessThanEqualsIfExists"]["aws:EpochTime"]=bucket_policy["Statement"][0]["Condition"]["DateLessThanEqualsIfExists"]["aws:EpochTime"].format(
                date_time)
        LOGGER.info(
            "Created a json with DateLessThanEqualsIfExists condition")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Uploading an object from account 2")
        create_file(BKT_POLICY_CONF["bucket_policy"]["file_path"],
                    BKT_POLICY_CONF["bucket_policy"]["file_size"])
        resp=s3_obj_2.put_object(
            bucket_name,
            test_cfg["object_name"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded from account 2")
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateLessThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6971")
    @CTFailOn(error_handler)
    def test_5926(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists',
        key 'aws:EpochTime', Effect 'Deny', Action 'PutObject'.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject'.")
        random_id=str(time.time())
        date_time=str(time.time()).split(".")[0]
        test_cfg=BKT_POLICY_CONF["test_5926"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanIfExists', "
            "key 'aws:EpochTime', Effect 'Deny', Action 'PutObject'.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6972")
    @CTFailOn(error_handler)
    def test_5937(self):
        """
        Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists',
        key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")
        random_id=str(time.time())
        date_time=str(time.time()).split(".")[0]
        test_cfg=BKT_POLICY_CONF["test_5937"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["email_id"].format(random_id))
        s3_obj_2=result[1]
        account_id=result[6]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        self.put_bkt_policy_with_date_format(
            account_id, date_time, test_cfg["effect"], s3_obj_2, test_cfg)
        LOGGER.info(
            "ENDED: Test Bucket Policy using Condition Operator 'DateGreaterThanEqualsIfExists', "
            "key 'aws:EpochTime', Effect 'Allow', Action 'PutObject'.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7709")
    @CTFailOn(error_handler)
    def test_1902(self):
        """
        Create Bucket Policy using "StringEquals" Condition Operator,
        key "s3:x-amz-acl" and value "public-read"

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value public-read")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_1902"]
        bucket_name=test_cfg["bucket_name"].format(random_id)
        obj_name=test_cfg["object_name"]

        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        S3_OBJ_2=result[1]
        ACL_OBJ_2=result[2]
        account_id=result[6]
        resp=S3_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        bkt_json_policy=eval(json.dumps(test_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"]=account_id
        bkt_json_policy["Statement"][0]["Resource"]=bkt_json_policy["Statement"][0]["Resource"].format(
            bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_json_policy)
        LOGGER.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp=ACL_OBJ_2.put_object_with_acl(
            bucket_name,
            test_cfg["object_name_2"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            acl=test_cfg["obj_permission"])
        assert resp[0], resp[1]
        try:
            S3_OBJ_2.put_object(
                bucket_name,
                test_cfg["object_name_2"],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 1: Uploading object to a bucket failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value public-read")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7710")
    @CTFailOn(error_handler)
    def test_1903(self):
        """
        Create Bucket Policy using "StringEquals" Condition Operator,
        key "s3:x-amz-acl" and value "bucket-owner-full-control"

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value bucket-owner-full-control")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_1903"]
        bucket_name=test_cfg["bucket_name"].format(random_id)
        obj_name=test_cfg["object_name"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        S3_OBJ_2=result[1]
        ACL_OBJ_2=result[2]
        account_id=result[6]
        resp=S3_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        bkt_json_policy=eval(json.dumps(test_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"]=account_id
        bkt_json_policy["Statement"][0]["Resource"]= \
            bkt_json_policy["Statement"][0]["Resource"].format(bucket_name)
        self.put_get_bkt_policy(bucket_name, bkt_json_policy)
        LOGGER.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp=ACL_OBJ_2.put_object_with_acl(
            bucket_name,
            test_cfg["object_name_2"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            acl=test_cfg["obj_permission"])
        assert resp[0], resp[1]
        try:
            S3_OBJ_2.put_object(
                bucket_name,
                test_cfg["object_name_2"],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 1: Uploading object to a bucket failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Create Bucket Policy using StringEquals Condition Operator, "
            "key 's3:x-amz-acl' and value bucket-owner-full-control")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7711")
    @CTFailOn(error_handler)
    def test_1904(self):
        """
        Create Bucket Policy using 'StringEquals' Condition Operator,
        key 's3:x-amz-grant-full-control'

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-full-control'")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_1904"]
        bucket_name=test_cfg["bucket_name"].format(random_id)
        obj_name=test_cfg["object_name"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        S3_OBJ_2=result[1]
        ACL_OBJ_2=result[2]
        account_id_2=result[6]
        canonical_id_2=result[0]
        resp=S3_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        bkt_json_policy=eval(json.dumps(test_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"]=account_id_2
        bkt_json_policy["Statement"][0]["Resource"]= \
            bkt_json_policy["Statement"][0]["Resource"].format(bucket_name)
        bkt_json_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"]= \
            bkt_json_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"].format(
                canonical_id_2)
        self.put_get_bkt_policy(bucket_name, bkt_json_policy)
        LOGGER.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp=ACL_OBJ_2.put_object_with_acl(
            bucket_name,
            test_cfg["object_name_2"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            grant_full_control=test_cfg["id_str"].format(canonical_id_2))
        assert resp[0], resp[1]
        try:
            S3_OBJ_2.put_object(
                bucket_name,
                test_cfg["object_name_2"],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 1: Uploading object to a bucket failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-full-control'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7712")
    @CTFailOn(error_handler)
    def test_1908(self):
        """
        Create Bucket Policy using 'StringEquals' Condition Operator,
        key 's3:x-amz-grant-write-acp''

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-write-acp'")
        random_id=str(time.time())
        test_cfg=BKT_POLICY_CONF["test_1908"]
        bucket_name=test_cfg["bucket_name"].format(random_id)
        obj_name=test_cfg["object_name"]
        result=self.create_s3iamcli_acc(
            test_cfg["account_name"].format(random_id),
            test_cfg["emailid"].format(random_id))
        S3_OBJ_2=result[1]
        ACL_OBJ_2=result[2]
        account_id_2=result[6]
        canonical_id_2=result[0]
        resp=S3_OBJ.create_bucket_put_object(
            bucket_name,
            obj_name,
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        bkt_json_policy=eval(json.dumps(test_cfg["bucket_policy"]))
        bkt_json_policy["Statement"][0]["Principal"]["AWS"]=account_id_2
        bkt_json_policy["Statement"][0]["Resource"]= \
            bkt_json_policy["Statement"][0]["Resource"].format(bucket_name)
        bkt_json_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-write-acp"]= \
            bkt_json_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-write-acp"].format(
                canonical_id_2)
        self.put_get_bkt_policy(bucket_name, bkt_json_policy)
        LOGGER.info(
            "Step 1: Upload object using second account account with "
            "and without acl permission")
        resp=ACL_OBJ_2.put_object_with_acl(
            bucket_name,
            test_cfg["object_name_2"],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            grant_write_acp=test_cfg["id_str"].format(canonical_id_2))
        assert resp[0], resp[1]
        try:
            S3_OBJ_2.put_object(
                bucket_name,
                test_cfg["object_name_2"],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 1: Uploading object to a bucket failed with error {0}".format(
                    error.message))
        LOGGER.info(
            "ENDED: Create Bucket Policy using 'StringEquals' Condition Operator, "
            "key 's3:x-amz-grant-write-acp'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6979")
    @CTFailOn(error_handler)
    def test_4937(self):
        """
        Create Bucket Policy using NumericLessThanIfExists Condition, key "s3:max-keys" and Effect Allow

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4937_cfg=BKT_POLICY_CONF["test_4937"]
        bucket_name=test_4937_cfg["bucket_name"]
        bucket_policy=test_4937_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4937_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4937_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4937_cfg["max_keys"]
        err_message=test_4937_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ1)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[3])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6980")
    @CTFailOn(error_handler)
    def test_4939(self):
        """
        Create Bucket Policy using NumericLessThanIfExists Condition, key "s3:max-keys" and Effect Deny

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4939_cfg=BKT_POLICY_CONF["test_4939"]
        bucket_name=test_4939_cfg["bucket_name"]
        bucket_policy=test_4939_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4939_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4939_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(
            bucket_name,
            bucket_policy)
        max_key_list=test_4939_cfg["max_keys"]
        err_message=test_4939_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[3])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6981")
    @CTFailOn(error_handler)
    def test_4940(self):
        """
        Create Bucket Policy using NumericGreaterThanIfExists Condition, key "s3:max-keys" and Effect Allow

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4940_cfg=BKT_POLICY_CONF["test_4940"]
        bucket_name=test_4940_cfg["bucket_name"]
        bucket_policy=test_4940_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4940_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4940_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4940_cfg["max_keys"]
        err_message=test_4940_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[2], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[3])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ1)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[3])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6982")
    @CTFailOn(error_handler)
    def test_4941(self):
        """
        Create Bucket Policy using NumericGreaterThanIfExists Condition, key "s3:max-keys" and Effect Deny

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4941_cfg=BKT_POLICY_CONF["test_4941"]
        bucket_name=test_4941_cfg["bucket_name"]
        bucket_policy=test_4941_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4941_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4941_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4941_cfg["max_keys"]
        err_message=test_4941_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[3])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6983")
    @CTFailOn(error_handler)
    def test_4942(self):
        """
        Create Bucket Policy using NumericEquals Condition Operator, key "s3:max-keys" and Effect Allow

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericEquals"
            " Condition Operator, key 's3:max-keys' and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4942_cfg=BKT_POLICY_CONF["test_4942"]
        bucket_name=test_4942_cfg["bucket_name"]
        bucket_policy=test_4942_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4942_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4942_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4942_cfg["max_keys"]
        err_message=test_4942_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[2])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ1)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[2])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericEquals"
            " Condition Operator, key 's3:max-keys' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6984")
    @CTFailOn(error_handler)
    def test_4943(self):
        """
        Create Bucket Policy using NumericNotEqualsIfExists Condition,
         key "s3:max-keys" and Effect Deny

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericNotEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4943_cfg=BKT_POLICY_CONF["test_4943"]
        bucket_name=test_4943_cfg["bucket_name"]
        bucket_policy=test_4943_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4943_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4943_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4943_cfg["max_keys"]
        err_message=test_4943_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[2])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericNotEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6985")
    @CTFailOn(error_handler)
    def test_4944(self):
        """
        Create Bucket Policy using NumericLessThanEqualsIfExists
         Condition, key "s3:max-keys" and Effect Allow

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericLessThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4944_cfg=BKT_POLICY_CONF["test_4944"]
        bucket_name=test_4944_cfg["bucket_name"]
        bucket_policy=test_4944_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4944_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4944_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4944_cfg["max_keys"]
        err_message=test_4944_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[2])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ1)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[2])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericLessThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6986")
    @CTFailOn(error_handler)
    def test_4945(self):
        """
        Create Bucket Policy using NumericGreaterThanEqualsIfExists Condition, key "s3:max-keys" and Effect Deny

        """
        LOGGER.info(
            "STARTED: Create Bucket Policy using NumericGreaterThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_4945_cfg=BKT_POLICY_CONF["test_4945"]
        bucket_name=test_4945_cfg["bucket_name"]
        bucket_policy=test_4945_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name,
            test_4945_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_4945_cfg["iam_acc_count"],
            name_prefix=bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info("Creating a json for bucket policy")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account1_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        max_key_list=test_4945_cfg["max_keys"]
        err_message=test_4945_cfg["err_message"]
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ1, max_key_list[3], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ1, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[0], err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ2, max_key_list[2], err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[0])
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ, max_key_list[2])
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        LOGGER.info(
            "ENDED: Create Bucket Policy using NumericGreaterThanEqualsIfExists"
            " Condition, key 's3:max-keys' and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6973")
    @CTFailOn(error_handler)
    def test_5449(self):
        """
        Test Create Bucket Policy using StringEqualsIfExists
        Condition, key "s3:prefix" and Effect Allow

        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition, key s3:prefix and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5449_cfg=BKT_POLICY_CONF["test_5449"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_5449_cfg["bucket_name"]
        err_message=test_5449_cfg["error_message"]
        bucket_policy=test_5449_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name, test_5449_cfg["obj_count"], obj_prefix)
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_5449_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account1_id)
        LOGGER.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ, obj_prefix)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ1, obj_prefix)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ1)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIfExists"
            " Condition, key s3:prefix and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6974")
    @CTFailOn(error_handler)
    def test_5471(self):
        """
        Test Create Bucket Policy using StringNotEqualsIfExists
        Condition Operator, key "s3:prefix" and Effect Deny

        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5471_cfg=BKT_POLICY_CONF["test_5471"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_5471_cfg["bucket_name"]
        err_message=test_5471_cfg["error_message"]
        bucket_policy=test_5471_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name, test_5471_cfg["obj_count"], obj_prefix)
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_5471_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]= \
            bucket_policy["Statement"][0][
                "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account1_id)
        LOGGER.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ, obj_prefix)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ1,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ1, err_message)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6975")
    @CTFailOn(error_handler)
    def test_5473(self):
        """
        Test Create Bucket Policy using StringNotEqualsIfExists
        Condition Operator, key "s3:prefix" and Effect Allow

        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Allow")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5473_cfg=BKT_POLICY_CONF["test_5473"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_5473_cfg["bucket_name"]
        err_message=test_5473_cfg["error_message"]
        bucket_policy=test_5473_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name, test_5473_cfg["obj_count"], obj_prefix)
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_5473_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account1_id)
        LOGGER.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ, obj_prefix)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ1,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ1)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringNotEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6976")
    @CTFailOn(error_handler)
    def test_5481(self):
        """
        Test Create Bucket Policy using StringEqualsIfExists
        Condition Operator, key "s3:prefix" and Effect Deny

        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5481_cfg=BKT_POLICY_CONF["test_5481"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_5481_cfg["bucket_name"]
        err_message=test_5481_cfg["error_message"]
        bucket_policy=test_5481_cfg["bucket_policy"]
        self.create_bucket_put_objects(
            bucket_name, test_5481_cfg["obj_count"], obj_prefix)
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_5481_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][1][1]["access_key"],
            secret_key=acc_details[1][1][1]["secret_key"])
        LOGGER.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account1_id)
        LOGGER.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ, obj_prefix)
        self.list_objects_with_diff_acnt(bucket_name, S3_OBJ)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ1,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ1, err_message)
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ2,
            obj_prefix,
            err_message)
        self.list_objects_with_diff_acnt(
            bucket_name, S3_OBJ2, err_message)
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:prefix and Effect Deny")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6977")
    @CTFailOn(error_handler)
    def test_5490(self):
        """
        Test Create Bucket Policy using "StringEqualsIfExists" Condition Operator,
        key "s3:x-amz-grant-write",Effect Allow and Action "s3:ListBucket"

        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:x-amz-grant-write,Effect Allow and Action s3:ListBucket")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5490_cfg=BKT_POLICY_CONF["test_5490"]
        bucket_name=test_5490_cfg["bucket_name"]
        bucket_policy=test_5490_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            BKT_POLICY_CONF["bucket_policy"]["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name,
                                   BKT_POLICY_CONF["bucket_policy"]["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_5490_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        LOGGER.info(
            "Creating a json with StringEqualsIfExists condition")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringEqualsIfExists"]["s3:x-amz-grant-write"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEqualsIfExists"][
                "s3:x-amz-grant-write"].format(account_id)
        LOGGER.info(
            "Created a json with StringEqualsIfExists condition")
        self.put_invalid_policy(
            bucket_name,
            bucket_policy,
            test_5490_cfg["error_message"])
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIfExists "
            "Condition Operator, key s3:x-amz-grant-write,Effect Allow and Action s3:ListBucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-18450")
    @CTFailOn(error_handler)
    def test_6550(self):
        """
        Test Bucket Policy having Single Condition with Single Key and Multiple Values

        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Single Condition"
            " with Single Key and Multiple Values")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6550_cfg=BKT_POLICY_CONF["test_6550"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_6550_cfg["bucket_name"]
        err_message=test_6550_cfg["error_message"]
        bucket_policy=test_6550_cfg["bucket_policy"]
        object_lst=[]
        LOGGER.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            bucket_name, test_6550_cfg["obj_count"], obj_prefix, object_lst)
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_6550_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_acl_test_lib.S3AclTestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        LOGGER.info(
            "Step 2 : Create a json file for  a Bucket Policy having Single Condition "
            "with Multiple Keys and each Key having single Value. Action -")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account1_id)
        LOGGER.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy.")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        LOGGER.info("Step 4 : Verify the Bucket Policy from cross account")
        resp=S3_OBJ1.put_object_with_acl(
            bucket_name,
            object_lst[0],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            acl=test_6550_cfg["obj_permission1"])
        assert resp[0], resp[1]
        resp=S3_OBJ1.put_object_with_acl(
            bucket_name,
            object_lst[0],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            acl=test_6550_cfg["obj_permission2"])
        assert resp[0], resp[1]
        try:
            S3_OBJ1.put_object_with_acl(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"],
                acl=test_6550_cfg["obj_permission3"])
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ2.put_object(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            assert err_message in error.message, error.message
        LOGGER.info(
            "ENDED: Test Bucket Policy having Single Condition"
            " with Single Key and Multiple Values")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-18451")
    @CTFailOn(error_handler)
    def test_6553(self):
        """
        Test Bucket Policy Single Condition, Multiple Keys having Single Value for each Key

        """
        LOGGER.info(
            "STARTED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6553_cfg=BKT_POLICY_CONF["test_6553"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_6553_cfg["bucket_name"]
        err_message=test_6553_cfg["error_message"]
        bucket_policy=test_6553_cfg["bucket_policy"]
        object_lst=[]
        LOGGER.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            bucket_name, test_6553_cfg["obj_count"], obj_prefix, object_lst)

        account_name2="{}{}".format(
            bkt_policy_cfg["acc_name_prefix"], str(
                time.time()))
        email2="{}{}".format(account_name2, bkt_policy_cfg["email_id"])
        resp1=IAM_OBJ.create_account_s3iamcli(
            account_name2, email2,
            self.ldap_user,
            self.ldap_pwd)
        account_id2=resp1[1]["Account_Id"]
        canonical_id_2=resp1[1]["canonical_id"]
        LOGGER.debug(
            "Account2 Id: {}, Cannonical_id_2: {}".format(
                account_id2, canonical_id_2))
        access_key=resp1[1]["access_key"]
        secret_key=resp1[1]["secret_key"]
        S3_OBJ1=s3_acl_test_lib.S3AclTestLib(
            access_key=access_key,
            secret_key=secret_key)
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=access_key,
            secret_key=secret_key)

        account_name3="{}{}".format(
            bkt_policy_cfg["acc_name_prefix"], str(
                time.time()))
        email3="{}{}".format(account_name3, bkt_policy_cfg["email_id"])
        resp2=IAM_OBJ.create_account_s3iamcli(
            account_name3, email3,
            self.ldap_user,
            self.ldap_pwd)
        canonical_id_3=resp2[1]["canonical_id"]
        LOGGER.debug("Cannonical_id_3: {}".format(canonical_id_3))

        LOGGER.info(
            "Step 2 : Create a json file for  a Bucket Policy having Single Condition with "
            "Multiple Keys and each Key having single Value")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id2)

        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"].format(
                canonical_id_2)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"].format(
                canonical_id_3)

        LOGGER.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy.")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Verify the Bucket Policy from cross account")
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        LOGGER.info("Step 4 : Verify the Bucket Policy from cross account")
        LOGGER.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp=ACL_OBJ.put_object_with_acl2(bucket_name,
                                            "{}{}".format(
                                                object_lst[0], str(time.time())),
                                            BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                            grant_full_control="ID={}".format(
                                                canonical_id_2),
                                            grant_read="ID={}".format(canonical_id_3))
        assert resp[0], resp[1]
        try:
            S3_OBJ2.put_object(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"],
                grant_full_control="emailaddress={}".format(email2))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"],
                grant_read="emailaddress={}".format(email3))
        except CTException as error:
            assert err_message in error.message, error.message
        LOGGER.info(
            "ENDED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7516")
    @CTFailOn(error_handler)
    def test_6693(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-acl" and Value "True".
        Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'True'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6693"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2:Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        acl_permission=test_cfg["permission"]
        LOGGER.info(
            "Case 1 put object with acl permission as {} with new account".format(acl_permission))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            acl=acl_permission, err_message=test_cfg["error_message"])
        LOGGER.info(
            "Case 2 put object without acl permission with new account")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'True'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7517")
    @CTFailOn(error_handler)
    def test_6703(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-acl" and Value "False".
        Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'False'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6703"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        acl_permission=test_cfg["permission"]
        LOGGER.info(
            "Case 1 put object with acl permission as {} with new account".format(acl_permission))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            acl=acl_permission)
        LOGGER.info(
            "Case 2 put object without acl permission with new account")
        self.put_object_with_acl_cross_acnt(
            bucket_name,
            S3_OBJ,
            bkt_policy_cfg["obj_name_prefix"],
            err_message=test_cfg["error_message"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl' and Value 'False'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7518")
    @CTFailOn(error_handler)
    def test_6704(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-acl" and Values ["False", "True"].
        Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl'"
            " and Values ['False', 'True']")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6704"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        acl_permission=test_cfg["permission"]
        LOGGER.info(
            "Case 1 put object with acl permission as {} with new account".format(acl_permission))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            acl=acl_permission)
        LOGGER.info(
            "Case 2 put object without acl permission with new account")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-acl'"
            " and Values ['False', 'True']")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7519")
    @CTFailOn(error_handler)
    def test_6760(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read"
        and Values ["False", "True"]. Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read'"
            " and Values ['False', 'True']")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6760"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        conanical_id=acc_details[0]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        grant_read=bkt_policy_cfg["id_str"].format(conanical_id)
        LOGGER.info(
            "Case 1 put object with grant permission for new account "
            "having id as {}".format(grant_read))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_read=grant_read)
        LOGGER.info("Case 2 put object without grant read permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read'"
            " and Values ['False', 'True']")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7520")
    @CTFailOn(error_handler)
    def test_6761(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write"
        and Values "True". Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values 'True'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6761"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values 'True'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6762")
    @CTFailOn(error_handler)
    def test_6763(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write"
        and Values ["False", "True" ]. Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values ['False', 'True']")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6763"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write'"
            " and Values ['False', 'True']")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7522")
    @CTFailOn(error_handler)
    def test_6764(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read-acp"
        and Values "True". Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'True'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6764"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant read acp permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_read_acp=bkt_policy_cfg["id_str"].format(canonical_id),
            err_message=test_cfg["error_message"])
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'True'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7523")
    @CTFailOn(error_handler)
    def test_6765(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read-acp"
        and Values "False". Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'False'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6765"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant read acp permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_read_acp=bkt_policy_cfg["id_str"].format(canonical_id))
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"],
            err_message=test_cfg["error_message"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values 'False'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7524")
    @CTFailOn(error_handler)
    def test_6766(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read-acp"
        and Values ['False', 'True']. Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values ['False', 'True']")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6766"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant read acp permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_read_acp=bkt_policy_cfg["id_str"].format(canonical_id))
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read-acp'"
            " and Values ['False', 'True']")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7525")
    @CTFailOn(error_handler)
    def test_6767(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write-acp"
        and Value 'True'. Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'True'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6767"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant write acp permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_write_acp=bkt_policy_cfg["id_str"].format(canonical_id),
            err_message=test_cfg["error_message"])
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'True'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7526")
    @CTFailOn(error_handler)
    def test_6768(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write-acp"
        and Value 'False'. Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'False'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6768"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant write acp permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_write_acp=bkt_policy_cfg["id_str"].format(canonical_id))
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"],
            err_message=test_cfg["error_message"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Value 'False'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7527")
    @CTFailOn(error_handler)
    def test_6769(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write-acp"
        and Values ["False", "True"]. Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Values ['False', 'True']")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6769"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant write acp permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_write_acp=bkt_policy_cfg["id_str"].format(canonical_id))
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write-acp'"
            " and Values ['False', 'True']")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7528")
    @CTFailOn(error_handler)
    def test_6770(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-full-control"
        and Value "True". Verify the result.
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-full-control'"
            " and Value 'True'")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_cfg=BKT_POLICY_CONF["test_6770"]
        bucket_name=test_cfg["bucket_name"]
        bucket_policy=test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket with multiple objects")
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(
                time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        s3test_acl_obj=acc_details[2]
        S3_OBJ=acc_details[1]
        account_id=acc_details[6]
        LOGGER.info(
            "Step 2: Create a json for a Bucket Policy having Null Condition operator")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0][
            "Sid"].format(policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator: {}".format(bucket_policy))
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket".format(bucket_name))
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Put and get bucket policy from {} bucket successful".format(bucket_name))
        LOGGER.info("Step 4: Verify the Bucket Policy from cross account")
        canonical_id=acc_details[0]
        LOGGER.info(
            "Case 1 put object with grant full control permission for new account "
            "having id as {}".format(canonical_id))
        self.put_object_with_acl_cross_acnt(
            bucket_name, s3test_acl_obj, bkt_policy_cfg["obj_name_prefix"],
            grant_full_control=bkt_policy_cfg["id_str"].format(canonical_id),
            err_message=test_cfg["error_message"])
        LOGGER.info("Case 2 put object without grant permission")
        self.put_object_with_acl_cross_acnt(
            bucket_name, S3_OBJ, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 4: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-full-control'"
            " and Value 'True'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7611")
    @CTFailOn(error_handler)
    def test_5921(self):
        """
        Test when blank file is provided for put bucket policy
        """
        LOGGER.info(
            "STARTED: Test when blank file is provided for put bucket policy")
        test_5921_cfg=BKT_POLICY_CONF["test_5921"]
        bucket_name=test_5921_cfg["bucket_name"].format(time.time())
        self.create_bucket_validate(bucket_name)
        self.put_invalid_policy(
            bucket_name,
            test_5921_cfg["bucket_policy"],
            test_5921_cfg["error_message"])
        LOGGER.info(
            "ENDED: Test when blank file is provided for put bucket policy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5210")
    @CTFailOn(error_handler)
    def test_5211(self):
        """
        Test Give own user permission for PutBucketPolicy and
        from user deny its account for Get/PutBucketPolicy
        """
        LOGGER.info(
            "STARTED: Test Give own user permission for PutBucketPolicy"
            " and from user deny its account for Get/PutBucketPolicy")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5211_cfg=BKT_POLICY_CONF["test_5211"]
        bucket_name=test_5211_cfg["bucket_name"].format(time.time())
        bucket_policy_1=test_5211_cfg["bucket_policy_1"]
        bucket_policy_2=test_5211_cfg["bucket_policy_2"]
        user_name="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id=resp[1][0]["User"][1]["User"]["UserId"]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            test_5211_cfg["object_name_2"])
        LOGGER.info("Step 1: Creating bucket policy with user id")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy_1["Statement"][0]["Principal"][
                "AWS"].format(user_id)
        bucket_policy_1["Statement"][0]["Resource"]=bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info("Step 1: Created bucket policy with user id")
        self.put_get_bkt_policy(bucket_name, bucket_policy_1)
        LOGGER.info(
            "Step 2: Creating another policy on a bucket for account 1 using account id")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]=bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            account_id)
        bucket_policy_2["Statement"][0]["Resource"]=bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name)
        bkt_policy_json_2=json.dumps(bucket_policy_2)
        LOGGER.info(
            "Step 2: Created policy for account 1 using account id")
        LOGGER.info("Step 3: Applying bucket policy using users credential")
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp=s3_policy_usr_obj.put_bucket_policy(
            bucket_name, bkt_policy_json_2)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Applied bucket policy using users credential")
        LOGGER.info(
            "Step 4: Applying bucket policy using account 1 credential")
        bkt_policy_json_1=json.dumps(bucket_policy_1)
        resp=S3_BKT_POLICY_OBJ.put_bucket_policy(
            bucket_name, bkt_policy_json_1)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Applied policy of a bucket using account 1 credential")
        LOGGER.info(
            "Step 5: Retrieving policy of a bucket using account 1 credential")
        resp=S3_BKT_POLICY_OBJ.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5: Retrieved policy of a bucket using account 2 credential")
        LOGGER.info(
            "ENDED: Test Give own user permission for PutBucketPolicy "
            "and from user deny its account for Get/PutBucketPolicy")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5211")
    @CTFailOn(error_handler)
    def test_5210(self):
        """
        Test Give own and cross account user permission specifying userid in principal and allow GetBucketPolicy.
        """
        LOGGER.info(
            "STARTED: Test Give own and cross account user permission "
            "specifying userid in principal and allow GetBucketPolicy.")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5210_cfg=BKT_POLICY_CONF["test_5210"]
        bucket_name=test_5210_cfg["bucket_name"].format(time.time())
        bucket_policy=test_5210_cfg["bucket_policy"]
        user_name_1="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        user_name_2="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        access_key_2=acc_details[4]
        secret_key_2=acc_details[5]
        resp=IAM_OBJ.create_user_access_key(user_name_1)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id_1=resp[1][0]["User"][1]["User"]["UserId"]
        LOGGER.info("Step 1: Creating user using account 2 credential")
        s3_policy_acc2_obj=iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp=s3_policy_acc2_obj.create_user_using_s3iamcli(
            user_name_2, access_key=access_key_2, secret_key=secret_key_2)
        assert resp[0]
        user_id_2=resp[1]["User Id"]
        LOGGER.info("Step 1: Created user using account 2 credential")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            test_5210_cfg["object_name_2"])
        LOGGER.info(
            "Step 2: Creating bucket policy on a bucket to account1 User and account2 User")
        bucket_policy["Statement"][0]["Principal"]["AWS"][0]=bucket_policy["Statement"][0]["Principal"]["AWS"][
            0].format(user_id_1)
        bucket_policy["Statement"][0]["Principal"]["AWS"][1]=bucket_policy["Statement"][0]["Principal"]["AWS"][
            1].format(user_id_2)
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info(
            "Step 2: Created bucket policy on a bucket to account1 User and account2 User")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3: Retrieving policy of a bucket using user of account 1")
        s3_policy_usr1_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp=s3_policy_usr1_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Retrieved policy of a bucket using user of account 1")
        LOGGER.info(
            "Step 4: Retrieving policy of a bucket using user of account 2")
        resp=s3_policy_acc2_obj.create_access_key(user_name_2)
        s3_bucket_usr2_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bucket_usr2_obj.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5210_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 4: Retrieving policy of a bucket using user of account 2 is failed with error {0}".format(
                    test_5210_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Test Give own and cross account user permission "
            "specifying userid in principal and allow GetBucketPolicy.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7614")
    @CTFailOn(error_handler)
    def test_5206(self):
        """
        Test give own user permission specifying user id in principal and allow GetBucketPolicy.
        """
        LOGGER.info(
            "STARTED: Test give own user permission specifying user id in principal and allow GetBucketPolicy.")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5206_cfg=BKT_POLICY_CONF["test_5206"]
        bucket_name=test_5206_cfg["bucket_name"].format(time.time())
        bucket_policy=test_5206_cfg["bucket_policy"]
        user_name_1="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        resp=IAM_OBJ.create_user_access_key(user_name_1)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id=resp[1][0]["User"][1]["User"]["UserId"]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            test_5206_cfg["object_name_2"])
        LOGGER.info(
            "Step 1: Creating bucket policy on a bucket to account1 user")
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"][
            "AWS"].format(user_id)
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info(
            "Step 1: Created bucket policy on a bucket to account1 User")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 2: Retrieving policy of a bucket using user of account 1")
        s3_policy_usr1_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp=s3_policy_usr1_obj.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Retrieved policy of a bucket using user of account 1")
        LOGGER.info(
            "ENDED: Test give own user permission specifying user id in principal and allow GetBucketPolicy.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7615")
    @CTFailOn(error_handler)
    def test_5212(self):
        """
        Test Give cross account user permission for Get/PutBucketPolicy
        and deny the bucket owner account for Get/PutBucketPolicy .
        """
        LOGGER.info(
            "STARTED: Test Give cross account user permission for "
            "Get/PutBucketPolicy and deny the bucket owner account for Get/PutBucketPolicy .")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5212_cfg=BKT_POLICY_CONF["test_5212"]
        bucket_name=test_5212_cfg["bucket_name"].format(str(time.time()))
        bucket_policy_1=test_5212_cfg["bucket_policy_1"]
        bucket_policy_2=test_5212_cfg["bucket_policy_2"]
        user_name="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_5212_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        assert acc_details[0], acc_details[1]
        access_key_1=acc_details[1][0][1]["access_key"]
        secret_key_1=acc_details[1][0][1]["secret_key"]
        acc_id_1=acc_details[1][0][1]["Account_Id"]
        access_key_2=acc_details[1][1][1]["access_key"]
        secret_key_2=acc_details[1][1][1]["secret_key"]
        LOGGER.info("Creating user in account 2")
        iam_obj_acc_2=iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp=iam_obj_acc_2.create_user_using_s3iamcli(
            user_name, access_key=access_key_2, secret_key=secret_key_2)
        assert resp[0], resp[1]
        user_id_2=resp[1]["User Id"]
        LOGGER.info("Created user in account 2")
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects in a bucket using account 1")
        s3_obj_acc_1=s3_test_lib.S3TestLib(
            access_key=access_key_1, secret_key=secret_key_1)
        resp=s3_obj_acc_1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        create_file(
            bkt_policy_cfg["file_path"],
            bkt_policy_cfg["file_size"])
        resp=s3_obj_acc_1.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        if os.path.exists(bkt_policy_cfg["folder_path"]):
            remove_dir(bkt_policy_cfg["folder_path"])
        try:
            os.mkdir(bkt_policy_cfg["folder_path"])
        except OSError as error:
            LOGGER.error(error)
        create_file(
            bkt_policy_cfg["file_path_2"],
            bkt_policy_cfg["file_size"])
        resp=s3_obj_acc_1.put_object(
            bucket_name,
            test_5212_cfg["object_name_2"],
            bkt_policy_cfg["file_path_2"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Bucket was created and objects are uploaded in the bucket using account 1")
        LOGGER.info("Step 2: Creating json on a bucket to account 2 user")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]=bucket_policy_1["Statement"][0]["Principal"][
            "AWS"].format(
            user_id_2)
        bucket_policy_1["Statement"][0]["Resource"]=bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name)
        bkt_policy_json_1=json.dumps(bucket_policy_1)
        LOGGER.info("Step 2: Created json on a bucket to account 2 user")
        LOGGER.info(
            "Step 3: Applying policy on a bucket {0}".format(bucket_name))
        s3_bkt_policy_acc1=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=access_key_1, secret_key=secret_key_1)
        resp=s3_bkt_policy_acc1.put_bucket_policy(
            bucket_name, bkt_policy_json_1)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Applied policy on a bucket {0}".format(bucket_name))
        LOGGER.info(
            "Step 4: Retrieving policy of a bucket {0}".format(bucket_name))
        resp=s3_bkt_policy_acc1.get_bucket_policy(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["Policy"], bkt_policy_json_1, resp[1])
        LOGGER.info(
            "Step 4: Retrieved policy of a bucket {0}".format(bucket_name))
        LOGGER.info("Step 5: Creating a json on a bucket to account 1")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]=bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            acc_id_1)
        bucket_policy_2["Statement"][0]["Resource"]=bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name)
        bkt_policy_json_2=json.dumps(bucket_policy_2)
        LOGGER.info("Step 5: Created json on a bucket to account 1")
        LOGGER.info(
            "Step 6: Applying the bucket policy using user of account 2")
        resp=iam_obj_acc_2.create_access_key(user_name)
        s3_bkt_policy_usr2=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bkt_policy_usr2.put_bucket_policy(
                bucket_name, bkt_policy_json_2)
        except CTException as error:
            LOGGER.info(error.message)
            assert test_5212_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 6: Applying the bucket policy using user of account 2 is failed with error {0}".format(
                    test_5212_cfg["error_message"]))
        LOGGER.info(
            "Step 7: Retrieving policy of a bucket using user of account 2")
        try:
            s3_bkt_policy_usr2.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5212_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 7: Retrieving policy of a bucket using user of account 2 is failed with error {0}".format(
                    test_5212_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Test Give cross account user permission for "
            "Get/PutBucketPolicy and deny the bucket owner account for Get/PutBucketPolicy .")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7616")
    @CTFailOn(error_handler)
    def test_5214(self):
        """
        Test Give user permission for PutBucketPolicy and from user allow
         Get/PutBucketPolicy,GetBucketAcl permission to cross account
        """
        LOGGER.info(
            "STARTED: Test Give user permission for PutBucketPolicy and"
            " from user allow Get/PutBucketPolicy,GetBucketAcl permission to cross account")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5214_cfg=BKT_POLICY_CONF["test_5214"]
        bucket_name=test_5214_cfg["bucket_name"].format(time.time())
        bucket_policy_1=test_5214_cfg["bucket_policy_1"]
        bucket_policy_2=test_5214_cfg["bucket_policy_2"]
        user_name="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        s3_bkt_policy_2=acc_details[3]
        s3_bkt_acl_2=acc_details[2]
        resp=IAM_OBJ.create_user_access_key(user_name)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id=resp[1][0]["User"][1]["User"]["UserId"]
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            test_5214_cfg["object_name_2"])
        LOGGER.info("Step 1: Creating bucket policy with user id")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]=bucket_policy_1["Statement"][0]["Principal"][
            "AWS"].format(user_id)
        bucket_policy_1["Statement"][0]["Resource"]=bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info("Step 1: Created bucket policy with user id")
        self.put_get_bkt_policy(bucket_name, bucket_policy_1)
        LOGGER.info(
            "Step 2: Creating another policy on a bucket to account 2 using account id")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]=bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            account_id)
        bucket_policy_2["Statement"][0]["Resource"]=bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name)
        bkt_policy_json_2=json.dumps(bucket_policy_2)
        LOGGER.info(
            "Step 2: Created another policy on a bucket to account 2 using account id")
        LOGGER.info("Step 3: Applying bucket policy using users credential")
        s3_policy_usr_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp=s3_policy_usr_obj.put_bucket_policy(
            bucket_name, bkt_policy_json_2)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Applied bucket policy using users credential")
        LOGGER.info(
            "Step 4: Applying bucket policy using account 2 credential")
        bkt_policy_json_1=json.dumps(bucket_policy_1)
        try:
            s3_bkt_policy_2.put_bucket_policy(bucket_name, bkt_policy_json_1)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5214_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 4: Applying bucket policy using account 2 credential is failed with error {0}".format(
                    test_5214_cfg["error_message"]))
        LOGGER.info(
            "Step 5: Retrieving policy of a bucket using account 2 credential")
        try:
            s3_bkt_policy_2.get_bucket_policy(bucket_name)
        except CTException as error:
            assert test_5214_cfg["error_message"] in error.message, error.message
            LOGGER.error(error.message)
            LOGGER.info(
                "Step 5: Retrieving policy of a bucket using account 2 credential is failed with error {0}".format(
                    test_5214_cfg["error_message"]))
        LOGGER.info(
            "Step 6: Retrieving acl of a bucket using account 2 credential")
        resp=s3_bkt_acl_2.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 6: Retrieved acl of a bucket using account 2 credential")
        LOGGER.info(
            "ENDED: Test Give user permission for PutBucketPolicy and "
            "from user allow Get/PutBucketPolicy,GetBucketAcl permission to cross account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7617")
    @CTFailOn(error_handler)
    def test_5215(self):
        """
        Test Give user permission for PutBucketPolicy and from user
        allow Get/PutBucketPolicy,PutBucketAcl permission to cross account user.
        """
        LOGGER.info(
            "STARTED: Test Give user permission for PutBucketPolicy and "
            "from user allow Get/PutBucketPolicy,PutBucketAcl permission to cross account user.")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5215_cfg=BKT_POLICY_CONF["test_5215"]
        bucket_name=test_5215_cfg["bucket_name"].format(str(time.time()))
        bucket_policy_1=test_5215_cfg["bucket_policy_1"]
        bucket_policy_2=test_5215_cfg["bucket_policy_2"]
        user_name_1="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        user_name_2="{0}{1}".format(
            bkt_policy_cfg["user_name"], str(
                time.time()))
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(time.time()))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        access_key_2=acc_details[4]
        secret_key_2=acc_details[5]
        can_id=acc_details[0]
        resp=IAM_OBJ.create_user_access_key(user_name_1)
        assert resp[0], resp[1]
        usr_access_key=resp[1][0]["Keys"][1]["AccessKey"]["AccessKeyId"]
        usr_secret_key=resp[1][0]["Keys"][1]["AccessKey"]["SecretAccessKey"]
        user_id_1=resp[1][0]["User"][1]["User"]["UserId"]
        LOGGER.info("Step 1: Creating user using account 2 credential")
        iam_acc2_obj=iam_test_lib.IamTestLib(
            access_key=access_key_2, secret_key=secret_key_2)
        resp=iam_acc2_obj.create_user_using_s3iamcli(
            user_name_2, access_key=access_key_2, secret_key=secret_key_2)
        assert resp[0]
        user_id_2=resp[1]["User Id"]
        LOGGER.info("Step 1: Created user using account 2 credential")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            test_5215_cfg["object_name_2"])
        LOGGER.info(
            "Step 2: Creating a policy on a bucket to account 1 User")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]=bucket_policy_1["Statement"][0]["Principal"][
            "AWS"].format(
            user_id_1)
        bucket_policy_1["Statement"][0]["Resource"]=bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name)
        bkt_policy_json_1=json.dumps(bucket_policy_1)
        LOGGER.info("Step 2: Created a policy on a bucket to account 1 User")
        self.put_get_bkt_policy(bucket_name, bucket_policy_1)
        LOGGER.info(
            "Step 3: Creating another policy on a bucket to account 2 user")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]=bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            user_id_2)
        bucket_policy_2["Statement"][0]["Resource"]=bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name)
        bkt_policy_json_2=json.dumps(bucket_policy_2)
        LOGGER.info(
            "Step 3: Created another policy on a bucket to account 2 user")
        LOGGER.info(
            "Step 4: Applying policy on a bucket using user of account 1")
        s3_policy_usr1_obj=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=usr_access_key, secret_key=usr_secret_key)
        resp=s3_policy_usr1_obj.put_bucket_policy(
            bucket_name, bkt_policy_json_2)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Applied policy on a bucket using user of account 1")
        LOGGER.info(
            "Step 5: Applying policy on a bucket using user of account 2")
        resp=iam_acc2_obj.create_access_key(user_name_2)
        s3_bkt_policy_usr2=s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bkt_policy_usr2.put_bucket_policy(
                bucket_name, bkt_policy_json_1)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5215_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 5: Applying policy on a bucket using user of account 2  is failed with error {0}".format(
                    test_5215_cfg["error_message"]))
        LOGGER.info(
            "Step 6: Retrieving policy of a bucket using user of account 2")
        try:
            s3_bkt_policy_usr2.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5215_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 6: Retrieving policy of a bucket using user of account 2 is failed with error {0}".format(
                    test_5215_cfg["error_message"]))
        LOGGER.info(
            "Step 7: Applying read acp permission on a bucket {0}".format(bucket_name))
        s3_bkt_acl_usr2=s3_acl_test_lib.S3AclTestLib(
            access_key=resp[1]["AccessKey"]["AccessKeyId"],
            secret_key=resp[1]["AccessKey"]["SecretAccessKey"])
        try:
            s3_bkt_acl_usr2.put_bucket_acl(
                bucket_name, grant_read_acp=test_5215_cfg["id_str"].format(can_id))
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5215_cfg["error_message_1"] in error.message, error.message
            LOGGER.info(
                "Step 7: Applying read acp permission on a bucket is failed with error {0}".format(
                    test_5215_cfg["error_message_1"]))
        LOGGER.info(
            "ENDED: Test Give user permission for PutBucketPolicy and "
            "from user allow Get/PutBucketPolicy,PutBucketAcl permission to cross account user.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7637")
    @CTFailOn(error_handler)
    def test_6771(self):
        """
        Test Bucket Policy having Null Condition operator
        Key "s3:x-amz-grant-full-control" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key "
            "s3:x-amz-grant-full-control and Value False")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6771_cfg=BKT_POLICY_CONF["test_6771"]
        timestamp=time.time()
        bucket_name=test_6771_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6771_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6771_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        canonical_id=acc_details[0]
        s3_bkt_acl_acc2=acc_details[2]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading object with grant full control using account 2")
        resp=s3_bkt_acl_acc2.put_object_with_acl(
            bucket_name,
            test_6771_cfg["object_name"],
            bkt_policy_cfg["file_path"],
            grant_full_control=test_6771_cfg["id_str"].format(canonical_id))
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Uploaded object with grant full control using account 2")
        LOGGER.info("Case 2: Uploading object with account 2")
        try:
            S3_OBJ_acc2.put_object(
                bucket_name,
                test_6771_cfg["object_name"],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6771_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Case 2: Uploading object with account 2 is failed with error {0}".format(
                    test_6771_cfg["error_message"]))
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key "
            "s3:x-amz-grant-full-control and Value False")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7638")
    @CTFailOn(error_handler)
    def test_6772(self):
        """
        Test Bucket Policy having Null Condition operator
        Key "s3:x-amz-grant-full-control" and Values ["False", "True"]
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator "
            "Key s3:x-amz-grant-full-control and Values [False, True]")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6772_cfg=BKT_POLICY_CONF["test_6772"]
        timestamp=time.time()
        bucket_name=test_6772_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6772_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6772_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        canonical_id=acc_details[0]
        s3_bkt_acl_acc2=acc_details[2]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with grant full control using account 2")
        resp=s3_bkt_acl_acc2.put_object_with_acl(
            bucket_name,
            test_6772_cfg["object_name"],
            bkt_policy_cfg["file_path"],
            grant_full_control=test_6772_cfg["id_str"].format(canonical_id))
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Uploaded an object with grant full control using account 2")
        LOGGER.info("Case 2: Uploading an object using account 2")
        resp=S3_OBJ_acc2.put_object(
            bucket_name,
            test_6772_cfg["object_name"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Uploaded an object using account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-grant-full-control and Values [False, True]")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7639")
    @CTFailOn(error_handler)
    def test_6773(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:max-keys" and Value "True"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value True")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6773_cfg=BKT_POLICY_CONF["test_6773"]
        timestamp=time.time()
        bucket_name=test_6773_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6773_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6773_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info("Case 1: Listing objects with max keys from account 2")
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name,
            S3_OBJ_acc2,
            test_6773_cfg["max_keys"],
            test_6773_cfg["error_message"])
        LOGGER.info(
            "Case 1: Listing objects with max keys from account 2 is failed with error {0}".format(
                test_6773_cfg["error_message"]))
        LOGGER.info("Case 2: Listing objects with account 2")
        resp=S3_OBJ_acc2.object_list(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Objects are listed from account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value True")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7640")
    @CTFailOn(error_handler)
    def test_6774(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:max-keys" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value False")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6774_cfg=BKT_POLICY_CONF["test_6774"]
        timestamp=time.time()
        bucket_name=test_6774_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6774_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6774_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info("Case 1: Listing objects with max keys from account 2")
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ_acc2, test_6774_cfg["max_keys"])
        LOGGER.info(
            "Case 1: Objects are listed with max keys from account 2")
        LOGGER.info("Case 2: Listing objects with account 2")
        try:
            S3_OBJ_acc2.object_list(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6774_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Case 2: Listing objects from account 2 is failed with error {0}".format(
                    test_6774_cfg["error_message"]))
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value False")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7641")
    @CTFailOn(error_handler)
    def test_6775(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:max-keys" and Value ["False", "True"]
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value [False, True]")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6775_cfg=BKT_POLICY_CONF["test_6775"]
        timestamp=time.time()
        bucket_name=test_6775_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6775_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6775_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info("Case 1: Listing objects with max keys from account 2")
        self.list_obj_with_max_keys_and_diff_acnt(
            bucket_name, S3_OBJ_acc2, test_6775_cfg["max_keys"])
        LOGGER.info(
            "Case 1: Objects are listed with max keys from account 2")
        LOGGER.info("Case 2: Listing objects with account 2")
        resp=S3_OBJ_acc2.object_list(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Objects are listed from account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:max-keys and Value [False, True]")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7642")
    @CTFailOn(error_handler)
    def test_6776(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:prefix" and Value "True"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value True")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6776_cfg=BKT_POLICY_CONF["test_6776"]
        timestamp=time.time()
        bucket_name=test_6776_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6776_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects to a bucket")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            test_6776_cfg["obj_key_1"],
            test_6776_cfg["obj_key_2"])
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        resp=S3_OBJ.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created a bucket and objects are uploaded to a bucket")
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 2: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info("Case 1: Listing objects with prefix from account 2")
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name,
            S3_OBJ_acc2,
            test_6776_cfg["obj_prefix"],
            test_6776_cfg["error_message"])
        LOGGER.info(
            "Case 1: Listing objects with prefix from account 2 is failed with error {0}".format(
                test_6776_cfg["error_message"]))
        LOGGER.info("Case 2: Listing object using account 2")
        resp=S3_OBJ_acc2.object_list(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Objects are listed using account 2")
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value True")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7643")
    @CTFailOn(error_handler)
    def test_6777(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:prefix" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value False")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6777_cfg=BKT_POLICY_CONF["test_6777"]
        timestamp=time.time()
        bucket_name=test_6777_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6777_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects to a bucket")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            test_6777_cfg["obj_key_1"],
            test_6777_cfg["obj_key_2"])
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        resp=S3_OBJ.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created a bucket and objects are uploaded to a bucket")
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 2: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info("Case 1: Listing objects with prefix from account 2")
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ_acc2, test_6777_cfg["obj_prefix"])
        LOGGER.info("Case 1: Objects are listed with prefix from account 2")
        LOGGER.info("Case 2: Listing object using account 2")
        try:
            S3_OBJ_acc2.object_list(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6777_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Case 2: Listing objects from account 2 is failed with error {0}".format(
                    test_6777_cfg["error_message"]))
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:prefix and Value False")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7644")
    @CTFailOn(error_handler)
    def test_6779(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:prefix" and Values ["False", "True"]
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:prefix and Values [False, True]")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6779_cfg=BKT_POLICY_CONF["test_6779"]
        timestamp=time.time()
        bucket_name=test_6779_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6779_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        LOGGER.info(
            "Step 1: Creating a bucket and uploading objects to a bucket")
        self.create_bucket_put_obj_with_dir(
            bucket_name,
            test_6779_cfg["obj_key_1"],
            test_6779_cfg["obj_key_2"])
        create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        resp=S3_OBJ.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created a bucket and objects are uploaded to a bucket")
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 2: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 2: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info("Case 1: Listing objects with prefix using account 2")
        self.list_obj_with_prefix_using_diff_accnt(
            bucket_name, S3_OBJ_acc2, test_6779_cfg["obj_prefix"])
        LOGGER.info("Case 1: Objects are listed with prefix using account 2")
        LOGGER.info("Case 2: Listing object using account 2")
        resp=S3_OBJ_acc2.object_list(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Objects are listed from account 2")
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:prefix and Values [False, True]")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7645")
    @CTFailOn(error_handler)
    def test_6783(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-content-sha256" and Value "True"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key s3:x-amz-content-sha256 and Value True")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6783_cfg=BKT_POLICY_CONF["test_6783"]
        timestamp=time.time()
        bucket_name=test_6783_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6783_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6783_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Uploading an object using account 2")
        try:
            S3_OBJ_acc2.put_object(
                bucket_name,
                bkt_policy_cfg["obj_name_prefix"],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6783_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: Uploading object with account 2 is failed with error {0}".format(
                    test_6783_cfg["error_message"]))
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key s3:x-amz-content-sha256 and Value True")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7646")
    @CTFailOn(error_handler)
    def test_6787(self):
        """
        Test Bucket Policy having Null Condition operator
        Key "s3:x-amz-content-sha256" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Value False")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6787_cfg=BKT_POLICY_CONF["test_6787"]
        timestamp=time.time()
        bucket_name=test_6787_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6787_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6787_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Uploading an object using account 2")
        resp=S3_OBJ_acc2.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Uploaded an object with account 2")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Value False")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7648")
    @CTFailOn(error_handler)
    def test_6788(self):
        """
        Test Bucket Policy having Null Condition operator Key
        "s3:x-amz-content-sha256" and Values ["False", "True"]
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Values False,True")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6788_cfg=BKT_POLICY_CONF["test_6788"]
        timestamp=time.time()
        bucket_name=test_6788_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6788_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6788_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Uploading an object using account 2")
        resp=S3_OBJ_acc2.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Uploaded an object with account 2")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-content-sha256 and Values False,True")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7650")
    @CTFailOn(error_handler)
    def test_6790(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-storage-class" and Value "True"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null "
            "Condition operator Key s3:x-amz-storage-class and Value True")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6790_cfg=BKT_POLICY_CONF["test_6790"]
        timestamp=time.time()
        bucket_name=test_6790_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6790_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6790_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with storage class STANDARD using account 2")
        try:
            S3_OBJ_acc2.put_object_with_storage_class(
                bucket_name,
                bkt_policy_cfg["obj_name_prefix"],
                bkt_policy_cfg["file_path"],
                test_6790_cfg["storage_class"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6790_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Case 1: Uploading an object with storage class "
                "STANDARD using account 2 is failed with error {0}".format(
                    test_6790_cfg["error_message"]))
        LOGGER.info("Case 2: Uploading an object with account 2")
        resp=S3_OBJ_acc2.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-storage-class and Value True")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7651")
    @CTFailOn(error_handler)
    def test_6791(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-storage-class" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-storage-class and Value False")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6791_cfg=BKT_POLICY_CONF["test_6791"]
        timestamp=time.time()
        bucket_name=test_6791_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6791_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6791_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with storage class STANDARD using account 2")
        resp=S3_OBJ_acc2.put_object_with_storage_class(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"],
            test_6791_cfg["storage_class"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Uploaded an object with storage class STANDARD using account 2")
        LOGGER.info("Case 2: Uploading an object with account 2")
        try:
            S3_OBJ_acc2.put_object(
                bucket_name,
                bkt_policy_cfg["obj_name_prefix"],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6791_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 2: Uploading an object with account 2 is failed with error {0}".format(
                test_6791_cfg["error_message"]))
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition "
            "operator Key s3:x-amz-storage-class and Value False")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8044")
    @CTFailOn(error_handler)
    def test_6792(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-storage-class" and Values ["True", "False"]
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-storage-class' and Values ['True', 'False']")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6792_cfg=BKT_POLICY_CONF["test_6792"]
        timestamp=time.time()
        bucket_name=test_6792_cfg["bucket_name"].format(timestamp)
        bucket_policy=test_6792_cfg["bucket_policy"]
        account_name="{0}{1}".format(
            bkt_policy_cfg["account_name"], str(timestamp))
        email_id="{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        self.create_bucket_put_objects(
            bucket_name,
            test_6792_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        acc_details=self.create_s3iamcli_acc(account_name, email_id)
        account_id=acc_details[6]
        S3_OBJ_acc2=acc_details[1]
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with storage class STANDARD using account 2")
        resp=S3_OBJ_acc2.put_object_with_storage_class(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"],
            test_6792_cfg["storage_class"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Uploaded an object with storage class STANDARD using account 2")
        LOGGER.info("Case 2: Uploading an object with account 2")
        resp=S3_OBJ_acc2.put_object(
            bucket_name,
            bkt_policy_cfg["obj_name_prefix"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-storage-class' and Values ['True', 'False']")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6763")
    @CTFailOn(error_handler)
    def test_6762(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-write" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write' and Value 'False'")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6762_cfg=BKT_POLICY_CONF["test_6762"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_6762_cfg["bucket_name"]
        bucket_policy=test_6762_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_6762_cfg["account_name_1"].format(random_id)
        email_id_1=test_6762_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1=result_1[0]
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with storage class --grant-write using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                grant_write_acp=test_6762_cfg["id_str"].format(canonical_id_user_1))
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6762_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Uploading an object with account 2 is failed with error {0}".format(
                test_6762_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Uploaded an object with storage class --grant-write using account 2")
        LOGGER.info("Case 2: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                bucket_name,
                object_names[0],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6762_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 2: Uploading an object with account 2 is failed with error {0}".format(
                test_6762_cfg["error_message"]))
        LOGGER.info("Case 2: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-write' and Value 'False'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8041")
    @CTFailOn(error_handler)
    def test_6707(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read" and Value "True"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'True'")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6707_cfg=BKT_POLICY_CONF["test_6707"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_6707_cfg["bucket_name"]
        bucket_policy=test_6707_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_6707_cfg["account_name_1"].format(random_id)
        email_id_1=test_6707_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1=result_1[0]
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with storage class --grant-read using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                grant_read=test_6707_cfg["id_str"].format(canonical_id_user_1))
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6707_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Uploading an object with account 2 is failed with error {0}".format(
                test_6707_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Uploaded an object with storage class --grant-read using account 2")
        LOGGER.info("Case 2: Uploading an object with account 2")
        resp=self.s3test_obj_1.put_object(
            bucket_name,
            object_names[0],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Case 2: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'True'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8042")
    @CTFailOn(error_handler)
    def test_6708(self):
        """
        Test Bucket Policy having Null Condition operator Key "s3:x-amz-grant-read" and Value "False"
        """
        LOGGER.info(
            "STARTED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'False'")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6708_cfg=BKT_POLICY_CONF["test_6708"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_6708_cfg["bucket_name"]
        bucket_policy=test_6708_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_6708_cfg["account_name_1"].format(random_id)
        email_id_1=test_6708_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1=result_1[0]
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json with Null Condition operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json with Null Condition operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with storage class --grant-read using account 2")
        resp=ACL_OBJ_1.put_object_with_acl(
            bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read=test_6708_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Uploaded an object with storage class --grant-read using account 2")
        LOGGER.info("Case 2: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                bucket_name,
                object_names[0],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6708_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Uploading an object with account 2 is failed with error {0}".format(
                test_6708_cfg["error_message"]))
        LOGGER.info("Case 2: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Bucket Policy having Null Condition operator Key 's3:x-amz-grant-read' and Value 'False'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8045")
    @CTFailOn(error_handler)
    def test_7051(self):
        """
        Test Verify Bucket Policy having Valid Condition Key and Invalid Value
        """
        LOGGER.info(
            "STARTED: Test Verify Bucket Policy having Valid Condition Key and Invalid Value")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7051_cfg=BKT_POLICY_CONF["test_7051"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7051_cfg["bucket_name"]
        bucket_policy=test_7051_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7051_cfg["account_name_1"].format(random_id)
        email_id_1=test_7051_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1=result_1[0]
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-read using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7051_cfg["bucket-owner-read"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7051_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-read is failed with error {0}".format(
                test_7051_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Uploaded an object with --acl bucket-owner-read using account 2")
        LOGGER.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7051_cfg["bucket-owner-full-control"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7051_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control is failed with error {0}".format(
                test_7051_cfg["error_message"]))
        LOGGER.info(
            "Case 2: Uploaded an object with --acl bucket-owner-full-control using account 2")
        LOGGER.info("Case 3: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                bucket_name,
                object_names[0],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7051_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 3: Uploading an object with account 2 is failed with error {0}".format(
                test_7051_cfg["error_message"]))
        LOGGER.info("Case 3: Uploaded an object with account 2")
        LOGGER.info(
            "Case 4: Uploading an object with invalid value 'xyz' using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7051_cfg["invalid_value"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7051_cfg["error_message_2"] in error.message, error.message
        LOGGER.info(
            "Case 4: Uploaded an object with invalid value 'xyz' using account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Verify Bucket Policy having Valid Condition Key and Invalid Value")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8046")
    @CTFailOn(error_handler)
    def test_7052(self):
        """
        Test Verify Bucket Policy having Invalid Condition Key
        """
        LOGGER.info(
            "STARTED: Test Verify Bucket Policy having Invalid Condition Key")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7052_cfg=BKT_POLICY_CONF["test_7052"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7052_cfg["bucket_name"]
        bucket_policy=test_7052_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7052_cfg["account_name_1"].format(random_id)
        email_id_1=test_7052_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json having valid condition key and invalid value")
        LOGGER.info(
            "Step 2: Verifying the Put Bucket Policy from cross account")
        try:
            bkt_policy_json=json.dumps(bucket_policy)
            S3_BKT_POLICY_OBJ.put_bucket_policy(
                bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7052_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "step 2: Put Bucket Policy is failed with error {0}".format(
                test_7052_cfg["error_message"]))
        LOGGER.info(
            "Step 2: Verified the Put Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Verify Bucket Policy having Invalid Condition Key")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8047")
    @CTFailOn(error_handler)
    def test_7054(self):
        """
        Test Verify Bucket Policy multiple conflicting Condition types(operators)
        """
        LOGGER.info(
            "STARTED: Test Verify Bucket Policy multiple conflicting Condition types(operators)")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7054_cfg=BKT_POLICY_CONF["test_7054"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7054_cfg["bucket_name"]
        bucket_policy=test_7054_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7054_cfg["account_name_1"].format(random_id)
        email_id_1=test_7054_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-read using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7054_cfg["bucket-owner-read"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7054_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-read is failed with error {0}".format(
                test_7054_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Uploaded an object with --acl bucket-owner-read using account 2")
        LOGGER.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7054_cfg["bucket-owner-full-control"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7054_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control is failed with error {0}".format(
                test_7054_cfg["error_message"]))
        LOGGER.info(
            "Case 2: Uploaded an object with --acl bucket-owner-full-control using account 2")
        LOGGER.info("Case 3: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                bucket_name,
                object_names[0],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7054_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 3: Uploading an object with account 2 is failed with error {0}".format(
                test_7054_cfg["error_message"]))
        LOGGER.info("Case 3: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Verify Bucket Policy multiple conflicting Condition types(operators)")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8048")
    @CTFailOn(error_handler)
    def test_7055(self):
        """
        Test Verify Bucket Policy Condition Values are case sensitive
        """
        LOGGER.info(
            "STARTED: Test Verify Bucket Policy Condition Values are case sensitive")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7055_cfg=BKT_POLICY_CONF["test_7055"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7055_cfg["bucket_name"]
        bucket_policy=test_7055_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7055_cfg["account_name_1"].format(random_id)
        email_id_1=test_7055_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 1: Creating a json having valid condition key and invalid value")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 1: Created a json having valid condition key and invalid value")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 2: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-read using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7055_cfg["bucket-owner-read"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7055_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-read is failed with error {0}".format(
                test_7055_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Uploaded an object with --acl bucket-owner-read using account 2")
        LOGGER.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7055_cfg["public-read"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7055_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 2: Uploading an object with --acl bucket-owner-full-control is failed with error {0}".format(
                test_7055_cfg["error_message"]))
        LOGGER.info(
            "Case 2: Uploaded an object with --acl bucket-owner-full-control using account 2")
        LOGGER.info("Case 3: Uploading an object with account 2")
        try:
            self.s3test_obj_1.put_object(
                bucket_name,
                object_names[0],
                bkt_policy_cfg["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7055_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 3: Uploading an object with account 2 is failed with error {0}".format(
                test_7055_cfg["error_message"]))
        LOGGER.info("Case 3: Uploaded an object with account 2")
        LOGGER.info("Step 2: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Verify Bucket Policy Condition Values are case sensitive")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8049")
    @CTFailOn(error_handler)
    def test_7056(self):
        """
        Test Create Bucket Policy using StringEqualsIgnoreCase Condition Operator, key "s3:prefix" and Effect Allow
        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7056_cfg=BKT_POLICY_CONF["test_7056"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7056_cfg["bucket_name"]
        bucket_policy=test_7056_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7056_cfg["account_name_1"].format(random_id)
        email_id_1=test_7056_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        self.create_bucket_put_objects(
            bucket_name,
            test_7056_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        prefix_upper=BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"].upper(
        )
        obj_name_upper="{}/{}".format(
            prefix_upper, str(int(time.time())))
        resp=S3_OBJ.put_object(
            bucket_name,
            obj_name_upper,
            BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 2: Create a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        bucket_policy["Statement"][0]["Condition"]["StringEqualsIgnoreCase"]["s3:prefix"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEqualsIgnoreCase"]["s3:prefix"].format(
                BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        LOGGER.info(
            "Step 2: Created a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: List objects with prefix using account 2")
        resp=self.s3test_obj_1.list_objects_with_prefix(
            bucket_name,
            prefix=BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Listed objects with prefix using account 2")
        LOGGER.info(
            "Case 2: List objects with upper prefix using account 2")
        resp=self.s3test_obj_1.list_objects_with_prefix(
            bucket_name,
            prefix=prefix_upper)
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 2: Listed objects with upper prefix using account 2")
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8050")
    @CTFailOn(error_handler)
    def test_7057(self):
        """
        Test Create Bucket Policy using StringNotEqualsIgnoreCase Condition Operator, key "s3:prefix" and Effect Allow
        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringNotEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7057_cfg=BKT_POLICY_CONF["test_7057"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7057_cfg["bucket_name"]
        bucket_policy=test_7057_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7057_cfg["account_name_1"].format(random_id)
        email_id_1=test_7057_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        self.create_bucket_put_objects(
            bucket_name,
            test_7057_cfg["obj_count"],
            BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        prefix_upper=BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"].upper(
        )
        obj_name_upper="{}/{}".format(
            prefix_upper, str(int(time.time())))
        resp=S3_OBJ.put_object(
            bucket_name,
            obj_name_upper,
            BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 2: Create a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        bucket_policy["Statement"][0]["Condition"]["StringNotEqualsIgnoreCase"]["s3:prefix"]= \
            bucket_policy["Statement"][0]["Condition"]["StringNotEqualsIgnoreCase"]["s3:prefix"].format(
                BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        LOGGER.info(
            "Step 2: Created a json file for bucket policy specifying StringEqualsIgnoreCase Condition Operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: List objects with prefix using account 2")
        try:
            self.s3test_obj_1.list_objects_with_prefix(
                bucket_name,
                prefix=BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7057_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: List objects with account 2 is failed with error {0}".format(
                test_7057_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Listed objects with prefix using account 2")
        LOGGER.info(
            "Case 2: List objects with upper prefix using account 2")
        try:
            self.s3test_obj_1.list_objects_with_prefix(
                bucket_name,
                prefix=prefix_upper)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7057_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 2: List objects with upper prefix is failed with error {0}".format(
                test_7057_cfg["error_message"]))
        LOGGER.info(
            "Case 2: Listed objects with upper prefix using account 2")
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringNotEqualsIgnoreCase Condition Operator, key 's3:prefix' and Effect Allow")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8051")
    @CTFailOn(error_handler)
    def test_7058(self):
        """
        Test Create Bucket Policy using StringLike Condition Operator, key "s3:x-amz-acl"
        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringLike Condition Operator, key 's3:x-amz-acl'")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7058_cfg=BKT_POLICY_CONF["test_7058"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7058_cfg["bucket_name"]
        bucket_policy=test_7058_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7058_cfg["account_name_1"].format(random_id)
        email_id_1=test_7058_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 2: Create a json file for bucket policy specifying StringLike Condition Operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 2: Created a json file for bucket policy specifying StringLike Condition Operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-full-control using account 2")
        resp=ACL_OBJ_1.put_object_with_acl(
            bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            acl=test_7058_cfg["bucket-owner-full-control"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Case 1: Uploaded an object with --acl bucket-owner-full-control using account 2")
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringLike Condition Operator, key 's3:x-amz-acl'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8052")
    @CTFailOn(error_handler)
    def test_7059(self):
        """
        Test Create Bucket Policy using StringNotLike Condition Operator, key "s3:x-amz-acl"
        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringNotLike Condition Operator, key 's3:x-amz-acl'")
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7059_cfg=BKT_POLICY_CONF["test_7059"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7059_cfg["bucket_name"]
        bucket_policy=test_7059_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_7059_cfg["account_name_1"].format(random_id)
        email_id_1=test_7059_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        ACL_OBJ_1=result_1[2]
        account_id_1=result_1[6]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket.")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        object_names=[]
        assert resp[0], resp[1]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket.")
        LOGGER.info(
            "Step 2: Create a json file for bucket policy specifying StringLike Condition Operator")
        bucket_policy["Statement"][0]["Resource"]=bucket_policy["Statement"][0]["Resource"].format(
            bucket_name)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(
            "Step 2: Created a json file for bucket policy specifying StringLike Condition Operator")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Verifying the Bucket Policy from cross account")
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-full-control using account 2")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                acl=test_7059_cfg["bucket-owner-full-control"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_7059_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Case 1: Put objects is failed with error {0}".format(
                test_7059_cfg["error_message"]))
        LOGGER.info(
            "Case 1: Uploading an object with --acl bucket-owner-full-control using account 2")
        LOGGER.info("Step 3: Verified the Bucket Policy from cross account")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringNotLike Condition Operator, key 's3:x-amz-acl'")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8037")
    @CTFailOn(error_handler)
    def test_5134(self):
        """
        Test apply allow PutObjectAcl api on object in policy and READ_ACP ACL on the object.
        """
        LOGGER.info(
            "STARTED: Test apply allow PutObjectAcl api on object in policy and READ_ACP ACL on the object."
        )
        random_id=str(time.time())
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_5134_cfg=BKT_POLICY_CONF["test_5134"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_5134_cfg["bucket_name"]
        bucket_policy=test_5134_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1=test_5134_cfg["account_name_1"].format(random_id)
        email_id_1=test_5134_cfg["emailid_1"].format(random_id)
        result_1=self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1=result_1[0]
        ACL_OBJ_1=result_1[2]
        self.s3test_obj_1=result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp=S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names=[]
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name="{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp=S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow PutObjectACL api on object in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']=bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource']=bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(
            "Step 2: Created a policy json and Allow PutObjectACL api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Apply READ_ACP ACL on the object to account2. - run from default")
        resp=ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read_acp=test_5134_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Applied READ_ACP ACL on the object to account2. - run from default")
        LOGGER.info(
            "Step 7: Check the object ACL to verify the applied ACL.  - run from account1")
        resp=ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7: Checked the object ACL to verify the applied ACL.  - run from default")
        LOGGER.info("Step 8: Put object ACL. - run from default")
        resp=ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read_acp=test_5134_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info("Step 8: Put object ACL. - run from default")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow PutObjectAcl api on object in policy and READ_ACP ACL on the object."
        )

    # Bug reported EOS-7215: Test is failing, need to revisit after bug is
    # fixed.
    @pytest.mark.s3
    @pytest.mark.tags("TEST-10359")
    @CTFailOn(error_handler)
    def test_7053(self):
        """
        Verify Bucket Policy Condition Keys are case insensitive
        """
        LOGGER.info(
            "STARTED: Verify Bucket Policy Condition Keys are case insensitive")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_7053_cfg=BKT_POLICY_CONF["test_7053"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_7053_cfg["bucket_name"]
        err_message=test_7053_cfg["error_message"]
        bucket_policy=test_7053_cfg["bucket_policy"]
        object_lst=[]
        LOGGER.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            bucket_name, test_7053_cfg["obj_count"], obj_prefix, object_lst)
        acc_details=IAM_OBJ.create_multiple_accounts(
            test_7053_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account1_id=acc_details[1][0][1]["Account_Id"]
        S3_OBJ1=s3_acl_test_lib.S3AclTestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        LOGGER.info(
            "Step 2:Create a json file for a Bucket Policy having Valid Condition")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account1_id)
        LOGGER.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 4 : Verify the Bucket Policy from cross account")
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        resp=S3_OBJ1.put_object_with_acl(
            bucket_name,
            object_lst[0],
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            acl=test_7053_cfg["obj_permission1"])
        assert resp[0], resp[1]
        try:
            S3_OBJ1.put_object_with_acl(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"],
                acl=test_7053_cfg["obj_permission2"])
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ2.put_object(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            assert err_message in error.message, error.message
        LOGGER.info(
            "ENDED: Verify Bucket Policy Condition Keys are case insensitive")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-18452")
    @CTFailOn(error_handler)
    def test_6554(self):
        """
        Test Bucket Policy Single Condition, Multiple Keys having Single Value for each Key

        """
        LOGGER.info(
            "STARTED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")
        bkt_policy_cfg=BKT_POLICY_CONF["bucket_policy"]
        test_6554_cfg=BKT_POLICY_CONF["test_6554"]
        obj_prefix=bkt_policy_cfg["obj_name_prefix"]
        bucket_name=test_6554_cfg["bucket_name"]
        err_message=test_6554_cfg["error_message"]
        bucket_policy=test_6554_cfg["bucket_policy"]
        object_lst=[]
        LOGGER.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            bucket_name, test_6554_cfg["obj_count"], obj_prefix, object_lst)

        acc_details=IAM_OBJ.create_multiple_accounts(
            test_6554_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account2_id=acc_details[1][0][1]["Account_Id"]
        account2_cid=acc_details[1][0][1]["canonical_id"]
        account3_cid=acc_details[1][1][1]["canonical_id"]
        account4_cid=acc_details[1][2][1]["canonical_id"]
        account5_cid=acc_details[1][3][1]["canonical_id"]
        S3_OBJ1=s3_acl_test_lib.S3AclTestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2=s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])

        LOGGER.info(
            "Step 2 : Create a json file for  a Bucket Policy having Single Condition with "
            "Multiple Keys and each Key having Multiple Values. Action - Put Object and Effect - Allow.")
        policy_id=f"Policy{uuid.uuid4()}"
        policy_sid=f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]=bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]=bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]=bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account2_id)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"]=bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"].format(
                [account2_cid, account3_cid])
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"]=bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"].format(
                [account4_cid, account5_cid])
        LOGGER.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step  4: Verify the Bucket Policy from cross account")
        resp=create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp=ACL_OBJ.put_object_with_acl2(bucket_name,
                                            "{}{}".format(
                                                object_lst[0], str(time.time())),
                                            BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                            grant_full_control="id={}".format(
                                                account3_cid),
                                            grant_read="id={}".format(account5_cid))
        assert resp[0], resp[1]
        LOGGER.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp=ACL_OBJ.put_object_with_acl2(bucket_name,
                                            "{}{}".format(
                                                object_lst[0], str(time.time())),
                                            BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                            grant_full_control="id={}".format(
                                                account2_cid),
                                            grant_read="id={}".format(account4_cid))
        assert resp[0], resp[1]
        try:
            LOGGER.info(
                "Put object with ACL : grant_full_control and grant_read")
            S3_OBJ1.put_object_with_acl2(bucket_name,
                                         "{}{}".format(
                                             object_lst[0], str(time.time())),
                                         BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                         grant_full_control="id={}".format(
                                             account5_cid),
                                         grant_read="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl2(bucket_name,
                                         "{}{}".format(
                                             object_lst[0], str(time.time())),
                                         BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                         grant_full_control="id={}".format(
                                             account5_cid),
                                         grant_read="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(bucket_name,
                                        "{}{}".format(
                                            object_lst[0], str(time.time())),
                                        BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                        grant_full_control="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(bucket_name,
                                        "{}{}".format(
                                            object_lst[0], str(time.time())),
                                        BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                        grant_read="id={}".format(account5_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ2.put_object(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            assert err_message in error.message, error.message
        LOGGER.info(
            "ENDED: Test Bucket Policy Single Condition, "
            "Multiple Keys having Single Value for each Key")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8038")
    @CTFailOn(error_handler)
    def test_5136(self):
        """
        Test apply allow GetObject api on object in policy and READ_ACP ACL on the object .
        """
        LOGGER.info(
            "STARTED: Test apply allow GetObject api on object in policy and READ_ACP ACL on the object ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5136_cfg= BKT_POLICY_CONF["test_5136"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5136_cfg["bucket_name"]
        bucket_policy= test_5136_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5136_cfg["account_name_1"].format(random_id)
        email_id_1= test_5136_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow GetObject api on object in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource']= bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(
            "Step 2: Created a policy json and Allow GetObject api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object. - run from account1")
        resp= self.s3test_obj_1.object_download(
            bucket_name,
            object_names[0],
            test_5136_cfg["obj_name_download"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object. - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Apply READ_ACP ACL on the object to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read_acp=test_5136_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Applied READ_ACP ACL on the object to account2. - run from default account")
        LOGGER.info(
            "Step 9: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 9: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info(
            "Step 10 & 11: Account switch"
            "Get object. - run from account1")
        resp= self.s3test_obj_1.object_download(
            bucket_name,
            object_names[0],
            test_5136_cfg["obj_name_download"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 10 & 11: Account switch"
            "Get object. - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow GetObject api on object in policy and READ_ACP ACL on the object ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-18453")
    @CTFailOn(error_handler)
    def test_6555(self):
        """
        Test Bucket Policy Multiple Conditions each Condition with Multiple Keys and Multiple Values

        """
        LOGGER.info(
            "STARTED: Test Bucket Policy Multiple Conditions "
            "each Condition with Multiple Keys and Multiple Values")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6555_cfg= BKT_POLICY_CONF["test_6555"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6555_cfg["bucket_name"]
        err_message= test_6555_cfg["error_message"]
        bucket_policy= test_6555_cfg["bucket_policy"]
        object_lst= []
        LOGGER.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            bucket_name, test_6555_cfg["obj_count"], obj_prefix, object_lst)

        acc_details= IAM_OBJ.create_multiple_accounts(
            test_6555_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account2_id= acc_details[1][0][1]["Account_Id"]
        account2_cid= acc_details[1][0][1]["canonical_id"]
        account3_cid= acc_details[1][1][1]["canonical_id"]
        account4_cid= acc_details[1][2][1]["canonical_id"]
        account5_cid= acc_details[1][3][1]["canonical_id"]
        account6_cid= acc_details[1][4][1]["canonical_id"]
        account7_cid= acc_details[1][5][1]["canonical_id"]
        account8_cid= acc_details[1][6][1]["canonical_id"]
        account9_cid= acc_details[1][7][1]["canonical_id"]
        S3_OBJ1= s3_acl_test_lib.S3AclTestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])
        S3_OBJ2= s3_test_lib.S3TestLib(
            access_key=acc_details[1][0][1]["access_key"],
            secret_key=acc_details[1][0][1]["secret_key"])

        LOGGER.info(
            "Step 2:Create a json file for  a Bucket Policy having Multiple Conditions with Multiple Keys "
            "and each Key having Multiple Values. Action - Put Object and Effect - Allow")
        policy_id= f"Policy{uuid.uuid4()}"
        policy_sid= f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]= bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]= bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account2_id)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"].format(
                [account2_cid, account3_cid])
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"].format(
                [account4_cid, account5_cid])
        bucket_policy["Statement"][0]["Condition"]["StringLike"]["s3:x-amz-grant-full-control"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"].format(
                [account6_cid, account7_cid])
        bucket_policy["Statement"][0]["Condition"]["StringLike"]["s3:x-amz-grant-read"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-read"].format(
                [account8_cid, account9_cid])
        LOGGER.info(
            "Step 3:Put the bucket policy on the bucket and Get Bucket Policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 4 : Verify the Bucket Policy from cross account")
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Put object with ACL : grant_full_control and grant_read")
        resp= ACL_OBJ.put_object_with_acl2(bucket_name,
                                            "{}{}".format(
                                                object_lst[0], str(time.time())),
                                            BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                            grant_full_control="id={}".format(
                                                account2_cid),
                                            grant_read="id={}".format(account4_cid))
        assert resp[0], resp[1]
        resp= ACL_OBJ.put_object_with_acl2(bucket_name,
                                            "{}{}".format(
                                                object_lst[0], str(time.time())),
                                            BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                            grant_full_control="id={}".format(
                                                account3_cid),
                                            grant_read="id={}".format(account5_cid))
        assert resp[0], resp[1]
        try:
            S3_OBJ1.put_object_with_acl2(bucket_name,
                                         "{}{}".format(
                                             object_lst[0], str(time.time())),
                                         BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                         grant_full_control="id={}".format(
                                             account6_cid),
                                         grant_read="id={}".format(account4_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl2(bucket_name,
                                         "{}{}".format(
                                             object_lst[0], str(time.time())),
                                         BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                         grant_full_control="id={}".format(
                                             account2_cid),
                                         grant_read="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(bucket_name,
                                        "{}{}".format(
                                            object_lst[0], str(time.time())),
                                        BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                        grant_full_control="id={}".format(account3_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(bucket_name,
                                        "{}{}".format(
                                            object_lst[0], str(time.time())),
                                        BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                        grant_read="id={}".format(account5_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(bucket_name,
                                        "{}{}".format(
                                            object_lst[0], str(time.time())),
                                        BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                        grant_full_control="id={}".format(account4_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ1.put_object_with_acl(bucket_name,
                                        "{}{}".format(
                                            object_lst[0], str(time.time())),
                                        BKT_POLICY_CONF["bucket_policy"]["file_path"],
                                        grant_read="id={}".format(account2_cid))
        except CTException as error:
            assert err_message in error.message, error.message
        try:
            S3_OBJ2.put_object(
                bucket_name,
                object_lst[0],
                BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            assert err_message in error.message, error.message
        LOGGER.info(
            "ENDED: Bucket Policy Multiple Conditions each "
            "Condition with Multiple Keys and Multiple Values")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8040")
    @CTFailOn(error_handler)
    def test_5138(self):
        """
        Test apply allow GetobjectAcl api on object in policy and WRITE_ACP ACL on the object.
        """
        LOGGER.info(
            "STARTED: Test apply allow GetobjectAcl api on object in policy and WRITE_ACP ACL on the object."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5138_cfg= BKT_POLICY_CONF["test_5138"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5138_cfg["bucket_name"]
        bucket_policy= test_5138_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5138_cfg["account_name_1"].format(random_id)
        email_id_1= test_5138_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow GetObjectAcl api on object in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource']= bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(
            "Step 2: Created a policy json and Allow GetObjectAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Apply WRITE_ACP ACL on the object to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_write_acp=test_5138_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Applied WRITE_ACP ACL on the object to account2. - run from default account")
        LOGGER.info(
            "Step 9: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 9: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow GetobjectAcl api on object in policy and WRITE_ACP ACL on the object."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8039")
    @CTFailOn(error_handler)
    def test_5121(self):
        """
        Test apply WRITE_ACP ACL on the object and deny PutobjectAcl on object api in policy .
        """
        LOGGER.info(
            "STARTED: Test apply WRITE_ACP ACL on the object and deny PutobjectAcl on object api in policy ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5121_cfg= BKT_POLICY_CONF["test_5121"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5121_cfg["bucket_name"]
        bucket_policy= test_5121_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5121_cfg["account_name_1"].format(random_id)
        email_id_1= test_5121_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply WRITE_ACP ACL on the object to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_write_acp=test_5121_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Apply WRITE_ACP ACL on the object to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch"
                    "Put object ACL. - run from account1")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_write_acp=test_5121_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info("Step 4 & 5: Put object ACL. - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            " Create a policy json and Deny PutObjectAcl api on object in policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Created a policy json and Deny PutObjectAcl api on object in policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch"
                    "Put object ACL - run from account1")
        try:
            ACL_OBJ_1.put_object_with_acl(
                bucket_name=bucket_name,
                key=object_names[0],
                file_path=bkt_policy_cfg["file_path"],
                grant_write_acp=test_5121_cfg["id_str"].format(canonical_id_user_1))
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5121_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch "
                    "put object ACL - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply WRITE_ACP ACL on the object and deny PutobjectAcl on object api in policy ."
        )

    # Cannot Automate as invalid JSON is used
    # def test_6556(self):
    #     """
    #     Test Bucket Policy Multiple Conditions having duplicate Condition types (operators)
    #     :avocado: tags=bkt_policy_multi_keys_values
    #     """

    # Cannot Automate as invalid JSON is used
    # def test_6558(self):
    #     """
    #     Test Bucket Policy Multiple duplicate Condition Keys in Single Condition is not allowed
    #     :avocado: tags=bkt_policy_multi_keys_values
    #     """

    @pytest.mark.s3
    @pytest.mark.tags("TEST-18454")
    @CTFailOn(error_handler)
    def test_6557(self):
        """
        Test Bucket Policy Multiple Conditions having one Invalid Condition

        """
        LOGGER.info(
            "STARTED: Test Bucket Policy Multiple Conditions having one Invalid Condition")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6555_cfg= BKT_POLICY_CONF["test_6555"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6555_cfg["bucket_name"]
        err_message= test_6555_cfg["error_message"]
        bucket_policy= test_6555_cfg["bucket_policy"]
        object_lst= []
        LOGGER.info(
            "Step 1 : Create a bucket and upload objects in the bucket")
        self.create_bucket_put_objects(
            bucket_name, test_6555_cfg["obj_count"], obj_prefix, object_lst)

        acc_details= IAM_OBJ.create_multiple_accounts(
            test_6555_cfg["acc_count"], bkt_policy_cfg["acc_name_prefix"])
        account2_id= acc_details[1][0][1]["Account_Id"]
        account2_cid= acc_details[1][0][1]["canonical_id"]
        account3_cid= acc_details[1][1][1]["canonical_id"]
        LOGGER.info(
            "Step 2 : Create a json file for  a Bucket Policy having one Invalid Condition. "
            "Action - Put Object and Effect - Allow.")
        policy_id= f"Policy{uuid.uuid4()}"
        policy_sid= f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]= bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]= bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Principal"]["AWS"]= \
            bucket_policy["Statement"][0]["Principal"]["AWS"].format(
                account2_id)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"]= \
            bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:x-amz-grant-full-control"].format(
                [account2_cid, account3_cid])
        LOGGER.info("Applying policy to a bucket {0}".format(bucket_name))
        bkt_policy_json= json.dumps(bucket_policy)
        LOGGER.info(
            "Step 3 : Put policy on the bucket")
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            assert err_message in error.message, error.message
        LOGGER.info(
            "ENDED: Test Bucket Policy Multiple Conditions having one Invalid Condition")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8036")
    @CTFailOn(error_handler)
    def test_5118(self):
        """
        Test apply READ ACL on the object and deny GetObject api on object in policy .
        """
        LOGGER.info(
            "STARTED: Test apply READ ACL on the object and deny GetObject api on object in policy ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5118_cfg= BKT_POLICY_CONF["test_5118"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5118_cfg["bucket_name"]
        bucket_policy= test_5118_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5118_cfg["account_name_1"].format(random_id)
        email_id_1= test_5118_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        self.s3test_obj_1= result_1[1]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply READ ACL on the object to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read=test_5118_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied READ ACL on the object to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch "
                    "Get object. - run from account1")
        resp= self.s3test_obj_1.object_download(
            bucket_name,
            object_names[0],
            test_5118_cfg["obj_name_download"])
        assert resp[0], resp[1]
        LOGGER.info("Step 4 & 5: Account switch"
                    " Get object. - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny GetObject api on object in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch"
            " Created a policy json and Deny GetObject api on object in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch"
                    "Get object. - run from account1")
        try:
            self.s3test_obj_1.object_download(
                bucket_name,
                object_names[0],
                test_5118_cfg["obj_name_download"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5118_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch"
                    "Get object.  - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply READ ACL on the object and deny GetObject api on object in policy ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7939")
    @CTFailOn(error_handler)
    def test_5115(self):
        """
        Test apply READ_ACP ACL on the bucket and deny GetBucketAcl on bucket api in policy.
        """
        LOGGER.info(
            "STARTED: Test apply READ_ACP ACL on the bucket and deny GetBucketAcl on bucket api in policy."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5115_cfg= BKT_POLICY_CONF["test_5115"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5115_cfg["bucket_name"]
        bucket_policy= test_5115_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5115_cfg["account_name_1"].format(random_id)
        email_id_1= test_5115_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5115_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read_acp=test_5115_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch"
                    "Get ACL of the bucket . - run from account1")
        resp= ACL_OBJ_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4 & 5: Got ACL of the bucket . - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny GetBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Created a policy json and Deny GetBucketAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch "
                    "Get ACL of the bucket -run from account1")
        try:
            ACL_OBJ_1.get_bucket_acl(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5115_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 10 & 11: Get ACL of the bucket  -run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply READ_ACP ACL on the bucket and deny GetBucketAcl on bucket api in policy."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7938")
    @CTFailOn(error_handler)
    def test_5114(self):
        """
        Test apply WRITE ACL on the bucket and deny PutObject api on bucket in policy.
        """
        LOGGER.info(
            "STARTED: Test apply WRITE ACL on the bucket and deny PutObject api on bucket in policy."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5114_cfg= BKT_POLICY_CONF["test_5114"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5114_cfg["bucket_name"]
        bucket_policy= test_5114_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5114_cfg["account_name_1"].format(random_id)
        email_id_1= test_5114_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5114_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write=test_5114_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch"
                    "Put object in the bucket . - run from account1")
        obj_name= "{0}{1}".format(
            obj_prefix, str(int(time.time())))
        resp= self.s3test_obj_1.put_object(
            bucket_name, obj_name, BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4 & 5: Put object in the bucket . - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny PutObject api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Created a policy json and Deny PutObject api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch "
                    "Put object in the bucket -run from account1")
        try:
            self.s3test_obj_1.put_object(
                bucket_name, obj_name, BKT_POLICY_CONF["bucket_policy"]["file_path"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5114_cfg["error_message"] in error.message, error.message
        LOGGER.info(
            "Step 10 & 11: Put object in the bucket  -run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply WRITE ACL on the bucket and deny PutObject api on bucket in policy."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7937")
    @CTFailOn(error_handler)
    def test_5110(self):
        """
        Test apply READ ACL on the bucket and deny ListBucket api on bucket in policy.
        """
        LOGGER.info(
            "STARTED: Test apply READ ACL on the bucket and deny ListBucket api on bucket in policy."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5110_cfg= BKT_POLICY_CONF["test_5110"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5110_cfg["bucket_name"]
        bucket_policy= test_5110_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5110_cfg["account_name_1"].format(random_id)
        email_id_1= test_5110_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5110_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read=test_5110_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch "
                    "List object in the bucket . - run from account1")
        self.list_objects_with_diff_acnt(bucket_name, self.s3test_obj_1)
        LOGGER.info("Step 4 & 5: "
                    "Listed object in the bucket . - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny ListBucket api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Created a policy json and Deny ListBucket api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch"
                    "List objects from the bucket -run from account1")
        try:
            self.s3test_obj_1.object_list(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5110_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch "
                    "List objects from the bucket  -run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply READ ACL on the bucket and deny ListBucket api on bucket in policy."
        )

    # Commented this test case as it is failing in current build and a bug was
    # already raised for this - EOS-7062
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7940")
    @CTFailOn(error_handler)
    def test_5116(self):
        """
        Test apply WRITE_ACP ACL on the bucket and deny PutBucketAcl on bucket api in policy .
        """
        LOGGER.info(
            "STARTED: Test apply WRITE_ACP ACL on the bucket and deny PutBucketAcl on bucket api in policy ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5116_cfg= BKT_POLICY_CONF["test_5116"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5116_cfg["bucket_name"]
        bucket_policy= test_5116_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5116_cfg["account_name_1"].format(random_id)
        email_id_1= test_5116_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5116_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write_acp=test_5116_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch"
                    "Put ACL on the bucket . - run from account1")
        resp= ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write_acp=test_5116_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info("Step 4 & 5: Account switch "
                    "Put ACL on the bucket . - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny PutBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal']['CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Created a policy json and Deny PutBucketAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch"
                    "Put ACL of the bucket -run from account1")
        try:
            ACL_OBJ_1.put_bucket_acl(
                bucket_name=bucket_name,
                grant_write_acp=test_5116_cfg["id_str"].format(canonical_id_user_1))
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5116_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch"
                    "Put ACL of the bucket  -run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply WRITE_ACP ACL on the bucket and deny PutBucketAcl on bucket api in policy."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7941")
    @CTFailOn(error_handler)
    def test_5117(self):
        """
        Test apply FULL_CONTROL ACL on the bucket and deny GetBucketAcl on bucket api in policy .
        """
        LOGGER.info(
            "STARTED: Test apply FULL_CONTROL ACL on the bucket and deny GetBucketAcl on bucket api in policy ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5117_cfg= BKT_POLICY_CONF["test_5117"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5117_cfg["bucket_name"]
        bucket_policy= test_5117_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5117_cfg["account_name_1"].format(random_id)
        email_id_1= test_5117_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5117_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply FULL_CONTROL ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_full_control=test_5117_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied FULL_CONTROL ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the bucket ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the bucket ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch "
                    "Get ACL of the bucket . - run from account1")
        resp= ACL_OBJ_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 4 & 5: Account switch"
                    "Get ACL of the bucket . - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Create a policy json and Deny GetBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch "
            "Created a policy json and Deny GetBucketAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch "
                    "Get ACL of the bucket - run from account1")
        try:
            ACL_OBJ_1.get_bucket_acl(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5117_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch "
                    "Get ACL of the bucket  - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply FULL_CONTROL ACL on the bucket and deny GetBucketAcl on bucket api in policy ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7943")
    @CTFailOn(error_handler)
    def test_5120(self):
        """
        Test apply READ_ACP ACL on the object and deny GetobjectAcl on object api in policy .
        """
        LOGGER.info(
            "STARTED: Test apply READ_ACP ACL on the object and deny GetobjectAcl on object api in policy ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5120_cfg= BKT_POLICY_CONF["test_5120"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5120_cfg["bucket_name"]
        bucket_policy= test_5120_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5120_cfg["account_name_1"].format(random_id)
        email_id_1= test_5120_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply READ_ACP ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read_acp=test_5120_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Applied READ_ACP ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch"
                    "Get object ACL. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4 & 5: Account switch "
                    "Get object ACL. - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny GetObjectAcl api on object in policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch"
            " Created a policy json and Deny GetObjectAcl api on object in policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch "
                    "Get object ACL - run from account1")
        try:
            ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                     object_key=object_names[0])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5120_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch"
                    "Get object ACL - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply READ_ACP ACL on the object and deny GetobjectAcl on object api in policy ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7945")
    @CTFailOn(error_handler)
    def test_5122(self):
        """
        Test apply FULL_CONTROL ACL on the object and deny GetobjectAcl on object api in policy .
        """
        LOGGER.info(
            "STARTED: Test apply FULL_CONTROL ACL on the object and deny GetobjectAcl on object api in policy ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5122_cfg= BKT_POLICY_CONF["test_5122"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5122_cfg["bucket_name"]
        bucket_policy= test_5122_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5122_cfg["account_name_1"].format(random_id)
        email_id_1= test_5122_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Apply FULL_CONTROL ACL on the object to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_full_control=test_5122_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Apply FULL_CONTROL ACL on the object to account2. - run from default account")
        LOGGER.info(
            "Step 3: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info("Step 4 & 5: Account switch "
                    "Get object ACL. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4 & 5: Account switch"
                    "Get object ACL. - run from account1")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Create a policy json and Deny GetObjectAcl api on object in policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Created a policy json and Denid GetObjectAcl api on object in policy to account2.- run from default account")
        LOGGER.info(
            "Step 8 & 9: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 8 & 9: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 10 & 11: Account switch "
                    "Get object ACL - run from account1")
        try:
            ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                     object_key=object_names[0])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_5122_cfg["error_message"] in error.message, error.message
        LOGGER.info("Step 10 & 11: Account switch "
                    "Get object ACL - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply FULL_CONTROL ACL on the object and deny GetobjectAcl on object api in policy ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7946")
    @CTFailOn(error_handler)
    def test_5123(self):
        """
        Test apply allow ListBucket api on bucket in policy and WRITE ACL on the bucket.
        """
        LOGGER.info(
            "STARTED: Test apply allow ListBucket api on bucket in policy and WRITE ACL on the bucket."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5123_cfg= BKT_POLICY_CONF["test_5123"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5123_cfg["bucket_name"]
        bucket_policy= test_5123_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5123_cfg["account_name_1"].format(random_id)
        email_id_1= test_5123_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5123_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and allow ListBucket api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 2: Created a policy json and allow ListBucket api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 5 & 6: Account switch"
                    "List objects in the bucket - run from account1")
        self.list_objects_with_diff_acnt(bucket_name, self.s3test_obj_1)
        LOGGER.info("Step 5 & 6: Account switch "
                    "List objects in the bucket - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Apply WRITE ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write=test_5123_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Applied WRITE ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 9: Check the bucket ACL to verify and applied ACL. - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 9: Check the bucket ACL to verify and applied ACL. - run from default account")
        LOGGER.info("Step 10 & 11: Account switch "
                    "List objects from the bucket - run from account1")
        self.list_objects_with_diff_acnt(bucket_name, self.s3test_obj_1)
        LOGGER.info("Step 10 & 11: Account switch"
                    "List objects from the bucket - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow ListBucket api on bucket in policy and WRITE ACL on the bucket."
        )

    # Commented this test case as it is failing in current build and a bug was
    # already raised for this - EOS-7062

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7947")
    @CTFailOn(error_handler)
    def test_5126(self):
        """
        Test apply allow PutBucketAcl api on bucket in policy and READ_ACP ACL on the bucket.
        """
        LOGGER.info(
            "STARTED: Test apply allow PutBucketAcl api on bucket in policy and READ_ACP ACL on the bucket."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5126_cfg= BKT_POLICY_CONF["test_5126"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5126_cfg["bucket_name"]
        bucket_policy= test_5126_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5126_cfg["account_name_1"].format(random_id)
        email_id_1= test_5126_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        S3_BKT_POLICY_OBJ_1= result_1[3]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5126_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and allow PutBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal']['CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 2: Create a policy json and allow PutBucketAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Apply READ_ACP ACL on the bucket to account2. - run from account1")
        resp= ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read_acp=test_5126_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch "
            "Applied READ_ACP ACL on the bucket to account2. - run from account1")
        LOGGER.info(
            "Step 7: Check the bucket ACL to verify and applied ACL. - run from account1")
        resp= ACL_OBJ_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7: Check the bucket ACL to verify and applied ACL. - run from account1")
        LOGGER.info("Step 8: Put bucket ACL - run from account1")
        resp= ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read_acp=test_5126_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info("Step 8: Put bucket ACL - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow PutBucketAcl api on bucket in policy and READ_ACP ACL on the bucket."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7936")
    @CTFailOn(error_handler)
    def test_5124(self):
        """
        Test apply allow PutObject api on bucket in policy and READ ACL on the bucket.
        """
        LOGGER.info(
            "STARTED: Test apply allow PutObject api on bucket in policy and READ ACL on the bucket."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5124_cfg= BKT_POLICY_CONF["test_5124"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5124_cfg["bucket_name"]
        bucket_policy= test_5124_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5124_cfg["account_name_1"].format(random_id)
        email_id_1= test_5124_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5124_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow PutObject api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 2: Created a policy json and Allow PutObject api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "upload new objects in the bucket. - run from account1")
        obj_name= "{0}{1}".format(
            obj_prefix, str(int(time.time())))
        resp= self.s3test_obj_1.put_object(
            bucket_name, obj_name, bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "uploaded new object in the bucket. - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Apply READ ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read=test_5124_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Applied READ ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        LOGGER.info("Step 10 & 11: Account switch"
                    "Put object in the bucket . - run from account1")
        resp= self.s3test_obj_1.put_object(
            bucket_name, obj_name, BKT_POLICY_CONF["bucket_policy"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 10 & 11: Put object in the bucket . - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow PutObject api on bucket in policy and READ ACL on the bucket."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7944")
    @CTFailOn(error_handler)
    def test_5125(self):
        """
        Test apply allow GetBucketAcl api on bucket in policy and WRITE_ACP ACL on the bucket.
        """
        LOGGER.info(
            "STARTED: Test apply allow GetBucketAcl api on bucket in policy and WRITE_ACP ACL on the bucket."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5125_cfg= BKT_POLICY_CONF["test_5125"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5125_cfg["bucket_name"]
        bucket_policy= test_5125_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5125_cfg["account_name_1"].format(random_id)
        email_id_1= test_5125_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_5125_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow GetBucketAcl api on bucket in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(
            str(canonical_id_user_1))
        LOGGER.info(
            "Step 2: Created a policy json and Allow GetBucketAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get ACL's of the bucket - run from account1")
        resp= ACL_OBJ_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get ACL's of the bucket - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Apply WRITE_ACP ACL on the bucket to account2. - run from default account")
        resp= ACL_OBJ.put_bucket_acl(
            bucket_name=bucket_name,
            grant_write_acp=test_5125_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Applied WRITE_ACP ACL on the bucket to account2. - run from default account")
        LOGGER.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        resp= ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 9: Check the bucket ACL to verify the applied ACL. - run from default account")
        LOGGER.info("Step 10 & 11: Account switch"
                    "Get bucket ACL. - run from account1")
        resp= ACL_OBJ_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 10 & 11:  Account switch"
            "Get bucket ACL - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow GetBucketAcl api on bucket in policy and WRITE_ACP ACL on the bucket."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7942")
    @CTFailOn(error_handler)
    def test_5137(self):
        """
        Test apply allow GetobjectAcl api on object in policy and READ ACL on the object .
        """
        LOGGER.info(
            "STARTED: Test apply allow GetobjectAcl api on object in policy and READ ACL on the object ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_5137_cfg= BKT_POLICY_CONF["test_5137"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_5137_cfg["bucket_name"]
        bucket_policy= test_5137_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_5137_cfg["account_name_1"].format(random_id)
        email_id_1= test_5137_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        canonical_id_user_1= result_1[0]
        ACL_OBJ_1= result_1[2]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow GetObjectAcl api on object in the policy to account2.- run from default account")
        bucket_policy['Statement'][0]['Principal']['CanonicalUser']= bucket_policy['Statement'][0]['Principal'][
            'CanonicalUser'].format(str(canonical_id_user_1))
        bucket_policy['Statement'][0]['Resource']= bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(
            "Step 2: Created a policy json and Allow GetObjectAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object ACL. - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Apply READ ACL on the object to account2. - run from default account")
        resp= ACL_OBJ.put_object_with_acl(
            bucket_name=bucket_name,
            key=object_names[0],
            file_path=bkt_policy_cfg["file_path"],
            grant_read=test_5137_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Applied READ ACL on the object to account2. - run from default account")
        LOGGER.info(
            "Step 9: Check the object ACL to verify the applied ACL.  - run from default account")
        resp= ACL_OBJ.get_object_acl(bucket=bucket_name,
                                      object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 9: Checked the object ACL to verify the applied ACL.  - run from default account")
        LOGGER.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 10 & 11: Account switch"
            "Get object ACL. - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test apply allow GetobjectAcl api on object in policy and READ ACL on the object."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9031")
    @CTFailOn(error_handler)
    def test_6967(self):
        """
        Test bucket policy authorization on bucket with API ListBucket
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API ListBucket"
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6967_cfg= BKT_POLICY_CONF["test_6967"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6967_cfg["bucket_name"]
        bucket_policy= test_6967_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6967_cfg["account_name_1"].format(random_id)
        email_id_1= test_6967_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_6967_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 5 & 6: Account switch "
                    "List object in the bucket . - run from account1")
        self.list_objects_with_diff_acnt(bucket_name, self.s3test_obj_1)
        LOGGER.info("Step 5 & 6: "
                    "Listed object in the bucket . - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API ListBucket"
        )

    # Defect raised for this test cases - EOS-7062

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9033")
    @CTFailOn(error_handler)
    def test_6969(self):
        """
        Test bucket policy authorization on bucket with API PutBucketAcl .
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API PutBucketAcl ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6969_cfg= BKT_POLICY_CONF["test_6969"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6969_cfg["bucket_name"]
        bucket_policy= test_6969_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6969_cfg["account_name_1"].format(random_id)
        email_id_1= test_6969_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        ACL_OBJ_1= result_1[2]
        account_id_1= result_1[6]
        canonical_id_user_1= result_1[0]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_6969_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 5 & 6: Account switch"
                    "Put ACL on account1 bucket . - run from account1")
        resp= ACL_OBJ_1.put_bucket_acl(
            bucket_name=bucket_name,
            grant_read_acp=bkt_policy_cfg["id_str"].format(canonical_id_user_1))
        assert resp[0], resp[1]
        LOGGER.info("Step 5 & 6: Account switch "
                    "Put ACL on account1 bucket . - run from account1")
        LOGGER.info("Step 7: Get acl of bucket - run from account1")
        resp= ACL_OBJ_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 7: Get acl of bucket - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API PutBucketAcl ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9038")
    @CTFailOn(error_handler)
    def test_6991(self):
        """
        Test bucket policy authorization on bucket with API PutBucketPolicy
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API PutBucketPolicy"
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6991_cfg= BKT_POLICY_CONF["test_6991"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6991_cfg["bucket_name"]
        bucket_policy= test_6991_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6991_cfg["account_name_1"].format(random_id)
        email_id_1= test_6991_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        S3_BKT_POLICY_OBJ_1= result_1[3]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_6991_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        try:
            S3_BKT_POLICY_OBJ_1.put_bucket_policy(
                bucket_name, bucket_policy)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6991_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 6: Applying policy on a bucket using user of account 2 is failed with error {0}".format(
                    test_6991_cfg["error_message"]))
        LOGGER.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API PutBucketPolicy"
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9039")
    @CTFailOn(error_handler)
    def test_6992(self):
        """
        Test bucket policy authorization on bucket with API GetBucketPolicy.
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketPolicy."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6992_cfg= BKT_POLICY_CONF["test_6992"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6992_cfg["bucket_name"]
        bucket_policy= test_6992_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6992_cfg["account_name_1"].format(random_id)
        email_id_1= test_6992_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        S3_BKT_POLICY_OBJ_1= result_1[3]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_6992_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        try:
            S3_BKT_POLICY_OBJ_1.get_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6992_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 6: Applying policy on a bucket using user of account 2 is failed with error {0}".format(
                    test_6992_cfg["error_message"]))
        LOGGER.info(
            "Step 5 & 6: Account switch "
            "Put bucket policy of account1 bucket - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketPolicy."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9041")
    @CTFailOn(error_handler)
    def test_6999(self):
        """
        Test bucket policy authorization on object with API GetObject .
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API GetObject ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6999_cfg= BKT_POLICY_CONF["test_6999"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6999_cfg["bucket_name"]
        bucket_policy= test_6999_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6999_cfg["account_name_1"].format(random_id)
        email_id_1= test_6999_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json and Allow GetObjectAcl api on object in the policy to account2.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        bucket_policy['Statement'][0]['Resource']= bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json and Allow GetObjectAcl api on bucket in the policy to account2.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object of default account bucket. - run from account1")
        resp= self.s3test_obj_1.object_download(
            bucket_name,
            object_names[0],
            test_6999_cfg["obj_name_download"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object of default account bucket - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API GetObject ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9042")
    @CTFailOn(error_handler)
    def test_7000(self):
        """
        Test bucket policy authorization on object with API GetObjectAcl .
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API GetObjectAcl ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_7000_cfg= BKT_POLICY_CONF["test_7000"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_7000_cfg["bucket_name"]
        bucket_policy= test_7000_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_7000_cfg["account_name_1"].format(random_id)
        email_id_1= test_7000_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        ACL_OBJ_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, str(int(time.time())), str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        bucket_policy['Statement'][0]['Resource']= bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object acl of default account bucket. - run from account1")
        resp= ACL_OBJ_1.get_object_acl(bucket=bucket_name,
                                        object_key=object_names[0])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get object acl of default account bucket - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API GetObjectAcl ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9032")
    @CTFailOn(error_handler)
    def test_6968(self):
        """
        Test bucket policy authorization on bucket with API ListBucketMultipartUploads.
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API ListBucketMultipartUploads."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6968_cfg= BKT_POLICY_CONF["test_6968"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6968_cfg["bucket_name"]
        bucket_policy= test_6968_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6968_cfg["account_name_1"].format(random_id)
        email_id_1= test_6968_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        S3_MULTIPART_OBJ_1= result_1[8]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket - run from default account")
        obj_name= "{0}{1}".format(obj_prefix, random_id)
        LOGGER.info(
            "Step 2: Create a multipart upload on the bucket - run from default account")
        resp= S3_MULTIPART_OBJ.create_multipart_upload(bucket_name, obj_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Created a multipart upload on the bucket - run from default account")
        LOGGER.info(
            "Step 3: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 3: Created a policy json.- run from default account")
        LOGGER.info(
            "Step 4 & 5: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 4 & 5: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "List bucket multipart - run from account1")
        resp= S3_MULTIPART_OBJ_1.list_multipart_uploads(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Listed bucket multipart - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API ListBucketMultipartUploads."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9034")
    @CTFailOn(error_handler)
    def test_6978(self):
        """
        Test bucket policy authorization on bucket with API GetBucketTagging.
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketTagging."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6978_cfg= BKT_POLICY_CONF["test_6978"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6978_cfg["bucket_name"]
        bucket_policy= test_6978_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6978_cfg["account_name_1"].format(random_id)
        email_id_1= test_6978_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        s3_bkt_tag_obj_1= result_1[7]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket - run from default account")
        LOGGER.info(
            "Step 2: Put bucket tagging - run from default account")
        resp= S3_TAG_OBJ.set_bucket_tag(bucket_name,
                                         key=test_6978_cfg["key"],
                                         value=test_6978_cfg["value"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 2: Put bucket tagging - run from default account")
        LOGGER.info(
            "Step 3: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 3: Created a policy json.- run from default account")
        LOGGER.info(
            "Step 4 & 5: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 4 & 5: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Get bucket tagging - run from account1")
        resp= s3_bkt_tag_obj_1.get_bucket_tagging(bucket_name)
        assert resp[test_6978_cfg["tagset"]][0][
                        test_6978_cfg["key_val"]] == test_6978_cfg["key1_validate"], resp
        assert resp[test_6978_cfg["tagset"]][0][
                        test_6978_cfg["value_val"]] == test_6978_cfg["key2_validate"], resp
        LOGGER.info(
            "Step 6 & 7: Account switch"
            "Get bucket tagging - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketTagging."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9035")
    @CTFailOn(error_handler)
    def test_6987(self):
        """
        Test bucket policy authorization on bucket with API GetBucketLocation.
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketLocation."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6987_cfg= BKT_POLICY_CONF["test_6987"]
        bucket_name= test_6987_cfg["bucket_name"]
        bucket_policy= test_6987_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6987_cfg["account_name_1"].format(random_id)
        email_id_1= test_6987_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        s3_bkt_tag_obj_1= result_1[7]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get bucket location - run from account1")
        resp= s3_bkt_tag_obj_1.bucket_location(bucket_name)
        assert resp[test_6987_cfg["loc"]] == test_6987_cfg["exp_loc"], resp
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Get bucket location - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketLocation."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9036")
    @CTFailOn(error_handler)
    def test_6988(self):
        """
        Test bucket policy authorization on bucket with API PutBucketTagging .
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API PutBucketTagging ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6988_cfg= BKT_POLICY_CONF["test_6988"]
        bucket_name= test_6988_cfg["bucket_name"]
        bucket_policy= test_6988_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6988_cfg["account_name_1"].format(random_id)
        email_id_1= test_6988_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        s3_bkt_tag_obj_1= result_1[7]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Put bucket tagging - run from account1")
        resp= s3_bkt_tag_obj_1.set_bucket_tag(bucket_name,
                                               key=test_6988_cfg["key"],
                                               value=test_6988_cfg["value"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Put bucket tagging - run from account1")
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Get bucket tagging - run from default")
        resp= S3_TAG_OBJ.get_bucket_tagging(bucket_name)
        assert resp[test_6988_cfg["tagset"]][0][
                        test_6988_cfg["key_val"]] == test_6988_cfg["key1_validate"], resp
        assert resp[test_6988_cfg["tagset"]][0][
                        test_6988_cfg["value_val"]] == test_6988_cfg["key2_validate"], resp
        LOGGER.info(
            "Step 7 & 8: Account switch"
            "Get bucket tagging - run from default")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API PutBucketTagging ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9037")
    @CTFailOn(error_handler)
    def test_6990(self):
        """
        Test bucket policy authorization on bucket with API DeleteBucketPolicy.
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API DeleteBucketPolicy."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6990_cfg= BKT_POLICY_CONF["test_6990"]
        bucket_name= test_6990_cfg["bucket_name"]
        bucket_policy= test_6990_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6990_cfg["account_name_1"].format(random_id)
        email_id_1= test_6990_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        S3_BKT_POLICY_OBJ_1= result_1[3]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json.- run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json.- run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Delete bucket policy - run from account1")
        try:
            S3_BKT_POLICY_OBJ_1.delete_bucket_policy(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_6990_cfg["error_message"] in error.message, error.message
            LOGGER.info(
                "Step 6: Delete bucket policy is failed with error {0}".format(
                    test_6990_cfg["error_message"]))
        LOGGER.info(
            "Step 5 & 6: Account switch"
            "Delete bucket policy - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API DeleteBucketPolicy."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9040")
    @CTFailOn(error_handler)
    def test_6997(self):
        """
        Test bucket policy authorization on object with API DeleteObject .
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API DeleteObject ."
        )
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6997_cfg= BKT_POLICY_CONF["test_6997"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6997_cfg["bucket_name"]
        bucket_policy= test_6997_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6997_cfg["account_name_1"].format(random_id)
        email_id_1= test_6997_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp= create_file(
            BKT_POLICY_CONF["bucket_policy"]["file_path"],
            BKT_POLICY_CONF["bucket_policy"]["file_size"])
        assert resp[0], resp[1]
        object_names= []
        for i in range(bkt_policy_cfg["range_val"]):
            obj_name= "{0}{1}{2}".format(
                obj_prefix, random_id, str(i))
            resp= S3_OBJ.put_object(
                bucket_name, obj_name, bkt_policy_cfg["file_path"])
            assert resp[0], resp[1]
            object_names.append(obj_name)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        bucket_policy['Statement'][0]['Resource']= bucket_policy['Statement'][0]['Resource'].format(
            object_names[0])
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 5 & 6: Account switch "
                    "Delete object - run from account1")
        resp= self.s3test_obj_1.delete_object(
            bucket_name,
            object_names[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 5 & 6: Account switch "
                    "Delete object - run from account1")
        LOGGER.info("Step 7 & 8: Account switch "
                    "List object - run from default")
        resp= S3_OBJ.list_objects_with_prefix(
            bucket_name, prefix=BKT_POLICY_CONF["bucket_policy"]["obj_name_prefix"])
        assert resp[0], resp[1]
        LOGGER.info("Step 7 & 8: Account switch "
                    "List object - run from default")
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        S3_OBJ.delete_bucket(bucket_name, force=True)
        LOGGER.info("set put_bucket_acl to private as part of teardown.")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API DeleteObject ."
        )

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8721")
    @CTFailOn(error_handler)
    def test_1295(self):
        """
        Test Create Bucket Policy using StringNotEquals Condition Operator and Deny Action
        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringNotEquals Condition Operator and Deny Action")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_1295_cfg= BKT_POLICY_CONF["test_1295"]
        bucket_name= test_1295_cfg["bucket_name"]
        bucket_policy= test_1295_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating a bucket and uploading objects to it")
        self.create_bucket_put_objects(
            bucket_name,
            test_1295_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created a bucket and uploaded objects to it")
        LOGGER.info("Step 2: Creating a json for bucket policy")
        policy_id= f"Policy{uuid.uuid4()}"
        policy_sid= f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]= bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]= bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringNotEquals"]["s3:prefix"]= bucket_policy["Statement"][
            0]["Condition"]["StringNotEquals"]["s3:prefix"].format(bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info(bucket_policy)
        LOGGER.info("Step 2: Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Listing objects of bucket with prefix")
        try:
            resp= S3_OBJ.list_objects_with_prefix(
                bucket_name, prefix=bkt_policy_cfg["obj_name_prefix"])
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 3: Listed objects of bucket with prefix successfully")
            LOGGER.info("Step 4: Listing objects of bucket without prefix")
            try:
                S3_OBJ.object_list(bucket_name)
            except CTException as error:
                LOGGER.error(error.message)
                assert test_1295_cfg["err_message"] in error.message, error.message
            LOGGER.info(
                "Step 4: Listing objects of bucket without prefix failed with {0}".format(
                    test_1295_cfg["err_message"]))
        except CTException as error:
            LOGGER.error(error.message)
        finally:
            LOGGER.info(
                "Step 5: Deleting a bucket policy for bucket {0}".format(bucket_name))
            resp= S3_BKT_POLICY_OBJ.delete_bucket_policy(bucket_name)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 5: Deleted a bucket policy for bucket {0}".format(bucket_name))
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringNotEquals Condition Operator and Deny Action")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8722")
    @CTFailOn(error_handler)
    def test_1297(self):
        """
        Test Create Bucket Policy using StringEquals Condition Operator and Deny Action
        """
        LOGGER.info(
            "STARTED: Test Create Bucket Policy using StringEquals Condition Operator and Deny Action")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_1297_cfg= BKT_POLICY_CONF["test_1297"]
        bucket_name= test_1297_cfg["bucket_name"]
        bucket_policy= test_1297_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating a bucket and uploading objects to it")
        self.create_bucket_put_objects(
            bucket_name,
            test_1297_cfg["s3_obj_count"],
            bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created a bucket and uploaded objects to it")
        LOGGER.info("Step 2: Creating a json for bucket policy")
        policy_id= f"Policy{uuid.uuid4()}"
        policy_sid= f"Stmt{uuid.uuid4()}"
        bucket_policy["Id"]= bucket_policy["Id"].format(policy_id)
        bucket_policy["Statement"][0]["Sid"]= bucket_policy["Statement"][0]["Sid"].format(
            policy_sid)
        bucket_policy["Statement"][0]["Condition"]["StringEquals"]["s3:prefix"]= bucket_policy["Statement"][
            0]["Condition"]["StringEquals"]["s3:prefix"].format(bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info(bucket_policy)
        LOGGER.info("Step 2: Created a json for bucket policy")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Listing objects of bucket with prefix")
        try:
            S3_OBJ.list_objects_with_prefix(
                bucket_name, prefix=bkt_policy_cfg["obj_name_prefix"])
        except CTException as error:
            LOGGER.error(error.message)
            assert test_1297_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Listed objects of bucket with prefix failed with {0}".format(
                test_1297_cfg["err_message"]))
        LOGGER.info("Step 4: Listing objects of bucket without prefix")
        resp= S3_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Listing objects of bucket without prefix successfully")
        LOGGER.info(
            "ENDED: Test Create Bucket Policy using StringEquals Condition Operator and Deny Action")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8720")
    @CTFailOn(error_handler)
    def test_4598(self):
        """
        Test principal arn combination with account-id and user as root.
        """
        LOGGER.info(
            "STARTED: Test principal arn combination with account-id and user as root.")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_4598_cfg= BKT_POLICY_CONF["test_4598"]
        bucket_name= test_4598_cfg["bucket_name"]
        bucket_policy= test_4598_cfg["bucket_policy"]
        obj_count= test_4598_cfg["s3_obj_count"]
        acc_name= test_4598_cfg["account_name"]
        email_id= f"{acc_name}{bkt_policy_cfg['email_id']}"
        LOGGER.info("Step 1: Creating a bucket and uploading objects to it")
        self.create_bucket_put_objects(
            bucket_name, obj_count, bkt_policy_cfg["obj_name_prefix"])
        LOGGER.info("Step 1: Created a bucket and uploaded objects to it")
        resp= self.create_s3iamcli_acc(acc_name, email_id)
        account_id= resp[6]
        LOGGER.info("Step 2: Creating a json for bucket policy")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        LOGGER.info(bucket_policy)
        LOGGER.info("Step 2: Created a json for bucket policy")
        LOGGER.info("Step 3: Applying bucket policy on a bucket")
        bkt_policy_json= json.dumps(bucket_policy)
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(bucket_name, bkt_policy_json)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_4598_cfg["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Applying bucket policy on a bucket failed with {0}".format(
                test_4598_cfg["err_message"]))
        LOGGER.info(
            "ENDED: Test principal arn combination with account-id and user as root.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8702")
    @CTFailOn(error_handler)
    def test_7001(self):
        """
        Test bucket policy authorization on object with API PutObject"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API PutObject")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7001"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_OBJ_acc2= acc_details[1]
        account_id= acc_details[6]
        LOGGER.info(
            "Step 2: Creating a json to allow PutObject for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 2: Created a json to allow PutObject for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Uploading an object using account 2")
        resp= S3_OBJ_acc2.put_object(
            bucket_name, object_lst[0], bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Uploaded an object using account 2")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API PutObject")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8703")
    @CTFailOn(error_handler)
    def test_7002(self):
        """
        Test bucket policy authorization on object with API PutObjectAcl"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API PutObjectAcl")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7002"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        ACL_OBJ_acc2= acc_details[2]
        account_id= acc_details[6]
        canonical_id= acc_details[0]
        LOGGER.info(
            "Step 2: Creating a json to allow PutObjectAcl for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 2: Created a json to allow PutObjectAcl for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Give grant_read_acp permissions to account 2")
        resp= ACL_OBJ_acc2.put_object_canned_acl(
            bucket_name,
            object_lst[0],
            grant_read_acp=test_cfg["id_str"].format(canonical_id))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: grant_read_acp permission has been given to account 2")
        LOGGER.info("Step 4: Retrieving object acl using account 2")
        resp= ACL_OBJ_acc2.get_object_acl(bucket_name, object_lst[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Retrieved object acl using account 2")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API PutObjectAcl")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8704")
    @CTFailOn(error_handler)
    def test_7009(self):
        """
        Test bucket policy authorization on object with API PutObjectTagging"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API PutObjectTagging")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7009"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_TAG_OBJ_acc2= acc_details[7]
        account_id= acc_details[6]
        LOGGER.info(
            "Step 2: Creating a json to allow PutObjectTagging for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 2: Created a json to allow PutObjectTagging for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Setting tag to an object from account 2")
        resp= S3_TAG_OBJ_acc2.set_object_tag(
            bucket_name, object_lst[0], test_cfg["key"], test_cfg["value"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Tag was set to an object from account 2")
        LOGGER.info("Step 4: Retrieving tag of an object using account 1")
        resp= S3_TAG_OBJ.get_object_tags(bucket_name, object_lst[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Retrieved tag of an object using account 1")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API PutObjectTagging")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8705")
    @CTFailOn(error_handler)
    def test_7014(self):
        """
        Test bucket policy authorization on object with API GetObjectTagging"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API GetObjectTagging")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7014"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_TAG_OBJ_acc2= acc_details[7]
        account_id= acc_details[6]
        LOGGER.info("Step 2: Setting tag to an object")
        resp= S3_TAG_OBJ.set_object_tag(
            bucket_name,
            object_lst[0],
            test_cfg["key"],
            test_cfg["value"])
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Tag was set to an object")
        LOGGER.info(
            "Step 3: Creating a json to allow GetObjectTagging for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 3: Created a json to allow GetObjectTagging for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 4: Retrieving tag of an object using account 2")
        resp= S3_TAG_OBJ_acc2.get_object_tags(bucket_name, object_lst[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Retrieved tag of an object using account 2")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API GetObjectTagging")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8706")
    @CTFailOn(error_handler)
    def test_7015(self):
        """
        Test bucket policy authorization on object with API ListMultipartUploadParts"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API ListMultipartUploadParts")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7015"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        self.create_bucket_validate(bucket_name)
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        account_id= acc_details[6]
        s3_mp_obj_acc2= acc_details[8]
        LOGGER.info("Step 1: Initiating multipart upload")
        res= S3_MULTIPART_OBJ.create_multipart_upload(
            bucket_name, test_cfg["object_name"])
        assert res[0], res[1]
        mpu_id= res[1]["UploadId"]
        LOGGER.info(
            "Step 1: Multipart Upload initiated with mpu_id {0}".format(mpu_id))
        LOGGER.info("Step 2: Uploading parts into bucket")
        resp= S3_MULTIPART_OBJ.upload_parts(
            mpu_id,
            bucket_name,
            test_cfg["object_name"],
            test_cfg["file_size"],
            test_cfg["total_parts"],
            bkt_policy_cfg["file_path"])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(len(resp[1]), test_cfg["total_parts"], resp[1])
        parts= res[1]
        LOGGER.info("Step 2: Uploaded parts into bucket: {0}".format(parts))
        LOGGER.info(
            "Step 3: Creating a json to allow ListMultipartUploadParts for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, test_cfg["object_name"])
        LOGGER.info(
            "Step 3: Created a json to allow ListMultipartUploadParts for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 4: Listing parts of multipart upload using account 2")
        resp= s3_mp_obj_acc2.list_parts(
            mpu_id,
            bucket_name,
            test_cfg["object_name"])
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(len(resp[1]["Parts"]),
                         test_cfg["total_parts"], resp[1])
        LOGGER.info(
            "Step 4: Listed parts of multipart upload: {0} using account 2".format(
                res[1]))
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API ListMultipartUploadParts")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8707")
    @CTFailOn(error_handler)
    def test_7016(self):
        """
        Test bucket policy authorization on object with API AbortMultipartUpload"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API AbortMultipartUpload")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7016"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        self.create_bucket_validate(bucket_name)
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        account_id= acc_details[6]
        s3_mp_obj_acc2= acc_details[8]
        LOGGER.info("Step 1: Initiating multipart upload")
        res= S3_MULTIPART_OBJ.create_multipart_upload(
            bucket_name, test_cfg["object_name"])
        assert res[0], res[1]
        mpu_id= res[1]["UploadId"]
        LOGGER.info(
            "Step 1: Multipart Upload initiated with mpu_id {0}".format(mpu_id))
        LOGGER.info(
            "Step 2: Creating a json to allow AbortMultipartUpload for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, test_cfg["object_name"])
        LOGGER.info(
            "Step 2: Created a json to allow AbortMultipartUpload for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Aborting multipart upload using account 2")
        resp= s3_mp_obj_acc2.abort_multipart_upload(
            bucket_name, test_cfg["object_name"], mpu_id)
        assert res[0], res[1]
        LOGGER.info("Step 3: Aborted multipart upload using account 2")
        LOGGER.info(
            "Step 4: Verifying multipart got aborted by listing multipart upload using account 1")
        resp= S3_MULTIPART_OBJ.list_multipart_uploads(bucket_name)
        assert mpu_id not in resp[1], resp[1]
        LOGGER.info("Step 4: Verified that multipart got aborted")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API AbortMultipartUpload")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8708")
    @CTFailOn(error_handler)
    def test_7849(self):
        """
        Test bucket policy authorization on bucket with API HeadBucket"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API HeadBucket")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7849"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy_1= test_cfg["bucket_policy_1"]
        bucket_policy_2= test_cfg["bucket_policy_2"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_OBJ_acc2= acc_details[1]
        account_id= acc_details[6]
        LOGGER.info(
            "Step 2: Creating a json to allow HeadBucket for account 2")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]= bucket_policy_1["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy_1["Statement"][0]["Resource"]= bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info(
            "Step 2: Created a json to allow HeadBucket for account 2")
        self.put_invalid_policy(
            bucket_name,
            bucket_policy_1,
            test_cfg["error_message"])
        LOGGER.info(
            "Step 3: Creating a json to allow ListBucket for account 2")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]= bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            account_id)
        bucket_policy_2["Statement"][0]["Resource"]= bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info(
            "Step 3: Created a json to allow ListBucket for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy_2)
        LOGGER.info(
            "Step 4: Performing head bucket on a bucket {0} using account 2".format(bucket_name))
        resp= S3_OBJ_acc2.head_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp)
        LOGGER.info(
            "Step 4: Performed head bucket on a bucket {0} using account 2".format(bucket_name))
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API HeadBucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8709")
    @CTFailOn(error_handler)
    def test_7850(self):
        """
        Test bucket policy authorization on object with API HeadObject"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API HeadObject")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7850"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy_1= test_cfg["bucket_policy_1"]
        bucket_policy_2= test_cfg["bucket_policy_2"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_OBJ_acc2= acc_details[1]
        account_id= acc_details[6]
        LOGGER.info(
            "Step 2: Creating a json to allow HeadObject for account 2")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]= bucket_policy_1["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy_1["Statement"][0]["Resource"]= bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 2: Created a json to allow HeadBucket for account 2")
        self.put_invalid_policy(
            bucket_name,
            bucket_policy_1,
            test_cfg["error_message"])
        LOGGER.info(
            "Step 3: Creating a json to allow GetObject for account 2")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]= bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            account_id)
        bucket_policy_2["Statement"][0]["Resource"]= bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 3: Created a json to allow GetObject for account 2")

        self.put_get_bkt_policy(bucket_name, bucket_policy_2)
        LOGGER.info("Step 4: Performing head object using account 2")
        resp= S3_OBJ_acc2.object_info(bucket_name, object_lst[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Performed head object using account 2")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API HeadObject`")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8710")
    @CTFailOn(error_handler)
    def test_7851(self):
        """
        Test bucket policy authorization on bucket with API DeleteBucketTagging"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API DeleteBucketTagging")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7851"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy_1= test_cfg["bucket_policy_1"]
        bucket_policy_2= test_cfg["bucket_policy_2"]
        self.create_bucket_validate(bucket_name)
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_TAG_OBJ_acc2= acc_details[7]
        account_id= acc_details[6]
        LOGGER.info(
            "Step 2: Creating a json to allow DeleteBucketTagging for account 2")
        bucket_policy_1["Statement"][0]["Principal"]["AWS"]= bucket_policy_1["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy_1["Statement"][0]["Resource"]= bucket_policy_1["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info(
            "Step 2: Created a json to allow DeleteBucketTagging for account 2")
        self.put_invalid_policy(
            bucket_name,
            bucket_policy_1,
            test_cfg["error_message"])
        LOGGER.info(
            "Step 3: Creating a json to allow PutBucketTagging for account 2")
        bucket_policy_2["Statement"][0]["Principal"]["AWS"]= bucket_policy_2["Statement"][0]["Principal"][
            "AWS"].format(
            account_id)
        bucket_policy_2["Statement"][0]["Resource"]= bucket_policy_2["Statement"][0]["Resource"].format(
            bucket_name)
        LOGGER.info(
            "Step 3: Created a json to allow PutBucketTagging for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy_2)
        LOGGER.info(
            "Step 4: Set bucket tagging to a bucket {0}".format(bucket_name))
        resp= S3_TAG_OBJ.set_bucket_tag(
            bucket_name, test_cfg["key"], test_cfg["value"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 4: Tag was set to a bucket {0}".format(bucket_name))
        LOGGER.info("Step 5: Deleting bucket tagging using account 2")
        resp= S3_TAG_OBJ_acc2.delete_bucket_tagging(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 5: Deleted bucket tagging using account 2")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API DeleteBucketTagging")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-8711")
    @CTFailOn(error_handler)
    def test_7852(self):
        """
        Test bucket policy authorization on object with API DeleteObjectTagging"""
        LOGGER.info(
            "STARTED: Test bucket policy authorization on object with API DeleteObjectTagging")
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_cfg= BKT_POLICY_CONF["test_7852"]
        bucket_name= test_cfg["bucket_name"].format(self.timestamp)
        bucket_policy= test_cfg["bucket_policy"]
        LOGGER.info("Step 1: Creating bucket and put multiple objects")
        object_lst= []
        self.create_bucket_put_objects(
            bucket_name,
            test_cfg["obj_count"],
            bkt_policy_cfg["obj_name_prefix"],
            object_lst)
        LOGGER.info("Step 1: Created bucket with multiple objects")
        account_name= "{0}{1}".format(
            bkt_policy_cfg["account_name"], str(self.timestamp))
        email_id= "{0}{1}".format(account_name, bkt_policy_cfg["email_id"])
        acc_details= self.create_s3iamcli_acc(account_name, email_id)
        S3_TAG_OBJ_acc2= acc_details[7]
        account_id= acc_details[6]
        LOGGER.info(
            "Step 2: Creating a json to allow DeleteObjectTagging for account 2")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id)
        bucket_policy["Statement"][0]["Resource"]= bucket_policy["Statement"][0]["Resource"].format(
            bucket_name, object_lst[0])
        LOGGER.info(
            "Step 2: Created a json to allow DeleteObjectTagging for account 2")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info("Step 3: Setting tag to an object")
        resp= S3_TAG_OBJ.set_object_tag(
            bucket_name,
            object_lst[0],
            test_cfg["key"],
            test_cfg["value"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Tag was set to an object")
        LOGGER.info("Step 4: Deleting tag of an object using account 2")
        resp= S3_TAG_OBJ_acc2.delete_object_tagging(
            bucket_name, object_lst[0])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Deleted tag of an object using account 2")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on object with API DeleteObjectTagging")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9661")
    @CTFailOn(error_handler)
    def test_6966(self):
        """
        Test bucket policy authorization on bucket with API DeleteBucket
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API DeleteBucket")
        random_id= str(time.time())
        test_6966_cfg= BKT_POLICY_CONF["test_6966"]
        bucket_name= test_6966_cfg["bucket_name"]
        bucket_policy= test_6966_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6966_cfg["account_name_1"].format(random_id)
        email_id_1= test_6966_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Creating a bucket  - run from default account")
        resp= S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 1: Created bucket - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket .Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 5 & 6: Account switch "
                    "Delete the bucket . - run from account1")
        self.s3test_obj_1.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 5 & 6: "
                    "Bucket deleted successfully. - run from account1")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API DeleteBucket")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-9662")
    @CTFailOn(error_handler)
    def test_6923(self):
        """
        Test bucket policy authorization on bucket with API GetBucketAcl
        """
        LOGGER.info(
            "STARTED: Test bucket policy authorization on bucket with API GetBucketAcl")
        random_id= str(time.time())
        bkt_policy_cfg= BKT_POLICY_CONF["bucket_policy"]
        test_6923_cfg= BKT_POLICY_CONF["test_6923"]
        obj_prefix= bkt_policy_cfg["obj_name_prefix"]
        bucket_name= test_6923_cfg["bucket_name"]
        bucket_policy= test_6923_cfg["bucket_policy"]
        LOGGER.info("Create new account.")
        account_name_1= test_6923_cfg["account_name_1"].format(random_id)
        email_id_1= test_6923_cfg["emailid_1"].format(random_id)
        result_1= self.create_s3iamcli_acc(account_name_1, email_id_1)
        account_id_1= result_1[6]
        self.s3test_obj_1= result_1[1]
        S3_OBJ_acl_1= result_1[2]
        LOGGER.info("New account created.")
        LOGGER.info(
            "Step 1: Create a bucket and upload object in the bucket. - run from default account")
        self.create_bucket_put_objects(
            bucket_name, test_6923_cfg["obj_count"], obj_prefix)
        LOGGER.info(
            "Step 1: Created bucket and uploaded object in the bucket. - run from default account")
        LOGGER.info(
            "Step 2: Create a policy json - run from default account")
        bucket_policy["Statement"][0]["Principal"]["AWS"]= bucket_policy["Statement"][0]["Principal"]["AWS"].format(
            account_id_1)
        LOGGER.info(bucket_policy)
        LOGGER.info(
            "Step 2: Created a policy json - run from default account")
        LOGGER.info(
            "Step 3 & 4: Apply the  policy on the bucket .Check the output,"
            "Check the bucket policy to verify the applied policy - run from default account")
        self.put_get_bkt_policy(bucket_name, bucket_policy)
        LOGGER.info(
            "Step 3 & 4: Applied the  policy on the bucket. Check the output,"
            "Checked the bucket policy to verify the applied policy - run from default account")
        LOGGER.info("Step 5 & 6: Account switch "
                    "Get bucket ACL. - run from account1")
        resp= S3_OBJ_acl_1.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 5 & 6: "
                    "Get bucket ACL response was success. - run from account1")
        LOGGER.info("set put_bucket_acl to private as part of teardown")
        ACL_OBJ.put_bucket_acl(
            bucket_name,
            acl=bkt_policy_cfg["acl_permission"])
        LOGGER.info("set put_bucket_acl to private as part of teardown")
        LOGGER.info(
            "ENDED: Test bucket policy authorization on bucket with API GetBucketAcl")
