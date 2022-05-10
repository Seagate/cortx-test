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
from libs.s3 import ACCESS_KEY, SECRET_KEY


# pylint:disable=too-many-public-methods, too-many-instance-attributes
class TestCortxcli:
    """Cortxcli Blackbox Testsuite."""

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        """Setup all the states required for execution of this test suit."""
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.file_size = 1
        cls.error = "InvalidAccessKeyId"
        cls.err_message = "EntityAlreadyExists"
        cls.account_name = "seagate_account"
        cls.test_file_path = "/root/testfile"
        cls.bucket_prefix = "clis3bkt"
        cls.s3acc_prefix = "cli_s3acc"
        cls.s3acc_email = "{}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.log.info("ENDED : Setup operations at test suit level")

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite.

        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.log.info("STARTED : Setup operations at test function level")
        self.iam_users_list = list()
        self.s3_accounts_list = list()
        self.s3acc_obj = CortxCliS3AccountOperations()
        self.s3acc_obj.open_connection()
        self.s3bkt_obj = CortxCliS3BucketOperations(session_obj=self.s3acc_obj.session_obj)
        self.csm_user_obj = CortxCliCsmUser(session_obj=self.s3acc_obj.session_obj)
        self.iam_user_obj = CortxCliIamUser(session_obj=self.s3acc_obj.session_obj)
        self.accesskeys_obj = CortxCliS3AccessKeys(session_obj=self.s3acc_obj.session_obj)
        self.s3acc_name = "{}_{}".format(self.s3acc_prefix, int(time.perf_counter_ns()))
        self.s3acc_email = self.s3acc_email.format(self.s3acc_name)
        self.s3bucket_name = "{}-{}".format("s3bucket", int(time.perf_counter_ns()))
        self.s3obj_name = "{}_{}_{}".format(self.s3acc_prefix, "object",
                                            int(time.perf_counter_ns()))
        self.s3user_name = "{0}{1}".format("iam_user", str(time.perf_counter_ns()))
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_true(login[0], login[1])
        self.log.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED : Teardown operations at test function level")
        for acc in self.s3_accounts_list:
            self.s3acc_obj.login_cortx_cli(username=acc, password=self.s3acc_password)
            for iam_user in self.iam_users_list:
                self.iam_user_obj.delete_iam_user(iam_user)
            self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            self.s3acc_obj.logout_cortx_cli()
        self.s3acc_obj.close_connection()
        self.log.info("ENDED : Teardown operations at test function level")

    def create_account(self, acc_name, acc_email, acc_password):
        """Function will create IAM account."""

        return self.s3acc_obj.create_s3account_cortx_cli(acc_name, acc_email, acc_password)

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-7177")
    @CTFailOn(error_handler)
    def test_2393(self):
        """Create account using cortxcli."""
        self.log.info("STARTED: create account using cortxcli")
        self.log.info("Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info("Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info("Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Verified that new account is created successfully")
        self.log.debug("Logging out from s3acc cortxcli")
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: create account using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-7178")
    @CTFailOn(error_handler)
    def test_2394(self):
        """List account using cortxcli."""
        self.log.info("STARTED: List account using cortxcli")
        self.log.info("Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info("Step 2: Listing account to verify new account is created")
        list_of_accounts = self.s3acc_obj.show_s3account_cortx_cli()
        assert_true(list_of_accounts[0], list_of_accounts[1])
        assert_in(self.s3acc_name, list_of_accounts[1])
        self.log.info("Step 2: Verified that new account is created successfully")
        self.log.debug("Logging out from s3acc cortxcli")
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: List account using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7179")
    @CTFailOn(error_handler)
    def test_2399(self):
        """Create 'N' No of Accounts."""
        self.log.info("STARTED: Create 'N' No of Accounts")
        total_accounts = 3
        self.log.info("Step 1: Creating %s accounts", total_accounts)
        account_list = []
        acc_name = self.account_name
        for account in range(total_accounts):
            account_name = f"{acc_name}{account}{str(int(time.perf_counter()))}"
            email_id = f"{account_name}@seagate.com"
            resp = self.create_account(account_name, email_id, self.s3acc_password)
            assert_true(resp[0], resp[1])
            account_list.append(account_name)
        self.log.info("Step 1: Created %s accounts", total_accounts)
        self.log.info("Verifying %s accounts are created by listing accounts", total_accounts)
        list_of_accounts = self.s3acc_obj.show_s3account_cortx_cli()
        assert_true(list_of_accounts[0], list_of_accounts[1])
        for account in account_list:
            assert_in(account, list_of_accounts[1])
        self.log.info("Verified %s accounts are created by listing accounts", total_accounts)
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("Deleting created account")
        for acc in account_list:
            self.s3acc_obj.login_cortx_cli(
                username=acc, password=self.s3acc_password)
            self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            self.s3acc_obj.logout_cortx_cli()
        self.log.info("ENDED: Create 'N' No of Accounts")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7180")
    @CTFailOn(error_handler)
    def test_2396(self):
        """Create account with existing name using cortxcli."""
        self.log.info("STARTED: create account with existing name using cortxcli")
        err_message = "EntityAlreadyExists"
        self.log.info("Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info("Step 2: Creating another account with existing account name")
        try:
            self.create_account(self.s3acc_name, acc_email=self.s3acc_email,
                                acc_password=self.s3acc_password)
        except CTException as error:
            assert_in(err_message, error.message, error.message)
        self.log.info("Step 2: Created another account with existing account name")
        self.log.debug("Logging out from s3acc cortxcli")
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: create account with existing name using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-7181")
    @CTFailOn(error_handler)
    def test_2395(self):
        """Delete Account using cortxcli."""
        self.log.info("STARTED: Delete Account using cortxcli")
        self.log.info("Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created a new account with name %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(username=self.s3acc_name,
                                               password=self.s3acc_password)
        assert_true(login[0], login[1])
        self.log.info("Step 2: Deleting account with name %s", self.s3acc_name)
        resp = self.s3acc_obj.delete_s3account_cortx_cli(self.s3acc_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Deleted account with name %s successfully",
                      self.s3acc_name)
        self.log.debug("Logging out from s3acc cortxcli")
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("ENDED: Delete Account using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7182")
    @CTFailOn(error_handler)
    def test_2430(self):
        """CRUD operations with valid login credentials using cortxcli."""
        self.log.info("STARTED: CRUD operations with valid login credentials using cortxcli")
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
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
        self.log.info("Step 1: Creating a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info("Step 1: Created a user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        user_access_key = resp[1]["access_key"]
        user_secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: Created access key for newly created user")
        s3_user_obj = s3_test_lib.S3TestLib(access_key=user_access_key, secret_key=user_secret_key)
        self.log.info("Step 3: Performing CRUD operations using valid user's credentials")
        self.log.info("Creating a bucket with name %s", self.s3bucket_name)
        resp = s3_user_obj.create_bucket(self.s3bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("Bucket with name %s is created successfully", self.s3bucket_name)
        create_file(self.test_file_path, count=1)
        self.log.info("Putting object %s to bucket %s", self.s3obj_name, self.s3bucket_name)
        resp = s3_user_obj.put_object(self.s3bucket_name, self.s3obj_name, self.test_file_path)
        assert_true(resp[0], resp[1])
        self.log.info("Object %s successfully put to bucket %s",
                      self.s3obj_name, self.s3bucket_name)
        self.log.info("Downloading object from bucket %s", self.s3bucket_name)
        resp = s3_user_obj.object_download(self.s3bucket_name, self.s3obj_name, self.test_file_path)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1], self.test_file_path, resp[1])
        self.log.info("Downloading object from bucket %s successfully", self.s3bucket_name)
        self.log.info("Step 3: Performed CRUD operations using valid user's credentials")
        self.log.debug("Logging out from s3_user cortxcli")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.iam_users_list.append(self.s3user_name)
        self.log.info("ENDED: CRUD operations with valid login credentials using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7183")
    @CTFailOn(error_handler)
    def test_2400(self):
        """Create user using cortxcli."""
        self.log.info("STARTED: create user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
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
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.iam_users_list.append(self.s3user_name)
        self.log.info("ENDED: create user using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
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
        self.log.info("Step 1: Creating a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info("Step 1: Created a user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Created access key for the user")
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.iam_users_list.append(self.s3user_name)
        self.log.info("ENDED: create access key for user using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7185")
    @CTFailOn(error_handler)
    def test_2405(self):
        """Max num of users supported using cortxcli."""
        self.log.info("STARTED: max num of users supported using cortxcli")
        self.log.info("Step 1: Create new account")
        total_users = 10
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
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
        assert_greater_equal((len(users_list)), total_users, resp[1])
        self.log.info("Verified %s users are created", total_users)
        self.log.info("Step 3: Deleting %s users", total_users)
        for user_name in users_list:
            resp = self.iam_user_obj.delete_iam_user(user_name)
            assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("ENDED: max num of users supported using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7186")
    @CTFailOn(error_handler)
    def test_2404(self):
        """Creating user with existing user name using cortxcli."""
        self.log.info("STARTED: creating user with existing user name using cortxcli")
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

        self.log.info("Step 1: Creating user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating user with existing name %s", self.s3user_name)
        try:
            self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                              password=self.s3acc_password,
                                              confirm_password=self.s3acc_password)
        except CTException as error:
            assert_in(err_message, error.message, error.message)
        self.log.info("Step 2: Could not create user with existing name %s", self.s3user_name)
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: creating user with existing user name using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
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

        self.log.info("Step 1: Creating user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Deleting user")
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("Step 2: Deleted user successfully")
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: Delete user using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
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
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("Listed users and verified user details are listed")
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: list user using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
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
        self.log.info("Step 1: Creating a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info("Step 1: Created a user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Created access, secret key for the user %s,%s",
                      resp[1]["access_key"],
                      resp[1]["secret_key"])
        self.log.info("Step 3: Deleting access key of the user")
        deleted_access_key = resp[1]["access_key"]
        resp = self.accesskeys_obj.delete_s3access_key(access_key=resp[1]["access_key"],
                                                       user_name=self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Deleted access key of the user")
        self.log.info("Step 4: Listing access key of the user")
        resp = self.accesskeys_obj.show_s3access_key(self.s3user_name)
        self.log.info(resp)
        # Verifying list is empty
        for item in resp["access_keys"]:
            assert_not_equal(item["access_key_id"], deleted_access_key)
        self.log.info("Step 4: Listed access key of the user successfully")
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.log.info("logging out from user account")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.iam_users_list.append(self.s3user_name)
        self.log.info("ENDED: delete accesskey using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7197")
    @CTFailOn(error_handler)
    def test_2409(self):
        """Update accesskey with inactive mode using cortxcli."""
        status = "Inactive"
        self.log.info("STARTED: update accesskey with inactive mode using cortxcli")
        self.log.info("Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info("Verifying s3account created using cortxcli")
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("Login to iam user account")
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Step 2: Creating a new user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        self.log.info("Verifying user is created by listing users")
        assert_true(resp[0], resp[1])
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Creating access key for the user %s", self.s3user_name)
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        created_access_key = resp[1]["access_key"]
        self.log.info("Step 3: Created access key for the user %s", self.s3user_name)
        self.log.info("Get Created Access Key %s", created_access_key)
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        acc_key_list = list()
        for item in resp["access_keys"]:
            acc_key_list.append(item["access_key_id"])
        assert_in(created_access_key, acc_key_list, "Key not created")
        self.log.info("Access Key Created")
        self.log.info("Step 4: Updating access key of user")
        resp = self.accesskeys_obj.update_s3access_key(user_name=self.s3user_name,
                                                       access_key=created_access_key,
                                                       status=status)
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Verifying that access key of user is updated")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        acc_key_list = list()
        for item in resp["access_keys"]:
            acc_key_list.append((item["access_key_id"], item["status"]))
        for data in acc_key_list:
            if data[0] == created_access_key and data[1] == "Inactive":
                self.log.info("Access Key updated")
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(user_name=self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("Step 6: Verified that access key of user is updated successfully")
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info("ENDED: update accesskey with inactive mode using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7198")
    @CTFailOn(error_handler)
    def test_2407(self):
        """List accesskey for User using cortxcli."""
        self.log.info("STARTED: list accesskey for User using cortxcli")
        self.log.info("Step 1: Creating a new account with name %s", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created a new account with name %s", self.s3acc_name)
        self.log.info("Step 2: Logging out to s3account and login to user account")
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: login to iam user account successfully")
        self.log.info("Step 3: Creating a user with name %s", self.s3user_name)
        self.log.info("Creating iam user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Created a user with name %s", self.s3user_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("access key after creating for user %s", resp[1]["access_key"])
        self.log.info("Step 4: Created access key for the user %s", self.s3user_name)
        user_access_key = resp[1]["access_key"]
        self.log.info("Step 5: Listing access key %s of the user", user_access_key)
        resp = self.accesskeys_obj.show_s3access_key(self.s3user_name)
        self.log.info("access keys after listing %s", resp)
        acc_key_list = list()
        for item in resp["access_keys"]:
            acc_key_list.append(item["access_key_id"])
        assert_in(user_access_key, acc_key_list, "Key not present")
        self.log.info("Access Key Listed")
        self.log.info("Step 5: Listed access key of the user successfully")
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(user_name=self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.s3_accounts_list.append(self.s3acc_name)
        self.iam_users_list.append(self.s3user_name)
        self.log.info("ENDED: list accesskey for User using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7192")
    @CTFailOn(error_handler)
    def test_2408(self):
        """Update accesskey with active mode using cortxcli."""
        self.log.info("STARTED: update accesskey with inactive mode using cortxcli")
        self.log.info("Step 1: Creating a new account with name %s using cortxcli", self.s3acc_name)
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        self.log.info("Verifying s3account created using cortxcli")
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("logging out from s3acc successfully")
        self.log.info("Login to iam user account")
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Step 2: Creating a new user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        self.log.info("Step 2: Created a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Creating access key for the user %s", self.s3user_name)
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Created access, secret key for the user %s,%s",
                      resp[1]["access_key"], resp[1]["secret_key"])
        created_access_key = resp[1]["access_key"]
        self.log.info("Get Created Access Key %s", created_access_key)
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        acc_key_list = list()
        for item in resp["access_keys"]:
            acc_key_list.append(item["access_key_id"])
        assert_in(created_access_key, acc_key_list, "Key not present")
        self.log.info("Access Key Created is %s", created_access_key)
        self.log.info("Step 4: Updating access key of user")
        resp = self.accesskeys_obj.update_s3access_key(
            user_name=self.s3user_name, access_key=created_access_key, status="Active")
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Verifying that access key of user is updated")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        acc_key_list = list()
        for item in resp["access_keys"]:
            acc_key_list.append((item["access_key_id"], item["status"]))
        for data in acc_key_list:
            if data[0] == created_access_key and data[1] == "Active":
                self.log.info("Access Key updated")
                break
        else:
            assert_true(created_access_key, "Key not updated")
        self.log.info("Step 5: Verified that access key of user is updated successfully")
        self.log.info("Deleting IAM user %s", self.s3user_name)
        resp = self.iam_user_obj.delete_iam_user(user_name=self.s3user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("Step 6: Verified that access key of user is updated successfully")
        self.s3_accounts_list.append(self.s3acc_name)
        self.iam_users_list.append(self.s3user_name)
        self.log.info("ENDED: update accesskey with inactive mode using cortxcli")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7193")
    @CTFailOn(error_handler)
    def test_2398(self):
        """Check Login to account with invalid creds and perform s3 crud ops using cortxcli."""
        self.log.info(
            "STARTED: login to account with invalid cred and perform s3 crud ops using cortxcli")
        self.log.info("Step 1: Create new account")
        err_message = "InvalidAccessKeyId"
        download_obj_err = "Forbidden"
        file_size = 1
        # Dummy access and secret keys
        user_access_key = ACCESS_KEY
        user_secret_key = SECRET_KEY
        resp = self.create_account(acc_name=self.s3acc_name, acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("Step 1: Created new account")
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        s3_user_obj = s3_test_lib.S3TestLib(access_key=user_access_key, secret_key=user_secret_key)
        self.log.info("Step 2: Performing operations with invalid user's credentials")
        self.log.info("Creating a bucket with name %s", self.s3bucket_name)
        try:
            s3_user_obj.create_bucket(self.s3bucket_name)
        except CTException as error:
            assert_in(err_message, error.message, error.message)
        self.log.info("Bucket with name %s is not created", self.s3bucket_name)
        self.log.info("Putting object %s to bucket %s", self.s3obj_name, self.s3bucket_name)
        try:
            create_file(self.test_file_path, file_size)
            s3_user_obj.put_object(self.s3bucket_name, self.s3obj_name, self.test_file_path)
        except CTException as error:
            assert_in(err_message, error.message, error.message)
        self.log.info("Could not put object %s to bucket %s", self.s3obj_name, self.s3bucket_name)
        self.log.info("Downloading object from bucket %s", self.s3bucket_name)
        try:
            s3_user_obj.object_download(self.s3bucket_name, self.s3obj_name, self.test_file_path)
        except CTException as error:
            assert_in(download_obj_err, error.message, error.message)
        self.log.info("Could not download object from bucket %s", self.s3bucket_name)
        self.log.info("Step 2: Performed CRUD operations with invalid user's credentials")
        self.s3_accounts_list.append(self.s3acc_name)
        self.log.info(
            "ENDED: login to account with invalid cred and perform s3 crud ops using cortxcli")

    @pytest.mark.skip(reason="Duplicate to test_2430")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7195")
    @CTFailOn(error_handler)
    def test_2397(self):
        """Login to account with valid credentials and perform s3 crud operations using cortxcli."""
        self.log.info("STARTED: login to account with valid creds and perform s3 crud ops"
                      " using cortxcli")
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
        self.log.info("Step 1: Creating a user with name %s", self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Verifying user is created by listing users")
        resp = self.iam_user_obj.list_iam_user()
        self.log.info("Users list %s", resp[1])
        assert_true(resp[0], resp[1])
        self.log.info("Verified that user is created by listing users")
        self.log.info("Step 1: Created a user with name %s", self.s3user_name)
        self.log.info("Step 2: Creating access key for the user")
        resp = self.accesskeys_obj.create_s3_iam_access_key(self.s3user_name)
        assert_true(resp[0], resp[1])
        user_access_key = resp[1]["access_key"]
        user_secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: Created access key for newly created user")
        s3_user_obj = s3_test_lib.S3TestLib(access_key=user_access_key, secret_key=user_secret_key)
        self.log.info("Step 3: Performing CRUD operations using valid user's credentials")
        self.log.info("Creating a bucket with name %s", self.s3bucket_name)
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.s3bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("Bucket with name %s is created successfully", self.s3bucket_name)
        create_file(self.test_file_path, count=1)
        self.log.info("Putting object %s to bucket %s", self.s3obj_name, self.s3bucket_name)
        resp = s3_user_obj.put_object(self.s3bucket_name, self.s3obj_name, self.test_file_path)
        assert_true(resp[0], resp[1])
        self.log.info("Object %s successfully put to bucket %s", self.s3obj_name,
                      self.s3bucket_name)
        self.log.info("Downloading object from bucket %s", self.s3bucket_name)
        resp = s3_user_obj.object_download(self.s3bucket_name, self.s3obj_name, self.test_file_path)
        assert_true(resp[0], resp[1])
        assert_equal(resp[1], self.test_file_path, resp[1])
        self.log.info("Downloading object from bucket %s successfully", self.s3bucket_name)
        self.log.info("Step 3: Performed CRUD operations using valid user's credentials")
        # Cleanup activity
        resp = s3_user_obj.delete_object(self.s3bucket_name, self.s3obj_name)
        assert_true(resp[0], resp[1])
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(self.s3bucket_name)
        assert_true(resp[0], resp[1])
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.log.info("ENDED: login to account with valid creds and perform s3 crud ops using "
                      "cortxcli")

    @pytest.mark.skip(reason="update user using cortxcli is not supported")
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7188")
    @CTFailOn(error_handler)
    def test_2402(self):
        """Update user using cortxcli."""
        self.log.info("STARTED: Update user using cortxcli")
        self.log.info("Step 1: Create new account and new user in it")
        new_user_name = "testuser2402"
        resp = self.create_account(acc_name=self.s3acc_name,
                                   acc_email=self.s3acc_email,
                                   acc_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        login = self.iam_user_obj.login_cortx_cli(username=self.s3acc_name,
                                                  password=self.s3acc_password)
        assert_utils.assert_equals(login[0], True, "Server authentication check failed")
        self.log.info("Creating iam user with name %s", self.s3user_name)
        self.log.info("Step 1: Creating user with name %s", self.s3user_name)
        resp = self.iam_user_obj.create_iam_user(user_name=self.s3user_name,
                                                 password=self.s3acc_password,
                                                 confirm_password=self.s3acc_password)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        resp = self.accesskeys_obj.show_s3access_key(user_name=self.s3user_name)
        access_key = resp["access_keys"][0]["access_key_id"]
        secret_key = resp["access_keys"][0]["secret_key_id"]
        self.log.info("Access Key for user is %s", access_key)
        self.log.info("Step 2: Updating user name of already existing user")
        new_iam_obj = iam_test_lib.IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.update_user(new_user_name, self.s3user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Updated user name of already existing user")
        self.log.info("Step 3: Listing users and verifying user name is updated")
        resp = self.iam_user_obj.list_iam_user()
        assert_true(resp[0], resp[1])
        assert_in(self.s3user_name, resp[1], resp[1])
        self.log.info("Step 3: Listed users and verified user name is updated")
        self.log.info("ENDED: Update user using cortxcli")
