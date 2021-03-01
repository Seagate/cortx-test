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
import random
import time
import pytest
from commons.utils import assert_utils
from commons.utils import config_utils as conf_util
from commons import cortxlogging as log
from commons.alerts_simulator.generate_alert_lib import \
    GenerateAlertLib, AlertType
from config import CMN_CFG
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations


CSM_USER = CortxCliCsmUser()
CSM_ALERT = CortxCliAlerts()
IAM_USER = CortxCliIamUser()
BKT_OPS = CortxCliS3BucketOperations()
S3_ACC = CortxCliS3AccountOperations()
CLI_CONF = conf_util.read_yaml("config/csm/csm_config.yaml")
GENERATE_ALERT_OBJ = GenerateAlertLib()


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
        cls.iam_password = CLI_CONF[1]["CliConfig"]["iam_password"]
        cls.update_password = None
        cls.new_pwd = None
        cls.user_name = None
        cls.email_id = None
        cls.s3acc_name = None
        cls.s3acc_email = None
        cls.iam_user_name = None
        cls.bucket_name = None

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
        self.update_password = False
        self.new_pwd = "Seagate@1"
        login = CSM_USER.login_cortx_cli()
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.user_name = "{0}{1}".format(
            "auto_csm_user", str(int(time.time())))
        self.email_id = "{0}{1}".format(self.user_name, "@seagate.com")
        self.s3acc_name = "cli_s3acc_{}".format(int(time.time()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.iam_user_name = "{0}{1}".format("iam_user", str(int(time.time())))
        self.bucket_name = "clis3bkt{}".format(int(time.time()))
        self.LOGGER.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete CSM users
            - Log out from CORTX CLI console.
        """
        self.LOGGER.info("STARTED : Teardown operations for test function")
        if self.update_password:
            resp = CSM_USER.reset_root_user_password(
                user_name=CMN_CFG["csm"]["admin_user"],
                current_password=self.new_pwd,
                new_password=CMN_CFG["csm"]["admin_pass"],
                confirm_password=CMN_CFG["csm"]["admin_pass"])
            assert_utils.assert_equals(resp[0], True, resp)
            CSM_USER.login_cortx_cli()
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

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10848")
    def test_1259(self):
        """
        Test that csmcli returns appropriate error msg for
        "users show -f" command with invalid value for param format
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying list csm user with invalid value for param format")
        resp = CSM_USER.list_csm_users(op_format="invalid_format")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "List csm user with invalid value for param format is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10850")
    def test_1249(self):
        """
        Test that csmcli returns appropriate list of csm users for
        "show user" command with valid value for param limit
        where users exists less than limit value
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
            "Verifying list csm user with valid value for param limit "
            "where users exists less than limit value")
        list_user = CSM_USER.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        no_of_users = len(list_user[1]["users"])
        resp = CSM_USER.list_csm_users(limit=(no_of_users + 1))
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(
            "Verified list csm user with valid value for param limit "
            "where users exists less than limit value")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    def test_1251(self):
        """
        Test that csmcli returns appropriate list of csm
        users with "users show -s" command with valid value for param sort
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
            "Verifying list csm user with valid value for param sort")
        resp = CSM_USER.list_csm_users(sort_by="user_id")
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(
            "Verified list csm user with valid value for param sort")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    def test_1252(self):
        """
        Test that csmcli returns appropriate error msg for
        "users show -s" command with invalid value for param sort
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying list csm user with invalid value for param sort")
        resp = CSM_USER.list_csm_users(sort_by="use_id")
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "List csm user with invalid value for param sort is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    def test_1253(self):
        """
        Test that csmcli returns appropriate error msg
        for "users show -s" command with no value for param sort
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Verifying list csm user with no value for param sort")
        resp = CSM_USER.list_csm_users(sort_by=" ")
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.LOGGER.info(
            "List csm user with no value for param sort is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    def test_1254(self):
        """
        Test that csmcli returns appropriate list of csm users
        for "users show -d" command with valid value for param direction
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
            "Verifying list csm user with valid value for param direction")
        resp = CSM_USER.list_csm_users(op_format="json", sort_dir="desc")
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(resp)
        self.LOGGER.info(
            "Verified list csm user with valid value for param direction")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    def test_1257(self):
        """
        Test that csmcli returns appropriate list of users for
        "users show -f" command with valid value for param format
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
            "Verifying list csm user with valid value for param format")
        resp = CSM_USER.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("List of users in json format %s", resp)
        resp = CSM_USER.list_csm_users(op_format="xml")
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("List of users in xml format %s", resp)
        self.LOGGER.info(
            "Verified list csm user with valid value for param format")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11232")
    def test_1848(self):
        """
        Test that csm user with manage role can only list
        commands using help (-h) to which the user has access to.
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
            "Verifying help response with csm manage role")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = CSM_USER.help_option()
        self.LOGGER.info(resp)
        assert_utils.assert_equals(
            resp[0], True, resp)
        CSM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified help response with csm manage role")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11740")
    def test_1843(self):
        """
        Test that csm user with manage role can perform list,
         create delete on csm_users using CLI
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = "auto_csm_user{0}".format(
            random.randint(0, 10))
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
            "Verifying csm user with manage role can perform list,create delete on csm_users")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Creating csm user")
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=username,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")

        self.LOGGER.info("Listing csm users")
        resp = CSM_USER.list_csm_users(op_format="json")
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)

        self.LOGGER.info("Deleting csm users")
        resp = CSM_USER.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_equals(resp[0], True, resp)
        CSM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified csm user with manage role can perform list,create delete on csm_users")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11743")
    def test_1855(self):
        """
        Test that csm user with monitor role can perform list operation on csm_users using CLI
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
        self.LOGGER.info(
            "Verifying csm monitor role can perform list operation on csm_users using")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = CSM_USER.list_csm_users(op_format="json")
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(
            "Verified csm monitor role can perform list operation on csm_users using")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12027")
    def test_1858(self):
        """
        Test that csm user with monitor role cannot
        perform update, delete, create operation on s3_accounts using CLI
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
        self.LOGGER.info(
            "Verifying csm monitor role cannot perform "
            "update, delete, create operation on s3_accounts")
        CSM_USER.logout_cortx_cli()
        resp = S3_ACC.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = S3_ACC.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")

        resp = S3_ACC.delete_s3account_cortx_cli(account_name=self.s3acc_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        S3_ACC.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified csm monitor role cannot "
            "perform update, delete, create operation on s3_accounts")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11744")
    def test_1000(self):
        """
        Test that CSM USER can create S3 account
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
            "Verifying csm manage role can create S3 account")
        CSM_USER.logout_cortx_cli()
        resp = S3_ACC.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = S3_ACC.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp)
        S3_ACC.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified csm manage role can create S3 account")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12030")
    def test_1260(self):
        """
        Test that csmcli returns appropriate list of csm
         users for "users show" command with valid values for all params
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
            "Verifying list of csm users with valid values for all params")
        resp = CSM_USER.list_csm_users(
            limit=1,
            op_format="json",
            sort_by="user_id",
            sort_dir="desc",
            offset=1)
        assert_utils.assert_equals(resp[0], True, resp)
        assert len(resp[1]["users"]) == 1
        self.LOGGER.info(
            "Verified list of csm users with valid values for all params")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11745")
    def test_1844(self):
        """
        Test that csm user with manage role can perform list, create on s3_accounts
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
            "Verifying csm manage role can list, create S3 account")
        CSM_USER.logout_cortx_cli()
        resp = S3_ACC.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = S3_ACC.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = S3_ACC.show_s3account_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        S3_ACC.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified csm manage role can list, create S3 account")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13135")
    def test_5506(self):
        """
        Test that csmcli doesnot create csm user with "user create" with empty password
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info(
            "Creating csm user with name %s with empty password",
            self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password="")
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "password field can't be empty")
        self.LOGGER.info("Created csm user with name %s", self.user_name)
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-15728")
    def test_1845(self):
        """
        Test that csm user with manage role cannot perform
        list, update, delete, create on iam_users using CLI
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
            "Verifying csm manage role cannot perform "
            "list, update, delete, create on iam_users")
        CSM_USER.logout_cortx_cli()
        resp = IAM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)

        self.LOGGER.info("Creating iam user with manage role")
        resp = IAM_USER.create_iam_user(
            user_name=self.iam_user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.LOGGER.info("Listing iam user with manage role")
        resp = IAM_USER.list_iam_user()
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.LOGGER.info("Deleting iam user with manage role")
        resp = IAM_USER.delete_iam_user(user_name=self.iam_user_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        IAM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16212")
    def test_1861(self):
        """
        Test that csm user with monitor role can
        only list commands using help (-h) to which the user has access to.
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
        self.LOGGER.info(
            "Verifying help response with csm monitor role")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = CSM_USER.help_option()
        self.LOGGER.info(resp)
        assert_utils.assert_equals(
            resp[0], True, resp)
        CSM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified help response with csm monitor role")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16928")
    def test_7426(self):
        """
        Test that Root user should able to change other
        users password and roles specifying old_password through CSM-CLI
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        new_password = "Seagate@7426"
        self.LOGGER.info(
            "Creating csm user %s with role manage", self.user_name)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info(
            "Created csm user %s with role manage", self.user_name)
        self.LOGGER.info("Updating user's password with root user")
        resp = CSM_USER.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=new_password,
            confirm_password=new_password)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.LOGGER.info("Updated user's password with root user")
        self.LOGGER.info("Verifying password is updated for csm user")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name, password=new_password)
        assert_utils.assert_equals(
            resp[0], True, resp)
        CSM_USER.logout_cortx_cli()
        self.LOGGER.info("Verified password is updated for csm user")
        CSM_USER.login_cortx_cli()
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16931")
    def test_1859(self):
        """
        Test that csm user with monitor role cannot perform
        list, update, delete, create operation on iam_users using CLI
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
        self.LOGGER.info(
            "Verifying csm manage role cannot perform "
            "list, update, delete, create on iam_users")
        CSM_USER.logout_cortx_cli()
        resp = IAM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)

        self.LOGGER.info("Creating iam user with manage role")
        resp = IAM_USER.create_iam_user(
            user_name=self.iam_user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.LOGGER.info("Listing iam user with manage role")
        resp = IAM_USER.list_iam_user()
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.LOGGER.info("Deleting iam user with manage role")
        resp = IAM_USER.delete_iam_user(user_name=self.iam_user_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        IAM_USER.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16927")
    def test_7428(self):
        """
        Test Non root user should able to change its
        password by specifying old_password and password through CSM-CLI
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Creating csm user with name %s", self.user_name)
        new_password = "Seagate@7428"
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
            "Verifying user should be able to change its password")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = CSM_USER.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=new_password,
            confirm_password=new_password)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Password Updated")
        self.LOGGER.info(
            "Verified user should be able to change its password")
        self.LOGGER.info("Verifying user should be login using new password")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name, password=new_password)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.LOGGER.info("Verified user is able to login using new password")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-17174")
    def test_1856(self):
        """
        Test that csm user with monitor role cannot update, delete, create csm_users using CLI
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
        self.LOGGER.info("Monitor user trying to create csm user")
        CSM_USER.logout_cortx_cli()
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = CSM_USER.create_csm_user_cli(
            csm_user_name=self.user_name,
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "Monitor user is failed to create csm user with error %s",
            resp[1])
        self.LOGGER.info("Monitor user trying to delete csm user")
        resp = CSM_USER.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info(
            "Monitor user is failed to delete csm user with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    def test_1850(self):
        """
        Test that csm user with monitor role cannot update alert using CLI
        :avocado: tags=csm_user
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
        start_time = time.time()
        self.LOGGER.info("Generating disk fault alert")
        resp = GENERATE_ALERT_OBJ.generate_alert(
            AlertType.disk_fault_alert,
            input_parameters={
                "du_val": -3,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info("Generated disk fault alert")
        self.LOGGER.info("Verifying alerts are generated")
        resp = CSM_ALERT.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        alert_id = resp[1]["alerts"][0]["alert_uuid"]
        self.LOGGER.info("Verified alerts are generated")
        self.LOGGER.info(
            "Verifying csm user with monitor role cannot update alert")
        resp = CSM_ALERT.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = CSM_ALERT.add_comment_alert(alert_id, "demo_comment")
        self.LOGGER.info(resp)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        CSM_ALERT.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Verified that csm user with monitor role cannot update alert")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14697")
    def test_7424(self):
        """
        Test that root user should able to modify self password through CSM-CLI
        :avocado: tags=csm_user
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.LOGGER.info("Updating root password")
        self.new_pwd = "Seagate@1"
        resp = CSM_USER.reset_root_user_password(
            user_name=CMN_CFG["csm"]["admin_user"],
            current_password=CMN_CFG["csm"]["admin_pass"],
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Password Updated.")
        CSM_USER.logout_cortx_cli()
        self.LOGGER.info("Updated root password")
        self.LOGGER.info(
            "Verifying root user is able to login with new password")
        resp = CSM_USER.login_cortx_cli(
            username=CMN_CFG["csm"]["admin_user"],
            password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        self.LOGGER.info(
            "Verified root user is able to login with new password")
        self.update_password = True
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16932")
    def test_7429(self):
        """
        Test that Non root user cannot change roles through CSM-CLI
        """
        self.LOGGER.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name_list = []
        user_name2 = "auto_csm_user{0}".format(
            random.randint(0, 10))
        user_name_list.append(self.user_name)
        user_name_list.append(user_name2)
        self.LOGGER.info("Creating csm users with manage and monitor role")
        for each in zip(user_name_list, ["manage", "monitor"]):
            resp = CSM_USER.create_csm_user_cli(
                csm_user_name=each[0],
                email_id=self.email_id,
                password=self.csm_user_pwd,
                confirm_password=self.csm_user_pwd,
                role=each[1])
            assert_utils.assert_equals(resp[0], True, resp)
        CSM_USER.logout_cortx_cli()
        self.LOGGER.info("Created csm users with manage and monitor role")
        self.LOGGER.info(
            "Verifying manage user can not change roles for other user")
        resp = CSM_USER.login_cortx_cli(
            username=self.user_name, password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = CSM_USER.update_role(
            user_name=user_name2,
            role="monitor",
            current_password=self.csm_user_pwd)
        self.LOGGER.debug(resp[1])
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Non super user cannot change other user")
        CSM_USER.logout_cortx_cli()
        self.LOGGER.info(
            "Verified manage user can not change roles for other user")
        self.LOGGER.info(
            "Verifying monitor user can not change roles for other user")
        resp = CSM_USER.login_cortx_cli(
            username=user_name2, password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = CSM_USER.update_role(
            user_name=self.user_name,
            role="manage",
            current_password=self.csm_user_pwd)
        self.LOGGER.debug(resp[1])
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Non super user cannot change other user")
        self.LOGGER.info(
            "Verified monitor user can not change roles for other user")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16934")
    def test_1847(self):
        """
        Test that csm user with manage role cannot
        perform list, update, delete, create on buckets using CLI
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
        self.LOGGER.info("Performing bucket operations with csm manage role")
        CSM_USER.logout_cortx_cli()
        resp = BKT_OPS.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.LOGGER.info("Creating bucket with csm manage role")
        resp = BKT_OPS.create_bucket_cortx_cli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info("Listing bucket with csm manage role")
        resp = BKT_OPS.list_buckets_cortx_cli()
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info("Deleting bucket with csm manage role")
        resp = BKT_OPS.delete_bucket_cortx_cli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        BKT_OPS.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info(
            "Performing bucket operations with csm manage role is failed with error %s",
            resp[1])
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12756")
    def test_1857(self):
        """
        Test that csm user with monitor role can list s3_accounts
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
        self.LOGGER.info("Listing csm user with monitor role")
        CSM_USER.logout_cortx_cli()
        resp = S3_ACC.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = S3_ACC.show_s3account_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        S3_ACC.logout_cortx_cli()
        CSM_USER.login_cortx_cli()
        self.LOGGER.info("Listed csm user with monitor role")
        self.LOGGER.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
