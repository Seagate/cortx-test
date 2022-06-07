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

"""This file contains test for IAM account login"""

import time
import logging
import pytest
from libs.s3 import iam_test_lib
from libs.s3 import LDAP_USERNAME
from libs.s3 import LDAP_PASSWD
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.assert_utils import assert_true
from commons.utils.assert_utils import assert_in
from commons.utils.assert_utils import assert_is_not_none
from commons.utils.assert_utils import assert_not_in
from config.s3 import S3_USER_ACC_MGMT_CONFIG

LOGGER = logging.getLogger(__name__)

# pylint: disable-msg=too-many-public-methods
class TestAccountLoginProfile:
    """Account Login Profile Test Suite."""

    # pylint: disable=C0302
    def setup_method(self):
        """
        It will perform all the pre-reqs and is invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operation")
        self.iam_obj = iam_test_lib.IamTestLib()
        self.account_name = "iamAccount"
        self.email_suffix = "@seagate.com"
        self.email_id = "{}{}".format(self.account_name, self.email_suffix)
        self.ldap_user = LDAP_USERNAME
        self.ldap_pwd = LDAP_PASSWD
        self.test_cfg = S3_USER_ACC_MGMT_CONFIG["test_configs"]
        LOGGER.info("ENDED: Setup Operation")

    def teardown_method(self):
        """
        Function to perform the clean up for each test.
        """
        LOGGER.info("STARTED: Teardown Operations")
        LOGGER.info("Deleting account starts with: %s", self.account_name)
        acc_list = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)[1]
        LOGGER.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        LOGGER.info(all_acc)
        for acc_name in all_acc:
            self.iam_obj.reset_access_key_and_delete_account(acc_name)
        LOGGER.info("ENDED: Teardown Operations")

    def create_account_n_login_profile(
            self,
            acc_name,
            email,
            **kwargs
            ):
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
        pwd = kwargs.get("pwd")
        pwd_reset = kwargs.get("pwd_reset")
        ldap_user = kwargs.get("ldap_user")
        ldap_pwd = kwargs.get("ldap_pwd")
        LOGGER.info("Step 1: Creating an account %s", acc_name)
        acc_res = self.iam_obj.create_account(acc_name, email,
                                                  ldap_user, ldap_pwd)
        assert_true(acc_res[0], acc_res[1])
        LOGGER.info("Step 1: Account created %s", acc_res[1])
        LOGGER.info(
            "Step 2: Creating login profile for an account %s", acc_name)
        login_res = self.iam_obj.create_account_login_profile(
            acc_name, pwd, acc_res[1]["access_key"],
            acc_res[1]["secret_key"], password_reset=pwd_reset)
        assert_true(login_res[0], login_res[1])
        LOGGER.info(
            "Step 2: Created login profile for an account %s", acc_name)
        return acc_res, login_res

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5651")
    @CTFailOn(error_handler)
    def test_2805(self):
        """Create account login profile for new account."""
        LOGGER.info("STARTED: Create account login profile for new account")
        LOGGER.info("Step 1: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(
            self.account_name, str(
                list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")
        LOGGER.info("Step 2: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 2: Account created %s", res[1])
        LOGGER.info(
            "Step 3: Creating login profile for an account %s",
            self.account_name)
        res = self.iam_obj.create_account_login_profile(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            res[1]["access_key"], res[1]["secret_key"],
            password_reset=True)
        assert_true(res[0], res[1])
        assert_in("PasswordResetRequired = true", res[1], res[1])
        LOGGER.info("Step 3: Created login profile for an account %s "
                    "and details are %s", self.account_name, res[1])
        LOGGER.info("ENDED: Create account login profile for new account")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5650")
    @CTFailOn(error_handler)
    def test_2806(self):
        """Create account login profile for nonexisting account."""
        LOGGER.info(
            "ENDED: Create account login profile for nonexisting account")
        LOGGER.info("Step 1: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(
            self.account_name, str(
                list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")
        LOGGER.info(
            "Step 2: Creating login profile for a non existing account")
        try:
            self.iam_obj.create_account_login_profile(
                "dummy_account", S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                "dummy_access_key", "dummy_secret_key",
                password_reset=False)
            LOGGER.info("after try")
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("InvalidAccessKeyId",
                      error.message, error.message)
        LOGGER.info(
            "Step 2: failed to create login profile for a non existing account")
        LOGGER.info(
            "ENDED: Create account login profile for nonexisting account")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5652")
    @CTFailOn(error_handler)
    def test_2807(self):
        """Create account login profile for currently deleted account."""
        LOGGER.info(
            "STARTED: Create account login profile for currently deleted account")
        LOGGER.info("Step 1: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(
            self.account_name, str(
                list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")
        LOGGER.info("Step 2: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 2: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info("Step 3: list and then delete recently created account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("Step 3: listed and Deleted recently created account")

        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_not_in(self.account_name, list_account[1])

        LOGGER.info(
            "Step 4: Creating account login profile for recently deleted account")
        try:
            self.iam_obj.create_account_login_profile(
                self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                access_key, secret_key, password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("InvalidAccessKeyId",
                      error.message, error.message)
            assert_in("The AWS access key Id you provided does not exist in our records.",
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to create login profile for recently deleted account")
        LOGGER.info(
            "ENDED: Create account login profile for currently deleted account")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5645")
    @CTFailOn(error_handler)
    def test_2808(self):
        """Create account login profile with password of 0 character."""
        LOGGER.info(
            "Create account login profile with password of 0 character")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating account login profile for account %s "
            "with password of 0 character", self.account_name)
        try:
            self.iam_obj.create_account_login_profile(
                self.account_name, self.test_cfg["test_9784"]["password"],
                access_key, secret_key, password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("PasswordPolicyVoilation",
                      error.message, error.message)
        LOGGER.info("Step 3: failed to create login profile for"
                    " an account %s", self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile with password of 0 character")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5644")
    @CTFailOn(error_handler)
    def test_2809(self):
        """Create account login profile with password of more than 128 characters."""
        LOGGER.info(
            "STARTED: Create account login profile with password of more than 128 characters.")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating login profile for an account %s "
            "with password more than 128 characters", self.account_name)
        try:
            self.iam_obj.create_account_login_profile(
                self.account_name, self.test_cfg["test_9785"]["password"],
                access_key, secret_key, password_reset=False)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("PasswordPolicyVoilation",
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to create login profile for an account %s "
            "with password more than 128 characters", self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile with password of more than 128 characters.")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5643")
    @CTFailOn(error_handler)
    def test_2810(self):
        """Create account login profile with password of possible combinations."""
        LOGGER.info(
            "STARTED: Create login profile with password of possible combinations")
        for each_pwd in range(len(self.test_cfg["test_9786"]["list_of_passwords"])):
            acc_name = "{}{}".format(self.account_name, each_pwd)
            email = "{}{}".format(acc_name, self.email_suffix)
            res = self.create_account_n_login_profile(
                acc_name,
                email,
                pwd=self.test_cfg["test_9786"]["list_of_passwords"][each_pwd],
                pwd_reset=False,
                ldap_user=self.ldap_user,
                ldap_pwd=self.ldap_pwd)
            LOGGER.debug(res)
        LOGGER.info(
            "ENDED: Create account login profile with password of possible combinations")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5642")
    @CTFailOn(error_handler)
    def test_2811(self):
        """Create account login profile with password using invalid characters."""
        LOGGER.info(
            "Create account login profile with password using invalid characters")
        for each_pwd in range(len(self.test_cfg["test_9787"]["list_special_invalid_char"])):
            acc_name = "{}{}".format(self.account_name, each_pwd)
            email = "{}{}".format(
                acc_name, self.email_suffix)
            pwd = self.test_cfg["test_9787"]["list_special_invalid_char"][each_pwd]
            res = self.create_account_n_login_profile(
                acc_name,
                email,
                pwd=pwd,
                pwd_reset=False,
                ldap_user=self.ldap_user,
                ldap_pwd=self.ldap_pwd)
            LOGGER.debug(res)
        LOGGER.info(
            "Create account login profile with password using invalid characters")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5649")
    @CTFailOn(error_handler)
    def test_2812(self):
        """Create account login profile with --no-password-reset-required option."""
        LOGGER.info(
            "Create account login profile with --no-password-reset-required option.")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Create account login profile with --no-password-reset-required option.")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5648")
    @CTFailOn(error_handler)
    def test_2813(self):
        """Create account login profile with --password-reset-required option."""
        LOGGER.info(
            "Create account login profile with --password-reset-required option.")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Create account login profile with --password-reset-required option.")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating login profile for account %s without password reset options",
            self.account_name)
        res = self.iam_obj.create_account_login_profile_without_both_reset_options(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Created login profile for account %s without password reset options",
            self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile without mentioning  "
            "--password-reset-required --no-password-reset-required")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        LOGGER.info("Step 2: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        assert_in(self.account_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 2: listed account")

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 3: Creating account login profile for account %s with"
            " both password reset value", self.account_name)
        res = self.iam_obj.create_account_login_profile_both_reset_options(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Created account login profile for account %s with"
            " both password reset value", self.account_name)
        LOGGER.info(
            "ENDED: Create account login profile with both options "
            "--no-password-reset-required --password-reset-required")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5647")
    @CTFailOn(error_handler)
    def test_2816(self):
        """Create account login profile with accesskey and sercret key of its user."""
        LOGGER.info(
            "STARTED: Create account login profile with accesskey "
            "and sercret key of its user")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = "seagate_user"
        LOGGER.info("Step 2: Creating user with name %s", user_name)
        res = self.iam_obj.create_user(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 2: Created user with name %s", user_name)
        LOGGER.info(
            "Step 3: Creating access key and secret key for user %s",
            user_name)
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_iam_obj.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info(
            "Step 3: Created access key and secret key for user %s", user_name)
        LOGGER.info(
            "Step 4: Creating account login profile for account %s with keys of its user",
            self.account_name)
        try:
            self.iam_obj.create_account_login_profile(
                self.account_name,
                S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                user_access_key,
                user_secret_key,
                password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Failed to create Account login profile",
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to create account login profile for "
            "account %s with keys of its user", self.account_name)
        LOGGER.info(
            "Step 5: Deleting access key of user %s", user_name)
        res = new_iam_obj.delete_access_key(user_name, user_access_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Deleted access key of user %s", user_name)
        LOGGER.info(
            "ENDED: Create account login profile with accesskey"
            " and sercret key of its user")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5629")
    @CTFailOn(error_handler)
    def test_2829(self):
        """Get the account login details."""
        LOGGER.info("STARTED: Get the account login details")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        LOGGER.info(
            "Step 3: Getting account login profile for account %s",
            self.account_name)
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Got account login profile for account %s",
            self.account_name)
        LOGGER.info("ENDED: Get the account login details")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5628")
    @CTFailOn(error_handler)
    def test_2830(self):
        """Get the account login details for account not present."""
        LOGGER.info("STARTED: Get the account login details "
                    "for account not present")
        LOGGER.info(
            "Step 1: Getting account login profile for account not present")
        try:
            self.iam_obj.get_account_login_profile(
                "dummy_account", "dummy_access_key", "dummy_secret_key")
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Failed to get login profile",
                      error.message, error.message)
        LOGGER.info(
            "Step 1: Failed to get account login profile for account not present")
        LOGGER.info("Get the account login details for account not present")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5627")
    @CTFailOn(error_handler)
    def test_2831(self):
        """Get login details for acc which is present but login not created."""
        LOGGER.info(
            "STARTED: Get login details for acc which is present but"
            " login not created")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        LOGGER.info(
            "Step 2: Getting account login profile for account %s for which "
            "login is not created", self.account_name)
        try:
            self.iam_obj.get_account_login_profile(
                self.account_name, access_key, secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Failed to get login profile",
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to get account login profile for account %s for "
            "which login is not created", self.account_name)
        LOGGER.info(
            "Ended: Get login details for acc which is present but login not created")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5626")
    @CTFailOn(error_handler)
    def test_2832(self):
        """Get login details for account which is recently got deleted."""
        LOGGER.info(
            "STARTED: Get login details for account which is recently got deleted")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Deleting account %s", self.account_name)
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Deleted account %s", self.account_name)
        LOGGER.info("Step 4: Get .account login profile.")
        try:
            self.iam_obj.get_account_login_profile(
                self.account_name, access_key, secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Failed to get login profile",
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to get .account login profile.")
        LOGGER.info(
            "ENDED: Get login details for account which is recently got deleted")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5640")
    @CTFailOn(error_handler)
    def test_2833(self):
        """Get login profile with access key and secret key of its user."""
        LOGGER.info(
            "STARTED : Get login profile with access key and secret key of its user")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = "seagate_user"
        LOGGER.info("Step 2: Creating user with name %s", user_name)
        res = self.iam_obj.create_user(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 2: Created user with name %s", user_name)
        LOGGER.info(
            "Step 3: Creating access key and secret key for user %s",
            user_name)
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_iam_obj.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info(
            "Step 3: Created access key and secret key for user %s", user_name)
        LOGGER.info(
            "Step 4: Creating account login profile for account %s with keys "
            "of its user", self.account_name)
        self.iam_obj.create_account_login_profile(
            self.account_name,
            S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            access_key,
            secret_key,
            password_reset=True)
        LOGGER.info(
            "Step 4: Created account login profile for account %s with "
            "keys of its user", self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        try:
            self.iam_obj.get_account_login_profile(
                self.account_name, user_access_key, user_secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("User is not authorized to perform invoked action",
                      error.message, error.message)
        LOGGER.info(
            "Step 5: Failed to get .account login profile.")
        LOGGER.info(
            "Step 5: Deleting access key of user %s", user_name)
        res = new_iam_obj.delete_access_key(user_name, user_access_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Deleted access key of user %s", user_name)
        LOGGER.info(
            "ENDED: Get login profile with access key and secret key of its user")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5611")
    @CTFailOn(error_handler)
    def test_2834(self):
        """Update account login profile with password only."""
        LOGGER.info(
            "STARTED: Update account login profile with password only")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        LOGGER.info(
            "Step 3: Getting account login profile for account %s",
            self.account_name)
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Getting account login profile for account %s",
            self.account_name)

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile(
            self.account_name, self.test_cfg["test_9812"]["new_password"],
            access_key, secret_key,
            password_reset=True)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Successful to get .account login profile.")
        LOGGER.info(
            "Deleting account %s", self.account_name)
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("ENDED: Update account login profile with password only")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5614")
    @CTFailOn(error_handler)
    def test_2835(self):
        """Update account login profile with --password-reset-required."""
        LOGGER.info(
            "STARTED: Update account login profile with --password-reset-required")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")
        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile(
            self.account_name,
            self.test_cfg["test_9812"]["new_password"],
            access_key,
            secret_key,
            password_reset=True)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("Step 5: Get .account login profile.")
        LOGGER.info("Deleting account %s", self.account_name)
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with --password-reset-required")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5616")
    @CTFailOn(error_handler)
    def test_2836(self):
        """Update account login profile with  --no-password-reset-required."""
        LOGGER.info(
            "STARTED: Update account login profile with  --no-password-reset-required")
        LOGGER.info(
            "Creating an account %s with email %s:",
            self.account_name, self.email_id)
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")
        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile(
            self.account_name,
            self.test_cfg["test_9812"]["new_password"],
            access_key,
            secret_key,
            password_reset=False)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info("Step 5: Get .account login profile.")
        LOGGER.info(
            "Deleting account %s", self.account_name)
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with  "
            "--no-password-reset-required")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile_both_reset_options(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            access_key, secret_key)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info("Step 5: Get .account login profile.")
        LOGGER.info(
            "Deleting account %s", self.account_name)
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with both"
            " --password-reset-required and --no-password-reset-required")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile(
            self.account_name, self.test_cfg["test_9812"]["new_password"],
            access_key, secret_key, password_reset=True)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get .account login profile. successful")
        LOGGER.info(
            "ENDED: Update account login profile with both password "
            "and reset flag")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s without"
            " password", self.account_name)
        try:
            self.iam_obj.update_account_login_profile_both_reset_options(
                self.account_name, access_key, secret_key)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Please provide password or password-reset flag",
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to update login profile for account %s without password",
            self.account_name)
        LOGGER.info(
            "ENDED: Update account login profile with both password "
            "and reset flag")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]

        LOGGER.info(
            "Step 2: Updating account login profile for account %s",
            self.account_name)
        try:
            self.iam_obj.update_account_login_profile(
                self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                access_key, secret_key, password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (NoSuchEntity) : LoginProfile not created for account",
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to update account login profile for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Update account login profile for the account"
            " which didn't have the login profile created")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5621")
    @CTFailOn(error_handler)
    def test_2841(self):
        """Update account login profile for the account which doesnt exist."""
        LOGGER.info(
            "STARTED: Update account login profile for the account "
            "which doesnt exist")
        LOGGER.info("Step 1: List account")
        list_account = self.iam_obj.list_accounts(
            self.ldap_user, self.ldap_pwd)
        acc_name = "no_account"
        assert_not_in(acc_name, str(list_account[1]), list_account[1])
        LOGGER.info("Step 1: listed account")

        LOGGER.info(
            "Step 2: Updating account login profile for account %s",
            acc_name)
        try:
            self.iam_obj.update_account_login_profile(
                acc_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                "no_accesskey", "no_secretkey", password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Account login profile wasn't Updated.An error occurred"
                      " (InvalidLdapUserId) : The Ldap user id you provided "
                      "does not exist.",
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to update login profile for account %s",
            acc_name)
        LOGGER.info(
            "ENDED: Update account login profile for the account "
            "which doesnt exist")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info(
            "Step 3: Deleting account %s", self.account_name)
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Deleted account %s", self.account_name)
        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        try:
            self.iam_obj.update_account_login_profile(
                self.account_name,
                self.test_cfg["test_9820"]["new_password"],
                access_key,
                secret_key,
                password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("Account login profile wasn't Updated.An error occurred"
                      " (InvalidLdapUserId) : The Ldap user id you provided"
                      " does not exist.",
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to update account login profile for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Update account login profile for the deleted account")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            access_key, secret_key, password_reset=True)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)

        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get .account login profile. successful")
        LOGGER.info(
            "ENDED: Update login profile for acc with new password"
            " as current password.")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=True,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]

        LOGGER.info("Step 3: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successful to get .account login profile.")

        LOGGER.info(
            "Step 4: Updating account login profile for account %s",
            self.account_name)
        resp = self.iam_obj.update_account_login_profile(
            self.account_name, self.test_cfg["test_9822"]["new_password"],
            access_key, secret_key, password_reset=True)
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Updated account login profile for account %s",
            self.account_name)
        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        LOGGER.debug(res)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get .account login profile. successful")
        LOGGER.info(
            "ENDED: Update the account login profiles password with the new "
            "password which contains invalid characters.Verify if it accepts "
            "all invalid characters")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])
        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = "new_user99"
        LOGGER.info("Step 2: Creating user with name %s", user_name)
        res = self.iam_obj.create_user(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 2: Created user with name %s", user_name)
        LOGGER.info(
            "Step 3: Creating access key and secret key for user %s",
            user_name)
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        res = new_iam_obj.create_access_key(user_name)
        user_access_key = res[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = res[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info(
            "Step 3: Created access key and secret key for user %s", user_name)
        LOGGER.info(
            "Step 4: Creating account login profile for account %s with keys"
            " of its user", self.account_name)
        self.iam_obj.create_account_login_profile(
            self.account_name,
            S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            access_key,
            secret_key,
            password_reset=False)

        LOGGER.info("Step 5: Get .account login profile.")
        res = self.iam_obj.get_account_login_profile(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get .account login profile.")
        LOGGER.info(
            "Updating account login profile for account %s",
            self.account_name)
        try:
            self.iam_obj.update_account_login_profile(
                self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                user_access_key, user_secret_key, password_reset=True)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("User is not authorized to perform invoked action",
                      error.message, error.message)
        LOGGER.info("Deleting user access key")
        res = new_iam_obj.delete_access_key(user_name, user_access_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "ENDED: Update account login profile with access key and "
            "secret key of its user")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5630")
    @CTFailOn(error_handler)
    def test_2882(self):
        """Get temporary credentials for Valid Account."""
        LOGGER.info("STARTED: Get temporary credentials for Valid Account")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = self.iam_obj.get_temp_auth_credentials_account(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        LOGGER.info("ENDED: Get temporary credentials for Valid Account")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5634")
    @CTFailOn(error_handler)
    def test_2883(self):
        """Get temporary credentials for Invalid Account."""
        LOGGER.info("STARTED: Get temporary credentials for Invalid Account")
        acc_name = "dummy_account"
        LOGGER.info(
            "%s invalid account used to get temporary creds.", acc_name)
        LOGGER.info(
            "Step 1: Getting temp auth credentials for invalid account")
        try:
            self.iam_obj.get_temp_auth_credentials_account(
                acc_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (NoSuchEntity)",
                      error.message, error.message)
        LOGGER.info(
            "Step 1: Failed to get temp auth credentials for invalid account")
        LOGGER.info("ENDED: Get temporary credentials for Invalid Account")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5625")
    @CTFailOn(error_handler)
    def test_2884(self):
        """Get the temp Cred for acc which is recently got deleted."""
        LOGGER.info(
            "STARTED: Get the temp Cred for acc which is recently got deleted")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        LOGGER.info("Step 2: Deleting recently created account")
        res = self.iam_obj.delete_account(
            self.account_name, access_key, secret_key)
        assert_true(res[0], res[1])
        LOGGER.info("Step 2: Deleted recently created account")
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s which is"
            "recently got deleted", self.account_name)
        try:
            self.iam_obj.get_temp_auth_credentials_account(
                self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (NoSuchEntity)",
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to get temp auth credentials for account %s "
            "which is recently got deleted", self.account_name)
        LOGGER.info(
            "ENDED: Get the temp Cred for acc which is recently got deleted")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5658")
    @CTFailOn(error_handler)
    def test_2885(self):
        """Verify using valid temp cred to perform s3 operations."""
        LOGGER.info(
            "STARTED: Verify using valid temp cred to perform s3 operations")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = self.iam_obj.get_temp_auth_credentials_account(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"])
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
        res = self.iam_obj.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            "iamtestbucket")
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 3: Successfully performed s3 ops using temp auth credentials "
            "for account %s", self.account_name)
        LOGGER.info(
            "ENDED: Verify using valid temp cred to perform s3 operations")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5608")
    @CTFailOn(error_handler)
    def test_2886(self):
        """ Verify using invalid temp credentials to perform s3 operations."""
        LOGGER.info(
            "STARTED: Verify using valid temp cred to perform s3 operations")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = self.iam_obj.get_temp_auth_credentials_account(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        LOGGER.info(
            "Step 4: Perform s3 ops using invalid temp auth credentials for account %s",
            self.account_name)
        try:
            self.iam_obj.s3_ops_using_temp_auth_creds(
                "qeopioErUdjalkjfaowf", "AslkfjfjksjRsfjlskgUljflglsd",
                "2wslfaflk1aldjlakjfkljf67skhvskjdjiwfha", "iamtestbucket")
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("InvalidAccessKeyId",
                      error.message, error.message)
        LOGGER.info(
            "Step 4: Failed to perform s3 ops using invalid temp auth "
            "credentials for account %s", self.account_name)
        LOGGER.info(
            "Verify that by using invalid temporary credentials "
            "to perform s3 operations")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5631")
    @CTFailOn(error_handler)
    def test_2887(self):
        """Get temp cred for the acc which doesn't contain the acc login prof for that acc"""
        LOGGER.info(
            "STARTED: Get temp cred for the acc which doesn't contain"
            " the acc login prof for that acc")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])
        LOGGER.info(
            "Step 2: Getting temp auth credentials for account %s",
            self.account_name)
        try:
            self.iam_obj.get_temp_auth_credentials_account(
                self.account_name, self.test_cfg["test_9866"]["password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (InvalidCredentials)",
                      error.message, error.message)
        LOGGER.info(
            "Step 2: failed to get temp auth credentials for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Get temp cred for the acc which doesn't contain"
            " the acc login prof for that acc")

    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5632")
    @CTFailOn(error_handler)
    def test_2888(self):
        """ Get temp cred for acc which contains acc login profile for that acc."""
        LOGGER.info(
            "STARTED: Get temp cred for acc which contains acc "
            "login profile for that acc.")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s",
            self.account_name)
        res = self.iam_obj.get_temp_auth_credentials_account(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"])
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        LOGGER.info(
            "ENDED: Get temp cred for acc which contains acc "
            "login profile for that acc.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5605")
    @CTFailOn(error_handler)
    def test_2889(self):
        """Verify time duration of 20 mins for Get temp cred for the valid acc"""
        LOGGER.info(
            "STARTED: Verify time duration of 20 mins for Get temp"
            " cred for the valid acc")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        duration = 1200
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account with %s "
            "sec duration %s", duration, self.account_name)
        res = self.iam_obj.get_temp_auth_credentials_account(
            self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"], duration)
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s successful %s",
            self.account_name, res)
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        LOGGER.info("Step 4: Performing s3 operations with temp credentials")
        res = self.iam_obj.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            "iamtestbucket")
        assert_true(res[0], res[1])
        LOGGER.info("Step 4: Performing s3 operations with temp credentials")
        time.sleep(duration)
        LOGGER.info("Step 5: Performing s3 operations with same temp "
                    "credentials after %s sec", duration)
        try:
            self.iam_obj.s3_ops_using_temp_auth_creds(
                temp_access_key,
                temp_secret_key,
                temp_session_token,
                "iamtestbucket")
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("ExpiredToken",
                      error.message, error.message)
        LOGGER.info("Step 5: Failed to perform s3 operations with same temp "
                    "credentials after %s sec", duration)
        LOGGER.info(
            "ENDED: Verify time duration of 20 mins for Get temp"
            " cred for the valid acc")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5606")
    @CTFailOn(error_handler)
    def test_2890(self):
        """Verify time duration less than 15 mins for Get temp cred for the valid acc"""
        LOGGER.info(
            "STARTED: Verify time duration less than 15 mins for Get temp"
            " cred for the valid acc")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        duration = 800
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account with %s "
            "sec duration less than 20min %s", duration, self.account_name)
        try:
            self.iam_obj.get_temp_auth_credentials_account(
                self.account_name, S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
                duration)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (MinDurationIntervalNotMaintained)",
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Get temp auth credentials for account %s unsuccessful %s",
            self.account_name, res)
        LOGGER.info(
            "ENDED: Verify time duration less than 15 mins "
            "for Get temp cred for the valid acc")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5623")
    @CTFailOn(error_handler)
    def test_2891(self):
        """Give invalid acc login prof password for the get temp cred"""
        LOGGER.info(
            "STARTED: Give invalid account login profile password for"
            " the get temprary credentials")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        LOGGER.info(
            "Step 3: Getting temp auth credentials for account %s with"
            " invalid password", self.account_name)
        try:
            self.iam_obj.get_temp_auth_credentials_account(
                self.account_name, self.test_cfg["test_9870"][
                    "invalid_password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (InvalidCredentials)",
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to get temp auth credentials for account %s",
            self.account_name)
        LOGGER.info(
            "ENDED: Give invalid account login profile password for "
            "the get temporary credentials")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5638")
    @CTFailOn(error_handler)
    def test_2892(self):
        """Get temp auth cred for the existing user which is present in that acc."""
        LOGGER.info(
            "STARTED: Get temp auth credentials for the existing user which"
            " is present in that account")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        user_name = "seagate_user"
        LOGGER.info("Step 3: Creating user with name %s", user_name)
        res = self.iam_obj.create_user(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 3: Created user with name %s", user_name)
        LOGGER.info("Step 4: Creating user login profile for user %s",
                    user_name)
        res = self.iam_obj.create_user_login_profile(
            user_name,
            self.test_cfg["test_9871"]["user_password"],
            False,
            access_key=access_key,
            secret_key=secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 4: Created user login profile for user %s", user_name)
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing user %s",
            user_name)
        res = self.iam_obj.get_temp_auth_credentials_user(
            self.account_name, user_name,
            self.test_cfg["test_9871"]["user_password"])
        assert_is_not_none(res[1], res[1])
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing "
            "user %s is successful", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the existing user which"
            " is present in that account")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5636")
    @CTFailOn(error_handler)
    def test_2893(self):
        """Get tempauth cred for the non-existing user which is not present in that acc."""
        LOGGER.info(
            "STARTED: Get tempauth credentials for the non-existing user which"
            " is not present in that account")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        user_name = "seagate_user"
        LOGGER.info(
            "Step 3: Get temp auth credentials for non existing user %s",
            user_name)
        try:
            self.iam_obj.get_temp_auth_credentials_user(
                self.account_name, user_name,
                self.test_cfg["test_9871"]["user_password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (NoSuchEntity)",
                      error.message, error.message)
        LOGGER.info(
            "Step 3: Failed to get temp auth credentials for "
            "non existing user %s", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the non-existing user "
            "which is not present in that account")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5639")
    @CTFailOn(error_handler)
    def test_2894(self):
        """Get tempauth cred for the existing user which doesnt contain UserLoginProfile."""
        LOGGER.info(
            "STARTED: Get tempauth credentials for the existing user which "
            "doesnt contain UserLoginProfile")
        res = self.create_account_n_login_profile(
            self.account_name,
            self.email_id,
            pwd=S3_USER_ACC_MGMT_CONFIG["s3_params"]["password"],
            pwd_reset=False,
            ldap_user=self.ldap_user,
            ldap_pwd=self.ldap_pwd)
        LOGGER.debug(res)
        access_key = res[0][1]["access_key"]
        secret_key = res[0][1]["secret_key"]
        user_name = "seagate_user"
        LOGGER.info("Step 3: Creating user with name %s", user_name)
        res = self.iam_obj.create_user(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 3: Created user with name %s", user_name)
        LOGGER.info("Step 4: Creating user login profile for user %s",
                    user_name)
        res = self.iam_obj.create_user_login_profile(
            user_name,
            self.test_cfg["test_9871"]["user_password"],
            False,
            access_key=access_key,
            secret_key=secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 4: Created user login profile for user %s", user_name)
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing user %s which does"
            " not contain login profile", user_name)
        try:
            self.iam_obj.get_temp_auth_credentials_user(
                self.account_name, user_name,
                self.test_cfg["test_9871"]["user_password"])
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (InvalidCredentials)",
                      error.message, error.message)
        LOGGER.info(
            "Step 5: Failed to get temp auth credentials for existing user %s which does"
            " not contain login profile", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the existing user which "
            "doesnt contain UserLoginProfile")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
    @pytest.mark.tags("TEST-5637")
    @CTFailOn(error_handler)
    def test_2895(self):
        """Get tempauth cred for existing user with time duration which is present in that acc."""
        LOGGER.info(
            "STARTED: Get tempauth credentials for the existing user with time"
            " duration which is present in that account")
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])

        access_key = res[1]["access_key"]
        secret_key = res[1]["secret_key"]
        user_name = "seagate_user"
        LOGGER.info("Step 3: Creating user with name %s", user_name)
        res = self.iam_obj.create_user(
            user_name, access_key, secret_key)
        assert_true(res[0], res[1])
        assert_is_not_none(res[1], res[1])
        LOGGER.info("Step 3: Created user with name %s", user_name)
        LOGGER.info("Step 4: Creating user login profile for user %s",
                    user_name)
        res = self.iam_obj.create_user_login_profile(
            user_name,
            self.test_cfg["test_9871"]["user_password"],
            False,
            access_key=access_key,
            secret_key=secret_key)
        assert_true(res[0], res[1])
        LOGGER.info(
            "Step 4: Created user login profile for user %s", user_name)
        LOGGER.info(
            "Step 5: Get temp auth credentials for existing user %s with time duration", user_name)
        res = self.iam_obj.get_temp_auth_credentials_user(
            self.account_name,
            user_name,
            self.test_cfg["test_9871"]["user_password"],
            1200)
        assert_is_not_none(res[0], res[1])
        LOGGER.info(
            "Step 5: Successfully gets temp auth credentials for existing user "
            "%s with time duration", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the existing user with time "
            "duration which is present in that account")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_account
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
        LOGGER.info("Step 1: Creating an account")
        res = self.iam_obj.create_account(self.account_name, self.email_id,
                                              self.ldap_user, self.ldap_pwd)
        assert_true(res[0], res[1])
        LOGGER.info("Step 1: Account created %s", res[1])
        user_name = "dummy_user"
        LOGGER.info(
            "Step 2: Get temp auth credentials for non existing user %s"
            " with time duration", user_name)
        try:
            self.iam_obj.get_temp_auth_credentials_user(
                self.account_name, user_name,
                self.test_cfg["test_9875"]["user_password"], 1000)
        except CTException as error:
            LOGGER.error("Expected failure: %s", error.message)
            assert_in("An error occurred (NoSuchEntity)",
                      error.message, error.message)
        LOGGER.info(
            "Step 2: Failed to get temp auth credentials for non"
            " existing user %s", user_name)
        LOGGER.info(
            "ENDED: Get tempauth credentials for the non-existing user with "
            " time duration which is not present in that account")
