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
HA test suite for node start stop operations.
"""

import logging
import time
from random import SystemRandom
import pytest
from commons import commands as cmds
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.bmc_helper import Bmc
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import HA_CFG
from config import RAS_TEST_CFG
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cortx_cli import CortxCli
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.ha.ha_common_libs import HALibs
from libs.s3.cortxcli_test_lib import CSMAccountOperations

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-lines
class TestHANodeStartStop:
    """
    Test suite for node start stop operation tests of HA.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.csm_alerts_obj = SystemAlerts()
        cls.alert_type = RAS_TEST_CFG["alert_types"]
        cls.ha_obj = HALibs()
        cls.ha_rest = SystemHealth()
        cls.loop_count = HA_CFG["common_params"]["loop_count"]
        cls.system_random = SystemRandom()
        cls.csm_obj = CSMAccountOperations()
        cls.setup_type = CMN_CFG["setup_type"]

        cls.node_list = []
        cls.host_list = []
        cls.hlt_list = []
        cls.bmc_list = []
        cls.srvnode_list = []
        cls.username = []
        cls.password = []
        cls.rpdu_encl_ip = []
        cls.rpdu_encl_user = []
        cls.rpdu_encl_pwd = []
        cls.rpdu_encl_port = []
        cls.lpdu_encl_ip = []
        cls.lpdu_encl_user = []
        cls.lpdu_encl_pwd = []
        cls.lpdu_encl_port = []
        cls.sys_list = []
        cls.restored = True
        cls.starttime = None
        cls.user_data = cls.manage_user = cls.email_id = cls.s3_data = cls.monitor_user = None

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.rpdu_encl_ip.append(CMN_CFG["nodes"][node]["encl_rpdu"]["ip"])
            cls.rpdu_encl_user.append(
                CMN_CFG["nodes"][node]["encl_rpdu"]["user"])
            cls.rpdu_encl_pwd.append(
                CMN_CFG["nodes"][node]["encl_rpdu"]["pwd"])
            cls.rpdu_encl_port.append(
                CMN_CFG["nodes"][node]["encl_rpdu"]["port"])
            cls.lpdu_encl_ip.append(CMN_CFG["nodes"][node]["encl_lpdu"]["ip"])
            cls.lpdu_encl_user.append(
                CMN_CFG["nodes"][node]["encl_lpdu"]["user"])
            cls.lpdu_encl_pwd.append(
                CMN_CFG["nodes"][node]["encl_lpdu"]["pwd"])
            cls.lpdu_encl_port.append(
                CMN_CFG["nodes"][node]["encl_lpdu"]["port"])
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.username[node],
                                      password=cls.password[node]))
            cls.hlt_list.append(Health(hostname=cls.host,
                                       username=cls.username[node],
                                       password=cls.password[node]))
            cls.bmc_list.append(Bmc(
                hostname=cls.host,
                username=cls.username[node],
                password=cls.password[node]))
            cls.sys_list.append(
                CortxCliSystemtOperations(
                    host=cls.host,
                    username=cls.username[node],
                    password=cls.password[node]))

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.starttime = time.time()
        self.s3_data = None
        self.user_data = None
        self.manage_user = None
        self.monitor_user = None
        LOGGER.info(
            "Precondition: Check PCS is up and running without any failures.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info(
            "Precondition: Check Health status shows all components as online in cortx REST.")
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Precondition: Health status shows all components as online & PCS looks clean.")

        LOGGER.info("Precondition: Create csm user having manage privileges.")
        self.manage_user = f"manage-user-{time.perf_counter_ns()}"
        self.email_id = f"{self.manage_user}@seagate.com"
        resp = self.csm_obj.csm_user_create(
            self.manage_user, self.email_id, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Created csm user having manage privileges.")
        self.user_data = [self.csm_user, self.manage_user]
        LOGGER.info("ENDED: Setup Operations")

    # pylint: disable-msg=too-many-statements
    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if not self.restored:
            for node in range(self.num_nodes):
                # Check if node needs to be power on from BMC/ssc-cloud.
                resp = system_utils.check_ping(self.host_list[node])
                if not resp:
                    LOGGER.info(
                        "Cleanup: Power on the %s from BMC/ssc-cloud.",
                        self.srvnode_list[node])
                    resp = self.ha_obj.host_power_on(
                        host=self.host_list[node],
                        bmc_obj=self.bmc_list[node])
                    assert_utils.assert_true(
                        resp, f"Failed to power on {self.srvnode_list[node]}.")
                LOGGER.info("Check if enclosure is accessible.")
                resp_encl1 = system_utils.run_remote_cmd(
                    cmd=cmds.CMD_PING.format("10.0.0.2"),
                    hostname=self.host_list[node],
                    username=self.username[node],
                    password=self.password[node])
                if not resp_encl1[0]:
                    resp_rpdu = self.node_list[node].toggle_apc_node_power(
                        pdu_ip=self.rpdu_encl_ip[node], pdu_user=self.rpdu_encl_user[node],
                        pdu_pwd=self.rpdu_encl_pwd[node],
                        node_slot=self.rpdu_encl_port[node], status="on")
                    if not resp_rpdu:
                        LOGGER.info(
                            "Failed to power on controller1 for node %s",
                            self.srvnode_list[node])
                resp_encl2 = system_utils.run_remote_cmd(
                    cmd=cmds.CMD_PING.format("10.0.0.3"),
                    hostname=self.host_list[node],
                    username=self.username[node],
                    password=self.password[node])
                if not resp_encl2[0]:
                    resp_lpdu = self.node_list[node].toggle_apc_node_power(
                        pdu_ip=self.lpdu_encl_ip[node], pdu_user=self.lpdu_encl_user[node],
                        pdu_pwd=self.lpdu_encl_pwd[node],
                        node_slot=self.lpdu_encl_port[node], status="on")
                    if not resp_lpdu:
                        LOGGER.info(
                            "Failed to power on controller2 for node %s",
                            self.srvnode_list[node])
                LOGGER.info(
                    "Enclosure accessible for %s node",
                    self.srvnode_list[node])
                # Check if node needs to be start.
                resp = self.ha_rest.verify_node_health_status_rest(
                    exp_status=['online'], node_id=node, single_node=True)
                if not resp[0]:
                    LOGGER.info(
                        "Cleanup: Start %s.", self.srvnode_list[node])
                    resp = self.ha_rest.perform_cluster_operation(
                        operation='start', resource='node', resource_id=node, login_as={
                            "username": self.user_data[0], "password": self.csm_passwd})
                    assert_utils.assert_true(resp[0], resp[1])
                if self.setup_type == "HW":
                    LOGGER.debug(
                        "HW: Need to enable stonith on the %s after power on",
                        self.host_list[node])
                    resp = system_utils.run_remote_cmd(
                        cmd=cmds.PCS_RESOURCE_STONITH_CMD.format(
                            "enable",
                            node + 1),
                        hostname=self.host_list[node],
                        username=self.username[node],
                        password=self.password[node],
                        read_lines=True)
                    assert_utils.assert_true(
                        resp[0], f"Failed to enable stonith on {self.host_list[node]}")
            if self.s3_data:
                LOGGER.info("Cleanup: Delete s3 accounts and buckets.")
                self.ha_obj.delete_s3_acc_buckets_objects(self.s3_data)
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Cleanup: All nodes are online and PCS looks clean.")
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Delete CSM manage user.")
        sys_obj = self.ha_obj.check_csm_service(
            self.node_list[0], self.srvnode_list, self.sys_list)
        assert_utils.assert_true(
            sys_obj[0],
            f"{sys_obj[1]} Could not get server which has CSM service running.")
        node_id = self.sys_list.index(sys_obj[1])
        cli_obj = (CortxCli(
            host=self.host_list[node_id],
            username=self.username[node_id],
            password=self.password[node_id]))
        cli_obj.open_connection()
        csm_obj = CortxCliCsmUser(session_obj=cli_obj.session_obj)
        csm_obj.login_cortx_cli()
        resp = csm_obj.delete_csm_user(user_name=self.manage_user)
        assert_utils.assert_true(resp[0], resp[1])
        if self.monitor_user:
            LOGGER.info("Cleanup: Delete CSM monitor user.")
            resp = csm_obj.delete_csm_user(user_name=self.monitor_user)
            assert_utils.assert_true(resp[0], resp[1])
        csm_obj.logout_cortx_cli()
        cli_obj.close_connection()
        LOGGER.info(
            "Cleanup: Health status shows all components as online in cortx REST.")
        LOGGER.info("ENDED: Teardown Operations.")

    # pylint: disable=R0915
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-25215")
    @CTFailOn(error_handler)
    def test_node_stop_start_one_by_one(self):
        """
        Test to Check Stop services on node one by one and start it back,
        through cortx REST with admin or manage user
        """
        LOGGER.info(
            "Started: Test to check stop start operation one by one for all nodes.")
        for node in range(self.num_nodes):
            self.restored = False
            opt_user = self.system_random.choice(self.user_data)
            LOGGER.info(
                "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-25215')
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_data = resp[2]
            LOGGER.info("Step 1: IOs are started successfully.")
            LOGGER.info("Step 2: Stop %s from cortx REST with %s user",
                        self.srvnode_list[node], opt_user)
            resp = self.ha_rest.perform_cluster_operation(
                operation='stop',
                resource='node',
                resource_id=node,
                login_as={"username": opt_user, "password": self.csm_passwd})
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.check_ping(host=self.host_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} is failed to ping")
            LOGGER.info("Step 2: %s is stopped and still is pinging",
                        self.srvnode_list[node])
            LOGGER.info(
                "Step 3: Check health status for %s is offline and "
                "cluster/rack/site is degraded with REST",
                self.srvnode_list[node])
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])
            check_rem_node = [
                "offline" if num == node else "online" for num in range(
                    self.num_nodes)]
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 3: Verified status for %s show offline and cluster/rack/site as degraded",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 4: Check for the %s down alert",
                self.srvnode_list[node])
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["get"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            LOGGER.info(
                "Step 4: Verified the %s down alert",
                self.srvnode_list[node])
            LOGGER.info("Step 5: Check PCS status")
            csm_resp = self.ha_obj.get_csm_failover_node(
                srvnode_list=self.srvnode_list,
                node_list=self.node_list,
                sys_list=self.sys_list,
                node=node)
            assert_utils.assert_true(
                csm_resp[0], "Failed to get CSM failover node")
            resp = self.ha_obj.check_pcs_status_resp(
                node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: PCS shows services stopped for %s, services on other nodes shows started",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 6: Start %s from REST with %s user",
                self.srvnode_list[node],
                opt_user)
            resp = self.ha_rest.perform_cluster_operation(
                operation='start',
                resource='node',
                resource_id=node,
                login_as={"username": opt_user, "password": self.csm_passwd})
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 6: Started the %s from REST with %s user",
                self.srvnode_list[node],
                opt_user)
            LOGGER.info(
                "Step 7: Check health status for %s shows online with REST & PCS status clean",
                self.srvnode_list[node])
            resp = self.ha_rest.check_csr_health_status_rest("online")
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(
                ['online'] * self.num_nodes)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Checking PCS clean")
            for hlt_obj in self.hlt_list:
                resp = hlt_obj.check_node_health()
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 7: Verified %s health status shows online and PCS is clean",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 8: Check the IEM fault resolved alert for node up")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            self.starttime = time.time()
            LOGGER.info(
                "Step 8: Verified the IEM fault resolved alert for node up")
            LOGGER.info("Step 9: Check DI for IOs run.")
            resp = self.ha_obj.perform_ios_ops(
                di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 9: Verified DI for IOs run.")
            self.restored = True

        LOGGER.info(
            "Completed: Test to check stop start operation one by one for all nodes.")

    # pylint: disable=R0915
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-25221")
    @CTFailOn(error_handler)
    def test_node_stop_unsafe_shutdown(self):
        """
        Test to Check Stop services on node through cortx REST with admin or manage
        user and with unsafe shutdown
        """
        LOGGER.info(
            "Started: Test to Check Stop services on node from REST and unsafe shutdown.")
        node = self.system_random.choice(list(range(self.num_nodes)))
        self.restored = False
        opt_user = self.system_random.choice(self.user_data)
        LOGGER.info(
            "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-25221')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_data = resp[2]
        LOGGER.info("Step 1: IOs are started successfully.")
        LOGGER.info(
            "Step 2: Stop %s from cortx REST with %s user and check its still pinging",
            self.srvnode_list[node],
            opt_user)
        resp = self.ha_rest.perform_cluster_operation(
            operation='stop',
            resource='node',
            resource_id=node,
            login_as={"username": opt_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.check_ping(host=self.host_list[node])
        assert_utils.assert_true(
            resp, f"{self.host_list[node]} is failed to ping")
        LOGGER.info("Step 2: Node is stopped but still is pinging")
        LOGGER.info("Step 3: Check health status from cortx REST")
        resp = self.ha_rest.check_csr_health_status_rest("degraded")
        assert_utils.assert_true(resp[0], resp[1])
        check_rem_node = [
            "offline" if num == node else "online" for num in range(
                self.num_nodes)]
        resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 3: Verified status for %s show offline and cluster/rack/site as degraded",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 4: Check for the %s down alert",
            self.srvnode_list[node])
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["get"], False, "iem")
        assert_utils.assert_true(resp, "Failed to get alert in CSM")
        LOGGER.info(
            "Step 4: Verified the %s down alert",
            self.srvnode_list[node])
        LOGGER.info("Step 5: Check PCS status")
        csm_resp = self.ha_obj.get_csm_failover_node(
            srvnode_list=self.srvnode_list,
            node_list=self.node_list,
            sys_list=self.sys_list,
            node=node)
        assert_utils.assert_true(
            csm_resp[0], "Failed to get CSM failover node")
        resp = self.ha_obj.check_pcs_status_resp(
            node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 5: PCS shows services stopped for %s, services on other nodes are online",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 6:Unsafe shutdown this node from BMC/ssc-cloud and check node is not pinging")
        LOGGER.info("Shutting down %s", self.srvnode_list[node])
        if self.setup_type == "HW":
            LOGGER.debug(
                "HW: Need to disable stonith on the %s before shutdown",
                self.host_list[node])
            resp = system_utils.run_remote_cmd(
                cmd=cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node + 1),
                hostname=self.host_list[node],
                username=self.username[node],
                password=self.password[node],
                read_lines=True)
            assert_utils.assert_true(
                resp[0], f"Failed to disable stonith on {self.host_list[node]}")
        resp = self.ha_obj.host_safe_unsafe_power_off(
            host=self.host_list[node],
            bmc_obj=self.bmc_list[node],
            node_obj=self.node_list[node])
        assert_utils.assert_true(
            resp, f"Failed to shutdown {self.host_list[node]}")
        LOGGER.info(
            "Step 6: Verified %s is powered off and not pinging.",
            self.host_list[node])
        resp = self.ha_rest.check_csr_health_status_rest("degraded")
        assert_utils.assert_true(resp[0], resp[1])
        check_rem_node = [
            "offline" if num == node else "online" for num in range(
                self.num_nodes)]
        resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 6: Verified status for %s show offline and cluster/rack/site as degraded",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 7: Power on node back from BMC/ssc-cloud and check node status")
        resp = self.ha_obj.host_power_on(
            host=self.host_list[node],
            bmc_obj=self.bmc_list[node])
        assert_utils.assert_true(
            resp, f"Failed to power on {self.host_list[node]}.")
        # To get all the services up and running
        time.sleep(40)
        LOGGER.info(
            "Step 7: Verified %s is powered on and pinging.",
            self.host_list[node])
        csm_resp = self.ha_obj.get_csm_failover_node(
            srvnode_list=self.srvnode_list,
            node_list=self.node_list,
            sys_list=self.sys_list,
            node=node)
        assert_utils.assert_true(
            csm_resp[0], "Failed to get CSM failover node")
        resp = self.ha_obj.check_pcs_status_resp(
            node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.check_csr_health_status_rest("degraded")
        assert_utils.assert_true(resp[0], resp[1])
        check_rem_node = [
            "offline" if num == node else "online" for num in range(
                self.num_nodes)]
        resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 7: Verified PCS shows services stopped for %s and health status show offline",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 8: Start node from REST and check health status for %s show online",
            self.srvnode_list[node])
        resp = self.ha_rest.perform_cluster_operation(
            operation='start',
            resource='node',
            resource_id=node,
            login_as={"username": opt_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        if self.setup_type == "HW":
            LOGGER.debug(
                "HW: Need to enable stonith on the %s after powered on",
                self.host_list[node])
            resp = system_utils.run_remote_cmd(
                cmd=cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node + 1),
                hostname=self.host_list[node],
                username=self.username[node],
                password=self.password[node],
                read_lines=True)
            assert_utils.assert_true(
                resp[0], f"Failed to enable stonith on {self.host_list[node]}")
        LOGGER.info("Checking PCS clean")
        for hlt_obj in self.hlt_list:
            resp = hlt_obj.check_node_health()
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 8: Verified %s health status shows online and PCS is clean")
        LOGGER.info("Step 9: Check the IEM fault resolved for node up")
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["resolved"], True, "iem")
        assert_utils.assert_true(resp, "Failed to get alert in CSM")
        self.starttime = time.time()
        LOGGER.info("Step 9: Verified the IEM fault resolved for node up")
        LOGGER.info("Step 10: Check DI for IOs run.")
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Verified DI for IOs run.")
        self.restored = True
        LOGGER.info(
            "Completed: Test to Check Stop services on node from REST and unsafe shutdown")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-25444")
    @CTFailOn(error_handler)
    def test_node_poweroff_start_server(self):
        """
        Test to Check Poweroff node (only server) one by one and start it
        back through cortx REST with admin or manage user
        """
        LOGGER.info(
            "Started: Test to check poweroff (only server) start operation one by one all nodes.")
        for node in range(self.num_nodes):
            self.restored = False
            opt_user = self.system_random.choice(self.user_data)
            LOGGER.info(
                "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-25444')
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_data = resp[2]
            LOGGER.info("Step 1: IOs are started successfully.")
            LOGGER.info(
                "Step 2: Poweroff %s only server from cortx REST with %s user",
                self.srvnode_list[node],
                opt_user)
            resp = self.ha_rest.perform_cluster_operation(
                operation='poweroff',
                resource='node',
                resource_id=node,
                login_as={"username": opt_user, "password": self.csm_passwd})
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.check_ping(host=self.host_list[node])
            assert_utils.assert_false(
                resp, f"{self.host_list[node]} is still pinging")
            LOGGER.info("Step 2: %s server is poweroff and not pinging",
                        self.srvnode_list[node])
            LOGGER.info(
                "Step 3: Check health status for %s is offline and "
                "cluster/rack/site is degraded with REST",
                self.srvnode_list[node])
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])
            check_rem_node = [
                "offline" if num == node else "online" for num in range(
                    self.num_nodes)]
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 3: Verified status for %s show offline and cluster/rack/site as degraded",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 4: Check for the %s down alert",
                self.srvnode_list[node])
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["get"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            LOGGER.info(
                "Step 4: Verified the %s down alert",
                self.srvnode_list[node])
            LOGGER.info("Step 5: Check PCS status")
            csm_resp = self.ha_obj.get_csm_failover_node(
                srvnode_list=self.srvnode_list,
                node_list=self.node_list,
                sys_list=self.sys_list,
                node=node)
            assert_utils.assert_true(
                csm_resp[0], "Failed to get CSM failover node")
            resp = self.ha_obj.check_pcs_status_resp(
                node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: PCS shows services stopped for %s, services on other nodes shows started",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 6: Start %s from REST with %s user",
                self.srvnode_list[node],
                opt_user)
            resp = self.ha_rest.perform_cluster_operation(
                operation='start',
                resource='node',
                resource_id=node,
                login_as={"username": opt_user, "password": self.csm_passwd})
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 6: Started the %s from REST with %s user",
                self.srvnode_list[node],
                opt_user)
            LOGGER.info(
                "Step 7: Check health status for %s shows online with REST & PCS status clean",
                self.srvnode_list[node])
            resp = self.ha_rest.check_csr_health_status_rest("online")
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(
                ['online'] * self.num_nodes)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Checking PCS clean")
            for hlt_obj in self.hlt_list:
                resp = hlt_obj.check_node_health()
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 7: Verified %s health status shows online and PCS is clean",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 8: Check the IEM fault resolved alert for node up")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            self.starttime = time.time()
            LOGGER.info(
                "Step 8: Verified the IEM fault resolved alert for node up")
            LOGGER.info("Step 9: Check DI for IOs run.")
            resp = self.ha_obj.perform_ios_ops(
                di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 9: Verified DI for IOs run.")
            self.restored = True

        LOGGER.info(
            "Completed: Test to check poweroff (only server) start operation one by one all nodes.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-25217")
    @CTFailOn(error_handler)
    def test_node_poweroff_start_server_storage(self):
        """
        Test to Power off node one by one along with storage and start it back
        through cortx REST with admin/manage user.
        """
        LOGGER.info(
            "Started: Test to Power off node one by one along with storage and start it back "
            "through cortx REST with admin/manage user.")
        for node in range(self.num_nodes):
            self.restored = False
            opt_user = self.system_random.choice(self.user_data)
            LOGGER.info(
                "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-25217')
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_data = resp[2]
            LOGGER.info("Step 1: IOs are started successfully.")
            LOGGER.info(
                "Step 2: Poweroff %s server and storage from cortx REST with %s user",
                self.srvnode_list[node],
                opt_user)
            resp = self.ha_rest.perform_cluster_operation(
                operation='poweroff',
                resource='node',
                resource_id=node,
                storage_off=True,
                login_as={"username": opt_user, "password": self.csm_passwd})
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.check_ping(host=self.host_list[node])
            assert_utils.assert_false(
                resp, f"{self.host_list[node]} is still pinging")
            LOGGER.info("Step 2: %s server is poweroff and not pinging",
                        self.srvnode_list[node])
            LOGGER.info(
                "Step 3: Check health status for %s is offline and "
                "cluster/rack/site is degraded with REST",
                self.srvnode_list[node])
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])
            check_rem_node = [
                "offline" if num == node else "online" for num in range(
                    self.num_nodes)]
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 3: Verified status for %s show offline and cluster/rack/site as degraded",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 4: Check for the %s down alert",
                self.srvnode_list[node])
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["get"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            LOGGER.info(
                "Step 4: Verified the %s down alert",
                self.srvnode_list[node])
            LOGGER.info("Step 5: Check PCS status")
            csm_resp = self.ha_obj.get_csm_failover_node(
                srvnode_list=self.srvnode_list,
                node_list=self.node_list,
                sys_list=self.sys_list,
                node=node)
            assert_utils.assert_true(
                csm_resp[0], "Failed to get CSM failover node")
            resp = self.ha_obj.check_pcs_status_resp(
                node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: PCS shows services stopped for %s, services on other nodes shows started",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 6: Start storage for %s from PDU",
                self.srvnode_list[node])
            if node == self.node_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            resp_rpdu = nd_obj.toggle_apc_node_power(
                pdu_ip=self.rpdu_encl_ip[node],
                pdu_user=self.rpdu_encl_user[node],
                pdu_pwd=self.rpdu_encl_pwd[node],
                node_slot=self.rpdu_encl_port[node],
                status="on")
            assert_utils.assert_true(resp_rpdu)
            resp_lpdu = nd_obj.toggle_apc_node_power(
                pdu_ip=self.lpdu_encl_ip[node],
                pdu_user=self.lpdu_encl_user[node],
                pdu_pwd=self.lpdu_encl_pwd[node],
                node_slot=self.lpdu_encl_port[node],
                status="on")
            assert_utils.assert_true(resp_lpdu)
            # Need to check on exact time it should take to start enclosure
            time.sleep(120)
            LOGGER.info(
                "Step 6: Storage for %s from PDU started",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 7: Start %s from REST with %s user",
                self.srvnode_list[node],
                opt_user)
            resp = self.ha_rest.perform_cluster_operation(
                operation='start',
                resource='node',
                resource_id=node,
                login_as={"username": opt_user, "password": self.csm_passwd})
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 7: Started the %s from REST with %s user",
                self.srvnode_list[node],
                opt_user)
            LOGGER.info(
                "Step 8: Check that the node server %s can ping enclosure.",
                self.srvnode_list[node])
            resp_encl1 = system_utils.run_remote_cmd(
                cmd=cmds.CMD_PING.format("10.0.0.2"),
                hostname=self.host_list[node],
                username=self.username[node],
                password=self.password[node])
            assert_utils.assert_true(resp_encl1[0], resp_encl1[1])
            resp_encl2 = system_utils.run_remote_cmd(
                cmd=cmds.CMD_PING.format("10.0.0.3"),
                hostname=self.host_list[node],
                username=self.username[node],
                password=self.password[node])
            assert_utils.assert_true(resp_encl2[0], resp_encl2[1])
            LOGGER.info(
                "Step 8: Node server %s can ping enclosure.",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 9: Check health status for %s shows online with REST & PCS status clean",
                self.srvnode_list[node])
            resp = self.ha_rest.check_csr_health_status_rest("online")
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(
                ['online'] * self.num_nodes)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Checking PCS clean")
            for hlt_obj in self.hlt_list:
                resp = hlt_obj.check_node_health()
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 9: Verified %s health status shows online and PCS is clean",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 10: Check the IEM fault resolved alert for node up")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            self.starttime = time.time()
            LOGGER.info(
                "Step 10: Verified the IEM fault resolved alert for node up")
            LOGGER.info("Step 11: Check DI for IOs run.")
            resp = self.ha_obj.perform_ios_ops(
                di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 11: Verified DI for IOs run.")
            self.restored = True

        LOGGER.info(
            "Completed: Test to Power off node one by one along with storage and start it back "
            "through cortx REST with admin/manage user.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-25219")
    @CTFailOn(error_handler)
    def test_node_stop_start_moniter_user(self):
        """
        Test to Check Negative scenario: Stop services/start node operation
        not supported by monitor user using REST
        """
        LOGGER.info(
            "Started: Test to Check node Stop/Start operation not supported by monitor user.")
        node = self.system_random.choice(list(range(self.num_nodes)))
        opt_user = self.system_random.choice(self.user_data)
        self.restored = False
        LOGGER.info("Create user with monitor privileges.")
        self.monitor_user = f"monitor-user-{time.perf_counter_ns()}"
        email_id = f"{self.monitor_user}@seagate.com"
        resp = self.csm_obj.csm_user_create(
            self.monitor_user, email_id, self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-25219')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_data = resp[2]
        LOGGER.info("Step 1: IOs are started successfully.")
        LOGGER.info(
            "Step 2: Login to cortx REST with %s user and try to stop services on %s",
            self.monitor_user,
            self.srvnode_list[node])
        resp = self.ha_rest.perform_cluster_operation(
            operation='stop', resource='node', resource_id=node, login_as={
                "username": self.monitor_user, "password": self.csm_passwd})
        assert_utils.assert_false(
            resp[0], "Stop {self.srvnode_list[node]} failed with {resp[1]}")
        LOGGER.info(
            "Step 2: Verified stop services command by %s user failed with %s response",
            self.monitor_user,
            resp[1])
        LOGGER.info(
            "Step 3: Login to cortx REST with %s user and try to poweroff %s",
            self.monitor_user,
            self.srvnode_list[node])
        resp = self.ha_rest.perform_cluster_operation(
            operation='poweroff', resource='node', resource_id=node, login_as={
                "username": self.monitor_user, "password": self.csm_passwd})
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info(
            "Step 3: Verified poweroff node command by %s user failed with %s response",
            self.monitor_user,
            resp[1])
        LOGGER.info(
            "Step 4: Login to cortx REST with %s user and try to stop services on %s",
            opt_user,
            self.srvnode_list[node])
        resp = self.ha_rest.perform_cluster_operation(
            operation='stop',
            resource='node',
            resource_id=node,
            login_as={"username": opt_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.check_ping(host=self.host_list[node])
        assert_utils.assert_true(
            resp, f"{self.host_list[node]} is failed to ping")
        resp = self.ha_rest.check_csr_health_status_rest("degraded")
        assert_utils.assert_true(resp[0], resp[1])
        check_rem_node = [
            "offline" if num == node else "online" for num in range(
                self.num_nodes)]
        resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        csm_resp = self.ha_obj.get_csm_failover_node(
            srvnode_list=self.srvnode_list,
            node_list=self.node_list,
            sys_list=self.sys_list,
            node=node)
        assert_utils.assert_true(
            csm_resp[0], "Failed to get CSM failover node")
        resp = self.ha_obj.check_pcs_status_resp(
            node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: PCS services stopped for %s, health status is offline but still pinging",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 5: Login to cortx REST with %s user and try to start the offline %s",
            self.monitor_user,
            self.srvnode_list[node])
        resp = self.ha_rest.perform_cluster_operation(
            operation='start', resource='node', resource_id=node, login_as={
                "username": self.monitor_user, "password": self.csm_passwd})
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info(
            "Step 5: Verified start node command by %s user failed with %s response",
            self.monitor_user,
            resp[1])
        resp = self.csm_obj.csm_user_delete(user_name=self.monitor_user)
        assert_utils.assert_true(resp[0], resp[1])
        self.monitor_user = None
        LOGGER.info(
            "Step 6: Login to cortx REST with %s user and start the offline %s",
            opt_user,
            self.srvnode_list[node])
        resp = self.ha_rest.perform_cluster_operation(
            operation='start',
            resource='node',
            resource_id=node,
            login_as={"username": opt_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        for hlt_obj in self.hlt_list:
            resp = hlt_obj.check_node_health()
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 6: Verified all the services on %s started and health status is online",
            self.srvnode_list[node])
        LOGGER.info("Step 7: Check DI for IOs run")
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.restored = True
        LOGGER.info("Step 7: Verified DI for IOs run.")
        LOGGER.info(
            "Completed: Test to Check node Stop/Start operation not supported by monitor user.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-25222")
    @CTFailOn(error_handler)
    def test_node_poweroff_external_power_on(self):
        """
        This test tests that node can be powered off along with storage from REST and
        started back from BMC/ssc-cloud/PDU and node comes back online with admin/manage user.
        """
        LOGGER.info(
            "Started: Node can be powered off along with storage from REST and "
            "started back from BMC/ssc-cloud/PDU and node comes "
            "back online with admin/manage user.")
        node = self.system_random.choice(list(range(self.num_nodes)))
        self.restored = False
        opt_user = self.system_random.choice(self.user_data)
        LOGGER.info(
            "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-25222')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_data = resp[2]
        LOGGER.info("Step 1: IOs are started successfully.")
        LOGGER.info(
            "Step 2: Poweroff %s server and storage from cortx REST with %s user",
            self.srvnode_list[node],
            opt_user)
        resp = self.ha_rest.perform_cluster_operation(
            operation='poweroff',
            resource='node',
            resource_id=node,
            storage_off=True,
            login_as={"username": opt_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.check_ping(host=self.host_list[node])
        assert_utils.assert_false(
            resp, f"{self.host_list[node]} is still pinging")
        LOGGER.info("Step 2: %s server is poweroff and not pinging",
                    self.srvnode_list[node])
        LOGGER.info(
            "Step 3: Check health status for %s is offline and "
            "cluster/rack/site is degraded with REST",
            self.srvnode_list[node])
        resp = self.ha_rest.check_csr_health_status_rest("degraded")
        assert_utils.assert_true(resp[0], resp[1])
        check_rem_node = [
            "offline" if num == node else "online" for num in range(
                self.num_nodes)]
        resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 3: Verified status for %s show offline and cluster/rack/site as degraded",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 4: Check for the %s down alert",
            self.srvnode_list[node])
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["get"], False, "iem")
        assert_utils.assert_true(resp, "Failed to get alert in CSM")
        LOGGER.info(
            "Step 4: Verified the %s down alert",
            self.srvnode_list[node])
        LOGGER.info("Step 5: Check PCS status")
        csm_resp = self.ha_obj.get_csm_failover_node(
            srvnode_list=self.srvnode_list,
            node_list=self.node_list,
            sys_list=self.sys_list,
            node=node)
        assert_utils.assert_true(
            csm_resp[0], "Failed to get CSM failover node")
        resp = self.ha_obj.check_pcs_status_resp(
            node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 5: PCS shows services stopped for %s, services on other nodes shows started",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 6: Start storage for %s from PDU", self.srvnode_list[node])
        if node == self.node_list[-1]:
            nd_obj = self.node_list[0]
        else:
            nd_obj = self.node_list[node + 1]
        resp_rpdu = nd_obj.toggle_apc_node_power(
            pdu_ip=self.rpdu_encl_ip[node],
            pdu_user=self.rpdu_encl_user[node],
            pdu_pwd=self.rpdu_encl_pwd[node],
            node_slot=self.rpdu_encl_port[node],
            status="on")
        assert_utils.assert_true(resp_rpdu)
        resp_lpdu = nd_obj.toggle_apc_node_power(
            pdu_ip=self.lpdu_encl_ip[node],
            pdu_user=self.lpdu_encl_user[node],
            pdu_pwd=self.lpdu_encl_pwd[node],
            node_slot=self.lpdu_encl_port[node],
            status="on")
        assert_utils.assert_true(resp_lpdu)
        # Need to check on exact time it should take to start enclosure
        time.sleep(120)
        LOGGER.info(
            "Step 6: Storage for %s from PDU started", self.srvnode_list[node])
        LOGGER.info(
            "Step 7: Start the %s node server from BMC.",
            self.srvnode_list[node])
        resp = self.ha_obj.host_power_on(
            host=self.host_list[node],
            bmc_obj=self.bmc_list[node])
        assert_utils.assert_true(
            resp, f"Failed to power on {self.host_list[node]}.")
        LOGGER.info(
            "Step 7: Node server from BMC is started.")
        LOGGER.info(
            "Step 8: Check PCS status and make sure powering on server "
            "doesn't start services")
        csm_resp = self.ha_obj.get_csm_failover_node(
            srvnode_list=self.srvnode_list,
            node_list=self.node_list,
            sys_list=self.sys_list,
            node=node)
        assert_utils.assert_true(
            csm_resp[0], "Failed to get CSM failover node")
        resp = self.ha_obj.check_pcs_status_resp(
            node, csm_resp[2], self.hlt_list, csm_node=self.node_list.index(csm_resp[2]))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 8: PCS shows services stopped for %s, services on other nodes shows started",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 9: Start %s from REST with %s user",
            self.srvnode_list[node],
            opt_user)
        resp = self.ha_rest.perform_cluster_operation(
            operation='start',
            resource='node',
            resource_id=node,
            login_as={"username": opt_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 9: Started the %s from REST with %s user",
            self.srvnode_list[node],
            opt_user)
        LOGGER.info(
            "Step 10: Check that the node server %s can ping enclosure.",
            self.srvnode_list[node])
        resp_encl1 = system_utils.run_remote_cmd(
            cmd=cmds.CMD_PING.format("10.0.0.2"),
            hostname=self.host_list[node],
            username=self.username[node],
            password=self.password[node])
        assert_utils.assert_true(resp_encl1[0], resp_encl1[1])
        resp_encl2 = system_utils.run_remote_cmd(
            cmd=cmds.CMD_PING.format("10.0.0.3"),
            hostname=self.host_list[node],
            username=self.username[node],
            password=self.password[node])
        assert_utils.assert_true(resp_encl2[0], resp_encl2[1])
        LOGGER.info(
            "Step 10: Node server %s can ping enclosure.",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 11: Check health status for %s shows online with REST & PCS status clean",
            self.srvnode_list[node])
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Checking PCS clean")
        for hlt_obj in self.hlt_list:
            resp = hlt_obj.check_node_health()
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 11: Verified %s health status shows online and PCS is clean",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 12: Check the IEM fault resolved alert for node up")
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["resolved"], True, "iem")
        assert_utils.assert_true(resp, "Failed to get alert in CSM")
        self.starttime = time.time()
        LOGGER.info(
            "Step 12: Verified the IEM fault resolved alert for node up")
        LOGGER.info("Step 13: Check DI for IOs run.")
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 13: Verified DI for IOs run.")
        self.restored = True

        LOGGER.info(
            "Completed: Node can be powered off along with storage from REST and "
            "started back from BMC/ssc-cloud/PDU and node comes "
            "back online with admin/manage user.")
