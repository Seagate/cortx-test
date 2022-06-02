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
Prov test file for all the post deploy validations for single node and multinode VMs.
"""

import logging
import secrets

import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons.utils import assert_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, PROV_CFG
from libs.prov.provisioner import Provisioner
from libs.csm.cli.cli_csm_user import CortxCliCsmUser

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestPostDeploySingleNode:
    """
    Test suite for post deploy scenarios for single node VM.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.hlt_obj = Health(hostname=cls.host, username=cls.uname,
                             password=cls.passwd)
        cls.prov_obj = Provisioner()
        cls.set_ntp = None
        cls.restored = True
        cls.csm_user = CortxCliCsmUser()
        cls.csm_user.open_connection()
        cls.ntp_keys = PROV_CFG['system_ntp']['ntp_data']
        LOGGER.info("Done: Setup module operations")

    def teardown_method(self):
        """
        Teardown operations after each test.
        """
        if not self.restored:
            LOGGER.info("TEARDOWN: Restore NTP configuration data.")
            resp = self.prov_obj.set_ntpsysconfg(self.nd_obj,
                                                 time_server=self.set_ntp[self.ntp_keys[0]],
                                                 timezone=self.set_ntp[self.ntp_keys[1]])
            assert_utils.assert_true(resp[0], resp[1])

            resp = self.prov_obj.sysconfg_verification(
                self.ntp_keys, self.nd_obj, node_id=1,
                exp_t_srv=self.set_ntp[self.ntp_keys[0]], exp_t_zone=self.set_ntp[self.ntp_keys[1]])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("TEARDOWN: Restored NTP configuration data: %s.", resp[1])
        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22639")
    @CTFailOn(error_handler)
    def test_verify_services_ports_single_node_vm(self):
        """
        Prov test to verify services running on respective nodes
        """
        LOGGER.info("Check that all cortx services are up")
        resp = self.nd_obj.execute_cmd(
            cmd=common_cmds.CMD_PCS_STATUS_FULL, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                PROV_CFG["system"]["stopped"],
                line,
                "Some services are not up")
        LOGGER.info(
            "Verifying third party services running on node %s",
            self.nd_obj.hostname)
        resp = self.nd_obj.send_systemctl_cmd(
            command="is-active",
            services=PROV_CFG["services"]["all"],
            decode=True,
            exc=False)
        assert_utils.assert_equal(
            resp.count(
                PROV_CFG["system"]["active"]), len(
                PROV_CFG["services"]["all"]))
        LOGGER.info("Checking all services are running on respective ports")
        resp = self.prov_obj.verify_services_ports(
            self.hlt_obj, PROV_CFG["service_ports"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Verified all the services running on node %s",
            self.nd_obj.hostname)

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22858")
    @CTFailOn(error_handler)
    def test_confstore_validate_single_node(self):
        """
        Test is for confstore keys validation on successful deployment from confstore template
        as well as provisioner pillar commands.
        """
        LOGGER.info("Started: confstore keys validation.")
        LOGGER.info("Check that the cluster is up and running.")
        res = self.hlt_obj.check_node_health()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Node is accessible and PCS is up and running.")

        node_id = 1
        for key in PROV_CFG["confstore_list"]:
            LOGGER.info(
                "Verification of %s from pillar as well as confstore template.", key)
            output = self.prov_obj.confstore_verification(
                key, self.nd_obj, node_id)
            assert_utils.assert_true(output[0], output[1])

        LOGGER.info("Completed: confstore keys validation.")

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22965")
    @CTFailOn(error_handler)
    def test_ntpconfg_validate_single_node(self):
        """
        Test validates NTP Configuration on successful single node deployment
        and NTP configuration can be changed from provisioner cli.
        """
        LOGGER.info("-----     Started NTP configuration Validation     -----")
        self.restored = False
        LOGGER.info("Store NTP configuration data.")
        resp = self.prov_obj.get_ntpsysconfg(self.ntp_keys, self.nd_obj, 1)
        assert_utils.assert_true(resp[0], resp[1])
        self.set_ntp = resp[1]
        LOGGER.info("Stored NTP configuration data = %s.", self.set_ntp)

        timeserver_data = PROV_CFG['system_ntp']['timeserver']
        timezone_data = PROV_CFG['system_ntp']['timezone']
        LOGGER.info("Step 1: Check that the cluster is up and running.")
        res = self.hlt_obj.check_node_health()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Step 1: Node is accessible and PCS is up and running.")

        LOGGER.info("Step 2: Validate that admin user is created")
        resp = self.csm_user.login_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_user.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Validated that admin user is created")

        LOGGER.info("Get NTP configuration data.")
        get_ntp_resp = self.prov_obj.get_ntpsysconfg(
            self.ntp_keys, self.nd_obj, 1)
        assert_utils.assert_true(get_ntp_resp[0], get_ntp_resp[1])
        LOGGER.info("NTP configuration data = %s.", get_ntp_resp[1])

        ntp_time_server_val = get_ntp_resp[1][self.ntp_keys[0]]
        ntp_time_zone_val = get_ntp_resp[1][self.ntp_keys[1]]
        LOGGER.info("Step 3: Validate time_server is set to %s in /etc/chrony.conf",
                    ntp_time_server_val)
        resp = self.prov_obj.get_chrony(
            node_obj=self.nd_obj,
            time_server=ntp_time_server_val)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Validated time_server in /etc/chrony.conf response = %s", resp[1])

        set_timezone = (secrets.choice(
            [ii for ii in timezone_data if ii != ntp_time_zone_val]))
        set_timesrv_ip = (secrets.choice(
            [ii for ii in timeserver_data if ii != ntp_time_server_val]))
        LOGGER.info("Step 4: Set time_server %s and timezone %s", set_timesrv_ip,
                    set_timezone)
        resp = self.prov_obj.set_ntpsysconfg(
            self.nd_obj, time_server=set_timesrv_ip, timezone=set_timezone)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 5: Validate set NTP configuration in pillar data")
        resp = self.prov_obj.sysconfg_verification(
            self.ntp_keys, self.nd_obj, node_id=1,
            exp_t_srv=set_timesrv_ip, exp_t_zone=set_timezone)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Validated set NTP configuration in pillar data %s.", resp[1])

        LOGGER.info("Step 6: Validate set time_server in /etc/chrony.conf")
        resp = self.prov_obj.get_chrony(
            node_obj=self.nd_obj, time_server=set_timesrv_ip)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Validated set time_server in /etc/chrony.conf response = %s", resp[1])
        LOGGER.info(
            "Step 7: Restore and Validate NTP configuration data to %s", self.set_ntp)
        resp = self.prov_obj.set_ntpsysconfg(
            self.nd_obj, time_server=self.set_ntp[self.ntp_keys[0]],
            timezone=self.set_ntp[self.ntp_keys[1]])
        assert_utils.assert_true(resp[0], resp[1])

        resp = self.prov_obj.sysconfg_verification(
            self.ntp_keys, self.nd_obj, node_id=1, exp_t_srv=self.set_ntp[self.ntp_keys[0]],
            exp_t_zone=self.set_ntp[self.ntp_keys[1]])
        LOGGER.info(
            "Step 7: Validated Restored NTP configuration on srvnode-1: %s", resp[1])
        self.restored = True
        LOGGER.info(
            "-----     Completed NTP configuration Validation     -----")


class TestPostDeployMultiNode:
    """
    Test suite for post deploy scenarios for multinode VM.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.setup_type = CMN_CFG["setup_type"]
        cls.node_obj_list = list()
        cls.hlt_obj_list = list()
        for node in CMN_CFG["nodes"]:
            nd_obj = Node(hostname=node["hostname"], username=node["username"],
                           password=node["password"])
            cls.node_obj_list.append(nd_obj)
            hlt_obj = Health(hostname=node["hostname"], username=node["username"],
                              password=node["password"])
            cls.hlt_obj_list.append(hlt_obj)

        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.prov_obj = Provisioner()
        cls.ntp_keys = PROV_CFG['system_ntp']['ntp_data']
        cls.ntp_data = {}
        cls.restored = True
        cls.no_nodes = len(CMN_CFG["nodes"])
        LOGGER.info("Done: Setup module operations")

    def teardown_method(self):
        """
        Teardown operations after each test.
        """
        if not self.restored:
            LOGGER.info("TEARDOWN: Restore NTP configuration data.")
            for node in range(1, self.no_nodes+1):
                resp = self.prov_obj.set_ntpsysconfg(
                    node_obj=self.node_obj_list[0],
                    time_server=self.ntp_data[f"srvnode-{node}"][self.ntp_keys[0]],
                    timezone=self.ntp_data[f"srvnode-{node}"][self.ntp_keys[1]])
                assert_utils.assert_true(resp[0], resp[1])

                resp = self.prov_obj.sysconfg_verification(
                    self.ntp_keys, node_obj=self.node_obj_list[0], node_id=node,
                    exp_t_srv=self.ntp_data[f"srvnode-{node}"][self.ntp_keys[0]],
                    exp_t_zone=self.ntp_data[f"srvnode-{node}"][self.ntp_keys[1]])
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info("TEARDOWN: Restored NTP Configuration on srvnode-%s:%s", node, resp[1])
            LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_management_ops
    @pytest.mark.multinode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-21919")
    @CTFailOn(error_handler)
    def test_verify_services_multi_node_vm(self):
        """
        Prov test for verification of all services on deployed system
        """
        LOGGER.info("Check that all cortx services are up")
        resp = self.node_obj_list[0].execute_cmd(
            cmd=common_cmds.CMD_PCS_STATUS_FULL, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                PROV_CFG["system"]["stopped"],
                line,
                "Some services are not up")

        LOGGER.info("Check that all third party services are up")
        for node in self.node_obj_list:
            LOGGER.info(
                "Verifying third party services running on node %s",
                node.hostname)
            resp = node.send_systemctl_cmd(
                command="is-active",
                services=PROV_CFG["services"]["all"],
                decode=True,
                exc=False)
            assert_utils.assert_equal(
                resp.count(
                    PROV_CFG["system"]["active"]), len(
                    PROV_CFG["services"]["all"]))
            resp = node.send_systemctl_cmd(
                command="is-active",
                services=PROV_CFG["services"]["multinode"],
                decode=True,
                exc=False)
            assert_utils.assert_equal(
                resp.count(
                    PROV_CFG["system"]["active"]), len(
                    PROV_CFG["services"]["multinode"]))
            if self.setup_type == "HW":
                resp = node.send_systemctl_cmd(
                    command="is-active",
                    services=PROV_CFG["services"]["hw_specific"],
                    decode=True,
                    exc=False)
                assert_utils.assert_equal(
                    resp.count(
                        PROV_CFG["system"]["active"]), len(
                        PROV_CFG["services"]["hw_specific"]))

        for node in self.hlt_obj_list:
            LOGGER.info(
                "Checking all services are running on respective ports")
            resp = self.prov_obj.verify_services_ports(
                node, PROV_CFG["service_ports"])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Verified all the services running on node %s",
                node.hostname)

    @pytest.mark.cluster_management_ops
    @pytest.mark.multinode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-21717")
    @CTFailOn(error_handler)
    def test_confstore_validate_multi_node(self):
        """
        Test is for confstore keys validation on successful deployment from confstore template
        as well as provisioner pillar commands.
        """
        LOGGER.info("Started: confstore keys validation.")
        LOGGER.info("Check that the cluster is up and running.")
        for hlt_obj in self.hlt_obj_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are accessible and PCS looks clean.")

        for node_id in range(1, self.no_nodes+1):
            for key in PROV_CFG["confstore_list"]:
                LOGGER.info("Verification of %s from pillar as well as confstore template.", key)
                output = self.prov_obj.confstore_verification(
                    key, self.node_obj_list[0], node_id)
                assert_utils.assert_true(output[0], output[1])

        LOGGER.info("Completed: confstore keys validation.")

    # pylint: disable=too-many-statements
    @pytest.mark.cluster_management_ops
    @pytest.mark.multinode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-21736")
    @CTFailOn(error_handler)
    def test_ntpconfg_validate_multi_node(self):
        """
        Test validates NTP Configuration on successful deployment and
        NTP configuration can be changed from provisioner cli.
        """
        LOGGER.info("-----     Started NTP configuration Validation     -----")
        self.restored = False
        for node in range(1, self.no_nodes+1):
            LOGGER.info("Store NTP configuration data for srvnode-{%s}.", node)
            resp = self.prov_obj.get_ntpsysconfg(
                self.ntp_keys, self.node_obj_list[0], node)
            assert_utils.assert_true(resp[0], resp[1])
            self.ntp_data[f"srvnode-{node}"] = resp[1]
            LOGGER.info("Stored NTP configuration data for srvnode-%s = %s.", node,
                        self.ntp_data[f"srvnode-{node}"])

        LOGGER.info("Step 1: Check that the cluster is up and running.")
        timeserver_data = PROV_CFG['system_ntp']['timeserver']
        timezone_data = PROV_CFG['system_ntp']['timezone']
        for hlt_obj in self.hlt_obj_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are accessible and PCS looks clean.")

        LOGGER.info("Step 2: Validate that admin user is created")
        csm_user = CortxCliCsmUser()
        csm_user.open_connection()
        resp = csm_user.login_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = csm_user.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Validated that admin user is created")

        LOGGER.info(
            "Step 3: Validate that NTP Configuration is same on all applicable nodes")
        for node in range(1, self.no_nodes+1):
            resp = self.prov_obj.sysconfg_verification(
                self.ntp_keys, node_obj=self.node_obj_list[0], node_id=node,
                exp_t_srv=self.ntp_data["srvnode-1"][self.ntp_keys[0]],
                exp_t_zone=self.ntp_data["srvnode-1"][self.ntp_keys[1]])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: Validated NTP Configuration on srvnode-%s:%s", node, resp[1])

        ntp_time_server_val = self.ntp_data["srvnode-1"][self.ntp_keys[0]]
        ntp_time_zone_val = self.ntp_data["srvnode-1"][self.ntp_keys[1]]
        LOGGER.info("Step 4: Validate time_server is set to %s in /etc/chrony.conf",
                    ntp_time_server_val)
        resp = self.prov_obj.get_chrony(
            node_obj=self.node_obj_list[0],
            time_server=ntp_time_server_val)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Validated time_server in /etc/chrony.conf response = %s", resp[1])

        set_timezone = (secrets.choice(
            [ii for ii in timezone_data if ii != ntp_time_zone_val]))
        set_timesrv_ip = (secrets.choice(
            [ii for ii in timeserver_data if ii != ntp_time_server_val]))
        LOGGER.info("Step 5: Set time_server %s and timezone %s", set_timesrv_ip, set_timezone)
        for node in range(1, self.no_nodes+1):
            resp = self.prov_obj.set_ntpsysconfg(
                node_obj=self.node_obj_list[0],
                time_server=set_timesrv_ip,
                timezone=set_timezone)
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 6: Validate set NTP configuration in pillar data")
        for node in range(1, self.no_nodes+1):
            resp = self.prov_obj.sysconfg_verification(
                self.ntp_keys, node_obj=self.node_obj_list[0], node_id=node,
                exp_t_srv=set_timesrv_ip, exp_t_zone=set_timezone)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Validated set NTP Configuration on srvnode-%s:%s", node, resp[1])

        LOGGER.info("Step 7: Validate set time_server in /etc/chrony.conf")
        resp = self.prov_obj.get_chrony(
            node_obj=self.node_obj_list[0],
            time_server=set_timesrv_ip)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Validated set time_server in /etc/chrony.conf response = %s", resp[1])

        LOGGER.info("Step 8: Restore NTP configuration data.")
        for node in range(1, self.no_nodes+1):
            resp = self.prov_obj.set_ntpsysconfg(node_obj=self.node_obj_list[0],
                                                 time_server=self.ntp_data[f"srvnode-{node}"]
                                                 [self.ntp_keys[0]],
                                                 timezone=self.ntp_data[f"srvnode-{node}"]
                                                 [self.ntp_keys[1]])
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.prov_obj.sysconfg_verification(
                self.ntp_keys, node_obj=self.node_obj_list[0], node_id=node,
                exp_t_srv=self.ntp_data[f"srvnode-{node}"][self.ntp_keys[0]],
                exp_t_zone=self.ntp_data[f"srvnode-{node}"][self.ntp_keys[1]])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 8: Validated Restored NTP Configuration on srvnode-%s:%s", node,
                        resp[1])
        LOGGER.info("Step 8: Restored NTP configuration data")
        self.restored = True
        LOGGER.info(
            "-----     Completed NTP configuration Validation     -----")
