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
"""This file contains test related to deleting account temp credentials"""

import time
import logging
import pytest
from libs.s3 import s3_test_lib, iam_test_lib
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.assert_utils import \
    assert_true, assert_in, assert_equal, assert_not_in

LOGGER = logging.getLogger(__name__)
IAM_TEST_OBJ = iam_test_lib.IamTestLib()
CMN_CONF = read_yaml("config/common_config.yaml")[1]
TEST_CONFIG = read_yaml("config/s3/test_delete_account_temp_cred.yaml")[1]
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD

class TestDeleteAccountTempCred():
    """Delete Account Temp Cred Testsuite."""

    cfg = TEST_CONFIG["delete_account_temp_cred"]

    def create_acnt_and_login_profile(self, account_name, email_id):
        """
        This function will create an IAM account with specified name and login profile for account.

        :param str account_name: Name of an account to be created
        :param str email_id: Email id for account creation
        :return: None
        """
        LOGGER.info(
            "Step 1: Creating an account with name %s", account_name)
        acc_create = IAM_TEST_OBJ.create_account_s3iamcli(
            account_name, email_id, self.ldap_user, self.ldap_pwd)
        assert_true(acc_create[0], acc_create[1])
        LOGGER.info(
            "Step 1: Created an account with name %s", account_name)
        LOGGER.info("Step 2: Listing accounts to verify account is created")
        acc_list = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_true(acc_list[0], acc_list[1])
        all_accounts = [acc["AccountName"] for acc in acc_list[1]]
        assert_in(
            account_name,
            all_accounts,
            self.cfg["acc_create_failed_msg"])
        LOGGER.info("Step 2: Verified that account is created")
        LOGGER.info(
            "Step 3: Creating a login profile for an account %s", account_name)
        acc_profile = IAM_TEST_OBJ.create_account_login_profile_s3iamcli(
            account_name,
            self.cfg["password"],
            acc_create[1]["access_key"],
            acc_create[1]["secret_key"],
            password_reset=self.cfg["password_reset"])
        assert_true(acc_profile[0], acc_profile[1])
        LOGGER.info(
            "Step 3: Created a login profile for an account %s", account_name)

    def get_temp_creds(self, account_name, account_password, duration=None):
        """
        This function will retrieve temporary credentials such as access key,
        secret key and session token for specified account.

        :param str account_name: Name of account whose temp creds to be retrieved.
        :param str account_password: Account password.
        :param int duration: Time duration for which temp creds are valid.
        :return: The temp credentials of the specified account.
        :rtype: Dict
        """
        LOGGER.info(
            "Step 4: Retrieving temporary credentials for the account %s",
            account_name)
        self.temp_creds = dict()
        temp_creds = IAM_TEST_OBJ.get_temp_auth_credentials_account(
            account_name, account_password, duration=duration)
        assert_true(temp_creds[0], temp_creds[1])
        self.temp_creds["access_key"] = temp_creds[1]["access_key"]
        self.temp_creds["secret_key"] = temp_creds[1]["secret_key"]
        self.temp_creds["session_token"] = temp_creds[1]["session_token"]
        LOGGER.info(
            "Step 4: Retrieved temporary credentials for the account %s",
            self.account_name)

    def setup_method(self):
        """
        This function will be invoked prior each test case.

        It will perform all prerequisite steps required for test execution.
        It will create an IAM account and create an account login profile for that
        account.
        """
        LOGGER.info("STARTED: Setup operations")
        self.ldap_user = LDAP_USERNAME
        self.ldap_pwd = LDAP_PASSWD
        self.account_name = "{0}{1}".format(
            self.cfg["account_name"], str(int(time.time())))
        self.email_id = self.cfg["email_id"].format(self.account_name)
        self.create_acnt_and_login_profile(self.account_name, self.email_id)
        LOGGER.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.

        It will perform clean up activities such as deleting an IAM accounts.
        """
        LOGGER.info("STARTED: Teardown operations")
        all_accounts = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        my_accounts = [acc["AccountName"]
                       for acc in all_accounts if self.cfg["account_name"] in acc["AccountName"]]
        LOGGER.info(my_accounts)
        if my_accounts:
            resp = IAM_TEST_OBJ.reset_account_access_key_s3iamcli(
                self.account_name, self.ldap_user, self.ldap_pwd)
            assert_true(resp[0], resp[1])
            access_key = resp[1]["AccessKeyId"]
            secret_key = resp[1]["SecretKey"]
            s3_temp_obj = s3_test_lib.S3TestLib(
                access_key=access_key, secret_key=secret_key)
            test_buckets = s3_temp_obj.bucket_list()[1]
            LOGGER.debug(test_buckets)
            if test_buckets:
                LOGGER.info("Deleting all buckets...")
                resp = s3_temp_obj.delete_all_buckets()
                assert_true(resp[0], resp[1])
                LOGGER.info("Deleted all buckets")
            LOGGER.info("Deleting IAM accounts...")
            for acc in my_accounts:
                resp = IAM_TEST_OBJ.reset_access_key_and_delete_account_s3iamcli(
                    acc)
                assert_true(resp[0], resp[1])
        LOGGER.info("Deleted accounts successfully")
        LOGGER.info("ENDED: Teardown operations")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6208")
    @CTFailOn(error_handler)
    def test_4518(self):
        """Delete account with valid temp credentials."""
        LOGGER.info("STARTED: Delete account with valid temp credentials")
        self.get_temp_creds(self.account_name, self.cfg["password"])
        LOGGER.info("Step 5: Deleting account using temporary credentials")
        resp = IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
            self.account_name,
            self.temp_creds["access_key"],
            self.temp_creds["secret_key"],
            self.temp_creds["session_token"])
        assert_true(resp[0], resp[1])
        LOGGER.info(resp[1])
        LOGGER.info(
            "Step 5: Deleted account using temporary credentials successfully")
        LOGGER.info(
            "Step 6: Listing accounts to check if account is deleted")
        resp = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_true(resp[0], resp[1])
        all_accounts = [acc["AccountName"] for acc in resp[1]]
        assert_not_in(self.account_name, all_accounts, resp[1])
        LOGGER.info("Step 6: Verified that account is deleted successfully")
        LOGGER.info("ENDED: Delete account with valid temp credentials")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6207")
    @CTFailOn(error_handler)
    def test_4519(self):
        """Delete account with invalid temp credentials."""
        LOGGER.info("STARTED: Delete account with invalid temp credentials")
        test_4519_cfg = TEST_CONFIG["test_4519"]
        self.get_temp_creds(self.account_name, self.cfg["password"])
        LOGGER.info("Step 5: Deleting account using invalid credentials")
        try:
            IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
                self.account_name,
                test_4519_cfg["temp_access_key"],
                test_4519_cfg["temp_secret_key"],
                test_4519_cfg["temp_session_token"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4519_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 5: Deleting account using invalid credentials failed with %s",
            test_4519_cfg["err_message"])
        LOGGER.info("ENDED: Delete account with invalid temp credentials")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6206")
    @CTFailOn(error_handler)
    def test_4520(self):
        """Delete non existing account with temp credentials.."""
        LOGGER.info(
            "STARTED: Delete non existing account with temp credentials.")
        test_4520_cfg = TEST_CONFIG["test_4520"]
        LOGGER.info(
            "Step 4: Deleting non existing account with temp credentials.")
        try:
            IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
                test_4520_cfg["account_name"],
                test_4520_cfg["temp_access_key"],
                test_4520_cfg["temp_secret_key"],
                test_4520_cfg["temp_session_token"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4520_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 4: Deleting non existing account with temp credentials failed with %s",
                test_4520_cfg["err_message"])
        LOGGER.info(
            "ENDED: Delete non existing account with temp credentials.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6205")
    @CTFailOn(error_handler)
    def test_4521(self):
        """
        Delete account after 20 mins using temp credentials with expire time limit,
        Note:-There is time limit for duration like example [1 hour].
        """
        LOGGER.info(
            "STARTED: Delete account after 20 mins using temp credentials with expire time limit.")
        test_4521_cfg = TEST_CONFIG["test_4521"]
        self.get_temp_creds(
            self.account_name,
            self.cfg["password"],
            duration=test_4521_cfg["time_duration"])
        time.sleep(test_4521_cfg["time_duration"])
        LOGGER.info(
            "Step 5: Deleting account %s using temporary credentials after expiry of time limit",
                self.account_name)
        try:
            IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
                self.account_name,
                self.temp_creds["access_key"],
                self.temp_creds["secret_key"],
                self.temp_creds["session_token"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4521_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 5: Deleting account using temporary credentials after"
            " expiry of time limit failed with %s",
            test_4521_cfg["err_message"])
        LOGGER.info(
            "ENDED: Delete account after 20 mins using temp credentials with expire time limit.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6204")
    @CTFailOn(error_handler)
    def test_4522(self):
        """Perform S3 operations using deleted account temp credentials."""
        LOGGER.info(
            "STARTED: Perform S3 operations using deleted account temp credentials")
        test_4522_cfg = TEST_CONFIG["test_4522"]
        self.get_temp_creds(self.account_name, self.cfg["password"])
        LOGGER.info(
            "Step 5: Deleting an account using temporary credentials")
        resp = IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
            self.account_name,
            self.temp_creds["access_key"],
            self.temp_creds["secret_key"],
            self.temp_creds["session_token"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 5: Deleted an account using temporary credentials successfully")
        LOGGER.info(
            "Step 6: Verifying that account is deleted using temporary credentials")
        resp = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_true(resp[0], resp[1])
        all_accounts = [acc["AccountName"] for acc in resp[1]]
        assert_not_in(self.account_name, all_accounts, resp[1])
        LOGGER.info(
            "Step 6: Verified that account is deleted using temporary credentials")
        s3_temp_test_obj = s3_test_lib.S3TestLib(
            access_key=self.temp_creds["access_key"],
            secret_key=self.temp_creds["secret_key"],
            aws_session_token=self.temp_creds["session_token"])
        LOGGER.info(
            "Step 7: Creating a bucket using temp credentials of a deleted account")
        try:
            s3_temp_test_obj.create_bucket(test_4522_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4522_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 7: Creating a bucket using temp credentials of a deleted account failed with %s",
                test_4522_cfg["err_message"])
        LOGGER.info(
            "ENDED: Perform S3 operations using deleted account temp credentials")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6203")
    @CTFailOn(error_handler)
    def test_4523(self):
        """Delete account using temp cred where that account recently got deleted."""
        LOGGER.info(
            "STARTED: Delete account using temp cred where that account recently got deleted")
        test_4523_cfg = TEST_CONFIG["test_4523"]
        self.get_temp_creds(self.account_name, self.cfg["password"])
        LOGGER.info(
            "Step 5: Deleting account using temporary credentials of an account %s",
                self.account_name)
        resp = IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
            self.account_name,
            self.temp_creds["access_key"],
            self.temp_creds["secret_key"],
            self.temp_creds["session_token"])
        assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 5: Deleting account using temporary credentials of an account %s",
                self.account_name)
        LOGGER.info(
            "Step 6: Verifying that account is deleted by listing accounts")
        resp = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)
        assert_true(resp[0], resp[1])
        all_accounts = [acc["AccountName"] for acc in resp[1]]
        assert_not_in(self.account_name, all_accounts, resp[1])
        LOGGER.info(
            "Step 6: Verified that account is deleted by listing accounts")
        LOGGER.info(
            "Step 7: Deleting account using temp credentials of deleted account")
        try:
            IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
                self.account_name,
                self.temp_creds["access_key"],
                self.temp_creds["secret_key"],
                self.temp_creds["session_token"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4523_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 7: Deleting account using temp credentials of deleted account failed with %s",
                test_4523_cfg["err_message"])
        LOGGER.info(
            "ENDED: Delete account using temp cred where that account recently got deleted")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6202")
    @CTFailOn(error_handler)
    def test_4525(self):
        """Perform S3 operations using expired temp credentials."""
        LOGGER.info(
            "STARTED: Perform S3 operations using expired temp credentials")
        test_4525_cfg = TEST_CONFIG["test_4525"]
        self.get_temp_creds(
            self.account_name,
            self.cfg["password"],
            duration=test_4525_cfg["time_duration"])
        time.sleep(test_4525_cfg["time_duration"])
        LOGGER.info(
            "Step 5: Creating a bucket using expired temporary credentials")
        s3_temp_test_obj = s3_test_lib.S3TestLib(
            access_key=self.temp_creds["access_key"],
            secret_key=self.temp_creds["secret_key"],
            aws_session_token=self.temp_creds["session_token"])
        try:
            s3_temp_test_obj.create_bucket(test_4525_cfg["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4525_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 5: Creating a bucket using expired temporary credentials failed with %s",
                test_4525_cfg["err_message"])
        LOGGER.info(
            "ENDED: Perform S3 operations using expired temp credentials")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6201")
    @CTFailOn(error_handler)
    def test_4526(self):
        """
        Delete account after 1 hour using temp credentials with expire time limit,
        Note:-There is time limit for duration like example [1 hour].
        """
        LOGGER.info(
            "STARTED: Delete account after 1 hour using temp credentials with expire time limit.")
        test_4526_cfg = TEST_CONFIG["test_4526"]
        try:
            self.get_temp_creds(
                self.account_name,
                self.cfg["password"],
                duration=test_4526_cfg["time_duration"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4526_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 4: Retrieving temporary credentials for the account failed with %s",
                test_4526_cfg["err_message"])
        LOGGER.info(
            "ENDED: Delete account after 1 hour using temp credentials with expire time limit.")

    @pytest.mark.s3
    @pytest.mark.tags("TEST-6200")
    @CTFailOn(error_handler)
    def test_4692(self):
        """Delete account forcefully using temp cred where that account contains some Resource."""
        LOGGER.info(
            "STARTED: Delete account forcefully using temp credentials "
            "where that account contains some Resource")
        test_4692_cfg = TEST_CONFIG["test_4692"]
        self.get_temp_creds(self.account_name, self.cfg["password"])
        s3_temp_obj = s3_test_lib.S3TestLib(
            access_key=self.temp_creds["access_key"],
            secret_key=self.temp_creds["secret_key"],
            aws_session_token=self.temp_creds["session_token"])
        LOGGER.info("Step 5: Creating a bucket using temp credentials")
        resp = s3_temp_obj.create_bucket(test_4692_cfg["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(test_4692_cfg["bucket_name"], resp[1], resp[1])
        LOGGER.info("Step 5: Created a bucket using temp credentials")
        LOGGER.info(
            "Step 6: Deleting an account forcefully using temp credentials")
        try:
            IAM_TEST_OBJ.delete_account_s3iamcli_using_temp_creds(
                self.account_name,
                self.temp_creds["access_key"],
                self.temp_creds["secret_key"],
                self.temp_creds["session_token"])
        except CTException as error:
            LOGGER.error(error.message)
            assert_in(
                test_4692_cfg["err_message"],
                error.message,
                error.message)
        LOGGER.info(
            "Step 6: Deleting an account forcefully using temp credentials failed with %s",
                test_4692_cfg["err_message"])
        LOGGER.info(
            "ENDED: Delete account forcefully using temp credentials "
            "where that account contains some Resource")
