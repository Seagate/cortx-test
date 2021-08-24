import os
import random
import logging
import pytest
import time
import pandas as pd
from commons.utils import assert_utils
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.controller_helper import ControllerLib
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from commons import constants as cons
from libs.ras.ras_test_lib import RASTestLib
from libs.csm.cli.cortx_node_cli_resource import CortxNodeCLIResourceOps
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from libs.csm.rest.csm_rest_alert import SystemAlerts


LOGGER = logging.getLogger(__name__)


class TestNodeHealth:
    @classmethod
    def setup_class(cls):
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.node_cnt = len(CMN_CFG["nodes"])
        LOGGER.info("Total number of nodes in cluster: %s", cls.node_cnt)
        LOGGER.info("Randomly picking node to create fault ")
        cls.test_node = random.randint(1, cls.node_cnt)
        cls.host = CMN_CFG["nodes"][cls.test_node-1]["host"]
        cls.uname = CMN_CFG["nodes"][cls.test_node-1]["username"]
        cls.passwd = CMN_CFG["nodes"][cls.test_node-1]["password"]
        cls.hostname = CMN_CFG["nodes"][cls.test_node-1]["hostname"]
        cls.ras_test_obj = RASTestLib(host=cls.hostname, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.hostname, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.hostname, username=cls.uname,
                                password=cls.passwd)
        cls.encl_ip = CMN_CFG["enclosure"]["primary_enclosure_ip"]
        cls.encl_username = CMN_CFG["enclosure"]["enclosure_user"]
        cls.encl_passwd = CMN_CFG["enclosure"]["enclosure_pwd"]
        cls.CONT_OBJ = ControllerLib(host=cls.hostname, h_user=cls.uname, h_pwd=cls.passwd,
                                     enclosure_ip=cls.encl_ip, enclosure_user=cls.encl_username,
                                     enclosure_pwd=cls.encl_passwd)
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.alert_api_obj = GenerateAlertLib()
        cls.resource_cli = CortxNodeCLIResourceOps(host=cls.hostname, username=cls.uname, password=cls.passwd)
        cls.resource_cli.open_connection()
        cls.alert_types = RAS_TEST_CFG["alert_types"]
        cls.sspl_resource_id = cls.cm_cfg["sspl_resource_id"]
        LOGGER.info("Check cluster health")
        node_d = cls.health_obj.get_current_srvnode()
        cls.current_srvnode = node_d[cls.hostname.split('.')[0]] if \
            cls.hostname.split('.')[0] in node_d.keys() else assert_utils.assert_true(
            False, "Node name not found")

        LOGGER.info("Creating objects for all the nodes in cluster")
        objs = cls.ras_test_obj.create_obj_for_nodes(ras_c=RASTestLib,
                                                     node_c=Node,
                                                     hlt_c=Health,
                                                     ctrl_c=ControllerLib)

        for i, key in enumerate(objs.keys()):
            globals()[f"srv{i+1}_hlt"] = objs[key]['hlt_obj']

        cls.md_device = RAS_VAL["raid_param"]["md0_path"]
        LOGGER.info("Successfully ran setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        self.starttime = time.time()
        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                        False)

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
            assert_utils.assert_true(resp, "Failed to start message bus channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Change sspl log level to DEBUG")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "DEBUG"})
        resp = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                     field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting SSPL service")
        service = self.cm_cfg["service"]
        services = [service["sspl_service"], service["kafka_service"]]
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])
        self.raid_stopped = False
        self.failed_disk = False
        self.removed_disk = False
        self.disable_disk = False
        LOGGER.info(
            "Fetching the disks details from mdstat for RAID array %s",
            self.md_device)
        md_stat = self.node_obj.get_mdstat()
        self.disks = md_stat["devices"][os.path.basename(
            self.md_device)]["disks"].keys()
        self.disk1 = RAS_VAL["raid_param"]["disk_path"].format(
            list(self.disks)[0])
        self.disk2 = RAS_VAL["raid_param"]["disk_path"].format(
            list(self.disks)[1])

        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        self.ras_test_obj.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                        True)
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

        if self.disable_disk:
            resp = self.ras_test_obj.get_node_drive_details()
            if not resp[0]:
                assert_utils.assert_true(resp[0], resp)
            self.drive_name = resp[1].split("/")[2]
            self.host_num = resp[2]
            self.drive_count = resp[3]
            resp = self.alert_api_obj.generate_alert(
                AlertType.OS_DISK_ENABLE,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"host_num": self.host_num,
                                  "drive_count": self.drive_count})
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
             url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                     field=cons.CONF_SSPL_LOG_LEVEL)
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
        self.node_obj.remove_file(filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_msg_bus:
            LOGGER.info("Terminating the process read_message_bus.py")
            self.ras_test_obj.kill_remote_process("read_message_bus.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                self.node_obj.remove_file(filename=file)

        LOGGER.info("Restarting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                        self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])
        self.resource_cli.close_connection()
        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22520")
    def test_22520_verify_resource_discover(self):
        """Verify resource discover command"""
        resp = self.resource_cli.resource_discover_node_cli()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("The test completed successfully %s", resp)

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22526")
    def test_22526_verify_show_health(self):
        """Verify resource show --health command"""
        resp = self.resource_cli.resource_health_show_node_cli(timeout=5 * 60)
        assert_utils.assert_true(resp[0], resp[1])
        result = self.resource_cli.format_str_to_dict(resp[1])
        LOGGER.info("The result is %s", result)
        LOGGER.info("======= Test Completed Successfully  =================")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22527")
    def test_22527_verify_resource_health_controller(self):
        """Verify resource show --health command with resource path"""
        resp = self.resource_cli.resource_discover_node_cli()
        assert_utils.assert_true(resp[0], resp[1])
        if resp[0]:
            resp = self.resource_cli.resource_show_cont_health(timeout=5 * 60)
            assert_utils.assert_true(resp[0], resp[1])
            out = resp[1].split("},")
            i = 0
            n = len(out)
            while i < n:
                out[i] = out[i] + "}"
                result = self.resource_cli.format_str_to_dict(out[i])
                LOGGER.info("======================================================")
                LOGGER.info(result["health"]["status"])
                LOGGER.info(result["health"]["description"])
                LOGGER.info("=======================================================")
                i = i + 1
            result = self.resource_cli.format_str_to_dict(out[i])
            LOGGER.info("======================================================")
            LOGGER.info(result["health"]["status"])
            LOGGER.info(result["health"]["description"])
            LOGGER.info("=======================================================")
        LOGGER.info("Test completed Successfully")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22528")
    def test_22528_verify_os_disk_health(self):
        """Verify resource show --health with removing a drive """
        LOGGER.info("Creating disk fault to check the health status")
        test_cfg = RAS_TEST_CFG["TEST-23606"]
        alert_list = [test_cfg["resource_type"], self.alert_types[
            "missing"], f"srvnode-{self.test_node}.mgmt.public"]
        resp = self.ras_test_obj.list_alert_validation(alert_list)
        if not resp[0]:
            LOGGER.info("alert not present")
            df = pd.DataFrame(index='Step1 Step2 Step3 Step4 Step5 Step6'.split(),
                              columns='Iteration0'.split())
            df = df.assign(Iteration0='Pass')
            LOGGER.info("Step 1: Getting RAID array details of node %s", self.hostname)
            resp = self.ras_test_obj.get_raid_array_details()
            if not resp[0]:
                df['Iteration0']['Step1'] = 'Fail'
            md_arrays = resp[1] if resp[0] \
                else assert_utils.assert_true(resp[0], "Step 1: Failed to get raid array details")

            LOGGER.info("MDRAID arrays: %s", md_arrays)
            for k, v in md_arrays.items():
                if v["state"] != "Active":
                    df['Iteration0']['Step1'] = 'Fail'
                    assert_utils.assert_true(False, f"Step 1: Array {k} is in degraded state")

            LOGGER.info("Step 1: Getting details of drive to be removed")
            resp = self.ras_test_obj.get_node_drive_details()
            if not resp[0]:
                df['Iteration0']['Step1'] = 'Fail'

            assert_utils.assert_true(resp[0], f"Step 1: Failed to get details of OS disks. "
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
                df['Iteration0']['Step2'] = 'Fail'
                LOGGER.info("Step 2: Failed to create fault. Error: %s", resp[1])
            else:
                LOGGER.info("Step 2: Successfully disabled/disconnected drive %s\n "
                            "Response: %s", drive_name, resp)
            self.disable_disk = True
            time.sleep(self.cm_cfg["sleep_val"])

            if self.start_msg_bus:
                LOGGER.info("Step 3: Verifying alert logs for fault alert ")
                alert_list = [test_cfg["resource_type"], self.alert_types[
                    "missing"], f"srvnode-{self.test_node}.mgmt.public"]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    df['Iteration0']['Step3'] = 'Fail'
                    LOGGER.error("Step 3: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 3: Checked generated alert logs. Response: "
                                "%s", resp)

            LOGGER.info("Step 4: Checking CSM REST API for alert")
            resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime, self.alert_types["missing"],
                                                              False, test_cfg["resource_type"])
            if not resp_csm:
                df['Iteration0']['Step4'] = 'Fail'
                LOGGER.error("Step 4: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 4: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)
            resp = self.resource_cli.resource_discover_node_cli()
            if resp[0]:
                resp = self.resource_cli.resource_show_disk_health(timeout=5 * 60)
                assert_utils.assert_true(resp[0], resp[1])
                out = resp[1].split("},")
                i = 0
                n = len(out)
                LOGGER.info("The len is %s", n)
                while i < n - 1:
                    out[i] = out[i] + "}" + "}" + "]" + "}" + "}"
                    result = self.resource_cli.format_str_to_dict(out[i])
                    LOGGER.info("======================================================")
                    LOGGER.info(result["health"]["status"])
                    LOGGER.info(result["health"]["description"])
                    i = i + 2
            LOGGER.info("Resolving fault...")
            LOGGER.info("Step 5: Connecting OS drive %s", drive_name)
            resp = self.alert_api_obj.generate_alert(
                AlertType.OS_DISK_ENABLE,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"host_num": host_num,
                                  "drive_count": drive_count})

            if not resp[0]:
                df['Iteration0']['Step5'] = 'Fail'
                LOGGER.error("Step 5: Failed to resolve fault.")
            else:
                LOGGER.info("Step 5: Successfully connected disk %s\n Response: %s",
                            resp[1], resp)

            new_drive = resp[1]
            LOGGER.info("Starting RAID recovery...")
            LOGGER.info("Step 6: Getting raid partitions of drive %s", new_drive)
            resp = self.ras_test_obj.get_drive_partition_details(
                filepath=RAS_VAL['ras_sspl_alert']['file']['fdisk_file'],
                drive=new_drive)
            if not resp[0]:
                df['Iteration0']['Step6'] = 'Fail'
            raid_parts = resp[1] if resp[0] \
                else assert_utils.assert_true(resp[0], f"Step 6: Failed to "
                                                       f"get partition "
                                                       f"details of "
                                                       f"{new_drive}")

            LOGGER.info("Step 7: Adding raid partitions of drive %s in raid array",
                        new_drive)
            resp = self.ras_test_obj.add_raid_partitions(
                alert_lib_obj=self.alert_api_obj, alert_type=AlertType,
                raid_parts=raid_parts, md_arrays=md_arrays)
            if not resp[0]:
                df['Iteration0']['Step7'] = 'Fail'
            new_array = resp[1] if resp[0] \
                else assert_utils.assert_true(resp[0], "Step 7: Failed to "
                                                       "add drive in raid "
                                                       "array")
            LOGGER.info("New MDARRAY: %s", new_array)

            time.sleep(self.cm_cfg["sleep_val"])
            LOGGER.info("Check health of node %s", self.test_node)
            resp = eval("srv{}_hlt.check_node_health()".format(self.test_node))
            assert_utils.assert_true(resp[0], resp[1])

            if self.start_msg_bus:
                LOGGER.info("Step 8: Checking the generated alert logs")
                alert_list = [test_cfg["resource_type"],
                              self.alert_types["insertion"]]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    df['Iteration0']['Step8'] = 'Fail'
                    LOGGER.error("Step 8: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 8: Successfully checked generated alert logs\n "
                                "Response: %s", resp)

            LOGGER.info("Step 9: Checking CSM REST API for alert")
            resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                              self.alert_types[
                                                                  "insertion"],
                                                              True,
                                                              test_cfg[
                                                                  "resource_type"])

            if not resp_csm:
                df['Iteration0']['Step9'] = 'Fail'
                LOGGER.error("Step 9: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 9: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)
            LOGGER.info("Verifying the Health status after resolving the Fault")
            resp = self.resource_cli.resource_discover_node_cli()
            if resp[0]:
                resp = self.resource_cli.resource_show_disk_health(timeout=5 * 60)
                assert_utils.assert_true(resp[0], resp[1])
                out = resp[1].split("},")
                i = 0
                n = len(out)
                LOGGER.info("The len is %s", n)
                while i < n - 1:
                    out[i] = out[i] + "}" + "}" + "]" + "}" + "}"
                    result = self.resource_cli.format_str_to_dict(out[i])
                    LOGGER.info("======================================================")
                    LOGGER.info(result["health"]["status"])
                    LOGGER.info(result["health"]["description"])
                    i = i + 2

            LOGGER.info("Summary of test: %s", df)
            result = False if 'Fail' in df.values else True
            assert_utils.assert_true(result, "Test failed. Please check summary for failed step")
            LOGGER.info("ENDED: Test alerts for OS disk removal and insertion")
        else:
            LOGGER.info("Alert is already Present")
            resp = self.resource_cli.resource_discover_node_cli()
            if resp[0]:
                resp = self.resource_cli.resource_show_disk_health(timeout=5 * 60)
                assert_utils.assert_true(resp[0], resp[1])
                out = resp[1].split("},")
                i = 0
                n = len(out)
                LOGGER.info("The len is %s", n)
                while i < n - 1:
                    out[i] = out[i] + "}" + "}" + "]" + "}" + "}"
                    result = self.resource_cli.format_str_to_dict(out[i])
                    LOGGER.info("======================================================")
                    LOGGER.info(result["health"]["status"])
                    LOGGER.info(result["health"]["description"])
                    i = i + 2
            LOGGER.info("======= Test Completed Successfully ========")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22529")
    def test_22529_verify_psu_health(self):
        """Verify resource show --health with removing a PSU from server node"""
        resp = self.resource_cli.resource_discover_node_cli()
        if resp[0]:
            resp = self.resource_cli.resource_show_psu_health(timeout=5*60)
            assert_utils.assert_true(resp[0], resp[1])
            out = resp[1].split("},")
            i = 0
            n = len(out)
            while i < n-1:
                out[i] = out[i] + "}"
                result = self.resource_cli.format_str_to_dict(out[i])
                LOGGER.info("======================================================")
                LOGGER.info(result["health"]["status"])
                LOGGER.info(result["health"]["description"])
                LOGGER.info("=======================================================")
                i = i+1
            result = self.resource_cli.format_str_to_dict(out[i])
            LOGGER.info("======================================================")
            LOGGER.info(result["health"]["status"])
            LOGGER.info(result["health"]["description"])
            LOGGER.info("=======================================================")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22530")
    def test_22530_wrong_parameter(self):
        """Verify resource show --health with wrong rpath"""
        resp = self.resource_cli.resource_health_show_invalid_param(timeout=5 * 60)
        error_msg = "cortx_setup command Failed:"
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_that(resp[1], error_msg)
        LOGGER.info("Requesting resource health failed with wrong rpath with error %s",
                    resp[1])
