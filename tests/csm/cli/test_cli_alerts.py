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
"""CLI Alert Testsuit"""

import time
import logging
import pytest
from commons.utils import assert_utils
from commons.alerts_simulator.generate_alert_lib import \
    GenerateAlertLib, AlertType
from commons import cortxlogging
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts

class TestCliAlert:
    """
    Alert Testsuite for CLI
    """

    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as admin user.
        """
        cls.generate_alert_obj = GenerateAlertLib()
        cls.log = logging.getLogger(__name__)
        cls.start_log = "##### Test started -  "
        cls.end_log = "##### Test Ended -  "
        cls.log.info("STARTED : Setup operations for test function")
        cls.log.info("Login to CORTX CLI using admin")
        cls.alert_obj = CortxCliAlerts()
        cls.alert_obj.open_connection()
        login = cls.alert_obj.login_cortx_cli()
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        cls.log.info("ENDED : Setup operations for test function")


    def teardown_function(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Log out from CORTX CLI console.
        """
        self.log.info("STARTED : Teardown operations for test function")
        self.alert_obj.logout_cortx_cli()
        self.alert_obj.close_connection()
        self.log.info("Ended : Teardown operations for test function")


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14032")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_131(self):
        """
        Test alerts acknowledge <alert id> -ack should acknowledge the given alert
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        start_time = time.time()
        self.log.info("Step 1: Generating disk fault alert")
        resp = self.generate_alert_obj.generate_alert(
            AlertType.disk_fault_alert,
            input_parameters={
                "du_val": -3,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info("Step 1: Generated disk fault alert")
        self.log.info("Step 2: Verifying alerts are generated")
        resp = self.alert_obj.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        end_time = time.time()
        duration = str(int(end_time - start_time)) + "s"
        alert_id = resp[1]["alerts"][0]["alert_uuid"]
        self.log.info("Step 2: Verified alerts are generated")
        self.log.info(
            "Step 3: Acknowledge alert %s from given list", alert_id)
        resp = self.alert_obj.acknowledge_alert_cli(alert_id=alert_id)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Alert Updated")
        self.log.info(
            "Step 3: Acknowledged alert %s from given list", alert_id)
        self.log.info("Step 4: Verifying alert is acknowledged")
        resp = self.alert_obj.show_alerts_cli(duration=duration,
                                        limit=1,
                                        output_format="json")
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["alerts"][0]["acknowledged"], True, resp[1])
        self.log.info("Step 4: Verified alert is acknowledged")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14031")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_6306(self):
        """
        Verify that all comments on alert is returned in table format on executing show alert
        command
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        start_time = time.time()
        self.log.info("Step 1: Generating disk fault alert")
        resp = self.generate_alert_obj.generate_alert(
            AlertType.disk_fault_alert,
            input_parameters={
                "du_val": -3,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info("Step 1: Generated disk fault alert")
        self.log.info("Step 2: Verifying alerts are generated")
        resp = self.alert_obj.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        alert_id = resp[1]["alerts"][0]["alert_uuid"]
        self.log.info("Step 2: Verified alerts are generated")
        self.log.info("Step 3: Adding comment to an alert")
        resp = self.alert_obj.add_comment_alert(
            alert_id, "Default_alert")
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Alert Comment Added")
        self.log.info("Step 3: Added comment to an alert")
        self.log.info(
            "Step 4: Verifying alert is returned in table format with all details")
        resp = self.alert_obj.show_alerts_comment_cli(alert_id)
        self.log.info(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info(
            "Step 4: Verified that alert is returned in table format with all details")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14662")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_3289(self):
        """
        csmcli alerts acknowledge <alert id> <comment> with invalid <alert id>
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        self.log.info(
            "Step 1: Acknowledge alert with invalid id")
        resp = self.alert_obj.acknowledge_alert_cli(alert_id="74659q349694-4r4r43")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Alert was not found")
        self.log.info(
            "Step 3: Acknowledging alert with invalid id is failed with error %s",
            resp[1])
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14663")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_3290(self):
        """
        Test "csmcli alerts acknowledge" command
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        start_time = time.time()
        self.log.info("Step 1: Running ALERT API for generating fault")
        resp = self.generate_alert_obj.generate_alert(
            AlertType.disk_fault_alert,
            input_parameters={
                "du_val": -3,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info(
            "Step 1: Successfully run ALERT API for generating fault")
        self.log.info("Step 2: Verifying alerts are generated")
        resp = self.alert_obj.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        end_time = time.time()
        duration = str(int(end_time - start_time)) + "s"
        alert_id = resp[1]["alerts"][0]["alert_uuid"]
        self.log.info("Step 2: Verified alerts are generated")
        self.log.info(
            "Step 3: Acknowledge alert %s from given list", alert_id)
        resp = self.alert_obj.acknowledge_alert_cli(alert_id)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Alert Updated")
        self.log.info(
            "Step 3: Acknowledged alert %s from given list", alert_id)
        self.log.info("Step 4: Verifying alert is acknowledged")
        resp = self.alert_obj.show_alerts_cli(
            duration=duration,
            limit=1,
            output_format="json")
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["alerts"][0]["acknowledged"], True, resp[1])
        self.log.info("Step 4: Verified alert is acknowledged")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14664")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_6309(self):
        """
        Test that help menu opens for both 'show'
        and 'add' comments options along with parameter details
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        self.log.info("Verifying help menu for show comment command")
        resp = self.alert_obj.show_alerts_comment_cli(help_param=True)
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info(resp[1])
        self.log.info("Verified help menu for show comment command")
        self.log.info("Verifying help menu for add comment command")
        resp = self.alert_obj.add_comment_alert(help_param=True)
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info(resp[1])
        self.log.info("Verified help menu for add comment command")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14754")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_245(self):
        """
        Test 'alerts acknowledge <wrong_alert id> -ack' should give error message
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        self.log.info(
            "Step 1: Acknowledge alert with invalid id")
        resp = self.alert_obj.acknowledge_alert_cli(alert_id="74659q349694-4r4r43-cc")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Alert was not found")
        self.log.info(
            "Step 3: Acknowledging alert with invalid id is failed with error %s",
            resp[1])
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-14755")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_3288(self):
        """
        Test "csmcli alerts acknowledge" command
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        start_time = time.time()
        self.log.info("Step 1: Running ALERT API for generating fault")
        resp = self.generate_alert_obj.generate_alert(
            AlertType.disk_fault_alert,
            input_parameters={
                "du_val": -3,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info(
            "Step 1: Successfully run ALERT API for generating fault")
        self.log.info("Step 2: Verifying alerts are generated")
        resp = self.alert_obj.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        end_time = time.time()
        duration = str(int(end_time - start_time)) + "s"
        alert_id = resp[1]["alerts"][0]["alert_uuid"]
        self.log.info("Step 2: Verified alerts are generated")
        self.log.info(
            "Step 3: Acknowledge alert %s from given list", alert_id)
        resp = self.alert_obj.acknowledge_alert_cli(alert_id)
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Alert Updated")
        self.log.info(
            "Step 3: Acknowledged alert %s from given list", alert_id)
        self.log.info("Step 4: Verifying alert is acknowledged")
        resp = self.alert_obj.show_alerts_cli(
            duration=duration,
            limit=1,
            output_format="json")
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["alerts"][0]["acknowledged"], True, resp[1])
        self.log.info("Step 4: Verified alert is acknowledged")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-15199")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_6308(self):
        """
        Test that error is returned when wrong alert_uuid is entered in show alert command
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        self.log.info(
            "Step 1: Performing show alert command with invalid alert id")
        resp = self.alert_obj.show_alerts_comment_cli(alert_id="74659q349694-4r4r43-cc")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(resp[1], "Alert was not found")
        self.log.info(
            "Step 1: Show alert command with invalid alert id is failed with error %s",
            resp[1])
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-15727")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_247(self):
        """
        Test 'alerts acknowledge' with missing parameter throws error
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        self.log.info(
            "Step 1: Performing alerts acknowledge with missing parameter")
        resp = self.alert_obj.acknowledge_alert_cli(alert_id="")
        assert_utils.assert_equals(resp[0], False, resp)
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required: alerts_id")
        self.log.info(
            "Step 1: Alerts acknowledge with missing parameter is failed with error %s",
            resp[1])
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16933")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_252(self):
        """
        Test 'alerts comments -h' should show the help
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        cmd = "alerts comment"
        alert_comment_help = ["positional arguments:",
                            "{show,add}",
                            "show      Displays comments of a particular alert.",
                            "add       Add comment to an existing alert."]
        self.log.info(
            "Step 1: Verifying help option for alerts comments command")
        resp = self.alert_obj.help_option(command=cmd)
        self.log.debug(resp)
        assert_utils.assert_equals(resp[0], True, resp)
        result = all(
            msg in resp[1] for msg in alert_comment_help)
        assert_utils.assert_equals(result, True, result)
        self.log.info(
            "Step 1: Verified help option for alerts comments")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-17177")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_1440(self):
        """
        Test if we give negative value or wrong value for any of the options it should throw error
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        self.log.info(
            "Step 1: Verifying show alert command with negative value")
        resp = self.alert_obj.show_alerts_cli(duration="-1")
        assert_utils.assert_equals(resp[0], True, resp)
        assert_utils.assert_exact_string(resp[1], "Invalid Parameter for Duration")
        self.log.info(
            "Step 1: Verifying show alert command with negative value is failed with error %s",
            resp[1])
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())


    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-19238")
    @pytest.mark.skip(reason="Not applicable for VM")
    def test_1438(self):
        """
        Test if `alerts show -f <format> -d<>` displays alert in desired given format
        :avocado: tags=cli_alerts
        """
        self.log.info("%s %s", self.start_log, cortxlogging.get_frame())
        start_time = time.time()
        self.log.info("Step 1: Generating disk fault alert")
        resp = self.generate_alert_obj.generate_alert(
            AlertType.disk_fault_alert,
            input_parameters={
                "du_val": -3,
                "fault": True,
                "fault_resolved": False})
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info("Step 1: Generated disk fault alert")
        self.log.info("Step 2: Verifying alerts are generated")
        resp = self.alert_obj.wait_for_alert(start_time=start_time)
        assert_utils.assert_equals(resp[0], True, resp)
        end_time = time.time()
        duration = str(int(end_time - start_time)) + "s"
        self.log.info("Step 2: Verified alerts are generated")
        self.log.info("Step 3: Listing alerts in different formats")
        self.log.info("1. Listing alert in json format")
        resp = self.alert_obj.show_alerts_cli(
            duration=duration,
            limit=1,
            output_format="json")
        self.log.info("Output in json format %s", resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info("2. Listing alert in xml format")
        resp = self.alert_obj.show_alerts_cli(
            duration=duration,
            limit=1,
            output_format="xml")
        self.log.info("Output in xml format %s", resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info("3. Listing alert in table format")
        resp = self.alert_obj.show_alerts_cli(
            duration=duration,
            limit=1,
            output_format="table")
        self.log.info("Output in table format %s", resp)
        assert_utils.assert_equals(resp[0], True, resp)
        self.log.info("Step 3: Listed alerts in different formats")
        self.log.info("%s %s", self.end_log, cortxlogging.get_frame())
