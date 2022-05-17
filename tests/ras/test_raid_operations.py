#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
RAS test file for all the RAS tests related to RAID operations.
"""

import logging
import os
import time

import pytest

from commons import commands as common_cmds
from commons import constants as common_cons
from commons.alerts_simulator.generate_alert_lib import AlertType
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import system_utils as sys_utils
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.s3 import S3H_OBJ

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class TestRAIDOperations:
    """
    Test suite for performing RAID related operations
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.hlt_obj = Health(hostname=cls.host, username=cls.uname,
                             password=cls.passwd)
        cls.ras_obj = RASTestLib(host=cls.host, username=cls.uname,
                                 password=cls.passwd)
        cls.csm_alert_obj = SystemAlerts(cls.nd_obj)
        cls.alert_api_obj = GenerateAlertLib()
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.s3obj = S3H_OBJ
        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        Setup operations for each test.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.md_device = RAS_VAL["raid_param"]["md0_path"]
        self.raid_stopped = False
        self.failed_disk = False
        self.removed_disk = False
        # Enable this flag for starting RMQ channel
        self.start_rmq = self.cm_cfg["start_rmq"]

        LOGGER.info("Fetching the disks details from mdstat for RAID array %s", self.md_device)
        md_stat = self.nd_obj.get_mdstat()
        self.disks = md_stat["devices"][os.path.basename(self.md_device)]["disks"].keys()
        self.disk1 = RAS_VAL["raid_param"]["disk_path"].format(list(self.disks)[0])
        self.disk2 = RAS_VAL["raid_param"]["disk_path"].format(list(self.disks)[1])

        LOGGER.info("Updating transmit interval value to 10")
        res = self.ras_obj.update_threshold_values(
            common_cons.KV_STORE_DISK_USAGE,
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_key"],
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_val"])
        assert res

        LOGGER.info("Delete keys with prefix SSPL_")
        cmd = common_cmds.REMOVE_UNWANTED_CONSUL
        response = sys_utils.run_remote_cmd(cmd=cmd, hostname=self.host,
                                            username=self.uname,
                                            password=self.passwd,
                                            read_nbytes=common_cons.BYTES_TO_READ,
                                            shell=False)
        assert response[0], response[1]

        LOGGER.info("Restarting sspl service")
        self.hlt_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"])
        time.sleep(self.cm_cfg["sspl_timeout"])

        LOGGER.info(
            "Verifying the status of sspl and rabittmq service is online")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]

        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["rabitmq_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info(
            "Validated the status of sspl and rabittmq service are online")

        if self.start_rmq:
            LOGGER.info("Running rabbitmq_reader.py script on node")
            resp = self.ras_obj.start_rabbitmq_reader_cmd(self.cm_cfg["sspl_exch"],
                                                          self.cm_cfg["sspl_key"])
            assert resp
            LOGGER.info("Successfully started rabbitmq_reader.py script on node")

        res = self.ras_obj.sspl_log_collect()
        assert res[0], res[1]
        self.starttime = time.time()
        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        Teardown operations after each test.
        """
        LOGGER.info("STARTED: Teardown Operations")
        if self.failed_disk:
            resp = self.alert_api_obj.generate_alert(
                AlertType.RAID_REMOVE_DISK_ALERT,
                input_parameters={
                    "operation": RAS_VAL["raid_param"]["remove_operation"],
                    "md_device": self.md_device,
                    "disk": self.failed_disk})
            assert resp[0], resp[1]
            self.removed_disk = self.failed_disk

        if self.removed_disk:
            resp = self.alert_api_obj.generate_alert(
                AlertType.RAID_ADD_DISK_ALERT,
                input_parameters={
                    "operation": RAS_VAL["raid_param"]["add_operation"],
                    "md_device": self.md_device,
                    "disk": self.removed_disk})
            assert resp[0], resp[1]

        LOGGER.info("Updating transmit interval value")
        res = self.ras_obj.update_threshold_values(
            common_cons.KV_STORE_DISK_USAGE,
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_key"],
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_dval"])
        assert res

        if self.start_rmq:
            LOGGER.info("Terminating the process rabbitmq_reader.py")
            self.ras_obj.kill_remote_process("rabbitmq_reader.py")

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.nd_obj.read_file(filename=self.cm_cfg["file"]["sspl_log_file"],
                                          local_path=self.cm_cfg["file"]["local_path"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")

        LOGGER.info(
            "Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        self.nd_obj.remove_file(filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_rmq:
            LOGGER.info("Removing alert log file from the Node")
            self.nd_obj.remove_file(
                filename=self.cm_cfg["file"]["alert_log_file"])
            self.nd_obj.remove_file(
                filename=self.cm_cfg["file"]["extracted_alert_file"])
            LOGGER.info("Removing screen log file")
            self.nd_obj.remove_file(filename=self.cm_cfg["file"]["screen_log"])

        self.hlt_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"])
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("ENDED: Teardown Operations")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.tags("TEST-15733")
    @pytest.mark.sw_alert
    @pytest.mark.skip
    @CTFailOn(error_handler)
    def test_5345(self):
        """
        EOS-10613 RAID: Assemble a array
        """
        LOGGER.info(
            "STARTED: TEST-5345 RAID: Assemble a array")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_5345"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "stopping array")
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_STOP_DEVICE_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["stop_operation"],
                "md_device": self.md_device,
                "disk": None})
        assert resp[0], resp[1]
        self.raid_stopped = True
        LOGGER.info("Step 1: Ran ALERT API for generating RAID fault alert by "
                    "stopping array")

        if self.start_rmq:
            LOGGER.info("Step 2: Checking the generated RAID fault alert on RMQ"
                        " channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"]]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID fault_resolved "
            "alert by assembling array")
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_ASSEMBLE_DEVICE_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["assemble_operation"],
                "md_device": self.md_device,
                "disk": None})
        assert resp[0], resp[1]
        self.raid_stopped = False
        LOGGER.info("Step 4: Ran ALERT API for generating RAID fault_resolved "
                    "alerts by assembling array")

        if self.start_rmq:
            LOGGER.info("Step 5: Checking the generated RAID fault alert on RMQ"
                        " channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault_resolved"]]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 5: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info(
            "Step 6: Checking CSM REST API for RAID fault_resolved alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault_resolved"],
            True,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info("Step 6: Successfully verified RAID fault_resolved alert "
                    "using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-5345 RAID: Assemble a array")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.tags("TEST-15732")
    @pytest.mark.sw_alert
    @pytest.mark.skip
    @CTFailOn(error_handler)
    def test_5342(self):
        """
        EOS-10615 RAID: Remove a drive from array
        """
        LOGGER.info(
            "STARTED: TEST-5342 RAID: Remove a drive from array")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_5342"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_FAIL_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0], resp[1]
        self.failed_disk = self.disk2
        resource_id = "{}:{}".format(self.md_device, self.disk2)
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing "
            "a disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel"
                " logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"], resource_id]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_REMOVE_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0], resp[1]
        self.removed_disk = self.disk2
        self.failed_disk = False
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID missing alert "
            "by removing faulty disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on RMQ "
                "channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_missing"], resource_id]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on RMQ channel logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_missing"],
            False,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info("Step 6: Successfully verified RAID missing alert using CSM"
                    " REST API")
        LOGGER.info(
            "ENDED: TEST-5342 RAID: Remove a drive from array")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.tags("TEST-15868")
    @pytest.mark.sw_alert
    @pytest.mark.skip
    @CTFailOn(error_handler)
    def test_4785(self):
        """
        EOS-10617 RAID: Fail a drive of array
        """
        LOGGER.info(
            "STARTED: TEST-4785 RAID: Fail a drive of array")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_4785"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_FAIL_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0], resp[1]
        self.failed_disk = self.disk2
        resource_id = "{}:{}".format(self.md_device, self.disk2)
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing "
            "a disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel"
                " logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"], resource_id]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-4785 RAID: Fail a drive of array")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.tags("TEST-16214")
    @pytest.mark.sw_alert
    @pytest.mark.skip
    @CTFailOn(error_handler)
    def test_5343(self):
        """
        EOS-10614 RAID: Add drive to array
        """
        LOGGER.info(
            "STARTED: TEST-5343 RAID: Add drive to array")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_5343"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_FAIL_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0], resp[1]
        self.failed_disk = self.disk2
        resource_id = "{}:{}".format(self.md_device, self.disk2)
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing "
            "a disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel"
                " logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"], resource_id]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_REMOVE_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0], resp[1]
        self.failed_disk = False
        self.removed_disk = self.disk2
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID missing alert by "
            "removing faulty disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on RMQ "
                "channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_missing"], resource_id]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on RMQ channel logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_missing"],
            False,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info("Step 6: Successfully verified RAID missing alert using CSM"
                    " REST API")

        LOGGER.info(
            "Step 7: Running ALERT API for generating RAID fault_resolved alert"
            "by adding removed disk %s to array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_ADD_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["add_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 7: Ran ALERT API for generating RAID fault_resolved alert "
            "by adding removed disk to array")

        md_stat = resp[1]
        if self.start_rmq:
            LOGGER.info("Step 8: Checking the generated RAID insertion alert on"
                        " RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_insertion"], resource_id]
            resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                 restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 8: Verified the RAID insertion alert on RMQ channel logs")

        LOGGER.info("Step 9: Checking CSM REST API for RAID insertion alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_insertion"],
            True,
            test_cfg["resource_type"])
        assert resp, csm_error_msg
        LOGGER.info("Step 9: Successfully verified RAID insertion alert using "
                    "CSM REST API")

        if not all(md_stat["devices"][os.path.basename(self.md_device)]["status"]["synced"]):
            time.sleep(raid_cmn_cfg["resync_delay"])

        if all(md_stat["devices"][os.path.basename(self.md_device)]["status"]["synced"]):
            if self.start_rmq:
                LOGGER.info("Step 10: Checking the generated RAID "
                            "fault_resolved alert on RMQ channel logs")
                alert_list = [test_cfg["resource_type"],
                              test_cfg["alert_fault_resolved"], resource_id]
                resp = self.ras_obj.alert_validation(string_list=alert_list,
                                                     restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 10: Verified the RAID fault_resolved alert on"
                            " RMQ channel logs")

            LOGGER.info(
                "Step 11: Checking CSM REST API for RAID fault_resolved alert")
            time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                test_cfg["alert_fault_resolved"],
                True,
                test_cfg["resource_type"])
            assert resp, csm_error_msg
        self.removed_disk = False
        LOGGER.info("Step 11: Successfully verified RAID fault_resolved alert "
                    "using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-5343 RAID: Add drive to array")
