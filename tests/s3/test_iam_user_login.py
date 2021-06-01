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

"""IAM uesr login tests module"""

import time
import logging
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.assert_utils import assert_true, assert_in, assert_false
from config import S3_USER_ACC_MGMT_CONFIG, S3_CFG
from libs.s3 import iam_test_lib
from libs.s3 import S3H_OBJ
from libs.s3 import cortxcli_test_lib


class TestUserLoginProfileTests():
    """User Login Profile Test Suite."""

    @classmethod
    def setup_class(cls):
        """It will perform all prerequisite test suite steps if any."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup operations at suit level")
        cls.cli_obj_class = cortxcli_test_lib.CortxCliTestLib()
        cls.user_name_prefix = "iamuser"
        cls.acc_name_prefix = "iamaccount"
        cls.default_acc = "iamaccount{}".format(time.perf_counter_ns())
        cls.default_acc_mail = "{}@seagate.com".format(cls.default_acc)
        cls.default_acc_pass = S3_CFG["CliConfig"]["s3_account"]["password"]
        create_account = cls.cli_obj_class.create_account_cortxcli(
            account_name=cls.default_acc,
            account_email=cls.default_acc_mail,
            password=cls.default_acc_pass)
        assert create_account[0], create_account[1]
        cls.log.debug("Successfully created s3 account %s", create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        cls.iam_test_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        cls.log.info("ENDED: Setup operations at suit level")

    def setup_method(self):
        """Setup method."""
        self.log.info("STARTED: Setup operations")
        self.user_name = "{}{}".format(self.user_name_prefix, time.perf_counter_ns())
        self.account_name = "iamaccount{}".format(time.perf_counter_ns())
        self.email_id = "@seagate.com"
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.test_cfg = S3_USER_ACC_MGMT_CONFIG["test_configs"]
        self.cli_obj = cortxcli_test_lib.CortxCliTestLib()
        self.log.info("ENDED: Setup operations")

    @classmethod
    def teardown_class(cls):
        """Teardown method."""
        cls.log.info("STARTED: Teardown operations at suit level")
        all_users = cls.iam_test_obj.list_users()[1]
        iam_users_list = [user["UserName"]
                          for user in all_users if
                          cls.user_name_prefix in user["UserName"]]
        cls.log.debug("IAM users: %s", iam_users_list)
        if iam_users_list:
            cls.log.debug("Deleting IAM users...")
            for user in iam_users_list:
                res = cls.iam_test_obj.list_access_keys(user)
                if res[0]:
                    cls.log.debug("Deleting user access key...")
                    keys_meta = res[1]["AccessKeyMetadata"]
                    for key in keys_meta:
                        cls.iam_test_obj.delete_access_key(
                            user, key["AccessKeyId"])
                    cls.log.debug("Deleted user access key")
                cls.iam_test_obj.delete_user(user)
                cls.log.debug("Deleted user : %s", user)
        all_accounts = cls.cli_obj_class.list_accounts_cortxcli()
        iam_accounts = [acc["account_name"]
                        for acc in all_accounts if cls.acc_name_prefix in acc["account_name"]]
        cls.log.debug("IAM accounts: %s", iam_accounts)
        if iam_accounts:
            cls.log.debug("Deleting IAM accounts...")
            for acc in iam_accounts:
                cls.log.debug("Deleting %s account", acc)
                cls.cli_obj_class.login_cortx_cli(
                    username=acc, password=cls.default_acc_pass)
                cls.cli_obj_class.delete_all_buckets_cortx_cli()
                cls.cli_obj_class.delete_all_iam_users()
                cls.cli_obj_class.logout_cortx_cli()
                cls.cli_obj_class.delete_account_cortxcli(
                    account_name=acc, password=cls.default_acc_pass)
        cls.log.info("ENDED: Teardown operations at suit level")

    def create_user_and_access_key(
            self,
            user_name,
            password,
            pwd_reset=False):
        """
        This function will create a specified user and login profile for the same user.
        Also it will create an access key for the specified user.
        :param user_name: Name of user to be created
        :param password: User password to create login profile
        :param pwd_reset: Password reset option(True/False)
        :return: Tuple containing access and secret keys of user
        """
        self.log.info("Creating a user with name %s", user_name)
        resp = self.iam_test_obj.create_user(user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created a user with name %s", user_name)
        self.log.info("Creating login profile for user %s", user_name)
        resp = self.iam_test_obj.create_user_login_profile(
            user_name, password, pwd_reset)
        assert_true(resp[0], resp[1])
        self.log.info("Created login profile for user %s", user_name)
        self.log.info("Creating access key for user %s", user_name)
        resp = self.iam_test_obj.create_access_key(user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created access key for user %s", user_name)
        access_key = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        return access_key, secret_key

    def create_account_and_user(
            self,
            acc_name,
            email_id,
            user_name,
            user_password=None,
            pwd_reset=False,
            user_profile=False):
        """
        This function will create an account and user under that account.
        :param acc_name: Name of an account to be created.
        :param email_id: Email id for account creation
        :param user_name: Name of user to be created.
        :param user_password: User password
        :param pwd_reset: Password reset value
        :param user_profile: Creates user login profile if this is True
        :return: Tuple containing access and secret keys of an account
        """
        self.log.info("Creating account with name %s", acc_name)
        resp = self.cli_obj.create_account_cortxcli(
            acc_name, email_id, self.s3acc_passwd)
        assert_true(resp[0], resp[1])
        self.log.info("Created account with name %s", acc_name)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Creating a user with name %s", user_name)
        iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = iam_obj.create_user(user_name=user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created a user with name %s", user_name)
        if user_profile:
            self.log.info(
                "Creating user login profile for user %s", user_name)
            resp = iam_obj.create_user_login_profile(
                user_name, user_password, pwd_reset)
            assert_true(resp[0], resp[1])
            self.log.info(
                "Created user login profile for user %s", user_name)
        return access_key, secret_key

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-5664")
    @CTFailOn(error_handler)
    def test_2846(self):
        """Verify update-login-profile (password change) for IAM user."""
        self.log.info(
            "STARTED:Verify update-login-profile (password change) for IAM user")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9824"]["password"],
            True)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.update_user_login_profile(
            self.user_name, self.test_cfg["test_9824"]["password"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED:Verify update-login-profile (password change) for IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5665")
    @CTFailOn(error_handler)
    def test_2847(self):
        """Verify update-login-profile (password change) for a non-existing IAM user."""
        self.log.info("STARTED: Verify update-login-profile (password change)"
                      " for a non-existing IAM user")
        try:
            self.iam_test_obj.update_user_login_profile(
                self.user_name, self.test_cfg["test_9825"]["password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info("ENDED: Verify update-login-profile (password change)"
                      " for a non-existing IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5663")
    @CTFailOn(error_handler)
    def test_2848(self):
        """Verify update-login-profile (passwd change) for IAM user with 'Blank' or 'NO' passwd."""
        self.log.info("STARTED: Verify update-login-profile (password change)"
                      " for IAM user with 'Blank' or 'NO' password")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9826"]["password"],
            True)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.update_user_login_profile(
                self.user_name, self.test_cfg["test_9826"]["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "Parameter validation failed:\nInvalid length for parameter Password",
                error.message,
                error.message)
        self.log.info("ENDED: Verify update-login-profile (password change)"
                      " for IAM user with 'Blank' or 'NO' password")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5681")
    @CTFailOn(error_handler)
    def test_2850(self):
        """Provide password length 128 valid characters long. """
        self.log.info("STARTED: Provide password length 128 valid "
                      "characters long")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9828"]["password"],
            True)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.update_user_login_profile(
            self.user_name, self.test_cfg["test_9828"]["new_password"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Provide password length 128 valid"
                      " characters long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5680")
    @CTFailOn(error_handler)
    def test_2851(self):
        """Provide password length more than128 valid characters long."""
        self.log.info("STARTED: Provide password length more than128"
                      " valid characters long")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9829"]["password"],
            True)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.update_user_login_profile(
                self.user_name, self.test_cfg["test_9829"]["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "PasswordPolicyVoilation",
                error.message,
                error.message)
        self.log.info("ENDED: Provide password length more than128 valid "
                      "characters long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5704")
    @CTFailOn(error_handler)
    def test_2852(self):
        """Change the password for IAM user with --password-reset-required option."""
        self.log.info("STARTED: Change the password for IAM user with "
                      "--password-reset-required option")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9830"]["password"],
            False)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.update_user_login_profile(
            self.user_name,
            self.test_cfg["test_9830"]["new_password"],
            True)
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Change the password for IAM user with "
                      "--password-reset-required option")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5678")
    @CTFailOn(error_handler)
    def test_2853(self):
        """Update login profile for IAM user which does not have the login profile created."""
        self.log.info("STARTED: Update login profile for IAM user which does"
                      " not have the login profile created")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.update_user_login_profile(
                self.user_name, self.test_cfg["test_9831"]["password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info("ENDED: Update login profile for IAM user which does "
                      " not have the login profile created")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5662")
    @CTFailOn(error_handler)
    def test_2854(self):
        """verify update-login-profile with password having
        combinations of special characters  _+=,.@- ."""
        self.log.info(
            "STARTED: verify update-login-profile with password having"
            " combinations of special characters  _+=,.@-")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            False)
        assert_true(resp[0], resp[1])
        for password in self.test_cfg["test_9832"]["special_char_pwd"]:
            resp = self.iam_test_obj.update_user_login_profile(
                self.user_name, password)
            assert_true(resp[0], resp[1])
        self.log.info("ENDED: verify update-login-profile with password having"
                      " combinations of special characters  _+=,.@-")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5676")
    @CTFailOn(error_handler)
    def test_2855(self):
        """Update login profile for IAM user without mentioning
        --password-reset-required --no-password-reset-required."""
        self.log.info("STARTED: Update login profile for IAM user without"
                      " mentioning  --password-reset-required "
                      "--no-password-reset-required")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9833"]["password"],
            True)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.update_user_login_profile_no_pwd_reset(
            self.user_name, self.test_cfg["test_9833"]["new_password"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Update login profile for IAM user without "
                      "mentioning--password-reset-required "
                      "--no-password-reset-required")

    # Both --password-reset-required and --no-password-reset-required cannot be provided
    # using boto3, hence skipping the test.
    @pytest.mark.skip
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5677")
    @CTFailOn(error_handler)
    def test_2856(self):
        """update login profile for IAM user with both options
         --no-password-reset-required --password-reset-required."""
        self.log.info("STARTED: update login profile for IAM user with both"
                      " options --no-password-reset-required "
                      "--password-reset-required")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name, self.test_cfg["test_9834"]["password"])
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.update_user_login_profile_s3iamcli_with_both_reset_options(
            self.user_name,
            self.test_cfg["test_9834"]["password"],
            S3H_OBJ.get_local_keys()[0],
            S3H_OBJ.get_local_keys()[1])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: update login profile for IAM user with both"
                      " options --no-password-reset-required "
                      "--password-reset-required")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5675")
    @CTFailOn(error_handler)
    def test_2857(self):
        """Update login profile for IAM user without password and reset flag enabled."""
        self.log.info("STARTED: Update login profile for IAM user without "
                      "password and reset flag enabled")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            True)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.update_user_login_profile_no_pwd_reset(
                self.user_name)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "Parameter validation failed:\nInvalid type for parameter Password",
                error.message,
                error.message)
        self.log.info("STARTED: Update login profile for IAM user without "
                      "password and reset flag enabled")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-5703")
    @CTFailOn(error_handler)
    def test_2858(self):
        """Create a login profile for the existing IAM user."""
        self.log.info(
            "STARTED: Create a login profile for the existing IAM user")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            True)
        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Create a login profile for the existing IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5702")
    @CTFailOn(error_handler)
    def test_2859(self):
        """Create a login profile for the non-existing IAM user."""
        self.log.info(
            "STARTED: Create a login profile for the non-existing IAM user")
        try:
            self.iam_test_obj.create_user_login_profile(
                self.user_name,
                self.test_cfg["test_9832"]["password"],
                True)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info(
            "ENDED: Create a login profile for the non-existing IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5697")
    @CTFailOn(error_handler)
    def test_2860(self):
        """Create a login profile with password of 0 character or
        without password for existing user"""
        self.log.info("STARTED: Create a login profile with password of 0 "
                      "character or without password for existing user")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.create_user_login_profile(
                self.user_name,
                self.test_cfg["test_9826"]["new_password"],
                True)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "Parameter validation failed:\nInvalid length for parameter Password",
                error.message,
                error.message)
        self.log.info("ENDED: Create a login profile with password of 0 "
                      "character or without password for existing user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5695")
    @CTFailOn(error_handler)
    def test_2862(self):
        """Create a login profile with password of 128 characters for existing user"""
        self.log.info("STARTED: Create a login profile with password of 128"
                      " characters for existing user")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9840"]["password"],
            True)
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create a login profile with password of 128"
                      " characters for existing user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5693")
    @CTFailOn(error_handler)
    def test_2863(self):
        """Create a login profile with password of more than 128 characters for existing user."""
        self.log.info("STARTED: Create a login profile with password of more "
                      "than 128 characters for existing user")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.create_user_login_profile(
                self.user_name,
                self.test_cfg["test_9841"]["password"],
                True)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "PasswordPolicyVoilation",
                error.message,
                error.message)
        self.log.info("ENDED: Create a login profile with password of more "
                      "than 128 characters for existing user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5699")
    @CTFailOn(error_handler)
    def test_2864(self):
        """Create a login profile with password having special characters only."""
        self.log.info("STARTED: Create a login profile with password having"
                      " special characters only")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9842"]["password"],
            True)
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create a login profile with password having"
                      " special characters only")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5701")
    @CTFailOn(error_handler)
    def test_2865(self):
        """Create a login profile with password - try few combinations of
        special characters and alphanumberic characters."""
        self.log.info("STARTED: Create a login profile with password - try few"
                      " combinations of special characters and alphanumberic "
                      "characters")
        for password in self.test_cfg["test_9843"]["special_char_pwd"]:
            resp = self.iam_test_obj.create_user(self.user_name)
            assert_true(resp[0], resp[1])
            self.log.debug(
                "Creating user login profile with password: %s", password)
            resp = self.iam_test_obj.create_user_login_profile(
                self.user_name, password, True)
            assert_true(resp[0], resp[1])
            resp = self.iam_test_obj.delete_user(self.user_name)
            assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create a login profile with password - try few"
                      " combinations of special characters and alphanumberic"
                      " characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5688")
    @CTFailOn(error_handler)
    def test_2866(self):
        """Create login profiles for maximum nos of existing IAM users."""
        self.log.info("STARTED: Create login profiles for maximum nos of "
                      "existing IAM users")
        self.log.debug("Creating 101 users")
        for cnt in range(101):
            new_user_name = "{0}{1}".format(
                self.user_name,
                "_{}".format(cnt))
            self.log.debug("Creating a user with name: %s", new_user_name)
            resp = self.iam_test_obj.create_user(new_user_name)
            assert_true(resp[0], resp[1])
            resp = self.iam_test_obj.create_user_login_profile(
                new_user_name, self.test_cfg["test_9832"]["password"], True)
            assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create login profiles for maximum nos of "
                      "existing IAM users")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5692")
    @CTFailOn(error_handler)
    def test_2867(self):
        """Create login profile for IAM user with --no-password-reset-required option."""
        self.log.info("STARTED: Create login profile for IAM user with "
                      "--no-password-reset-required option")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            False)
        assert_true(resp[0], resp[1])
        assert_false(resp[1]["password_reset_required"], resp[1])
        self.log.info("ENDED: Create login profile for IAM user with "
                      "--no-password-reset-required option")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5691")
    @CTFailOn(error_handler)
    def test_2868(self):
        """Create login profile for IAM user with --password-reset-required option."""
        self.log.info(
            "STARTED: Create login profile for IAM user with "
            "--password-reset-required option")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            True)
        assert_true(resp[0], resp[1])
        assert_true(resp[1]["password_reset_required"], resp[1])
        self.log.info(
            "ENDED: Create login profile for IAM user with "
            "--password-reset-required option")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5689")
    @CTFailOn(error_handler)
    def test_2869(self):
        """Create login profile for IAM user without mentioning
        --password-reset-required --no-password-reset-required."""
        self.log.info(
            "STARTED: Create login profile for IAM user without mentioning  "
            "--password-reset-required --no-password-reset-required .")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"]
        )
        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Create login profile for IAM user without mentioning  "
            "--password-reset-required --no-password-reset-required .")

    # Both --password-reset-required and --no-password-reset-required cannot be provided
    # using boto3, hence skipping the test.
    @pytest.mark.skip
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5690")
    @CTFailOn(error_handler)
    def test_2870(self):
        """Create login profile for IAM user with both options
        --no-password-reset-required --password-reset-required."""
        self.log.info(
            "STARTED: Create login profile for IAM user with both options "
            "--no-password-reset-required --password-reset-required .")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile_s3iamcli_with_both_reset_options(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            S3H_OBJ.get_local_keys()[0],
            S3H_OBJ.get_local_keys()[1],
            both_reset_options=True)
        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Create login profile for IAM user with both options "
            "--no-password-reset-required --password-reset-required .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5670")
    @CTFailOn(error_handler)
    def test_2871(self):
        """Verify get-login-profile for s3 IAM user."""
        self.log.info("STARTED: Verify get-login-profile for s3 IAM user")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.create_user_login_profile(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            True)
        assert_true(resp[0], resp[1])
        resp = self.iam_test_obj.get_user_login_profile(self.user_name)
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Verify get-login-profile for s3 IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5671")
    @CTFailOn(error_handler)
    def test_2872(self):
        """Verify get-login-profile for non-existing s3 IAM user."""
        self.log.info(
            "STARTED: Verify get-login-profile for non-existing s3 IAM user")
        try:
            self.iam_test_obj.get_user_login_profile(self.user_name)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info(
            "ENDED: Verify get-login-profile for non-existing s3 IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5672")
    @CTFailOn(error_handler)
    def test_2873(self):
        """Verify get-login-profile for a non profile IAM user
         (IAM user with no profile created)."""
        self.log.info(
            "STARTED: Verify get-login-profile for a non profile "
            "IAM user (IAM user with no profile created)")
        resp = self.iam_test_obj.create_user(self.user_name)
        assert_true(resp[0], resp[1])
        try:
            self.iam_test_obj.get_user_login_profile(self.user_name)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info(
            "ENDED: Verify get-login-profile for a non profile IAM user "
            "(IAM user with no profile created)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-5668")
    @CTFailOn(error_handler)
    def test_2897(self):
        """Verify password change for IAM user."""
        self.log.info("STARTED: Verify password change for IAM user")
        email_id = "{0}{1}".format(
            self.account_name, self.email_id)
        resp = self.cli_obj.create_account_cortxcli(self.account_name,
                                                    email_id,
                                                    self.s3acc_passwd)
        assert_true(resp[0], resp[1])
        login = self.cli_obj.login_cortx_cli(
            username=self.account_name,
            password=self.s3acc_passwd)
        assert_true(login[0], login[1])
        resp = self.cli_obj.create_user_cortxcli(self.user_name,
                                                 self.test_cfg["test_9832"]["password"])
        assert_true(resp[0], resp[1])
        resp = self.cli_obj.reset_iamuser_password_cortxcli(
            self.user_name, self.test_cfg["test_9876"]["new_password"])
        assert_true(resp[0], resp[1])
        self.cli_obj.logout_cortx_cli()
        self.log.info("ENDED: Verify password change for IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5669")
    @CTFailOn(error_handler)
    def test_2898(self):
        """Verify password change for a non-existing IAM user."""
        self.log.info("STARTED: Verify password change for a "
                      "non-existing IAM user")
        self.log.info("Change user password for a non-existing IAM user")
        try:
            login = self.cli_obj.login_cortx_cli(
                username=self.default_acc, password=self.default_acc_pass)
            assert_true(login[0], login[1])
            self.cli_obj.reset_iamuser_password(
                self.user_name, self.test_cfg["test_9876"]["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "The request was rejected because it referenced a user that does not exist",
                error.message,
                error.message)
        finally:
            self.cli_obj.logout_cortx_cli()
        self.log.info("ENDED: Verify password change for a "
                      "non-existing IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5682")
    @CTFailOn(error_handler)
    def test_2899(self):
        """Provide only six character length in password."""
        self.log.info("STARTED: Provide only six character length in password")
        email_id = "{0}{1}".format(
            self.account_name, self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9832"]["password"])
        try:
            login = self.cli_obj.login_cortx_cli(
                username=self.account_name, password=self.s3acc_passwd)
            assert_true(login[0], login[1])
            self.cli_obj.reset_iamuser_password(
                self.user_name, self.test_cfg["test_2899"]["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "Password Policy Not Met",
                error.message,
                error.message)
        finally:
            self.cli_obj.logout_cortx_cli()
        self.log.info("ENDED: Provide only six character length in password")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5683")
    @CTFailOn(error_handler)
    def test_2849(self):
        """Provide only one character length in password."""
        self.log.info("STARTED: Provide only one character length in password")
        email_id = "{0}{1}".format(
            self.account_name, self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9832"]["password"])
        try:
            login = self.cli_obj.login_cortx_cli(
                username=self.account_name, password=self.s3acc_passwd)
            assert_true(login[0], login[1])
            self.cli_obj.reset_iamuser_password(
                self.user_name, self.test_cfg["test_9879"]["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "Password Policy Not Met",
                error.message,
                error.message)
        finally:
            self.cli_obj.logout_cortx_cli()
        self.log.info("ENDED: Provide only one character length in password")

    #  #Duplicate of test_2850
    # def test_9880(self):
    #     """
    #     Provide password length 128 valid characters long
    #
    #     """
    #     self.log.info("Provide password length 128 valid characters long")
    #     resp = self.create_user_and_access_key(
    #         self.user_name,
    #         self.test_cfg["test_9832"]["password"])
    #     user_access_key = resp[0]
    #     user_secret_key = resp[1]
    #     resp = self.iam_test_obj.change_user_password(
    #         self.test_cfg["test_9832"]["password"],
    #         self.test_cfg["test_9840"]["new_password"],
    #         user_access_key,
    #         user_secret_key)
    #     assert_true(resp[0], resp[1])
    #     self.log.info("Provide password length 128 valid characters long")

    # def test_2851(self): # Duplicate
    #     """
    #     Provide password length more than 128 valid characters long
    #
    #     """
    #     self.log.info(
    #         "Provide password length more than 128 valid characters long")
    #     test_9881_cfg = USER_CONFIG["test_9881"]
    #     resp = self.create_user_and_access_key(
    #         self.user_name,
    #         self.test_cfg["test_9832"]["password"])
    #     user_access_key = resp[0]
    #     user_secret_key = resp[1]
    #     try:
    #         self.iam_test_obj.change_user_password(
    #             self.test_cfg["test_9832"]["password"],
    #             self.test_cfg["test_9841"]["new_password"],
    #             user_access_key,
    #             user_secret_key)
    #     except CTException as error:
    #         self.log.debug(error.message)
    #         assert_in(
    #             "InvalidParameterValue",
    #             error.message,
    #             error.message)
    #     self.log.info(
    #         "Provide password length more than128 valid characters long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5661")
    @CTFailOn(error_handler)
    def test_2903(self):
        """
        verify with valid strings as passwordNote:Allowed special characters are
        ~, !, @, #, $, %, ^, *, (, ),-, _, +, =, \\, /, ?, .., \n, \t, \rFor special
        characters &, <, > and | , if user want to use these then
        password should be added in quote.
        """
        self.log.info("STARTED: Password with allowed special "
                      "characters ~,$,?,&,\\n,\\t,<,>")
        email_id = "{0}{1}".format(
            self.account_name, self.email_id)
        resp = self.cli_obj.create_account_cortxcli(self.account_name,
                                                    email_id,
                                                    self.s3acc_passwd)
        assert_true(resp[0], resp[1])
        login = self.cli_obj.login_cortx_cli(
            username=self.account_name,
            password=self.s3acc_passwd)
        assert_true(login[0], login[1])
        resp = self.cli_obj.create_user_cortxcli(self.user_name,
                                                 self.test_cfg["test_9832"]["password"])
        assert_true(resp[0], resp[1])
        for new_password in self.test_cfg["test_9882"]["list_special_char_pwd"]:
            self.log.debug(new_password)
            resp = self.cli_obj.reset_iamuser_password_cortxcli(
                self.user_name, new_password)
            assert_true(resp[0], resp[1])
        self.cli_obj.logout_cortx_cli()
        self.log.info("ENDED: Password with allowed special "
                      "characters ~,$,?,&,\\n,\\t,<,>")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5673")
    @CTFailOn(error_handler)
    def test_2904(self):
        """Verify change password with old password."""
        self.log.info("STARTED: Verify change password with old password")
        email_id = "{0}{1}".format(
            self.account_name, self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9832"]["password"])
        login = self.cli_obj.login_cortx_cli(
            username=self.account_name,
            password=self.s3acc_passwd)
        assert_true(login[0], login[1])
        try:
            self.cli_obj.reset_iamuser_password(
                self.user_name, self.test_cfg["test_9832"]["password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "InvalidPassword",
                error.message,
                error.message)
        finally:
            self.cli_obj.logout_cortx_cli()
        self.log.info("ENDED: Verify change password with old password")

    # Access key and secret key is not needed for resetting iam user password using cortxcli
    # Hence invalid scenario
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5705")
    @CTFailOn(error_handler)
    def test_2905(self):
        """Verify change password for the user with users invalid
         access key and secret key."""
        self.log.info("STARTED: Verify change password for the user with "
                      "users invalid access key and secret key")
        self.create_user_and_access_key(
            self.user_name,
            self.test_cfg["test_9832"]["password"])
        try:
            self.iam_test_obj.change_user_password(
                self.test_cfg["test_9832"]["password"],
                self.test_cfg["test_9884"]["new_password"],
                "aldkjakjfakjfklafj",
                "kahdahfouk692583")
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "InvalidAccessKeyId",
                error.message,
                error.message)
        self.log.info("ENDED: Verify change password for the user with "
                      "users invalid access key and secret key")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5686")
    @CTFailOn(error_handler)
    def test_2929(self):
        """Get temporary credentials for valid user."""
        self.log.info("STARTED: Get temporary credentials for valid user")
        email_id = "{0}{1}".format(
            self.account_name, self.email_id)
        self.log.info(
            "Creating account with name %s and email id %s",
            self.account_name, email_id)
        resp = self.iam_test_obj.create_account_s3iamcli(
            self.account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Creating account login profile for account %s",
            self.account_name)
        resp = self.iam_test_obj.create_account_login_profile_s3iamcli(
            self.account_name,
            self.test_cfg["test_9923"]["account_password"],
            access_key,
            secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Creating user %s for account %s",
            self.user_name,
            self.account_name)
        resp = self.iam_test_obj.create_user_using_s3iamcli(
            self.user_name, access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Creating user login profile for user %s",
            self.user_name)
        resp = self.iam_test_obj.create_user_login_profile_s3iamcli(
            self.user_name,
            self.test_cfg["test_9832"]["password"],
            False,
            access_key=access_key,
            secret_key=secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Getting temporary credentials for user %s",
            self.user_name)
        resp = self.iam_test_obj.get_temp_auth_credentials_user(
            self.account_name,
            self.user_name,
            self.test_cfg["test_9832"]["password"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Get temporary credentials for valid user")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5660")
    @CTFailOn(error_handler)
    def test_2930(self):
        """Get temporary credentials for Invalid user."""
        self.log.info("STARTED: Get temporary credentials for Invalid user")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.log.info("Creating account with name %s and email id %s",
                      self.account_name, email_id)
        res = self.iam_test_obj.create_account_s3iamcli(
            self.account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert_true(res[0], res[1])
        self.log.info("Getting temporary credentials for invalid user")
        try:
            self.iam_test_obj.get_temp_auth_credentials_user(
                self.account_name,
                self.user_name,
                self.test_cfg["test_9924"]["user_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info("ENDED: Get temporary credentials for Invalid user")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5685")
    @CTFailOn(error_handler)
    def test_2931(self):
        """Get the temporary Credentials for user which is recently got deleted."""
        self.log.info("STARTED: Get the temporary Credentials for user which "
                      "is recently got deleted")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.log.info("Creating account with name %s and email id %s",
                      self.account_name, email_id)
        res = self.iam_test_obj.create_account_s3iamcli(
            self.account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert_true(res[0], res[1])
        acc_access_key = res[1]["access_key"]
        acc_secret_key = res[1]["secret_key"]
        self.log.info("Creating user with name %s",
                      self.user_name)
        res = self.iam_test_obj.create_user_using_s3iamcli(
            self.user_name, acc_access_key, acc_secret_key)
        assert_true(res[0], res[1])
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=acc_access_key,
            secret_key=acc_secret_key)
        self.log.info("Deleting user %s", self.user_name)
        res = new_iam_obj.delete_user(self.user_name)
        assert_true(res[0], res[1])
        self.log.info("Getting temporary credentials for "
                      "recently deleted user")
        try:
            self.iam_test_obj.get_temp_auth_credentials_user(
                self.account_name,
                self.user_name,
                self.test_cfg["test_9924"]["user_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "NoSuchEntity",
                error.message,
                error.message)
        self.log.info("ENDED: Get the temporary Credentials for user "
                      "which is recently got deleted")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-10923")
    @CTFailOn(error_handler)
    def test_2932(self):
        """Verify that by using user valid temporary credentials
         to perform s3 operations."""
        self.log.info("STARTED: Verify that by using user valid temporary "
                      "credentials to perform s3 operations")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            user_profile=True)
        self.log.info("Getting temporary credentials for user %s",
                      self.user_name)
        res = self.iam_test_obj.get_temp_auth_credentials_user(
            self.account_name,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"])
        assert_true(res[0], res[1])
        self.log.info("Performing s3 operations using users "
                      "temporary credentials")
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        res = self.iam_test_obj.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            "iambkt9927")
        assert_true(res[0], res[1])
        self.log.info("ENDED: Verify that by using user valid temporary "
                      "credentials to perform s3 operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5674")
    @CTFailOn(error_handler)
    def test_2933(self):
        """Verify and perform s3 operations by using user invalid temporary credentials."""
        self.log.info(
            "STARTED: Verify and perform s3 operations by using user "
            "invalid temporary credentials")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            user_profile=True)
        self.log.info(
            "Performing s3 operations using invalid temporary credentials")
        try:
            self.iam_test_obj.s3_ops_using_temp_auth_creds(
                "qeopioErUdjalkjfaowf",
                "AslkfjfjksjRsfjlskgUljflglsd",
                "2wslfaflk1aldjlakjfkljf67skhvskjdjiwfha",
                "iambkt9928")
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "InvalidAccessKeyId",
                error.message,
                error.message)
        self.log.info("ENDED: Verify and perform s3 operations by using "
                      "user invalid temporary credentials")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5659")
    @CTFailOn(error_handler)
    def test_2934(self):
        """Get temporary credentials for the user which doesn't
        contain the user login profile for that user."""
        self.log.info("STARTED: Verify and perform s3 operations by using "
                      "user invalid temporary credentials")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            user_profile=False)
        self.log.info(
            "Getting temporary credentials for user %s which "
            "does not contain login profile", self.user_name)
        try:
            self.iam_test_obj.get_temp_auth_credentials_user(
                self.account_name,
                self.user_name,
                self.test_cfg["test_9924"]["user_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "InvalidCredentials",
                error.message,
                error.message)
        self.log.info(
            "ENDED: Get temporary credentials for the user "
            "which doesn't contain the user login profile for that user")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5687")
    @CTFailOn(error_handler)
    def test_2935(self):
        """Get temporary credentials for the user which contain the user login profile."""
        self.log.info(
            "STARTED: Get temporary credentials for the user which contain"
            " the user login profile")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            user_profile=True)
        self.log.info("Getting temporary credentials for user %s",
                      self.user_name)
        res = self.iam_test_obj.get_temp_auth_credentials_user(
            self.account_name,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"])
        assert_true(res[0], res[1])
        self.log.info(
            "ENDED: Get temporary credentials for the user which contain"
            " the user login profile")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5666")
    @CTFailOn(error_handler)
    def test_2936(self):
        """Verify time duration of 20 mins for the Get temporary credentials for the valid user."""
        self.log.info("STARTED: Verify time duration of 20 mins for the Get"
                      " temporary credentials for the valid user")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            user_profile=True)
        self.log.info("Getting temporary credentials for user %s with 20 min"
                      " time duration", self.user_name)
        res = self.iam_test_obj.get_temp_auth_credentials_user(
            self.account_name,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            1200)
        assert_true(res[0], res[1])
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        self.log.info("Performing s3 operations with temp credentials")
        res = self.iam_test_obj.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            "iambkt9931")
        assert_true(res[0], res[1])
        time.sleep(1200)
        self.log.info("Performing s3 operations with expired temp credentials")
        try:
            self.iam_test_obj.s3_ops_using_temp_auth_creds(
                temp_access_key,
                temp_secret_key,
                temp_session_token,
                "iambkt9931")
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "ExpiredToken",
                error.message,
                error.message)
        self.log.info("ENDED: Verify time duration of 20 mins for the Get "
                      "temporary credentials for the valid user")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5667")
    @CTFailOn(error_handler)
    def test_2937(self):
        """Verify time duration less than 15 mins for the Get temporary
         credentails for the valid user."""
        self.log.info(
            "STARTED: Verify time duration less than 15 mins for "
            "the Get temporary credentials for the valid user")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            user_profile=True)
        self.log.info(
            "Getting temp auth credentials for user %s "
            "with less than 20 min duration", self.user_name)
        try:
            self.iam_test_obj.get_temp_auth_credentials_user(
                self.account_name,
                self.user_name,
                self.test_cfg["test_9927"]["user_password"],
                800)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "MinDurationIntervalNotMaintained",
                error.message,
                error.message)
        self.log.info(
            "STARTED: Verify time duration less than 15 mins for the "
            "Get temporary credentails for the valid user")

    # No api available yet for getting Temp auth credentials using cortxcli
    # Hence temporary skipping this test
    @pytest.mark.skip(reason="Will be taken after F-11D")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5684")
    @CTFailOn(error_handler)
    def test_2939(self):
        """List users By using Users get temporary credentials."""
        self.log.info("STARTED:List users By using Users get temp credentials")
        email_id = "{0}{1}".format(
            self.account_name,
            self.email_id)
        self.create_account_and_user(
            self.account_name,
            email_id,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"],
            user_profile=True)
        self.log.info("Getting temp auth credentials for user %s",
                      self.user_name)
        res = self.iam_test_obj.get_temp_auth_credentials_user(
            self.account_name,
            self.user_name,
            self.test_cfg["test_9927"]["user_password"])
        assert_true(res[0], res[1])
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_obj = iam_test_lib.IamTestLib(
            access_key=temp_access_key,
            secret_key=temp_secret_key)
        try:
            temp_obj.list_users()
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                "InvalidClientTokenId",
                error.message,
                error.message)
        self.log.info("ENDED: List users By using Users get temp credentials.")
