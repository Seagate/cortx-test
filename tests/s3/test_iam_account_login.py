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
    assert_true, assert_in, assert_equal, assert_is_not_none

S3_OBJ = s3_test_lib.S3TestLib()
LOGGER = logging.getLogger(__name__)
TAG_OBJ = s3_tagging_test_lib.S3TaggingTestLib()

IAM_CFG = read_yaml("config/s3/test_iam_account_login.yaml")
IAM_OBJ = iam_test_lib.IamTestLib()


class TestAccountLoginProfile():
    """
    Account Login Profile Test Suite
    """

    @CTPLogformatter()
    def setup_method(self):
        self.log.info("STARTED: Setup and Teardown Operations")
        self.account_name = IAM_CFG["iam_account_login"]["acc_name_prefix"]
        self.email_id = "{}{}".format(
            self.account_name,
            IAM_CFG["iam_account_login"]["email_suffix"])
        self.ldap_user = LDAP_USERNAME
        self.ldap_pwd = LDAP_PASSWD
        self.log.info("Deleting account starts with: {}".format(
            self.account_name))
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        self.log.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        self.log.info(all_acc)
        for acc_name in all_acc:
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        self.log.info("ENDED: Setup and Teardown Operations")

    def teardown_method(self):
        """
        Function to perform the clean up for each test.
        """
        self.setUp()

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
        self.log.info("Step 1: Creating an account %s",acc_name)
        acc_res = IAM_OBJ.create_account_s3iamcli(acc_name, email,
                                                  ldap_user, ldap_pwd)
        self.assertTrue(acc_res[0], acc_res[1])
        self.log.info("Step 1: Account created %s", acc_res[1])
        self.log.info(
            "Step 2: Creating login profile for an account %s", acc_name)
        login_res = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, pwd, acc_res[1]["access_key"],
            acc_res[1]["secret_key"], pwd_reset)
        self.assertTrue(login_res[0], login_res[1])
        self.log.info(
            "Step 2: Created login profile for an account %s", acc_name)
        return acc_res, login_res

    @ctp_fail_on(error_handler)
    def test_2805(self):
        """Create account login profile for new account."""
        self.log.info("STARTED: Create account login profile for new account")
        test_cfg = IAM_CFG["test_9780"]
        self.log.info("Step 1: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertNotIn(
            self.account_name, str(
                list_account[1]), list_account[1])
        self.log.info("Step 1: listed account")
        self.log.info("Step 2: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 2: Account created %s", res[1])
        self.log.info(
            "Step 3: Creating login profile for an account %s",
                self.account_name)
        res = IAM_OBJ.create_account_login_profile_s3iamcli(
            self.account_name, test_cfg["password"], res[1]["access_key"],
            res[1]["secret_key"], test_cfg["password_reset"])
        self.assertTrue(res[0], res[1])
        self.assertIn(test_cfg["msg"], res[1], res[1])
        self.log.info("Step 3: Created login profile for an account %s "
                      "and details are %s", self.account_name, res[1])
        self.log.info("ENDED: Create account login profile for new account")

    def test_2806(self):
        """Create account login profile for nonexisting account."""
        self.log.info("ENDED: Create account login profile for nonexisting account")
        test_cfg = IAM_CFG["test_9782"]
        self.log.info("Step 1: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertNotIn(
            self.account_name, str(
                list_account[1]), list_account[1])
        self.log.info("Step 1: listed account")
        self.log.info(
            "Step 2: Creating login profile for a non existing account")
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                test_cfg["account"], test_cfg["password"],
                test_cfg["access_key"], test_cfg["secret_key"],
                test_cfg["password_reset"])
            self.log.info("after try")
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 2: failed to create login profile for a non existing account")
        self.log.info("ENDED: Create account login profile for nonexisting account")

    def test_2807(self):
        """Create account login profile for currently deleted account."""
        self.log.info(
            "STARTED: Create account login profile for currently deleted account")
        test_cfg = IAM_CFG["test_9783"]
        self.log.info("Step 1: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertNotIn(
            self.account_name, str(
                list_account[1]), list_account[1])
        self.log.info("Step 1: listed account")
        self.log.info("Step 2: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 2: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        self.log.info("Step 3: list and then delete recently created account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertIn(self.account_name, str(list_account[1]), list_account[1])
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 3: listed and Deleted recently created account")

        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertNotIn(self.account_name, list_account[1])

        self.log.info(
            "Step 4: Creating account login profile for recently deleted account")
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key,
                secret_key, test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
            self.assertIn(test_cfg["long_err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 4: Failed to create login profile for recently deleted account")
        self.log.info(
            "ENDED: Create account login profile for currently deleted account")

    def test_2808(self):
        """Create account login profile with password of 0 character."""
        self.log.info(
            "Create account login profile with password of 0 character")
        test_cfg = IAM_CFG["test_9784"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        self.log.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertIn(self.account_name, str(list_account[1]), list_account[1])
        self.log.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        self.log.info(
            "Step 3: Creating account login profile for account %s "
            "with password of 0 character", self.account_name)
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key,
                secret_key, test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info("Step 3: failed to create login profile for"
                      " an account %s", self.account_name)
        self.log.info(
            "ENDED: Create account login profile with password of 0 character")

    def test_2809(self):
        """Create account login profile with password of more than 128 characters."""
        self.log.info(
            "STARTED: Create account login profile with password of more than 128 characters.")
        test_cfg = IAM_CFG["test_9785"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        self.log.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertIn(self.account_name, str(list_account[1]), list_account[1])
        self.log.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        self.log.info(
            "Step 3: Creating login profile for an account %s "
            "with password more than 128 characters", self.account_name)
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key,
                secret_key, test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 3: Failed to create login profile for an account %s "
            "with password more than 128 characters", self.account_name)
        self.log.info(
            "ENDED: Create account login profile with password of more than 128 characters.")

    @ctp_fail_on(error_handler)
    def test_2810(self):
        """Create account login profile with password of possible combinations."""
        self.log.info(
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
                test_cfg["password_reset"],
                self.ldap_user,
                self.ldap_pwd)
            self.log.debug(res)
        self.log.info(
            "ENDED: Create account login profile with password of possible combinations")

    @ctp_fail_on(error_handler)
    def test_2811(self):
        """Create account login profile with password using invalid characters."""
        self.log.info(
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
                test_cfg["password_reset"],
                self.ldap_user,
                self.ldap_pwd)
            self.log.debug(res)
        self.log.info(
            "Create account login profile with password using invalid characters")

    @ctp_fail_on(error_handler)
    def test_2812(self):
        """Create account login profile with --no-password-reset-required option."""
        self.log.info(
            "Create account login profile with --no-password-reset-required option.")
        test_cfg = IAM_CFG["test_9788"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Create account login profile with --no-password-reset-required option.")

    @ctp_fail_on(error_handler)
    def test_2813(self):
        """Create account login profile with --password-reset-required option."""
        self.log.info(
            "Create account login profile with --password-reset-required option.")
        test_cfg = IAM_CFG["test_9789"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Create account login profile with --password-reset-required option.")

    @ctp_fail_on(error_handler)
    def test_2814(self):
        """
        Create account login profile without mentioning  --password-reset-required
        --no-password-reset-required
        """
        self.log.info(
            "Create account login profile without mentioning  "
            "--password-reset-required --no-password-reset-required")
        test_cfg = IAM_CFG["test_9790"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        self.log.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertIn(self.account_name, str(list_account[1]), list_account[1])
        self.log.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        self.log.info(
            "Step 3: Creating login profile for account %s without password reset options",
                self.account_name)
        res = IAM_OBJ.create_account_login_profile_without_both_reset_options(
            self.account_name, test_cfg["password"], access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Created login profile for account %s without password reset options",
            self.account_name)
        self.log.info(
            "ENDED: Create account login profile without mentioning  "
            "--password-reset-required --no-password-reset-required")

    @ctp_fail_on(error_handler)
    def test_2815(self):
        """
        Create account login profile with both options
         --no-password-reset-required --password-reset-required
        """
        self.log.info(
            "STARTED: Create account login profile with both options "
            "--no-password-reset-required --password-reset-required")
        test_cfg = IAM_CFG["test_9791"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        self.log.info("Step 2: List account")
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        self.assertIn(self.account_name, str(list_account[1]), list_account[1])
        self.log.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        self.log.info(
            "Step 3: Creating account login profile for account %s with"
            " both password reset value",self.account_name)
        res = IAM_OBJ.create_account_login_profile_both_reset_options(
            self.account_name, test_cfg["password"], access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Created account login profile for account %s with"
            " both password reset value",self.account_name)
        self.log.info(
            "ENDED: Create account login profile with both options "
            "--no-password-reset-required --password-reset-required")

    def test_2816(self):
        """Create account login profile with accesskey and sercret key of its user."""
        self.log.info(
            "STARTED: Create account login profile with accesskey "
            "and sercret key of its user")
        test_cfg = IAM_CFG["test_9792"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        self.log.info("Step 2: Creating user with name %s",user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.assertIsNotNone(res[1], res[1])
        self.log.info("Step 2: Created user with name %s",user_name)
        self.log.info(
            "Step 3: Creating access key and secret key for user %s",user_name)
        new_IAM_OBJ = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_IAM_OBJ.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        self.log.info(
            "Step 3: Created access key and secret key for user %s",user_name)
        self.log.info(
            "Step 4: Creating account login profile for account %s with keys of its user",
            self.account_name)
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                self.account_name,
                test_cfg["password"],
                user_access_key,
                user_secret_key,
                test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 4: Failed to create account login profile for "
            "account %s with keys of its user", self.account_name)
        self.log.info(
            "Step 5: Deleting access key of user %s", user_name)
        res = new_IAM_OBJ.delete_access_key(user_name, user_access_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Deleted access key of user %s",user_name)
        self.log.info(
            "ENDED: Create account login profile with accesskey"
            " and sercret key of its user")

    @ctp_fail_on(error_handler)
    def test_2829(self):
        """Get the account login details."""
        self.log.info("STARTED: Get the account login details")
        test_cfg = IAM_CFG["test_9807"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        self.log.info(
            "Step 3: Getting account login profile for account %s",
                self.account_name)
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Got account login profile for account %s",
                self.account_name)
        self.log.info("ENDED: Get the account login details")

    def test_2830(self):
        """Get the account login details for account not present."""
        self.log.info("STARTED: Get the account login details "
                      "for account not present")
        test_cfg = IAM_CFG["test_9808"]
        self.log.info(
            "Step 1: Getting account login profile for account not present")
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                test_cfg["account_name"], test_cfg["access_key"], test_cfg["secret_key"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 1: Failed to get account login profile for account not present")
        self.log.info("Get the account login details for account not present")

    def test_2831(self):
        """Get login details for acc which is present but login not created."""
        self.log.info(
            "Started: Get login details for acc which is present but login not created")
        test_cfg = IAM_CFG["test_9809"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        self.log.info(
            "Step 2: Getting account login profile for account {} for which login is not created".format(
                self.account_name))
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                self.account_name, access_key, secret_key)
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 2: Failed to get account login profile for account {} for which login is not created".format(
                self.account_name))
        self.log.info(
            "Ended: Get login details for acc which is present but login not created")

    def test_2832(self):
        """Get login details for account which is recently got deleted."""
        self.log.info(
            "STARTED: Get login details for account which is recently got deleted")
        test_cfg = IAM_CFG["test_9810"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        self.log.debug(res)
        self.log.info(
            "Step 3: Deleting account {} using s3iamcli".format(
                self.account_name))
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Deleted account {} using s3iamcli".format(
                self.account_name))
        self.log.info("Step 4: Get account login profile using s3iamcli")
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                self.account_name, access_key, secret_key)
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 4: Failed to get account login profile using s3iamcli")
        self.log.info(
            "ENDED: Get login details for account which is recently got deleted")

    def test_2833(self):
        """Get login profile with access key and secret key of its user."""
        self.log.info(
            "STARTED : Get login profile with access key and secret key of its user")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9811"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        self.log.info("Step 2: Creating user with name %s",user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.assertIsNotNone(res[1], res[1])
        self.log.info("Step 2: Created user with name %s",user_name)
        self.log.info(
            "Step 3: Creating access key and secret key for user %s",user_name)
        new_IAM_OBJ = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_IAM_OBJ.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        self.log.info(
            "Step 3: Created access key and secret key for user %s",user_name)
        self.log.info(
            "Step 4: Creating account login profile for account {} with keys of its user".format(
                self.account_name))
        IAM_OBJ.create_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["password"],
            access_key,
            secret_key,
            test_cfg["password_reset"])
        self.log.info(
            "Step 4: Created account login profile for account {} with keys of its user".format(
                self.account_name))
        self.log.info("Step 5: Get account login profile using s3iamcli")
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                self.account_name, user_access_key, user_secret_key)
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 5: Failed to get account login profile using s3iamcli")
        self.log.info(
            "Step 5: Deleting access key of user %s", user_name)
        res = new_IAM_OBJ.delete_access_key(user_name, user_access_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Deleted access key of user %s",user_name)
        self.log.info(
            "ENDED: Get login profile with access key and secret key of its user")

    @ctp_fail_on(error_handler)
    def test_2834(self):
        """Update account login profile with password only."""
        self.log.info(
            "STARTED: Update account login profile with password only")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9812"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        self.log.info(
            "Step 3: Getting account login profile for account {}".format(
                self.account_name))
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Getting account login profile for account {}".format(
                self.account_name))

        self.log.info(
            "Step 4: Updating account login profile for account {}".format(
                self.account_name))
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["new_password"], access_key, secret_key,
            test_cfg["password_reset"])
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account {}".format(
                self.account_name))
        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Successful to get account login profile using s3iamcli")
        self.log.info(
            "Deleting account {} using s3iamcli".format(
                self.account_name))
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info("ENDED: Update account login profile with password only")

    @ctp_fail_on(error_handler)
    def test_2835(self):
        """Update account login profile with --password-reset-required."""
        self.log.info(
            "STARTED: Update account login profile with --password-reset-required")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9813"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")
        self.log.info(
            "Step 4: Updating account login profile for account {}".format(
                self.account_name))
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["new_password"],
            access_key,
            secret_key,
            test_cfg["new_password_reset"])
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account {}".format(
                self.account_name))
        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 5: Get account login profile using s3iamcli")
        self.log.info(
            "Deleting account {} using s3iamcli".format(
                self.account_name))
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "ENDED: Update account login profile with --password-reset-required")

    @ctp_fail_on(error_handler)
    def test_2836(self):
        """Update account login profile with  --no-password-reset-required."""
        self.log.info(
            "STARTED: Update account login profile with  --no-password-reset-required")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9814"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")
        self.log.info(
            "Step 4: Updating account login profile for account {}".format(
                self.account_name))
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["new_password"],
            access_key,
            secret_key,
            test_cfg["new_password_reset"])
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account {}".format(
                self.account_name))
        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 5: Get account login profile using s3iamcli")
        self.log.info(
            "Deleting account {} using s3iamcli".format(
                self.account_name))
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "ENDED: Update account login profile with  --no-password-reset-required")

    @ctp_fail_on(error_handler)
    def test_2837(self):
        """
        Update account login profile with both --password-reset-required and
        --no-password-reset-required
        """
        self.log.info(
            "STARTED: Update account login profile with both --password-reset-required "
            "and --no-password-reset-required")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9815"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        self.log.info(
            "Step 4: Updating account login profile for account {}".format(
                self.account_name))
        resp = IAM_OBJ.update_account_login_profile_both_reset_options(
            self.account_name, test_cfg["password"], access_key, secret_key)
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account {}".format(
                self.account_name))
        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 5: Get account login profile using s3iamcli")
        self.log.info(
            "Deleting account {} using s3iamcli".format(
                self.account_name))
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "ENDED: Update account login profile with both --password-reset-required"
            "and --no-password-reset-required")

    @ctp_fail_on(error_handler)
    def test_2838(self):
        """Update account login profile with both password and reset flag."""
        self.log.info(
            "Update account login profile with both password and reset flag")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9816"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        self.log.info(
            "Step 4: Updating account login profile for account {}".format(
                self.account_name))
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["new_password"], access_key, secret_key,
            test_cfg["new_password_reset"])
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account {}".format(
                self.account_name))
        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Get account login profile using s3iamcli successful")
        self.log.info(
            "Update account login profile with both password and reset flag")

    def test_2839(self):
        """Update account login profile without password and without password reset flag."""
        self.log.info(
            "STARTED: Update account login profile without password and without "
            "password reset flag")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9817"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        self.log.info(
            "Step 4: Updating account login profile for account {} without password".format(
                self.account_name))
        try:
            IAM_OBJ.update_account_login_profile_both_reset_options(
                self.account_name, access_key, secret_key)
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 4: Failed to update login profile for account %s without password",
                self.account_name)
        self.log.info(
            "ENDED: Update account login profile with both password "
            "and reset flag")

    def test_2840(self):
        """Update login profile for account which didn't have the login profile created."""
        self.log.info(
            "STARTED: Update account login profile for the account which didn't have"
            "the login profile created")
        self.log.info("Creating an account %s with email %s", self.account_name, self.email_id))
        test_cfg=IAM_CFG["test_9818"]
        self.log.info("Step 1: Creating an account")
        res=IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        access_key=res[1]["access_key"]
        secret_key=res[1]["secret_key"]

        self.log.info(
            "Step 2: Updating account login profile for account %s",
                self.account_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                self.account_name, test_cfg["password"], access_key, secret_key,
                test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 2: Failed to update account login profile for account %s",
                self.account_name)
        self.log.info(
            "ENDED: Update account login profile for the account which didn't have"
            "the login profile created")

    def test_2841(self):
        """Update account login profile for the account which doesnt exist."""
        self.log.info(
            "STARTED: Update account login profile for the account which doesnt exist")
        self.log.info("Step 1: List account")
        test_cfg = IAM_CFG["test_9819"]
        list_account = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        acc_name = test_cfg["account_name"]
        self.assertNotIn(acc_name, str(list_account[1]), list_account[1])
        self.log.info("Step 1: listed account")

        self.log.info(
            "Step 2: Updating account login profile for account %s",
                acc_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                acc_name, test_cfg["password"], test_cfg["access_key"],
                test_cfg["secret_key"], test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s",error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 2: Failed to update login profile for account %s",
                acc_name)
        self.log.info(
            "ENDED: Update account login profile for the account which doesnt exist")

    def test_2842(self):
        """Update account login profile for the deleted account."""
        self.log.info(
            "STARTED: Update account login profile for the deleted account")
        self.log.info(
            "Creating an account %s with email %s:", self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9820"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info(
            "Step 3: Deleting account %s using s3iamcli", self.account_name)
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Deleted account %s using s3iamcli", account_name)
        self.log.info(
            "Step 4: Updating account login profile for account %s", account_name)
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                self.account_name,
                test_cfg["new_password"],
                access_key,
                secret_key,
                test_cfg["password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 4: Failed to update account login profile for account %s", self.account_name)
        self.log.info(
            "ENDED: Update account login profile for the deleted account")

    @ctp_fail_on(error_handler)
    def test_2843(self):
        """Update login profile for acc with new password as current password."""
        self.log.info(
            "STARTED: Update login profile for acc with new password as current password.")
        self.log.info(
            "Creating an account %s with email %s:", self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9821"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        self.log.info(
            "Step 4: Updating account login profile for account %s",
                self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["password"], access_key, secret_key,
            test_cfg["password_reset"])
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account %s",
                self.account_name)

        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Get account login profile using s3iamcli successful")
        self.log.info(
            "ENDED: Update login profile for acc with new password as current password.")

    @ctp_fail_on(error_handler)
    def test_2844(self):
        """
        Update the account login profiles password with the new password
        which contains invalid characters Verify if it accepts all invalid
        characters
        """
        self.log.info(
            "STARTED: Update the account login profiles password with the new password which"
            "contains invalid characters.Verify if it accepts all invalid characters")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9822"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        self.log.info("Step 3: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successful to get account login profile using s3iamcli")

        self.log.info(
            "Step 4: Updating account login profile for account %s",
                self.account_name)
        resp = IAM_OBJ.update_account_login_profile_s3iamcli(
            self.account_name, test_cfg["new_password"], access_key, secret_key,
            test_cfg["password_reset"])
        self.assertTrue(resp[0], resp[1])
        self.log.info(
            "Step 4: Updated account login profile for account %s",
                self.account_name)
        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.log.debug(res)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Get account login profile using s3iamcli successful")
        self.log.info(
            "ENDED: Update the account login profiles password with the new password which contains"
            "invalid characters.Verify if it accepts all invalid characters")

    def test_2845(self):
        """Update login profile with accesskey and sercret key of its user."""
        self.log.info(
            "STARTED: Update login profile with accesskey and sercret key of its user")
        self.log.info(
            "Creating an account %s with email %s:",
                self.account_name, self.email_id)
        test_cfg = IAM_CFG["test_9823"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])
        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        self.log.info("Step 2: Creating user with name %s",user_name)
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.assertIsNotNone(res[1], res[1])
        self.log.info("Step 2: Created user with name %s",user_name)
        self.log.info(
            "Step 3: Creating access key and secret key for user %s",user_name)
        new_IAM_OBJ = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_IAM_OBJ.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        self.log.info(
            "Step 3: Created access key and secret key for user %s",user_name)
        self.log.info(
            "Step 4: Creating account login profile for account {} with keys of its user".format(
                self.account_name))
        IAM_OBJ.create_account_login_profile_s3iamcli(
            self.account_name,
            test_cfg["password"],
            access_key,
            secret_key,
            test_cfg["password_reset"])

        self.log.info("Step 5: Get account login profile using s3iamcli")
        res = IAM_OBJ.get_account_login_profile_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Get account login profile using s3iamcli")
        self.log.info(
            "Updating account login profile for account {}".format(
                self.account_name))
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                self.account_name, test_cfg["new_password"], user_access_key,
                user_secret_key, test_cfg["new_password_reset"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info("Deleting user access key")
        res = new_IAM_OBJ.delete_access_key(user_name, user_access_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Update account login profile with accesskey and sercret key of its user")

    @ctp_fail_on(error_handler)
    def test_2882(self):
        """
        Get temporary credentials for Valid Account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info("Get temporary credentials for Valid Account")
        test_cfg = IAM_CFG["test_9861"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Step 3: Getting temp auth credentials for account {}".format(
                self.account_name))
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        self.assertIsNotNone(res[0], res[1])
        self.log.info(
            "Step 3: Get temp auth credentials for account {} successful {}".format(
                self.account_name, res))
        self.log.info("Get temporary credentials for Valid Account")

    def test_2883(self):
        """
        Get temporary credentials for Invalid Account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info("Get temporary credentials for Invalid Account")
        test_cfg = IAM_CFG["test_9862"]
        acc_name = test_cfg["account_name"]
        self.log.info(
            f"{acc_name} invalid account used to get temporary creds.")
        self.log.info(
            "Step 1: Getting temp auth credentials for invalid account")
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                acc_name, test_cfg["password"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 1: Failed to get temp auth credentials for invalid account")
        self.log.info("Get temporary credentials for Invalid Account")

    def test_2884(self):
        """
        Get the temporary Credentials for account which is recently got deleted
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get the temporary Credentials for account which is recently got deleted")
        test_cfg = IAM_CFG["test_9862"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        self.log.info("Step 2: Deleting recently created account")
        res = IAM_OBJ.delete_account_s3iamcli(
            self.account_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 2: Deleted recently created account")
        self.log.info(
            "Step 3: Getting temp auth credentials for account {} which is"
            "recently got deleted".format(self.account_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["password"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 3: Failed to get temp auth credentials for account {} which is recently got deleted".format(
                self.account_name))
        self.log.info(
            "Get the temporary Credentials for account which is recently got deleted")

    @ctp_fail_on(error_handler)
    def test_2885(self):
        """
        Verify that by using valid temporary credentials to perform s3 operations
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Verify that by using valid temporary credentials to perform s3 operations")
        test_cfg = IAM_CFG["test_9864"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Step 3: Getting temp auth credentials for account {}".format(
                self.account_name))
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        self.assertIsNotNone(res[0], res[1])
        self.log.info(
            "Step 3: Get temp auth credentials for account {} successful {}".format(
                self.account_name, res))
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        self.log.info(
            "Step 3: Perform s3 ops using temp auth credentials for account {}"
            "with creds as {}".format(self.account_name, res[1]))
        res = IAM_OBJ.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            test_cfg["bucket_name"])
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 3: Successfully performed s3 ops using temp auth credentials "
            "for account {}".format(
                self.account_name))
        self.log.info(
            "Verify that by using valid temporary credentials to perform s3 operations")

    def test_2886(self):
        """
        Verify that by using invalid temporary credentials to perform s3 operations
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Verify that by using invalid temporary credentials to perform s3 operations")
        test_cfg = IAM_CFG["test_9865"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Step 3: Getting temp auth credentials for account {}".format(
                self.account_name))
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        self.assertIsNotNone(res[0], res[1])
        self.log.info(
            "Step 3: Get temp auth credentials for account {} successful {}".format(
                self.account_name, res))
        self.log.info(
            "Step 4: Perform s3 ops using invalid temp auth credentials for account {}".format(
                self.account_name))
        try:
            IAM_OBJ.s3_ops_using_temp_auth_creds(
                test_cfg["temp_access_key"], test_cfg["temp_secret_key"],
                test_cfg["temp_session_token"], test_cfg["bucket_name"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 4: Failed to perform s3 ops using invalid temp auth credentials for account {}".format(
                self.account_name))
        self.log.info(
            "Verify that by using invalid temporary credentials to perform s3 operations")

    def test_2887(self):
        """
        Get temporary credentials for the account which doesn't contain the account login profile for that account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get temporary credentials for the account which doesn't contain the account login profile for that account")
        test_cfg = IAM_CFG["test_9866"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])
        self.log.info(
            "Step 2: Getting temp auth credentials for account {}".format(
                self.account_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["password"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 2: failed to get temp auth credentials for account {}".format(
                self.account_name))
        self.log.info(
            "Get temporary credentials for the account which doesn't contain the account login profile for that account")

    @ctp_fail_on(error_handler)
    def test_2888(self):
        """
        Get temporary credentials for the account which contain the account login profile for that account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get temporary credentials for the account which contain the account login profile for that account")
        test_cfg = IAM_CFG["test_9867"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Step 3: Getting temp auth credentials for account {}".format(
                self.account_name))
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"])
        self.assertIsNotNone(res[0], res[1])
        self.log.info(
            "Step 3: Get temp auth credentials for account {} successful {}".format(
                self.account_name, res))
        self.log.info(
            "Get temporary credentials for the account which contain the account login profile for that account")

    def test_2889(self):
        """
        Verify time duration of 20 mins for the Get temporary credentails for the valid account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Verify time duration of 20 mins for the Get temporary credentails for the valid account")
        test_cfg = IAM_CFG["test_9868"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        duration = test_cfg["duration"]
        self.log.info(
            "Step 3: Getting temp auth credentials for account with {} sec duration {}".format(
                duration, self.account_name))
        res = IAM_OBJ.get_temp_auth_credentials_account(
            self.account_name, test_cfg["password"], duration)
        self.assertIsNotNone(res[0], res[1])
        self.log.info(
            "Step 3: Get temp auth credentials for account {} successful {}".format(
                self.account_name, res))
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        self.log.info("Step 4: Performing s3 operations with temp credentials")
        res = IAM_OBJ.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            test_cfg["bucket_name"])
        self.assertTrue(res[0], res[1])
        self.log.info("Step 4: Performing s3 operations with temp credentials")
        time.sleep(duration)
        self.log.info("Step 5: Performing s3 operations with same temp "
                      "credentials after {} sec".format(duration))
        try:
            IAM_OBJ.s3_ops_using_temp_auth_creds(
                temp_access_key,
                temp_secret_key,
                temp_session_token,
                test_cfg["bucket_name"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info("Step 5: Failed to perform s3 operations with same temp "
                      "credentials after {} sec".format(duration))
        self.log.info(
            "Verify time duration of 20 mins for the Get temporary credentails for the valid account")

    def test_2890(self):
        """
        Verify time duration less than 15 mins for the Get temporary credentails for the valid account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Verify time duration less than 15 mins for the Get temporary credentails for the valid account")
        test_cfg = IAM_CFG["test_9869"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        duration = test_cfg["duration"]
        self.log.info(
            "Step 3: Getting temp auth credentials for account with {} sec duration less than 20min {}".format(
                duration, self.account_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["password"], duration)
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 3: Get temp auth credentials for account {} unsuccessful {}".format(
                self.account_name, res))
        self.log.info(
            "Verify time duration less than 15 mins for the Get temporary credentails for the valid account")

    def test_2891(self):
        """
        Give invalid account login profile password for the get temporary credentials
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Give invalid account login profile password for the get temprary credentials")
        test_cfg = IAM_CFG["test_9870"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        self.log.info(
            "Step 3: Getting temp auth credentials for account {} with invalid password".format(
                self.account_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_account(
                self.account_name, test_cfg["invalid_password"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 3: Failed to get temp auth credentials for account {}".format(
                self.account_name))
        self.log.info(
            "Give invalid account login profile password for the get temporary credentials")

    @ctp_fail_on(error_handler)
    def test_2892(self):
        """
        Get tempauth credentials for the existing user which is present in that account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get tempauth credentials for the existing user which is present in that account")
        test_cfg = IAM_CFG["test_9871"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        user_name = test_cfg["user_name"]
        self.log.info("Step 3: Creating user with name {}".format(user_name))
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.assertIsNotNone(res[1], res[1])
        self.log.info("Step 3: Created user with name {}".format(user_name))
        self.log.info(
            "Step 4: Creating user login profile for user {}".format(user_name))
        res = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name,
            test_cfg["user_password"],
            test_cfg["password_reset"],
            access_key,
            secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 4: Created user login profile for user {}".format(user_name))
        self.log.info(
            "Step 5: Get temp auth credentials for existing user {}".format(user_name))
        res = IAM_OBJ.get_temp_auth_credentials_user(
            self.account_name, user_name, test_cfg["user_password"])
        self.assertIsNotNone(res[1], res[1])
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 5: Get temp auth credentials for existing user {} is successful".format(user_name))
        self.log.info(
            "Get tempauth credentials for the existing user which is present in that account")

    def test_2893(self):
        """
        Get tempauth credentials for the non-existing user which is not present in that account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get tempauth credentials for the non-existing user which is not present in that account")
        test_cfg = IAM_CFG["test_9872"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        user_name = test_cfg["user_name"]
        self.log.info(
            "Step 3: Get temp auth credentials for non existing user {}".format(
                user_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_user(
                self.account_name, user_name, test_cfg["user_password"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 3: Failed to get temp auth credentials for non existing user {}".format(user_name))
        self.log.info(
            "Get tempauth credentials for the non-existing user which is not present in that account")

    def test_2894(self):
        """
        Get tempauth credentials for the existing user which doesnt contain UserLoginProfile
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get tempauth credentials for the existing user which doesnt contain UserLoginProfile")
        test_cfg = IAM_CFG["test_9873"]
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            test_cfg["password"],
            test_cfg["password_reset"],
            self.ldap_user,
            self.ldap_pwd)
        self.log.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        user_name = test_cfg["user_name"]
        self.log.info("Step 3: Creating user with name {}".format(user_name))
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.assertIsNotNone(res[1], res[1])
        self.log.info("Step 3: Created user with name {}".format(user_name))
        self.log.info(
            "Step 4: Creating user login profile for user {}".format(user_name))
        res = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name,
            test_cfg["user_password"],
            test_cfg["password_reset"],
            access_key,
            secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 4: Created user login profile for user {}".format(user_name))
        self.log.info(
            "Step 5: Get temp auth credentials for existing user {} which does"
            " not contain login profile".format(user_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_user(
                self.account_name, user_name, test_cfg["user_password"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 5: Failed to get temp auth credentials for existing user {} which does"
            " not contain login profile".format(user_name))
        self.log.info(
            "Get tempauth credentials for the existing user which doesnt contain UserLoginProfile")

    def test_2895(self):
        """
        Get tempauth credentials for the existing user with time duration which is present in that account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get tempauth credentials for the existing user with time duration which is present in that account")
        test_cfg = IAM_CFG["test_9874"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = test_cfg["user_name"]
        self.log.info("Step 3: Creating user with name {}".format(user_name))
        res = IAM_OBJ.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.assertIsNotNone(res[1], res[1])
        self.log.info("Step 3: Created user with name {}".format(user_name))
        self.log.info(
            "Step 4: Creating user login profile for user {}".format(user_name))
        res = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name, test_cfg["user_password"], test_cfg["password_reset"],
            access_key, secret_key)
        self.assertTrue(res[0], res[1])
        self.log.info(
            "Step 4: Created user login profile for user {}".format(user_name))
        self.log.info(
            "Step 5: Get temp auth credentials for existing user {} with time duration".format(user_name))
        res = IAM_OBJ.get_temp_auth_credentials_user(
            self.account_name,
            user_name,
            test_cfg["user_password"],
            test_cfg["duration"])
        self.assertIsNotNone(res[0], res[1])
        self.log.info(
            "Step 5: Successfully gets temp auth credentials for existing user "
            "{} with time duration".format(user_name))
        self.log.info(
            "Get tempauth credentials for the existing user with time duration which is present in that account")

    def test_2896(self):
        """
        Get tempauth credentials for the non-existing user with time duration
        which is not present in that account
        :avocado: tags=get_temp_auth_creds
        """
        self.log.info(
            "Get tempauth credentials for the non-existing user with time"
            " duration which is not present in that account")
        test_cfg = IAM_CFG["test_9875"]
        self.log.info("Step 1: Creating an account")
        res = IAM_OBJ.create_account_s3iamcli(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        self.assertTrue(res[0], res[1])
        self.log.info("Step 1: Account created %s",res[1])
        user_name = test_cfg["user_name"]
        self.log.info(
            "Step 2: Get temp auth credentials for non existing user {}"
            " with time duration".format(user_name))
        try:
            IAM_OBJ.get_temp_auth_credentials_user(
                self.account_name, user_name, test_cfg["user_password"],
                test_cfg["duration"])
        except CTException as error:
            self.log.error("Expected failure: %s", error.message)
            self.assertIn(test_cfg["err_msg"],
                          error.message, error.message)
        self.log.info(
            "Step 2: Failed to get temp auth credentials for non existing user {}".format(user_name))
        self.log.info(
            "Get tempauth credentials for the non-existing user with time duration"
            " which is not present in that account")
