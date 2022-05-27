#!/usr/bin/python
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
#
"""Test suite for S3 account operations"""

# pylint: disable=too-many-lines
import logging
import time
import pytest
from commons import commands
from commons import constants
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons import cortxlogging as log
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
        cls.s3acc_prefix = "cli_s3acc"
        cls.s3acc_name = cls.s3acc_prefix
        cls.s3acc_email = "{}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.start_log_format = "##### Test started -  "
        cls.end_log_format = "##### Test Ended -  "
        cls.logger.info("ENDED : Setup operations at test suit level")
        cls.s3acc_obj = None
        cls.s3acc_obj1 = None
        cls.s3bkt_obj = None
        cls.csm_user_obj = None
        cls.iam_user_obj = None
        cls.alert_obj = None
        cls.s3acc_name = None
        cls.s3acc_email = None
        cls.bucket_name = None
        cls.csm_user_name = None
        cls.csm_user_email = None
        cls.csm_user_pwd = None

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.logger.info("STARTED : Setup operations at test function level")
        self.s3acc_obj = CortxCliS3AccountOperations()
        self.s3acc_obj.open_connection()
        self.s3acc_obj1 = CortxCliS3AccountOperations()
        self.s3acc_obj1.open_connection()
        self.s3bkt_obj = CortxCliS3BucketOperations(
            session_obj=self.s3acc_obj.session_obj)
        self.csm_user_obj = CortxCliCsmUser(
            session_obj=self.s3acc_obj.session_obj)
        self.iam_user_obj = CortxCliIamUser(
            session_obj=self.s3acc_obj.session_obj)
        self.alert_obj = CortxCliAlerts(session_obj=self.s3acc_obj.session_obj)
        self.s3acc_name = f"{self.s3acc_name}_{int(time.time())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"clis3bkt{int(time.time())}"
        self.csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        self.csm_user_email = f"{self.csm_user_name}@seagate.com"
        self.csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
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
        self.logger.info(
            "STARTED : Teardown operations at test function level")
        self.s3acc_obj.logout_cortx_cli()
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        accounts = self.s3acc_obj.show_s3account_cortx_cli(output_format="json")[1]
        accounts = self.s3acc_obj.format_str_to_dict(
            input_str=accounts)["s3_accounts"]
        accounts = [acc["account_name"]
                    for acc in accounts if self.s3acc_prefix in acc["account_name"]]
        for acc in accounts:
            try:
                self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            except Exception as error:
                self.logger.error(error)
            finally:
                self.s3acc_obj.logout_cortx_cli()
        self.s3acc_obj.close_connection()
        self.logger.info("ENDED : Teardown operations at test function level")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10872")
    @CTFailOn(error_handler)
    def test_1008_delete_s3_account(self):
        """
        Verify that S3 account should be deleted successfully on executing delete command
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted s3 account %s", self.s3acc_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires» S3 Account login are unsupported")
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
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        s3acc_name2 = f"cli_s3acc_{int(time.time())}"
        s3acc_email2 = f"{s3acc_name2}@seagate.com"
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
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=s3acc_name2)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Access denied")
        self.logger.info(
            "Deleting different account failed with error %s", resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10869")
    @CTFailOn(error_handler)
    def test_1003_create_acc_invalid_passwd(self):
        """
        Test that appropriate error should be returned when CSM user/admin enters invalid password
        while creating S3 account
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        dummy_pwd = CSM_CFG["CliConfig"]["s3_account"]["invalid_password"]
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10870")
    @CTFailOn(error_handler)
    def test_1005_create_duplicate_acc(self):
        """
        Test that appropriate error should be thrown when CSM user/admin tries to
        create duplicate S3 user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10871")
    @CTFailOn(error_handler)
    def test_1007_list_acc_invalid_format(self):
        """
        Verify that error msg is returned when command to list s3 users contains
        incorrect/invalid format
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        output_format = "text"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        error_msg = f" invalid choice: '{output_format}'"
        resp = self.s3acc_obj.show_s3account_cortx_cli(
            output_format=output_format)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Listing S3 accounts with invalid format failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10873")
    @CTFailOn(error_handler)
    def test_1009_no_on_deletion(self):
        """
        Verify that s3 account is not deleted when user selects "no" on confirmation
        :avocado: tags=s3_account_user_cli
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        delete_s3acc_cmd = f"s3accounts delete {self.s3acc_name}"
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
        response = self.s3acc_obj.execute_cli_commands(
            cmd=delete_s3acc_cmd, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.s3acc_obj.execute_cli_commands(
                cmd="n", patterns=["cortxcli"])
        assert_utils.assert_equals(True, response[0], response[1])
        resp = self.s3acc_obj.show_s3account_cortx_cli()
        assert_utils.assert_exact_string(resp[1], self.s3acc_name)
        self.logger.info(
            "Verified that account is not deleted with 'no' on confirmation")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10874")
    @CTFailOn(error_handler)
    def test_1010_delete_multiple_acc(self):
        """
        verify that appropriate error should be returned when S3 account user try to
        delete different multiple s3 accounts simultaneously
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        dummy_acc1 = f"cli_s3acc_{int(time.time_ns())}"
        dummy_acc2 = f"cli_s3acc_{int(time.time_ns())}"
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
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=acc_names)
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10875")
    @CTFailOn(error_handler)
    def test_1011_delete_invalid_acc(self):
        """
        Verify that appropriate error msg should be returned when command to delete s3 user contains
        incorrect/invalid account_name
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        dummy_acc = f"cli_s3acc_{int(time.time())}"
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
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=dummy_acc)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Performing delete operation with invalid s3 account name is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10881")
    @CTFailOn(error_handler)
    def test_1144_acc_login_with_param(self):
        """
        Test that S3 account is able to login to csmcli passing username as parameter
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
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
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
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
        self.logger.info(
            "Logging into CORTX CLI as s3 account %s",
            self.s3acc_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as s3 account %s",
            self.s3acc_name)
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.csm_user_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10885")
    @CTFailOn(error_handler)
    def test_1916_update_acc_passwd(self):
        """
        Test s3 account user can update his password through csmcli
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        new_password = CSM_CFG["CliConfig"]["csm_user"]["password"]
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10887")
    @CTFailOn(error_handler)
    def test_4428_delete_acc_with_buckets(self):
        """
        Test that appropriate error should be returned when s3 account user try to delete
        s3 account containing buckets
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        bucket_name = f"clis3bkt{int(time.time())}"
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10888")
    @CTFailOn(error_handler)
    def test_6219_create_duplicate_acc_name(self):
        """
        Test that duplicate users should not be created between csm users
        and s3 account users in CSM CLI
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(self.s3acc_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10889")
    @CTFailOn(error_handler)
    def test_1006_list_account_with_format(self):
        """
        Verify that list of all existing S3 accounts should be returned in given <format>
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10890")
    @CTFailOn(error_handler)
    def test_1918_different_confirm_password(self):
        """
        Test that error should be returned when s3 user enters different passwords in
        both password and confirm password
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        dummy_acc = f"cli_s3acc_{int(time.time())}"
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
        self.logger.info(
            "Update s3 account password failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10892")
    @CTFailOn(error_handler)
    def test_1920_no_on_update_password(self):
        """
        Test that password is not updated when user selects "NO" on update password confirmation
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info(
            "Verified s3account password not updated when user selects 'No' on confirmation")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10893")
    @CTFailOn(error_handler)
    def test_1921_reset_invalid_password(self):
        """
        Test that new password should be of 8 characters long which consist
        atleast one lowercase, one uppercase, one nemeric and one special character
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        for pwd in dummy_pwds:
            resp = self.s3acc_obj.reset_s3account_password(
                account_name=self.s3acc_name, new_password=pwd)
            assert_utils.assert_equals(False, resp[0], resp[1])
            assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info(
            "Update s3 account password failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11230")
    @CTFailOn(error_handler)
    def test_949_create_account_with_admin(self):
        """
        Verify that CSM Admin can create S3 account
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11231")
    @CTFailOn(error_handler)
    def test_882_perform_iam_operations(self):
        """
        Verify that only S3 account user must able
        to perform s3iamuser create/delete/show operations
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
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
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        bucket_name = f"clis3bkt{int(time.time())}"
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11233")
    @CTFailOn(error_handler)
    def test_4030_access_secret_key_on_login(self):
        """
        Verify that Secret key and access key should not be visible on login
        using s3 credentials on CSM Cli
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11741")
    @CTFailOn(error_handler)
    def test_1871_s3_account_help(self):
        """
        Test that s3_account user can only list commands using help (-h)
        to which the user has access to.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        resp = self.s3acc_obj.execute_cli_commands(
            cmd=commands.CMD_HELP_OPTION, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        for cmd in constants.S3ACCOUNT_HELP_CMDS:
            assert_utils.assert_exact_string(resp[1], cmd)
        self.logger.info("Successfully verified help response for s3 account")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11747")
    @CTFailOn(error_handler)
    def test_4031_perform_s3_operations(self):
        """
        Test User should able to perform s3 operations after login using s3 credentials on CSM Cli
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        bucket_name = f"clis3bkt{int(time.time())}"
        iam_user_name = f"cli_iam_user{int(time.time())}"
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11746")
    @CTFailOn(error_handler)
    def test_1866_csm_user_operations_with_account(self):
        """
        Test that s3_account user cannot perform list, update, create, delete
        operation on csm_users using CLI.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        resp = self.s3acc_obj.execute_cli_commands(
            cmd=commands.CMD_HELP_OPTION, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        result = csm_user_opt in resp[1]
        assert_utils.assert_equals(False, result, resp[1])
        self.logger.info(
            "Verified csm user option is not available in s3 account help")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12844")
    @CTFailOn(error_handler)
    def test_1869_perform_iam_operations(self):
        """
        Test that s3_account user can perform list, create, delete operation on
        iam_users using CLI created by owner S3_account
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13136")
    @CTFailOn(error_handler)
    def test_1868_non_supported_s3account_operations(self):
        """
        Test that s3_account user cannot perform delete (except owner)
        create operation on s3_accounts using CLI
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        s3acc_name2 = f"cli_s3acc_{int(time.time())}"
        s3acc_email2 = f"{s3acc_name2}@seagate.com"
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
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=s3acc_name2)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Access denied")
        self.logger.info(
            "Deleting different account failed with error %s", resp[1])
        s3acc_name3 = f"cli_s3acc_{int(time.time())}"
        s3acc_email3 = f"{s3acc_name3}@seagate.com"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name3,
            account_email=s3acc_email3,
            password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Creating s3 account failed with error %s", resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13139")
    @CTFailOn(error_handler)
    def test_1867_s3account_operations(self):
        """
        Test that s3_account user can perform list, update, delete operation on
        owner s3_accounts using CLI
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14033")
    @CTFailOn(error_handler)
    def test_1862_alert_operations_with_s3account(self):
        """
        Test that s3_account user cannot list, update alert using CLI
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14033")
    @CTFailOn(error_handler)
    def test_1001_create_s3account_with_s3account(self):
        """
        Test that S3 user is not permitted to create S3 account
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        s3acc_name2 = f"cli_s3acc_{int(time.time())}"
        s3acc_email2 = f"{s3acc_name2}@seagate.com"
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name2,
            account_email=s3acc_email2,
            password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Creating s3 account failed with error %s", resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10879")
    @CTFailOn(error_handler)
    def test_1013_help_options(self):
        """
        Test that help opens on executing "-h" option with commands
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
            resp = self.s3acc_obj.execute_cli_commands(
                cmd=command, patterns=["usage:"])
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
            resp = self.s3acc_obj.execute_cli_commands(
                cmd=command, patterns=["usage:"])
            assert_utils.assert_equals(True, resp[0], resp[1])
            for option in help_options:
                assert_utils.assert_exact_string(resp[1], option)
        self.logger.info(
            "Successfully verified help responses for all s3 account commands")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18190")
    @CTFailOn(error_handler)
    def test_18190_admin_user_reset_pwd(self):
        """
        Test that csm Admin user is able to reset the s3 account users password through cortxcli.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        self.logger.info("Resetting password of S3 account through admin user")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=new_pwd)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("New password is set to S3 account")
        self.logger.info("Login into cortxcli using new password")
        #  s3 login
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Logged in cortxcli using new password")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18191")
    @CTFailOn(error_handler)
    def test_18191_reset_pwd_with_csm_user(self):
        """
        Test that csm user with Manage rights is able
        to reset the s3 account users password through cortxcli.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
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
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.csm_user_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        self.logger.info(
            "Verify reset password of S3 account using CSM manage user")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=new_pwd)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info(
            "Verified reset password of S3 account using CSM manage user")
        # : login chk
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI with new password")
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18192")
    @CTFailOn(error_handler)
    def test_18192_reset_acc_passwd(self):
        """
        Test that s3 account user is able to reset is own password through cortxcli.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
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
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18193")
    @CTFailOn(error_handler)
    def test_18193_reset_diff_acc_passwd(self):
        """
        Test that s3 account user is not able to reset
        password of other s3 account user through cortxcli.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        new_password = CSM_CFG["CliConfig"]["csm_user"]["password"]
        s3acc_name_list = []
        for i in range(2):
            s3acc_name = f"{self.s3acc_prefix}_{ int(time.time())}{i}"
            s3acc_email = f"{s3acc_name}@seagate.com"

            resp = self.s3acc_obj.create_s3account_cortx_cli(
                account_name=s3acc_name,
                account_email=s3acc_email,
                password=self.s3acc_password)
            assert_utils.assert_equals(True, resp[0], resp[1])
            s3acc_name_list.append(s3acc_name)
            self.logger.info("Created s3 account %s", s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=s3acc_name_list[0],
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info("Verify reset password of another s3 account")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=s3acc_name_list[1], new_password=new_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Access denied")
        self.logger.info(
            "Reset password of another s3 account is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18194")
    @CTFailOn(error_handler)
    def test_18194_reset_pwd_with_csm_monitor(self):
        """
        Test that csm user with monitor role is not
        able to reset is password of s3 account user through cortxcli.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.logger.info("Creating csm user with name %s", csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="monitor",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_equals(True, resp[0], resp[1])
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
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.csm_user_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        self.logger.info(
            "Verify reset password of S3 account using CSM monitor user")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=new_pwd)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Verified reset password of S3 account using CSM monitor user")
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18195")
    @CTFailOn(error_handler)
    def test_18195_reset_acc_invalid_passwd(self):
        """
        Test that reset password for s3 account does not accept invalid password.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        dummy_pwds = CSM_CFG["CliConfig"]["s3_account"]["invalid_password"]
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
        self.logger.info("Reset password with invalid password")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=dummy_pwds)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Password Policy Not Met")
        self.logger.info(
            "Reset password with invalid password is falied with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18196")
    @CTFailOn(error_handler)
    def test_18196_reset_acc_invalid_acc_name(self):
        """
        Test that reset password for s3 account does not accept invalid password.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        self.logger.info("Reset password with invalid account name")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name="invalid-@name", new_password=self.s3acc_password)
        assert_utils.assert_equals(False, resp[0], resp[1])
        self.logger.info(
            "Reset password with invalid account name is falied with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18197")
    @CTFailOn(error_handler)
    def test_18197_reset_iam_user_pwd(self):
        """
        Test that S3 account user is able to reset password of it's Child IAM user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
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
        self.logger.info("Reset password of iam user")
        resp = self.iam_user_obj.reset_iamuser_password(
            iamuser_name=iam_user_name, new_password=new_pwd)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info(
            "Verified reset password of IAM user operation is perfomed successfully")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18198")
    @CTFailOn(error_handler)
    def test_18198_reset_iam_user_pwd(self):
        """
        Test that S3 account user is not able to reset
         password of IAM user who are not created under his account.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]

        s3acc_name_list = []
        for i in range(2):
            s3acc_name = f"{self.s3acc_prefix}_{int(time.time())}{i}"
            s3acc_email = f"{s3acc_name}@seagate.com"

            resp = self.s3acc_obj.create_s3account_cortx_cli(
                account_name=s3acc_name,
                account_email=s3acc_email,
                password=self.s3acc_password)
            assert_utils.assert_equals(True, resp[0], resp[1])
            s3acc_name_list.append(s3acc_name)
            self.logger.info("Created s3 account %s", s3acc_name)

        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=s3acc_name_list[0],
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.iam_user_obj.create_iam_user(user_name=iam_user_name,
                                                 password=iam_user_pwd,
                                                 confirm_password=iam_user_pwd)
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Created IAM user %s", iam_user_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=s3acc_name_list[1],
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Verify S3 account user is not able to reset "
            "password of IAM user who are not created under his account")
        resp = self.iam_user_obj.reset_iamuser_password(
            iamuser_name=iam_user_name, new_password=new_pwd)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "request was rejected")
        self.logger.debug(resp)
        self.logger.info(
            "Verified reset password of IAM user operation is perfomed successfully")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18199")
    @CTFailOn(error_handler)
    def test_18199_reset_iam_invalid_pwd(self):
        """
        Test that reset password for IAM user does not accept invalid password.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        invalid_pwds = "seagate"
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
        self.logger.info("Verify iam user does not accept invalid password")
        resp = self.iam_user_obj.reset_iamuser_password(
            iamuser_name=iam_user_name, new_password=invalid_pwds)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Password Policy Not Met")
        self.logger.info(
            "Verify reset password with invalid password is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18200")
    @CTFailOn(error_handler)
    def test_18200_reset_iam_invalid_name(self):
        """
        Test that reset password for IAM user does not accept invalid IAM user name.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
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
        self.logger.info("Verify iam user does not accept invalid user name")
        resp = self.iam_user_obj.reset_iamuser_password(
            iamuser_name="iam-user@1", new_password=new_pwd)
        assert_utils.assert_equals(False, resp[0], resp[1])
        self.logger.info(
            "Verify reset password with invalid user name is failed with erro %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18201")
    @CTFailOn(error_handler)
    def test_18201_reset_pwd_iam_user_with_csm_user(self):
        """
        Test that any CSM user is not able to reset password for any IAM user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        iam_user_name = f"cli_iam_user{str(int(time.time()))}"
        iam_user_pwd = CSM_CFG["CliConfig"]["iam_user"]["password"]
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
        self.logger.info("Creating IAM user %s", iam_user_name)
        login = self.iam_user_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.iam_user_obj.create_iam_user(user_name=iam_user_name,
                                                 password=iam_user_pwd,
                                                 confirm_password=iam_user_pwd)
        assert_utils.assert_exact_string(resp[1], iam_user_name)
        self.logger.info("Created IAM user %s", iam_user_name)
        logout = self.iam_user_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.csm_user_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        self.logger.info(
            "Verify reset password of S3 account using CSM manage user")
        resp = self.s3acc_obj.reset_s3account_password(
            account_name=self.s3acc_name, new_password=new_pwd)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info(
            "Verified reset password of S3 account using CSM manage user")
        logout = self.csm_user_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI with new password")
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18202")
    @CTFailOn(error_handler)
    def test_18202_help_s3_account_reset_pwd(self):
        """
        Test that user is able to view the help document
        for reset s3 account password command with -h parameter.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info("Creating s3 account %s", self.s3acc_name)
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
        self.logger.info(
            "Performing help command for reset password of S3 account")
        resp = self.s3acc_obj.help_option(
            command=commands.CMD_RESET_S3ACC_PWD.format("-h"))
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.debug(resp)
        self.logger.info(
            "Performed help command for reset password of S3 account")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18203")
    @CTFailOn(error_handler)
    def test_18203_help_iam_user_reset_pwd(self):
        """
        Test that user is able to view the help document for
        16reset IAM user password command with -h parameter.
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info("Creating s3 account %s", self.s3acc_name)
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
        self.logger.info(
            "Performing help command for reset password of IAM user")
        resp = self.s3acc_obj.help_option(
            command=commands.CMD_RESET_IAM_PWD.format("-h"))
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.debug(resp)
        self.logger.info(
            "Performed help command for reset password of IAM user")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22446")
    @CTFailOn(error_handler)
    def test_22446_delete_s3_acc(self):
        """
        Test that csm Admin user should able to delete s3account user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        self.logger.info("Deleting S3 account using admin credential")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Deleted S3 account using admin credential")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22447")
    @CTFailOn(error_handler)
    def test_22447_delete_acc_manage_user(self):
        """
        Test that csm Manage user should able to delete s3account user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.logger.info("Creating csm user with name %s", csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="manage",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", csm_user_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        self.logger.info("Deleting S3 account using CSM manage user")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("Deleted S3 account using CSM manage user")

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22448")
    @CTFailOn(error_handler)
    def test_22448_delete_s3_acc(self):
        """
        Test that csm Admin user should not able to
        delete s3account user when bucket is present for s3account user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        bucket_name = f"clis3bkt{int(time.time())}"
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as S3 account %s",
            self.s3acc_name)
        login = self.s3bkt_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as S3 account %s",
            self.s3acc_name)
        self.logger.info("Creating bucket %s", bucket_name)
        resp = self.s3bkt_obj.create_bucket_cortx_cli(bucket_name=bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created bucket %s", bucket_name)
        logout = self.s3bkt_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        login = self.s3bkt_obj.login_cortx_cli()
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Deleting S3 account when bucket is present for s3account user")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Deleting S3 account is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22449")
    @CTFailOn(error_handler)
    def test_22449_delete_acc_manage_user(self):
        """
        Test that csm manage user should not able to
        delete s3account user when bucket is present for s3account user
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=self.csm_user_name,
            email_id=self.csm_user_email,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.csm_user_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            self.csm_user_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.csm_user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            self.csm_user_name)
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as S3 account %s",
            self.s3acc_name)
        login = self.s3bkt_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as S3 account %s",
            self.s3acc_name)
        self.logger.info("Creating bucket %s", self.bucket_name)
        resp = self.s3bkt_obj.create_bucket_cortx_cli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        logout = self.s3bkt_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            self.csm_user_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.csm_user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            self.csm_user_name)
        self.logger.info(
            "Deleting S3 account when bucket is present for s3account user")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Deleting S3 account is failed with error %s",
            resp[1])
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(self.csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22451")
    @CTFailOn(error_handler)
    def test_22451_delete_non_exist_s3_acc(self):
        """
        Test that csm Admin user should not able to delete s3account user with user name not
        present in the list
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info(
            "Deleting non existing S3 account using admin credential")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name="non_exist_acc")
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Deleted non existing S3 account is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22452")
    @CTFailOn(error_handler)
    def test_22452_delete_acc(self):
        """
        Test that csm manage user should not able to
        delete s3account user with user name not present in the list
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=self.csm_user_name,
            email_id=self.csm_user_email,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.csm_user_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            self.csm_user_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=self.csm_user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            self.csm_user_name)
        self.logger.info(
            "Deleting non existing S3 account using CSM user with manage role")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name="non_exist_acc")
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Deleted non existing S3 account is failed with error %s",
            resp[1])
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(self.csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22453")
    @CTFailOn(error_handler)
    def test_22453_help_opt_admin(self):
        """
        Test that csm Admin user help option should show delete s3account operation
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info(
            "Verify delete option should be present in help option")
        resp = self.s3acc_obj.help_option("s3accounts -h")
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Verified delete option should be present in help option")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22454")
    @CTFailOn(error_handler)
    def test_22454_help_opt_csm_user(self):
        """
        Test that csm manage user help option should show delete s3account operation
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.logger.info("Creating csm user with name %s", csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="manage",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", csm_user_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        self.logger.info(
            "Verify delete option should be present in help option for CSM user")
        resp = self.s3acc_obj.help_option("s3accounts -h")
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Verified delete option should be present in help option")
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22455")
    @CTFailOn(error_handler)
    def test_22455_without_param_admin(self):
        """
        Test that csm Admin user should get proper error msg
        for delete s3account operation without username parameter
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info(
            "Performing delete S3 account without account name parameter")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name="")
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required: account_name")
        self.logger.info(resp[1])
        self.logger.info(
            "Performed delete S3 account without account name parameter")
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22456")
    @CTFailOn(error_handler)
    def test_22456_without_param_csm_user(self):
        """
        Test that csm manage user should get proper error msg
        for delete s3account operation without username parameter
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.logger.info("Creating csm user with name %s", csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="manage",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", csm_user_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as csm user %s",
            csm_user_name)
        login = self.s3acc_obj.login_cortx_cli(
            username=csm_user_name,
            password=csm_user_pwd)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as csm user %s",
            csm_user_name)
        self.logger.info(
            "Performing delete S3 account without account name parameter using CSM user")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name="")
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Performed delete S3 account without account name parameter is failed with error %s",
            resp[1])
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22457")
    @CTFailOn(error_handler)
    def test_22457_session_timeout(self):
        """
        Test that session should get logged out with proper
        error msg in case user try to access deleted s3account
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        self.logger.info("Login as S3 account user in new ssh connection")
        login = self.s3acc_obj1.login_cortx_cli(
            username=self.s3acc_name, password=self.s3acc_password)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as S3 account user")
        self.logger.info("Delete S3 account using admin credential")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Deleted S3 account using admin credential")
        self.logger.info(
            "Try to access deleted S3 account using new ssh connection")
        resp = self.s3acc_obj1.show_s3account_cortx_cli()
        assert_utils.assert_exact_string(resp[1], "Session expired")
        self.logger.info(resp)
        self.logger.info("%s %s", self.end_log_format, log.get_frame())

    @pytest.mark.skip(reason="EOS-22249: TODO")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-22757")
    @CTFailOn(error_handler)
    def test_22757_delete_s3_acc_with_bkt(self):
        """
        Verify admin should not be able to delete S3 account if it has S3 buckets
        """
        self.logger.info("%s %s", self.start_log_format, log.get_frame())
        bucket_name = f"clis3bkt{int(time.time())}"
        self.logger.info("Creating s3 account %s", self.s3acc_name)
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        self.logger.info(
            "Logging into CORTX CLI as S3 account %s",
            self.s3acc_name)
        login = self.s3bkt_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Successfully logged in to CORTX CLI as S3 account %s",
            self.s3acc_name)
        self.logger.info("Creating bucket %s", bucket_name)
        resp = self.s3bkt_obj.create_bucket_cortx_cli(bucket_name=bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created bucket %s", bucket_name)
        self.logger.info("Verify bucket is created")
        resp = self.s3bkt_obj.list_buckets_cortx_cli()
        assert_utils.assert_exact_string(resp[1], bucket_name)
        self.logger.info("Bucket list : %s", resp)
        self.logger.info("Verified bucket is created")
        logout = self.s3bkt_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        login = self.s3bkt_obj.login_cortx_cli()
        assert_utils.assert_true(login[0], login[1])
        self.logger.info(
            "Deleting S3 account when bucket is present for s3account user")
        resp = self.s3acc_obj.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(resp[1])
        self.logger.info(
            "Deleting S3 account is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.end_log_format, log.get_frame())
