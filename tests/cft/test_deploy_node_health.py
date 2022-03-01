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
#import os
import secrets
import time
import logging
from time import perf_counter_ns
import pytest
import pandas as pd
from commons.utils import assert_utils
from commons.utils.system_utils import run_remote_cmd
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.controller_helper import ControllerLib
from commons.exceptions import CTException
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from commons import constants as cons
from commons.constants import const
from commons import commands
from libs.ras.ras_test_lib import RASTestLib
from libs.ha.ha_common_libs import HALibs
from libs.csm.cli.cortx_node_cli_resource import CortxNodeCLIResourceOps
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.s3 import S3H_OBJ, s3_test_lib
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from config.s3 import S3_CFG
from scripts.s3_bench import s3bench

LOGGER = logging.getLogger(__name__)
S3_OBJ = s3_test_lib.S3TestLib()

class TestNodeHealth:
    """
    cortx_setup resource show health Test suite
    """
    @classmethod
    def setup_class(cls):
        """  Setup module  """
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.node_cnt = len(CMN_CFG["nodes"])
        LOGGER.info("Total number of nodes in cluster: %s", cls.node_cnt)
        cls.list1 = []
        for index in range(1, cls.node_cnt):
            cls.list1.append(index)
        cls.node_num = cls.list1
        cls.test_node = secrets.choice(cls.node_num)
        cls.host = CMN_CFG["nodes"][cls.test_node-1]["host"]
        cls.uname = CMN_CFG["nodes"][cls.test_node-1]["username"]
        cls.passwd = CMN_CFG["nodes"][cls.test_node-1]["password"]
        cls.hostname = CMN_CFG["nodes"][cls.test_node-1]["hostname"]
        cls.io_bucket_name = "iobkt1-copyobject-{}".format(perf_counter_ns())
        cls.ras_test_obj = RASTestLib(host=cls.hostname, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.hostname, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.hostname, username=cls.uname,
                                password=cls.passwd)
        cls.encl_ip = CMN_CFG["enclosure"]["primary_enclosure_ip"]
        cls.encl_username = CMN_CFG["enclosure"]["enclosure_user"]
        cls.encl_passwd = CMN_CFG["enclosure"]["enclosure_pwd"]
        cls.CONT_OBJ = ControllerLib(host=cls.hostname, h_user=cls.uname,
                                     h_pwd=cls.passwd,
                                     enclosure_ip=cls.encl_ip,
                                     enclosure_user=cls.encl_username,
                                     enclosure_pwd=cls.encl_passwd)
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.alert_api_obj = GenerateAlertLib()
        cls.resource_cli = CortxNodeCLIResourceOps(host=cls.hostname, username=cls.uname,
                                                   password=cls.passwd)
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
        cls.disable_disk = False
        cls.starttime = time.time()
        resp = cls.ras_test_obj.get_node_drive_details()
        if not resp[0]:
            assert_utils.assert_true(resp[0], resp)
        cls.drive_name = resp[1].split("/")[2]
        cls.host_num = resp[2]
        cls.drive_count = resp[3]
        LOGGER.info("Successfully ran setup_class")

    def setup_method(self):
        """Setup operations per test."""
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
            LOGGER.info("Successfully started read_message_bus.py script on node")
        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        self.ras_test_obj.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                        True)
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

        if self.start_msg_bus:
            LOGGER.info("Terminating the process read_message_bus.py")
            self.ras_test_obj.kill_remote_process("read_message_bus.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                if self.node_obj.path_exists(file):
                    self.node_obj.remove_file(filename=file)

        LOGGER.info("Restarting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                        self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])
        self.resource_cli.close_connection()
        LOGGER.info("Successfully performed Teardown operation")

    def s3_ios(self, bucket=None, log_file_prefix="ios", duration="0h1m",
               obj_size="24Kb", **kwargs):
        """
        Perform io's for specific durations.

        1. Create bucket.
        2. perform io's for specified durations.
        3. Check executions successful.
        """
        kwargs.setdefault("num_clients", 2)
        kwargs.setdefault("num_sample", 5)
        kwargs.setdefault("obj_name_pref", "load_gen_")
        kwargs.setdefault("end_point", S3_CFG["s3_url"])
        LOGGER.info("STARTED: s3 io's operations.")
        bucket = bucket if bucket else self.io_bucket_name
        resp = S3_OBJ.create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = S3H_OBJ.get_local_keys()
        resp = s3bench.s3bench(
            access_key,
            secret_key,
            bucket=bucket,
            end_point=kwargs["end_point"],
            num_clients=kwargs["num_clients"],
            num_sample=kwargs["num_sample"],
            obj_name_pref=kwargs["obj_name_pref"],
            obj_size=obj_size,
            duration=duration,
            log_file_prefix=log_file_prefix)
        LOGGER.info(resp)
        assert_utils.assert_true(
            os.path.exists(
                resp[1]),
            f"failed to generate log: {resp[1]}")
        LOGGER.info("ENDED: s3 io's operations.")

    @pytest.mark.lr
    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22520")
    def test_22520_verify_resource_discover(self):
        """Verify resource discover command"""
        resp = self.resource_cli.resource_discover_node_cli()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("The Test Completed successfully %s", resp)

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
            result = self.resource_cli.convert_to_list_format(resp[1], "},")
            LOGGER.info("Test Completed Successfully %s", result)

    # pylint:disable=too-many-locals,too-many-statements,too-many-branches
    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22528")
    def test_22528_verify_os_disk_health(self):
        """Verify resource show --health with removing a drive """
        LOGGER.info("Creating disk fault to check the health status")
        test_cfg = RAS_TEST_CFG["TEST-23606"]
        alert_list = [test_cfg["resource_type"], self.alert_types[
            "missing"], f"srvnode-{self.test_node}.mgmt.public"]
        resp = self.ras_test_obj.list_alert_validation(alert_list)
        if resp[0]:
            LOGGER.info("Alert not present")
            df_obj = pd.DataFrame(index='Step1 Step2 Step3 Step4 Step5 Step6'.split(),
                                  columns='Iteration0'.split())
            df_obj = df_obj.assign(Iteration0='Pass')
            LOGGER.info("Step 1: Getting RAID array details of node %s", self.hostname)
            resp = self.ras_test_obj.get_raid_array_details()
            if not resp[0]:
                df_obj['Iteration0']['Step1'] = 'Fail'
            md_arrays = resp[1] if resp[0] \
                else assert_utils.assert_true(resp[0],
                                              "Step 1: Failed to get raid array details")
            LOGGER.info("MDRAID arrays: %s", md_arrays)
            for k, val in md_arrays.items():
                if val["state"] != "Active":
                    df_obj['Iteration0']['Step1'] = 'Fail'
                    assert_utils.assert_true(False, f"Step 1: Array {k} is in degraded state")
            LOGGER.info("Step 1: Getting details of drive to be removed")
            resp = self.ras_test_obj.get_node_drive_details()
            if not resp[0]:
                df_obj['Iteration0']['Step1'] = 'Fail'
            assert_utils.assert_true(resp[0], f"Step 1: Failed to get details of OS disks."
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
                df_obj['Iteration0']['Step2'] = 'Fail'
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
                    df_obj['Iteration0']['Step3'] = 'Fail'
                    LOGGER.error("Step 3: Expected alert not found. Error: %s",
                                 resp[1])
                else:
                    LOGGER.info("Step 3: Checked generated alert logs. Response: "
                                "%s", resp)
            LOGGER.info("Step 4: Checking CSM REST API for alert")
            resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                              self.alert_types["missing"],
                                                              False, test_cfg["resource_type"])
            if not resp_csm:
                df_obj['Iteration0']['Step4'] = 'Fail'
                LOGGER.error("Step 4: Expected alert not found. Error: %s",
                             test_cfg["csm_error_msg"])
            else:
                LOGGER.info("Step 4: Successfully checked CSM REST API for "
                            "fault alert. Response: %s", resp_csm)
            resp = self.resource_cli.resource_discover_node_cli()
            if resp[0]:
                resp = self.resource_cli.resource_show_disk_health(timeout=5 * 60)
                assert_utils.assert_true(resp[0], resp[1])
                result = self.resource_cli.split_str_to_list(resp[1], "},")
                LOGGER.info("Health Map is %s", result)
            LOGGER.info("Resolving fault...")
            LOGGER.info("Step 5: Connecting OS drive %s", drive_name)
            resp = self.alert_api_obj.generate_alert(
                AlertType.OS_DISK_ENABLE,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"host_num": host_num,
                                  "drive_count": drive_count})
            if not resp[0]:
                df_obj['Iteration0']['Step5'] = 'Fail'
                LOGGER.error("Step 5: Failed to resolve fault.")
            else:
                LOGGER.info("Step 5: Successfully connected disk %s\n Response: %s",
                            resp[1], resp)
            new_drive = resp[1]
            LOGGER.info("Step 6: Getting raid partitions of drive %s", new_drive)
            resp = self.ras_test_obj.get_drive_partition_details(
                filepath=RAS_VAL['ras_sspl_alert']['file']['fdisk_file'],
                drive=new_drive)
            if not resp[0]:
                df_obj['Iteration0']['Step6'] = 'Fail'
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
                df_obj['Iteration0']['Step7'] = 'Fail'
            new_array = resp[1] if resp[0] \
                else assert_utils.assert_true(resp[0], "Step 7: Failed to "
                                                       "add drive in raid "
                                                       "array")
            LOGGER.info("New MDARRAY: %s", new_array)
            time.sleep(self.cm_cfg["sleep_val"])
            if self.start_msg_bus:
                LOGGER.info("Step 8: Checking the generated alert logs")
                alert_list = [test_cfg["resource_type"],
                              self.alert_types["insertion"]]
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                if not resp[0]:
                    df_obj['Iteration0']['Step8'] = 'Fail'
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
                df_obj['Iteration0']['Step9'] = 'Fail'
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
                result = self.resource_cli.split_str_to_list(resp[1], "},")
                LOGGER.info("Health Map is: %s", result)
            LOGGER.info("Summary of test: %s", df_obj)
            result = bool(df_obj.values)
            assert_utils.assert_true(result, "Test failed !")
        else:
            LOGGER.info("Alert is already Present")
            resp = self.resource_cli.resource_discover_node_cli()
            if resp[0]:
                resp = self.resource_cli.resource_show_disk_health(timeout=5 * 60)
                assert_utils.assert_true(resp[0], resp[1])
                result = self.resource_cli.split_str_to_list(resp[1], "},")
                LOGGER.info("Test Completed Successfully %s", result)

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22529")
    def test_22529_verify_psu_health(self):
        """Verify resource show --health with removing a PSU from server node"""
        resp = self.resource_cli.resource_discover_node_cli()
        if resp[0]:
            resp = self.resource_cli.resource_show_psu_health(timeout=5*60)
            assert_utils.assert_true(resp[0], resp[1])
            result = self.resource_cli.convert_to_list_format(resp[1], "},")
            LOGGER.info("Test Completed Successfully %s", result)

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22530")
    def test_22530_wrong_parameter(self):
        """Verify resource show --health with wrong rpath"""
        resp = self.resource_cli.resource_discover_node_cli()
        if not resp[0]:
            LOGGER.error("Failed to discover the Health Map")
        resp = self.resource_cli.resource_health_show_invalid_param(timeout=5 * 60)
        error_msg = "cortx_setup command Failed:"
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_that(resp[1], error_msg)
        LOGGER.info("Requesting resource health failed with wrong rpath with error %s",
                    resp[1])

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-26848")
    def test_26848(self):
        """
        Verify "cortx_setup cluster reset --type data" command works fine
        """
        LOGGER.info("Step 1: Check cluster status, all services are running before starting test.")

        HALibs.check_cluster_health()
        LOGGER.info("Step 2: Start S3 IO.")
        io_bucket_name = "test-26848-pre-reset-{}".format(perf_counter_ns())
        self.s3_ios(bucket=io_bucket_name, log_prefix="test_26848_ios", duration="0h1m")

        username = CMN_CFG["nodes"][0]["username"]
        password = CMN_CFG["nodes"][0]["password"]
        host = CMN_CFG["nodes"][0]["hostname"]
        LOGGER.info("Step 3: Verify cortx_setup cluster reset --type data command.")
        _, result = run_remote_cmd(
            cmd=commands.CORTX_DATA_CLEANUP,
            hostname=host,
            username=username,
            password=password,
            read_lines=True)

        LOGGER.info(" ********* Cortx setup cleanup command response for %s ********* "
                    "\n %s \n", self.host, result)
        time.sleep(120)
        LOGGER.info("Step 4: Check cluster status, all services are running before starting test.")
        HALibs.check_cluster_health()

        LOGGER.info("Step 5: Verify if log files got cleaned from all nodes.")

        nodes = CMN_CFG["nodes"]
        for _, node in enumerate(nodes):

            LOGGER.info(node)
            _, result = run_remote_cmd(
                cmd="cat " + const.HAPROXY_LOG_PATH,
                hostname=node["hostname"],
                username=node["username"],
                password=node["password"],
                read_lines=True)

            LOGGER.info(" ********* path exists %s ********* \n %s \n",
                        node["hostname"], result)
            if "No such file" in str(result):
                LOGGER.info("reset worked fine")
            else:
                LOGGER.error("after reset also haproxy.log file exists")
        LOGGER.info("Step 6: Create bucket to verify s3 account got deleted")
        bucket = "test-26848-post-reset-{}".format(perf_counter_ns())
        try:
            S3_OBJ.create_bucket(bucket)
        except CTException as response:
            LOGGER.info("Response = %s", response)
            if "InvalidAccessKeyId" in str(response):
                LOGGER.info("S3 account got deleted as expected")
            else:
                LOGGER.error("S3 account not deleted")

        LOGGER.info("Test Completed.")
