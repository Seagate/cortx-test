#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
HA test suite for Node failure: Fault tolerance (READ/WRITE/DELETE) testing.
"""

import logging
import time
from random import SystemRandom

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import RAS_TEST_CFG
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs import HALibs

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
class TestHANodeFailure:
    """
    Test suite for Node failure: Fault tolerance (READ/WRITE/DELETE) testing.
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
        cls.system_random = SystemRandom()
        cls.mgnt_ops = ManagementOPs()
        cls.node_list = []
        cls.host_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.username = []
        cls.password = []
        cls.restored = True
        cls.starttime = cls.s3user_info = cls.iss3cleanup = None

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.username[node],
                                      password=cls.password[node]))
            cls.hlt_list.append(Health(hostname=cls.host,
                                       username=cls.username[node],
                                       password=cls.password[node]))
        LOGGER.info("COMPLETED: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.starttime = time.time()
        self.s3user_info = None
        self.iss3cleanup = None
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
        LOGGER.info("COMPLETED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if not self.restored:
            for node in range(self.num_nodes):
                # Check if node needs to be start.
                resp = self.ha_rest.verify_node_health_status_rest(
                    exp_status=['online'], node_id=node, single_node=True)
                if not resp[0]:
                    LOGGER.info(
                        "Cleanup: Start %s.", self.srvnode_list[node])
                    resp = self.ha_rest.perform_cluster_operation(
                        operation='start', resource='node', resource_id=node, login_as={
                            "username": self.csm_user, "password": self.csm_passwd})
                    assert_utils.assert_true(resp[0], resp[1])
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Cleanup: All nodes are online and PCS looks clean.")
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Cleanup: Health status shows all components as online in cortx REST.")
        # Check if s3 buckets deletion is required
        if self.iss3cleanup:
            for user_info in self.s3user_info.values():
                resp = self.ha_obj.ha_s3_workload_operation(
                    s3userinfo=user_info, log_prefix=self.iss3cleanup,
                    skipwrite=True, skipread=True)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Cleanup: Deleted s3 objects and buckets.")
        # Check if s3 user deletion is required
        if self.s3user_info:
            resp = self.ha_obj.delete_s3_acc_buckets_objects(
                self.s3user_info)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Cleanup: Deleted s3 user accounts.")
        # TODO: Need to add steps to reset data once node is back up
        LOGGER.info("COMPLETED: Teardown Operations.")

    # pylint: disable-msg=too-many-statements
    @pytest.mark.ha
    @pytest.mark.tags("TEST-26435")
    @CTFailOn(error_handler)
    def test_node_down_degraded_reads(self):
        """
        Test to Verify degraded READs after node down - node poweroff (server only)
        """
        LOGGER.info(
            "Started: Test to check degraded READs after node down - node poweroff.")
        node = self.system_random.choice(list(range(self.num_nodes)))
        self.restored = False

        LOGGER.info(
            "Step 1: Perform WRITEs with variable object sizes: 0B + (1KB - 5GB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.iss3cleanup = 'test_26435'
        resp = self.ha_obj.ha_s3_workload_operation(
            s3userinfo=list(users.values())[0],
            log_prefix=self.iss3cleanup,
            skipread=True,
            skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3user_info = users
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")
        LOGGER.info("Step 2: Poweroff %s from cluster with CORTX REST with %s user",
            self.srvnode_list[node],
            self.csm_user)
        resp = self.ha_rest.perform_cluster_operation(
            operation='poweroff',
            resource='node',
            resource_id=node,
            login_as={"username": self.csm_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.check_ping(host=self.host_list[node])
        assert_utils.assert_false(
            resp, f"{self.host_list[node]} is still pinging")
        LOGGER.info("Step 2: %s server is poweroff and not pinging",
                    self.srvnode_list[node])
        LOGGER.info("Step 3: Check for the %s down alert",
            self.srvnode_list[node])
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["get"], False, "iem")
        assert_utils.assert_true(resp, "Failed to get alert in CSM")
        LOGGER.info("Step 3: Verified the %s down alert",
                    self.srvnode_list[node])
        LOGGER.info(
            "Step 4: Check health status for %s is offline and "
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
            "Step 4: Verified status for %s show offline and cluster/rack/site as degraded",
            self.srvnode_list[node])
        LOGGER.info("Step 5: Check PCS status")
        resp = self.ha_obj.check_pcs_status_resp(
            node, self.node_list, self.hlt_list)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 5: PCS shows services stopped for %s, services on other nodes shows started",
            self.srvnode_list[node])
        LOGGER.info("Step 6: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(
            users.values())[0], log_prefix=self.iss3cleanup, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed READs and verified DI on the written data")
        LOGGER.info("Step 7: Start %s from REST with %s user",
            self.srvnode_list[node],
            self.csm_user)
        resp = self.ha_rest.perform_cluster_operation(
            operation='start',
            resource='node',
            resource_id=node,
            login_as={"username": self.csm_user, "password": self.csm_passwd})
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Started the %s from REST with %s user",
                    self.srvnode_list[node],
                    self.csm_user)
        LOGGER.info(
            "Step 8: Check health status for %s shows online with REST & PCS status clean",
            self.srvnode_list[node])
        resp = self.ha_rest.check_csr_health_status_rest("online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(
            ['online'] * self.num_nodes)
        assert_utils.assert_true(resp[0], resp[1])
        # To get all the services up and running
        time.sleep(40)
        for hlt_obj in self.hlt_list:
            resp = hlt_obj.check_node_health()
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 8: Verified %s health status shows online and PCS is clean",
            self.srvnode_list[node])
        LOGGER.info(
            "Step 9: Check the IEM fault resolved alert for node up")
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["resolved"], True, "iem")
        assert_utils.assert_true(resp, "Failed to get alert in CSM")
        self.starttime = time.time()
        LOGGER.info(
            "Step 9: Verified the IEM fault resolved alert for node up")
        LOGGER.info("Step 10: Delete all the test objects, buckets and s3 user")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(
            users.values())[0], log_prefix=self.iss3cleanup, skipwrite=True, skipread=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.iss3cleanup = None
        resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3user_info)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3user_info = None
        LOGGER.info("Step 10: Deleted all the test objects, buckets and s3 user")
        self.restored = True
        LOGGER.info(
            "Completed: Test to check degraded READs after node down - node poweroff.")
