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

"""Aws iam test module."""

import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import system_utils
from commons.utils import assert_utils
from config.s3 import S3_CFG
from config.s3 import S3_BLKBOX_CFG
from libs.s3 import iam_test_lib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI


class TestAwsIam:
    """Blackbox Testsuite for aws iam tool."""

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log.info("STARTED: setup test suite operations.")
        cls.rest_obj = S3AccountOperationsRestAPI()
        cls.iam_obj = iam_test_lib.IamTestLib()
        resp = system_utils.path_exists(S3_CFG["aws_config_path"])
        assert_utils.assert_true(
            resp, "config path not exists: {}".format(
                S3_CFG["aws_config_path"]))
        cls.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        cls.log.info("ENDED: setup test suite operations.")

    # pylint: disable=attribute-defined-outside-init
    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """Function to perform the setup ops for each test."""
        self.log.info("STARTED: setup method operations")
        self.account_name = "seagate_account_{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.user_name = "seagate_user{}".format(time.perf_counter_ns())
        self.s3_accounts_list = list()
        self.iam_obj_list = list()
        self.log.info("ENDED: setup method operations")
        yield
        self.log.info("STARTED: Teardown Operations")
        self.iam_obj_list.append(self.iam_obj)
        for iam_obj in self.iam_obj_list:
            usr_list = iam_obj.list_users()[1]
            all_users = [usr["UserName"] for usr in usr_list]
            if all_users:
                resp = iam_obj.delete_users_with_access_key(all_users)
                assert_utils.assert_true(resp, "Failed to Delete IAM users")
        for acc in self.s3_accounts_list:
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], f"Failed to delete s3 users: {resp}")
        self.log.info("ENDED: Test teardown Operations.")

    def create_account(self):
        """Function will create s3 account."""
        self.log.info("Account name: %s, Account email: %s", self.account_name, self.email_id)
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_password)
        assert_utils.assert_true(resp[0], resp)
        self.s3_accounts_list.append(self.account_name)

        return resp

    def create_user_and_access_key(self, user_name, password, iam_obj, pwd_reset=False):
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
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created a user with name %s", user_name)
        self.log.info("Creating login profile for user %s", user_name)
        resp = iam_obj.create_user_login_profile(
            user_name, password, pwd_reset)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created login profile for user %s", user_name)
        self.log.info("Creating access key for user %s", user_name)
        resp = iam_obj.create_access_key(user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created access key for user %s", user_name)
        access_key = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        return access_key, secret_key

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7166")
    @CTFailOn(error_handler)
    def test_update_user_2419(self):
        """Update User using aws iam. Duplicate of TEST-2077."""
        self.log.info("STARTED: Update User using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        resp = new_iam_obj.create_user_login_profile(
            self.user_name,
            S3_BLKBOX_CFG["password"],
            True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        self.log.info("Step 2: Updating user name of already existing user")
        resp = new_iam_obj.update_user(
            "iamusertest2419", self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Updated user name of already existing user")
        self.log.info(
            "Step 3: Listing users and verifying user name is updated")
        resp = new_iam_obj.list_users()
        self.log.info("User: %s", resp[1])
        assert_utils.assert_true(resp[0], resp[1])
        all_users = resp[1]
        iam_users_list = ["iamusertest2419"
                          for user in all_users if
                          "iamusertest2419" in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_utils.assert_in("iamusertest2419", iam_users_list)
        self.log.info("Step 3: Listed users and verified user name is updated")
        self.log.info("ENDED: Update User using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7167")
    @CTFailOn(error_handler)
    def test_list_user_2420(self):
        """list user using aws iam. Duplicate of TEST-2078."""
        self.log.info(
            "STARTED: list user using aws iam")
        self.log.info("Step 1: Create new account and new user in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info(
            "Step 2: Listing users and verifying user name present")
        all_users = new_iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        iam_users_list = [user["UserName"]
                          for user in all_users if
                          "seagate_user" in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_utils.assert_list_equal([self.user_name], iam_users_list)
        self.log.info("Step 2: Listed users and verified user name is present")
        self.log.info("ENDED: list user using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7168")
    def test_del_user_2421(self):
        """Delete User using aws iam. Duplicate of TEST-2079."""
        self.log.info(
            "STARTED: Delete User using aws iam")
        self.log.info("Step 1: Create new account and new user in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        self.log.info("Step 1: Created new account and new user in it")
        resp = new_iam_obj.delete_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        all_users = new_iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        iam_users_list = [self.user_name
                          for user in all_users if
                          self.user_name == user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_utils.assert_not_in(self.user_name, iam_users_list,
                                   f"{self.user_name} is not deleted successfully")
        self.log.info("ENDED: Delete User using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7169")
    @CTFailOn(error_handler)
    def test_create_100_users_per_account_2422(self):
        """Create 100 Users per account using aws iam. Duplicate of TEST-2080."""
        self.log.info(
            "STARTED: Create 100 Users per account using aws iam")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        self.iam_obj_list.append(new_iam_obj)
        self.log.debug(
            "Creating %s users", 100)
        for num in range(100):
            new_user_name = "{0}{1}".format("iamuser2422", "_{}".format(num))
            self.log.debug(
                "Creating a user with name: %s", new_user_name)
            resp = new_iam_obj.create_user(new_user_name)
            assert_utils.assert_true(resp[0], resp[1])
        all_users = new_iam_obj.list_users()[1]
        assert_utils.assert_true(
            len(all_users) >= 100, f"Failed to create 100 users: {len(all_users)}")
        self.log.info("ENDED: Create 100 Users per account using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7170")
    @CTFailOn(error_handler)
    def test_list_accesskeys_2425(self):
        """List accesskeys for the user using aws iam. Duplicate of TEST-2083."""
        self.log.info("STARTED: list accesskeys for the user using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        self.new_access_key = resp[1]["access_key"]
        self.new_secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=self.new_access_key,
            secret_key=self.new_secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        resp = new_iam_obj.create_user_login_profile(
            self.user_name,
            S3_BLKBOX_CFG["password"],
            True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        self.log.info("Creating access key for user %s",
                      self.user_name)
        resp = new_iam_obj.create_access_key(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Created access key for user %s",
            self.user_name)
        resp = new_iam_obj.list_access_keys(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: list accesskeys for the user using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7171")
    @CTFailOn(error_handler)
    def test_delete_accesskeys_2426(self):
        """Delete Accesskey of a user using aws iam. Duplicate of TEST-2084."""
        self.log.info("STARTED: Delete Accesskey of a user using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = self.create_user_and_access_key(
            self.user_name, S3_BLKBOX_CFG["password"], new_iam_obj)
        user_access_key = resp[0]
        self.iam_obj_list.append(new_iam_obj)
        resp = new_iam_obj.delete_access_key(self.user_name, user_access_key)
        assert_utils.assert_true(resp[0], f"Failed to delete access key. Response: {resp}")
        self.log.info("ENDED: Delete Accesskey of a user using aws iam %s", resp)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7172")
    @CTFailOn(error_handler)
    def test_create_accesskey_2424(self):
        """Create Access key to the user using aws iam. Duplicate of TEST-2082."""
        self.log.info("STARTED: Create Access key to the user using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        resp = new_iam_obj.create_user_login_profile(
            self.user_name,
            S3_BLKBOX_CFG["password"],
            True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        self.log.info(
            "Step 2: Creating access key for user %s",
            self.user_name)
        resp = new_iam_obj.create_access_key(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Created access key for user %s",
            self.user_name)
        resp = new_iam_obj.list_access_keys(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Create Access key to the user using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7173")
    @CTFailOn(error_handler)
    def test_create_new_user_2418(self):
        """Create new user for current Account AWS IAM. Duplicate of TEST-2076."""
        self.log.info(
            "STARTED: Create new user for current Account AWS IAM")
        self.log.info("Step 1: Create new account and new user in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info(
            "Step 2: Listing users and verifying user name present")
        all_users = new_iam_obj.list_users()[1]
        self.log.debug("all_users %s", all_users)
        iam_users_list = [self.user_name
                          for user in all_users if
                          self.user_name in user["UserName"]]
        self.log.debug("IAM users: %s", iam_users_list)
        assert_utils.assert_list_item(iam_users_list, self.user_name)
        self.log.info("Step 2: Listed users and verified user name is present")
        self.log.info("ENDED: Create new user for current Account AWS IAM")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7191")
    @CTFailOn(error_handler)
    def test_create_user_existing_name_2423(self):
        """Creating user with existing name With AWS IAM client. Duplicate of TEST-2081."""
        self.log.info(
            "STARTED: creating user with existing name With AWS IAM client")
        self.log.info("Step 1: Create new account")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info(
            "Step 1: Creating user with name %s with access_key %s and secret_key %s ",
            self.user_name, access_key, secret_key)
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        self.log.info("Step 1: Created user with name %s", self.user_name)
        self.log.info("Step 2: Creating user with existing name %s", self.user_name)
        try:
            resp = new_iam_obj.create_user(self.user_name)
            assert_utils.assert_false(resp[0], "EntityAlreadyExists")
        except CTException as error:
            self.log.error("EntityAlreadyExists: %s", error.message)
            assert_utils.assert_in("EntityAlreadyExists", error.message, error.message)
            self.log.info("Step 2: Could not create user with existing name %s", self.user_name)
        self.log.info("ENDED: creating user with existing name With AWS IAM client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7174")
    @CTFailOn(error_handler)
    def test_update_accesskey_2427(self):
        """Update Accesskey of a user with active mode using aws iam. Duplicate of TEST-2085."""
        self.log.info(
            "STARTED: Update Accesskey of a user with active mode using aws iam")
        self.log.info(
            "Step 1: Creating a new account with name %s",
            self.account_name)
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        self.log.info(
            "Step 1: Created a new account with name %s", self.account_name)
        self.log.info(
            "Step 3: Creating a user with name %s", self.user_name)
        resp = iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(iam_obj)
        self.log.info(
            "Step 3: Created a user with name %s", self.user_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(self.user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updating access key of user")
        resp = iam_obj.update_access_key(access_key_to_update, "Active", self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updated access key of user")
        self.log.info("Step 6: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        self.log.debug("Accesskey ID: %s, Accesskey status: %s", new_access_key, status)
        assert_utils.assert_equal(new_access_key, access_key_to_update, resp[1])
        assert_utils.assert_equal(status, "Active", resp[1])
        self.log.info(
            "Step 6: Verified that access key of user is updated successfully")
        self.log.info(
            "ENDED: Update Accesskey of a user with active mode using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7175")
    @CTFailOn(error_handler)
    def test_update_accesskey_userinactive_2428(self):
        """Update accesskey of a user with inactive mode using aws iam. Duplicate of TEST-2086."""
        self.log.info(
            "STARTED: update accesskey of a user with inactive mode using aws iam")
        self.log.info(
            "Step 1: Creating a new account with name %s",
            self.account_name)
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        self.log.info(
            "Step 1: Created a new account with name %s", self.account_name)
        self.log.info("Step 3: Creating a user with name %s", self.user_name)
        resp = iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(iam_obj)
        self.log.info("Step 3: Created a user with name %s", self.user_name)
        self.log.info("Step 4: Creating access key for the user")
        resp = iam_obj.create_access_key(self.user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updating access key of user")
        resp = iam_obj.update_access_key(access_key_to_update, "Inactive", self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Updated access key of user")
        self.log.info("Step 6: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        self.log.debug("Accesskey ID: %s, Accesskey status: %s", new_access_key, status)
        assert_utils.assert_equal(new_access_key, access_key_to_update, resp[1])
        assert_utils.assert_equal(status, "Inactive", resp[1])
        self.log.info(
            "Step 6: Verified that access key of user is updated successfully")
        self.log.info(
            "ENDED: update access key of a user with inactive mode using aws iam")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7176")
    @CTFailOn(error_handler)
    def test_create_accesskey_existinguser_2429(self):
        """Create access key key with existing user name using aws iam. Duplicate of TEST-2087."""
        self.log.info(
            "STARTED: create access key key with existing user name using aws iam")
        self.log.info(
            "Step 1: Create new account and new user and new profile in it")
        resp = self.create_account()
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        new_iam_obj = iam_test_lib.IamTestLib(
            access_key=access_key,
            secret_key=secret_key)
        resp = new_iam_obj.create_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.iam_obj_list.append(new_iam_obj)
        resp = new_iam_obj.create_user_login_profile(
            self.user_name,
            S3_BLKBOX_CFG["password"],
            True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created new account and new user and new profile in it")
        for _ in range(2):
            self.log.info(
                "Step 2: Creating access key for user %s",
                self.user_name)
            resp = new_iam_obj.create_access_key(self.user_name)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info(
                "Step 2: Created access key for user %s",
                self.user_name)
            resp = new_iam_obj.list_access_keys(self.user_name)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: create access key with existing user name using aws iam")
