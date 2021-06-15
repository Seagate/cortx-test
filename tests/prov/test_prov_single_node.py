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
Prov test file for all the Prov tests scenarios for single node VM.
"""

import os
import logging
import random
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons import constants as common_cnst
from commons.utils import assert_utils
from commons import pswdmanager
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, PROV_CFG
from libs.prov.provisioner import Provisioner
from libs.csm.cli.cli_csm_user import CortxCliCsmUser

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestProvSingleNode:
    """
    Test suite for prov tests scenarios for single node VM.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.build = os.getenv("Build", None)
        cls.build = "{}/{}".format(cls.build,
                                   "prod") if cls.build else "last_successful_prod"
        cls.build_branch = os.getenv("Build_Branch", "stable")
        cls.build_path = PROV_CFG["build_url"].format(
            cls.build_branch, cls.build)
        LOGGER.info(
            "User provided Hostname: {} and build path: {}".format(
                cls.host, cls.build_path))
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.hlt_obj = Health(hostname=cls.host, username=cls.uname,
                             password=cls.passwd)
        cls.prov_obj = Provisioner()
        cls.set_ntp = None
        cls.restored = True
        cls.CSM_USER = CortxCliCsmUser()
        cls.CSM_USER.open_connection()
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
            LOGGER.info(
                "TEARDOWN: Restored NTP configuration data: {}.".format(
                    resp[1]))
        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
    @pytest.mark.tags("TEST-19439")
    @CTFailOn(error_handler)
    def test_deployment_single_node(self):
        """
        Test method for the single node VM deployment.
        This has 3 main stages: check for the required prerequisites, trigger the deployment jenkins job
        and after deployment done, check for services status.
        """
        LOGGER.info("Starting the prerequisite checks.")
        test_cfg = PROV_CFG["single-node"]["prereq"]

        LOGGER.info("Check that the host is pinging")
        cmd = common_cmds.CMD_PING.format(self.host)
        self.nd_obj.execute_cmd(cmd, read_lines=True)

        LOGGER.info("Checking number of volumes present")
        cmd = common_cmds.CMD_LSBLK
        count = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("count : {}".format(int(count[0])))
        assert_utils.assert_greater_equal(
            int(count[0]), test_cfg["count"], "Need at least 2 disks for deployment")

        LOGGER.info("Checking OS release version")
        cmd = common_cmds.CMD_OS_REL
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        resp = resp[0].strip()
        LOGGER.info("os rel: {}".format(resp))
        assert_utils.assert_equal(resp, test_cfg["os_release"],
                                  "OS release is different than expected.")

        LOGGER.info("Checking kernel version")
        cmd = common_cmds.CMD_KRNL_VER
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        resp = resp[0].strip()
        LOGGER.info("kernel: {}".format(resp))
        assert_utils.assert_equal(
            resp,
            test_cfg["kernel"],
            "Kernel version differs than expected.")

        LOGGER.info("Starting the deployment steps.")
        test_cfg = PROV_CFG["single-node"]["deploy"]

        common_cnst.PARAMS["CORTX_BUILD"] = self.build_path
        common_cnst.PARAMS["HOST"] = self.host
        common_cnst.PARAMS["HOST_PASS"] = self.passwd
        token = pswdmanager.decrypt(common_cnst.TOKEN_NAME)
        output = Provisioner.build_job(
            test_cfg["job_name"], common_cnst.PARAMS, token)
        LOGGER.info("Jenkins Build URL: {}".format(output['url']))
        assert_utils.assert_equal(
            output['result'],
            test_cfg["success_msg"],
            "Deployment is not successful, please check the url.")

        LOGGER.info("Starting the post deployment checks.")
        test_cfg = PROV_CFG["system"]

        LOGGER.info("Check that all the services are up in hctl.")
        cmd = common_cmds.MOTR_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["offline"], line, "Some services look offline.")

        LOGGER.info("Check that all services are up in pcs.")
        cmd = common_cmds.PCS_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["stopped"], line, "Some services are not up.")
        LOGGER.info(
            "Successfully deployed the build after prereq checks and done post "
            "deploy checks as well.")

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
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
                "Verification of {} from pillar as well as confstore template.".format(key))
            output = self.prov_obj.confstore_verification(
                key, self.nd_obj, node_id)
            assert_utils.assert_true(output[0], output[1])

        LOGGER.info("Completed: confstore keys validation.")

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
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
        LOGGER.info("Stored NTP configuration data = {}.".format(self.set_ntp))

        timeserver_data = PROV_CFG['system_ntp']['timeserver']
        timezone_data = PROV_CFG['system_ntp']['timezone']
        LOGGER.info("Step 1: Check that the cluster is up and running.")
        res = self.hlt_obj.check_node_health()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Step 1: Node is accessible and PCS is up and running.")

        LOGGER.info("Step 2: Validate that admin user is created")
        resp = self.CSM_USER.login_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.CSM_USER.logout_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Validated that admin user is created")

        LOGGER.info("Get NTP configuration data.")
        get_ntp_resp = self.prov_obj.get_ntpsysconfg(
            self.ntp_keys, self.nd_obj, 1)
        assert_utils.assert_true(get_ntp_resp[0], get_ntp_resp[1])
        LOGGER.info("NTP configuration data = {}.".format(get_ntp_resp[1]))

        ntp_time_server_val = get_ntp_resp[1][self.ntp_keys[0]]
        ntp_time_zone_val = get_ntp_resp[1][self.ntp_keys[1]]
        LOGGER.info("Step 3: Validate time_server is set to {} in /etc/chrony.conf".format(
            ntp_time_server_val))
        resp = self.prov_obj.get_chrony(
            node_obj=self.nd_obj,
            time_server=ntp_time_server_val)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Validated time_server in /etc/chrony.conf response = {}".format(
            resp[1]))

        set_timezone = (random.choice(
            [ii for ii in timezone_data if ii != ntp_time_zone_val]))
        set_timesrv_ip = (random.choice(
            [ii for ii in timeserver_data if ii != ntp_time_server_val]))
        LOGGER.info("Step 4: Set time_server {} and timezone {}".format(
            set_timesrv_ip, set_timezone))
        resp = self.prov_obj.set_ntpsysconfg(
            self.nd_obj, time_server=set_timesrv_ip, timezone=set_timezone)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 5: Validate set NTP configuration in pillar data")
        resp = self.prov_obj.sysconfg_verification(
            self.ntp_keys, self.nd_obj, node_id=1,
            exp_t_srv=set_timesrv_ip, exp_t_zone=set_timezone)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 5: Validated set NTP configuration in pillar data {}.".format(
                resp[1]))

        LOGGER.info("Step 6: Validate set time_server in /etc/chrony.conf")
        resp = self.prov_obj.get_chrony(
            node_obj=self.nd_obj, time_server=set_timesrv_ip)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Validated set time_server in /etc/chrony.conf response = {}".format(
            resp[1]))

        LOGGER.info(
            "Step 7: Restore and Validate NTP configuration data to {}".format(
                self.set_ntp))
        resp = self.prov_obj.set_ntpsysconfg(
            self.nd_obj, time_server=self.set_ntp[self.ntp_keys[0]],
            timezone=self.set_ntp[self.ntp_keys[1]])
        assert_utils.assert_true(resp[0], resp[1])

        resp = self.prov_obj.sysconfg_verification(
            self.ntp_keys, self.nd_obj, node_id=1, exp_t_srv=self.set_ntp[self.ntp_keys[0]],
            exp_t_zone=self.set_ntp[self.ntp_keys[1]])
        LOGGER.info(
            "Step 7: Validated Restored NTP configuration on srvnode-1: {}".format(resp[1]))
        self.restored = True
        LOGGER.info(
            "-----     Completed NTP configuration Validation     -----")
