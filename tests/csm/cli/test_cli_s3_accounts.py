#!/usr/bin/python
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
#
"""Test suite for S3 account operations"""

import logging
import time
import pytest
from commons import commands
from commons import constants
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from config import CSM_CFG
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations


class TestCliS3ACC:
    """CORTX CLI Test suite for S3 account operations"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("STARTED : Setup operations at test suit level")
        cls.s3acc_obj = CortxCliS3AccountOperations()
        cls.s3acc_obj.open_connection()
        cls.s3bkt_obj = CortxCliS3BucketOperations(session_obj=cls.s3acc_obj.session_obj)
        cls.csm_user_obj = CortxCliCsmUser(session_obj=cls.s3acc_obj.session_obj)
        cls.iam_user_obj = CortxCliIamUser(session_obj=cls.s3acc_obj.session_obj)
        cls.alert_obj = CortxCliAlerts(session_obj=cls.s3acc_obj.session_obj)
        cls.s3acc_prefix = "cli_s3acc"
        cls.s3acc_name = cls.s3acc_prefix
        cls.s3acc_email = "{}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.logger.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.logger.info("STARTED : Setup operations at test function level")
        self.s3acc_name = "{}_{}".format(self.s3acc_name, int(time.time()))
        self.s3acc_email = self.s3acc_email.format(self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.logger.info("STARTED : Teardown operations at test function level")
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
            self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            self.s3acc_obj.logout_cortx_cli()
        self.logger.info("ENDED : Teardown operations at test function level")

    @classmethod
    def teardown_class(cls):
        """
        Teardown any state that was previously setup with a setup_class
        """
        cls.logger.info("STARTED : Teardown operations at test suit level")
        cls.s3acc_obj.close_connection()
        cls.logger.info("ENDED : Teardown operations at test suit level")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10872")
    @CTFailOn(error_handler)
    def test_1008_delete_s3_account(self):
        """
        Verify that S3 account should be deleted successfully on executing delete command
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted s3 account %s", self.s3acc_name)

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10877")
    @CTFailOn(error_handler)
    def test_1012_delete_diff_acc(self):
        """
        Verify that appropriate error msg should be returned when s3 account tries to
        delete different s3 account
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        s3acc_name2 = "cli_s3acc_{}".format(int(time.time()))
        s3acc_email2 = "{}@seagate.com".format(s3acc_name2)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name2,
            account_email=s3acc_email2,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created another s3 account %s", s3acc_name2)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name=s3acc_name2)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Access denied")
        self.logger.info(
            "Deleting different account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10869")
    @CTFailOn(error_handler)
    def test_1003_create_acc_invalid_passwd(self):
        """
        Test that appropriate error should be returned when CSM user/admin enters invalid password
        while creating S3 account
        """
        dummy_pwd = "seagate"
        error_msg = "Password Policy Not Met"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=dummy_pwd)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Creating S3 account with invalid password failed with error %s",
            resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10870")
    @CTFailOn(error_handler)
    def test_1005_create_duplicate_acc(self):
        """
        Test that appropriate error should be thrown when CSM user/admin tries to
        create duplicate S3 user
        """
        error_msg = "attempted to create an account that already exists"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Creating duplicate S3 account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10871")
    @CTFailOn(error_handler)
    def test_1007_list_acc_invalid_format(self):
        """
        Verify that error msg is returned when command to list s3 users contains
        incorrect/invalid format
        """
        output_format = "text"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        error_msg = " invalid choice: '{}'".format(output_format)
        resp = self.s3acc_obj.show_s3account_cortx_cli(output_format=output_format)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Listing S3 accounts with invalid format failed with error %s",
            resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10873")
    @CTFailOn(error_handler)
    def test_1009_no_on_deletion(self):
        """
        Verify that s3 account is not deleted when user selects "no" on confirmation
        :avocado: tags=s3_account_user_cli
        """
        delete_s3acc_cmd = "s3accounts delete {}".format(self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info("Logging into CORTX CLI as %s", self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info("Deleting s3 account %s", self.s3acc_name)
        response = self.s3acc_obj.execute_cli_commands(cmd=delete_s3acc_cmd, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.s3acc_obj.execute_cli_commands(cmd="n", patterns=["cortxcli"])
        assert_utils.assert_equals(True, response[0], response[1])
        resp = self.s3acc_obj.show_s3account_cortx_cli()
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info(
            "Verified that account is not deleted with 'no' on confirmation")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10874")
    @CTFailOn(error_handler)
    def test_1010_delete_multiple_acc(self):
        """
        verify that appropriate error should be returned when S3 account user try to
        delete different multiple s3 accounts simultaneously
        """
        dummy_acc1 = "cli_s3acc_{}".format(int(time.time()))
        dummy_acc2 = "cli_s3acc_{}".format(int(time.time()))
        error_msg = "Access denied"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info("Logging into CORTX CLI as %s", self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Performing simultaneous delete operation without mentioning currently \
            logged in s3account")
        acc_names = " ".join([dummy_acc1, dummy_acc2])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc_names)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Performing simultaneous delete operation without mentioning currently logged \
            in s3 account user failed with error %s", resp[1])
        self.logger.info(
            "Performing simultaneous delete operation with currently logged in s3 account")
        acc_names = " ".join([self.s3acc_name, dummy_acc1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=acc_names)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted s3 account %s", self.s3acc_name)

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10875")
    @CTFailOn(error_handler)
    def test_1011_delete_invalid_acc(self):
        """
        Verify that appropriate error msg should be returned when command to delete s3 user contains
        incorrect/invalid account_name
        """
        dummy_acc = "cli_s3acc_{}".format(int(time.time()))
        error_msg = "Access denied"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info("Logging into CORTX CLI as %s", self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name=dummy_acc)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Performing delete operation with invalid s3 account name is failed with error %s",
            resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10881")
    @CTFailOn(error_handler)
    def test_1144_acc_login_with_param(self):
        """
        Test that S3 account is able to login to csmcli passing username as parameter
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI with username as parameter as %s",
            self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password,
            username_param=self.s3acc_name)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged into CORTX CLI by passing username as parameter")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10883")
    @CTFailOn(error_handler)
    def test_1147_s3_acc_login(self):
        """
        Test that s3 account, csm admin and csm user can login to csm interactive session
        without passing username as direct parameter in command
        """
        csm_user_name = "{0}{1}".format("auto_csm_user", str(int(time.time())))
        csm_user_email = "{0}{1}".format(csm_user_name, "@seagate.com")
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.logger.info("Creating csm user with name %s", csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="manage",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_equals(
            True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", csm_user_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info("Logging into CORTX CLI as s3 account %s", self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as s3 account %s",
            self.s3acc_name)
        self.logger.info("Logging into CORTX CLI as csm user %s", csm_user_name)
        login = self.csm_user_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10885")
    @CTFailOn(error_handler)
    def test_1916_update_acc_passwd(self):
        """
        Test s3 account user can update his password through csmcli
        """
        new_password = CSM_CFG["CliConfig"]["csm_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=new_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as s3 account %s with new password",
            self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=new_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as s3 account %s with new password",
            self.s3acc_name)
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted s3 account %s", self.s3acc_name)

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10887")
    @CTFailOn(error_handler)
    def test_4428_delete_acc_with_buckets(self):
        """
        Test that appropriate error should be returned when s3 account user try to delete
        s3 account containing buckets
        """
        bucket_name = "{0}{1}".format("clis3bkt", int(time.time()))
        error_msg = "Account cannot be deleted as it owns some resources"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3bkt_obj.create_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", bucket_name)
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Deleting s3 account failed with error %s", resp[1])
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted bucket %s", bucket_name)

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10888")
    @CTFailOn(error_handler)
    def test_6219_create_duplicate_acc_name(self):
        """
        Test that duplicate users should not be created between csm users
        and s3 account users in CSM CLI
        """
        error_msg = "name already exists"
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=self.s3acc_name,
            email_id=self.s3acc_email,
            role="manage",
            password=self.s3acc_password,
            confirm_password=self.s3acc_password)
        assert_utils.assert_equals(
            True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Creating s3 account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10889")
    @CTFailOn(error_handler)
    def test_1006_list_account_with_format(self):
        """
        Verify that list of all existing S3 accounts should be returned in given <format>
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.show_s3account_cortx_cli(output_format="table")
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info("Successfully listed S3 accounts in table format")
        resp = self.s3acc_obj.show_s3account_cortx_cli(output_format="json")
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info("Successfully listed S3 accounts in json format")
        resp = self.s3acc_obj.show_s3account_cortx_cli(output_format="xml")
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info("Successfully listed S3 accounts in xml format")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10890")
    @CTFailOn(error_handler)
    def test_1918_different_confirm_password(self):
        """
        Test that error should be returned when s3 user enters different passwords in
        both password and confirm password
        """
        error_msg = "password do not match"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password,
            confirm_password=CSM_CFG["CliConfig"]["csm_user"]["password"])
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Creating s3 account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10891")
    @CTFailOn(error_handler)
    def test_1919_reset_password_incorrect_name(self):
        """
        Test that error should be returned when s3 user enters incorrect account name
        while resetting account password
        """
        dummy_acc = "cli_s3acc_{}".format(int(time.time()))
        error_msg = "Access denied"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=dummy_acc, new_password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Update s3 account password failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10892")
    @CTFailOn(error_handler)
    def test_1920_no_on_update_password(self):
        """
        Test that password is not updated when user selects "NO" on update password confirmation
        """
        new_password = CSM_CFG["CliConfig"]["csm_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name,
            new_password=new_password,
            reset_password="n")
        assert_utils.assert_equals(False, resp[0], resp[1])
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Verified s3account password not updated when user selects 'No' on confirmation")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10893")
    @CTFailOn(error_handler)
    def test_1921_reset_invalid_password(self):
        """
        Test that new password should be of 8 characters long which consist
        atleast one lowercase, one uppercase, one nemeric and one special character
        """
        dummy_pwds = [
            "Sea@123",
            "seagate@123",
            "SEAGATE@123",
            "Seagate@",
            "Seagate123"]
        error_msg = "Password Policy Not Met"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        for pwd in dummy_pwds:
            resp = self.s3acc_obj.reset_s3account_password(
                account_name=self.s3acc_name, new_password=pwd)
            assert_utils.assert_equals(False, resp[0], resp[1])
            assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Update s3 account password failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11230")
    @CTFailOn(error_handler)
    def test_949_create_account_with_admin(self):
        """
        Verify that CSM Admin can create S3 account
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.show_s3account_cortx_cli()
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info(
            "Successfully verified that admin user can create S3 account")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-11231")
    @CTFailOn(error_handler)
    def test_882_perform_iam_operations(self):
        """
        Verify that only S3 account user must able
        to perform s3iamuser create/delete/show operations
        """
        iam_user_name = "{0}{1}".format("cli_iam_user", str(int(time.time())))
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.iam_user_obj.create_iam_user(user_name=iam_user_name,
                                            password=iam_user_pwd,
                                            confirm_password=iam_user_pwd)
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Created IAM user %s", iam_user_name)
        resp = self.iam_user_obj.list_iam_user()
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Listed IAM user %s", resp[1])
        resp = self.iam_user_obj.delete_iam_user(iam_user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.logger.info("Deleted IAM user %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-11748")
    @CTFailOn(error_handler)
    def test_1870_perform_bucket_operations(self):
        """
        Test that s3_account user can perform list, create, delete operation on buckets
        created by S3_account owner using CLI
        """
        bucket_name = "{0}{1}".format("clis3bkt", int(time.time()))
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3bkt_obj.create_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", bucket_name)
        resp = self.s3bkt_obj.list_buckets_cortx_cli()
        assert_utils.assert_exact_string(resp[1], bucket_name)
        self.logger.info("Listed buckets %s", resp[1])
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted buckets %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11233")
    @CTFailOn(error_handler)
    def test_4030_access_secret_key_on_login(self):
        """
        Verify that Secret key and access key should not be visible on login
        using s3 credentials on CSM Cli
        """
        key_var = ["Access Key", "Secret Key"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        result = all(key not in login[1] for key in key_var)
        assert_utils.assert_equals(True, result, login[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11741")
    @CTFailOn(error_handler)
    def test_1871_s3_account_help(self):
        """
        Test that s3_account user can only list commands using help (-h)
        to which the user has access to.
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.execute_cli_commands(cmd=commands.CMD_HELP_OPTION, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        for cmd in constants.S3ACCOUNT_HELP_CMDS:
            assert_utils.assert_exact_string(resp[1], cmd)
        self.logger.info("Successfully verified help response for s3 account")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11747")
    @CTFailOn(error_handler)
    def test_4031_perform_s3_operations(self):
        """
        Test User should able to perform s3 operations after login using s3 credentials on CSM Cli
        """
        bucket_name = "{0}{1}".format("clis3bkt", int(time.time()))
        iam_user_name = "{0}{1}".format("cli_iam_user", str(int(time.time())))
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])

        self.logger.info("Performing s3 bucket operations using s3 account")
        resp = self.s3bkt_obj.create_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", bucket_name)
        resp = self.s3bkt_obj.list_buckets_cortx_cli()
        assert_utils.assert_exact_string(resp[1], bucket_name)
        self.logger.info("Listed buckets %s", resp[1])
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted buckets %s", resp[1])

        self.logger.info("Performing IAM user operations using s3 account")
        resp = self.iam_user_obj.create_iam_user(user_name=iam_user_name,
                                            password=iam_user_pwd,
                                            confirm_password=iam_user_pwd)
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Created IAM user %s", iam_user_name)
        resp = self.iam_user_obj.list_iam_user()
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Listed IAM user %s", resp[1])
        resp = self.iam_user_obj.delete_iam_user(iam_user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.logger.info("Deleted IAM user %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11746")
    @CTFailOn(error_handler)
    def test_1866_csm_user_operations_with_account(self):
        """
        Test that s3_account user cannot perform list, update, create, delete
        operation on csm_users using CLI.
        """
        csm_user_opt = "'users'"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.execute_cli_commands(cmd=commands.CMD_HELP_OPTION, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        result = csm_user_opt in resp[1]
        assert_utils.assert_equals(False, result, resp[1])
        self.logger.info(
            "Verified csm user option is not available in s3 account help")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12844")
    @CTFailOn(error_handler)
    def test_1869_perform_iam_operations(self):
        """
        Test that s3_account user can perform list, create, delete operation on
        iam_users using CLI created by owner S3_account
        """
        iam_user_name = "{0}{1}".format("cli_iam_user", str(int(time.time())))
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.iam_user_obj.create_iam_user(user_name=iam_user_name,
                                            password=iam_user_pwd,
                                            confirm_password=iam_user_pwd)
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Created IAM user %s", iam_user_name)
        resp = self.iam_user_obj.list_iam_user()
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Listed IAM user %s", resp[1])
        resp = self.iam_user_obj.delete_iam_user(iam_user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.logger.info("Deleted IAM user %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13136")
    @CTFailOn(error_handler)
    def test_1868_non_supported_s3account_operations(self):
        """
        Test that s3_account user cannot perform delete (except owner)
        create operation on s3_accounts using CLI
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        s3acc_name2 = "cli_s3acc_{}".format(int(time.time()))
        s3acc_email2 = "{}@seagate.com".format(s3acc_name2)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name2,
            account_email=s3acc_email2,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created another s3 account %s", s3acc_name2)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name=s3acc_name2)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Access denied")
        self.logger.info(
            "Deleting different account failed with error %s", resp[1])
        s3acc_name3 = "cli_s3acc_{}".format(int(time.time()))
        s3acc_email3 = "{}@seagate.com".format(s3acc_name3)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name3,
            account_email=s3acc_email3,
            password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Creating s3 account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13139")
    @CTFailOn(error_handler)
    def test_1867_s3account_operations(self):
        """
        Test that s3_account user can perform list, update, delete operation on
        owner s3_accounts using CLI
        """
        new_password = CSM_CFG["CliConfig"]["csm_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.show_s3account_cortx_cli()
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info("Successfully listed S3 accounts %s", resp[1])
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=new_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info(
            "Successfully updated S3 accounts password to: %s",
            new_password)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=new_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted s3 account %s", self.s3acc_name)

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14033")
    @CTFailOn(error_handler)
    def test_1862_alert_operations_with_s3account(self):
        """
        Test that s3_account user cannot list, update alert using CLI
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        resp = self.alert_obj.show_alerts_cli(duration="5m")
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "List alert with s3 account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14033")
    @CTFailOn(error_handler)
    def test_1001_create_s3account_with_s3account(self):
        """
        Test that S3 user is not permitted to create S3 account
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        s3acc_name2 = "cli_s3acc_{}".format(int(time.time()))
        s3acc_email2 = "{}@seagate.com".format(s3acc_name2)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name2,
            account_email=s3acc_email2,
            password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Creating s3 account failed with error %s", resp[1])

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10879")
    @CTFailOn(error_handler)
    def test_1013_help_options(self):
        """
        Test that help opens on executing "-h" option with commands
        """
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        command_list = [
            commands.CMD_S3ACC,
            commands.CMD_CREATE_S3ACC]
        help_option_list = [
            constants.S3ACCOUNT_HELP,
            constants.S3ACC_CREATE_HELP]
        for command, help_options in zip(command_list, help_option_list):
            command = " ".join([command, commands.CMD_HELP_OPTION])
            resp = self.s3acc_obj.execute_cli_commands(cmd=command, patterns=["usage:"])
            assert_utils.assert_equals(True, resp[0], resp[1])
            for option in help_options:
                assert_utils.assert_exact_string(resp[1], option)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        command_list = [
            commands.CMD_SHOW_BUCKETS,
            commands.CMD_DELETE_S3ACC]
        help_option_list = [
            constants.S3ACC_SHOW_HELP,
            constants.S3ACC_DELETE_HELP]
        for command, help_options in zip(command_list, help_option_list):
            command = " ".join([command, commands.CMD_HELP_OPTION])
            resp = self.s3acc_obj.execute_cli_commands(cmd=command, patterns=["usage:"])
            assert_utils.assert_equals(True, resp[0], resp[1])
            for option in help_options:
                assert_utils.assert_exact_string(resp[1], option)
        self.logger.info(
            "Successfully verified help responses for all s3 account commands")
