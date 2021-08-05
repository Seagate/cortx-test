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
HA test suite for node start stop operations.
"""

import logging
from random import SystemRandom
import time
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, HA_CFG, RAS_TEST_CFG
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ha.ha_common_libs import HALibs
from libs.s3.cortxcli_test_lib import CSMAccountOperations
from libs.csm.rest.csm_rest_system_health import SystemHealth


# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
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

        cls.node_list = []
        cls.host_list = []
        cls.sys_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.hostname = []
        cls.restored = True
        cls.starttime = None
        cls.csm_failover = cls.user_data = cls.manage_user = cls.email_id = cls.s3_data = None

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.hostname.append(cls.host)
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.uname, password=cls.passwd))
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname,
                                       password=cls.passwd))
            cls.sys_list.append(CortxCliSystemtOperations(
                host=cls.host, username=cls.uname, password=cls.passwd))

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.starttime = time.time()
        self.csm_failover = None
        self.s3_data = None
        self.user_data = None
        self.manage_user = None
        LOGGER.info(
            "Precondition: Check PCS is up and running without any failures.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info(
            "Precondition: Check Health status shows all components as online in cortx CLI/REST.")
        self.ha_obj.status_nodes_online(
            node_obj=self.node_list[0],
            srvnode_list=self.srvnode_list,
            sys_list=self.sys_list,
            no_nodes=self.num_nodes)
        LOGGER.info(
            "Precondition: Health status shows all components as online & PCS looks clean.")

        LOGGER.info("Precondition: Create csm user having manage privileges.")
        self.manage_user = "csm-user-{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.manage_user)
        resp = self.csm_obj.csm_user_create(
            self.manage_user, self.email_id, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Created csm user having manage privileges.")
        self.user_data = [self.csm_user, self.manage_user]
        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        LOGGER.info("Cleanup: Delete CSM manage user.")
        resp = self.csm_obj.csm_user_delete(user_name=self.manage_user)
        assert_utils.assert_true(resp[0], resp[1])
        if not self.restored:
            for node in range(self.num_nodes):
                resp = self.ha_rest.verify_node_health_status_rest(
                    exp_status=['online'], node_id=node, single_node=True)
                if not resp[0]:
                    LOGGER.info(
                        "Cleanup: Start %s.", self.srvnode_list[node])
                    resp = self.ha_obj.perform_node_operation(
                        sys_obj=self.csm_failover, operation='start',
                        resource_id=node, user=self.user_data[0], pswd=self.csm_passwd)
                    assert_utils.assert_true(resp[0], resp[1])
            if self.s3_data:
                LOGGER.info("Cleanup: Delete s3 accounts and buckets.")
                self.ha_obj.delete_s3_acc_buckets_objects(self.s3_data)
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Cleanup: All nodes are online and PCS looks clean.")
        LOGGER.info("ENDED: Teardown Operations.")

    # pylint: disable=R0915
    @pytest.mark.ha
    @pytest.mark.tags("TEST-22486")
    @CTFailOn(error_handler)
    def test_node_stop_start_one_by_one(self):
        """
        Test to Check Stop services on node one by one and start it back,
        through cortx CLI with admin or manage user
        """
        LOGGER.info(
            "Started: Test to check stop start operation one by one for all nodes.")
        for node in range(self.num_nodes):
            self.restored = False
            opt_user = self.system_random.choice(self.user_data)
            LOGGER.info(
                "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-22486')
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_data = resp[2]
            LOGGER.info("Step 1: IOs are started successfully.")
            LOGGER.info("Step 2: Stop %s from cortx CLI with %s user",
                        self.srvnode_list[node], opt_user)
            resp = self.ha_obj.check_csm_service(
                self.node_list[0], self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            resp = self.ha_obj.perform_node_operation(
                sys_obj=sys_obj,
                operation='stop',
                resource_id=node,
                user=opt_user,
                pswd=self.csm_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.check_ping(host=self.host_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} is failed to ping")
            LOGGER.info("Step 2: %s is stopped and still is pinging",
                        self.srvnode_list[node])
            LOGGER.info(
                "Step 3: Check health status for %s is offline and "
                "cluster/rack/site is degraded with CLI/REST",
                self.srvnode_list[node])
            resp = self.ha_obj.get_csm_failover_node(
                srvnode_list=self.srvnode_list,
                node_list=self.node_list,
                sys_list=self.sys_list,
                node=node)
            assert_utils.assert_true(resp[0], resp[1])
            self.csm_failover = sys_obj = resp[1]
            nd_obj = resp[2]
            resp = self.ha_obj.check_csrn_status(
                sys_obj=sys_obj,
                csr_sts="degraded",
                node_sts="offline",
                node_id=node)
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
            # TODO: If CSM REST getting changed, add alert check from msg bus
            LOGGER.info("Step 5: Check PCS status")
            resp = self.ha_obj.check_pcs_status_resp(
                node, self.node_list, self.hlt_list)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 5: PCS shows services stopped for %s, services on other nodes shows started",
                self.srvnode_list[node])
            LOGGER.info(
                "Step 6: Start %s from CLI with %s user",
                self.srvnode_list[node],
                opt_user)
            resp = self.ha_obj.perform_node_operation(
                sys_obj=sys_obj,
                operation='start',
                resource_id=node,
                user=opt_user,
                pswd=self.csm_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Step 6: Started the %s from CLI with %s user",
                self.srvnode_list[node],
                opt_user)
            LOGGER.info(
                "Step 7: Check health status for %s shows online with CLI/REST & PCS status clean",
                self.srvnode_list[node])
            self.ha_obj.status_cluster_resource_online(
                self.srvnode_list, self.sys_list, nd_obj)
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
            # TODO: If CSM REST getting changed, add alert check from msg bus
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
