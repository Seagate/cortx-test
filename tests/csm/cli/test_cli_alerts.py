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
"""CLI Alert Testsuit"""

import time
import logging
import pytest
from commons.utils import assert_utils
from commons.alerts_simulator.generate_alert_lib import \
    GenerateAlertLib, AlertType
from commons import cortxlogging
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts


ALERT_OBJ = CortxCliAlerts()
GENERATE_ALERT_OBJ = GenerateAlertLib()
LOGGER = logging.getLogger(__name__)
START_LOG_FORMAT = "##### Test started -  "
END_LOG_FORMAT = "##### Test Ended -  "


def setup_function():
    """
    This function will be invoked prior to each test function in the module.
    It is performing below operations as pre-requisites.
        - Login to CORTX CLI as admin user.
    """
    LOGGER.info("STARTED : Setup operations for test function")
    LOGGER.info("Login to CORTX CLI using admin")
    ALERT_OBJ.open_connection()
    login = ALERT_OBJ.login_cortx_cli()
    assert_utils.assert_equals(
        login[0], True, "Server authentication check failed")
    LOGGER.info("ENDED : Setup operations for test function")


def teardown_function():
    """
    This function will be invoked after each test function in the module.
    It is performing below operations.
        - Log out from CORTX CLI console.
    """
    LOGGER.info("STARTED : Teardown operations for test function")
    ALERT_OBJ.logout_cortx_cli()
    ALERT_OBJ.close_connection()
    LOGGER.info("Ended : Teardown operations for test function")


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14032")
@pytest.mark.skip(reason="Not applicable for VM")
def test_131():
    """
    Test alerts acknowledge <alert id> -ack should acknowledge the given alert
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    start_time = time.time()
    LOGGER.info("Step 1: Generating disk fault alert")
    resp = GENERATE_ALERT_OBJ.generate_alert(
        AlertType.disk_fault_alert,
        input_parameters={
            "du_val": -3,
            "fault": True,
            "fault_resolved": False})
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info("Step 1: Generated disk fault alert")
    LOGGER.info("Step 2: Verifying alerts are generated")
    resp = ALERT_OBJ.wait_for_alert(start_time=start_time)
    assert_utils.assert_equals(resp[0], True, resp)
    end_time = time.time()
    duration = "{0}{1}".format(
        int(end_time - start_time), "s")
    alert_id = resp[1]["alerts"][0]["alert_uuid"]
    LOGGER.info("Step 2: Verified alerts are generated")
    LOGGER.info(
        "Step 3: Acknowledge alert %s from given list", alert_id)
    resp = ALERT_OBJ.acknowledge_alert_cli(alert_id=alert_id)
    assert_utils.assert_equals(resp[0], True, resp)
    assert_utils.assert_exact_string(resp[1], "Alert Updated")
    LOGGER.info(
        "Step 3: Acknowledged alert %s from given list", alert_id)
    LOGGER.info("Step 4: Verifying alert is acknowledged")
    resp = ALERT_OBJ.show_alerts_cli(duration=duration,
                                     limit=1,
                                     output_format="json")
    LOGGER.info(resp)
    assert_utils.assert_equals(
        resp[1]["alerts"][0]["acknowledged"], True, resp[1])
    LOGGER.info("Step 4: Verified alert is acknowledged")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14031")
@pytest.mark.skip(reason="Not applicable for VM")
def test_6306():
    """
    Verify that all comments on alert is returned in table format on executing show alert command
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    start_time = time.time()
    LOGGER.info("Step 1: Generating disk fault alert")
    resp = GENERATE_ALERT_OBJ.generate_alert(
        AlertType.disk_fault_alert,
        input_parameters={
            "du_val": -3,
            "fault": True,
            "fault_resolved": False})
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info("Step 1: Generated disk fault alert")
    LOGGER.info("Step 2: Verifying alerts are generated")
    resp = ALERT_OBJ.wait_for_alert(start_time=start_time)
    assert_utils.assert_equals(resp[0], True, resp)
    alert_id = resp[1]["alerts"][0]["alert_uuid"]
    LOGGER.info("Step 2: Verified alerts are generated")
    LOGGER.info("Step 3: Adding comment to an alert")
    resp = ALERT_OBJ.add_comment_alert(
        alert_id, "Default_alert")
    assert_utils.assert_equals(resp[0], True, resp)
    assert_utils.assert_exact_string(resp[1], "Alert Comment Added")
    LOGGER.info("Step 3: Added comment to an alert")
    LOGGER.info(
        "Step 4: Verifying alert is returned in table format with all details")
    resp = ALERT_OBJ.show_alerts_comment_cli(alert_id)
    LOGGER.info(resp)
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info(
        "Step 4: Verified that alert is returned in table format with all details")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14662")
@pytest.mark.skip(reason="Not applicable for VM")
def test_3289(self):
    """
    csmcli alerts acknowledge <alert id> <comment> with invalid <alert id>
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    self.log.info(
        "Step 1: Acknowledge alert with invalid id")
    resp = ALERT_OBJ.acknowledge_alert_cli(alert_id="74659q349694-4r4r43")
    assert_utils.assert_equals(resp[0], False, resp)
    assert_utils.assert_exact_string(resp[1], "Alert was not found")
    self.log.info(
        "Step 3: Acknowledging alert with invalid id is failed with error %s",
        resp[1])
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14663")
@pytest.mark.skip(reason="Not applicable for VM")
def test_3290():
    """
    Test "csmcli alerts acknowledge" command
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    start_time = time.time()
    LOGGER.info("Step 1: Running ALERT API for generating fault")
    resp = GENERATE_ALERT_OBJ.generate_alert(
        AlertType.disk_fault_alert,
        input_parameters={
            "du_val": -3,
            "fault": True,
            "fault_resolved": False})
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info(
        "Step 1: Successfully run ALERT API for generating fault")
    LOGGER.info("Step 2: Verifying alerts are generated")
    resp = ALERT_OBJ.wait_for_alert(start_time=start_time)
    assert_utils.assert_equals(resp[0], True, resp)
    end_time = time.time()
    duration = "{0}{1}".format(
        int(end_time - start_time), "s")
    alert_id = resp[1]["alerts"][0]["alert_uuid"]
    LOGGER.info("Step 2: Verified alerts are generated")
    LOGGER.info(
        "Step 3: Acknowledge alert %s from given list", alert_id)
    resp = ALERT_OBJ.acknowledge_alert_cli(alert_id)
    assert_utils.assert_equals(resp[0], True, resp)
    assert_utils.assert_exact_string(resp[1], "Alert Updated")
    LOGGER.info(
        "Step 3: Acknowledged alert %s from given list", alert_id)
    LOGGER.info("Step 4: Verifying alert is acknowledged")
    resp = ALERT_OBJ.show_alerts_cli(
        duration=duration,
        limit=1,
        output_format="json")
    LOGGER.info(resp)
    assert_utils.assert_equals(
        resp[1]["alerts"][0]["acknowledged"], True, resp[1])
    LOGGER.info("Step 4: Verified alert is acknowledged")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14664")
@pytest.mark.skip(reason="Not applicable for VM")
def test_6309():
    """
    Test that help menu opens for both 'show'
    and 'add' comments options along with parameter details
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    LOGGER.info("Verifying help menu for show comment command")
    resp = ALERT_OBJ.show_alerts_comment_cli(help_param=True)
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info(resp[1])
    LOGGER.info("Verified help menu for show comment command")
    LOGGER.info("Verifying help menu for add comment command")
    resp = ALERT_OBJ.add_comment_alert(help_param=True)
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info(resp[1])
    LOGGER.info("Verified help menu for add comment command")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14754")
@pytest.mark.skip(reason="Not applicable for VM")
def test_245():
    """
    Test 'alerts acknowledge <wrong_alert id> -ack' should give error message
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    LOGGER.info(
        "Step 1: Acknowledge alert with invalid id")
    resp = ALERT_OBJ.acknowledge_alert_cli(alert_id="74659q349694-4r4r43-cc")
    assert_utils.assert_equals(resp[0], False, resp)
    assert_utils.assert_exact_string(resp[1], "Alert was not found")
    LOGGER.info(
        "Step 3: Acknowledging alert with invalid id is failed with error %s",
        resp[1])
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-14755")
@pytest.mark.skip(reason="Not applicable for VM")
def test_3288():
    """
    Test "csmcli alerts acknowledge" command
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    start_time = time.time()
    LOGGER.info("Step 1: Running ALERT API for generating fault")
    resp = GENERATE_ALERT_OBJ.generate_alert(
        AlertType.disk_fault_alert,
        input_parameters={
            "du_val": -3,
            "fault": True,
            "fault_resolved": False})
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info(
        "Step 1: Successfully run ALERT API for generating fault")
    LOGGER.info("Step 2: Verifying alerts are generated")
    resp = ALERT_OBJ.wait_for_alert(start_time=start_time)
    assert_utils.assert_equals(resp[0], True, resp)
    end_time = time.time()
    duration = "{0}{1}".format(
        int(end_time - start_time), "s")
    alert_id = resp[1]["alerts"][0]["alert_uuid"]
    LOGGER.info("Step 2: Verified alerts are generated")
    LOGGER.info(
        "Step 3: Acknowledge alert %s from given list", alert_id)
    resp = ALERT_OBJ.acknowledge_alert_cli(alert_id)
    assert_utils.assert_equals(resp[0], True, resp)
    assert_utils.assert_exact_string(resp[1], "Alert Updated")
    LOGGER.info(
        "Step 3: Acknowledged alert %s from given list", alert_id)
    LOGGER.info("Step 4: Verifying alert is acknowledged")
    resp = ALERT_OBJ.show_alerts_cli(
        duration=duration,
        limit=1,
        output_format="json")
    LOGGER.info(resp)
    assert_utils.assert_equals(
        resp[1]["alerts"][0]["acknowledged"], True, resp[1])
    LOGGER.info("Step 4: Verified alert is acknowledged")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-15199")
@pytest.mark.skip(reason="Not applicable for VM")
def test_6308():
    """
    Test that error is returned when wrong alert_uuid is entered in show alert command
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    LOGGER.info(
        "Step 1: Performing show alert command with invalid alert id")
    resp = ALERT_OBJ.show_alerts_comment_cli(alert_id="74659q349694-4r4r43-cc")
    assert_utils.assert_equals(resp[0], False, resp)
    assert_utils.assert_exact_string(resp[1], "Alert was not found")
    LOGGER.info(
        "Step 1: Show alert command with invalid alert id is failed with error %s",
        resp[1])
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-15727")
@pytest.mark.skip(reason="Not applicable for VM")
def test_247(self):
    """
    Test 'alerts acknowledge' with missing parameter throws error
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    self.log.info(
        "Step 1: Performing alerts acknowledge with missing parameter")
    resp = ALERT_OBJ.acknowledge_alert_cli(alert_id="")
    assert_utils.assert_equals(resp[0], False, resp)
    assert_utils.assert_exact_string(
        resp[1], "The following arguments are required: alerts_id")
    self.log.info(
        "Step 1: Alerts acknowledge with missing parameter is failed with error %s",
        resp[1])
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-16933")
@pytest.mark.skip(reason="Not applicable for VM")
def test_252():
    """
    Test 'alerts comments -h' should show the help
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    cmd = "alerts comment"
    alert_comment_help = ["positional arguments:",
                          "{show,add}",
                          "show      Displays comments of a particular alert.",
                          "add       Add comment to an existing alert."]
    LOGGER.info(
        "Step 1: Verifying help option for alerts comments command")
    resp = ALERT_OBJ.help_option(command=cmd)
    LOGGER.debug(resp)
    assert_utils.assert_equals(resp[0], True, resp)
    result = all(
        msg in resp[1] for msg in alert_comment_help)
    assert_utils.assert_equals(result, True, result)
    LOGGER.info(
        "Step 1: Verified help option for alerts comments")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-17177")
@pytest.mark.skip(reason="Not applicable for VM")
def test_1440():
    """
    Test if we give negative value or wrong value for any of the options it should throw error
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    LOGGER.info(
        "Step 1: Verifying show alert command with negative value")
    resp = ALERT_OBJ.show_alerts_cli(duration="-1")
    assert_utils.assert_equals(resp[0], True, resp)
    assert_utils.assert_exact_string(resp[1], "Invalid Parameter for Duration")
    LOGGER.info(
        "Step 1: Verifying show alert command with negative value is failed with error %s",
        resp[1])
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())


@pytest.mark.cluster_user_ops
@pytest.mark.csm_cli
@pytest.mark.tags("TEST-19238")
@pytest.mark.skip(reason="Not applicable for VM")
def test_1438():
    """
    Test if `alerts show -f <format> -d<>` displays alert in desired given format
    :avocado: tags=cli_alerts
    """
    LOGGER.info("%s %s", START_LOG_FORMAT, cortxlogging.get_frame())
    start_time = time.time()
    LOGGER.info("Step 1: Generating disk fault alert")
    resp = GENERATE_ALERT_OBJ.generate_alert(
        AlertType.disk_fault_alert,
        input_parameters={
            "du_val": -3,
            "fault": True,
            "fault_resolved": False})
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info("Step 1: Generated disk fault alert")
    LOGGER.info("Step 2: Verifying alerts are generated")
    resp = ALERT_OBJ.wait_for_alert(start_time=start_time)
    assert_utils.assert_equals(resp[0], True, resp)
    end_time = time.time()
    duration = "{0}{1}".format(
        int(end_time - start_time), "s")
    LOGGER.info("Step 2: Verified alerts are generated")
    LOGGER.info("Step 3: Listing alerts in different formats")
    LOGGER.info("1. Listing alert in json format")
    resp = ALERT_OBJ.show_alerts_cli(
        duration=duration,
        limit=1,
        output_format="json")
    LOGGER.info("Output in json format %s", resp)
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info("2. Listing alert in xml format")
    resp = ALERT_OBJ.show_alerts_cli(
        duration=duration,
        limit=1,
        output_format="xml")
    LOGGER.info("Output in xml format %s", resp)
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info("3. Listing alert in table format")
    resp = ALERT_OBJ.show_alerts_cli(
        duration=duration,
        limit=1,
        output_format="table")
    LOGGER.info("Output in table format %s", resp)
    assert_utils.assert_equals(resp[0], True, resp)
    LOGGER.info("Step 3: Listed alerts in different formats")
    LOGGER.info("%s %s", END_LOG_FORMAT, cortxlogging.get_frame())
