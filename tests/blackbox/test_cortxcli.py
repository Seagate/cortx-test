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
from commons.utils.assert_utils import assert_true, assert_equal
from commons.utils.assert_utils import assert_greater_equal, assert_in, assert_not_equal
from config import CSM_CFG

from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3access_keys import CortxCliS3AccessKeys

from libs.s3 import s3_test_lib, iam_test_lib

s3_test_obj = s3_test_lib.S3TestLib()
iam_obj = iam_test_lib.IamTestLib()


class TestCortxcli:
    """Cortxcli Blackbox Testsuite."""

    iam_user_obj = None
    s3bucket_name = None
    s3obj_name = None
    s3user_name = None

    @classmethod
    def setup_class(cls):
        """Setup all the states required for execution of this test suit."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.file_size = 1
        cls.error = "InvalidAccessKeyId"
        cls.err_message = "EntityAlreadyExists"
        cls.account_name = "seagate_account"
        # cls.user_name = "seagate_user"
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
        cls.accesskeys_obj = CortxCliS3AccessKeys(session_obj=cls.s3acc_obj.session_obj)
        cls.bucket_prefix = "clis3bkt"
        cls.s3acc_prefix = "cli_s3acc"
        cls.s3acc_name = cls.s3acc_prefix
        cls.s3acc_email = "{}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.log.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite.

        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.log.info("STARTED : Setup operations at test function level")
        self.s3acc_name = "{}_{}".format(self.s3acc_name, int(time.perf_counter()))
        self.s3acc_email = self.s3acc_email.format(self.s3acc_name)
        self.s3bucket_name = "{}_{}_{}".format(
            self.s3acc_prefix, "bucket", int(time.perf_counter()))
        self.s3obj_name = "{}_{}_{}".format(
            self.s3acc_prefix, "object", int(time.perf_counter()))
        self.s3user_name = "{0}{1}".format("iam_user", str(time.perf_counter())).replace('.', '_')
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        self.log.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED : Teardown operations at test function level")
        self.s3acc_obj.logout_cortx_cli()
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        accounts = self.s3acc_obj.show_s3account_cortx_cli(output_format="json")[1]
        accounts = self.s3acc_obj.format_str_to_dict(
            input_str=accounts)["s3_accounts"]
        accounts = [acc["account_name"]
                    for acc in accounts if self.s3acc_prefix in acc["account_name"]]
        self.s3acc_obj.logout_cortx_cli()
        for acc in accounts:
            self.s3acc_obj.login_cortx_cli(
                username=acc, password=self.s3acc_password)
            #self.s3bkt_obj.delete_all_buckets_cortx_cli()
            self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            self.s3acc_obj.logout_cortx_cli()
        self.log.info("ENDED : Teardown operations at test function level")

    @classmethod
    def teardown_class(cls):
        """Teardown any state that was previously setup with a setup_class."""
        cls.log.info("STARTED : Teardown operations at test suit level")
        cls.s3acc_obj.close_connection()
        cls.log.info("ENDED : Teardown operations at test suit level")

    @classmethod
    def create_account(cls, acc_name, acc_email, acc_password):
        """Function will create IAM account."""
        return cls.s3acc_obj.create_s3account_cortx_cli(
            acc_name,
            acc_email,
            acc_password)

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7177")
    @CTFailOn(error_handler)
    def test_2393(self):
        """Create account using cortxcli."""
        self.log.info("STARTED: create account using cortxcli")

        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info(
            "Step 1: Created a new account with name %s", self.s3acc_name)
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
        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info(
            "Step 2: Listing account to verify new account is created")
        list_of_accounts = self.s3acc_obj.show_s3account_cortx_cli()
        assert_true(list_of_accounts[0], list_of_accounts[1])
        assert_in(self.s3acc_name, list_of_accounts[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info("ENDED: List account using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7179")
    @CTFailOn(error_handler)
    def test_2399(self):
        """Create 'N' No of Accounts."""
        self.log.info("STARTED: Create 'N' No of Accounts")
        total_accounts = 3
        self.log.info(
            "Step 1: Creating %s accounts", total_accounts)
        account_list = []
        acc_name = self.account_name
        for account in range(total_accounts):
            account_name = f"{acc_name}{account}{str(int(time.perf_counter()))}"
            email_id = f"{account_name}@seagate.com"
            resp = self.create_account(
                account_name, email_id, self.s3acc_password)
            assert_true(resp[0], resp[1])
            account_list.append(account_name)
        self.log.info("Step 1: Created %s accounts",
                      total_accounts)
        self.log.info(
            "Verifying %s accounts are created by listing accounts",
            total_accounts)
        list_of_accounts = self.s3acc_obj.show_s3account_cortx_cli()
        assert_true(list_of_accounts[0], list_of_accounts[1])
        for account in account_list:
            assert_in(account, list_of_accounts[1])
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
        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info(
            "Step 2: Creating another account with existing account name")
        try:
            self.create_account(self.s3acc_name,
                                acc_email=self.s3acc_email,
                                acc_password=self.s3acc_password)
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
        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info(
            "Step 2: Deleting account with name %s", self.s3acc_name)

        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_true(login[0], login[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(self.s3acc_name)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Deleted account with name %s successfully",
            self.s3acc_name)
        self.log.info("ENDED: Delete Account using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7182")
    @CTFailOn(error_handler)
    def test_2430(self):
        """CRUD operations with valid login credentials using cortxcli."""
        self.log.info(
            "STARTED: CRUD operations with valid login credentials using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        file_size = 1
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])

        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)

        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Create access key for newly created user")
        resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
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
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.s3bucket_name)
        # resp = s3_user_obj.create_bucket(self.s3bucket_name)
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
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])

        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Listing users and verifying user is created")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users_List %s", resp[1])
        assert_true(resp[0], resp[1])
        assert_in(self.s3user_name, resp[1], resp[1])
        self.log.info("Step 2: Listed users and verified user is created")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info("ENDED: create user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7184")
    @CTFailOn(error_handler)
    def test_2406(self):
        """Create access key for user using cortxcli."""
        self.log.info("STARTED: create access key for user using cortxcli")
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        self.log.info(
            "Step 1: Creating a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info(
            "Step 1: Created a user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Created access key for the user")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info("ENDED: create access key for user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7185")
    @CTFailOn(error_handler)
    def test_2405(self):
        """Max num of users supported using cortxcli."""
        self.log.info("STARTED: max num of users supported using cortxcli")
        self.log.info("Step 1: Create new account")
        total_users = 100
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account successfully")
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Step 2: Creating %s users", total_users)
        users_list = list()
        for user in range(total_users):
            my_user_name = f"{self.s3user_name}{user}"
            self.log.info("Creating user with name %s", my_user_name)
            resp = self.iam_user_obj.create_iam_user(user_name=my_user_name,
                                                     password=self.s3acc_password,
                                                     confirm_password=self.s3acc_password)
            assert_true(resp[0], resp[1])
            users_list.append(my_user_name)
            self.log.info("Created user with name %s", my_user_name)
        self.log.info("Step 2: Created %s users", total_users)
        self.log.info("Verifying %s users are created", total_users)
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users_List %s", resp[1])
        assert_true(resp[0], resp[1])
        for user in users_list:
            assert_in(user, resp[1], resp[1])
        self.log.info("Number of users : %s", len(resp[1]))
        assert_true(resp[0], resp[1])
        assert_greater_equal(
            (len(users_list)),
            self.total_users,
            resp[1])
        self.log.info("Verified %s users are created", total_users)
        self.log.info("Step 3: Deleting %s users", total_users)
        for user_name in users_list:
            resp = self.iam_user_obj.delete_iam_user(user_name)
            assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
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
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)

        self.log.info(
            "Step 1: Creating user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created user with name %s", self.s3user_name)
        self.log.info(
            "Step 2: Creating user with existing name %s", self.s3user_name)
        try:
            self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                              password=self.s3acc_password,
                                              confirm_password=self.s3acc_password)
        except CTException as error:
            assert_in(err_message,
                      error.message,
                      error.message)
        self.log.info(
            "Step 2: Could not create user with existing name %s", self.s3user_name)
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info(
            "ENDED: creating user with existing user name using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7187")
    @CTFailOn(error_handler)
    def test_2403(self):
        """Delete user using cortxcli."""
        self.log.info("STARTED: Delete user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)

        self.log.info(
            "Step 1: Creating user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Deleting user")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info("Step 2: Deleted user successfully")
        self.log.info("ENDED: Delete user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7188")
    @CTFailOn(error_handler)
    def test_2402(self):
        """Update user using cortxcli."""
        self.log.info("STARTED: Update user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        # new_user_name = "testuser2402"
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)

        self.log.info(
            "Step 1: Creating user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        access_key = resp["access_keys"][0]["access_key_id"]
        self.log.info("Access Key for user is %s", access_key)
        self.log.info("Step 2: Updating user name of already existing user")
        # new_iam_obj = iam_test_lib.IamTestLib(
        #     access_key=access_key,
        #     secret_key=secret_key)
        # resp = new_iam_obj.update_user(new_user_name, usr_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Updated user name of already existing user")
        self.log.info(
            "Step 3: Listing users and verifying user name is updated")
        resp = self.iam_user_obj.list_iam_user()
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3user_name,
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
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])

        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Listing users and verifying user is created")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users_List %s", resp[1])
        assert_true(resp[0], resp[1])
        assert_in(self.s3user_name, resp[1], resp[1])
        self.log.info("Step 2: Listed users and verified user is created")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info(
            "Listed users and verified user details are listed")
        self.log.info("ENDED: list user using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7196")
    @CTFailOn(error_handler)
    def test_2410(self):
        """Delete accesskey using cortxcli."""
        self.log.info("STARTED: delete accesskey using cortxcli")
        self.log.info("creating s3account using cortxcli")
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info("Verifying s3account created using cortxcli")
        assert_true(resp[0], resp[1])
        self.log.info("s3account created using cortxcli")
        self.log.info("loggingout from s3acc")
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("loggingout from s3acc successfully")
        self.log.info("Login to iam user account")
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("login to iam account successfully")
        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        self.log.info(
            "Step 1: Creating a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info(
            "Step 1: Created a user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Created access key for the user")
        self.log.info("Step 3: Deleting access key of the user")
        resp = self.accesskeys_obj.delete_s3access_key(access_key=resp[1],
                                                       user_name=self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Deleted access key of the user")

        self.log.info("Step 4: Listing access key of the user")
        resp = self.accesskeys_obj.show_s3access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        # Verifying list is empty
        assert_true(len(resp["access_keys"][1]["access_key_id"]) == 0,
                    resp["access_keys"][1]["access_key_id"])
        self.log.info("Step 4: Listed access key of the user successfully")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.log.info("logging out from user account")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info("ENDED: delete accesskey using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7197")
    @CTFailOn(error_handler)
    def test_2409(self):
        """Update accesskey with inactive mode using cortxcli."""
        status = "Inactive"
        self.log.info(
            "STARTED: update accesskey with inactive mode using cortxcli")
        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        self.log.info("creating s3account using cortxcli")
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info("Verifying s3account created using cortxcli")
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: s3account created using cortxcli")
        self.log.info("loggingout from s3acc")
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("loggingout from s3acc successfully")
        self.log.info("Login to iam user account")
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("login to iam account successfully")
        self.log.info(
            "Step 2: Creating a new user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)

        self.log.info("Step 2: Created a user with name %s", self.s3user_name)
        self.log.info("Verifying user is created by listing users")
        assert_true(resp[0], resp[1])
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info(
            "Step 3: Created a user with name %s", self.s3user_name)
        self.log.info("Step 3: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Created access key for the user")
        self.log.info("Get Created Access Key")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        # assert_true(resp[0], resp[1])
        access_key_to_update = resp["access_keys"][1]["access_key_id"]
        self.log.info("access key to update is %s", access_key_to_update)
        self.log.info("Step 4: Updating access key of user")
        resp = self.accesskeys_obj.update_s3access_key(user_name=self.s3user_name,
                                                       access_key=access_key_to_update,
                                                       status=status)
        assert_true(resp[0], resp[1])
        self.log.info("Step 4: Updated access key of user")
        self.log.info("Step 5: Verifying that access key of user is updated")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        new_access_key = resp["access_keys"][1]["access_key_id"]
        self.log.info("New access key after update %s", new_access_key)
        # status = resp[1]["access_keys"][1]["Status"]
        assert_not_equal(new_access_key, access_key_to_update, resp)
        # assert_equal(status, status, resp[1])
        self.log.info(
            "Step 5: Verified that access key of user is updated successfully")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(user_name=self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
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

        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a new account with name %s", self.s3acc_name)

        self.log.info(
            "Step 2: Logiing out to s3account and login to user account")
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: login to iam user account successfully")

        self.log.info(
            "Step 3: Creating a user with name %s", self.s3user_name)
        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s", self.s3user_name)

        self.log.info("Step 4: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("access key after creating for user %s", resp[1])
        self.log.info("Step 4: Created access key for the user %s", self.s3user_name)
        # user_access_key = resp[1]["Access Key"]["AccessKeyId"]
        self.log.info("Step 5: Listing access key of the user")
        resp = self.accesskeys_obj.show_s3access_key(self.s3user_name)
        self.log.info("access key after listing %s", resp)
        resp_access_key = resp[1]["access_keys"][1]["access_key_id"]
        # assert_equal(user_access_key, resp_access_key, resp[1])
        self.log.info("Step 5: Listed access key of the user successfully %s", resp_access_key)
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(user_name=self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info("ENDED: list accesskey for User using cortxcli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7192")
    @CTFailOn(error_handler)
    def test_2408(self):
        """Update accesskey with active mode using cortxcli."""
        status = "Active"
        self.log.info(
            "STARTED: update accesskey with active mode using cortxcli")
        self.log.info(
            "Step 1: Creating a new account with name %s", self.s3acc_name)
        self.log.info("creating s3account using cortxcli")
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info("Verifying s3account created using cortxcli")
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: s3account created using cortxcli")
        self.log.info("loggingout from s3acc")
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("loggingout from s3acc successfully")
        self.log.info("Login to iam user account")
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("login to iam account successfully")
        self.log.info(
            "Step 2: Creating a new user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)

        self.log.info("Step 2: Created a user with name %s", self.s3user_name)
        self.log.info("Verifying user is created by listing users")
        assert_true(resp[0], resp[1])
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info(
            "Step 3: Created a user with name %s", self.s3user_name)
        self.log.info("Step 3: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Created access key for the user")
        self.log.info("Get Created Access Key")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        # assert_true(resp[0], resp[1])
        access_key_to_update = resp["access_keys"][1]["access_key_id"]
        self.log.info("access key to update is %s", access_key_to_update)
        self.log.info("Step 4: Updating access key of user")
        resp = self.accesskeys_obj.update_s3access_key(user_name=self.s3user_name,
                                                       access_key=access_key_to_update,
                                                       status=status)
        assert_true(resp[0], resp[1])
        self.log.info("Step 4: Updated access key of user")
        self.log.info("Step 5: Verifying that access key of user is updated")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        new_access_key = resp["access_keys"][1]["access_key_id"]
        self.log.info("New access key after update %s", new_access_key)
        assert_equal(new_access_key, access_key_to_update, resp)
        self.log.info(
            "Step 5: Verified that access key of user is updated successfully")
        self.log.info(
            "Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(user_name=self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.iam_user_obj.logout_cortx_cli()
        self.log.info(
            "ENDED: update accesskey with active mode using cortxcli")

    #
    # @pytest.mark.s3_ops
    # @pytest.mark.tags("TEST-7193")
    # @CTFailOn(error_handler)
    # def test_2398(self):
    #     """Check Login to account with invalid creds and perform s3 crud operations using cortxcli."""
    #     self.log.info(
    #         "STARTED: login to account with invalid cred and perform s3 crud ops using cortxcli")
    #     self.log.info("Step 1: Create new account")
    #     from libs.s3 import ACCESS_KEY, SECRET_KEY
    #     err_message = "InvalidAccessKeyId"
    #     download_obj_err = "Forbidden"
    #     file_size = 1
    #     # Dummy access and secret keys
    #     user_access_key = ACCESS_KEY
    #     user_secret_key = SECRET_KEY
    #     resp = self.create_account(acc_name=self.s3acc_name,
    #                                acc_email=self.s3acc_email,
    #                                acc_password=self.s3acc_password)
    #     assert_true(resp[0], resp[1])
    #     self.log.info("Step 1: Created new account")
    #     s3_user_obj = s3_test_lib.S3TestLib(
    #         access_key=user_access_key,
    #         secret_key=user_secret_key)
    #     self.log.info("Step 2: Performing operations with invalid user's credentials")
    #     self.log.info("Creating a bucket with name %s", self.s3bucket_name)
    #     try:
    #         s3_user_obj.create_bucket(self.s3bucket_name)
    #     except CTException as error:
    #         assert_in(
    #             err_message,
    #             error.message,
    #             error.message)
    #     self.log.info(
    #         "Bucket with name %s is not created", self.s3bucket_name)
    #     self.log.info(
    #         "Putting object %s to bucket %s",
    #         self.s3obj_name, self.s3bucket_name)
    #     try:
    #         create_file(
    #             self.test_file_path,
    #             file_size)
    #         s3_user_obj.put_object(
    #             self.s3bucket_name,
    #             self.s3obj_name,
    #             self.test_file_path)
    #     except CTException as error:
    #         assert_in(
    #             err_message,
    #             error.message,
    #             error.message)
    #     self.log.info(
    #         "Could not put object %s to bucket %s",
    #         self.s3obj_name, self.s3bucket_name)
    #     self.log.info("Downloading object from bucket %s", self.s3bucket_name)
    #     try:
    #         s3_user_obj.object_download(
    #             self.s3bucket_name,
    #             self.s3obj_name,
    #             self.test_file_path)
    #     except CTException as error:
    #         assert_in(
    #             download_obj_err,
    #             error.message,
    #             error.message)
    #     self.log.info(
    #         "Could not download object from bucket %s", self.s3bucket_name)
    #     self.log.info(
    #         "Step 2: Performed CRUD operations with invalid user's credentials")
    #     self.log.info(
    #         "ENDED: login to account with invalid cred and perform s3 crud ops using cortxcli")
    #
    # @pytest.mark.s3_ops
    # @pytest.mark.tags("TEST-7195")
    # @CTFailOn(error_handler)
    # def test_2397(self):
    #     """Login to account with valid credentials and perform s3 crud operations using cortxcli."""
    #     self.log.info(
    #         "STARTED: login to account with valid creds and perform s3 crud ops using cortxcli")
    #     self.log.info("Step 1: Create new account and new user in it")
    #     file_size = 1
    #     resp = self.create_account(acc_name=self.s3acc_name,
    #                                acc_email=self.s3acc_email,
    #                                acc_password=self.s3acc_password)
    #     assert_true(resp[0], resp[1])
    #
    #     self.s3acc_obj.logout_cortx_cli()
    #     login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
    #                                               password=self.s3acc_password)
    #     assert_utils.assert_equals(login[0], True, "Server authentication check failed")
    #     self.log.info("Creating iam user with name %s", self.s3user_name)
    #     resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
    #                                              password=self.s3acc_password,
    #                                              confirm_password=self.s3acc_password)
    #     assert_true(resp[0], resp[1])
    #     self.log.info("Step 1: Created new account and new user in it")
    #     self.log.info("Step 2: Create access key for newly created user")
    #     # new_iam_obj = iam_test_lib.IamTestLib(
    #     #     access_key=access_key,
    #     #     secret_key=secret_key)
    #     resp = self.accesskeys_obj.create_s3access_key(self.s3user_name)
    #     assert_true(resp[0], resp[1])
    #     # user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
    #     # user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
    #     self.log.info("Step 2: Created access key for newly created user")
    #     s3_user_obj = s3_test_lib.S3TestLib(
    #         access_key=user_access_key,
    #         secret_key=user_secret_key)
    #     self.log.info(
    #         "Step 3: Performing CRUD operations using valid user's credentials")
    #     self.log.info("Creating a bucket with name %s", self.s3bucket_name)
    #     resp = self.s3bkt_obj.create_bucket_cortx_cli(self.s3bucket_name)
    #     assert_true(resp[0], resp[1])
    #     self.log.info(
    #         "Bucket with name %s is created successfully", self.s3bucket_name)
    #     create_file(self.test_file_path, file_size)
    #     self.log.info(
    #         "Putting object %s to bucket %s",
    #         self.s3obj_name, self.s3bucket_name)
    #     resp = s3_user_obj.put_object(
    #         self.s3bucket_name,
    #         self.s3obj_name,
    #         self.test_file_path)
    #     assert_true(resp[0], resp[1])
    #     self.log.info(
    #         "Object %s successfully put to bucket %s",
    #         self.s3obj_name, self.s3bucket_name)
    #     self.log.info("Downloading object from bucket %s", self.s3bucket_name)
    #     resp = s3_user_obj.object_download(
    #         self.s3bucket_name, self.s3obj_name, self.test_file_path)
    #     assert_true(resp[0], resp[1])
    #     assert_equal(
    #         resp[1],
    #         self.test_file_path,
    #         resp[1])
    #     self.log.info(
    #         "Downloading object from bucket %s successfully", self.s3bucket_name)
    #     self.log.info(
    #         "Step 3: Performed CRUD operations using valid user's credentials")
    #     # Cleanup activity
    #     resp = self.s3bkt_obj.delete_bucket_cortx_cli(self.s3bucket_name)
    #     assert_true(resp[0], resp[1])
    #     self.log.info(
    #         "ENDED: login to account with valid creds and perform s3 crud ops using cortxcli")
