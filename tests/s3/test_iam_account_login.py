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
"""This file contains test for IAM account login"""

import time
import logging
import pytest
from libs.s3 import iam_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.assert_utils import \
    assert_true, assert_in, assert_is_not_none, assert_not_in

LOGGER = logging.getLogger(__name__)
IAM_OBJ = iam_test_lib.IamTestLib()
IAM_CFG = read_yaml("config/s3/test_iam_account_login.yaml")


class TestAccountLoginProfile():
    """Account Login Profile Test Suite."""

    def setup_method(self):
        LOGGER.info("STARTED: Setup Operation")
        self.account_name = IAM_CFG["iam_account_login"]["acc_name_prefix"]
        self.email_id = "{}{}".format(
            self.account_name,
            IAM_CFG["iam_account_login"]["email_suffix"])
        self.ldap_user = LDAP_USERNAME
        self.ldap_pwd = LDAP_PASSWD
        LOGGER.info("Deleting account starts with: {}".format(
            self.account_name))
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        LOGGER.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        LOGGER.info(all_acc)
        for acc_name in all_acc:
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        LOGGER.info("ENDED: Setup Operation")

    def teardown_method(self):
        """
        Function to perform the clean up for each test.
        """
        LOGGER.info("STARTED: Teardown Operations")
        self.account_name = IAM_CFG["iam_account_login"]["acc_name_prefix"]
        self.email_id = "{}{}".format(
            self.account_name,
            IAM_CFG["iam_account_login"]["email_suffix"])
        self.ldap_user = LDAP_USERNAME
        self.ldap_pwd = LDAP_PASSWD
        LOGGER.info("Deleting account starts with: {}".format(
            self.account_name))
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        LOGGER.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        LOGGER.info(all_acc)
        for acc_name in all_acc:
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        LOGGER.info("ENDED: Teardown Operations")

    def create_account_n_login_profile(
            self,
            acc_name,
            email,
            pwd,
            pwd_reset,
            ldap_user,
            ldap_pwd):
        """
        Helper method to create account and login profile for the same account.
        :param acc_name: Name of the account
        :param email: email ID for the account
        :param pwd: password for creating login profile
        :param pwd_reset: password resent value while creating login proffile for the account
        :param ldap_user: ldap user name
        :param ldap_pwd: ldap password
        :return: None
        """
        LOGGER.info("Step 1: Creating an account %s", acc_name)
        acc_res = IAM_OBJ.create_account_s3iamcli(acc_name, email,
                                                  ldap_user, ldap_pwd)
        assert_true(acc_res[0], acc_res[1])
        LOGGER.info("Step 1: Account created %s", acc_res[1])
        LOGGER.info(
            "Step 2: Creating login profile for an account %s", acc_name)
        login_res = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, pwd, acc_res[1]["access_key"],
            acc_res[1]["secret_key"], password_reset=pwd_reset)
        assert_true(login_res[0], login_res[1])
        LOGGER.info(
            "Step 2: Created login profile for an account %s", acc_name)
        return acc_res, login_res

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5651")
    @CTFailOn(error_handler)
    def test_2805(self):
        """Create account login profile for new account."""
        LOGGER.info("STARTED: Create account login profile for new account")
        test_cfg = IAM_CFG["test_9780"]
        LOGGER.info("Step 1: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(
            self.account_name, str(
                list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")
        LOGGER.info("Step 2: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 2: Account created %s", res[1])
        LOGGER.info(
            "Step 3: Creating login profile for an account %s",
            self.account_name)
        res = IAM_OBJ.create_account_login_profile_s3iamcli(
            self.account_name, test_cfg["password"], res[1]["access_key"],
            res[1]["secret_key"], password_reset=test_cfg["password_reset"])
        assert_true(res[0], res[1])
        assert_in(test_cfg["msg"], res[1], res[1])
        LOGGER.info("Step 3: Created login profile for an account %s "
                    "and details are %s", self.account_name, res[1])
        LOGGER.info("ENDED: Create account login profile for new account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5650")
    @CTFailOn(error_handler)
    def test_2806(self):
        """Create account login profile for nonexisting account."""
        LOGGER.info(
            "ENDED: Create account login profile for nonexisting account")
        test_cfg = IAM_CFG["test_9782"]
        LOGGER.info("Step 1: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(
            self.account_name, str(
                list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")
        LOGGER.info(
            "Step 2: Creating login profile for a non existing account")
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                test_cfg["account"], test_cfg["password"],
                test_cfg["access_key"], test_cfg["secret_key"],
                password_reset=test_cfg["password_reset"])
            LOGGER.info("after try")
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 2: failed to create login profile for a non existing account")
        LOGGER.info(
            "ENDED: Create account login profile for nonexisting account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5652")
    @CTFailOn(error_handler)
    def test_2807(self):
        """Create account login profile for currently deleted account."""
        LOGGER.info(
            "STARTED: Create account login profile for currently deleted account")
        test_cfg = IAM_CFG["test_9783"]
        LOGGER.info("Step 1: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(
            self.account_name, str(
                list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")
        LOGGER.info("Step 2: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 2: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info("Step 3: list and then delete recently created account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("Step 3: listed and Deleted recently created account")

        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(self.account_name, list_account[1])

        LOGGER.info(
            "Step 4: Creating account login profile for recently deleted account")
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key,
                secret_key, password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
            assert_in(test_cfg["long_err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to create login profile for recently deleted account")
        LOGGER.info(
            "ENDED: Create account login profile for currently deleted account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5645")
    @CTFailOn(error_handler)
    def test_2808(self):
        """Create account login profile with password of 0 character."""
        LOGGER.info(
            "Create account login profile with password of 0 character")
        test_cfg = IAM_CFG["test_9784"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating account login profile for account %s "
            "with password of 0 character", self.account_name)
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key,
                secret_key, password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info("Step 3: failed to create login profile for"
                    " an account %s", self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile with password of 0 character")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5644")
    @CTFailOn(error_handler)
    def test_2809(self):
        """Create account login profile with password of more than 128 characters."""
        LOGGER.info(
            "STARTED: Create account login profile with password of more than 128 characters.")
        test_cfg = IAM_CFG["test_9785"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating login profile for an account %s "
            "with password more than 128 characters", self.account_name)
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key,
                secret_key, password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to create login profile for an account %s "
            "with password more than 128 characters", self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile with password of more than 128 characters.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5643")
    @CTFailOn(error_handler)
    def test_2810(self):
        """Create account login profile with password of possible combinations."""
        LOGGER.info(
            "STARTED: Create login profile with password of possible combinations")
        test_cfg = IAM_CFG["test_9786"]
        for each_pwd in range(len(test_cfg["list_of_passwords"])):
            acc_name = "{}{}".format(self.account_name, each_pwd)
            email = "{}{}".format(
                acc_name, IAM_CFG["iam_account_login"]["email_suffix"])
            res = self.create_account_n_login_profile(
                acc_name,
                email,
                test_cfg["list_of_passwords"][each_pwd],
                password_reset=test_cfg["password_reset"],
                self.ldap_user,
                self.ldap_pwd)
            LOGGER.debug(res)
        LOGGER.info(
            "ENDED: Create account login profile with password of possible combinations")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5642")
    @CTFailOn(error_handler)
    def test_2811(self):
        """Create account login profile with password using invalid characters."""
        LOGGER.info(
            "Create account login profile with password using invalid characters")
        test_cfg = IAM_CFG["test_9787"]
        for each_pwd in range(len(test_cfg["list_special_invalid_char"])):
            acc_name = "{}{}".format(self.account_name, each_pwd)
            email = "{}{}".format(
                acc_name, IAM_CFG["iam_account_login"]["email_suffix"])
            pwd = test_cfg["list_special_invalid_char"][each_pwd]
            res = self.create_account_n_login_profile(
                acc_name,
                email,
                pwd,
                password_reset=test_cfg["password_reset"],
                self.ldap_user,
                self.ldap_pwd)
            LOGGER.debug(res)
        LOGGER.info(
            "Create account login profile with password using invalid characters")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5649")
    @CTFailOn(error_handler)
    def test_2812(self):
        """Create account login profile with --no-password-reset-required option."""
        LOGGER.info(
            "Create account login profile with --no-password-reset-required option.")
        test_cfg = IAM_CFG["test_9788"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Create account login profile with --no-password-reset-required option.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5648")
    @CTFailOn(error_handler)
    def test_2813(self):
        """Create account login profile with --password-reset-required option."""
        LOGGER.info(
            "Create account login profile with --password-reset-required option.")
        test_cfg = IAM_CFG["test_9789"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Create account login profile with --password-reset-required option.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5641")
    @CTFailOn(error_handler)
    def test_2814(self):
        """
        Create account login profile without mentioning  --password-reset-required
        --no-password-reset-required
        """
        LOGGER.info(
            "Create account login profile without mentioning  "
            "--password-reset-required --no-password-reset-required")
        test_cfg = IAM_CFG["test_9790"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating login profile for account %s without password reset options",
            self.account_name)
        res = IAM_OBJ.create_account_login_profile_without_both_reset_options(
            self.account_name, test_cfg["password"], access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Created login profile for account %s without password reset options",
            self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile without mentioning  "
            "--password-reset-required --no-password-reset-required")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5646")
    @CTFailOn(error_handler)
    def test_2815(self):
        """
        Create account login profile with both options
         --no-password-reset-required --password-reset-required
        """
        LOGGER.info(
            "STARTED: Create account login profile with both options "
            "--no-password-reset-required --password-reset-required")
        test_cfg = IAM_CFG["test_9791"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating account login profile for account %s with"
            " both password reset value", self.account_name)
        res = IAM_OBJ.create_account_login_profile_both_reset_options(
            self.account_name, test_cfg["password"], access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Created account login profile for account %s with"
            " both password reset value", self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile with both options "
            "--no-password-reset-required --password-reset-required")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5647")
    @CTFailOn(error_handler)
    def test_2816(self):
        """Create account login profile with accesskey and sercret key of its user."""
        LOGGER.info(
            "STARTED: Create account login profile with accesskey "
            "and sercret key of its user")
        test_cfg = IAM_CFG["test_9792"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        LOGGER.info("Step 2: Creating user with name %s", user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 2: Created user with name %s", user_name)
        LOGGER.info(
            "Step 3: Creating access key and secret key for user %s",
            user_name)
        new_IAM_OBJ = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_IAM_OBJ.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info(
            "Step 3: Created access key and secret key for user %s", user_name)
        LOGGER.info(
            "Step 4: Creating account login profile for account %s with keys of its user",
            self.account_name)
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name,
                test_cfg["password"],
                user_access_key,
                user_secret_key,
                password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to create account login profile for "
            "account %s with keys of its user", self.account_name)
        LOGGER.info(
            "Step 5: Deleting access key of user %s", user_name)
        res = new_IAM_OBJ.delete_access_key(user_name, user_access_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Deleted access key of user %s", user_name)
        LOGGER.info(
            "ENDED: Create account login profile with accesskey"
            " and sercret key of its user")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5629")
    @CTFailOn(error_handler)
    def test_2829(self):
        """Get the account login details."""
        LOGGER.info("STARTED: Get the account login details")
        test_cfg = IAM_CFG["test_9807"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        LOGGER.info(
            "Step 3: Getting account login profile for account %s",
            self.account_name)
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Got account login profile for account %s",
            self.account_name)
        LOGGER.info("ENDED: Get the account login details")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5628")
    @CTFailOn(error_handler)
    def test_2830(self):
        """Get the account login details for account not present."""
        LOGGER.info("STARTED: Get the account login details "
                    "for account not present")
        test_cfg = IAM_CFG["test_9808"]
        LOGGER.info(
            "Step 1: Getting account login profile for account not present")
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                test_cfg["account_name"], test_cfg["access_key"], test_cfg["secret_key"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 1: Failed to get account login profile for account not present")
        LOGGER.info("Get the account login details for account not present")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5627")
    @CTFailOn(error_handler)
    def test_2831(self):
        """Get login details for acc which is present but login not created."""
        LOGGER.info(
            "STARTED: Get login details for acc which is present but"
            " login not created")
        test_cfg = IAM_CFG["test_9809"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        LOGGER.info(
            "Step 2: Getting account login profile for account %s for which "
            "login is not created", self.account_name)
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                self.account_name, access_key, secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to get account login profile for account %s for "
            "which login is not created", self.account_name)
        LOGGER.info(
            "Ended: Get login details for acc which is present but login not created")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5626")
    @CTFailOn(error_handler)
    def test_2832(self):
        """Get login details for account which is recently got deleted."""
        LOGGER.info(
            "STARTED: Get login details for account which is recently got deleted")
        test_cfg = IAM_CFG["test_9810"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Deleted account %s using s3iamcli", self.account_name)
        LOGGER.info("Step 4: Get account login profile using s3iamcli")
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                self.account_name, access_key, secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to get account login profile using s3iamcli")
        LOGGER.info(
            "ENDED: Get login details for account which is recently got deleted")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5640")
    @CTFailOn(error_handler)
    def test_2833(self):
        """Get login profile with access key and secret key of its user."""
        LOGGER.info(
            "STARTED : Get login profile with access key and secret key of its user")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9811"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        LOGGER.info("Step 2: Creating user with name %s", user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 2: Created user with name %s", user_name)
        LOGGER.info(
            "Step 3: Creating access key and secret key for user %s",
            user_name)
        new_IAM_OBJ = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_IAM_OBJ.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info(
            "Step 3: Created access key and secret key for user %s", user_name)
        LOGGER.info(
            "Step 4: Creating account login profile for account %s with keys "
            "of its user", self.account_name)
        IAM_OBJ.create_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["password"],
            access_key,
            secret_key,
            password_reset=test_cfg["password_reset"])
        LOGGER.info(
            "Step 4: Created account login profile for account %s with "
            "keys of its user", self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                self.account_name, user_access_key, user_secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 5: Failed to get account login profile using s3iamcli")
        LOGGER.info(
            "Step 5: Deleting access key of user %s", user_name)
        res = new_IAM_OBJ.delete_access_key(user_name, user_access_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Deleted access key of user %s", user_name)
        LOGGER.info(
            "ENDED: Get login profile with access key and secret key of its user")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5611")
    @CTFailOn(error_handler)
    def test_2834(self):
        """Update account login profile with password only."""
        LOGGER.info(
            "STARTED: Update account login profile with password only")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9812"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        LOGGER.info(
            "Step 3: Getting account login profile for account %s",
            self.account_name)
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Getting account login profile for account %s",
            self.account_name)

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["new_password"], access_key, secret_key,
            password_reset=test_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Successful to get account login profile using s3iamcli")
        LOGGER.info(
            "Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("ENDED: Update account login profile with password only")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5614")
    @CTFailOn(error_handler)
    def test_2835(self):
        """Update account login profile with --password-reset-required."""
        LOGGER.info(
            "STARTED: Update account login profile with --password-reset-required")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9813"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")
        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["new_password"],
            access_key,
            secret_key,
            test_cfg["new_password_reset"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        LOGGER.info("Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with --password-reset-required")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5616")
    @CTFailOn(error_handler)
    def test_2836(self):
        """Update account login profile with  --no-password-reset-required."""
        LOGGER.info(
            "STARTED: Update account login profile with  --no-password-reset-required")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9814"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")
        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["new_password"],
            access_key,
            secret_key,
            test_cfg["new_password_reset"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        LOGGER.info(
            "Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with  "
            "--no-password-reset-required")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5613")
    @CTFailOn(error_handler)
    def test_2837(self):
        """
        Update account login profile with both --password-reset-required and
        --no-password-reset-required
        """
        LOGGER.info(
            "STARTED: Update account login profile with both "
            "--password-reset-required and --no-password-reset-required")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9815"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_both_reset_options(
            self.account_name, test_cfg["password"], access_key, secret_key)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        LOGGER.info(
            "Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with both"
            " --password-reset-required and --no-password-reset-required")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5612")
    @CTFailOn(error_handler)
    def test_2838(self):
        """Update account login profile with both password and reset flag."""
        LOGGER.info(
            "STARTED: Update account login profile with both password"
            " and reset flag")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9816"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["new_password"], access_key, secret_key,
            test_cfg["new_password_reset"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get account login profile using s3iamcli successful")
        LOGGER.info(
            "ENDED: Update account login profile with both password "
            "and reset flag")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5610")
    @CTFailOn(error_handler)
    def test_2839(self):
        """Update account login profile without password and without password reset flag."""
        LOGGER.info(
            "STARTED: Update account login profile without password and"
            " without password reset flag")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9817"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s without"
            " password", self.account_name)
        try:
            IAM_OBJ.update_account_login_profile_both_reset_options(
                self.account_name, access_key, secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to update login profile for account %s without password",
            self.account_name)
        LOGGER.info(
            "ENDED: Update account login profile with both password "
            "and reset flag")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5622")
    @CTFailOn(error_handler)
    def test_2840(self):
        """Update login profile for account which didn't have the login profile created."""
        LOGGER.info(
            "STARTED: Update account login profile for the account"
            " which didn't have the login profile created")
        LOGGER.info(
            "Creating an account %s with email %s",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9818"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 2: Updating account login profile for account %s",
            self.account_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key, secret_key,
                password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to update account login profile for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Update account login profile for the account"
            " which didn't have the login profile created")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5621")
    @CTFailOn(error_handler)
    def test_2841(self):
        """Update account login profile for the account which doesnt exist."""
        LOGGER.info(
            "STARTED: Update account login profile for the account "
            "which doesnt exist")
        LOGGER.info("Step 1: List account")
        test_cfg = IAM_CFG["test_9819"]
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        acc_name = test_cfg["account_name"]
        assert_not_in(acc_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")

        LOGGER.info(
            "Step 2: Updating account login profile for account %s",
            acc_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                acc_name, test_cfg["password"], test_cfg["access_key"],
                test_cfg["secret_key"], password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to update login profile for account %s",
            acc_name)
        LOGGER.info(
            "ENDED: Update account login profile for the account "
            "which doesnt exist")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5617")
    @CTFailOn(error_handler)
    def test_2842(self):
        """Update account login profile for the deleted account."""
        LOGGER.info(
            "STARTED: Update account login profile for the deleted account")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name,
            self.email_id)
        test_cfg = IAM_CFG["test_9820"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info(
            "Step 3: Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Deleted account %s using s3iamcli", account_name)
        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            account_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                self.account_name,
                test_cfg["new_password"],
                access_key,
                secret_key,
                password_reset=test_cfg["password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to update account login profile for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Update account login profile for the deleted account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5620")
    @CTFailOn(error_handler)
    def test_2843(self):
        """Update login profile for acc with new password as current password."""
        LOGGER.info(
            "STARTED: Update login profile for acc with new"
            " password as current password.")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9821"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["password"], access_key, secret_key,
            password_reset=test_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)

        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get account login profile using s3iamcli successful")
        LOGGER.info(
            "ENDED: Update login profile for acc with new password"
            " as current password.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5618")
    @CTFailOn(error_handler)
    def test_2844(self):
        """
        Update the account login profiles password with the new password
        which contains invalid characters Verify if it accepts all invalid
        characters
        """
        LOGGER.info(
            "STARTED: Update the account login profiles password with the new"
            " password which contains invalid characters.Verify if it accepts"
            " all invalid characters")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9822"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["new_password"], access_key, secret_key,
            password_reset=test_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get account login profile using s3iamcli successful")
        LOGGER.info(
            "ENDED: Update the account login profiles password with the new "
            "password which contains invalid characters.Verify if it accepts "
            "all invalid characters")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5679")
    @CTFailOn(error_handler)
    def test_2845(self):
        """Update login profile with accesskey and secret key of its user."""
        LOGGER.info(
            "STARTED: Update login profile with accesskey and "
            "secret key of its user")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9823"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])
        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        LOGGER.info("Step 2: Creating user with name %s", user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 2: Created user with name %s", user_name)
        LOGGER.info(
            "Step 3: Creating access key and secret key for user %s",
            user_name)
        new_IAM_OBJ = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_IAM_OBJ.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info(
            "Step 3: Created access key and secret key for user %s", user_name)
        LOGGER.info(
            "Step 4: Creating account login profile for account %s with keys"
            " of its user", self.account_name)
        IAM_OBJ.create_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["password"],
            access_key,
            secret_key,
            password_reset=test_cfg["password_reset"])

        LOGGER.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get account login profile using s3iamcli")
        LOGGER.info(
            "Updating account login profile for account %s",
            self.account_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                self.account_name, test_cfg["new_password"], user_access_key,
                user_secret_key, test_cfg["new_password_reset"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info("Deleting user access key")
        res = new_IAM_OBJ.delete_access_key(user_name, user_access_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with accesskey and "
            "secret key of its user")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5630")
    @CTFailOn(error_handler)
    def test_2882(self):
        """Get temporary credentials for Valid Account."""
        LOGGER.info("STARTED: Get temporary credentials for Valid Account")
        test_cfg = IAM_CFG["test_9861"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        LOGGER.info("ENDED: Get temporary credentials for Valid Account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5634")
    @CTFailOn(error_handler)
    def test_2883(self):
        """Get temporary credentials for Invalid Account."""
        LOGGER.info("STARTED: Get temporary credentials for Invalid Account")
        test_cfg = IAM_CFG["test_9862"]
        acc_name = test_cfg["account_name"]
        LOGGER.info(
            "%s invalid account used to get temporary creds.", acc_name)
        LOGGER.info(
            "Step 1: Getting temp auth credentials for invalid account")
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                acc_name, test_cfg["password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 1: Failed to get temp auth credentials for invalid account")
        LOGGER.info("ENDED: Get temporary credentials for Invalid Account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5625")
    @CTFailOn(error_handler)
    def test_2884(self):
        """Get the temp Cred for acc which is recently got deleted."""
        LOGGER.info(
            "STARTED: Get the temp Cred for acc which is recently got deleted")
        test_cfg = IAM_CFG["test_9862"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        LOGGER.info("Step 2: Deleting recently created account")
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("Step 2: Deleted recently created account")
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account {} which is"
            "recently got deleted".format(self.account_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to get temp auth credentials for account %s "
            "which is recently got deleted", self.account_name)
        LOGGER.info(
            "ENDED: Get the temp Cred for acc which is recently got deleted")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5658")
    @CTFailOn(error_handler)
    def test_2885(self):
        """Verify using valid temp cred to perform s3 operations."""
        LOGGER.info(
            "STARTED: Verify using valid temp cred to perform s3 operations")
        test_cfg = IAM_CFG["test_9864"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        LOGGER.info(
            "Step 3: Perform s3 ops using temp auth credentials for account %s"
            "with creds as %s", self.account_name, res[1])
        res = IAM_OBJ.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            test_cfg["bucket_name"])
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successfully performed s3 ops using temp auth credentials "
            "for account %s", self.account_name)
        LOGGER.info(
            "ENDED: Verify using valid temp cred to perform s3 operations")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5608")
    @CTFailOn(error_handler)
    def test_2886(self):
        """ Verify using invalid temp credentials to perform s3 operations."""
        LOGGER.info(
            "STARTED: Verify using valid temp cred to perform s3 operations")
        test_cfg = IAM_CFG["test_9865"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        LOGGER.info(
            "Step 4: Perform s3 ops using invalid temp auth credentials for account %s",
            self.account_name)
        try:
            IAM_OBJ.s3_ops_using_temp_auth_creds(
                test_cfg["temp_access_key"], test_cfg["temp_secret_key"],
                test_cfg["temp_session_token"], test_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to perform s3 ops using invalid temp auth "
            "credentials for account %s", self.account_name)
        LOGGER.info(
            "Verify that by using invalid temporary credentials "
            "to perform s3 operations")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5631")
    @CTFailOn(error_handler)
    def test_2887(self):
        """Get temp cred for the acc which doesn't contain the acc login prof for that acc"""
        LOGGER.info(
            "STARTED: Get temp cred for the acc which doesn't contain"
            " the acc login prof for that acc")
        test_cfg = IAM_CFG["test_9866"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])
        LOGGER.info(
            "Step 2: Getting temp auth credentials for account %s",
            self.account_name)
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 2: failed to get temp auth credentials for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Get temp cred for the acc which doesn't contain"
            " the acc login prof for that acc")"

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5632")
    @CTFailOn(error_handler)
    def test_2888(self):
        """ Get temp cred for acc which contains acc login profile for that acc."""
        LOGGER.info(
            "STARTED: Get temp cred for acc which contains acc "
            "login profile for that acc.")
        test_cfg = IAM_CFG["test_9867"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        LOGGER.info(
            "ENDED: Get temp cred for acc which contains acc "
            "login profile for that acc.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5605")
    @CTFailOn(error_handler)
    def test_2889(self):
        """Verify time duration of 20 mins for Get temp cred for the valid acc"""
        LOGGER.info(
            "STARTED: Verify time duration of 20 mins for Get temp"
            " cred for the valid acc")
        test_cfg = IAM_CFG["test_9868"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        duration = test_cfg["duration"]
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account with %s "
            "sec duration %s", duration, self.account_name)
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"], duration)
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        LOGGER.info("Step 4: Performing s3 operations with temp credentials")
        res = IAM_OBJ.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            test_cfg["bucket_name"])
        assert_true(res[0], res[1])
        LOGGER.info("Step 4: Performing s3 operations with temp credentials")
        time.sleep(duration)
        LOGGER.info("Step 5: Performing s3 operations with same temp "
                    "credentials after %s sec", duration)
        try:
            IAM_OBJ.s3_ops_using_temp_auth_creds(
                temp_access_key,
                temp_secret_key,
                temp_session_token,
                test_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info("Step 5: Failed to perform s3 operations with same temp "
                    "credentials after %s sec", duration)
        LOGGER.info(
            "ENDED: Verify time duration of 20 mins for Get temp"
            " cred for the valid acc")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5606")
    @CTFailOn(error_handler)
    def test_2890(self):
        """Verify time duration less than 15 mins for Get temp cred for the valid acc"""
        LOGGER.info(
            "STARTED: Verify time duration less than 15 mins for Get temp"
            " cred for the valid acc")
        test_cfg = IAM_CFG["test_9869"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        duration = test_cfg["duration"]
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account with %s "
            "sec duration less than 20min %s", duration, self.account_name)
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["password"], duration)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s unsuccessful %s",
            self.account_name, res)
        LOGGER.info(
            "ENDED: Verify time duration less than 15 mins "
            "for Get temp cred for the valid acc")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5623")
    @CTFailOn(error_handler)
    def test_2891(self):
        """Give invalid acc login prof password for the get temp cred"""
        LOGGER.info(
            "STARTED: Give invalid account login profile password for"
            " the get temprary credentials")
        test_cfg = IAM_CFG["test_9870"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s with"
            " invalid password", self.account_name)
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["invalid_password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to get temp auth credentials for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Give invalid account login profile password for "
            "the get temporary credentials")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5638")
    @CTFailOn(error_handler)
    def test_2892(self):
        """Get temp auth cred for the existing user which is present in that acc."""
        LOGGER.info(
            "STARTED: Get temp auth credentials for the existing user which"
            " is present in that account")
        test_cfg = IAM_CFG["test_9871"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        user_name = test_cfg["user_name"]
        LOGGER.info("Step 3: Creating user with name %s", user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 3: Created user with name %s", user_name)
        LOGGER.info("Step 4: Creating user login profile for user %s",
                    user_name)
        res = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name,
            test_cfg["user_password"],
            password_reset=test_cfg["password_reset"],
            access_key=access_key,
            secret_key=secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 4: Created user login profile for user %s", user_name)
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing user %s",
            user_name)
        res = IAM_OBJ.get_temp_auth_credentials_user(
            self.account_name, user_name, test_cfg["user_password"])
        assert_is_not_none(res[1], res[1])
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing "
            "user %s is successful", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the existing user which"
            " is present in that account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5636")
    @CTFailOn(error_handler)
    def test_2893(self):
        """Get tempauth cred for the non-existing user which is not present in that acc."""
        LOGGER.info(
            "STARTED: Get tempauth credentials for the non-existing user which"
            " is not present in that account")
        test_cfg = IAM_CFG["test_9872"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        user_name = test_cfg["user_name"]
        LOGGER.info(
            "Step 3: Get temp auth credentials for non existing user %s",
            user_name)
        try:
            IAM_OBJ.get_temp_auth_credentials_user(
                self.account_name, user_name, test_cfg["user_password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to get temp auth credentials for "
            "non existing user %s", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the non-existing user "
            "which is not present in that account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5639")
    @CTFailOn(error_handler)
    def test_2894(self):
        """Get tempauth cred for the existing user which doesnt contain UserLoginProfile."""
        LOGGER.info(
            "STARTED: Get tempauth credentials for the existing user which "
            "doesnt contain UserLoginProfile")
        test_cfg = IAM_CFG["test_9873"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            password_reset=test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        user_name = test_cfg["user_name"]
        LOGGER.info("Step 3: Creating user with name %s", user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 3: Created user with name %s", user_name)
        LOGGER.info("Step 4: Creating user login profile for user %s",
                    user_name)
        res = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name,
            test_cfg["user_password"],
            password_reset=test_cfg["password_reset"],
            access_key=access_key,
            secret_key=secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 4: Created user login profile for user %s", user_name)
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing user %s which does"
            " not contain login profile", user_name)
        try:
            IAM_OBJ.get_temp_auth_credentials_user(
                self.account_name, user_name, test_cfg["user_password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 5: Failed to get temp auth credentials for existing user %s which does"
            " not contain login profile", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the existing user which "
            "doesnt contain UserLoginProfile")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5637")
    @CTFailOn(error_handler)
    def test_2895(self):
        """Get tempauth cred for existing user with time duration which is present in that acc."""
        LOGGER.info(
            "STARTED: Get tempauth credentials for the existing user with time"
            " duration which is present in that account")
        test_cfg = IAM_CFG["test_9874"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        LOGGER.info("Step 3: Creating user with name %s", user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 3: Created user with name %s", user_name)
        LOGGER.info("Step 4: Creating user login profile for user %s",
                    user_name)
        res = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name,
            test_cfg["user_password"],
            password_reset=test_cfg["password_reset"],
            access_key=access_key,
            secret_key=secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 4: Created user login profile for user %s", user_name)
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing user {} with time duration".format(user_name))
        res = IAM_OBJ.get_temp_auth_credentials_user(
            self.account_name,
            user_name,
            test_cfg["user_password"],
            test_cfg["duration"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 5: Successfully gets temp auth credentials for existing user "
            "%s with time duration", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the existing user with time "
            "duration which is present in that account")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-5635")
    @CTFailOn(error_handler)
    def test_2896(self):
        """
        Get tempauth credentials for the non-existing user with time duration
        which is not present in that account
        """
        LOGGER.info(
            "STARTED: Get tempauth credentials for the non-existing user"
            " with time duration which is not present in that account")
        test_cfg = IAM_CFG["test_9875"]
        LOGGER.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])
        user_name = test_cfg["user_name"]
        LOGGER.info(
            "Step 2: Get temp auth credentials for non existing user %s"
            " with time duration", user_name)
        try:
            IAM_OBJ.get_temp_auth_credentials_user(
                self.account_name, user_name, test_cfg["user_password"],
                test_cfg["duration"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in(test_cfg["err_msg"],
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to get temp auth credentials for non"
            " existing user %s", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the non-existing user with "
            " time duration which is not present in that account")
