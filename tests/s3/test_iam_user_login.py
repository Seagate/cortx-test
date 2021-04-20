# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates.
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

"""IAM uesr login tests module."""

import time
import logging
import pytest
from config import CSM_CFG

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.configmanager import get_config_wrapper
from commons.utils.assert_utils import assert_true, assert_in, assert_false, assert_equal
from libs.s3 import iam_test_lib
from libs.s3 import S3H_OBJ
from libs.s3.cortxcli_test_lib import CortxcliS3AccountOperations, CortxcliS3BucketOperations
from libs.s3.cortxcli_test_lib import CortxcliCsmUser, CortxcliIamUser
from libs.s3.cortxcli_test_lib import CortxCliTestLib

IAM_TEST_OBJ = iam_test_lib.IamTestLib()
USER_CONFIG = get_config_wrapper(fpath="config/s3/test_iam_user_login.yaml")


class TestUserLoginProfileTests():
    """User Login Profile Test Suite."""

    @classmethod
    def setup_class(cls):
        """Setup all the states required for execution of this test suit."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.s3acc_obj = CortxcliS3AccountOperations()
        cls.s3acc_obj.open_connection()
        cls.s3bkt_obj = CortxcliS3BucketOperations(
            session_obj=cls.s3acc_obj.session_obj)
        cls.csm_user_obj = CortxcliCsmUser(
            session_obj=cls.s3acc_obj.session_obj)
        cls.iam_user_obj = CortxcliIamUser(
            session_obj=cls.s3acc_obj.session_obj)
        cls.cortx_obj = CortxCliTestLib(session_obj=cls.s3acc_obj.session_obj)
        cls.s3acc_prefix = "cli_s3acc"
        cls.s3acc_name = cls.s3acc_prefix
        cls.s3acc_email = "{}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.log.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """Setup method."""
        self.log.info("STARTED: Setup operations")
        self.delete_accounts_and_users()
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """Teardown method."""
        self.log.info("STARTED: Teardown operations")
        self.delete_accounts_and_users()
        self.log.info("ENDED: Teardown operations")

    @classmethod
    def teardown_class(cls):
        """Teardown any state that was previously setup with a setup_class."""
        cls.log.info("STARTED : Teardown operations at test suit level")
        cls.cortx_obj.close_connection()
        cls.log.info("ENDED : Teardown operations at test suit level")

    def delete_accounts_and_users(self):
        """Function will delete all accounts and users.

         which are getting created while running test cases.
         """
        user_cfg = USER_CONFIG["iam_user_login"]
        all_users = IAM_TEST_OBJ.list_users()[1]
        iam_users_list = [user["UserName"]
                          for user in all_users if
                          user_cfg["user_name_prefix"] in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        if iam_users_list:
            self.log.debug("Deleting IAM users...")
            for user in iam_users_list:
                res = IAM_TEST_OBJ.list_access_keys(user)
                if res[0]:
                    self.log.debug("Deleting user access key...")
                    keys_meta = res[1]["AccessKeyMetadata"]
                    for key in keys_meta:
                        IAM_TEST_OBJ.delete_access_key(
                            user, key["AccessKeyId"])
                    self.log.debug("Deleted user access key")
                IAM_TEST_OBJ.delete_user(user)
                self.log.debug("Deleted user : %s", user)
        self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        all_accounts = self.cortx_obj.list_accounts_cortxcli()[1]
        iam_accounts = [acc["AccountName"]
                        for acc in all_accounts if user_cfg["acc_name_prefix"] in acc["AccountName"]]
        self.log.debug("IAM accounts: %s", iam_accounts)
        if iam_accounts:
            self.log.debug("Deleting IAM accounts...")
            for acc in iam_accounts:
                self.log.debug("Deleting %s account", acc)
                resp = self.cortx_obj.delete_user()
                assert_equal(True, resp[0], resp[1])
                resp = self.cortx_obj.delete_s3account_cortx_cli(acc)
                assert_equal(True, resp[0], resp[1])
            self.log.debug("Deleted IAM accounts successfully")

    def create_user_and_access_key(
            self,
            user_name,
            password,
            pwd_reset=False):
        """
        Function will create a specified user and login profile for the same user.

        it will create an access key for the specified user.
        :param user_name: Name of user to be created
        :param password: User password to create login profile
        :param pwd_reset: Password reset option(True/False)
        :return: Tuple containing access and secret keys of user
        """
        self.log.info("Creating a user with name %s", user_name)
        resp = IAM_TEST_OBJ.create_user(user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created a user with name %s", user_name)
        self.log.info("Creating login profile for user %s", user_name)
        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name, password, pwd_reset)
        assert_true(resp[0], resp[1])
        self.log.info("Created login profile for user %s", user_name)
        self.log.info("Creating access key for user %s", user_name)
        resp = IAM_TEST_OBJ.create_access_key(user_name)
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

        resp = self.cortx_obj.create_s3account_cortx_cli(
            account_name=acc_name,
            account_email=email_id,
            password=self.s3acc_password)

        assert_true(resp[0], resp[1])
        self.log.info("Created account with name %s", acc_name)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Creating a user with name %s", user_name)
        resp = IAM_TEST_OBJ.create_user(user_name, user_password)
        assert_true(resp[0], resp[1])
        self.log.info("Created a user with name %s", user_name)
        if user_profile:
            self.log.info(
                "Creating user login profile for user %s", user_name)
            resp = IAM_TEST_OBJ.create_user_login_profile(
                user_name, user_password, pwd_reset)
            assert_true(resp[0], resp[1])
            self.log.info(
                "Created user login profile for user %s", user_name)
        return access_key, secret_key

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5664")
    @CTFailOn(error_handler)
    def test_2846(self):
        """Verify update-login-profile (password change) for IAM user."""
        self.log.info(
            "STARTED:Verify update-login-profile (password change) for IAM user")
        test_9824_cfg = USER_CONFIG["test_9824"]
        resp = IAM_TEST_OBJ.create_user(test_9824_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9824_cfg["user_name"],
            test_9824_cfg["password"],
            test_9824_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.update_user_login_profile(
            test_9824_cfg["user_name"], test_9824_cfg["password"])
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
        test_9825_cfg = USER_CONFIG["test_9825"]
        try:
            IAM_TEST_OBJ.update_user_login_profile(
                test_9825_cfg["user_name"], test_9825_cfg["password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9825_cfg["err_message"],
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
        test_9826_cfg = USER_CONFIG["test_9826"]
        resp = IAM_TEST_OBJ.create_user(test_9826_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9826_cfg["user_name"],
            test_9826_cfg["password"],
            test_9826_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.update_user_login_profile(
                test_9826_cfg["user_name"], test_9826_cfg["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9826_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Verify update-login-profile (password change)"
                      " for IAM user with 'Blank' or 'NO' password")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5681")
    @CTFailOn(error_handler)
    def test_2850(self):
        """Provide password length 128 valid characters long."""
        self.log.info("STARTED: Provide password length 128 valid "
                      "characters long")
        test_9828_cfg = USER_CONFIG["test_9828"]
        resp = IAM_TEST_OBJ.create_user(test_9828_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9828_cfg["user_name"],
            test_9828_cfg["password"],
            test_9828_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.update_user_login_profile(
            test_9828_cfg["user_name"], test_9828_cfg["new_password"])
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
        test_9829_cfg = USER_CONFIG["test_9829"]
        resp = IAM_TEST_OBJ.create_user(test_9829_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9829_cfg["user_name"],
            test_9829_cfg["password"],
            test_9829_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.update_user_login_profile(
                test_9829_cfg["user_name"], test_9829_cfg["new_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9829_cfg["err_message"],
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
        test_9830_cfg = USER_CONFIG["test_9830"]
        resp = IAM_TEST_OBJ.create_user(test_9830_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9830_cfg["user_name"],
            test_9830_cfg["password"],
            test_9830_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.update_user_login_profile(
            test_9830_cfg["user_name"],
            test_9830_cfg["new_password"],
            test_9830_cfg["new_password_reset"])
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
        test_9831_cfg = USER_CONFIG["test_9831"]
        resp = IAM_TEST_OBJ.create_user(test_9831_cfg["user_name"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.update_user_login_profile(
                test_9831_cfg["user_name"], test_9831_cfg["password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9831_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Update login profile for IAM user which does "
                      " not have the login profile created")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5662")
    @CTFailOn(error_handler)
    def test_2854(self):
        """verify update-login-profile with password.

        having combinations of special characters  _+=,.@- ."""
        self.log.info(
            "STARTED: verify update-login-profile with password having"
            " combinations of special characters  _+=,.@-")
        test_9832_cfg = USER_CONFIG["test_9832"]
        resp = IAM_TEST_OBJ.create_user(test_9832_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9832_cfg["user_name"],
            test_9832_cfg["password"],
            test_9832_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        for password in test_9832_cfg["special_char_pwd"]:
            resp = IAM_TEST_OBJ.update_user_login_profile(
                test_9832_cfg["user_name"], password)
            assert_true(resp[0], resp[1])
        self.log.info("ENDED: verify update-login-profile with password having"
                      " combinations of special characters  _+=,.@-")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5676")
    @CTFailOn(error_handler)
    def test_2855(self):
        """Update login profile for IAM user without mentioning.

        --password-reset-required --no-password-reset-required."""
        self.log.info("STARTED: Update login profile for IAM user without"
                      " mentioning  --password-reset-required "
                      "--no-password-reset-required")
        test_9833_cfg = USER_CONFIG["test_9833"]
        resp = IAM_TEST_OBJ.create_user(test_9833_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9833_cfg["user_name"],
            test_9833_cfg["password"],
            test_9833_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.update_user_login_profile_no_pwd_reset(
            test_9833_cfg["user_name"], test_9833_cfg["new_password"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Update login profile for IAM user without "
                      "mentioning--password-reset-required "
                      "--no-password-reset-required")

    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5677")
    @CTFailOn(error_handler)
    def test_2856(self):
        """update login profile for IAM user with both options.

         --no-password-reset-required --password-reset-required."""
        self.log.info("STARTED: update login profile for IAM user with both"
                      " options --no-password-reset-required "
                      "--password-reset-required")
        test_9834_cfg = USER_CONFIG["test_9834"]
        resp = IAM_TEST_OBJ.create_user(test_9834_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9834_cfg["user_name"], test_9834_cfg["password"])
        assert_true(resp[0], resp[1])

        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name=test_9834_cfg["user_name"],
            password=test_9834_cfg["password"],
            password_reset=False)
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name=test_9834_cfg["user_name"],
            password=test_9834_cfg["password"],
            password_reset=True)
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
        test_9835_cfg = USER_CONFIG["test_9835"]
        resp = IAM_TEST_OBJ.create_user(test_9835_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9835_cfg["user_name"],
            test_9835_cfg["password"],
            test_9835_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.update_user_login_profile_without_passowrd_and_reset_option(
                test_9835_cfg["user_name"],
                S3H_OBJ.get_local_keys()[0],
                S3H_OBJ.get_local_keys()[1])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9835_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("STARTED: Update login profile for IAM user without "
                      "password and reset flag enabled")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5703")
    @CTFailOn(error_handler)
    def test_2858(self):
        """Create a login profile for the existing IAM user."""
        self.log.info(
            "STARTED: Create a login profile for the existing IAM user")
        test_9836_cfg = USER_CONFIG["test_9836"]
        resp = IAM_TEST_OBJ.create_user(test_9836_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9836_cfg["user_name"],
            test_9836_cfg["password"],
            test_9836_cfg["password_reset"])
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
        test_9837_cfg = USER_CONFIG["test_9837"]
        try:
            IAM_TEST_OBJ.create_user_login_profile(
                test_9837_cfg["user_name"],
                test_9837_cfg["password"],
                test_9837_cfg["password_reset"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9837_cfg["err_message"],
                error.message,
                error.message)
        self.log.info(
            "ENDED: Create a login profile for the non-existing IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5697")
    @CTFailOn(error_handler)
    def test_2860(self):
        """Create a login profile with password of 0 character.

         or without password for existing user"""
        self.log.info("STARTED: Create a login profile with password of 0 "
                      "character or without password for existing user")
        test_9838_cfg = USER_CONFIG["test_9838"]
        resp = IAM_TEST_OBJ.create_user(test_9838_cfg["user_name"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.create_user_login_profile(
                test_9838_cfg["user_name"],
                test_9838_cfg["password"],
                test_9838_cfg["password_reset"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9838_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Create a login profile with password of 0 "
                      "character or without password for existing user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5695")
    @CTFailOn(error_handler)
    def test_2862(self):
        """Create a login profile with password of 128 characters for existing user."""
        self.log.info("STARTED: Create a login profile with password of 128"
                      " characters for existing user")
        test_9840_cfg = USER_CONFIG["test_9840"]
        resp = IAM_TEST_OBJ.create_user(test_9840_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9840_cfg["user_name"],
            test_9840_cfg["password"],
            test_9840_cfg["password_reset"])
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
        test_9841_cfg = USER_CONFIG["test_9841"]
        resp = IAM_TEST_OBJ.create_user(test_9841_cfg["user_name"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.create_user_login_profile(
                test_9841_cfg["user_name"],
                test_9841_cfg["password"],
                test_9841_cfg["password_reset"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9841_cfg["err_message"],
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
        test_9842_cfg = USER_CONFIG["test_9842"]
        resp = IAM_TEST_OBJ.create_user(test_9842_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9842_cfg["user_name"],
            test_9842_cfg["password"],
            test_9842_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create a login profile with password having"
                      " special characters only")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5701")
    @CTFailOn(error_handler)
    def test_2865(self):
        """Create a login profile with password.

        try few combinations of special characters and alphanumeric characters.
        """
        self.log.info("STARTED: Create a login profile with password - try few"
                      " combinations of special characters and alphanumberic "
                      "characters")
        test_9843_cfg = USER_CONFIG["test_9843"]
        for password in test_9843_cfg["special_char_pwd"]:
            resp = IAM_TEST_OBJ.create_user(test_9843_cfg["user_name"])
            assert_true(resp[0], resp[1])
            self.log.debug(
                "Creating user login profile with password: %s", password)
            resp = IAM_TEST_OBJ.create_user_login_profile(
                test_9843_cfg["user_name"], password, test_9843_cfg["password_reset"])
            assert_true(resp[0], resp[1])
            resp = IAM_TEST_OBJ.delete_user(test_9843_cfg["user_name"])
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
        test_9844_cfg = USER_CONFIG["test_9844"]
        self.log.debug("Creating %d users", test_9844_cfg["no_of_users"])
        for no_of_users in range(test_9844_cfg["no_of_users"]):
            new_user_name = "{0}{1}".format(
                test_9844_cfg["user_name"],
                test_9844_cfg["user_name_suffix"].format(no_of_users))
            self.log.debug("Creating a user with name: %s", new_user_name)
            resp = IAM_TEST_OBJ.create_user(new_user_name)
            assert_true(resp[0], resp[1])
            resp = IAM_TEST_OBJ.create_user_login_profile(
                new_user_name, test_9844_cfg["password"], test_9844_cfg["password_reset"])
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
        test_9845_cfg = USER_CONFIG["test_9845"]
        resp = IAM_TEST_OBJ.create_user(test_9845_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9845_cfg["user_name"],
            test_9845_cfg["password"],
            test_9845_cfg["password_reset"])
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
        test_9846_cfg = USER_CONFIG["test_9846"]
        resp = IAM_TEST_OBJ.create_user(test_9846_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9846_cfg["user_name"],
            test_9846_cfg["password"],
            test_9846_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        assert_true(resp[1]["password_reset_required"], resp[1])
        self.log.info(
            "ENDED: Create login profile for IAM user with "
            "--password-reset-required option")

    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5689")
    @CTFailOn(error_handler)
    def test_2869(self):
        """Create login profile for IAM user.

         without mentioning --password-reset-required --no-password-reset-required.
         """
        self.log.info(
            "STARTED: Create login profile for IAM user without mentioning  "
            "--password-reset-required --no-password-reset-required .")
        test_9847_cfg = USER_CONFIG["test_9847"]
        resp = IAM_TEST_OBJ.create_user(test_9847_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name=test_9847_cfg["user_name"],
            password=test_9847_cfg["password"],
            password_reset=False)
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name=test_9847_cfg["user_name"],
            password=test_9847_cfg["password"],
            password_reset=True)

        assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Create login profile for IAM user without mentioning  "
            "--password-reset-required --no-password-reset-required .")

    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5690")
    @CTFailOn(error_handler)
    def test_2870(self):
        """Create login profile for IAM user with both options.

        --no-password-reset-required --password-reset-required.
        """
        self.log.info(
            "STARTED: Create login profile for IAM user with both options "
            "--no-password-reset-required --password-reset-required .")
        test_9848_cfg = USER_CONFIG["test_9848"]
        resp = IAM_TEST_OBJ.create_user(test_9848_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name=test_9848_cfg["user_name"],
            password=test_9848_cfg["password"],
            password_reset=False)
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            user_name=test_9848_cfg["user_name"],
            password=test_9848_cfg["password"],
            password_reset=True)
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
        test_9849_cfg = USER_CONFIG["test_9849"]
        resp = IAM_TEST_OBJ.create_user(test_9849_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.create_user_login_profile(
            test_9849_cfg["user_name"],
            test_9849_cfg["password"],
            test_9849_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.get_user_login_profile(
            test_9849_cfg["user_name"])
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
        test_9850_cfg = USER_CONFIG["test_9850"]
        try:
            resp = IAM_TEST_OBJ.get_user_login_profile(
                test_9850_cfg["user_name"])
            assert_true(resp[0], resp[1])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9850_cfg["err_message"],
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
        test_9851_cfg = USER_CONFIG["test_9851"]
        resp = IAM_TEST_OBJ.create_user(test_9851_cfg["user_name"])
        assert_true(resp[0], resp[1])
        try:
            IAM_TEST_OBJ.get_user_login_profile(test_9851_cfg["user_name"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9851_cfg["err_message"],
                error.message,
                error.message)
        self.log.info(
            "ENDED: Verify get-login-profile for a non profile IAM user "
            "(IAM user with no profile created)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5668")
    @CTFailOn(error_handler)
    def test_2897(self):
        """Verify password change for IAM user."""
        self.log.info("STARTED: Verify password change for IAM user")
        test_9876_cfg = USER_CONFIG["test_9876"]
        resp = self.create_user_and_access_key(
            test_9876_cfg["user_name"],
            test_9876_cfg["password"])
        user_access_key = resp[0]
        user_secret_key = resp[1]
        resp = IAM_TEST_OBJ.change_user_password(
            test_9876_cfg["password"],
            test_9876_cfg["new_password"],
            user_access_key,
            user_secret_key)
        assert_true(resp[0], resp[1])
        resp = IAM_TEST_OBJ.delete_access_key(
            test_9876_cfg["user_name"], user_access_key)
        assert_true(resp[0], resp[1])
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
        test_9877_cfg = USER_CONFIG["test_9877"]
        try:
            IAM_TEST_OBJ.change_user_password(
                test_9877_cfg["password"],
                test_9877_cfg["new_password"],
                test_9877_cfg["user_access_key"],
                test_9877_cfg["user_secret_key"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9877_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Verify password change for a "
                      "non-existing IAM user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5682")
    @CTFailOn(error_handler)
    def test_2899(self):
        """Provide only six character length in password."""
        self.log.info("STARTED: Provide only six character length in password")
        test_9878_cfg = USER_CONFIG["test_9878"]
        resp = self.create_user_and_access_key(
            test_9878_cfg["user_name"],
            test_9878_cfg["password"])
        user_access_key = resp[0]
        user_secret_key = resp[1]
        resp = IAM_TEST_OBJ.change_user_password(
            test_9878_cfg["password"],
            test_9878_cfg["new_password"],
            user_access_key,
            user_secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Provide only six character length in password")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5683")
    @CTFailOn(error_handler)
    def test_2849(self):
        """Provide only one character length in password."""
        self.log.info("STARTED: Provide only one character length in password")
        test_9879_cfg = USER_CONFIG["test_9879"]
        resp = self.create_user_and_access_key(
            test_9879_cfg["user_name"],
            test_9879_cfg["password"])
        user_access_key = resp[0]
        user_secret_key = resp[1]
        try:
            IAM_TEST_OBJ.change_user_password(
                test_9879_cfg["password"],
                test_9879_cfg["new_password"],
                user_access_key,
                user_secret_key)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9879_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Provide only one character length in password")

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
        test_9882_cfg = USER_CONFIG["test_9882"]
        resp = self.create_user_and_access_key(
            test_9882_cfg["user_name"],
            test_9882_cfg["password"],
            test_9882_cfg["password_reset"])
        user_access_key = resp[0]
        user_secret_key = resp[1]
        for new_password in test_9882_cfg["list_special_char_pwd"]:
            self.log.debug(new_password)
            resp = IAM_TEST_OBJ.change_user_password(
                test_9882_cfg["password"],
                new_password,
                user_access_key,
                user_secret_key)
            assert_true(resp[0], resp[1])
            resp = IAM_TEST_OBJ.change_user_password(
                new_password, test_9882_cfg["password"], user_access_key, user_secret_key)
            assert_true(resp[0], resp[1])
        self.log.info("ENDED: Password with allowed special "
                      "characters ~,$,?,&,\\n,\\t,<,>")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5673")
    @CTFailOn(error_handler)
    def test_2904(self):
        """Verify change password with old password."""
        self.log.info("STARTED: Verify change password with old password")
        test_9883_cfg = USER_CONFIG["test_9883"]
        resp = self.create_user_and_access_key(
            test_9883_cfg["user_name"],
            test_9883_cfg["password"],
            test_9883_cfg["password_reset"])
        user_access_key = resp[0]
        user_secret_key = resp[1]
        try:
            IAM_TEST_OBJ.change_user_password(
                test_9883_cfg["password"],
                test_9883_cfg["password"],
                user_access_key,
                user_secret_key)
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9883_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Verify change password with old password")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5705")
    @CTFailOn(error_handler)
    def test_2905(self):
        """Verify change password for the user with users invalid
         access key and secret key."""
        self.log.info("STARTED: Verify change password for the user with "
                      "users invalid access key and secret key")
        test_9884_cfg = USER_CONFIG["test_9884"]
        self.create_user_and_access_key(
            test_9884_cfg["user_name"],
            test_9884_cfg["password"])
        try:
            IAM_TEST_OBJ.change_user_password(
                test_9884_cfg["password"],
                test_9884_cfg["new_password"],
                test_9884_cfg["dummy_access_key"],
                test_9884_cfg["dummy_secret_key"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9884_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Verify change password for the user with "
                      "users invalid access key and secret key")

    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5686")
    @CTFailOn(error_handler)
    def test_2929(self):
        """Get temporary credentials for valid user.

        This method is not be executed as account profile is not supported
        with cortxcli.
        """
        self.log.info("STARTED: Get temporary credentials for valid user")
        test_9923_cfg = USER_CONFIG["test_9923"]
        email_id = "{0}{1}".format(
            test_9923_cfg["account_name"],
            test_9923_cfg["email_id"])
        self.log.info(
            "Creating account with name %s and email id %s",
            test_9923_cfg["account_name"],
            email_id)

        resp = self.s3acc_obj.create_account_cortxcli(
            test_9923_cfg["account_name"], email_id, self.s3acc_password)

        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Creating account login profile for account %s",
            USER_CONFIG["test_9923"]["account_name"])

        resp = IAM_TEST_OBJ.create_account_login_profile_s3iamcli(
            test_9923_cfg["account_name"],
            test_9923_cfg["account_password"],
            access_key,
            secret_key)

        assert_true(resp[0], resp[1])
        self.log.info(
            "Creating user %s for account %s",
            test_9923_cfg["user_name"],
            test_9923_cfg["account_name"])
        resp = IAM_TEST_OBJ.create_user_using_s3iamcli(
            test_9923_cfg["user_name"], access_key, secret_key)

        assert_true(resp[0], resp[1])
        self.log.info(
            "Creating user login profile for user %s",
            test_9923_cfg["user_name"])

        resp = IAM_TEST_OBJ.create_user_login_profile_s3iamcli(
            test_9923_cfg["user_name"],
            test_9923_cfg["user_password"],
            test_9923_cfg["password_reset"],
            access_key=access_key,
            secret_key=secret_key)
        assert_true(resp[0], resp[1])
        self.log.info("Created IAM user %s", test_9923_cfg["user_name"])

        self.log.info(
            "Getting temporary credentials for user %s",
            USER_CONFIG["test_9923"]["user_name"])
        resp = IAM_TEST_OBJ.get_temp_auth_credentials_user(
            test_9923_cfg["account_name"],
            test_9923_cfg["user_name"],
            test_9923_cfg["user_password"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Get temporary credentials for valid user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5660")
    @CTFailOn(error_handler)
    def test_2930(self):
        """Get temporary credentials for Invalid user."""
        self.log.info("STARTED: Get temporary credentials for Invalid user")
        test_9924_cfg = USER_CONFIG["test_9924"]
        email_id = "{0}{1}".format(
            test_9924_cfg["account_name"],
            test_9924_cfg["email_id"])
        self.log.info("Creating account with name %s and email id %s",
                      test_9924_cfg["account_name"], email_id)
        res = self.cortx_obj.create_account_cortxcli(
            test_9924_cfg["account_name"], email_id, password=self.s3acc_password)
        assert_true(res[0], res[1])
        self.log.info("Getting temporary credentials for invalid user")
        try:
            IAM_TEST_OBJ.get_temp_auth_credentials_user(
                test_9924_cfg["account_name"],
                test_9924_cfg["user_name"],
                test_9924_cfg["user_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9924_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Get temporary credentials for Invalid user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5685")
    @CTFailOn(error_handler)
    def test_2931(self):
        """Get the temporary Credentials for user which is recently got deleted."""
        self.log.info("STARTED: Get the temporary Credentials for user which "
                      "is recently got deleted")
        test_9925_cfg = USER_CONFIG["test_9925"]
        email_id = "{0}{1}".format(
            test_9925_cfg["account_name"],
            test_9925_cfg["email_id"])
        self.log.info("Creating account with name %s and email id %s",
                      test_9925_cfg["account_name"], email_id)
        res = self.cortx_obj.create_account_cortxcli(
            test_9925_cfg["account_name"], email_id, password=self.s3acc_password)
        assert_true(res[0], res[1])
        acc_access_key = res[1]["access_key"]
        acc_secret_key = res[1]["secret_key"]
        self.log.info("Creating user with name %s",
                      USER_CONFIG["test_9925"]["user_name"])

        res = self.cortx_obj.create_user_cortxcli(
            user_name=test_9925_cfg["user_name"],
            password=test_9925_cfg["user_password"],
            confirm_password=test_9925_cfg["user_password"])
        assert_true(res[0], res[1])
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=acc_access_key,
            secret_key=acc_secret_key)
        self.log.info("Deleting user %s", test_9925_cfg["user_name"])
        res = new_iam_obj.delete_user(test_9925_cfg["user_name"])
        assert_true(res[0], res[1])
        self.log.info("Getting temporary credentials for "
                      "recently deleted user")
        try:
            IAM_TEST_OBJ.get_temp_auth_credentials_user(
                test_9925_cfg["account_name"],
                test_9925_cfg["user_name"],
                test_9925_cfg["user_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_9925_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Get the temporary Credentials for user "
                      "which is recently got deleted")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-10923")
    @CTFailOn(error_handler)
    def test_2932(self):
        """Verify that by using user valid temporary credentials
         to perform s3 operations."""
        self.log.info("STARTED: Verify that by using user valid temporary "
                      "credentials to perform s3 operations")
        test_9927_cfg = USER_CONFIG["test_9927"]
        email_id = "{0}{1}".format(
            test_9927_cfg["account_name"],
            test_9927_cfg["email_id"])
        self.create_account_and_user(
            test_9927_cfg["account_name"],
            email_id,
            test_9927_cfg["user_name"],
            test_9927_cfg["user_password"],
            user_profile=True)
        self.log.info("Getting temporary credentials for user %s",
                      USER_CONFIG["test_9927"]["user_name"])
        res = IAM_TEST_OBJ.get_temp_auth_credentials_user(
            test_9927_cfg["account_name"],
            test_9927_cfg["user_name"],
            test_9927_cfg["user_password"])
        assert_true(res[0], res[1])
        self.log.info("Performing s3 operations using users "
                      "temporary credentials")
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        res = IAM_TEST_OBJ.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            test_9927_cfg["bucket_name"])
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
        test_28_cfg = USER_CONFIG["test_9928"]
        email_id = "{0}{1}".format(
            test_28_cfg["account_name"],
            test_28_cfg["email_id"])
        self.create_account_and_user(
            test_28_cfg["account_name"],
            email_id,
            test_28_cfg["user_name"],
            test_28_cfg["user_password"],
            user_profile=True)
        self.log.info(
            "Performing s3 operations using invalid temporary credentials")
        try:
            IAM_TEST_OBJ.s3_ops_using_temp_auth_creds(
                test_28_cfg["dummy_access_key"],
                test_28_cfg["dummy_secret_key"],
                test_28_cfg["dummy_session_token"],
                test_28_cfg["bucket_name"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_28_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Verify and perform s3 operations by using "
                      "user invalid temporary credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5659")
    @CTFailOn(error_handler)
    def test_2934(self):
        """Get temporary credentials for the user which doesn't
        contain the user login profile for that user."""
        self.log.info("STARTED: Verify and perform s3 operations by using "
                      "user invalid temporary credentials")
        test_29_cfg = USER_CONFIG["test_9929"]
        email_id = "{0}{1}".format(
            test_29_cfg["account_name"],
            test_29_cfg["email_id"])
        self.create_account_and_user(
            test_29_cfg["account_name"],
            email_id,
            test_29_cfg["user_name"],
            user_profile=False)
        self.log.info(
            "Getting temporary credentials for user %s which "
            "does not contain login profile", test_29_cfg["user_name"])
        try:
            IAM_TEST_OBJ.get_temp_auth_credentials_user(
                test_29_cfg["account_name"],
                test_29_cfg["user_name"],
                test_29_cfg["user_password"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_29_cfg["err_message"],
                error.message,
                error.message)
        self.log.info(
            "ENDED: Get temporary credentials for the user "
            "which doesn't contain the user login profile for that user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5687")
    @CTFailOn(error_handler)
    def test_2935(self):
        """Get temporary credentials for the user which contain the user login profile."""
        self.log.info(
            "STARTED: Get temporary credentials for the user which contain"
            " the user login profile")
        test_30_cfg = USER_CONFIG["test_9930"]
        email_id = "{0}{1}".format(
            test_30_cfg["account_name"],
            test_30_cfg["email_id"])
        self.create_account_and_user(
            test_30_cfg["account_name"],
            email_id,
            test_30_cfg["user_name"],
            test_30_cfg["user_password"],
            user_profile=True)
        self.log.info("Getting temporary credentials for user %s",
                      test_30_cfg["user_name"])
        res = IAM_TEST_OBJ.get_temp_auth_credentials_user(
            test_30_cfg["account_name"],
            test_30_cfg["user_name"],
            test_30_cfg["user_password"])
        assert_true(res[0], res[1])
        self.log.info(
            "ENDED: Get temporary credentials for the user which contain"
            " the user login profile")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5666")
    @CTFailOn(error_handler)
    def test_2936(self):
        """Verify time duration of 20 mins for the Get temporary credentials for the valid user."""
        self.log.info("STARTED: Verify time duration of 20 mins for the Get"
                      " temporary credentials for the valid user")
        test_31_cfg = USER_CONFIG["test_9931"]
        email_id = "{0}{1}".format(
            test_31_cfg["account_name"],
            test_31_cfg["email_id"])
        self.create_account_and_user(
            test_31_cfg["account_name"],
            email_id,
            test_31_cfg["user_name"],
            test_31_cfg["user_password"],
            user_profile=True)
        self.log.info("Getting temporary credentials for user %s with 20 min"
                      " time duration", test_31_cfg["user_name"])
        res = IAM_TEST_OBJ.get_temp_auth_credentials_user(
            test_31_cfg["account_name"],
            test_31_cfg["user_name"],
            test_31_cfg["user_password"],
            test_31_cfg["duration"])
        assert_true(res[0], res[1])
        temp_access_key = res[1]["access_key"]
        temp_secret_key = res[1]["secret_key"]
        temp_session_token = res[1]["session_token"]
        self.log.info("Performing s3 operations with temp credentials")
        res = IAM_TEST_OBJ.s3_ops_using_temp_auth_creds(
            temp_access_key,
            temp_secret_key,
            temp_session_token,
            test_31_cfg["bucket_name"])
        assert_true(res[0], res[1])
        time.sleep(test_31_cfg["duration"])
        self.log.info("Performing s3 operations with expired temp credentials")
        try:
            IAM_TEST_OBJ.s3_ops_using_temp_auth_creds(
                temp_access_key,
                temp_secret_key,
                temp_session_token,
                test_31_cfg["bucket_name"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_31_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: Verify time duration of 20 mins for the Get "
                      "temporary credentials for the valid user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5667")
    @CTFailOn(error_handler)
    def test_2937(self):
        """Verify time duration less than 15 mins.

         for the Get temporary credentails for the valid user."""
        self.log.info(
            "STARTED: Verify time duration less than 15 mins for "
            "the Get temporary credentials for the valid user")
        test_32_cfg = USER_CONFIG["test_9932"]
        email_id = "{0}{1}".format(
            test_32_cfg["account_name"],
            test_32_cfg["email_id"])
        self.create_account_and_user(
            test_32_cfg["account_name"],
            email_id,
            test_32_cfg["user_name"],
            test_32_cfg["user_password"],
            user_profile=True)
        self.log.info(
            "Getting temp auth credentials for user %s "
            "with less than 20 min duration", test_32_cfg["user_name"])
        try:
            IAM_TEST_OBJ.get_temp_auth_credentials_user(
                test_32_cfg["account_name"],
                test_32_cfg["user_name"],
                test_32_cfg["user_password"],
                test_32_cfg["duration"])
        except CTException as error:
            self.log.debug(error.message)
            assert_in(
                test_32_cfg["err_message"],
                error.message,
                error.message)
        self.log.info(
            "STARTED: Verify time duration less than 15 mins for the "
            "Get temporary credentails for the valid user")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5684")
    @CTFailOn(error_handler)
    def test_2939(self):
        """List users By using Users get temporary credentials."""
        self.log.info("STARTED:List users By using Users get temp credentials")
        test_36_cfg = USER_CONFIG["test_9936"]
        email_id = "{0}{1}".format(
            test_36_cfg["account_name"],
            test_36_cfg["email_id"])
        self.create_account_and_user(
            test_36_cfg["account_name"],
            email_id,
            test_36_cfg["user_name"],
            test_36_cfg["user_password"],
            user_profile=True)
        self.log.info("Getting temp auth credentials for user %s",
                      test_36_cfg["user_name"])
        res = IAM_TEST_OBJ.get_temp_auth_credentials_user(
            test_36_cfg["account_name"],
            test_36_cfg["user_name"],
            test_36_cfg["user_password"])
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
                test_36_cfg["err_message"],
                error.message,
                error.message)
        self.log.info("ENDED: List users By using Users get temp credentials.")
