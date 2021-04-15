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

"""Cortxcli test module."""
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils.system_utils import create_file
from commons.utils.assert_utils import assert_true, assert_equal, assert_greater_equal, assert_in
from config import CSM_CFG

from libs.csm.cli.cli_alerts_lib import CortxCliAlerts
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser

from libs.s3 import s3_test_lib, iam_test_lib

s3_test_obj = s3_test_lib.S3TestLib()
iam_obj = iam_test_lib.IamTestLib()


class TestCortxcli:
    """Cortxcli Blackbox Testsuite."""

    iam_user_obj = None
    s3bucket_name = None
    s3obj_name = None
    @classmethod
    def setup_class(cls):
        """Setup all the states required for execution of this test suit."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.file_size = 1
        cls.error = "InvalidAccessKeyId"
        cls.err_message = "EntityAlreadyExists"
        cls.account_name = "seagate_account"
        cls.user_name = "seagate_user"
        cls.total_users = 100
        cls.test_file_path = "/root/testfile"
        cls.s3acc_obj = CortxCliS3AccountOperations()
        cls.s3acc_obj.open_connection()
        cls.s3bkt_obj = CortxCliS3BucketOperations(
            session_obj=cls.s3acc_obj.session_obj)
        cls.csm_user_obj = CortxCliCsmUser(
            session_obj=cls.s3acc_obj.session_obj)
        cls.iam_user_obj = CortxCliIamUser(
            session_obj=cls.s3acc_obj.session_obj)
        cls.alert_obj = CortxCliAlerts(session_obj=cls.s3acc_obj.session_obj)
        cls.s3acc_prefix = "cli_s3acc"
        cls.s3acc_name = cls.s3acc_prefix
        cls.s3acc_email = "{}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.log.info("ENDED : Setup operations at test suit level")

    @classmethod
    def create_account(cls, acc_name, email_id=None, acc_password=None):
        """Function will create IAM account."""
        if email_id is None:
            acc_email = "{}{}".format(acc_name, cls.s3acc_email)
        else:
            acc_email = email_id
        return cls.iam_user_obj.create_s3account_cortx_cli(
            acc_name,
            acc_email,
            acc_password)

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite.

        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.log.info("STARTED : Setup operations at test function level")
        self.s3acc_name = "{}_{}".format(self.s3acc_name, int(time.time()))
        self.s3acc_email = self.s3acc_email.format(self.s3acc_name)
        self.s3bucket_name = "{}_{}_{}".format(
            self.s3acc_prefix, "bucket", int(time.time()))
        self.s3obj_name = "{}_{}_{}".format(
            self.s3acc_prefix, "object", int(time.time()))
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        self.log.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown Operations")
        all_users = self.iam_user_obj.list_iam_user()[1]
        users_list = [user["UserName"]
                      for user in all_users if
                      self.user_name in user["UserName"]]
        self.log.info("IAM users: %s", users_list)
        if users_list:
            self.log.info("Deleting IAM users...")
            for user in users_list:
                res = iam_obj.list_access_keys(user)
                if res[0]:
                    self.log.info("Deleting user access key...")
                    keys_meta = res[1]["AccessKeyMetadata"]
                    for key in keys_meta:
                        iam_obj.delete_access_key(
                            user, key["AccessKeyId"])
                    self.log.info("Deleted user access key")
                self.iam_user_obj.delete_iam_user(user)
        self.log.info("Deleted users successfully")
        acc_list = self.s3acc_obj.show_s3account_cortx_cli(output_format="json")[
            1]
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        if all_acc:
            self.log.info("Accounts to delete: %s", all_acc)
            for acc in all_acc:
                self.log.info("Deleting %s account", acc)
                iam_obj.reset_access_key_and_delete_account_s3iamcli(acc)
                self.log.info("Deleted %s account", acc)
        self.log.info("ENDED: Teardown Operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7177")
    @CTFailOn(error_handler)
    def test_2393(self):
        """Create account using cortxcli."""
        self.log.info("STARTED: create account using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info("ENDED: create account using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7178")
    @CTFailOn(error_handler)
    def test_2394(self):
        """List account using cortxcli."""
        self.log.info("STARTED: List account using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Listing account to verify new account is created")
        list_of_accounts = self.s3acc_obj.show_s3account_cortx_cli(
            output_format="text")
        assert_true(list_of_accounts[0], list_of_accounts[1])
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        assert_in(acc_name, new_accounts)
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info("ENDED: List account using s3iamcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7179")
    @CTFailOn(error_handler)
    def test_2399(self):
        """Create 'N' No of Accounts."""
        self.log.info("STARTED: Create 'N' No of Accounts")
        total_accounts = 50
        self.log.info(
            "Step 1: Creating %s accounts", total_accounts)
        account_list = []
        access_keys = []
        secret_keys = []
        acc_name = self.account_name
        for account in range(total_accounts):
            account_name = f"{acc_name}{account}{account}{str(int(time.time()))}"
            email_id = f"{acc_name}{account}{account}@seagate.com"
            resp = self.create_account(
                account_name, email_id, self.s3acc_password)
            assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            account_list.append(account_name)
        self.log.info("Step 1: Created %s accounts",
                      total_accounts)
        self.log.info(
            "Verifying %s accounts are created by listing accounts",
            total_accounts)
        list_of_accounts = self.s3acc_obj.show_s3account_cortx_cli(
            output_format="text")
        assert_true(list_of_accounts[0], list_of_accounts[1])
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        for account in range(total_accounts):
            assert_in(account_list[account], new_accounts)
        self.log.info(
            "Verified %s accounts are created by listing accounts",
            total_accounts)
        self.log.info("ENDED: Create 'N' No of Accounts")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7180")
    @CTFailOn(error_handler)
    def test_2396(self):
        """Create account with existing name using cortxcli."""
        self.log.info(
            "STARTED: create account with existing name using cortxcli")
        err_message = "EntityAlreadyExists"
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Creating another account with existing account name")
        try:
            self.create_account(acc_name, acc_password=self.s3acc_password)
        except CTException as error:
            assert_in(
                err_message,
                error.message,
                error.message)
        self.log.info(
            "Step 2: Created another account with existing account name")
        self.log.info(
            "ENDED: create account with existing name using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7181")
    @CTFailOn(error_handler)
    def test_2395(self):
        """Delete Account using cortxcli."""
        self.log.info("STARTED: Delete Account using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Deleting account with name %s", acc_name)
        resp = self.s3acc_obj.delete_s3account_cortx_cli(acc_name)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Deleted account with name %s successfully",
            self.account_name)
        self.log.info("ENDED: Delete Account using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7125")
    @CTFailOn(error_handler)
    def test_2430(self):
        """CRUD operations with valid login credentials using cortxcli."""
        self.log.info(
            "STARTED: CRUD operations with valid login credentials using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        file_size = 1
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Create access key for newly created user")
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_access_key(usr_name)
        assert_true(resp[0], resp[1])
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        self.log.info("Step 2: Created access key for newly created user")
        s3_user_obj = s3_test_lib.S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        self.log.info(
            "Step 3: Performing CRUD operations using valid user's credentials")
        self.log.info("Creating a bucket with name %s", self.s3bucket_name)
        resp = s3_user_obj.create_bucket(self.s3bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Bucket with name %s is created successfully", self.s3bucket_name)
        create_file(self.test_file_path, file_size)
        self.log.info(
            "Putting object %s to bucket %s",
            self.s3obj_name, self.s3bucket_name)
        resp = s3_user_obj.put_object(
            self.s3bucket_name,
            self.s3obj_name,
            self.test_file_path)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Object %s successfully put to bucket %s",
            self.s3obj_name, self.s3bucket_name)
        self.log.info("Downloading object from bucket %s", self.s3bucket_name)
        resp = s3_user_obj.object_download(
            self.s3bucket_name, self.s3obj_name, self.test_file_path)
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1],
            self.test_file_path,
            resp[1])
        self.log.info(
            "Downloading object from bucket %s successfully", self.s3bucket_name)
        self.log.info(
            "Step 3: Performed CRUD operations using valid user's credentials")
        # Cleanup activity
        resp = s3_user_obj.delete_bucket(self.s3bucket_name, force=True)
        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: CRUD operations with valid login credentials using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7183")
    @CTFailOn(error_handler)
    def test_2400(self):
        """Create user using cortxcli."""
        self.log.info("STARTED: create user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Listing users and verifying user is created")
        resp = self.iam_user_obj.list_iam_user(access_key, secret_key)
        self.log.info("Users_List %s", resp[1])
        assert_true(resp[0], resp[1])
        assert_in(usr_name, resp[1], resp[1])
        self.log.info("Step 2: Listed users and verified user is created")
        self.log.info("ENDED: create user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7184")
    @CTFailOn(error_handler)
    def test_2406(self):
        """Create access key for user using cortxcli."""
        self.log.info("STARTED: create access key for user using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = CortxCliIamUser(
            session_obj=self.s3acc_obj.session_obj)
        self.log.info(
            "Step 1: Creating a user with name %s", usr_name)
        resp = new_iam_obj.create_iam_user(usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = new_iam_obj.list_iam_user()
        self.log.info("Users list %s", resp[0])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info(
            "Step 1: Created a user with name %s", usr_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(usr_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Created access key for the user")
        self.log.info("ENDED: create access key for user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7185")
    @CTFailOn(error_handler)
    def test_2405(self):
        """Max num of users supported using cortxcli."""
        self.log.info("STARTED: max num of users supported using cortxcli")
        self.log.info("Step 1: Create new account")
        total_users = 100
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Step 1: Created new account successfully")
        self.log.info("Step 2: Creating %s users", total_users)
        for user in range(total_users):
            my_user_name = f"{usr_name}{user}"
            self.log.info("Creating user with name %s", my_user_name)
            resp = self.iam_user_obj.create_iam_user(
                my_user_name, access_key, secret_key)
            assert_true(resp[0], resp[1])
            self.log.info("Created user with name %s", my_user_name)
        self.log.info("Step 2: Created %s users", total_users)
        self.log.info("Verifying %s users are created", total_users)
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        list_of_users = new_iam_obj.list_users_s3iamcli(
            access_key, secret_key)[1]
        self.log.info(list_of_users)
        self.log.info("Number of users : %s", len(list_of_users))
        assert_true(resp[0], resp[1])
        assert_greater_equal(
            (len(list_of_users)),
            self.total_users,
            list_of_users[1])
        self.log.info("Verified %s users are created", total_users)
        self.log.info("Step 3: Deleting %s users", total_users)
        self.log.info("ENDED: max num of users supported using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7186")
    @CTFailOn(error_handler)
    def test_2404(self):
        """Creating user with existing user name using cortxcli."""
        self.log.info(
            "STARTED: creating user with existing user name using cortxcli")
        self.log.info("Step 1: Create new account")
        err_message = "EntityAlreadyExists"
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Step 1: Creating user with name %s", usr_name)
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created user with name %s", usr_name)
        self.log.info(
            "Step 2: Creating user with existing name %s", usr_name)
        try:
            self.iam_user_obj.create_iam_user(usr_name, access_key, secret_key)
        except CTException as error:
            assert_in(err_message,
                      error.message,
                      error.message)
        self.log.info(
            "Step 2: Could not create user with existing name %s", usr_name)
        self.log.info(
            "ENDED: creating user with existing user name using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7187")
    @CTFailOn(error_handler)
    def test_2403(self):
        """Delete user using cortxcli."""
        self.log.info("STARTED: Delete user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Deleting user")
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.delete_user(usr_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Deleted user successfully")
        self.log.info("ENDED: Delete user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7188")
    @CTFailOn(error_handler)
    def test_2402(self):
        """Update user using cortxcli."""
        self.log.info("STARTED: Update user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        new_user_name = "testuser2402"
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Updating user name of already existing user")
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.update_user(new_user_name, usr_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Updated user name of already existing user")
        self.log.info(
            "Step 3: Listing users and verifying user name is updated")
        # resp = self.iam_user_obj.list_users_s3iamcli(access_key, secret_key)
        resp = self.iam_user_obj.list_iam_user()
        assert_true(resp[0], resp[1])
        assert_in(
            new_user_name,
            resp[1],
            resp[1])
        self.log.info("Step 3: Listed users and verified user name is updated")
        self.log.info("ENDED: Update user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7190")
    @CTFailOn(error_handler)
    def test_2401(self):
        """List user using cortxcli."""
        self.log.info("STARTED: list user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info(
            "Step 2: Listing users and verifying user details are listed")
        resp = self.iam_user_obj.list_iam_user()
        assert_true(resp[0], resp[1])
        assert_in(usr_name, resp[1], resp[1])
        self.log.info(
            "Step 2: Listed users and verified user details are listed")
        self.log.info("ENDED: list user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7193")
    @CTFailOn(error_handler)
    def test_2398(self):
        """Login to account with invalid creds and perform s3 crud operations using cortxcli."""
        self.log.info(
            "STARTED: login to account with invalid cred and perform s3 crud ops using cortxcli")
        self.log.info("Step 1: Create new account")
        err_message = "InvalidAccessKeyId"
        download_obj_err = "Forbidden"
        file_size = 1
        # Dummy access and secret keys
        user_access_key = "alfjkalfjiecnk@#&kafjkancsmnc"
        user_secret_key = "*HSLKJMDqpowdapofmamcamc"
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account")
        s3_user_obj = s3_test_lib.S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        self.log.info(
            "Step 2: Performing operations with invalid user's credentials")
        self.log.info("Creating a bucket with name %s", self.s3bucket_name)
        try:
            s3_user_obj.create_bucket(self.s3bucket_name)
        except CTException as error:
            assert_in(
                err_message,
                error.message,
                error.message)
        self.log.info(
            "Bucket with name %s is not created", self.s3bucket_name)
        self.log.info(
            "Putting object %s to bucket %s",
            self.s3obj_name, self.s3bucket_name)
        try:
            create_file(
                self.test_file_path,
                file_size)
            s3_user_obj.put_object(
                self.s3bucket_name,
                self.s3obj_name,
                self.test_file_path)
        except CTException as error:
            assert_in(
                err_message,
                error.message,
                error.message)
        self.log.info(
            "Could not put object %s to bucket %s",
            self.s3obj_name, self.s3bucket_name)
        self.log.info("Downloading object from bucket %s", self.s3bucket_name)
        try:
            s3_user_obj.object_download(
                self.s3bucket_name,
                self.s3obj_name,
                self.test_file_path)
        except CTException as error:
            assert_in(
                download_obj_err,
                error.message,
                error.message)
        self.log.info(
            "Could not download object from bucket %s", self.s3bucket_name)
        self.log.info(
            "Step 2: Performed CRUD operations with invalid user's credentials")
        self.log.info(
            "ENDED: login to account with invalid cred and perform s3 crud ops using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7195")
    @CTFailOn(error_handler)
    def test_2397(self):
        """Login to account with valid credentials and perform s3 crud operations using cortxcli."""
        self.log.info(
            "STARTED: login to account with valid creds and perform s3 crud ops using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        file_size = 1
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = self.iam_user_obj.create_iam_user(
            usr_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Create access key for newly created user")
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_access_key(usr_name)
        assert_true(resp[0], resp[1])
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        self.log.info("Step 2: Created access key for newly created user")
        s3_user_obj = s3_test_lib.S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        self.log.info(
            "Step 3: Performing CRUD operations using valid user's credentials")
        self.log.info("Creating a bucket with name %s", self.s3bucket_name)
        resp = s3_user_obj.create_bucket(self.s3bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Bucket with name %s is created successfully", self.s3bucket_name)
        create_file(self.test_file_path, file_size)
        self.log.info(
            "Putting object %s to bucket %s",
            self.s3obj_name, self.s3bucket_name)
        resp = s3_user_obj.put_object(
            self.s3bucket_name,
            self.s3obj_name,
            self.test_file_path)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Object %s successfully put to bucket %s",
            self.s3obj_name, self.s3bucket_name)
        self.log.info("Downloading object from bucket %s", self.s3bucket_name)
        resp = s3_user_obj.object_download(
            self.s3bucket_name, self.s3obj_name, self.test_file_path)
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1],
            self.test_file_path,
            resp[1])
        self.log.info(
            "Downloading object from bucket %s successfully", self.s3bucket_name)
        self.log.info(
            "Step 3: Performed CRUD operations using valid user's credentials")
        # Cleanup activity
        resp = s3_user_obj.delete_bucket(self.s3bucket_name, force=True)
        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: login to account with valid creds and perform s3 crud ops using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7196")
    @CTFailOn(error_handler)
    def test_2410(self):
        """Delete accesskey using cortxcli."""
        self.log.info("STARTED: delete accesskey using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        # self.iam_user_obj = iam_test_lib.IamTestLib(
        #     access_key=access_key,
        #     secret_key=secret_key)
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info(
            "Step 3: Creating a user with name %s", usr_name)
        resp = self.iam_user_obj.create_iam_user(usr_name,
                                                 access_key,
                                                 secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s", usr_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(usr_name)
        assert_true(resp[0], resp[1])
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        self.log.info("Step 4: Created access key for the user")
        self.log.info("Step 5: Deleting access key of the user")
        resp = iam_obj.delete_access_key(
            usr_name, user_access_key)
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Deleted access key of the user")
        self.log.info("Step 6: Listing access key of the user")
        resp = iam_obj.list_access_keys(usr_name)
        assert_true(resp[0], resp[1])
        # Verifying list is empty
        assert_true(len(resp[1]["AccessKeyMetadata"])
                    == 0, resp[1]["AccessKeyMetadata"])
        self.log.info("Step 6: Listed access key of the user successfully")
        self.log.info("ENDED: delete accesskey using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7197")
    @CTFailOn(error_handler)
    def test_2409(self):
        """Update accesskey with inactive mode using cortxcli."""
        status = "InActive"
        self.log.info(
            "STARTED: update accesskey with inactive mode using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        # self.iam_user_obj = iam_test_lib.IamTestLib(
        #     access_key=access_key,
        #     secret_key=secret_key)
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info(
            "Step 3: Creating a user with name %s", usr_name)
        resp = self.iam_user_obj.create_iam_user(usr_name,
                                                 access_key,
                                                 secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s", usr_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(usr_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updating access key of user")
        resp = iam_obj.update_access_key(
            access_key_to_update,
            status,
            usr_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updated access key of user")
        self.log.info("Step 6: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(usr_name)
        assert_true(resp[0], resp[1])
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert_equal(new_access_key, access_key_to_update, resp[1])
        assert_equal(status, status, resp[1])
        self.log.info(
            "Step 6: Verified that access key of user is updated successfully")
        self.log.info(
            "ENDED: update accesskey with inactive mode using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7198")
    @CTFailOn(error_handler)
    def test_2407(self):
        """List accesskey for User using cortxcli."""
        self.log.info("STARTED: list accesskey for User using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s",
            self.account_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info(
            "Step 3: Creating a user with name %s", usr_name)
        resp = self.iam_user_obj.create_iam_user(usr_name,
                                                 access_key,
                                                 secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s", usr_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(usr_name)
        assert_true(resp[0], resp[1])
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        self.log.info("Step 4: Created access key for the user")
        self.log.info("Step 5: Listing access key of the user")
        resp = iam_obj.list_access_keys(usr_name)
        assert_true(resp[0], resp[1])
        resp_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        assert_equal(user_access_key, resp_access_key, resp[1])
        self.log.info("Step 5: Listed access key of the user successfully")
        self.log.info("ENDED: list accesskey for User using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7192")
    @CTFailOn(error_handler)
    def test_2408(self):
        """Update accesskey with active mode using cortxcli."""
        status = "Active"
        self.log.info(
            "STARTED: update accesskey with active mode using cortxcli")
        acc_name = "{}{}".format(self.account_name,
                                 str(int(time.time())))
        usr_name = "{}{}".format(
            self.user_name, str(int(time.time())))
        self.log.info(
            "Step 1: Creating a new account with name %s", acc_name)
        resp = self.create_account(acc_name, acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Step 1: Created a new account with name %s", acc_name)
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info(
            "Step 3: Creating a user with name %s", usr_name)
        resp = self.iam_user_obj.create_iam_user(usr_name,
                                                 access_key,
                                                 secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s", usr_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(usr_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updating access key of user")
        resp = iam_obj.update_access_key(
            access_key_to_update,
            status,
            usr_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updated access key of user")
        self.log.info("Step 6: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(usr_name)
        assert_true(resp[0], resp[1])
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert_equal(new_access_key, access_key_to_update, resp[1])
        assert_equal(status, status, resp[1])
        self.log.info(
            "Step 6: Verified that access key of user is updated successfully")
        self.log.info(
            "ENDED: update accesskey with active mode using cortxcli")
