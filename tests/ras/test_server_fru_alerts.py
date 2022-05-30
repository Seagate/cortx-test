#!/usr/bin/python # pylint: disable=C0302
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

"""Test suite for server fru related tests"""

import ast
import logging
import os
import random
import time

import pandas as pd
import pytest

from commons import commands as common_cmd
from commons import constants as cons
from commons.alerts_simulator.generate_alert_lib import AlertType
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.bmc_helper import Bmc
from commons.helpers.controller_helper import ControllerLib
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import RAS_TEST_CFG
from config import RAS_VAL
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.s3 import S3H_OBJ

LOGGER = logging.getLogger(__name__)


class TestServerFruAlerts:
    """SSPL Server FRU Test Suite."""

    # pylint: disable=R0902
    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.node_cnt = len(CMN_CFG["nodes"])
        LOGGER.info("Total number of nodes in cluster: %s", cls.node_cnt)

        LOGGER.info("Randomly picking node to create fault")
        cls.system_random = random.SystemRandom()
        cls.test_node = cls.system_random.randint(1, cls.node_cnt)

        LOGGER.info("Fault testing will be done on node: %s", cls.test_node)
        cls.host = CMN_CFG["nodes"][cls.test_node-1]["host"]
        cls.uname = CMN_CFG["nodes"][cls.test_node-1]["username"]
        cls.passwd = CMN_CFG["nodes"][cls.test_node-1]["password"]
        cls.hostname = CMN_CFG["nodes"][cls.test_node-1]["hostname"]
        cls.lpdu_details = CMN_CFG["nodes"][cls.test_node-1]["lpdu"]
        cls.rpdu_details = CMN_CFG["nodes"][cls.test_node - 1]["rpdu"]

        cls.ras_test_obj = RASTestLib(host=cls.hostname, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.hostname, username=cls.uname,
                            password=cls.passwd)
        cls.bmc_obj = Bmc(hostname=cls.hostname, username=cls.uname,
                          password=cls.passwd)
        cls.health_obj = Health(hostname=cls.hostname, username=cls.uname,
                                password=cls.passwd)
        cls.controller_obj = ControllerLib(
            host=cls.hostname, h_user=cls.uname, h_pwd=cls.passwd,
            enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
            enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
            enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])

        cls.alert_api_obj = GenerateAlertLib()
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        # Enable this flag for starting RMQ channel
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.s3obj = S3H_OBJ
        cls.alert_types = RAS_TEST_CFG["alert_types"]
        cls.sspl_resource_id = cls.cm_cfg["sspl_resource_id"]

        node_d = cls.health_obj.get_current_srvnode()
        cls.current_srvnode = node_d[cls.hostname.split('.')[0]] if \
            cls.hostname.split('.')[0] in node_d.keys() else assert_utils.assert_true(
            False, "Node name not found")

        LOGGER.info("Creating objects for all the nodes in cluster")
        objs = cls.ras_test_obj.create_obj_for_nodes(ras_c=RASTestLib,
                                                     node_c=Node,
                                                     hlt_c=Health,
                                                     ctrl_c=ControllerLib,
                                                     bmc_c=Bmc)

        for i, key in enumerate(objs.keys()):
            globals()[f"srv{i+1}_hlt"] = objs[key]['hlt_obj']
            globals()[f"srv{i+1}_ras"] = objs[key]['ras_obj']
            globals()[f"srv{i+1}_nd"] = objs[key]['nd_obj']
            globals()[f"srv{i+1}_bmc"] = objs[key]['bmc_obj']

        cls.md_device = RAS_VAL["raid_param"]["md0_path"]
        cls.server_psu_fault = False
        LOGGER.info("Successfully ran setup_class")

    # pylint: disable=too-many-statements
    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        self.starttime = time.time()
        LOGGER.info("Check cluster health")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"], False)

        LOGGER.info("Performing Setup operations")

        LOGGER.info("Checking SSPL state file")
        res = self.ras_test_obj.get_sspl_state()
        if not res:
            LOGGER.info("SSPL not present updating same on server")
            response = self.ras_test_obj.check_status_file()
            assert response[0], response[1]
        LOGGER.info("Done Checking SSPL state file")

        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd()
            assert_utils.assert_true(
                resp, "Failed to start message bus channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Change sspl log level to DEBUG")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "DEBUG"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting SSPL service")
        service = self.cm_cfg["service"]
        services = [service["sspl_service"], service["kafka_service"]]
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])

        for svc in services:
            LOGGER.info("Checking status of %s service", svc)
            resp = self.s3obj.get_s3server_service_status(service=svc,
                                                          host=self.hostname,
                                                          user=self.uname,
                                                          pwd=self.passwd)
            assert resp[0], resp[1]
            LOGGER.info("%s service is active/running", svc)

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")

        self.raid_stopped = False
        self.failed_disk = False
        self.removed_disk = False
        self.server_psu_fault = False
        LOGGER.info(
            "Fetching the disks details from mdstat for RAID array %s",
            self.md_device)
        md_stat = self.node_obj.get_mdstat()
        self.disks = md_stat["devices"][os.path.basename(
            self.md_device)]["disks"].keys()
        if len(self.disks) >= 2:
            self.disk1 = RAS_VAL["raid_param"]["disk_path"].format(
                list(self.disks)[0])
            self.disk2 = RAS_VAL["raid_param"]["disk_path"].format(
                list(self.disks)[1])
        else:
            LOGGER.error("Not enough disks in raid array to perform operations: %s", self.disks)

        LOGGER.info("Successfully performed Setup operations")

    # pylint: disable=too-many-statements
    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        self.ras_test_obj.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"], True)

        if self.failed_disk:
            resp = self.alert_api_obj.generate_alert(
                AlertType.RAID_REMOVE_DISK_ALERT,
                input_parameters={
                    "operation": RAS_VAL["raid_param"]["remove_operation"],
                    "md_device": self.md_device,
                    "disk": self.failed_disk})
            assert_utils.assert_true(resp[0], resp[1])
            self.removed_disk = self.failed_disk

        if self.removed_disk:
            resp = self.alert_api_obj.generate_alert(
                AlertType.RAID_ADD_DISK_ALERT,
                input_parameters={
                    "operation": RAS_VAL["raid_param"]["add_operation"],
                    "md_device": self.md_device,
                    "disk": self.removed_disk})
            assert_utils.assert_true(resp[0], resp[1])

        if self.raid_stopped:
            resp = self.alert_api_obj.generate_alert(
                AlertType.RAID_ASSEMBLE_DEVICE_ALERT,
                input_parameters={
                    "operation": RAS_VAL["raid_param"]["assemble_operation"],
                    "md_device": self.raid_stopped,
                    "disk": None})
            assert_utils.assert_true(resp[0], resp[1])

        if self.server_psu_fault:
            resp = self.alert_api_obj.generate_alert(
                AlertType.SERVER_PSU_FAULT_RESOLVED)
            assert_utils.assert_true(resp[0], resp[1])

        if self.power_failure_flag:
            test_cfg = RAS_TEST_CFG["power_failure"]
            other_node = self.test_node - 1 if self.test_node > 1 else self.test_node + 1
            other_host = CMN_CFG["nodes"][other_node - 1]["hostname"]

            LOGGER.info("Powering on node %s from node %s",
                        self.hostname, other_host)
            status = test_cfg["power_on"]
            if test_cfg["bmc_shutdown"]:
                LOGGER.info("Using BMC ip")
                bmc_user = CMN_CFG["bmc"]["username"]
                bmc_pwd = CMN_CFG["bmc"]["password"]
                res = self.bmc_obj.bmc_node_power_on_off(bmc_user=bmc_user,
                                                         bmc_pwd=bmc_pwd,
                                                         status=status)
            else:
                LOGGER.info("Using PDU ip")
                LOGGER.info("Making left pdu port up")
                cmd = f"srv{other_node}_nd.toggle_apc_node_power(" \
                      f"pdu_ip='{self.lpdu_details['ip']}', " \
                      f"pdu_user='{self.lpdu_details['user']}', " \
                      f"pdu_pwd='{self.lpdu_details['pwd']}', " \
                      f"node_slot='{self.lpdu_details['port']}', " \
                      f"status='{status}')"
                LOGGER.info("Command: %s", cmd)
                res = ast.literal_eval(cmd)
                LOGGER.debug(res)
                LOGGER.info("Making right pdu port up")
                cmd = f"srv{other_node}_nd.toggle_apc_node_power(" \
                      f"pdu_ip='{self.rpdu_details['ip']}', " \
                      f"pdu_user='{self.rpdu_details['user']}', " \
                      f"pdu_pwd='{self.rpdu_details['pwd']}', " \
                      f"node_slot='{self.rpdu_details['port']}', " \
                      f"status='{status}')"
                LOGGER.info("Command: %s", cmd)
                res = ast.literal_eval(cmd)
            LOGGER.debug(res)
            self.power_failure_flag = False
            time.sleep(test_cfg["wait_10_min"])
            LOGGER.info("Successfully powered on node using APC/BMC.")

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        if os.path.exists(self.cm_cfg["file"]["telnet_xml"]):
            LOGGER.info("Remove telnet file")
            os.remove(self.cm_cfg["file"]["telnet_xml"])

        if self.node_obj.path_exists(
                RAS_VAL["ras_sspl_alert"]["file"]["disk_usage_temp_file"]):
            LOGGER.info("Remove temp disk usage file")
            self.node_obj.remove_file(
                filename=RAS_VAL["ras_sspl_alert"]["file"]
                ["disk_usage_temp_file"])

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.node_obj.read_file(
            filename=self.cm_cfg["file"]["sspl_log_file"],
            local_path=self.cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")

        LOGGER.info(
            "Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        self.node_obj.remove_remote_file(
            filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_msg_bus:
            LOGGER.info("Terminating the process read_message_bus.py")
            self.ras_test_obj.kill_remote_process("read_message_bus.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                self.node_obj.remove_remote_file(filename=file)

        LOGGER.info("Restarting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Successfully performed Teardown operation")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23606")
    @CTFailOn(error_handler)
    def test_disable_enable_os_drive_23606(self):
        """
        TEST-23606: Test verifies fault and fault resolved alert in message
        bus and CSM REST after disabling and enabling a node drive.
        """
        LOGGER.info("STARTED: Test alerts for OS disk removal and insertion")

        test_cfg = RAS_TEST_CFG["TEST-23606"]
        d_f = pd.DataFrame(index='Step1 Step2 Step3 Step4 Step5 Step6'.split(),
                           columns='Iteration0'.split())
        d_f = d_f.assign(Iteration0='Pass')

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Getting RAID array details of node %s",
                    self.hostname)
        resp = self.ras_test_obj.get_raid_array_details()
        if not resp[0]:
            d_f['Iteration0']['Step1'] = 'Fail'
        md_arrays = resp[1] if resp[0] else assert_utils.assert_true(
            resp[0], "Step 1: Failed" " to get raid " "array details")

        LOGGER.info("MDRAID arrays: %s", md_arrays)
        for k_k, v_v in md_arrays.items():
            if v_v["state"] != "Active":
                d_f['Iteration0']['Step1'] = 'Fail'
                assert_utils.assert_true(
                    False, f"Step 1: Array {k_k} is in degraded state")

        LOGGER.info("Step 1: Getting details of drive to be removed")
        resp = self.ras_test_obj.get_node_drive_details()
        if not resp[0]:
            d_f['Iteration0']['Step1'] = 'Fail'

        assert_utils.assert_true(
            resp[0],
            f"Step 1: Failed to get details of OS disks. "
            f"Response: {resp}")

        drive_name = resp[1].split("/")[2]
        host_num = resp[2]
        drive_count = resp[3]
        LOGGER.info("Step 1: Drive details:\nOS drive name: %s \n"
                    "Host number: %s \nOS Drive count: %s \n",
                    drive_name, host_num, drive_count)

        LOGGER.info("Creating fault...")
        LOGGER.info("Step 2: Disconnecting OS drive %s", drive_name)
        resp = self.alert_api_obj.generate_alert(
            AlertType.OS_DISK_DISABLE,
            host_details={"host": self.hostname, "host_user": self.uname,
                          "host_password": self.passwd},
            input_parameters={"drive_name": drive_name.split("/")[-1],
                              "drive_count": drive_count})
        if not resp[0]:
            d_f['Iteration0']['Step2'] = 'Fail'
            LOGGER.error("Step 2: Failed to create fault. Error: %s", resp[1])
        else:
            LOGGER.info(
                "Step 2: Successfully disabled/disconnected drive %s\n "
                "Response: %s", drive_name, resp)

        time.sleep(self.cm_cfg["sleep_val"])
        LOGGER.info("Check health of node %s", self.test_node)
        resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
        assert_utils.assert_true(resp[0], resp[1])

        if self.start_msg_bus:
            LOGGER.info("Step 3: Verifying alert logs for fault alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types[
                "missing"], f"srvnode-{self.test_node}.mgmt.public"]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step3'] = 'Fail'
                LOGGER.error("Step 3: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 3: Checked generated alert logs. Response: "
                            "%s", resp)

        LOGGER.info("Step 4: Checking CSM REST API for alert")
        resp_csm = self.csm_alert_obj.verify_csm_response(
            self.starttime, self.alert_types["missing"], False, test_cfg["resource_type"])

        if not resp_csm:
            d_f['Iteration0']['Step4'] = 'Fail'
            LOGGER.error("Step 4: Expected alert not found. Error: %s",
                         test_cfg["csm_error_msg"])
        else:
            LOGGER.info("Step 4: Successfully checked CSM REST API for "
                        "fault alert. Response: %s", resp_csm)

        LOGGER.info("Resolving fault...")
        LOGGER.info("Step 5: Connecting OS drive %s", drive_name)
        resp = self.alert_api_obj.generate_alert(
            AlertType.OS_DISK_ENABLE,
            host_details={"host": self.hostname, "host_user": self.uname,
                          "host_password": self.passwd},
            input_parameters={"host_num": host_num,
                              "drive_count": drive_count})

        if not resp[0]:
            d_f['Iteration0']['Step5'] = 'Fail'
            LOGGER.error("Step 5: Failed to resolve fault.")
        else:
            LOGGER.info(
                "Step 5: Successfully connected disk %s\n Response: %s",
                resp[1],
                resp)

        new_drive = resp[1]
        LOGGER.info("Starting RAID recovery...")
        LOGGER.info("Step 6: Getting raid partitions of drive %s", new_drive)
        resp = self.ras_test_obj.get_drive_partition_details(
            filepath=RAS_VAL['ras_sspl_alert']['file']['fdisk_file'],
            drive=new_drive)
        if not resp[0]:
            d_f['Iteration0']['Step6'] = 'Fail'
        raid_parts = resp[1] if resp[0] else assert_utils.assert_true(
            resp[0], f"Step 6: Failed to " f"get partition " f"details of " f"{new_drive}")

        LOGGER.info("Step 7: Adding raid partitions of drive %s in raid array",
                    new_drive)
        resp = self.ras_test_obj.add_raid_partitions(
            alert_lib_obj=self.alert_api_obj, alert_type=AlertType,
            raid_parts=raid_parts, md_arrays=md_arrays)
        if not resp[0]:
            d_f['Iteration0']['Step7'] = 'Fail'
        new_array = resp[1] if resp[0] else assert_utils.assert_true(
            resp[0], "Step 7: Failed to " "add drive in raid " "array")
        LOGGER.info("New MDARRAY: %s", new_array)

        time.sleep(self.cm_cfg["sleep_val"])
        LOGGER.info("Check health of node %s", self.test_node)
        resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
        assert_utils.assert_true(resp[0], resp[1])

        if self.start_msg_bus:
            LOGGER.info("Step 8: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"],
                          self.alert_types["insertion"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step8'] = 'Fail'
                LOGGER.error("Step 8: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info(
                    "Step 8: Successfully checked generated alert logs\n "
                    "Response: %s", resp)

        LOGGER.info("Step 9: Checking CSM REST API for alert")
        resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                          self.alert_types[
                                                              "insertion"],
                                                          True,
                                                          test_cfg[
                                                              "resource_type"])

        if not resp_csm:
            d_f['Iteration0']['Step9'] = 'Fail'
            LOGGER.error("Step 9: Expected alert not found. Error: %s",
                         test_cfg["csm_error_msg"])
        else:
            LOGGER.info("Step 9: Successfully checked CSM REST API for "
                        "fault alert. Response: %s", resp_csm)

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("Summary of test: %s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(
            result,
            "Test failed. Please check summary for failed "
            "step.")
        LOGGER.info("ENDED: Test alerts for OS disk removal and insertion")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23622")
    @CTFailOn(error_handler)
    def test_os_disk_alert_persistent_node_reboot_23622(self):
        """
        TEST-23622: Test verifies fault and fault resolved alerts of OS disk
        are persistent across node reboot.
        """
        LOGGER.info("STARTED: Test alerts for OS disk are persistent across "
                    "node reboot")

        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["TEST-23606"]

        LOGGER.info("Getting details of drive on which faults are to "
                    "be created")
        resp = self.ras_test_obj.get_node_drive_details()
        assert_utils.assert_true(
            resp[0], f"Failed to get details of OS disks. "
            f"Response: {resp}")

        drive_name = resp[1].split("/")[2]
        host_num = resp[2]
        drive_count = resp[3]
        LOGGER.info("Drive details:\nOS drive name: %s \n"
                    "Host number: %s \nOS Drive count: %s \n",
                    drive_name, host_num, drive_count)

        os_disk_faults = {
            'availability': {'alert_enum': AlertType.OS_DISK_DISABLE,
                             'resolve_enum': AlertType.OS_DISK_ENABLE,
                             'fault_alert': self.alert_types["missing"],
                             'resolved_alert': self.alert_types["insertion"]
                             }
        }
        d_f = pd.DataFrame(columns=f"{list(os_disk_faults.keys())[0]} ".split(),
                           index='Step1 Step2 Step3 Step4 Step5 Step6 '
                                 'Step7 Step8'.split())

        for key, value in os_disk_faults.items():
            d_f[key] = 'Pass'
            alert_enum = value['alert_enum']
            resolve_enum = value['resolve_enum']
            fault_alert = value['fault_alert']
            resolved_alert = value['resolved_alert']

            LOGGER.info("Step 1: Getting RAID array details of node %s",
                        self.hostname)
            resp = self.ras_test_obj.get_raid_array_details()
            if not resp[0]:
                d_f['Iteration0']['Step1'] = 'Fail'
            md_arrays = resp[1] if resp[0] else assert_utils.assert_true(
                resp[0], "Step 1: Failed" " to get raid " "array details")

            LOGGER.info("MDRAID arrays: %s", md_arrays)
            for k_k, v_v in md_arrays.items():
                if v_v["state"] != "Active":
                    d_f['Iteration0']['Step1'] = 'Fail'
                    assert_utils.assert_true(
                        False, f"Step 1: Array {k_k} is in degraded state")

            LOGGER.info("Step 1: Generating %s os disk fault on drive %s",
                        key, drive_name)
            resp = self.alert_api_obj.generate_alert(
                alert_enum,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"drive_name": drive_name,
                                  "drive_count": drive_count})
            if not resp[0]:
                d_f[key]['Step1'] = 'Fail'
                LOGGER.error("Step 1: Failed to create fault. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 1: Successfully created fault on disk %s\n "
                            "Response: %s", drive_name, resp)

            time.sleep(self.cm_cfg["sleep_val"])
            LOGGER.info("Check health of node %s", self.test_node)
            resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
            # Revisit when health state information is available
            LOGGER.info("Response: %s", resp)

            if self.start_msg_bus:
                LOGGER.info("Step 2: Verifying alert logs for fault alert ")
                alert_list = [test_cfg["resource_type"],
                              fault_alert]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    d_f[key]['Step2'] = 'Fail'
                    LOGGER.error("Step 2: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 2: Checked generated alert logs. "
                                "Response: %s", resp)

            LOGGER.info("Step 3: Checking CSM REST API for alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp_csm = self.csm_alert_obj.verify_csm_response(
                self.starttime, fault_alert, False, test_cfg["resource_type"])

            if not resp_csm[0]:
                d_f[key]['Step3'] = 'Fail'
                LOGGER.error("Step 3: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 3: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)

            LOGGER.info("Step 4: Rebooting node %s ", self.hostname)
            resp = self.node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                             read_lines=True, exc=False)
            LOGGER.info(
                "Step 4: Rebooted node: %s, Response: %s", self.hostname, resp)
            time.sleep(self.cm_cfg["reboot_delay"])
            LOGGER.info("Check health of node %s", self.test_node)
            resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
            # Revisit when health state information is available
            LOGGER.info("Response: %s", resp)

            LOGGER.info("Step 5: Checking if fault alert is persistent "
                        "in CSM across node reboot")
            resp_csm = self.csm_alert_obj.verify_csm_response(
                self.starttime, fault_alert, False, test_cfg["resource_type"])

            if not resp_csm:
                d_f[key]['Step5'] = 'Fail'
                LOGGER.error("Step 5: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 5: Successfully checked CSM REST API for "
                            "fault alert persistent across node reboot. "
                            "Response: %s", resp_csm)

            LOGGER.info("Step 6: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                resolve_enum,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"host_num": host_num,
                                  "drive_count": drive_count})

            if not resp[0]:
                d_f[key]['Step6'] = 'Fail'
                LOGGER.error("Step 6: Failed to resolve fault on %s",
                             resp[1])
            else:
                LOGGER.info(
                    "Step 6: Successfully resolved fault for disk %s\n "
                    "Response: %s", drive_name, resp)

            new_drive = resp[1]
            LOGGER.info("Starting RAID recovery...")
            LOGGER.info("Step 6: Getting raid partitions of drive %s",
                        new_drive)
            resp = self.ras_test_obj.get_drive_partition_details(
                filepath=RAS_VAL['ras_sspl_alert']['file']['fdisk_file'],
                drive=new_drive)
            if not resp[0]:
                d_f['Iteration0']['Step6'] = 'Fail'
            raid_parts = resp[1] if resp[0] else LOGGER.error(
                "Step 6: Failed to "
                "get partition "
                "details of "
                "%s", new_drive)

            LOGGER.info(
                "Step 7: Adding raid partitions of drive %s in raid array",
                new_drive)
            resp = self.ras_test_obj.add_raid_partitions(
                alert_lib_obj=self.alert_api_obj, alert_type=AlertType,
                raid_parts=raid_parts, md_arrays=md_arrays)
            if not resp[0]:
                d_f['Iteration0']['Step7'] = 'Fail'
            new_array = resp[1] if resp[0] else LOGGER.error(
                "Step 7: Failed to "
                "add drive in raid "
                "array")
            LOGGER.info("New MDARRAY: %s", new_array)

            time.sleep(self.cm_cfg["sleep_val"])
            if self.start_msg_bus:
                LOGGER.info("Step 7: Checking the generated alert logs")
                alert_list = [test_cfg["resource_type"],
                              resolved_alert]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    d_f[key]['Step7'] = 'Fail'
                    LOGGER.error("Step 7: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 7: Successfully checked generated alert "
                                "logs\n Response: %s", resp)

            LOGGER.info("Step 8: Checking CSM REST API for alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp_csm = self.csm_alert_obj.verify_csm_response(
                self.starttime, resolved_alert, True, test_cfg["resource_type"])

            if not resp_csm:
                d_f[key]['Step8'] = 'Fail'
                LOGGER.error("Step 8: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 8: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)

            LOGGER.info("Check health of node %s", self.test_node)
            resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Summary of test: \n%s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(
            result,
            "Test failed. Please check summary for failed "
            "step.")

        LOGGER.info("ENDED: Test alerts for OS disk are persistent across "
                    "node reboot")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23624")
    @CTFailOn(error_handler)
    def test_os_disk_alert_persistent_sspl_stop_start_23624(self):
        """
        TEST-23624: Test verifies fault and fault resolved alerts of OS disk
        are persistent across sspl stop and start.
        """
        LOGGER.info("STARTED: Test alerts for OS disk are persistent across "
                    "sspl stop and start")

        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["TEST-23606"]
        service = self.cm_cfg["service"]

        LOGGER.info("Getting details of drive on which faults are to "
                    "be created")
        resp = self.ras_test_obj.get_node_drive_details()
        assert_utils.assert_true(
            resp[0], f"Failed to get details of OS disks. "
            f"Response: {resp}")

        drive_name = resp[1].split("/")[2]
        host_num = resp[2]
        drive_count = resp[3]
        LOGGER.info("Drive details:\nOS drive name: %s \n"
                    "Host number: %s \nOS Drive count: %s \n",
                    drive_name, host_num, drive_count)

        os_disk_faults = {
            'availability': {'alert_enum': AlertType.OS_DISK_DISABLE,
                             'resolve_enum': AlertType.OS_DISK_ENABLE,
                             'fault_alert': self.alert_types["missing"],
                             'resolved_alert': self.alert_types["insertion"]
                             }
        }
        d_f = pd.DataFrame(columns=f"{list(os_disk_faults.keys())[0]} ".split(),
                           index='Step1 Step2 Step3 Step4 Step5 Step6 '
                                 'Step7 Step8 Step9 Step10'.split())

        for key, value in os_disk_faults.items():
            d_f[key] = 'Pass'
            alert_enum = value['alert_enum']
            resolve_enum = value['resolve_enum']
            fault_alert = value['fault_alert']
            resolved_alert = value['resolved_alert']

            LOGGER.info("Step 1: Getting RAID array details of node %s",
                        self.hostname)
            resp = self.ras_test_obj.get_raid_array_details()
            if not resp[0]:
                d_f['Iteration0']['Step1'] = 'Fail'
            md_arrays = resp[1] if resp[0] else assert_utils.assert_true(
                resp[0], "Step 1: Failed" " to get raid " "array details")

            LOGGER.info("MDRAID arrays: %s", md_arrays)
            for k_k, v_v in md_arrays.items():
                if v_v["state"] != "Active":
                    d_f['Iteration0']['Step1'] = 'Fail'
                    assert_utils.assert_true(
                        False, f"Step 1: Array {k_k} is in degraded state")

            LOGGER.info("Step 1: Stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = self.health_obj.pcs_resource_ops_cmd(
                command="ban", resources=[self.sspl_resource_id],
                srvnode=self.current_srvnode)
            if not resp:
                d_f[key]['Step1'] = 'Fail'
                assert_utils.assert_true(
                    resp, f"Failed to ban/stop {self.sspl_resource_id} "
                    f"on node {self.current_srvnode}")
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 1: Checking if SSPL is in stopped state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                        "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "inactive":
                d_f[key]['Step1'] = 'Fail'
                assert_utils.compare(resp[0], "inactive")
            else:
                LOGGER.info("Step 1: Successfully stopped SSPL service")

            LOGGER.info("Step 2: Generating %s os disk fault on drive %s",
                        key, drive_name)
            resp = self.alert_api_obj.generate_alert(
                alert_enum,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"drive_name": drive_name,
                                  "drive_count": drive_count})
            if not resp[0]:
                d_f[key]['Step2'] = 'Fail'
                LOGGER.error("Step 2: Failed to create fault. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 2: Successfully created fault on disk %s\n "
                            "Response: %s", drive_name, resp)

            LOGGER.info("Step 3: Starting SSPL service")
            resp = self.health_obj.pcs_resource_ops_cmd(
                command="clear", resources=[
                    self.sspl_resource_id], srvnode=self.current_srvnode)
            if not resp:
                d_f[key]['Step3'] = 'Fail'
                LOGGER.error("Failed to clear/start %s on node %s",
                             self.sspl_resource_id, self.current_srvnode)
            LOGGER.info("Successfully enabled %s", self.sspl_resource_id)
            LOGGER.info("Step 3: Checking if SSPL is in running state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                        "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "active":
                d_f[key]['Step3'] = 'Fail'
                LOGGER.error("SSPL state: %s", resp[0])
            else:
                LOGGER.info("Step 3: Successfully started SSPL service")

            time.sleep(self.cm_cfg["sleep_val"])
            if self.start_msg_bus:
                LOGGER.info("Step 4: Verifying alert logs for fault alert ")
                alert_list = [test_cfg["resource_type"],
                              fault_alert]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    d_f[key]['Step4'] = 'Fail'
                    LOGGER.error("Step 4: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 4: Successfully checked generated alert "
                                "logs. Response: %s", resp)

            LOGGER.info("Step 5: Checking CSM REST API for alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp_csm = self.csm_alert_obj.verify_csm_response(
                self.starttime, fault_alert, False, test_cfg["resource_type"])

            if not resp_csm:
                d_f[key]['Step5'] = 'Fail'
                LOGGER.error("Step 5: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 5: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)

            LOGGER.info("Check health of node %s", self.test_node)
            resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
            # Revisit when health state information is available
            LOGGER.info("Response: %s", resp)

            LOGGER.info("Step 6: Again stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = self.health_obj.pcs_resource_ops_cmd(
                command="ban", resources=[self.sspl_resource_id],
                srvnode=self.current_srvnode)
            if not resp:
                d_f[key]['Step6'] = 'Fail'
                LOGGER.error("Failed to ban/stop %s on node %s",
                             self.sspl_resource_id, self.current_srvnode)
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 6: Checking if SSPL is in stopped state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                        "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "inactive":
                d_f[key]['Step6'] = 'Fail'
                LOGGER.error("SSPL state: %s", resp[0])
            else:
                LOGGER.info("Step 6: Successfully stopped SSPL service")

            LOGGER.info("Step 7: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                resolve_enum,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"host_num": host_num,
                                  "drive_count": drive_count})

            if not resp[0]:
                d_f[key]['Step7'] = 'Fail'
                LOGGER.error("Step 7: Failed to resolve fault on %s",
                             resp[1])
            else:
                LOGGER.info(
                    "Step 7: Successfully resolved fault for disk %s\n "
                    "Response: %s", drive_name, resp)

            new_drive = resp[1]
            LOGGER.info("Starting RAID recovery...")
            LOGGER.info("Step 6: Getting raid partitions of drive %s",
                        new_drive)
            resp = self.ras_test_obj.get_drive_partition_details(
                filepath=RAS_VAL['ras_sspl_alert']['file']['fdisk_file'],
                drive=new_drive)
            if not resp[0]:
                d_f['Iteration0']['Step6'] = 'Fail'
            raid_parts = resp[1] if resp[0] else LOGGER.error("Step 6: Failed "
                                                              "to get partition"
                                                              " details of %s",
                                                              new_drive)

            LOGGER.info(
                "Step 7: Adding raid partitions of drive %s in raid array",
                new_drive)
            resp = self.ras_test_obj.add_raid_partitions(
                alert_lib_obj=self.alert_api_obj, alert_type=AlertType,
                raid_parts=raid_parts, md_arrays=md_arrays)
            if not resp[0]:
                d_f['Iteration0']['Step7'] = 'Fail'
            new_array = resp[1] if resp[0] else LOGGER.error(
                "Step 7: Failed to "
                "add drive in raid "
                "array")
            LOGGER.info("New MDARRAY: %s", new_array)

            LOGGER.info("Step 8: Starting SSPL service")
            resp = self.health_obj.pcs_resource_ops_cmd(
                command="clear", resources=[
                    self.sspl_resource_id], srvnode=self.current_srvnode)
            if not resp:
                d_f[key]['Step8'] = 'Fail'
                LOGGER.error("Failed to clear/start %s on node %s",
                             self.sspl_resource_id, self.current_srvnode)
            LOGGER.info("Successfully enabled %s", self.sspl_resource_id)
            LOGGER.info("Step 8: Checking if SSPL is in running state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                        "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "active":
                d_f[key]['Step8'] = 'Fail'
                LOGGER.error("SSPL state: %s", resp[0])
            else:
                LOGGER.info("Step 8: Successfully started SSPL service")

            time.sleep(self.cm_cfg["sleep_val"])
            if self.start_msg_bus:
                LOGGER.info("Step 9: Checking the generated alert logs")
                alert_list = [test_cfg["resource_type"],
                              resolved_alert]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    d_f[key]['Step9'] = 'Fail'
                    LOGGER.error("Step 7: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 9: Successfully checked generated alert "
                                "logs\n Response: %s", resp)

            LOGGER.info("Step 10: Checking CSM REST API for alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp_csm = self.csm_alert_obj.verify_csm_response(
                self.starttime, resolved_alert, True, test_cfg["resource_type"])

            if not resp_csm:
                d_f[key]['Step10'] = 'Fail'
                LOGGER.error("Step 10: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 10: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)

            LOGGER.info("Check health of node %s", self.test_node)
            resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Summary of test: \n%s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(
            result,
            "Test failed. Please check summary for failed "
            "step.")

        LOGGER.info("ENDED: Test alerts for OS disk are persistent across "
                    "sspl stop and start")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23715")
    @CTFailOn(error_handler)
    def test_assemble_dissemble_raid_array_23715(self):
        """
        TEST-23715: Test alerts for assembling and dissembling RAID array
        """
        LOGGER.info(
            "STARTED: TEST-23715: Test alerts for assembling and dissembling RAID array")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_23715"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]
        alert_types = RAS_TEST_CFG["alert_types"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "stopping array")
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_STOP_DEVICE_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["stop_operation"],
                "md_device": test_cfg["md_device"],
                "disk": None})
        assert_utils.assert_true(resp[0], resp[1])
        self.raid_stopped = test_cfg["md_device"]
        LOGGER.info("Step 1: Ran ALERT API for generating RAID fault alert by "
                    "stopping array")

        if self.start_msg_bus:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ"
                " channel logs")
            alert_list = [test_cfg["resource_type"],
                          alert_types["fault"]]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                      restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["fault"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info("Performing health check after fault creation")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID fault_resolved "
            "alert by assembling array")
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_ASSEMBLE_DEVICE_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["assemble_operation"],
                "md_device": self.md_device,
                "disk": None})
        assert_utils.assert_true(resp[0], resp[1])
        self.raid_stopped = False
        LOGGER.info("Step 4: Ran ALERT API for generating RAID fault_resolved "
                    "alerts by assembling array")

        if self.start_msg_bus:
            LOGGER.info(
                "Step 5: Checking the generated RAID fault alert on RMQ"
                " channel logs")
            alert_list = [test_cfg["resource_type"],
                          alert_types["resolved"]]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                      restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info(
            "Step 6: Checking CSM REST API for RAID fault_resolved alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["resolved"],
            True,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info("Step 6: Successfully verified RAID fault_resolved alert "
                    "using CSM REST API")

        LOGGER.info("Performing health check after fault resolved")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "ENDED: TEST-23715: Test alerts for assembling and dissembling RAID array")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23723")
    @CTFailOn(error_handler)
    def test_fail_remove_add_drive_raid_array_23723(self):
        """
        TEST-23723: Test alerts for failing drive, removing drive
        from RAID array and adding drive in RAID array.
        """
        LOGGER.info(
            "STARTED: Test alerts for failing drive, removing drive"
            "from RAID array and adding drive in RAID array")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_23723"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]
        alert_types = RAS_TEST_CFG["alert_types"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_FAIL_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disk = self.disk2
        resource_id = f"{self.md_device}:{self.disk2}"
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing "
            "a disk from array")

        if self.start_msg_bus:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on message bus")
            alert_list = [test_cfg["resource_type"],
                          alert_types["fault"], resource_id]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on message bus logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["fault"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk %s from array %s",
            self.disk2,
            self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_REMOVE_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disk = False
        self.removed_disk = self.disk2
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID missing alert by "
            "removing faulty disk from array")

        if self.start_msg_bus:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on message bus")
            alert_list = [test_cfg["resource_type"],
                          alert_types["missing"], resource_id]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on message bus logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["missing"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 6: Successfully verified RAID missing alert using CSM"
            " REST API")

        LOGGER.info("Performing health check after fault creation")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info(
            "Step 7: Running ALERT API for generating RAID fault_resolved alert"
            "by adding removed disk %s to array %s",
            self.disk2,
            self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_ADD_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["add_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 7: Ran ALERT API for generating RAID fault_resolved alert "
            "by adding removed disk to array")

        md_stat = resp[1]
        if self.start_msg_bus:
            LOGGER.info(
                "Step 8: Checking the generated RAID insertion alert on"
                " message bus logs")
            alert_list = [test_cfg["resource_type"],
                          alert_types["insertion"], resource_id]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                      restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 8: Verified the RAID insertion alert on message bus logs")

        LOGGER.info("Step 9: Checking CSM REST API for RAID insertion alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["insertion"],
            True,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info("Step 9: Successfully verified RAID insertion alert using "
                    "CSM REST API")

        if not all(md_stat["devices"][os.path.basename(
                self.md_device)]["status"]["synced"]):
            time.sleep(raid_cmn_cfg["resync_delay"])

        if all(md_stat["devices"][os.path.basename(
                self.md_device)]["status"]["synced"]):
            if self.start_msg_bus:
                LOGGER.info("Step 10: Checking the generated RAID "
                            "fault_resolved alert on message bus logs")
                alert_list = [test_cfg["resource_type"],
                              alert_types["resolved"], resource_id]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Step 10: Verified the RAID fault_resolved alert on"
                    " message bus logs")

            LOGGER.info(
                "Step 11: Checking CSM REST API for RAID fault_resolved alert")
            time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert_types["resolved"],
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, csm_error_msg)
        self.removed_disk = False
        LOGGER.info("Step 11: Successfully verified RAID fault_resolved alert "
                    "using CSM REST API")

        LOGGER.info("Performing health check after fault resolved")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info(
            "ENDED: Test alerts for failing drive, removing drive"
            "from RAID array and adding drive in RAID array")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23724")
    @CTFailOn(error_handler)
    def test_raid_array_alert_persistence_node_reboot_23724(self):
        """
        TEST-23724: Test alert persistence of RAID array alerts across node reboot.
        """
        LOGGER.info(
            "STARTED: Test alert persistence of RAID array alerts across node reboot")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_23723"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]
        alert_types = RAS_TEST_CFG["alert_types"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_FAIL_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disk = self.disk2
        resource_id = f"{self.md_device}:{self.disk2}"
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing "
            "a disk from array")

        if self.start_msg_bus:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on message bus")
            alert_list = [test_cfg["resource_type"],
                          alert_types["fault"], resource_id]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on message bus logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["fault"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk %s from array %s",
            self.disk2,
            self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_REMOVE_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disk = False
        self.removed_disk = self.disk2
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID missing alert by "
            "removing faulty disk from array")

        if self.start_msg_bus:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on message bus")
            alert_list = [test_cfg["resource_type"],
                          alert_types["missing"], resource_id]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on message bus logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["missing"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 6: Successfully verified RAID missing alert using CSM"
            " REST API")

        LOGGER.info("Step 7: Rebooting node %s ", self.hostname)
        resp = self.node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                         read_lines=True, exc=False)
        LOGGER.info(
            "Step 7: Rebooted node: %s, Response: %s", self.hostname, resp)
        time.sleep(self.cm_cfg["reboot_delay"])

        LOGGER.info("Performing health check after node reboot")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 8: Checking if fault alert is persistent "
                    "in CSM across node reboot")
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["missing"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info("Step 8: Successfully checked CSM REST API for RAID "
                    "fault alert persistent across node reboot. ")

        LOGGER.info(
            "Step 9: Running ALERT API for generating RAID fault_resolved alert"
            "by adding removed disk %s to array %s",
            self.disk2,
            self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_ADD_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["add_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 9: Ran ALERT API for generating RAID fault_resolved alert "
            "by adding removed disk to array")

        md_stat = resp[1]
        if self.start_msg_bus:
            LOGGER.info(
                "Step 10: Checking the generated RAID insertion alert on"
                " message bus logs")
            alert_list = [test_cfg["resource_type"],
                          alert_types["insertion"], resource_id]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                      restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 10: Verified the RAID insertion alert on message bus logs")

        LOGGER.info("Step 11: Checking CSM REST API for RAID insertion alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["insertion"],
            True,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 11: Successfully verified RAID insertion alert using "
            "CSM REST API")

        if not all(md_stat["devices"][os.path.basename(
                self.md_device)]["status"]["synced"]):
            time.sleep(raid_cmn_cfg["resync_delay"])

        if all(md_stat["devices"][os.path.basename(
                self.md_device)]["status"]["synced"]):
            if self.start_msg_bus:
                LOGGER.info("Step 12: Checking the generated RAID "
                            "fault_resolved alert on message bus logs")
                alert_list = [test_cfg["resource_type"],
                              alert_types["resolved"], resource_id]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Step 12: Verified the RAID fault_resolved alert on"
                    " message bus logs")

            LOGGER.info(
                "Step 13: Checking CSM REST API for RAID fault_resolved alert")
            time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert_types["resolved"],
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, csm_error_msg)
        self.removed_disk = False
        LOGGER.info("Step 13: Successfully verified RAID fault_resolved alert "
                    "using CSM REST API")
        LOGGER.info(
            "ENDED: Test alert persistence of RAID array alerts across node reboot")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23725")
    @CTFailOn(error_handler)
    def test_raid_array_alert_persistence_sspl_stop_start_23725(self):
        """
        TEST-23724: Test alert persistence of RAID array alerts across sspl stop and start.
        """
        LOGGER.info(
            "STARTED: Test alert persistence of RAID array alerts across sspl stop and start")
        raid_cmn_cfg = RAS_VAL["raid_param"]
        test_cfg = RAS_TEST_CFG["test_23723"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]
        service = self.cm_cfg["service"]
        alert_types = RAS_TEST_CFG["alert_types"]

        LOGGER.info("Step 1: Stopping pcs resource for SSPL: %s",
                    self.sspl_resource_id)
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="ban", resources=[self.sspl_resource_id],
            srvnode=self.current_srvnode)

        assert_utils.assert_true(
            resp, f"Failed to ban/stop {self.sspl_resource_id} "
            f"on node {self.current_srvnode}")
        LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in stopped state.")
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=[service[
                                                    "sspl_service"]],
                                                decode=True, exc=False)
        assert_utils.assert_exact_string(
            "inactive",
            resp[0],
            "sspl service is not in stopped state")
        LOGGER.info("Step 1: Successfully stopped SSPL service")

        LOGGER.info(
            "Step 2: Running ALERT API for generating RAID fault alert by "
            "failing disk %s from array %s", self.disk2, self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_FAIL_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disk = self.disk2
        resource_id = f"{self.md_device}:{self.disk2}"
        LOGGER.info(
            "Step 2: Ran ALERT API for generating RAID fault alert by failing "
            "a disk from array")

        LOGGER.info(
            "Step 3: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk %s from array %s",
            self.disk2,
            self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_REMOVE_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disk = False
        self.removed_disk = self.disk2
        LOGGER.info(
            "Step 3: Ran ALERT API for generating RAID missing alert by "
            "removing faulty disk from array")

        LOGGER.info("Step 4: Starting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="clear", resources=[
                self.sspl_resource_id], srvnode=self.current_srvnode)
        assert_utils.assert_true(
            resp, f"Failed to clear/start {self.sspl_resource_id} "
            f"on node {self.current_srvnode}")
        LOGGER.info("Successfully enabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in running state.")
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=[service[
                                                    "sspl_service"]],
                                                decode=True, exc=False)
        assert_utils.assert_exact_string(
            "active", resp[0], "sspl service is not active")
        LOGGER.info("Step 4: Successfully started SSPL service")

        LOGGER.info("Performing health check after SSPL start")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        if self.start_msg_bus:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on message bus")
            alert_list = [test_cfg["resource_type"],
                          alert_types["missing"], resource_id]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on message bus logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["missing"],
            False,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 6: Successfully verified RAID missing alert using CSM"
            " REST API")

        LOGGER.info("Step 7: Again stopping pcs resource for SSPL: %s",
                    self.sspl_resource_id)
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="ban", resources=[self.sspl_resource_id],
            srvnode=self.current_srvnode)

        assert_utils.assert_true(
            resp, f"Failed to ban/stop {self.sspl_resource_id} "
            f"on node {self.current_srvnode}")
        LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in stopped state.")
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=[service[
                                                    "sspl_service"]],
                                                decode=True, exc=False)
        assert_utils.assert_exact_string(
            "inactive",
            resp[0],
            "sspl service is not in stopped state")
        LOGGER.info("Step 7: Successfully stopped SSPL service")

        LOGGER.info(
            "Step 8: Running ALERT API for generating RAID fault_resolved alert"
            "by adding removed disk %s to array %s",
            self.disk2,
            self.md_device)
        resp = self.alert_api_obj.generate_alert(
            AlertType.RAID_ADD_DISK_ALERT,
            input_parameters={
                "operation": raid_cmn_cfg["add_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 8: Ran ALERT API for generating RAID fault_resolved alert "
            "by adding removed disk to array")

        LOGGER.info("Step 9: Starting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="clear", resources=[
                self.sspl_resource_id], srvnode=self.current_srvnode)
        assert_utils.assert_true(
            resp, f"Failed to clear/start {self.sspl_resource_id} "
            f"on node {self.current_srvnode}")
        LOGGER.info("Successfully enabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in running state.")
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=[service[
                                                    "sspl_service"]],
                                                decode=True, exc=False)
        assert_utils.assert_exact_string(
            "active", resp[0], "sspl service is not active")
        LOGGER.info("Step 9: Successfully started SSPL service")

        LOGGER.info("Performing health check after SSPL start")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        md_stat = resp[1]
        if self.start_msg_bus:
            LOGGER.info(
                "Step 10: Checking the generated RAID insertion alert on"
                " message bus logs")
            alert_list = [test_cfg["resource_type"],
                          alert_types["insertion"], resource_id]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                      restart=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 10: Verified the RAID insertion alert on message bus logs")

        LOGGER.info("Step 11: Checking CSM REST API for RAID insertion alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            alert_types["insertion"],
            True,
            test_cfg["resource_type"])
        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info(
            "Step 11: Successfully verified RAID insertion alert using "
            "CSM REST API")

        if not all(md_stat["devices"][os.path.basename(
                self.md_device)]["status"]["synced"]):
            time.sleep(raid_cmn_cfg["resync_delay"])

        if all(md_stat["devices"][os.path.basename(
                self.md_device)]["status"]["synced"]):
            if self.start_msg_bus:
                LOGGER.info("Step 12: Checking the generated RAID "
                            "fault_resolved alert on message bus logs")
                alert_list = [test_cfg["resource_type"],
                              alert_types["resolved"], resource_id]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Step 12: Verified the RAID fault_resolved alert on"
                    " message bus logs")

            LOGGER.info(
                "Step 13: Checking CSM REST API for RAID fault_resolved alert")
            time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert_types["resolved"],
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, csm_error_msg)
        self.removed_disk = False
        LOGGER.info("Step 13: Successfully verified RAID fault_resolved alert "
                    "using CSM REST API")
        LOGGER.info(
            "ENDED: Test alert persistence of RAID array alerts across sspl "
            "stop and start")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23679")
    @CTFailOn(error_handler)
    def test_node_power_failure_alert_23679(self):
        """
        TEST-23679: Test alert when one of the node's power cable is
        disconnected and connected
        """
        LOGGER.info(
            "STARTED: Test alert when one of the node's power cable is "
            "disconnected and connected")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["power_failure"]
        csm_error_msg = test_cfg["csm_error_msg"]
        fault_description = test_cfg["fault_description"].format(self.test_node)
        fault_res_desc = test_cfg["fault_res_desc"].format(self.test_node)
        other_node = self.test_node - 1 if self.test_node > 1 else self.test_node + 1
        other_host = CMN_CFG["nodes"][other_node-1]["hostname"]
        bmc_user = CMN_CFG["bmc"]["username"]
        bmc_pwd = CMN_CFG["bmc"]["password"]

        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node %s",
                        other_host)
            resp = ast.literal_eval(f"srv{other_node}_ras.start_message_bus_reader_cmd()")
            assert_utils.assert_true(resp, "Failed to start message bus "
                                           "channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Shutting down node %s from node %s",
                    self.hostname, other_host)
        status = test_cfg["power_off"]
        if test_cfg["bmc_shutdown"]:
            LOGGER.info("Using BMC ip")
            res = self.bmc_obj.bmc_node_power_on_off(bmc_user=bmc_user,
                                                     bmc_pwd=bmc_pwd,
                                                     status=status)
        else:
            LOGGER.info("Using PDU ip")
            LOGGER.info("Making left pdu port down")
            cmd = f"srv{other_node}_nd.toggle_apc_node_power(" \
                  f"pdu_ip='{self.lpdu_details['ip']}', " \
                  f"pdu_user='{self.lpdu_details['user']}', " \
                  f"pdu_pwd='{self.lpdu_details['pwd']}', " \
                  f"node_slot='{self.lpdu_details['port']}', " \
                  f"status='{status}')"
            LOGGER.info("Command: %s", cmd)
            res = ast.literal_eval(cmd)
            LOGGER.debug(res)
            LOGGER.info("Making right pdu port down")
            cmd = f"srv{other_node}_nd.toggle_apc_node_power(" \
                  f"pdu_ip='{self.rpdu_details['ip']}', " \
                  f"pdu_user='{self.rpdu_details['user']}', " \
                  f"pdu_pwd='{self.rpdu_details['pwd']}', " \
                  f"node_slot='{self.rpdu_details['port']}', " \
                  f"status='{status}')"
            LOGGER.info("Command: %s", cmd)
            res = ast.literal_eval(cmd)

        LOGGER.debug("Response: %s", res)

        LOGGER.info("Checking if node is powered off")
        resp = system_utils.check_ping(host=self.hostname)
        assert_utils.assert_false(resp, "Failed to power off the node")
        self.power_failure_flag = True
        LOGGER.info("Step 1: Successfully powered off node using APC/BMC.")

        if self.start_msg_bus:
            time.sleep(self.cm_cfg["sleep_val"])
            LOGGER.info("Step 2: Verifying alert logs for get alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types["get"],
                          fault_description]
            resp = ast.literal_eval(f"srv{other_node}_ras.list_alert_validation({alert_list})")
            assert_utils.assert_true(resp[0], f"Step 2: Expected alert not "
                                              f"found. Error: {resp[1]}")

            LOGGER.info("Step 2: Successfully checked generated alert logs. "
                        "Response: %s", resp)

        LOGGER.info("Step 3: Checking CSM REST API for alert")
        time.sleep(common_cfg["csm_alert_gen_delay"])
        resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                          self.alert_types[
                                                              "get"],
                                                          False,
                                                          test_cfg[
                                                              "resource_type"],
                                                          fault_description)

        assert_utils.assert_true(resp_csm, f"Step 3: Expected alert not "
                                           f"found. Error: {csm_error_msg}")

        LOGGER.info("Step 3: Successfully checked CSM REST API for "
                    "fault alert. Response: %s", resp_csm)

        LOGGER.info("Step 4: Powering on node %s from node %s",
                    self.hostname, other_host)
        status = test_cfg["power_on"]
        if test_cfg["bmc_shutdown"]:
            LOGGER.info("Using BMC ip")
            res = self.bmc_obj.bmc_node_power_on_off(bmc_user=bmc_user,
                                                     bmc_pwd=bmc_pwd,
                                                     status=status)
        else:
            LOGGER.info("Using PDU ip")
            LOGGER.info("Making left pdu port up")
            cmd = f"srv{other_node}_nd.toggle_apc_node_power(" \
                  f"pdu_ip='{self.lpdu_details['ip']}', " \
                  f"pdu_user='{self.lpdu_details['user']}', " \
                  f"pdu_pwd='{self.lpdu_details['pwd']}', " \
                  f"node_slot='{self.lpdu_details['port']}', " \
                  f"status='{status}')"
            LOGGER.info("Command: %s", cmd)
            res = ast.literal_eval(cmd)
            LOGGER.debug(res)
            LOGGER.info("Making right pdu port up")
            cmd = f"srv{other_node}_nd.toggle_apc_node_power(" \
                  f"pdu_ip='{self.rpdu_details['ip']}', " \
                  f"pdu_user='{self.rpdu_details['user']}', " \
                  f"pdu_pwd='{self.rpdu_details['pwd']}', " \
                  f"node_slot='{self.rpdu_details['port']}', " \
                  f"status='{status}')"
            LOGGER.info("Command: %s", cmd)
            res = ast.literal_eval(cmd)
        LOGGER.debug("Response: %s", res)

        time.sleep(test_cfg["wait_10_min"])
        LOGGER.info("Checking if node is powered on")
        resp = system_utils.check_ping(host=self.hostname)
        assert_utils.assert_true(resp, "Failed to power on the node")
        self.power_failure_flag = False
        LOGGER.info("Step 4: Successfully powered on node using APC/BMC.")

        LOGGER.info("Step 5: Check cluster health")
        resp = ast.literal_eval(f"srv{other_node}_hlt.check_node_health()")
        assert_utils.assert_true(resp[0], f"Step 5: Cluster health is not good. \nResponse: {resp}")
        LOGGER.info("Step 5: Cluster health is good. \nResponse: %s", resp)

        if self.start_msg_bus:
            time.sleep(self.cm_cfg["sleep_val"])
            LOGGER.info("Step 6: Verifying alert logs for get alert ")
            alert_list = [test_cfg["resource_type"],
                          self.alert_types["resolved"], fault_res_desc]
            resp = ast.literal_eval(f"srv{other_node}_ras.list_alert_validation({alert_list})")
            assert_utils.assert_true(resp[0], f"Step 6: Expected alert not found. Error: {resp[1]}")

            LOGGER.info("Step 6: Successfully checked generated alert logs. "
                        "Response: %s", resp)

        LOGGER.info("Step 7: Checking CSM REST API for alert")
        resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                          self.alert_types[
                                                              "resolved"],
                                                          True,
                                                          test_cfg[
                                                              "resource_type"],
                                                          fault_res_desc)

        assert_utils.assert_true(resp_csm, f"Step 7: Expected alert not "
                                           f"found. Error: {csm_error_msg}")

        LOGGER.info("Step 7: Successfully checked CSM REST API for "
                    "fault resolved alert. Response: %s", resp_csm)

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        if self.start_msg_bus:
            LOGGER.info("Terminating the process read_message_bus.py")
            ast.literal_eval(f"srv{other_node}_ras.kill_remote_process('read_message_bus.py')")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                cmd = f"srv{other_node}_nd.remove_remote_file(filename='{file}')"
                LOGGER.info("Command: %s", cmd)
                ast.literal_eval(cmd)

        LOGGER.info("ENDED: Test alert when one of the node's power cable is "
                    "disconnected and connected")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23682")
    @CTFailOn(error_handler)
    def test_server_psu_alerts_23682(self):
        """
        TEST-23682: Test server psu alerts for following psu states:
            - "Presence detected"
            - "Failure detected"
            - "Power Supply AC lost"
        """
        LOGGER.info(
            "STARTED: Test alerts for server psu faults")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["test_23682"]

        for state, alert in test_cfg["sensor_states"].items():
            LOGGER.info(
                "Generating server power supply device fault for state %s",
                state)
            resp = self.alert_api_obj.generate_alert(
                AlertType.SERVER_PSU_FAULT,
                input_parameters={
                    "sensor_type": test_cfg["sensor_type"],
                    "sensor_states": [state],
                    "deassert": False})
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated psu fault alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert,
                              state]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the psu fault alert on message bus logs")

            LOGGER.info("Checking CSM REST API for psu fault alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert,
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified psu fault alert using CSM REST API")
        self.server_psu_fault = True

        LOGGER.info("Performing health check after fault generation")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        for state, alert in test_cfg["sensor_states"].items():
            LOGGER.info(
                "Resolving server power supply device fault for state %s",
                state)
            resp = self.alert_api_obj.generate_alert(
                AlertType.SERVER_PSU_FAULT_RESOLVED,
                input_parameters={
                    "sensor_type": test_cfg["sensor_type"],
                    "sensor_states": [state],
                    "deassert": True})
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated psu fault_resolved alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert,
                              state]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the psu fault_resolved alert on message bus logs")

            LOGGER.info("Checking CSM REST API for psu fault_resolved alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert,
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified psu fault_resolved alert using CSM REST API")
        self.server_psu_fault = False

        LOGGER.info("Performing health check after resolving fault")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "ENDED: Test alerts for server psu faults")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23685")
    @CTFailOn(error_handler)
    def test_power_supply_alert_persistency_node_reboot_23685(self):
        """
        TEST-23685: Test system power supply alert persistency across node reboot
        """
        LOGGER.info(
            "STARTED: Test system power supply alert persistency across node reboot")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["test_23682"]

        for state, alert in test_cfg["sensor_states"].items():
            LOGGER.info(
                "Generating server power supply device fault for state %s",
                state)
            resp = self.alert_api_obj.generate_alert(
                AlertType.SERVER_PSU_FAULT,
                input_parameters={
                    "sensor_type": test_cfg["sensor_type"],
                    "sensor_states": [state],
                    "deassert": False})
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated psu fault alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert,
                              state]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the psu fault alert on message bus logs")

            LOGGER.info("Checking CSM REST API for psu fault alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert,
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified psu fault alert using CSM REST API")
        self.server_psu_fault = True

        LOGGER.info("Rebooting node %s ", self.hostname)
        resp = self.node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                         read_lines=True, exc=False)
        LOGGER.info(
            "Rebooted node: %s, Response: %s", self.hostname, resp)
        time.sleep(common_cfg["reboot_delay"])

        LOGGER.info("Performing health check after node reboot")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        for state, alert in test_cfg["sensor_states"].items():
            LOGGER.info(
                "Resolving server power supply device fault for state %s",
                state)
            resp = self.alert_api_obj.generate_alert(
                AlertType.SERVER_PSU_FAULT_RESOLVED,
                input_parameters={
                    "sensor_type": test_cfg["sensor_type"],
                    "sensor_states": [state],
                    "deassert": True})
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated psu fault_resolved alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert,
                              state]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the psu fault_resolved alert on message bus logs")

            LOGGER.info("Checking CSM REST API for psu fault_resolved alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert,
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified psu fault_resolved alert using CSM REST API")
        self.server_psu_fault = False

        LOGGER.info("Performing health check after resolving fault")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "ENDED: Test system power supply alert persistency across node reboot")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23686")
    @CTFailOn(error_handler)
    def test_power_supply_alert_persistency_sspl_restart_23686(self):
        """
        TEST-23686: Test system power supply alert persistency across sspl stop and start
        """
        LOGGER.info(
            "STARTED: Test system power supply alert persistency across sspl stop and start")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["test_23682"]
        service = common_cfg["service"]

        LOGGER.info(
            "Stopping pcs resource for SSPL: %s",
            self.sspl_resource_id)
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="ban", resources=[self.sspl_resource_id],
            srvnode=self.current_srvnode)

        assert_utils.assert_true(
            resp,
            f"Failed to ban/stop {self.sspl_resource_id} on node {self.current_srvnode}")
        LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in stopped state.")
        resp = self.node_obj.send_systemctl_cmd(
            command="is-active",
            services=[
                service["sspl_service"]],
            decode=True,
            exc=False)
        assert_utils.assert_exact_string(
            "inactive",
            resp[0],
            "sspl service is not in stopped state")
        LOGGER.info("Successfully stopped SSPL service")

        LOGGER.info("Generating server power supply device fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.SERVER_PSU_FAULT,
            input_parameters={
                "sensor_type": test_cfg["sensor_type"],
                "sensor_states": [list(test_cfg["sensor_states"].keys())],
                "deassert": False})
        assert_utils.assert_true(resp[0], resp[1])
        self.server_psu_fault = True

        LOGGER.info("Starting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="clear", resources=[
                self.sspl_resource_id], srvnode=self.current_srvnode)
        assert_utils.assert_true(
            resp,
            f"Failed to clear/start {self.sspl_resource_id} on node {self.current_srvnode}")
        LOGGER.info("Successfully enabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in running state.")
        resp = self.node_obj.send_systemctl_cmd(
            command="is-active",
            services=[
                service["sspl_service"]],
            decode=True,
            exc=False)
        assert_utils.assert_exact_string(
            "active", resp[0], "sspl service is not active")
        LOGGER.info("Successfully started SSPL service")

        LOGGER.info("Performing health check after SSPL start")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        for state, alert in test_cfg["sensor_states"].items():
            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated psu fault alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert,
                              state]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the psu fault alert on message bus logs")

            LOGGER.info("Checking CSM REST API for psu fault alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert,
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified psu fault alert using CSM REST API")

        LOGGER.info(
            "Stopping pcs resource for SSPL: %s",
            self.sspl_resource_id)
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="ban", resources=[self.sspl_resource_id],
            srvnode=self.current_srvnode)

        assert_utils.assert_true(
            resp,
            f"Failed to ban/stop {self.sspl_resource_id} on node {self.current_srvnode}")
        LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in stopped state.")
        resp = self.node_obj.send_systemctl_cmd(
            command="is-active",
            services=[
                service["sspl_service"]],
            decode=True,
            exc=False)
        assert_utils.assert_exact_string(
            "inactive",
            resp[0],
            "sspl service is not in stopped state")
        LOGGER.info("Successfully stopped SSPL service")

        LOGGER.info("Resolving server power supply device fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.SERVER_PSU_FAULT_RESOLVED,
            input_parameters={
                "sensor_type": test_cfg["sensor_type"],
                "sensor_states": [list(test_cfg["sensor_states"].keys())],
                "deassert": True})
        assert_utils.assert_true(resp[0], resp[1])
        self.server_psu_fault = False

        LOGGER.info("Starting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(
            command="clear", resources=[
                self.sspl_resource_id], srvnode=self.current_srvnode)
        assert_utils.assert_true(
            resp,
            f"Failed to clear/start {self.sspl_resource_id} on node {self.current_srvnode}")
        LOGGER.info("Successfully enabled %s", self.sspl_resource_id)
        LOGGER.info("Checking if SSPL is in running state.")
        resp = self.node_obj.send_systemctl_cmd(
            command="is-active",
            services=[
                service["sspl_service"]],
            decode=True,
            exc=False)
        assert_utils.assert_exact_string(
            "active", resp[0], "sspl service is not active")
        LOGGER.info("Successfully started SSPL service")

        LOGGER.info("Performing health check after SSPL start")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        for state, alert in test_cfg["sensor_states"].items():
            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated psu fault_resolved alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert,
                              state]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the psu fault_resolved alert on message bus logs")

            LOGGER.info("Checking CSM REST API for psu fault_resolved alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert,
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified psu fault_resolved alert using CSM REST API")

        LOGGER.info(
            "ENDED: Test system power supply alert persistency across sspl stop and start")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23633")
    @CTFailOn(error_handler)
    def test_node_fan_alerts_23633(self):
        """
        TEST-23633: Test alerts for faulty node fan modules for following FAN states:
            - lnr : Lower Non-Recoverable
            - lcr : Lower Critical
            - lnc : Lower Non-Critical
            - unc : Upper Non-Critical
            - ucr : Upper Critical
            - unr : Upper Non-Recoverable
        """
        LOGGER.info(
            "STARTED: Test alerts for faulty node fan modules")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["test_23633"]
        alert_types = RAS_TEST_CFG["alert_types"]

        for state in test_cfg["sensor_states"]:
            LOGGER.info(
                "Generating FAN fault alert for state %s",
                state)
            resp = self.alert_api_obj.generate_alert(
                AlertType.FAN_ALERT,
                input_parameters={
                    "sensor_type": test_cfg["sensor_type"],
                    "sensor_states": [state],
                    "deassert": False})
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated FAN fault alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert_types["fault"]]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the FAN fault alert on message bus logs")

            LOGGER.info("Checking CSM REST API for FAN fault alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert_types["resolved"],
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified FAN fault alert using CSM REST API")

        LOGGER.info("Performing health check after fault generation")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        for state in test_cfg["sensor_states"]:
            LOGGER.info(
                "Resolving node FAN fault alert for state %s",
                state)
            resp = self.alert_api_obj.generate_alert(
                AlertType.FAN_ALERT_RESOLVED,
                input_parameters={
                    "sensor_type": test_cfg["sensor_type"],
                    "sensor_states": [state],
                    "deassert": True})
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info(
                    "Checking the generated FAN fault_resolved alert on message bus")
                alert_list = [test_cfg["resource_type"],
                              alert_types["resolved"]]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info(
                    "Verified the FAN fault_resolved alert on message bus logs")

            LOGGER.info("Checking CSM REST API for FAN fault_resolved alert")
            time.sleep(common_cfg["csm_alert_gen_delay"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                alert_types["resolved"],
                True,
                test_cfg["resource_type"])
            assert_utils.assert_true(resp, common_cfg["csm_error_msg"])
            LOGGER.info(
                "Successfully verified FAN fault_resolved alert using CSM REST API")

        LOGGER.info("Performing health check after resolving fault")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "ENDED: Test alerts for faulty node fan modules")
