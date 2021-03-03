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

"""CSM CLI csm user TestSuite"""

import logging
import time
import pytest
from commons.utils import assert_utils
from commons.utils import config_utils as conf_util
from commons import cortxlogging as log
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts

CSM_USER = CortxCliCsmUser()
CSM_USER.open_connection()
CSM_ALERT = CortxCliAlerts(session_obj=CSM_USER.session_obj)
CLI_CONF = conf_util.read_yaml("config/csm/csm_config.yaml")


class TestCliCSMUser:
    """CSM user Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
        """
        cls.LOGGER = logging.getLogger(__name__)
        cls.LOGGER.info("STARTED : Setup operations for test suit")
        cls.csm_user_pwd = CLI_CONF[1]["CliConfig"]["csm_user_pwd"]
        cls.acc_password = CLI_CONF[1]["CliConfig"]["acc_password"]
        cls.user_name = None
        cls.email_id = None
        cls.START_LOG_FORMAT = "##### Test started -  "
        cls.END_LOG_FORMAT = "##### Test Ended -  "

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as admin user.
        """
        self.LOGGER.info("STARTED : Setup operations for test function")
        self.LOGGER.info("Login to CORTX CLI using s3 account")
        login = CSM_USER.login_cortx_cli()
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.user_name = "{0}{1}".format(
            "auto_csm_user", str(int(time.time())))
        self.email_id = "{0}{1}".format(self.user_name, "@seagate.com")
        self.LOGGER.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete CSM users
            - Log out from CORTX CLI console.
        """
        self.LOGGER.info("STARTED : Teardown operations for test function")
        resp = CSM_USER.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        if resp[1]["users"]:
            user_list = [each["username"] for each in resp[1]["users"]]
        my_users = [
            myuser for myuser in user_list if "auto_csm_user" in myuser]
        if my_users:
            for user in my_users:
                self.LOGGER.info("Deleting CSM users %s", user)
                CSM_USER.delete_csm_user(user_name=user)
                self.LOGGER.info("Deleted CSM users %s", user)
        CSM_USER.logout_cortx_cli()
        self.LOGGER.info("Ended : Teardown operations for test function")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11229")
    def test_1143(self):
        """
        Test that CSM user/admin is able to login to csmcli passing username as parameter
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info(
            "Verifying CSM user is able to login cortxcli by passing username as parameter")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_with_username_param(
            username=self.user_name, password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, "Server authentication check failed")
        CSM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified CSM user is able to login cortxcli by passing username as paramter")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13138")
    def test_1849(self):
        """
        Test that csm user with monitor role can list alert using CLI
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Logging using csm monitor role")
        CSM_USER.logout_cortx_cli()
        resp = CSM_ALERT.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, "Server authentication check failed")
        self.LOGGER.info("Logged in using csm monitor role")
        self.LOGGER.info("Listing alerts using csm monitor role")
        resp = CSM_ALERT.show_alerts_cli(duration="1d")
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.LOGGER.info("Listed alerts using csm monitor role")
        CSM_ALERT.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10816")
    def test_1266(self):
        """
        Initiating the test case to verify create CSM User
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10817")
    def test_1267(self):
        """
        Initiating the test case to verify create CSM User with monitor role
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10818")
    def test_1270(self):
        """
        Initiating the test case to verify create CSM User with invalid role
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with invalid role")
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="invali_role",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "Creating csm user with invalid role is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10819")
    def test_1268(self):
        """
        Initiating the test case to verify create CSM User with duplicate user name
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Creating csm user with same name")
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "User already exists")
        self.LOGGER.info(
            "Creating csm user with duplicate name is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10820")
    def test_1265(self):
        """
        Initiating the test case to verify create CSM User with help response
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Display help response for create csm user")
        resp = CSM_USER.create_csm_user_cli(help_param=True)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(resp[1])
        self.LOGGER.info("Displayed help response for create csm user")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10821")
    def test_1269(self):
        """
        Initiating the test case to verify create CSM User through unauthorized user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        CSM_USER.logout_cortx_cli()
        self.LOGGER.info(
            "Login through s3 account to verify create CSM User using unauthorized user")
        login = CSM_USER.login_cortx_cli(
            username="cli_s3acc", password=self.acc_password)
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.LOGGER.info("Logged in to s3 account")
        self.LOGGER.info("Creating CSM user with unauthorized user")
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], False, resp)
        CSM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Creating CSM user with unauthorized user is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10823")
    def test_1240(self):
        """
        Initiating the test case to verify list csm user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Verifying list csm user")
        resp = CSM_USER.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        user_list = [each["username"] for each in resp[1]["users"]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.LOGGER.info("Verified list csm user")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10824")
    def test_1244(self):
        """
        Initiating the test case to verify list csm user with offset
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        offset = 2
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Verifying list csm user with offset")
        list_user = CSM_USER.list_csm_users(op_format="json")
        assert_utils.assert_equals(list_user[0], True, list_user)
        assert len(list_user[1]["users"]) > 0
        list_with_offset = CSM_USER.list_csm_users(
            offset=offset, op_format="json")
        assert len(list_user[1]["users"]) == len(
            list_with_offset[1]["users"]) + offset
        self.LOGGER.info("Verified list csm user with offset")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10826")
    def test_1246(self):
        """
        Test that user cannot list CSM user using cli with no value for param offset
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Verifying list csm user with no value for offset")
        resp = CSM_USER.list_csm_users(op_format="json", offset=" ")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.LOGGER.info(
            "List csm user with no value for offset is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10827")
    def test_1247(self):
        """
        Test that user can list CSM user using cli with valid value for param limit
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        limit = 1
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Verifying list csm user with limit")
        resp = CSM_USER.list_csm_users(limit=limit, op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        assert len(resp[1]["users"]) == limit
        self.LOGGER.info("Verified list csm user with limit")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10829")
    def test_1248(self):
        """
        Test that user cannot list CSM user using cli with invalid value for param limit
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info(
            "Verifying list csm user with invalid value for limit")
        resp = CSM_USER.list_csm_users(limit=-1, op_format="json")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "value must be positive integer")
        self.LOGGER.info(
            "List csm user with invalid value for limit is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10830")
    def test_1250(self):
        """
        Test that user cannot list CSM user using cli with no value for param limit
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Verifying list csm user with no value for limit")
        resp = CSM_USER.list_csm_users(limit=" ", op_format="json")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.LOGGER.info(
            "List csm user with no value for limit is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10830")
    def test_1261(self):
        """
        Initiating the test case to verify delete CSM User
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("Deleting CSM user with name %s", self.user_name)
        resp = CSM_USER.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User deleted")
        self.LOGGER.info("Deleted CSM user with name %s", self.user_name)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10832")
    def test_1262(self):
        """
        Initiating the test case to verify delete CSM User with username which doesn't exist
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Deleting non existing csm user")
        resp = CSM_USER.delete_csm_user(user_name="non_exist_username")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "User does not exist")
        self.LOGGER.info(
            "Deleting non existing csm user is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10834")
    def test_1263(self):
        """
        Initiating the test case to verify delete CSM User with no username
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Performing delete operation with no username")
        resp = CSM_USER.delete_csm_user(user_name="")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required: username")
        self.LOGGER.info(
            "Performing delete operation with no username is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10835")
    def test_1264(self):
        """
        Initiating the test case to verify help menu for delete CSM User
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Verify help menu for delete CSM User")
        resp = CSM_USER.delete_csm_user(help_param=True)
        self.LOGGER.info(resp[1])
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Verified help menu for delete CSM User")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10836")
    def test_6290(self):
        """
        Initiating the test case to verify delete admin/root User
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Verifying delete admin/root User")
        resp = CSM_USER.delete_csm_user(user_name="admin")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Can't delete super user")
        self.LOGGER.info(
            "Verifying delete admin/root User is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10838")
    def test_6292(self):
        """
        Initiating the test case to verify CSM User
        is not deleted on entering 'no' on confirmation question
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info(
            "Verifying CSM User is not deleted on entering 'no' on confirmation question")
        resp = CSM_USER.delete_csm_user(user_name=self.user_name, confirm="n")
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "cortxcli")
        self.LOGGER.info(
            "Verified CSM User is not deleted on entering 'no' on confirmation question")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10839")
    def test_6291(self):
        """
        Test that user cannot create CSM user using cli with input 'n' for confirmation prompt
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying CSM User is not created on entering 'no' on confirmation question")
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd,
            confirm="n")
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "cortxcli")
        self.LOGGER.info(
            "Verified CSM User is not created on entering 'no' on confirmation question")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10841")
    def test_6289(self):
        """
        Test that user cannot create CSM user using cli with a role as root
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with role as root")
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="root",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "Creating csm user with role as root is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10842")
    def test_1241(self):
        """
        Test that csmcli returns appropriate help message for "show user -h" command
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Verifying help message for list command")
        resp = CSM_USER.list_csm_users(help_param=True)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(resp[1])
        self.LOGGER.info("Verified help message for list command")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10843")
    def test_1255(self):
        """
        Initiating the test case to verify list csm user with invalid value of direction
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying list csm user with invalid value of direction")
        resp = CSM_USER.list_csm_users(sort_dir="abc")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "List csm user with invalid value of direction is faield with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10845")
    def test_1256(self):
        """
        Initiating the test case to verify list csm user with invalid value of direction
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying list csm user with invalid value of direction")
        resp = CSM_USER.list_csm_users(sort_dir=" ")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.LOGGER.info(
            "List csm user with invalid value of direction is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10846")
    def test_1258(self):
        """
        Test that csmcli returns appropriate error msg
        for "users show -f" command with no value for param format
        """
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying list csm user with no value for param message")
        resp = CSM_USER.list_csm_users(op_format=" ")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.LOGGER.info(
            "List csm user with no value for param message is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
