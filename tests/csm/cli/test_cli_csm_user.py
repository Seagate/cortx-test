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

"""CSM CLI csm user TestSuite"""

# pylint: disable=too-many-lines
import logging
import time
import pytest
from commons.utils import assert_utils
from commons import cortxlogging as log
from commons.alerts_simulator.generate_alert_lib import \
    GenerateAlertLib, AlertType
from commons import constants
from config import CMN_CFG
from config import CSM_CFG
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations


class TestCliCSMUser:
    """CSM user Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
        """
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("STARTED : Setup operations for test suit")
        cls.GENERATE_ALERT_OBJ = GenerateAlertLib()
        cls.csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        cls.acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.iam_password = CSM_CFG["CliConfig"]["iam_user"]["password"]
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
        cls.csm_user_conn = None
        cls.csm_alert_conn = None
        cls.iam_user_conn = None
        cls.bkt_ops = None
        cls.s3_acc_conn = None

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as admin user.
        """
        self.logger.info("STARTED : Setup operations for test function")
        self.csm_user_conn = CortxCliCsmUser()
        self.csm_user_conn.open_connection()
        self.csm_alert_conn = CortxCliAlerts(session_obj=self.csm_user_conn.session_obj)
        self.iam_user_conn = CortxCliIamUser(session_obj=self.csm_user_conn.session_obj)
        self.bkt_ops = CortxCliS3BucketOperations(session_obj=self.csm_user_conn.session_obj)
        self.s3_acc_conn = CortxCliS3AccountOperations(session_obj=self.csm_user_conn.session_obj)
        self.logger.info("Login to CORTX CLI using s3 account")
        self.update_password = False
        self.new_pwd = CSM_CFG["CliConfig"]["csm_user"]["update_password"]
        login = self.csm_user_conn.login_cortx_cli()
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.user_name = f"auto_csm_user{str(int(time.time()))}"
        self.email_id = f"{self.user_name}@seagate.com"
        self.s3acc_name = f"cli_s3acc_{int(time.time())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.iam_user_name = f"iam_user{str(int(time.time()))}"
        self.bucket_name = f"clis3bkt{int(time.time())}"
        self.logger.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete CSM users
            - Log out from CORTX CLI console.
        """
        self.logger.info("STARTED : Teardown operations for test function")
        if self.update_password:
            resp = self.csm_user_conn.reset_root_user_password(
                user_name=CMN_CFG["csm"]["csm_admin_user"]["username"],
                current_password=self.new_pwd,
                new_password=CMN_CFG["csm"]["csm_admin_user"]["password"],
                confirm_password=CMN_CFG["csm"]["csm_admin_user"]["password"])
            assert_utils.assert_equals(resp[0], True, resp)
            self.csm_user_conn.login_cortx_cli()
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        if resp[1]["users"]:
            user_list = [each["username"] for each in resp[1]["users"]]
        my_users = [
            myuser for myuser in user_list if "auto_csm_user" in myuser]
        if my_users:
            for user in my_users:
                self.logger.info("Deleting CSM users %s", user)
                self.csm_user_conn.delete_csm_user(user_name=user)
                self.logger.info("Deleted CSM users %s", user)
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.close_connection()
        self.logger.info("Ended : Teardown operations for test function")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11229")
    def test_1143(self):
        """
        Test that CSM user/admin is able to login to csmcli passing username as parameter
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying CSM user is able to login cortxcli by passing username as parameter")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_with_username_param(
            username=self.user_name, password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, "Server authentication check failed")
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified CSM user is able to login cortxcli by passing username as paramter")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13138")
    def test_1849(self):
        """
        Test that csm user with monitor role can list alert using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Logging using csm monitor role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_alert_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, "Server authentication check failed")
        self.logger.info("Logged in using csm monitor role")
        self.logger.info("Listing alerts using csm monitor role")
        resp = self.csm_alert_conn.show_alerts_cli(duration="1d")
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.logger.info("Listed alerts using csm monitor role")
        self.csm_alert_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10816")
    def test_1266(self):
        """
        Initiating the test case to verify create CSM User
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10817")
    def test_1267(self):
        """
        Initiating the test case to verify create CSM User with monitor role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10818")
    def test_1270(self):
        """
        Initiating the test case to verify create CSM User with invalid role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with invalid role")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="invali_role",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "Creating csm user with invalid role is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10819")
    def test_1268(self):
        """
        Initiating the test case to verify create CSM User with duplicate user name
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Creating csm user with same name")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "User already exists")
        self.logger.info(
            "Creating csm user with duplicate name is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10820")
    def test_1265(self):
        """
        Initiating the test case to verify create CSM User with help response
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Display help response for create csm user")
        resp = self.csm_user_conn.create_csm_user_cli(help_param=True)
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(resp[1])
        self.logger.info("Displayed help response for create csm user")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10821")
    def test_1269(self):
        """
        Initiating the test case to verify create CSM User through unauthorized user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        resp = self.s3_acc_conn.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", self.s3acc_name)
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info(
            "Login through s3 account to verify create CSM User using unauthorized user")
        login = self.csm_user_conn.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.logger.info("Logged in to s3 account")
        self.logger.info("Creating CSM user with unauthorized user")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], False, resp)
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Creating CSM user with unauthorized user is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10823")
    def test_1240(self):
        """
        Initiating the test case to verify list csm user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Verifying list csm user")
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        user_list = [each["username"] for each in resp[1]["users"]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.logger.info("Verified list csm user")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10824")
    def test_1244(self):
        """
        Initiating the test case to verify list csm user with offset
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        offset = 2
        self.logger.info("Creating csm user with name %s", self.user_name)
        for i in range(2):
            user_name = f"{self.user_name}{i}"
            resp = self.csm_user_conn.create_csm_user_cli(
                csm_user_name=user_name,
                email_id=self.email_id,
                role="manage",
                password=self.csm_user_pwd,
                confirm_password=self.csm_user_pwd)
            assert_utils.assert_equals(
                resp[0], True, resp)
            assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Verifying list csm user with offset")
        list_user = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(list_user[0], True, list_user)
        assert len(list_user[1]["users"]) > 0
        list_with_offset = self.csm_user_conn.list_csm_users(
            offset=offset, op_format="json")
        assert len(list_user[1]["users"]) == len(
            list_with_offset[1]["users"]) + offset
        self.logger.info("Verified list csm user with offset")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10826")
    def test_1246(self):
        """
        Test that user cannot list CSM user using cli with no value for param offset
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Verifying list csm user with no value for offset")
        resp = self.csm_user_conn.list_csm_users(op_format="json", offset=" ")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.logger.info(
            "List csm user with no value for offset is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10827")
    def test_1247(self):
        """
        Test that user can list CSM user using cli with valid value for param limit
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        limit = 1
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Verifying list csm user with limit")
        resp = self.csm_user_conn.list_csm_users(limit=limit, op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        assert len(resp[1]["users"]) == limit
        self.logger.info("Verified list csm user with limit")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10829")
    def test_1248(self):
        """
        Test that user cannot list CSM user using cli with invalid value for param limit
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying list csm user with invalid value for limit")
        resp = self.csm_user_conn.list_csm_users(limit=-1, op_format="json")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "Invalid parameter")
        self.logger.debug(resp[1])
        self.logger.info(
            "List csm user with invalid value for limit is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10830")
    def test_1250(self):
        """
        Test that user cannot list CSM user using cli with no value for param limit
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Verifying list csm user with no value for limit")
        resp = self.csm_user_conn.list_csm_users(limit=" ", op_format="json")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.logger.info(
            "List csm user with no value for limit is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10831")
    def test_1261(self):
        """
        Initiating the test case to verify delete CSM User
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Deleting CSM user with name %s", self.user_name)
        resp = self.csm_user_conn.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User deleted")
        self.logger.info("Deleted CSM user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10832")
    def test_1262(self):
        """
        Initiating the test case to verify delete CSM User with username which doesn't exist
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Deleting non existing csm user")
        resp = self.csm_user_conn.delete_csm_user(user_name="non_exist_username")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "User does not exist")
        self.logger.info(
            "Deleting non existing csm user is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10834")
    def test_1263(self):
        """
        Initiating the test case to verify delete CSM User with no username
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Performing delete operation with no username")
        resp = self.csm_user_conn.delete_csm_user(user_name="")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required: username")
        self.logger.info(
            "Performing delete operation with no username is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10835")
    def test_1264(self):
        """
        Initiating the test case to verify help menu for delete CSM User
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Verify help menu for delete CSM User")
        resp = self.csm_user_conn.delete_csm_user(help_param=True)
        self.logger.info(resp[1])
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info("Verified help menu for delete CSM User")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10836")
    def test_6290(self):
        """
        Initiating the test case to verify delete admin/root User
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Verifying delete admin/root User")
        resp = self.csm_user_conn.delete_csm_user(user_name="admin")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Cannot delete")
        self.logger.debug(resp[1])
        self.logger.info(
            "Verifying delete admin/root User is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10838")
    def test_6292(self):
        """
        Initiating the test case to verify CSM User
        is not deleted on entering 'no' on confirmation question
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying CSM User is not deleted on entering 'no' on confirmation question")
        resp = self.csm_user_conn.delete_csm_user(
            user_name=self.user_name, confirm="n")
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "cortxcli")
        self.logger.info(
            "Verified CSM User is not deleted on entering 'no' on confirmation question")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10839")
    def test_6291(self):
        """
        Test that user cannot create CSM user using cli with input 'n' for confirmation prompt
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying CSM User is not created on entering 'no' on confirmation question")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd,
            confirm="n")
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "cortxcli")
        self.logger.info(
            "Verified CSM User is not created on entering 'no' on confirmation question")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10841")
    def test_6289(self):
        """
        Test that user cannot create CSM user using cli with a role as root
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with role as root")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="root",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "Creating csm user with role as root is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10842")
    def test_1241(self):
        """
        Test that csmcli returns appropriate help message for "show user -h" command
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info("Verifying help message for list command")
        resp = self.csm_user_conn.list_csm_users(help_param=True)
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(resp[1])
        self.logger.info("Verified help message for list command")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10843")
    def test_1255(self):
        """
        Initiating the test case to verify list csm user with invalid value of direction
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying list csm user with invalid value of direction")
        resp = self.csm_user_conn.list_csm_users(sort_dir="abc")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "List csm user with invalid value of direction is faield with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10845")
    def test_1256(self):
        """
        Initiating the test case to verify list csm user with invalid value of direction
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying list csm user with invalid value of direction")
        resp = self.csm_user_conn.list_csm_users(sort_dir=" ")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.logger.info(
            "List csm user with invalid value of direction is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10846")
    def test_1258(self):
        """
        Test that csmcli returns appropriate error msg
        for "users show -f" command with no value for param format
        """
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying list csm user with no value for param message")
        resp = self.csm_user_conn.list_csm_users(op_format=" ")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.logger.info(
            "List csm user with no value for param message is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10848")
    def test_1259(self):
        """
        Test that csmcli returns appropriate error msg for
        "users show -f" command with invalid value for param format
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying list csm user with invalid value for param format")
        resp = self.csm_user_conn.list_csm_users(op_format="invalid_format")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "List csm user with invalid value for param format is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10850")
    def test_1249(self):
        """
        Test that csmcli returns appropriate list of csm users for
        "show user" command with valid value for param limit
        where users exists less than limit value
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying list csm user with valid value for param limit "
            "where users exists less than limit value")
        list_user = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        no_of_users = len(list_user[1]["users"])
        resp = self.csm_user_conn.list_csm_users(limit=(no_of_users + 1))
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(
            "Verified list csm user with valid value for param limit "
            "where users exists less than limit value")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18713")
    def test_1251(self):
        """
        Test that csmcli returns appropriate list of csm
        users with "users show -s" command with valid value for param sort
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying list csm user with valid value for param sort")
        resp = self.csm_user_conn.list_csm_users(sort_by="user_id")
        self.logger.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(
            "Verified list csm user with valid value for param sort")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18712")
    def test_1252(self):
        """
        Test that csmcli returns appropriate error msg for
        "users show -s" command with invalid value for param sort
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying list csm user with invalid value for param sort")
        resp = self.csm_user_conn.list_csm_users(sort_by="use_id")
        self.logger.info(resp)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "List csm user with invalid value for param sort is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18711")
    def test_1253(self):
        """
        Test that csmcli returns appropriate error msg
        for "users show -s" command with no value for param sort
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Verifying list csm user with no value for param sort")
        resp = self.csm_user_conn.list_csm_users(sort_by=" ")
        self.logger.info(resp)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "expected one argument")
        self.logger.info(
            "List csm user with no value for param sort is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18710")
    def test_1254(self):
        """
        Test that csmcli returns appropriate list of csm users
        for "users show -d" command with valid value for param direction
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying list csm user with valid value for param direction")
        resp = self.csm_user_conn.list_csm_users(op_format="json", sort_dir="desc")
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(resp)
        self.logger.info(
            "Verified list csm user with valid value for param direction")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-12789")
    def test_1257(self):
        """
        Test that csmcli returns appropriate list of users for
        "users show -f" command with valid value for param format
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying list csm user with valid value for param format")
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info("List of users in json format %s", resp)
        resp = self.csm_user_conn.list_csm_users(op_format="xml")
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info("List of users in xml format %s", resp)
        self.logger.info(
            "Verified list csm user with valid value for param format")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11232")
    def test_1848(self):
        """
        Test that csm user with manage role can only list
        commands using help (-h) to which the user has access to.
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying help response with csm manage role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = self.csm_user_conn.help_option()
        self.logger.info(resp)
        assert_utils.assert_equals(
            resp[0], True, resp)
        for msg in constants.CSM_USER_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified help response with csm manage role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-11740")
    def test_1843(self):
        """
        Test that csm user with manage role can perform list,
         create delete on csm_users using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{int(time.time_ns())}"
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm user with manage role can perform list,create delete on csm_users")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info("Creating csm user")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")

        self.logger.info("Listing csm users")
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        self.logger.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)

        self.logger.info("Deleting csm users")
        resp = self.csm_user_conn.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_equals(resp[0], True, resp)
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified csm user with manage role can perform list,create delete on csm_users")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11743")
    def test_1855(self):
        """
        Test that csm user with monitor role can perform list operation on csm_users using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm monitor role can perform list operation on csm_users using")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        self.logger.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(
            "Verified csm monitor role can perform list operation on csm_users using")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12027")
    def test_1858(self):
        """
        Test that csm user with monitor role cannot
        perform update, delete, create operation on s3_accounts using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm monitor role cannot perform "
            "update, delete, create operation on s3_accounts")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.s3_acc_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.s3_acc_conn.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")

        resp = self.s3_acc_conn.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.s3_acc_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified csm monitor role cannot "
            "perform update, delete, create operation on s3_accounts")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11744")
    def test_1000(self):
        """
        Test that CSM USER can create S3 account
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm manage role can create S3 account")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.s3_acc_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.s3_acc_conn.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp)
        self.s3_acc_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified csm manage role can create S3 account")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12030")
    def test_1260(self):
        """
        Test that csmcli returns appropriate list of csm
         users for "users show" command with valid values for all params
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying list of csm users with valid values for all params")
        resp = self.csm_user_conn.list_csm_users(
            limit=1,
            op_format="json",
            sort_by="user_id",
            sort_dir="desc",
            offset=1)
        assert_utils.assert_equals(resp[0], True, resp)
        assert len(resp[1]["users"]) == 1
        self.logger.info(
            "Verified list of csm users with valid values for all params")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-11745")
    def test_1844(self):
        """
        Test that csm user with manage role can perform list, create on s3_accounts
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm manage role can list, create S3 account")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.s3_acc_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.s3_acc_conn.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.s3_acc_conn.show_s3account_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        self.s3_acc_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified csm manage role can list, create S3 account")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13135")
    def test_5506(self):
        """
        Test that csmcli doesnot create csm user with "user create" with empty password
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Creating csm user with name %s with empty password",
            self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password="")
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "password field can not be empty")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-15728")
    def test_1845(self):
        """
        Test that csm user with manage role cannot perform
        list, update, delete, create on iam_users using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm manage role cannot perform "
            "list, update, delete, create on iam_users")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.iam_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)

        self.logger.info("Creating iam user with manage role")
        resp = self.iam_user_conn.create_iam_user(
            user_name=self.iam_user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.logger.info("Listing iam user with manage role")
        resp = self.iam_user_conn.list_iam_user()
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.logger.info("Deleting iam user with manage role")
        resp = self.iam_user_conn.delete_iam_user(user_name=self.iam_user_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.iam_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16212")
    def test_1861(self):
        """
        Test that csm user with monitor role can
        only list commands using help (-h) to which the user has access to.
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info(
            "Verifying help response with csm monitor role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = self.csm_user_conn.help_option()
        self.logger.info(resp)
        assert_utils.assert_equals(
            resp[0], True, resp)
        for msg in constants.CSM_USER_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified help response with csm monitor role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16928")
    def test_7426(self):
        """
        Test that Root user should able to change other
        users password and roles specifying old_password through CSM-CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Creating csm user %s with role manage", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info(
            "Created csm user %s with role manage", self.user_name)
        self.logger.info("Updating user's password with root user")
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.logger.info("Updated user's password with root user")
        self.logger.info("Verifying password is updated for csm user")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name, password=self.new_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info("Verified password is updated for csm user")
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16931")
    def test_1859(self):
        """
        Test that csm user with monitor role cannot perform
        list, update, delete, create operation on iam_users using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying csm manage role cannot perform "
            "list, update, delete, create on iam_users")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.iam_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)

        self.logger.info("Creating iam user with manage role")
        resp = self.iam_user_conn.create_iam_user(
            user_name=self.iam_user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.logger.info("Listing iam user with manage role")
        resp = self.iam_user_conn.list_iam_user()
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.logger.info("Deleting iam user with manage role")
        resp = self.iam_user_conn.delete_iam_user(user_name=self.iam_user_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")

        self.iam_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16927")
    def test_7428(self):
        """
        Test Non root user should able to change its
        password by specifying old_password and password through CSM-CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verifying user should be able to change its password")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Password Updated")
        self.logger.info(
            "Verified user should be able to change its password")
        self.logger.info("Verifying user should be login using new password")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name, password=self.new_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.logger.info("Verified user is able to login using new password")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-17174")
    def test_1856(self):
        """
        Test that csm user with monitor role cannot update, delete, create csm_users using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Monitor user trying to create csm user")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Monitor user is failed to create csm user with error %s",
            resp[1])
        self.logger.info("Monitor user trying to delete csm user")
        resp = self.csm_user_conn.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.logger.info(
            "Monitor user is failed to delete csm user with error %s",
            resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-18709")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_1850(self):
        """
        Test that csm user with monitor role cannot update alert using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        start_time = time.time()
        self.logger.info("Generating disk fault alert")
        resp = self.GENERATE_ALERT_OBJ.generate_alert(
            AlertType.DISK_FAULT_ALERT,
            input_parameters={
                "du_val": 8,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info("Generated disk fault alert")
        self.logger.info("Verifying alerts are generated")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_alert_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.csm_alert_conn.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        alert_id = resp[1]["alerts"][0]["alert_uuid"]
        self.logger.info("Verified alerts are generated")
        self.logger.info(
            "Verifying csm user with monitor role cannot update alert")
        resp = self.csm_alert_conn.add_comment_alert(alert_id, "demo_comment")
        self.logger.info(resp)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid choice")
        self.csm_alert_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified that csm user with monitor role cannot update alert")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14697")
    def test_7424(self):
        """
        Test that root user should able to modify self password through CSM-CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Updating root password")
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=CMN_CFG["csm"]["csm_admin_user"]["username"],
            current_password=CMN_CFG["csm"]["csm_admin_user"]["password"],
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Password Updated.")
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info("Updated root password")
        self.logger.info(
            "Verifying root user is able to login with new password")
        resp = self.csm_user_conn.login_cortx_cli(
            username=CMN_CFG["csm"]["csm_admin_user"]["username"],
            password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        self.logger.info(
            "Verified root user is able to login with new password")
        self.update_password = True
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16932")
    def test_7429(self):
        """
        Test that Non root user cannot change roles through CSM-CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name_list = []
        user_name2 = f"auto_csm_user{str(int(time.time_ns))}"
        user_name_list.append(self.user_name)
        user_name_list.append(user_name2)
        self.logger.info("Creating csm users with manage and monitor role")
        for each in zip(user_name_list, ["manage", "monitor"]):
            resp = self.csm_user_conn.create_csm_user_cli(
                csm_user_name=each[0],
                email_id=self.email_id,
                password=self.csm_user_pwd,
                confirm_password=self.csm_user_pwd,
                role=each[1])
            assert_utils.assert_equals(resp[0], True, resp)
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info("Created csm users with manage and monitor role")
        self.logger.info(
            "Verifying manage user can not change roles for other user")
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name, password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.csm_user_conn.update_role(
            user_name=user_name2,
            role="monitor",
            current_password=self.csm_user_pwd)
        self.logger.debug(resp[1])
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "can not update")
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info(
            "Verified manage user can not change roles for other user")
        self.logger.info(
            "Verifying monitor user can not change roles for other user")
        resp = self.csm_user_conn.login_cortx_cli(
            username=user_name2, password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        resp = self.csm_user_conn.update_role(
            user_name=self.user_name,
            role="manage",
            current_password=self.csm_user_pwd)
        self.logger.debug(resp[1])
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "can not update")
        self.logger.info(
            "Verified monitor user can not change roles for other user")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16934")
    def test_1847(self):
        """
        Test that csm user with manage role cannot
        perform list, update, delete, create on buckets using CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Performing bucket operations with csm manage role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.bkt_ops.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        self.logger.info("Creating bucket with csm manage role")
        resp = self.bkt_ops.create_bucket_cortx_cli(
            bucket_name=self.bucket_name)
        assert_utils.assert_equals(
            resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info("Listing bucket with csm manage role")
        resp = self.bkt_ops.list_buckets_cortx_cli()
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info("Deleting bucket with csm manage role")
        resp = self.bkt_ops.delete_bucket_cortx_cli(
            bucket_name=self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.bkt_ops.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Performing bucket operations with csm manage role is failed with error %s",
            resp[1])
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12756")
    def test_1857(self):
        """
        Test that csm user with monitor role can list s3_accounts
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Listing csm user with monitor role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.s3_acc_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            resp[0], True, resp)
        resp = self.s3_acc_conn.show_s3account_cortx_cli()
        assert_utils.assert_equals(resp[0], True, resp)
        self.s3_acc_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("Listed csm user with monitor role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-19811")
    def test_reset_csm_user_pwd_by_admin(self):
        """
        verify admin user can change password of csm user(monitor/manage)
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name_list = []
        user_name2 = f"auto_csm_user{str(int(time.time_ns))}"
        user_name_list.append(self.user_name)
        user_name_list.append(user_name2)
        self.logger.info("Creating csm users with manage and monitor role")
        for each in zip(user_name_list, ["manage", "monitor"]):
            resp = self.csm_user_conn.create_csm_user_cli(
                csm_user_name=each[0],
                email_id=self.email_id,
                password=self.csm_user_pwd,
                confirm_password=self.csm_user_pwd,
                role=each[1])
            assert_utils.assert_equals(resp[0], True, resp[1])
            assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm users with manage and monitor role")
        self.logger.info("Resetting password of csm users")
        for each_user in user_name_list:
            resp = self.csm_user_conn.reset_root_user_password(
                user_name=each_user,
                current_password=self.csm_user_pwd,
                new_password=self.new_pwd,
                confirm_password=self.new_pwd)
            assert_utils.assert_equals(resp[0], True, resp[1])
        self.logger.info("Password has been changed for csm users")
        self.logger.info("Login to CSM user using new password")
        for each_user in user_name_list:
            self.csm_user_conn.logout_cortx_cli()
            err_msg = "Login is failed for CSM user %s", each_user
            resp = self.csm_user_conn.login_cortx_cli(
                username=each_user, password=self.new_pwd)
            assert_utils.assert_equals(resp[0], True, err_msg)
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-19869")
    def test_reset_admin_pwd(self):
        """
        Admin user is able to modify self password
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Performing list CSM user before updating admin password")
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        if resp[1]["users"]:
            user_list_1 = [each["username"] for each in resp[1]["users"]]
        self.logger.info("Updating root password")
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=CMN_CFG["csm"]["csm_admin_user"]["username"],
            current_password=CMN_CFG["csm"]["csm_admin_user"]["password"],
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Password Updated.")
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info("Updated root password")
        self.logger.info(
            "Verifying root user is able to login with new password")
        resp = self.csm_user_conn.login_cortx_cli(
            username=CMN_CFG["csm"]["csm_admin_user"]["username"],
            password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp)
        self.update_password = True
        self.logger.info(
            "Verified root user is able to login with new password")
        self.logger.info(
            "Performing list CSM user after updating admin password")
        resp = self.csm_user_conn.list_csm_users(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp)
        if resp[1]["users"]:
            user_list_2 = [each["username"] for each in resp[1]["users"]]
        self.logger.info("Verifying no data loss due to password update")
        assert_utils.assert_list_equal(user_list_1, user_list_2)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-19871")
    def test_reset_self_pwd_by_csm_user(self):
        """
        Verify CSM user can change password of self(manage or monitor) user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name_list = []
        user_name2 = f"auto_csm_user{str(int(time.time_ns))}"
        user_name_list.append(self.user_name)
        user_name_list.append(user_name2)
        self.logger.info("Creating csm users with manage and monitor role")
        for each in zip(user_name_list, ["manage", "monitor"]):
            resp = self.csm_user_conn.create_csm_user_cli(
                csm_user_name=each[0],
                email_id=self.email_id,
                password=self.csm_user_pwd,
                confirm_password=self.csm_user_pwd,
                role=each[1])
            assert_utils.assert_equals(resp[0], True, resp[1])
            assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm users with manage and monitor role")
        self.logger.info("Resetting password of csm users")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name, password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp[1])
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info("Password has been changed for csm users")
        self.logger.info("Login to CSM user using new password")
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name, password=self.new_pwd)
        assert_utils.assert_equals(resp[0], True, resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.logger.info("Login successful using new password")
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-19879")
    def test_reset_admin_pwd_by_csm_user(self):
        """
        Verify CSM user can not change password of admin user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm users with manage role")
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd,
            role="manage")
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm users with manage and monitor role")
        self.logger.info("Resetting password of admin by csm user")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name, password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp[1])
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=CMN_CFG["csm"]["csm_admin_user"]["username"],
            current_password=CMN_CFG["csm"]["csm_admin_user"]["password"],
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "can not update")
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Resetting password of admin by csm user is failed with error")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16211")
    def test_7425(self):
        """
        Test that no user should not able to change roles for root user through CSM-CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        user_name_list = []
        user_name2 = f"auto_csm_user{str(int(time.time_ns))}"
        user_name_list.append(self.user_name)
        user_name_list.append(user_name2)
        self.logger.info("Creating csm users with manage and monitor role")
        for each in zip(user_name_list, ["manage", "monitor"]):
            resp = self.csm_user_conn.create_csm_user_cli(
                csm_user_name=each[0],
                email_id=self.email_id,
                password=self.csm_user_pwd,
                confirm_password=self.csm_user_pwd,
                role=each[1])
            assert_utils.assert_equals(resp[0], True, resp[1])
            assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm users with manage and monitor role")
        self.logger.info(
            "Verifying admin user should not able to change roles for root user")
        resp = self.csm_user_conn.update_role(
            user_name=CMN_CFG["csm"]["csm_admin_user"]["username"],
            role="manage",
            current_password=CMN_CFG["csm"]["csm_admin_user"]["password"])
        self.logger.debug(resp)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1], "Cannot change role")
        self.logger.info(
            "Verified admin user should not able to change roles for root user")
        self.logger.info(
            "Verifying csm user is not able to change roles for root user")
        self.csm_user_conn.logout_cortx_cli()
        for each_user in zip(user_name_list, ["monitor", "manage"]):
            resp = self.csm_user_conn.login_cortx_cli(
                username=each_user[0], password=self.csm_user_pwd)
            assert_utils.assert_equals(resp[0], True, resp[1])
            resp = self.csm_user_conn.update_role(
                user_name=CMN_CFG["csm"]["csm_admin_user"]["username"],
                role=each_user[1],
                current_password=CMN_CFG["csm"]["csm_admin_user"]["password"])
            self.logger.debug(resp)
            assert_utils.assert_false(resp[0], resp[1])
            self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified csm user is not able to change roles for root user")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23772")
    def test_23772(self):
        """
        Test that admin user should be able to create users with admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23775")
    def test_23775(self):
        """
        Test that manage user should NOT be able to create users with admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM manage user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verify manage user should NOT be able to create users with admin role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name="admin_user",
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_false(resp[0], resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified manage user should NOT be able to create users with admin role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23779")
    def test_23779(self):
        """
        Test that admin user should be able to delete users with admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Deleting csm user with admin role %s",
            self.user_name)
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.delete_csm_user(user_name=self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Deleted csm user with admin role %s", self.user_name)
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23780")
    def test_23780(self):
        """
        Test that manage user should NOT be able to delete users with admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info(
            "Creating csm user with manage role : %s",
            self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM manage user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info(
            "Created csm user with manage role %s",
            self.user_name)
        self.logger.info("Creating csm user with admin role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM admin user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with admin role %s", username)
        self.logger.info(
            "Deleting csm user with manage role %s",
            self.user_name)
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.delete_csm_user(user_name=username)
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(
            "Deleting csm user with manage role is failed with error %s", resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23790")
    def test_23790(self):
        """
        Test that manage user should be able to delete users with monitor role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info(
            "Creating csm user with manage role : %s",
            self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM manage user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info(
            "Created csm user with manage role %s",
            self.user_name)
        self.logger.info("Creating csm user with monitor role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM monitor user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with monitor role %s", username)
        self.logger.info(
            "Deleting csm user with manage role %s",
            self.user_name)
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.delete_csm_user(user_name=username)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Deleted csm user with manage role")
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23792")
    def test_23792(self):
        """
        Test that admin user should be able to reset password of users with admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info(
            "Creating csm user with admin role : %s",
            self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with admin role %s", self.user_name)
        self.logger.info(
            "Performing reset password operation on csm user with admin role %s",
            self.user_name)
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(
            "Password has been changed for CSM user with admin role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23808")
    def test_23808(self):
        """
        Test that manage user should be able to reset password of users with monitor role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info(
            "Creating csm user with manage role : %s",
            self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM manage user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info(
            "Created csm user with manage role %s",
            self.user_name)
        self.logger.info("Creating csm user with monitor role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM monitor user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with monitor role %s", username)
        self.logger.info(
            "Verifying password change of monitor user using manage user")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_equals(
            True, resp[0], resp[1])
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=username,
            current_password=self.csm_user_pwd,
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23810")
    def test_23810(self):
        """
        Test that monitor user should NOT be able to reset password of any user with any role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info(
            "Creating csm user with manage role : %s",
            self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM manage user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info(
            "Created csm user with manage role %s",
            self.user_name)
        self.logger.info("Creating csm user with monitor role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM monitor user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with monitor role %s", username)
        self.logger.info(
            "Verifying password change of monitor user using manage user")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=username,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.reset_root_user_password(
            user_name=self.user_name,
            current_password=self.csm_user_pwd,
            new_password=self.new_pwd,
            confirm_password=self.new_pwd)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23811")
    def test_23811(self):
        """
        Test that admin user should be able to change
        role of other admin user from admin role to manage role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Change role of other admin user from admin role to manage role")
        resp = self.csm_user_conn.update_role(
            user_name=self.user_name,
            role="manage",
            current_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(
            "Changed role of other admin user from admin role to manage role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23812")
    def test_23812(self):
        """
        Test that admin user should be able to change
        role of other admin user from admin role to monitor role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admn user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Change role of other admin user from admin role to monitor role")
        resp = self.csm_user_conn.update_role(
            user_name=self.user_name,
            role="monitor",
            current_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(
            "Changed role of other admin user from admin role to monitor role")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23813")
    def test_23813(self):
        """
        Test that admin user should be able to change
        role of manage user from manage role to admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Creating csm user with manage role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM manage user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with manage role %s", username)
        self.logger.info("Change role of manage user to admin")
        resp = self.csm_user_conn.update_role(
            user_name=username,
            role="admin",
            current_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Changed role of manage user to admin")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23814")
    def test_23814(self):
        """
        Test that admin user should be able to
        change role of monitor user from monitor role to admin role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Creating csm user with monitor role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM monitor user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with monitor role %s", username)
        self.logger.info("Change role of monitor user to admin")
        resp = self.csm_user_conn.update_role(
            user_name=username,
            role="admin",
            current_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Changed role of monitor user to admin")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23815")
    def test_23815(self):
        """
        Test that admin user should be able to
        change role of monitor user from monitor role to manage role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Creating csm user with monitor role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM monitor user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with monitor role %s", username)
        self.logger.info("Change role of monitor user to manage")
        resp = self.csm_user_conn.update_role(
            user_name=username,
            role="manage",
            current_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Changed role of monitor user to manage")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23816")
    def test_23816(self):
        """
        Test that monitor user should NOT be able to
        change role of any user with any role including self role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM monitor user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verify monitor user should NOT be able to change role of any user")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.update_role(
            user_name=self.user_name,
            role="manage",
            current_password=self.csm_user_pwd)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info(
            "Verified monitor user should NOT be able to change role of any user")
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23817")
    def test_23817(self):
        """
        Test that manage user should NOT be able to change role of self to any other role
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM manage user '{self.user_name}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info(
            "Verify manage user should NOT be able to change role of self to any other role")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.update_role(
            user_name=self.user_name,
            role="monitor",
            current_password=self.csm_user_pwd)
        assert_utils.assert_false(resp[0], resp[1])
        self.logger.info(
            "Verified manage user should NOT be able to change role of self to any other role")
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-23818")
    def test_23818(self):
        """
        Test that manage user should NOT be able to change role of user with any role to admin
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        username = f"auto_csm_user{str(int(time.time()))}"
        email_id = f"{username}@seagate.com"
        self.logger.info("Creating csm user with name %s", self.user_name)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="admin",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(
            resp[1],
            "User created",
            f"Failed to create CSM admin user '{self.user_name}',Error : '{resp[1]}'")
        self.logger.info("Created csm user with name %s", self.user_name)
        self.logger.info("Creating csm user with monitor role %s", username)
        resp = self.csm_user_conn.create_csm_user_cli(
            csm_user_name=username,
            email_id=email_id,
            role="monitor",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created",
            f"Failed to create CSM monitor user '{username}', Error : '{resp[1]}'")
        self.logger.info("Created csm user with monitor role %s", username)
        self.logger.info(
            "Verify manage user should NOT be able to change role of user with any role to admin")
        self.csm_user_conn.logout_cortx_cli()
        resp = self.csm_user_conn.login_cortx_cli(
            username=self.user_name,
            password=self.csm_user_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user_conn.update_role(
            user_name=username,
            role="admin",
            current_password=self.csm_user_pwd)
        assert_utils.assert_false(resp[0], resp[1])
        self.csm_user_conn.logout_cortx_cli()
        self.csm_user_conn.login_cortx_cli()
        self.logger.info(
            "Verified manage user should NOT be able to change role of user with any role to admin")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
