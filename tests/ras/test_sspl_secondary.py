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

"""SSPL test cases: Secondary Node."""

import logging
import os
import time

import pytest

from commons import commands as common_cmd
from commons import constants as cons
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG
from config import RAS_TEST_CFG
from config import RAS_VAL
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.s3 import S3H_OBJ

LOGGER = logging.getLogger(__name__)


class TestSSPLSecondary:
    """SSPL Test Suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.nodes = CMN_CFG["nodes"]
        cls.host2 = CMN_CFG["nodes"][1]["host"]
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]

        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)

        cls.ras_test_obj2 = RASTestLib(host=cls.host2, username=cls.uname,
                                       password=cls.passwd)
        cls.node_obj2 = Node(hostname=cls.host2, username=cls.uname,
                             password=cls.passwd)
        cls.health_obj2 = Health(hostname=cls.host2, username=cls.uname,
                                 password=cls.passwd)

        cls.csm_alert_obj = SystemAlerts(cls.node_obj2)
        cls.s3obj = S3H_OBJ

        # Enable this flag for starting RMQ channel
        cls.start_rmq = cls.cm_cfg["start_rmq"]

        field_list = ["primary_controller_ip", "secondary_controller_ip",
                      "primary_controller_port", "secondary_controller_port",
                      "user", "password", "secret"]
        LOGGER.info("Putting expected values in KV store")
        for field in field_list:
            res = cls.ras_test_obj.put_kv_store(
                CMN_CFG["enclosure"]["enclosure_user"],
                CMN_CFG["enclosure"]["enclosure_pwd"], field)
            assert res

    def setup_method(self):
        """Setup operations."""
        self.starttime = time.time()
        self.sspl_disable = False
        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj2.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"], False)

        LOGGER.info("Performing Setup operations")

        LOGGER.info("Checking SSPL state file")
        res = self.ras_test_obj2.get_sspl_state()
        if not res:
            LOGGER.info("SSPL not present updating same on server")
            response = self.ras_test_obj2.check_status_file()
            assert response[0], response[1]
        LOGGER.info("Done Checking SSPL state file")

        LOGGER.info("Delete keys with prefix SSPL_")
        cmd = common_cmd.REMOVE_UNWANTED_CONSUL
        response = self.node_obj2.execute_cmd(cmd=cmd,
                                              read_nbytes=cons.BYTES_TO_READ)
        LOGGER.info("Response is: %s", response)

        LOGGER.info("Restarting sspl service")
        self.health_obj2.restart_pcs_resource(self.cm_cfg["sspl_resource_id"])
        time.sleep(self.cm_cfg["sspl_timeout"])
        LOGGER.info(
            "Verifying the status of sspl and rabittmq service is online")

        # Getting SSPl and RabbitMQ service status
        services = self.cm_cfg["service"]
        resp = self.s3obj.get_s3server_service_status(
            service=services["sspl_service"], host=self.host, user=self.uname,
            pwd=self.passwd)
        assert resp[0], resp[1]
        resp = self.s3obj.get_s3server_service_status(
            service=services["rabitmq_service"], host=self.host,
            user=self.uname,
            pwd=self.passwd)
        assert resp[0], resp[1]

        LOGGER.info(
            "Validated the status of sspl and rabittmq service are online")

        if self.start_rmq:
            LOGGER.info("Running rabbitmq_reader.py script on node")
            resp = self.ras_test_obj2.start_rabbitmq_reader_cmd(
                self.cm_cfg["sspl_exch"], self.cm_cfg["sspl_key"])
            assert resp, "Failed to start RMQ channel"
            LOGGER.info(
                "Successfully started rabbitmq_reader.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj2.sspl_log_collect()
        assert res[0], res[1]
        LOGGER.info("Started collection of sspl logs")

        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        self.ras_test_obj2.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                         True)

        if os.path.exists(self.cm_cfg["file"]["telnet_xml"]):
            LOGGER.info("Remove telnet file")
            os.remove(self.cm_cfg["file"]["telnet_xml"])

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj2.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.node_obj2.read_file(
            filename=self.cm_cfg["file"]["sspl_log_file"],
            local_path=self.cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")

        LOGGER.info(
            "Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        self.node_obj2.remove_file(filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_rmq:
            LOGGER.info("Terminating the process rabbitmq_reader.py")
            self.ras_test_obj2.kill_remote_process("rabbitmq_reader.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                self.node_obj2.remove_file(filename=file)

        self.health_obj2.restart_pcs_resource(
            resource=self.cm_cfg["sspl_resource_id"])
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Successfully performed Teardown operation")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-14034")
    @pytest.mark.skip
    @CTFailOn(error_handler)
    def test_1648(self):
        """
        EOS-10619: Pacemaker Resource Agents for SSPL service(Stop sspl service
        on Node)

        pacemaker_sspl
        """
        LOGGER.info(
            "STARTED: Pacemaker Resource Agents for SSPL service(Stop sspl "
            "service on Node)")
        test_cfg = RAS_TEST_CFG["test_1648"]

        LOGGER.info(
            "Step 1: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 2: Checking sspl-ll service status on secondary "
                    "node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Sspl-ll is up and running on secondary node")

        LOGGER.info("Step 3: Checking sspl state on both the nodes")
        res = self.ras_test_obj.get_sspl_state()
        LOGGER.info("State of sspl on %s is %s", self.nodes[0]["host"], res[1])

        res = self.ras_test_obj2.get_sspl_state()
        LOGGER.info("State of sspl on %s is %s", self.nodes[1]["host"], res[1])

        LOGGER.info("Step 4: Stopping sspl-ll service on node %s", self.nodes[1]["host"])
        resp = self.ras_test_obj2.enable_disable_service(
            "disable", self.cm_cfg["sspl_resource_id"])
        assert not resp[0], resp[1]
        self.sspl_disable = True
        LOGGER.info("Step 4: SSPL service was successfully stopped and "
                    "validated on node %s", self.nodes[1]["host"])

        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Step 5: Checking if sspl-ll is restarted automatically "
                    "by pacemaker")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 5: Sspl-ll is up and running on node %s", self.nodes[1]["host"])

        LOGGER.info("Inducing FAN alert")
        buffer_sz = test_cfg["buffer_sz"]

        LOGGER.info(
            "Step 6: Run 'ipmitool sdr list' to inquire about FAN "
            "state/details")
        fan_name = self.ras_test_obj2.get_fan_name()
        LOGGER.info("Step 6: FAN to be used for inducing fault: %s", fan_name)

        LOGGER.info("Step 7: Generating fan alert using ipmi tool")
        cmd = test_cfg["ipmitool_event"].format(fan_name, test_cfg["op"])
        LOGGER.info("Running command: %s", cmd)
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)

        LOGGER.info("SEL response : %s", resp)
        LOGGER.info(
            "Step 7: Successfully generated fault on fan %s", fan_name)

        time.sleep(test_cfg["wait_time"])
        LOGGER.info("Step 8: Checking CSM REST API for no alerts")
        csm_resp = self.csm_alert_obj.verify_csm_response(
            self.starttime, test_cfg["alert_type"], False,
            test_cfg["resource_type"])

        LOGGER.info("Step 9: Resolving fan fault using ipmi tool")
        cmd = common_cmd.RESOLVE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info("Running command: %s", cmd)
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)
        LOGGER.info("SEL response : %s", resp)
        LOGGER.info("Step 9: Successfully resolved fault on fan %s", fan_name)

        if self.start_rmq:
            time.sleep(test_cfg["wait_time"])
            LOGGER.info("Step 10: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            LOGGER.debug("RMQ alert check: %s", alert_list)
            self.ras_test_obj2.alert_validation(alert_list)
            LOGGER.info(
                "Step 10: Successfully verified the RabbitMQ channel for alert "
                "responses")

        assert csm_resp, "No alert should be seen in CSM REST API"
        LOGGER.info(
            "Step 8: Successfully checked CSM REST API for no alerts")

        LOGGER.info(
            "ENDED: Pacemaker Resource Agents for SSPL service(Stop sspl "
            "service on Node)")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-14035")
    @pytest.mark.skip
    @CTFailOn(error_handler)
    def test_1783(self):
        """
        EOS-10620: Run SSPL in degraded mode (Fail  SSPL service)

        pacemaker_sspl
        """
        LOGGER.info(
            "STARTED: Run SSPL in degraded mode (Fail  SSPL service)")
        service_cfg = self.cm_cfg["service"]
        test_cfg = RAS_TEST_CFG["test_1648"]

        LOGGER.info(
            "Step 1: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 2: Checking sspl-ll service status on secondary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Sspl-ll is up and running on secondary node")

        LOGGER.info("Step 3: Checking sspl state on %s", self.nodes[0]["host"])
        res = self.ras_test_obj.get_sspl_state()
        LOGGER.info("State of sspl on %s is %s", self.nodes[0]["host"], res[1])

        LOGGER.info("Step 3: Checking sspl state on %s", self.nodes[1]["host"])
        res = self.ras_test_obj2.get_sspl_state()
        LOGGER.info("State of sspl on %s is %s", self.nodes[1]["host"], res[1])

        LOGGER.info("Step 4: Killing sspl-ll service on node %s", self.nodes[1]["host"])
        resp = self.ras_test_obj2.check_service_recovery(
            service_cfg["sspl_service"])

        assert resp
        LOGGER.info("Step 4: SSPL service was successfully killed and "
                    "validated on node %s", self.nodes[1]["host"])

        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Step 5: Checking if sspl-ll is restarted automatically "
                    "by pacemaker")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 5: Sspl-ll is up and running on node %s", self.nodes[1]["host"])

        LOGGER.info("Inducing FAN alert")
        buffer_sz = test_cfg["buffer_sz"]

        LOGGER.info(
            "Step 6: Run 'ipmitool sdr list' to inquire about FAN "
            "state/details")
        fan_name = self.ras_test_obj2.get_fan_name()
        LOGGER.info("Step 6: FAN to be used for inducing fault: %s", fan_name)

        LOGGER.info("Step 7: Generating fan alert using ipmi tool")
        cmd = test_cfg["ipmitool_event"].format(fan_name, test_cfg["op"])
        LOGGER.info("Running command: %s", cmd)
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)
        LOGGER.info("SEL response : %s", resp)

        LOGGER.info(
            "Step 7: Successfully generated fault on fan %s", fan_name)

        time.sleep(test_cfg["wait_time"])
        LOGGER.info("Step 8: Checking CSM REST API for no alerts")
        csm_resp = self.csm_alert_obj.verify_csm_response(
            self.starttime, test_cfg["alert_type"], False,
            test_cfg["resource_type"])

        LOGGER.info("Step 9: Resolving fan fault using ipmi tool")
        cmd = common_cmd.RESOLVE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info("Running command: %s", cmd)
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)
        LOGGER.info("SEL response : %s", resp)
        LOGGER.info("Step 9: Successfully resolved fault on fan %s", fan_name)

        if self.start_rmq:
            time.sleep(test_cfg["wait_time"])
            LOGGER.info("Step 10: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            LOGGER.debug("RMQ alert check: %s", alert_list)
            self.ras_test_obj2.alert_validation(alert_list)
            LOGGER.info(
                "Step 10: Successfully verified the RabbitMQ channel for alert "
                "responses")

        assert csm_resp, "No alert should be seen in CSM REST API"
        LOGGER.info(
            "Step 8: Successfully checked CSM REST API for no alerts")

        LOGGER.info(
            "ENDED: Pacemaker Resource Agents for SSPL service(Stop sspl "
            "service on Node)")

    # pylint: disable=too-many-statements
    @pytest.mark.skip
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-14794")
    @CTFailOn(error_handler)
    def test_1645(self):
        """
        EOS-10618: Pacemaker Resource Agents for SSPL service (Reboot the Node
        server)

        pacemaker_sspl
        """
        LOGGER.info(
            "STARTED: Pacemaker Resource Agents for SSPL service (Reboot the "
            "Node server)")
        test_cfg = RAS_TEST_CFG["test_1645"]

        LOGGER.info(
            "Step 1: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 2: Checking sspl-ll service status on secondary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Sspl-ll is up and running on secondary node")

        LOGGER.info("Checking sspl state on node %s", self.host2)
        res = self.ras_test_obj2.get_sspl_state_pcs()
        LOGGER.info("SSPL state is %s", res)

        master_node = res["masters"].replace("srv", "eos")
        slave_node = res["slaves"].replace("srv", "eos")

        node_obj_master = Node(hostname=master_node, username=self.uname,
                               password=self.passwd)
        node_obj_slave = Node(hostname=slave_node, username=self.uname,
                              password=self.passwd)
        ras_obj_slave = RASTestLib(host=slave_node, username=self.uname,
                                   password=self.passwd)
        LOGGER.info(
            "Step 3: Rebooting node %s having sspl service status as active",
            master_node)
        resp = node_obj_master.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                           read_nbytes=test_cfg["buffer_sz"],
                                           exc=False)
        LOGGER.info(
            "Step 3: Rebooted node: %s, Response: %s", master_node, resp)

        LOGGER.info(
            "Step 4: Inducing FAN alert on node %s", slave_node)

        LOGGER.info(
            "Run 'ipmitool sdr list' to inquire about FAN state/details")
        fan_name = ras_obj_slave.get_fan_name()
        LOGGER.info(
            "FAN to be used for inducing fault: %s", fan_name)

        LOGGER.info("Generating fan alert using ipmi tool")
        cmd = common_cmd.GENERATE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info("Running command: %s", cmd)
        resp = node_obj_slave.execute_cmd(cmd=cmd,
                                          read_nbytes=test_cfg["buffer_sz"])
        LOGGER.info("SEL response : %s", resp)
        LOGGER.info(
            "Step 4: Successfully generated fault on fan %s", fan_name)

        time.sleep(test_cfg["alert_delay"])
        LOGGER.info("Step 5: Checking CSM REST API for no alerts")
        csm_resp = self.csm_alert_obj.verify_csm_response(
            self.starttime, test_cfg["alert_type"], False,
            test_cfg["resource_type"])

        LOGGER.info("Step 6: Resolving fan fault using ipmi tool")
        cmd = common_cmd.RESOLVE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info("Running command: %s", cmd)
        resp = node_obj_slave.execute_cmd(cmd=cmd,
                                          read_nbytes=test_cfg["buffer_sz"])
        LOGGER.info("SEL response : %s", resp)
        LOGGER.info(
            "Step 6: Successfully resolved fault on fan %s", fan_name)

        if self.start_rmq:
            time.sleep(test_cfg["alert_delay"])
            LOGGER.info("Step 6: Checking the generated alert logs on node %s",
                        slave_node)
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            LOGGER.debug("RMQ alert check: %s", alert_list)
            resp = ras_obj_slave.alert_validation(alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 6: Successfully verified the RabbitMQ channel for fan "
                "alert responses")

        LOGGER.info(
            "Waiting for %s sec for node %s and services to come online",
            test_cfg["reboot_delay"], master_node)
        time.sleep(test_cfg["reboot_delay"])

        LOGGER.info(
            "Step 7: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 7: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 8: Checking sspl-ll service status on secondary node")
        resp = self.s3obj.get_s3server_service_status(
            service=self.cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp[0], resp[1]
        LOGGER.info("Step 8: Sspl-ll is up and running on secondary node")

        LOGGER.info("Checking sspl state on node %s", self.host2)
        res = self.ras_test_obj2.get_sspl_state_pcs()
        LOGGER.info("SSPL state is %s", res)

        LOGGER.info(
            "Step 9: Check if sspl services has swap their roles after a node "
            "reboot")
        assert_utils.compare(slave_node, res["masters"].replace("srv", "eos"))
        assert_utils.compare(master_node, res["slaves"].replace("srv", "eos"))

        assert csm_resp, "No alert should be seen in CSM REST API"
        LOGGER.info(
            "Step 8: Successfully checked CSM REST API for no alerts")

        LOGGER.info(
            "Step 9: Verified that sspl services has swap their roles after a "
            "node reboot")
        LOGGER.info(
            "ENDED: Pacemaker Resource Agents for SSPL service (Reboot the "
            "Node server)")
