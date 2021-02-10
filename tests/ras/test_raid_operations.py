#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
RAS test file for all the RAS tests related to RAID operations.
"""

import os
import time
import logging
import pytest
from libs.ras.ras_test_lib import RASTestLib
from commons.utils import config_utils as conf_utils
from commons.utils import system_utils as sys_utils
from commons.helpers.s3_helper import S3Helper
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import constants as common_cons
from commons import commands as common_cmds
#from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib, AlertType

# Global Constants
BYTES_TO_READ = common_cons.BYTES_TO_READ
LOGGER = logging.getLogger(__name__)

RAS_TEST_CFG = conf_utils.read_yaml("config/ras_config.yaml")[1]
TEST_CFG = conf_utils.read_yaml("config/ras_test.yaml")[1]
CM_CFG = conf_utils.read_yaml("config/common_config.yaml")[1]
CSM_CONF = conf_utils.read_yaml(common_cons.CSM_CONF)[1]


class RAIDOperations:
    """
    Test suite for performing RAID related operations
    """

    def setup_module(self):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        self.host = CM_CFG["host"]
        self.uname = CM_CFG["username"]
        self.passwd = CM_CFG["password"]
        self.nd_obj = Node(hostname=self.host, username=self.uname, password=self.passwd)
        self.hlt_obj = Health(hostname=self.host, username=self.uname, password=self.passwd)
        try:
            self.s3_obj = S3Helper()
        except ImportError as err:
            LOGGER.info(str(err))
            self.s3_obj = S3Helper.get_instance()
        self.ras_obj = RASTestLib(host=self.host, username=self.uname, password=self.passwd)
        self.csm_alert_obj = SystemAlerts()
        self.csm_user_obj = RestCsmUser()
        self.alert_api_obj = GenerateAlertLib()
        self.cm_cfg = RAS_TEST_CFG["ras_sspl_alert"]
        LOGGER.info("Done: Setup module operations")

    def setup_function(self):
        """
        Setup operations for each test.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.md_device = RAS_TEST_CFG["raid_param"]["md0_path"]
        self.raid_stopped = False
        self.failed_disk = False
        self.removed_disk = False
        # Enable this flag for starting RMQ channel
        self.start_rmq = self.cm_cfg["start_rmq"]

        LOGGER.info(
            "Fetching the disks details from mdstat for RAID array {}".format(
                self.md_device))
        md_stat = self.nd_obj.get_mdstat()
        self.disks = md_stat["devices"][os.path.basename(
            self.md_device)]["disks"].keys()
        self.disk1 = RAS_TEST_CFG["raid_param"]["disk_path"].format(
            list(self.disks)[0])
        self.disk2 = RAS_TEST_CFG["raid_param"]["disk_path"].format(
            list(self.disks)[1])

        LOGGER.info("Updating transmit interval value to 10")
        res = self.ras_obj.update_threshold_values(
            common_cons.KV_STORE_DISK_USAGE,
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_key"],
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_val"])
        assert res is True

        LOGGER.info("Delete keys with prefix SSPL_")
        cmd = common_cmds.REMOVE_UNWANTED_CONSUL
        response = sys_utils.run_remote_cmd(cmd=cmd, hostname=self.host,
                                            username=self.uname,
                                            password=self.passwd,
                                            read_nbytes=BYTES_TO_READ,
                                            shell=False)
        assert response[0] is True, response[1]

        LOGGER.info("Restarting sspl service")
        self.hlt_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"], shell=False)
        time.sleep(self.cm_cfg["after_service_restart_sleep_val"])

        LOGGER.info(
            "Verifying the status of sspl and rabittmq service is online")
        resp = self.s3_obj.get_s3server_service_status(
            self.cm_cfg["service"]["sspl_service"])
        assert resp[0] is True, resp[1]

        resp = self.s3_obj.get_s3server_service_status(
            self.cm_cfg["service"]["rabitmq_service"])
        assert resp[0] is True, resp[1]
        LOGGER.info(
            "Validated the status of sspl and rabittmq service are online")

        if self.start_rmq:
            LOGGER.info("Running rabbitmq_reader.py script on node")
            resp = self.ras_obj.start_rabbitmq_reader_cmd(self.cm_cfg["sspl_exch"],
                                                          self.cm_cfg["sspl_key"])
            assert resp is True
            LOGGER.info("Successfully started rabbitmq_reader.py script on node")

        res = self.ras_obj.sspl_log_collect()
        assert res[0] is True, res[1]
        self.starttime = time.time()
        LOGGER.info("ENDED: Setup Operations")

    def teardown_function(self):
        """
        Teardown operations after each test.
        """
        LOGGER.info("STARTED: Teardown Operations")
        if self.failed_disk:
            resp = self.alert_api_obj.generate_alert(
                AlertType.raid_remove_disk_alert,
                input_parameters={
                    "operation": RAS_TEST_CFG["raid_param"]["remove_operation"],
                    "md_device": self.md_device,
                    "disk": self.failed_disk})
            assert resp[0] is True, resp[1]
            self.removed_disk = self.failed_disk

        if self.removed_disk:
            resp = self.alert_api_obj.generate_alert(
                AlertType.raid_add_disk_alert,
                input_parameters={
                    "operation": RAS_TEST_CFG["raid_param"]["add_operation"],
                    "md_device": self.md_device,
                    "disk": self.removed_disk})
            assert resp[0] is True, resp[1]

        LOGGER.info("Updating transmit interval value")
        res = self.ras_obj.update_threshold_values(
            common_cons.KV_STORE_DISK_USAGE,
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_key"],
            self.cm_cfg["sspl_config"]
            ["sspl_trans_intv_dval"])
        assert res is True

        if self.start_rmq:
            LOGGER.info("Terminating the process rabbitmq_reader.py")
            self.ras_obj.kill_remote_process("rabbitmq_reader.py")

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.nd_obj.read_file(filename=
                                          self.cm_cfg["file"]["sspl_log_file"],
                                          local_path=self.cm_cfg["file"]["local_path"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")

        LOGGER.info(
            "Removing file {}".format(
                self.cm_cfg["file"]["sspl_log_file"]))
        self.nd_obj.remove_file(filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_rmq:
            LOGGER.info("Removing alert log file from the Node")
            self.nd_obj.remove_file(
                filename=self.cm_cfg["file"]["alert_log_file"])
            self.nd_obj.remove_file(
                filename=self.cm_cfg["file"]["extracted_alert_file"])

        LOGGER.info("Removing screen log file")
        self.nd_obj.remove_file(filename=self.cm_cfg["file"]["screen_log"])
        self.hlt_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"], shell=False)
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("ENDED: Teardown Operations")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-15733")
    def test_5345(self):
        """
        EOS-10613 RAID: Assemble a array
        """
        LOGGER.info(
            "STARTED: TEST-5345 RAID: Assemble a array")
        raid_cmn_cfg = RAS_TEST_CFG["raid_param"]
        test_cfg = TEST_CFG["test_5345"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by stopping array")
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_stop_device_alert,
            input_parameters={
                "operation": raid_cmn_cfg["stop_operation"],
                "md_device": self.md_device,
                "disk": None})
        assert resp[0] is True, resp[1]
        self.raid_stopped = True
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by stopping array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"]]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID fault_resolved "
            "alert by assembling array")
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_assemble_device_alert,
            input_parameters={
                "operation": raid_cmn_cfg["assemble_operation"],
                "md_device": self.md_device,
                "disk": None})
        assert resp[0] is True, resp[1]
        self.raid_stopped = False
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID fault_resolved alerts by assembling array")

        if self.start_rmq:
            LOGGER.info(
                "Step 5: Checking the generated RAID fault alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault_resolved"]]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
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
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 6: Successfully verified RAID fault_resolved alert using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-5345 RAID: Assemble a array")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-15732")
    def test_5342(self):
        """
        EOS-10615 RAID: Remove a drive from array
        """
        LOGGER.info(
            "STARTED: TEST-5342 RAID: Remove a drive from array")
        raid_cmn_cfg = RAS_TEST_CFG["raid_param"]
        test_cfg = TEST_CFG["test_5342"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk {} from array {}".format(self.disk2, self.md_device))
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_fail_disk_alert,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0] is True, resp[1]
        self.failed_disk = self.disk2
        resource_id = "{}:{}".format(self.md_device, self.disk2)
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing a disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"], resource_id]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk {} from array {}".format(self.disk2, self.md_device))
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_remove_disk_alert,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0] is True, resp[1]
        self.removed_disk = self.disk2
        self.failed_disk = False
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID missing alert "
            "by removing faulty disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_missing"], resource_id]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on RMQ channel logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_missing"],
            False,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 6: Successfully verified RAID missing alert using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-5342 RAID: Remove a drive from array")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-15868")
    def test_4785(self):
        """
        EOS-10617 RAID: Fail a drive of array
        """
        LOGGER.info(
            "STARTED: TEST-4785 RAID: Fail a drive of array")
        raid_cmn_cfg = RAS_TEST_CFG["raid_param"]
        test_cfg = TEST_CFG["test_4785"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by "
            "failing disk {} from array {}".format(self.disk2, self.md_device))
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_fail_disk_alert,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0] is True, resp[1]
        self.failed_disk = self.disk2
        resource_id = "{}:{}".format(self.md_device, self.disk2)
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing a disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"], resource_id]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-4785 RAID: Fail a drive of array")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-16214")
    def test_5343(self):
        """
        EOS-10614 RAID: Add drive to array
        """
        LOGGER.info(
            "STARTED: TEST-5343 RAID: Add drive to array")
        raid_cmn_cfg = RAS_TEST_CFG["raid_param"]
        test_cfg = TEST_CFG["test_5343"]
        csm_error_msg = raid_cmn_cfg["csm_error_msg"]

        LOGGER.info(
            "Step 1: Running ALERT API for generating RAID fault alert by failing disk {} from array {}".format(
                self.disk2, self.md_device))
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_fail_disk_alert,
            input_parameters={
                "operation": raid_cmn_cfg["fail_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0] is True, resp[1]
        self.failed_disk = self.disk2
        resource_id = "{}:{}".format(self.md_device, self.disk2)
        LOGGER.info(
            "Step 1: Ran ALERT API for generating RAID fault alert by failing a disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 2: Checking the generated RAID fault alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_fault"], resource_id]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 2: Verified the RAID fault alert on RMQ channel logs")

        LOGGER.info("Step 3: Checking CSM REST API for RAID fault alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_fault"],
            False,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 3: Successfully verified RAID fault alert using CSM REST API")

        LOGGER.info(
            "Step 4: Running ALERT API for generating RAID missing alert by "
            "removing faulty disk {} from array {}".format(self.disk2, self.md_device))
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_remove_disk_alert,
            input_parameters={
                "operation": raid_cmn_cfg["remove_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0] is True, resp[1]
        self.failed_disk = False
        self.removed_disk = self.disk2
        LOGGER.info(
            "Step 4: Ran ALERT API for generating RAID missing alert by removing faulty disk from array")

        if self.start_rmq:
            LOGGER.info(
                "Step 5: Checking the generated RAID missing alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_missing"], resource_id]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 5: Verified the RAID missing alert on RMQ channel logs")

        LOGGER.info("Step 6: Checking CSM REST API for RAID missing alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_missing"],
            False,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 6: Successfully verified RAID missing alert using CSM REST API")

        LOGGER.info(
            "Step 7: Running ALERT API for generating RAID fault_resolved alert by "
            "adding removed disk {} to array {}".format(self.disk2, self.md_device))
        resp = self.alert_api_obj.generate_alert(
            AlertType.raid_add_disk_alert,
            input_parameters={
                "operation": raid_cmn_cfg["add_operation"],
                "md_device": self.md_device,
                "disk": self.disk2})
        assert resp[0] is True, resp[1]
        LOGGER.info(
            "Step 7: Ran ALERT API for generating RAID fault_resolved alert "
            "by adding removed disk to array")

        md_stat = resp[1]
        if self.start_rmq:
            LOGGER.info(
                "Step 8: Checking the generated RAID insertion alert on RMQ channel logs")
            alert_list = [test_cfg["resource_type"],
                          test_cfg["alert_insertion"], resource_id]
            resp = self.ras_obj.list_alert_validation(alert_list)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 8: Verified the RAID insertion alert on RMQ channel logs")

        LOGGER.info("Step 9: Checking CSM REST API for RAID insertion alert")
        time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
        resp = self.csm_alert_obj.verify_csm_response(
            self.starttime,
            test_cfg["alert_insertion"],
            True,
            test_cfg["resource_type"])
        assert resp is True, csm_error_msg
        LOGGER.info(
            "Step 9: Successfully verified RAID insertion alert using CSM REST API")

        if not all(md_stat["devices"][os.path.basename(self.md_device)]["status"]["synced"]):
            time.sleep(raid_cmn_cfg["resync_delay"])

        if all(md_stat["devices"][os.path.basename(self.md_device)]["status"]["synced"]):
            if self.start_rmq:
                LOGGER.info(
                    "Step 10: Checking the generated RAID fault_resolved alert on RMQ channel logs")
                alert_list = [test_cfg["resource_type"],
                              test_cfg["alert_fault_resolved"], resource_id]
                resp = self.ras_obj.list_alert_validation(alert_list)
                assert resp[0] is True, resp[1]
                LOGGER.info(
                    "Step 10: Verified the RAID fault_resolved alert on RMQ channel logs")

            LOGGER.info(
                "Step 11: Checking CSM REST API for RAID fault_resolved alert")
            time.sleep(raid_cmn_cfg["csm_alert_reflection_time"])
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                test_cfg["alert_fault_resolved"],
                True,
                test_cfg["resource_type"])
            assert resp is True, csm_error_msg
        self.removed_disk = False
        LOGGER.info(
            "Step 11: Successfully verified RAID fault_resolved alert using CSM REST API")
        LOGGER.info(
            "ENDED: TEST-5343 RAID: Add drive to array")
