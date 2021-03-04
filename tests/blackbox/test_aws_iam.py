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

"""Aws iam test module."""

import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.assert_utils import \
    assert_true, assert_false, assert_in, assert_equal
from libs.s3 import iam_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD

IAM_OBJ = iam_test_lib.IamTestLib()

IAM_CFG = read_yaml("config/blackbox/test_aws_iam.yaml")[1]
cmn_conf = read_yaml("config/common_config.yaml")[1]


def create_account():
    """Function will create IAM account."""
    acc_name = "{}{}".format(
        IAM_CFG["acc_user_mng"]["account_name"], str(int(time.time())))
    acc_email = "{}{}".format(acc_name, IAM_CFG["acc_user_mng"]["email_id"])
    return IAM_OBJ.create_account_s3iamcli(
        acc_name,
        acc_email,
        LDAP_USERNAME,
        LDAP_PASSWD)


class TestBlackBox:
    """Blackbox Testsuite for aws iam tool."""

    cfg = IAM_CFG["acc_user_mng"]

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.new_access_key = None
        cls.new_secret_key = None
        cls.random_str = None

    @CTFailOn(error_handler)
    def setup_method(self):
        """Function to perform the setup ops for each test."""
        self.random_str = str(int(time.time()))

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown Operations")
        user_cfg = IAM_CFG["iam_user_login"]
        all_users = IAM_OBJ.list_users()[1]
        iam_users_list = [user["UserName"]
                          for user in all_users if
                          user_cfg["user_name_prefix"] in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        if iam_users_list:
            self.log.debug("Deleting IAM users...")
            for user in iam_users_list:
                res = IAM_OBJ.list_access_keys(user)
                if res[0]:
                    self.log.debug("Deleting user access key...")
                    keys_meta = res[1]["AccessKeyMetadata"]
                    for key in keys_meta:
                        IAM_OBJ.delete_access_key(
                            user, key["AccessKeyId"])
                    self.log.debug("Deleted user access key")
                IAM_OBJ.delete_user(user)
                self.log.debug("Deleted user : %s", user)
        account_name = self.cfg["account_name"]
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            LDAP_USERNAME,
            LDAP_PASSWD)[1]
        all_acc = [acc["AccountName"]
                   for acc in acc_list if account_name in acc["AccountName"]]
        if all_acc:
            self.log.info("Accounts to delete: %s", all_acc)
            for acc in all_acc:
                self.log.info("Deleting %s account", acc)
                IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc)
                self.log.info("Deleted %s account", acc)
        self.log.info("ENDED: Teardown Operations")

    def create_user_and_access_key(
            self,
            user_name,
            password,
            iam_obj,
            pwd_reset=False):
        """
        Function will create a specified user and login profile for the same user.

        Also it will create an access key for the specified user.
        :param iam_obj:
        :param str user_name: Name of user to be created
        :param str password: User password to create login profile
        :param bool pwd_reset: Password reset option(True/False)
        :return: Tuple containing access and secret keys of user
        """
        self.log.info("Creating a user with name %s", user_name)
        resp = iam_obj.create_user(user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created a user with name %s", user_name)
        self.log.info("Creating login profile for user %s", user_name)
        resp = iam_obj.create_user_login_profile(
            user_name, password, pwd_reset)
        assert_true(resp[0], resp[1])
        self.log.info("Created login profile for user %s", user_name)
        self.log.info("Creating access key for user %s", user_name)
        resp = iam_obj.create_access_key(user_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created access key for user %s", user_name)
        access_key = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        return access_key, secret_key

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7166")
    @CTFailOn(error_handler)
    def test_update_user_2419(self):
        """Update User using aws iam."""
        self.log.info("STARTED: Update User using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        test_2419_cfg = IAM_CFG["test_2419"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        user_nm = test_2419_cfg["user_name"].format(self.random_str)
        resp = new_iam_obj.create_user(user_nm)
        assert_true(resp[0], resp[1])
        resp = new_iam_obj.create_user_login_profile(
            user_nm,
            test_2419_cfg["password"],
            test_2419_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        self.log.info("Step 2: Updating user name of already existing user")
        new_user_name = IAM_CFG["test_2419"]["new_user_name"]
        resp = new_iam_obj.update_user(
            new_user_name, user_nm)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Updated user name of already existing user")
        self.log.info(
            "Step 3: Listing users and verifying user name is updated")
        resp = new_iam_obj.list_users()
        self.log.info("User: %s", resp[1])
        assert_true(resp[0], resp[1])
        all_users = resp[1]
        iam_users_list = [IAM_CFG["test_2419"]["new_user_name"]
                          for user in all_users if
                          IAM_CFG["test_2419"]["new_user_name"] in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_true(iam_users_list, "true")
        self.log.info("Step 3: Listed users and verified user name is updated")
        self.log.info("ENDED: Update User using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7167")
    @CTFailOn(error_handler)
    def test_list_user_2420(self):
        """list user using aws iam."""
        self.log.info(
            "STARTED: list user using aws iam")
        self.log.info("Step 1: Create new account and new user in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        test_2420_cfg = IAM_CFG["test_2420"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_user(test_2420_cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info(
            "Step 2: Listing users and verifying user name present")
        all_users = new_iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        iam_users_list = [IAM_CFG["test_2420"]["user_name"]
                          for user in all_users if
                          IAM_CFG["test_2420"]["user_name"] in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_true(iam_users_list, "true")
        self.log.info("Step 2: Listed users and verified user name is present")
        self.log.info("ENDED: list user using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7168")
    def test_del_user_2421(self):
        """Delete User using aws iam."""
        self.log.info(
            "STARTED: Delete User using aws iam")
        self.log.info("Step 1: Create new account and new user in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        test_2421_cfg = IAM_CFG["test_2421"]
        resp = new_iam_obj.create_user(test_2421_cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        resp = new_iam_obj.delete_user(test_2421_cfg["user_name"])
        assert_true(resp[0], resp[1])
        all_users = new_iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        iam_users_list = [IAM_CFG["test_2421"]["user_name"]
                          for user in all_users if
                          IAM_CFG["test_2421"]["user_name"] in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_false(iam_users_list, "false")
        self.log.info("ENDED: Delete User using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7169")
    @CTFailOn(error_handler)
    def test_create_100_users_per_account_2422(self):
        """Create 100 Users per account using aws iam."""
        self.log.info(
            "STARTED: Create 100 Users per account using aws iam")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        test_2422_cfg = IAM_CFG["test_2422"]
        self.log.debug(
            "Creating %s users",
            test_2422_cfg["no_of_users"])
        for num in range(test_2422_cfg["no_of_users"]):
            new_user_name = "{0}{1}".format(
                test_2422_cfg["user_name"],
                test_2422_cfg["user_name_suffix"].format(num))
            self.log.debug(
                "Creating a user with name: %s", new_user_name)
            resp = new_iam_obj.create_user(new_user_name)
            assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Create 100 Users per account using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7170")
    @CTFailOn(error_handler)
    def test_list_accesskeys_2425(self):
        """List accesskeys for the user using aws iam."""
        self.log.info("STARTED: list accesskeys for the user using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        self.new_access_key = resp[1]["access_key"]
        self.new_secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=self.new_access_key,
            secret_key=self.new_secret_key)
        test_2425_cfg = IAM_CFG["test_2425"]
        resp = new_iam_obj.create_user(test_2425_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = new_iam_obj.create_user_login_profile(
            test_2425_cfg["user_name"],
            test_2425_cfg["password"],
            test_2425_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        self.log.info("Creating access key for user %s",
                      test_2425_cfg["user_name"])
        resp = new_iam_obj.create_access_key(test_2425_cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Created access key for user %s",
            test_2425_cfg["user_name"])
        resp = new_iam_obj.list_access_keys(test_2425_cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: list accesskeys for the user using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7171")
    @CTFailOn(error_handler)
    def test_delete_accesskeys_2426(self):
        """Delete Accesskey of a user using aws iam."""
        self.log.info("STARTED: Delete Accesskey of a user using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        test_2426_cfg = IAM_CFG["test_2426"]
        resp = self.create_user_and_access_key(
            test_2426_cfg["user_name"],
            test_2426_cfg["password"],
            new_iam_obj)
        user_access_key = resp[0]
        user_secret_key = resp[1]
        resp = new_iam_obj.delete_access_key(
            test_2426_cfg["user_name"], user_access_key)
        assert_true(user_access_key, user_secret_key)
        self.log.info("ENDED: Delete Accesskey of a user using aws iam %s", resp)

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7172")
    @CTFailOn(error_handler)
    def test_create_accesskey_2424(self):
        """Create Access key to the user using aws iam."""
        self.log.info("STARTED: Create Access key to the user using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        test_2424_cfg = IAM_CFG["test_2424"]
        resp = new_iam_obj.create_user(test_2424_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = new_iam_obj.create_user_login_profile(
            test_2424_cfg["user_name"],
            test_2424_cfg["password"],
            test_2424_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        self.log.info(
            "Step 2: Creating access key for user %s",
            test_2424_cfg["user_name"])
        resp = new_iam_obj.create_access_key(test_2424_cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Created access key for user %s",
            test_2424_cfg["user_name"])
        resp = new_iam_obj.list_access_keys(test_2424_cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create Access key to the user using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7173")
    @CTFailOn(error_handler)
    def test_create_new_user_2418(self):
        """Create new user for current Account AWS IAM."""
        self.log.info(
            "STARTED: Create new user for current Account AWS IAM")
        self.log.info("Step 1: Create new account and new user in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        test_2418_cfg = IAM_CFG["test_2418"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        user_nm = test_2418_cfg["user_name"].format(self.random_str)
        resp = new_iam_obj.create_user(user_nm)
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info(
            "Step 2: Listing users and verifying user name present")
        all_users = new_iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        iam_users_list = [user_nm
                          for user in all_users if
                          user_nm in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_true(iam_users_list, "true")
        self.log.info("Step 2: Listed users and verified user name is present")
        self.log.info("ENDED: Create new user for current Account AWS IAM")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7191")
    @CTFailOn(error_handler)
    def test_create_user_existing_name_2423(self):
        """Creating user with existing name With AWS IAM client."""
        self.log.info(
            "STARTED: creating user with existing name With AWS IAM client")
        self.log.info("Step 1: Create new account")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Step 1: Creating user with name %s",
            IAM_CFG["acc_user_mng"]["user_name"])
        resp = IAM_OBJ.create_user_using_s3iamcli(
            IAM_CFG["acc_user_mng"]["user_name"], access_key, secret_key)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created user with name %s",
            IAM_CFG["acc_user_mng"]["user_name"])
        self.log.info(
            "Step 2: Creating user with existing name %s",
            IAM_CFG["acc_user_mng"]["user_name"])
        try:
            IAM_OBJ.create_user(
                IAM_CFG["acc_user_mng"]["user_name"])
        except CTException as error:
            assert_in(
                IAM_CFG["test_2423"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 2: Could not create user with existing name %s",
            IAM_CFG["acc_user_mng"]["user_name"])
        self.log.info(
            "ENDED: creating user with existing name With AWS IAM client")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7174")
    @CTFailOn(error_handler)
    def test_update_accesskey_2427(self):
        """Update Accesskey of a user with active mode using aws iam."""
        test_2427_cfg = IAM_CFG["test_2427"]
        self.log.info(
            "STARTED: Update Accesskey of a user with active mode using aws iam")
        self.log.info(
            "Step 1: Creating a new account with name %s",
            IAM_CFG["acc_user_mng"]["account_name"])
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        self.log.info(
            "Step 1: Created a new account with name %s",
            IAM_CFG["acc_user_mng"]["account_name"])
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info(
            "Step 3: Creating a user with name %s",
            self.cfg["user_name"])
        resp = iam_obj.create_user(self.cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s",
            self.cfg["user_name"])
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(self.cfg["user_name"])
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updating access key of user")
        resp = iam_obj.update_access_key(
            access_key_to_update,
            test_2427_cfg["status"],
            self.cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updated access key of user")
        self.log.info("Step 6: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(self.cfg["user_name"])
        assert_true(resp[0], resp[1])
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert_equal(new_access_key, access_key_to_update, resp[1])
        assert_equal(status, test_2427_cfg["status"], resp[1])
        self.log.info(
            "Step 6: Verified that access key of user is updated successfully")
        self.log.info(
            "ENDED: Update Accesskey of a user with active mode using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7175")
    @CTFailOn(error_handler)
    def test_update_accesskey_userinactive_2428(self):
        """Update accesskey of a user with inactive mode using aws iam."""
        test_2428_cfg = IAM_CFG["test_2428"]
        self.log.info(
            "STARTED: update accesskey of a user with inactive mode using aws iam")
        self.log.info(
            "Step 1: Creating a new account with name %s",
            IAM_CFG["acc_user_mng"]["account_name"])
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        self.log.info(
            "Step 1: Created a new account with name %s",
            IAM_CFG["acc_user_mng"]["account_name"])
        self.log.info(
            "Step 2: Verifying that new account is created successfully")
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Verified that new account is created successfully")
        self.log.info(
            "Step 3: Creating a user with name %s",
            self.cfg["user_name"])
        resp = iam_obj.create_user(self.cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Created a user with name %s",
            self.cfg["user_name"])
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(self.cfg["user_name"])
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updating access key of user")
        resp = iam_obj.update_access_key(
            access_key_to_update,
            test_2428_cfg["status"],
            self.cfg["user_name"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updated access key of user")
        self.log.info("Step 6: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(self.cfg["user_name"])
        assert_true(resp[0], resp[1])
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert_equal(new_access_key, access_key_to_update, resp[1])
        assert_equal(status, test_2428_cfg["status"], resp[1])
        self.log.info(
            "Step 6: Verified that access key of user is updated successfully")
        self.log.info(
            "ENDED: update accesskey of a user with inactive mode using aws iam")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-7176")
    @CTFailOn(error_handler)
    def test_create_accesskey_existinguser_2429(self):
        """Create accesskey key with existing user name using aws iam."""
        self.log.info(
            "STARTED: create accesskey key with existing user name using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = create_account()
        assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        test_2429_cfg = IAM_CFG["test_2429"]
        resp = new_iam_obj.create_user(test_2429_cfg["user_name"])
        assert_true(resp[0], resp[1])
        resp = new_iam_obj.create_user_login_profile(
            test_2429_cfg["user_name"],
            test_2429_cfg["password"],
            test_2429_cfg["password_reset"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        for _ in range(IAM_CFG["test_2429"]["accesskey_count"]):
            self.log.info(
                "Step 2: Creating access key for user %s",
                test_2429_cfg["user_name"])
            resp = new_iam_obj.create_access_key(test_2429_cfg["user_name"])
            assert_true(resp[0], resp[1])
            self.log.info(
                "Step 2: Created access key for user %s",
                test_2429_cfg["user_name"])
            resp = new_iam_obj.list_access_keys(test_2429_cfg["user_name"])
            assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: create accesskey key with existing user name using aws iam")
