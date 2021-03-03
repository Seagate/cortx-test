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

"""CSM CLI IAM user TestSuite"""

import time
import logging
import pytest
from commons.utils import assert_utils
from commons.utils import config_utils as conf_util
from commons.helpers import node_helper
from commons import cortxlogging as log
from config import CMN_CFG
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser


IAM_OBJ = CortxCliIamUser()
IAM_OBJ.open_connection()
NODE_HELPER_OBJ = node_helper.Node(hostname=CMN_CFG[1]["csm"]["mgmt_vip"],
                                   username=CMN_CFG[1]["username"],
                                   password=CMN_CFG[1]["password"])
CLI_CONF = conf_util.read_yaml("config/csm/csm_config.yaml")


class TestCliIAMUser:
    """IAM user Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
        """
        cls.LOGGER = logging.getLogger(__name__)
        cls.LOGGER.info("STARTED : Setup operations for test suit")
        cls.iam_password = CLI_CONF[1]["CliConfig"]["iam_password"]
        cls.acc_password = CLI_CONF[1]["CliConfig"]["acc_password"]
        cls.user_name = None
        cls.START_LOG_FORMAT = "##### Test started -  "
        cls.END_LOG_FORMAT = "##### Test Ended -  "

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as s3account user.
        """
        self.LOGGER.info("STARTED : Setup operations for test function")
        self.LOGGER.info("Login to CORTX CLI using s3 account")
        login = IAM_OBJ.login_cortx_cli(
            username="cli_s3acc", password=self.acc_password)
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.user_name = "{0}{1}".format("iam_user", str(int(time.time())))
        self.LOGGER.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete IAM users created in a s3account
            - Log out from CORTX CLI console.
        """
        self.LOGGER.info("STARTED : Teardown operations for test function")
        resp = IAM_OBJ.list_iam_user(output_format="json")
        if resp[0]:
            resp = resp[1]["iam_users"]
            user_del_list = [user["user_name"]
                             for user in resp if "iam_user" in user["user_name"]]
            for each_user in user_del_list:
                self.LOGGER.info(
                    "Deleting IAM user %s", each_user)
                resp = IAM_OBJ.delete_iam_user(each_user)
                assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
                self.LOGGER.info(
                    "Deleted IAM user %s", each_user)
        IAM_OBJ.logout_cortx_cli()
        self.LOGGER.info("ENDED : Teardown operations for test function")

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10858")
    def test_867(self):
        """
        Test that ` s3iamuser create <user_name>` with
        correct username and password should create new IAM user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        resp = IAM_OBJ.create_iam_user(user_name=self.user_name,
                                       password=self.iam_password,
                                       confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.LOGGER.info("Created iam user with name %s", self.iam_password)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10861")
    def test_875(self):
        """
        Test that ` s3iamuser delete <iam_user_name>` must delete the given IAM user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        resp = IAM_OBJ.create_iam_user(user_name=self.user_name,
                                       password=self.iam_password,
                                       confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.LOGGER.info("Created iam user with name %s", self.user_name)
        self.LOGGER.info("Deleting iam user with name %s", self.user_name)
        resp = IAM_OBJ.delete_iam_user(self.user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.LOGGER.info("Deleted iam user with name %s", self.user_name)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10852")
    def test_873(self):
        """
        Initiating the test case to verify duplicate IAM user in same account
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Created iam user with name %s", self.user_name)
        self.LOGGER.info("Verifying duplicate user will not get created")
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1],
            "The request was rejected because it attempted"
            " to create or update a resource that already exists.")
        self.LOGGER.info("Verified that duplicate user was not created")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10851")
    def test_870(self):
        """
        Initiating the test case to display help information for s3iamusers create
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Displaying help information for s3iamusers create")
        resp = IAM_OBJ.create_iam_user(help_param=True)
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Displayed help information for s3iamusers create")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10854")
    def test_871(self):
        """
        Initiating the test case to verify invalid IAM user name
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_username = "Inv@lid-User"
        self.LOGGER.info(
            "Verifying iam user will not get created with invalid name")
        resp = IAM_OBJ.create_iam_user(
            user_name=invalid_username,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Invalid request message received")
        self.LOGGER.info(
            "Verified that iam user was not created with invalid name")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10855")
    def test_872(self):
        """
        Initiating the test case to verify missing IAM user name
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying that error will through with missing user name parameter")
        resp = IAM_OBJ.create_iam_user(
            user_name="",
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required: user_name")
        self.LOGGER.info(
            "Verified that error was displayed with missing user name parameter")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10856")
    def test_874(self, generate_random_string):
        """
        Initiating the test case to verify invalid IAM user password
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_password = generate_random_string
        self.LOGGER.info(
            "Verifying that iam user will not create with invalid password")
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=invalid_password,
            confirm_password=invalid_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Invalid request message received")
        self.LOGGER.info(
            "Verified that iam user is not created with invalid password")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10859")
    def test_6453(self):
        """
        Initiating the test case to verify error message in
         case providing mismatch password while creating IAM user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        mismatch_pwd = "Seagate@123"
        self.LOGGER.info(
            "Verifying that user is not created in case of mismatch password")
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=mismatch_pwd)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "password do not match")
        self.LOGGER.info(
            "Verified that user is not created in case of mismatch password")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10860")
    def test_876(self):
        """
        Initiating the test case to verify delete non existing IAM user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name = "invalid_user"
        self.LOGGER.info("Verifying delete non existing IAM user")
        resp = IAM_OBJ.delete_iam_user(user_name=user_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1],
            "The request was rejected because it referenced a user that does not exist")
        self.LOGGER.info(
            "Verified that delete non existing IAM user is failed")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10862")
    def test_1145(self):
        """
        Initiating the test case to verify IAM user should not able to login to csmcli
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name = "{0}{1}".format("iam_user", str(int(time.time())))
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Created iam user with name %s", self.user_name)
        self.LOGGER.info("Verifying iam user is created")
        resp = IAM_OBJ.list_iam_user(output_format="json")[1]["iam_users"]
        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, user_name)
        self.LOGGER.info("Verified that iam user is created")
        self.LOGGER.info("Verifying iam user is not able to login cortxcli")
        logout = IAM_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(logout[0], True, logout)
        login = IAM_OBJ.login_cortx_cli(
            username=self.user_name,
            password=self.iam_password)
        assert_utils.assert_equals(login[0], False, resp)
        IAM_OBJ.login_cortx_cli(
            username="cli_s3acc",
            password=self.acc_password)
        self.LOGGER.info(
            "Verified that iam user is not able to login cortxcli")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10863")
    def test_878(self):
        """
        Initiating the test case to verify IAM user show command
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Created iam user with name %s", self.user_name)
        self.LOGGER.info(
            "Verifying show command is able to list user in all format(json,xml,table)")
        # show command with json format
        resp = IAM_OBJ.list_iam_user(output_format="json")[1]["iam_users"]

        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, self.user_name)

        # show command with xml format
        resp = IAM_OBJ.list_iam_user(output_format="xml")[1]
        user_list = [each["iam_users"]["user_name"]
                     for each in resp if each.get("iam_users")]
        assert_utils.assert_list_item(user_list, self.user_name)

        # show command with table format
        resp = IAM_OBJ.list_iam_user(output_format="table")
        user_list = [each_user[1] for each_user in resp[1]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.LOGGER.info(
            "Verified show command is able to list user in all format(json,xml,table)")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10864")
    def test_1152(self):
        """
        Initiating the test case to verify User is logged out from csmcli when he enters exit
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        self.LOGGER.info(
            "Verifying user is logged out from cortxcli when he enters exit")
        resp = IAM_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(
            "Verified that user is logged out from csmcli when he enters exit")
        IAM_OBJ.login_cortx_cli(
            username="cli_s3acc",
            password=self.acc_password)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10865")
    def test_1149(self, generate_random_string):
        """
        Initiating the test case to verify appropriate
        error should be returned when user enters invalid password
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_password = generate_random_string
        self.LOGGER.info("Creating iam user with name %s", self.user_name)
        resp = IAM_OBJ.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Created iam user with name %s", self.user_name)
        self.LOGGER.info("Verifying iam user is created")
        resp = IAM_OBJ.list_iam_user(output_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        resp = resp[1]["iam_users"]
        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.LOGGER.info("Verified that iam user is created")
        self.LOGGER.info(
            "Verifying that appropriate error should be returned when user enters invalid password")
        resp = IAM_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        resp = IAM_OBJ.login_cortx_cli(
            username=self.user_name,
            password=invalid_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Server authentication check failed")
        IAM_OBJ.login_cortx_cli(
            username="cli_s3acc",
            password=self.acc_password)
        self.LOGGER.info(
            "Verified that appropriate error should be returned when user enters invalid password")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10866")
    def test_1148(self):
        """
        Initiating the test case to verify appropriate
        error should be returned when user enters invalid username
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        invalid_user = "Invalid_user"
        self.LOGGER.info(
            "Verifying that appropriate error should be returned when user enters invalid username")
        resp = IAM_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(resp[0], False, resp)
        resp = IAM_OBJ.login_cortx_cli(
            username=invalid_user,
            password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Server authentication check failed")
        IAM_OBJ.login_cortx_cli(
            username="cli_s3acc",
            password=self.acc_password)
        self.LOGGER.info(
            "Verified that appropriate error should be returned when user enters invalid username")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10868")
    def test_1154(self):
        """
        Initiating the test case to verify user is logged
        out when user presses Ctrl+C in interactive csmcli
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Sending keyboard interrupt signal to cli process ")
        resp = NODE_HELPER_OBJ.pgrep(process="cortxcli")
        assert_utils.assert_equals(resp[0], True, resp)
        cmd = "python3 -c 'import os; os.kill({0}, signal.SIGINT))'".format(
            int(resp[1][0].split()[0]))
        resp = NODE_HELPER_OBJ.execute_cmd(cmd=cmd)
        time.sleep(3)
        resp = IAM_OBJ.login_cortx_cli(
            username="cli_s3acc",
            password=self.acc_password)
        self.LOGGER.info(
            "Keyboard interrupt signal has been sent to running process ")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm
    @pytest.mark.csm_iamuser
    @pytest.mark.tags("TEST-10867")
    def test_1150(self):
        """
        Initiating the test case to verify appropriate
        message should be returned when user enters valid username
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying that appropriate message should be returned when user enters valid username")
        resp = IAM_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        resp = IAM_OBJ.login_cortx_cli(
            username="cli_s3acc",
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(
            resp[1], "CORTX Interactive Shell")
        self.LOGGER.info(
            "Verified that appropriate message should be returned when user enters valid username")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

