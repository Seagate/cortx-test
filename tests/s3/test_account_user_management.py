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

"""Account User Management test module."""

import os
import time
import shutil
import logging
import pytest

from commons.configmanager import get_config_wrapper
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import S3H_OBJ, LDAP_USERNAME, LDAP_PASSWD
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.iam_test_lib import IamTestLib
from config import S3_CMN_CONFIG

IAM_OBJ = IamTestLib()
S3_OBJ = S3TestLib()


class TestAccountUserManagement:
    """Account User Management TestSuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.ca_cert_path = const.CA_CERT_PATH
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_passwd = LDAP_PASSWD
        cls.test_file = "testfile"
        cls.test_dir_path = os.path.join(os.getcwd(), "testdata")
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not os.path.exists(cls.test_dir_path):
            os.makedirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("Test file path: %s", cls.test_file_path)
        cls.log.info("STARTED: Test setup operations.")
        cls.log.info("Certificate path: %s", cls.ca_cert_path)
        cls.log.info(
            "LDAP credentials: User: %s, pass: %s",
            cls.ldap_user,
            cls.ldap_passwd)
        cls.log.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if os.path.exists(cls.test_dir_path):
            shutil.rmtree(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        # Delete created user with prefix.
        self.log.info("STARTED: Test setup operations.")

        self.timestamp = time.time()
        self.bucket_name = "testbucket{}".format(str(time.time()))
        self.obj_name = "testobj{}".format(str(time.time()))
        self.account_name = "accusrmgmt_account"
        self.email_id = "{}@seagate.com"
        self.user_name = "accusrmgmt_user"

        self.log.info(
            "Delete created user with prefix: %s", self.user_name)
        usr_list = IAM_OBJ.list_users()[1]
        self.log.debug("Listing users: %s", usr_list)
        all_usrs = [usr["UserName"]
                    for usr in usr_list if self.user_name in usr["UserName"]]
        if all_usrs:
            IAM_OBJ.delete_users_with_access_key(all_usrs)
        # Delete account created with prefix.
        self.log.info(
            "Delete created account with prefix: %s", self.user_name)
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user,
            self.ldap_passwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.user_name in acc["AccountName"]]
        if all_acc:
            IAM_OBJ.delete_multiple_accounts(all_acc)

        self.log.info("ENDED: Test setup operations.")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Test teardown Operations.")
        users_list = [user["UserName"]
                      for user in IAM_OBJ.list_users()[1]
                      if self.user_name in user["UserName"]]
        self.log.info("IAM users: %s", str(users_list))
        if users_list:
            self.log.info("Deleting IAM users...")
            for user in users_list:
                res = IAM_OBJ.list_access_keys(user)
                if res[0]:
                    self.log.info("Deleting user access key...")
                    for key in res[1]["AccessKeyMetadata"]:
                        IAM_OBJ.delete_access_key(
                            user, key["AccessKeyId"])
                    self.log.info("Deleted user access key.")
                try:
                    self.log.info("Deleting a user: %s", str(user))
                    resp = IAM_OBJ.delete_user(user)
                    self.log.info(resp)
                except CTException as error:
                    self.log.error(error)
        self.log.info("Deleted users successfully.")
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_passwd)[1]
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]
                   ]
        if all_acc:
            self.log.info("Accounts to delete: %s", str(all_acc))
            for acc in all_acc:
                try:
                    self.log.info("Deleting %s account", str(acc))
                    resp = IAM_OBJ.reset_account_access_key_s3iamcli(
                        acc, self.ldap_user, self.ldap_passwd)
                    access_key = resp[1]["AccessKeyId"]
                    secret_key = resp[1]["SecretKey"]
                    s3_temp_obj = S3TestLib(
                        access_key=access_key, secret_key=secret_key)
                    test_buckets = s3_temp_obj.bucket_list()[1]
                    if test_buckets:
                        self.log.info("Deleting all buckets...")
                        bkt_list = s3_temp_obj.bucket_list()[1]
                        self.log.info("bucket-list: %s", bkt_list)
                        resp = s3_temp_obj.delete_multiple_buckets(bkt_list)
                        assert resp[0], resp[1]
                        self.log.info("Deleted all buckets")
                    self.log.info("Deleting IAM accounts...")
                    resp = IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(
                        acc)
                    self.log.info(
                        "reset access_key, delete account, response: %s", resp)
                    assert resp[0], resp[1]
                    self.log.info("Deleted %s account", str(acc))
                except CTException as error:
                    self.log.info(error)
        self.log.info("ENDED: Test teardown Operations.")

    def create_account(self, account_name):
        """Create s3 account using s3iamcli."""
        response = IAM_OBJ.create_account_s3iamcli(
            account_name,
            self.email_id.format(account_name),
            self.ldap_user,
            self.ldap_passwd)
        self.log.info(
            "Create account: %s, response: %s",
            account_name,
            response)

        return response

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5440")
    @CTFailOn(error_handler)
    def test_create_new_account_1968(self):
        """Create new account."""
        self.log.info("START: Test create new account.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        self.log.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert resp[0], resp[1]
        self.log.info("END: Tested create new account.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5429")
    @CTFailOn(error_handler)
    def test_list_account_1969(self):
        """List account."""
        self.log.info("START: Test List account.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        self.log.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Listing account to verify new account is created")
        list_of_accounts = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_passwd)
        assert list_of_accounts[0], list_of_accounts[1]
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        self.log.info(new_accounts)
        assert account_name in new_accounts, f"{account_name} not in {new_accounts}"
        self.log.info("END: Tested List account.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5432")
    @CTFailOn(error_handler)
    def test_delete_account_1970(self):
        """Delete Account."""
        self.log.info("START: Test Delete Account.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        self.log.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Step 2: Deleting account with name %s", str(account_name))
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("END: Tested Delete Account.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5443")
    @CTFailOn(error_handler)
    def test_create_100_number_of_account_1971(self):
        """Create 100 No of Accounts."""
        self.log.info("START: Create 100 No of Accounts.")
        total_account = 100
        self.log.info("Step 1: Creating %s accounts", str(total_account))
        # Defining list.
        account_list, access_keys, secret_keys = list(), list(), list()
        acc_name = self.account_name
        self.log.info("account prefix: %s", str(acc_name))
        for cnt in range(total_account):
            account_name = f"{acc_name}{cnt}{cnt}{str(int(time.time()))}"
            email_id = f"{acc_name}{cnt}{cnt}@seagate.com"
            self.log.info("account name: %s", str(account_name))
            self.log.info("email id: %s", str(email_id))
            resp = IAM_OBJ.create_account_s3iamcli(
                account_name, email_id, self.ldap_user, self.ldap_passwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            account_list.append(account_name)
            self.log.info("account list: %s", str(account_list))
        self.log.info("Created %s accounts", str(total_account))
        self.log.info(
            "Step 2: Verifying %s accounts are created by listing accounts",
            str(total_account))
        list_of_accounts = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_passwd)
        assert list_of_accounts[0], list_of_accounts[1]
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        for cnt in range(total_account):
            assert account_list[cnt] in new_accounts
        self.log.info(
            "Verified %s accounts are created by listing accounts",
            str(total_account))
        self.log.info("END: Create 100 No of Accounts.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5437")
    @CTFailOn(error_handler)
    def test_create_new_account_with_existing_name_1972(self):
        """Creating new account with existing account name."""
        self.log.info(
            "START: Test creating new account with existing account name.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        self.log.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        self.log.info("Created a new account with name %s", str(account_name))
        self.log.info(
            "Step 2: Creating another account with existing account name")
        try:
            resp = self.create_account(account_name)
            assert not resp[0], resp[1]
        except CTException as error:
            assert "EntityAlreadyExists" in error.message, error.message
        self.log.info("Created another account with existing account name")
        self.log.info(
            "END: Tested creating new account with existing account name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5434")
    @CTFailOn(error_handler)
    def test_crud_operations_with_valid_cred_1973(self):
        """CRUD operations with valid login credentials."""
        self.log.info(
            "START: Test CRUD operations with valid login credentials.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Create new account and new user in it")
        self.log.info(
            "account name: %s and user name: %s",
            str(account_name),
            str(user_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("access key: %s", str(access_key))
        self.log.info("secret key: %s", str(secret_key))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created new account and new user in it")
        self.log.info("Step 2: Create access key for newly created user")
        new_s3h_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_s3h_obj.create_access_key(user_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        s3_user_obj = S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        self.log.info(
            "Step 3: Performing CRUD operations using valid user's credentials")
        bucket_name = self.bucket_name
        self.log.info("Creating a bucket with name %s", str(bucket_name))
        resp = s3_user_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Bucket with name %s is created successfully", str(bucket_name))
        obj_name = self.obj_name
        self.log.info("Object name: %s", str(obj_name))
        resp = create_file(self.test_file_path, 1)
        self.log.info(resp)
        self.log.info("Putting object %s to bucket %s", obj_name, bucket_name)
        resp = s3_user_obj.put_object(
            bucket_name, obj_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Object %s successfully put to bucket %s", obj_name, bucket_name)
        self.log.info("Downloading object from bucket %s", str(bucket_name))
        resp = s3_user_obj.object_download(
            bucket_name, obj_name, self.test_file_path)
        self.log.info(resp)
        assert resp[0], resp[1]
        assert resp[1] == self.test_file_path, resp[1]
        self.log.info(
            "Downloading object from bucket %s successfully",
            str(bucket_name))
        self.log.info(
            "Step 3: Performed CRUD operations using valid user's credentials")
        resp = s3_user_obj.delete_bucket(bucket_name, force=True)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info(
            "END: Tested CRUD operations with valid login credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5435")
    @CTFailOn(error_handler)
    def test_crud_operations_with_invalid_cred_1974(self):
        """CRUD operations with invalid login credentials."""
        self.log.info(
            "START: Test CRUD operations with invalid login credentials.")
        self.log.info("Step 1: Create new account and new user in it.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info(
            "username: %s and account name: %s",
            str(user_name),
            str(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created new account and new user in it.")
        # Dummy access and secret keys.
        user_access_key = "alfjkalfjiecnk@#&kafjkancsmnc"
        user_secret_key = "*HSLKJMDqpowdapofmamcamc"
        self.log.info("user_access_key: %s and user_secret_key: %s",
                      str(user_access_key), str(user_secret_key))
        s3_user_obj = S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        self.log.info(
            "Step 2: Performing CRUD operations with invalid user's credentials.")
        bucket_name = self.bucket_name
        self.log.info(bucket_name)
        self.log.info("Creating a bucket with name %s", str(bucket_name))
        err_message = "InvalidAccessKeyId"
        try:
            resp = s3_user_obj.create_bucket(bucket_name)
            assert not resp[0], resp[1]
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info("Bucket with name %s is not created", str(bucket_name))
        obj_name = self.obj_name
        self.log.info("Putting object %s to bucket %s", obj_name, bucket_name)
        try:
            respo = create_file(self.test_file_path, 1)
            self.log.info(respo)
            resp = s3_user_obj.put_object(
                bucket_name, obj_name, self.test_file_path)
            assert resp[0], resp[1]
        except CTException as error:
            assert err_message in error.message, error.message
        self.log.info(
            "Could not put object %s to bucket %s", obj_name, bucket_name)
        self.log.info("Downloading object from bucket %s", str(bucket_name))
        try:
            resp = s3_user_obj.object_download(
                bucket_name, obj_name, self.test_file_path)
            self.log.info(resp)
            assert resp[0], resp[1]
        except CTException as error:
            assert "Forbidden" in error.message, error.message
        self.log.info(
            "Could not download object from bucket %s", str(bucket_name))
        self.log.info(
            "Step 2: Performed CRUD operations with invalid user's credentials.")
        self.log.info("END: CRUD operations with invalid login credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5439")
    @CTFailOn(error_handler)
    def test_create_new_user_from_current_account_2076(self):
        """Create new user for current Account."""
        self.log.info("START: Create new user for current Account.")
        self.log.info("Step 1: Create new account and new user in it")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("account_name: %s", str(account_name))
        self.log.info("user_name: %s", str(user_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("access key: %s", str(access_key))
        self.log.info("secret key: %s", str(secret_key))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created new account and new user in it.")
        self.log.info("Step 2: Listing users and verifying user is created.")
        resp = IAM_OBJ.list_users_s3iamcli(access_key, secret_key)
        self.log.info(resp)
        self.log.info("Users_List %s", str(resp[1]))
        assert resp[0], resp[1]
        assert user_name in resp[1], resp[1]
        self.log.info("Listed users and verified user is created")
        self.log.info("END: Create new user for current Account.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5422")
    @CTFailOn(error_handler)
    def test_update_user_2077(self):
        """Update User."""
        self.log.info("START: Update User.")
        self.log.info("Step 1: Create new account and new user in it")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Updating user name of already existing user")
        new_s3h_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        new_user_name = "testuser8676"
        resp = new_s3h_obj.update_user(new_user_name, user_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Updated user name of already existing user")
        self.log.info(
            "Step 3: Listing users and verifying user name is updated.")
        resp = IAM_OBJ.list_users_s3iamcli(access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        assert "testuser8676" in resp[1], resp[1]
        self.log.info("Listed users and verified user name is updated.")
        self.log.info("END: Update User.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5428")
    @CTFailOn(error_handler)
    def test_list_user_2078(self):
        """List user."""
        self.log.info("START: list user")
        self.log.info("Step 1: Create new account and new user in it")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info(
            "Step 2: Listing users and verifying user details are listed")
        resp = IAM_OBJ.list_users_s3iamcli(access_key, secret_key)
        assert resp[0], resp[1]
        assert user_name in resp[1], resp[1]
        self.log.info("Listed users and verified user details are listed")
        self.log.info("END: list user.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5431")
    @CTFailOn(error_handler)
    def test_delete_user_2079(self):
        """Delete User."""
        self.log.info("START: Delete User")
        self.log.info("Step 1: Create new account and new user in it.")
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("Created new account and new user in it")
        self.log.info("Step 2: Deleting user")
        new_s3h_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_s3h_obj.delete_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Deleted user successfully")
        self.log.info("END: Delete User")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5438")
    @CTFailOn(error_handler)
    def test_create_100_number_of_users_2080(self):
        """Created 100 No of Users."""
        self.log.info("START: Created 100 No of Users")
        total_users = 100
        self.log.info("Step 1: Create new %s account", str(total_users))
        account_name = f'{self.account_name}_{str(int(time.time()))}'
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Created new account successfully.")
        self.log.info("Step 2: Creating %s users", str(total_users))
        for cnt in range(total_users):
            my_user_name = f"{user_name}{cnt}"
            self.log.info("Creating user with name %s", str(my_user_name))
            resp = IAM_OBJ.create_user_using_s3iamcli(
                my_user_name, access_key, secret_key)
            assert resp[0], resp[1]
            self.log.info("Created user with name %s", str(my_user_name))
        self.log.info("Step 2: Created %s users", str(total_users))
        self.log.info("Verifying %s users are created", total_users)
        new_s3h_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        list_of_users = new_s3h_obj.list_users()[1]
        self.log.info(list_of_users)
        self.log.info("Number of users : %s", str(len(list_of_users)))
        assert resp[0], resp[1]
        assert len(list_of_users) >= total_users, list_of_users[1]
        self.log.info("Verified %s users are created", str(total_users))
        self.log.info("END: Created 100 No of Users.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5436")
    @CTFailOn(error_handler)
    def test_create_user_with_existing_name_2081(self):
        """Creating user with existing name."""
        self.log.info("START: creating user with existing name.")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created user with name %s", str(user_name))
        self.log.info(
            "Step 2: Creating user with existing name %s", str(user_name))
        try:
            resp = IAM_OBJ.create_user(user_name)
            self.log.info(resp)
            assert not resp[0], resp[1]
        except CTException as error:
            assert "EntityAlreadyExists" in error.message, error.message
        self.log.info(
            "Could not create user with existing name %s", str(user_name))
        self.log.info("END: creating user with existing name.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5442")
    @CTFailOn(error_handler)
    def test_create_access_key_to_the_user_2082(self):
        """Create Access key to the user."""
        self.log.info("START: Create Access key to the user")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Verifying user is created by listing users")
        resp = IAM_OBJ.list_users()
        self.log.info("Users list %s", str(resp[1]))
        assert resp[0], resp[1]
        assert user_name in str(resp[1]), resp[1]
        self.log.info("Verified that user is created by listing users")
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = IAM_OBJ.create_access_key(user_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Created access key for the user")
        self.log.info("END: Create Access key to the user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5430")
    @CTFailOn(error_handler)
    def test_list_access_keys_for_the_user_2083(self):
        """List accesskeys for the user."""
        self.log.info("START: List accesskeys for the user")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = IAM_OBJ.create_access_key(user_name)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        self.log.info("Created access key for the user")
        self.log.info("Step 3: Listing access key of the user")
        resp = IAM_OBJ.list_access_keys(user_name)
        assert resp[0], resp[1]
        resp_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        assert user_access_key == resp_access_key, resp[1]
        self.log.info("Listed access key of the user successfully")
        self.log.info("END: List accesskeys for the user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5433")
    @CTFailOn(error_handler)
    def test_delete_access_key_of_a_user_2084(self):
        """Delete Accesskey of a user."""
        self.log.info("START: Delete Accesskey of a users")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = IAM_OBJ.create_access_key(user_name)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        self.log.info("Created access key for the user")
        self.log.info("Step 3: Deleting access key of the user")
        resp = IAM_OBJ.delete_access_key(user_name, user_access_key)
        assert resp[0], resp[1]
        self.log.info("Deleted access key of the user")
        self.log.info("Step 4: Listing access key of the user")
        resp = IAM_OBJ.list_access_keys(user_name)
        assert resp[0], resp[1]
        # Verifying list is empty.
        assert not resp[1]["AccessKeyMetadata"], resp[1]["AccessKeyMetadata"]
        self.log.info("Listed access key of the user successfully.")
        self.log.info("END: Delete Accesskey of a users")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5425")
    @CTFailOn(error_handler)
    def test_update_access_key_of_a_user_2085(self):
        """Update Accesskey of a user."""
        self.log.info("START: Update Accesskey of a user.")
        self.log.info("Update Accesskey of a user")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = IAM_OBJ.create_access_key(user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert resp[0], resp[1]
        self.log.info("Step 3: Updating access key of user")
        resp = IAM_OBJ.update_access_key(
            access_key_to_update, "Active", user_name)
        assert resp[0], resp[1]
        self.log.info("Updated access key of user")
        self.log.info("Step 4: Verifying that access key of user is updated")
        resp = IAM_OBJ.list_access_keys(user_name)
        assert resp[0], resp[1]
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert new_access_key == access_key_to_update, resp[1]
        assert status == "Active", resp[1]
        self.log.info(
            "Verified that access key of user is updated successfully")
        self.log.info("END: Update Accesskey of a user.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5424")
    @CTFailOn(error_handler)
    def test_update_accesskey_of_user_with_inactive_mode_2086(self):
        """Update accesskey of a user with inactive mode."""
        self.log.info("START: update accesskey of a user with inactive mode.")
        self.log.info("update accesskey of a user with inactive mode")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = IAM_OBJ.create_access_key(user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert resp[0], resp[1]
        self.log.info("Step 3: Updating access key of user")
        resp = IAM_OBJ.update_access_key(
            access_key_to_update, "Inactive", user_name)
        assert resp[0], resp[1]
        self.log.info("Updated access key of user")
        self.log.info("Step 4: Verifying that access key of user is updated")
        resp = IAM_OBJ.list_access_keys(user_name)
        assert resp[0], resp[1]
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert new_access_key == access_key_to_update, resp[1]
        assert status == "Inactive", resp[1]
        self.log.info(
            "Verified that access key of user is updated successfully")
        self.log.info("END: update accesskey of a user with inactive mode")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5441")
    @CTFailOn(error_handler)
    def test_create_max_accesskey_with_existing_user_name_2087(self):
        """Create max accesskey with existing user name."""
        self.log.info("START: create max accesskey with existing user name.")
        self.log.info("create max accesskey with existing user name")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info("Step 2: Creating %s access keys for user %s", 2, user_name)
        for _ in range(2):
            resp = IAM_OBJ.create_access_key(user_name)
            assert resp[0], resp[1]
        self.log.info("END: create max accesskey with existing user name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5423")
    @CTFailOn(error_handler)
    def test_update_login_profile_2088(self):
        """Update login profile."""
        self.log.info("START: update login profile.")
        self.log.info("update login profile")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info(
            "Step 2: Creating login profile for user %s", str(user_name))
        resp = IAM_OBJ.create_user_login_profile(
            user_name, S3_CMN_CONFIG["s3_params"]["password"], True)
        assert resp[0], resp[1]
        self.log.info("Created login profile for user %s", str(user_name))
        self.log.info(
            "Step 3: Updating login profile for user %s", str(user_name))
        resp = IAM_OBJ.update_user_login_profile(
            user_name,
            S3_CMN_CONFIG["s3_params"]["new_password"],
            True)
        assert resp[0], resp[1]
        self.log.info("Updated login profile for user %s", str(user_name))
        self.log.info("END: update login profile")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5427")
    @CTFailOn(error_handler)
    def test_ssl_certificate_2090(self):
        """SSL certificate."""
        self.log.info("START: SSL certificate.")
        resp = S3H_OBJ.is_s3_server_path_exists(self.ca_cert_path)
        assert resp, "certificate path not present: {}".format(
            self.ca_cert_path)
        status, resp = S3H_OBJ.copy_s3server_file(
            self.ca_cert_path, "ca.crt")
        assert status, resp
        with open("ca.crt", "r") as file:
            file_data = file.readlines()
        self.log.info(file_data)
        assert "-----BEGIN CERTIFICATE-----" in file_data[0],\
            "Certificate does not begin with {}".format("-----BEGIN CERTIFICATE-----")
        assert "-----END CERTIFICATE-----" in file_data[-1],\
            "Certificate does not end with {}".format("-----END CERTIFICATE-----")
        remove_file("ca.crt")
        self.log.info("END: SSL certificate.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5426")
    @CTFailOn(error_handler)
    def test_check_ssl_certificate_present_2091(self):
        """Check SSL certificate present."""
        self.log.info("START: ssl certificate present.")
        self.log.info(
            "Step 1: Checking if %s file exists on server", str(
                self.ca_cert_path))
        resp = S3H_OBJ.is_s3_server_path_exists(self.ca_cert_path)
        assert resp, "certificate path not present: {}".format(
            self.ca_cert_path)
        self.log.info(
            "Verified that %s file exists on server", str(self.ca_cert_path))
        self.log.info("END: ssl certificate present.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5444")
    @CTFailOn(error_handler)
    def test_change_pwd_for_iam_user_2092(self):
        """Change passsword for IAM user."""
        self.log.info("START: Change password for IAM user.")
        user_name = f'{self.user_name}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info(
            "Step 2: Creating login profile for user %s", str(user_name))
        resp = IAM_OBJ.create_user_login_profile(
            user_name, S3_CMN_CONFIG["s3_params"]["password"], True)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created login profile for user %s", str(user_name))
        self.log.info(
            "Step 3: Creating access key for user %s", str(user_name))
        resp = IAM_OBJ.create_access_key(user_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created access key for user %s", str(user_name))
        access_key = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        self.log.info("Step 4: Changing password for %s user", str(user_name))
        resp = IAM_OBJ.change_user_password(
            S3_CMN_CONFIG["s3_params"]["password"],
            S3_CMN_CONFIG["s3_params"]["new_password"],
            access_key,
            secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Changed password for %s user", str(user_name))
        self.log.info("END: Change password for IAM user.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8718")
    @CTFailOn(error_handler)
    def test_create_user_account_and_check_arn_4625(self):
        """Test Create user for the account and verify output with proper ARN format."""
        self.log.info(
            "START: Test Create user for the account and verify output with proper ARN format")
        account_name = f"{self.account_name}_{str(int(time.time()))}"
        user_name = f"{self.user_name}_{str(int(time.time()))}"
        self.log.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        account_id = resp[1]["Account_Id"]
        self.log.info("Created a new account with name %s", str(account_name))
        self.log.info("Step 2: Creating a user with name %s", str(user_name))
        resp = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("Created a user with name %s", str(user_name))
        self.log.info(
            "Step 3: Verifying ARN format of user %s", str(user_name))
        arn_format = "arn:aws:iam::{}:user/{}".format(account_id, user_name)
        assert arn_format == resp[1]["ARN"], "Invalid user ARN format"
        self.log.info(
            "Step 3: Verified ARN format of user %s successfully",
            str(user_name))
        self.log.info(
            "END: Test Create user for the account and verify output with proper ARN format")
