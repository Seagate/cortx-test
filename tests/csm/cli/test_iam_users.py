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

"""CSM CLI IAM user TestSuite"""

import time
import logging
import pytest
from commons.utils import assert_utils
from commons.helpers import node_helper
from commons import cortxlogging as log
from config import CMN_CFG
from config import CSM_CFG
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_s3access_keys import CortxCliS3AccessKeys


class TestCliIAMUser:
    """IAM user Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
            - Creating s3 account to perform IAM test cases
        """
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("STARTED : Setup operations for test suit")
        cls.iam_password = CSM_CFG["CliConfig"]["iam_user"]["password"]
        cls.acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.user_name = None
        cls.iam_obj = CortxCliIamUser()
        cls.iam_obj.open_connection()
        cls.node_helper_obj = node_helper.Node(
            hostname=CMN_CFG["csm"]["mgmt_vip"],
            username=CMN_CFG["csm"]["csm_admin_user"]["username"],
            password=CMN_CFG["csm"]["csm_admin_user"]["password"])
        cls.s3acc_obj = CortxCliS3AccountOperations(
            session_obj=cls.iam_obj.session_obj)
        cls.access_key_obj = CortxCliS3AccessKeys(
            session_obj=cls.iam_obj.session_obj)
        cls.s3acc_name = f"cli_s3acc_{int(time.time())}"
        cls.s3acc_email = f"{cls.s3acc_name}@seagate.com"
        cls.logger.info("Creating s3 account with name %s", cls.s3acc_name)
        resp = cls.s3acc_obj.login_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = cls.s3acc_obj.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        cls.s3acc_obj.logout_cortx_cli()
        cls.logger.info("Created s3 account")
        cls.START_LOG_FORMAT = "##### Test started -  "
        cls.END_LOG_FORMAT = "##### Test Ended -  "

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as s3account user.
        """
        self.logger.info("STARTED : Setup operations for test function")
        self.logger.info("Login to CORTX CLI using s3 account")
        login = self.iam_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        assert_utils.assert_true(login[0], login[1])
        self.user_name = f"iam_user{str(int(time.time()))}"
        self.logger.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete IAM users created in a s3account
            - Log out from CORTX CLI console.
        """
        self.logger.info("STARTED : Teardown operations for test function")
        resp = self.iam_obj.list_iam_user(output_format="json")
        if resp[0]:
            resp = resp[1]["iam_users"]
            user_del_list = [user["user_name"]
                             for user in resp if "iam_user" in user["user_name"]]
            for each_user in user_del_list:
                self.logger.info(
                    "Deleting IAM user %s", each_user)
                resp = self.iam_obj.delete_iam_user(each_user)
                assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
                self.logger.info(
                    "Deleted IAM user %s", each_user)
        self.iam_obj.logout_cortx_cli()
        self.logger.info("ENDED : Teardown operations for test function")

    @classmethod
    def teardown_class(cls):
        """
        This function will be invoked after test suit.
        It is performing below operations as pre-requisites.
            - Deleting S3 account
            - Logout from cortxcli
        """
        cls.logger.info("Deleting s3 account %s", cls.s3acc_name)
        resp = cls.s3acc_obj.login_cortx_cli(
            username=cls.s3acc_name, password=cls.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        resp = cls.s3acc_obj.delete_s3account_cortx_cli(
            account_name=cls.s3acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        cls.s3acc_obj.logout_cortx_cli()
        cls.iam_obj.close_connection()
        cls.logger.info("Deleted s3 account %s", cls.s3acc_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10858")
    def test_867_create_iam_user(self):
        """
        Test that ` s3iamuser create <user_name>` with
        correct username and password should create new IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10861")
    def test_875_delete_iam_user(self):
        """
        Test that ` s3iamuser delete <iam_user_name>` must delete the given IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Deleting iam user with name %s", self.user_name)
        resp = self.iam_obj.delete_iam_user(self.user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.logger.info("Deleted iam user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10852")
    def test_873_create_duplicate_user(self):
        """
        Initiating the test case to verify duplicate IAM user in same account
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Verifying duplicate user will not get created")
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "The request was rejected because it attempted"
            " to create or update a resource that already exists.")
        self.logger.info("Verified that duplicate user was not created")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10851")
    def test_870_display_help(self):
        """
        Initiating the test case to display help information for s3iamusers create
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Displaying help information for s3iamusers create")
        resp = self.iam_obj.create_iam_user(help_param=True)
        self.logger.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Displayed help information for s3iamusers create")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10854")
    def test_871_create_invalid_user(self):
        """
        Initiating the test case to verify invalid IAM user name
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_username = "Inv@lid$&-User"
        self.logger.info(
            "Verifying iam user will not get created with invalid name")
        resp = self.iam_obj.create_iam_user(
            user_name=invalid_username,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "Invalid request message received")
        self.logger.info(
            "Verified that iam user was not created with invalid name")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10855")
    def test_872_missing_username_param(self):
        """
        Initiating the test case to verify missing IAM user name
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying that error will through with missing user name parameter")
        resp = self.iam_obj.create_iam_user(
            user_name="",
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required: user_name")
        self.logger.info(
            "Verified that error was displayed with missing user name parameter")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10856")
    def test_874_invalid_pwd(self, generate_random_string):
        """
        Initiating the test case to verify invalid IAM user password
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_password = generate_random_string
        self.logger.info(
            "Verifying that iam user will not create with invalid password")
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=invalid_password,
            confirm_password=invalid_password)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "Invalid request message received")
        self.logger.info(
            "Verified that iam user is not created with invalid password")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10859")
    def test_6453_mismatch_pwd(self):
        """
        Initiating the test case to verify error message in
         case providing mismatch password while creating IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        mismatch_pwd = "Seagate@123"
        self.logger.info(
            "Verifying that user is not created in case of mismatch password")
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=mismatch_pwd)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "password do not match")
        self.logger.info(
            "Verified that user is not created in case of mismatch password")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10860")
    def test_876_delete_non_exist_user(self):
        """
        Initiating the test case to verify delete non existing IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name = "invalid_user"
        self.logger.info("Verifying delete non existing IAM user")
        resp = self.iam_obj.delete_iam_user(user_name=user_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "The request was rejected because it referenced a user that does not exist")
        self.logger.info(
            "Verified that delete non existing IAM user is failed")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10862")
    def test_1145_login_with_iam_user(self):
        """
        Initiating the test case to verify IAM user should not able to login to csmcli
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Verifying iam user is created")
        resp = self.iam_obj.list_iam_user(output_format="json")[1]["iam_users"]
        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.logger.info("Verified that iam user is created")
        self.logger.info("Verifying iam user is not able to login cortxcli")
        logout = self.iam_obj.logout_cortx_cli()
        assert_utils.assert_true(logout[0], logout[1])
        login = self.iam_obj.login_cortx_cli(
            username=self.user_name,
            password=self.iam_password)
        assert_utils.assert_false(login[0], login[1])
        self.iam_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.acc_password)
        self.logger.info(
            "Verified that iam user is not able to login cortxcli")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10863")
    def test_878_list_user(self):
        """
        Initiating the test case to verify IAM user show command
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info(
            "Verifying show command is able to list user in all format(json,xml,table)")
        # show command with json format
        resp = self.iam_obj.list_iam_user(output_format="json")[1]["iam_users"]

        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, self.user_name)

        # show command with xml format
        resp = self.iam_obj.list_iam_user(output_format="xml")[1]
        user_list = [each["iam_users"]["user_name"]
                     for each in resp if each.get("iam_users")]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.logger.info(
            "Verified show command is able to list user in all format(json,xml,table)")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10864")
    def test_1152_user_logout(self):
        """
        Initiating the test case to verify User is logged out from csmcli when he enters exit
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        self.logger.info(
            "Verifying user is logged out from cortxcli when he enters exit")
        resp = self.iam_obj.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(
            "Verified that user is logged out from csmcli when he enters exit")
        self.iam_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.acc_password)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10865")
    def test_1149_invalid_password(self, generate_random_string):
        """
        Initiating the test case to verify appropriate
        error should be returned when user enters invalid password
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_password = generate_random_string
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Verifying iam user is created")
        resp = self.iam_obj.list_iam_user(output_format="json")
        assert_utils.assert_true(resp[0], resp[1])
        resp = resp[1]["iam_users"]
        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.logger.info("Verified that iam user is created")
        self.logger.info(
            "Verifying that appropriate error should be returned when user enters invalid password")
        resp = self.iam_obj.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.iam_obj.login_cortx_cli(
            username=self.user_name,
            password=invalid_password)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "Server authentication check failed")
        self.iam_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.acc_password)
        self.logger.info(
            "Verified that appropriate error should be returned when user enters invalid password")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10866")
    def test_1148_invalid_username(self):
        """
        Initiating the test case to verify appropriate
        error should be returned when user enters invalid username
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_user = "Invalid_user"
        self.logger.info(
            "Verifying that appropriate error should be returned when user enters invalid username")
        resp = self.iam_obj.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.iam_obj.login_cortx_cli(
            username=invalid_user,
            password=self.iam_password)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "Server authentication check failed")
        self.iam_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.acc_password)
        self.logger.info(
            "Verified that appropriate error should be returned when user enters invalid username")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10868")
    def test_1154_logged_out_with_ctrl_c(self):
        """
        Initiating the test case to verify user is logged
        out when user presses Ctrl+C in interactive csmcli
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Sending keyboard interrupt signal to cli process ")
        resp = self.node_helper_obj.pgrep(process="cortxcli")
        assert_utils.assert_true(resp[0], resp[1])
        tmp = int(resp[1][0].split()[0])
        cmd = f"python3 -c 'import os; os.kill({tmp}, signal.SIGINT))'"
        resp = self.node_helper_obj.execute_cmd(cmd=cmd)
        time.sleep(3)
        resp = self.iam_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.acc_password)
        self.logger.info(
            "Keyboard interrupt signal has been sent to running process ")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10867")
    def test_1150_login_with_valid_user(self):
        """
        Initiating the test case to verify appropriate
        message should be returned when user enters valid username
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying that appropriate message should be returned when user enters valid username")
        resp = self.iam_obj.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.iam_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "CORTX Interactive Shell")
        self.logger.info(
            "Verified that appropriate message should be returned when user enters valid username")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-21823")
    def test_21823_create_access_key(self):
        """
        Create access keys for IAM user through CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info("Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert create_access_key[1]["access_key"] in access_keys
        self.logger.info("Verified access key is created")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-21824")
    def test_21824_delete_access_key(self):
        """
        Verify delete access key for IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info("Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key in access_keys
        self.logger.info("Verified access key is created")
        self.logger.info("Deleting access key of IAM user %s", self.user_name)
        resp = self.access_key_obj.delete_s3access_key(
            access_key=iam_access_key, user_name=self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Deleted access key of IAM user %s", self.user_name)
        self.logger.info(
            "Verify access key is deleted for IAM user %s",
            self.user_name)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key not in access_keys
        self.logger.info(
            "Verified access key is deleted for IAM user %s",
            self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-21825")
    def test_21825_update_access_key_status(self):
        """
        Update status of access for IAM user through CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        access_key_status = "Inactive"
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info("Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key in access_keys
        self.logger.info("Verified access key is created")
        self.logger.info(
            "Updating status of access key of user %s",
            self.user_name)
        resp = self.access_key_obj.update_s3access_key(
            access_key=iam_access_key,
            user_name=self.user_name,
            status=access_key_status)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(
            "Updated status of access key of user %s",
            self.user_name)
        self.logger.info(
            "Verify status is updated for access key %s",
            iam_access_key)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        updated_status = [i["status"] for i in resp["access_keys"]
                          if iam_access_key == i["access_key_id"]]
        assert_utils.assert_equals(updated_status[0], access_key_status, resp)
        self.logger.info(
            "Verified status is updated for access key %s",
            iam_access_key)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-21999")
    def test_21999_check_access_key_count(self):
        """
        Verify IAM user can not create more than two access keys
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        access_key_status = "Inactive"
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info(
            "Verify two access keys are present for IAM user %s",
            self.user_name)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key in access_keys
        assert len(access_keys) == 2
        self.logger.info(
            "Verified two access keys are present for IAM user %s",
            self.user_name)
        self.logger.info(
            "Verify IAM user can not have more than two access keys")
        resp = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "exceeded quota")
        self.logger.info(resp)
        self.logger.info(
            "Verified IAM user can not have more than two access keys")

        self.logger.info("Verify invalid user name for delete option")
        resp = self.access_key_obj.delete_s3access_key(
            access_key="AA-FGH-@r", user_name="dummy_iam_user")
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info("Verified invalid user name for delete option")
        self.logger.info("Updating status of invalid access key")
        resp = self.access_key_obj.update_s3access_key(
            access_key="invalid-access-key",
            user_name=self.user_name,
            status=access_key_status)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "access key that does not exist")
        self.logger.info(
            "Updating status of invalid access key is failed with error %s",
            resp[1])
