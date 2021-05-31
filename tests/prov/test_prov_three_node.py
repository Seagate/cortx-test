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
import time
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons.utils import assert_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, PROV_CFG
from libs.prov.provisioner import Provisioner

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestProvThreeNode:
    """
    Test suite for prov tests scenarios for three node VM.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.setup_type = CMN_CFG["setup_type"]
        cls.build = os.getenv("Build", None)
        cls.build = "{}/{}".format(cls.build,
                                   "prod") if cls.build else "last_successful_prod"
        cls.build_branch = os.getenv("Build_Branch", "stable")
        cls.build_url = PROV_CFG["build_url"].format(
            cls.build_branch, cls.build)
        cls.host1 = CMN_CFG["nodes"][0]["hostname"]
        cls.uname1 = CMN_CFG["nodes"][0]["username"]
        cls.passwd1 = CMN_CFG["nodes"][0]["password"]
        cls.nd1_obj = Node(hostname=cls.host1, username=cls.uname1,
                           password=cls.passwd1)
        cls.hlt_obj1 = Health(hostname=cls.host1, username=cls.uname1,
                              password=cls.passwd1)

        cls.host2 = CMN_CFG["nodes"][1]["hostname"]
        cls.uname2 = CMN_CFG["nodes"][1]["username"]
        cls.passwd2 = CMN_CFG["nodes"][1]["password"]
        cls.nd2_obj = Node(hostname=cls.host2, username=cls.uname2,
                           password=cls.passwd2)
        cls.hlt_obj2 = Health(hostname=cls.host2, username=cls.uname2,
                              password=cls.passwd2)

        cls.host3 = CMN_CFG["nodes"][2]["hostname"]
        cls.uname3 = CMN_CFG["nodes"][2]["username"]
        cls.passwd3 = CMN_CFG["nodes"][2]["password"]
        cls.nd3_obj = Node(hostname=cls.host3, username=cls.uname3,
                           password=cls.passwd3)
        cls.hlt_obj3 = Health(hostname=cls.host3, username=cls.uname3,
                              password=cls.passwd3)
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.prov_obj = Provisioner()
        LOGGER.info("Done: Setup module operations")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-21584")
    @CTFailOn(error_handler)
    def test_deployment_three_node_vm(self):
        """
        Prov test for deployment of 3-node node VM
        """
        test_cfg = PROV_CFG["3-node-vm"]
        node_obj_list = [self.nd1_obj, self.nd2_obj, self.nd3_obj]
        for nd_obj in node_obj_list:
            LOGGER.info(
                "Starting the prerequisite checks on node %s",
                nd_obj.hostname)
            LOGGER.info("Check that the host is pinging")
            nd_obj.execute_cmd(
                common_cmds.CMD_PING.format(
                    nd_obj.hostname),
                read_lines=True)

            LOGGER.info("Checking number of volumes present")
            count = nd_obj.execute_cmd(common_cmds.CMD_LSBLK, read_lines=True)
            LOGGER.info("No. of disks : %s", count[0])
            assert_utils.assert_greater_equal(int(
                count[0]), test_cfg["prereq"]["min_disks"], "Need at least 8 disks for deployment")

            LOGGER.info("Checking OS release version")
            resp = nd_obj.execute_cmd(
                common_cmds.CMD_OS_REL,
                read_lines=True)[0].strip()
            LOGGER.info("OS Release Version: %s", resp)
            assert_utils.assert_equal(resp, test_cfg["prereq"]["os_release"],
                                      "OS version is different than expected.")

            LOGGER.info("Checking kernel version")
            resp = nd_obj.execute_cmd(
                common_cmds.CMD_KRNL_VER,
                read_lines=True)[0].strip()
            LOGGER.info("Kernel Version: %s", resp)
            assert_utils.assert_equal(
                resp,
                test_cfg["prereq"]["kernel"],
                "Kernel Version is different than expected.")

            LOGGER.info(
                "Installing Provisioner API and requisite packages on node %s",
                nd_obj.hostname)
            resp = self.prov_obj.install_pre_requisites(
                node_obj=nd_obj, build_url=self.build_url)
            assert_utils.assert_true(
                resp[0], "Provisioner Installation Failed")
            LOGGER.info("Provisioner Version: %s", resp[1])

        LOGGER.info("Creating config.ini file")
        config_file = self.prov_obj.create_deployment_config(
            test_cfg["config_template"], node_obj_list, mgmt_vip=self.mgmt_vip)
        assert_utils.assert_true(config_file[0], config_file[1])
        self.nd1_obj.copy_file_to_remote(
            config_file[1], test_cfg["config_path_remote"])
        LOGGER.info(
            "Created and copied config.ini file at %s on node %s",
            test_cfg["config_path_remote"],
            self.nd1_obj)

        LOGGER.info("Performing Cortx Bootstrap")
        resp = self.prov_obj.bootstrap_cortx(
            test_cfg["config_path_remote"], self.build_url, node_obj_list)
        assert_utils.assert_true(resp[0], "Bootstrap Failed")

        LOGGER.info("Preparing pillar data")
        resp = self.prov_obj.prepare_pillar_data(
            self.nd1_obj, test_cfg["config_path_remote"], node_count=3)
        assert_utils.assert_true(resp[0], "Pillar data updation Failed")

        LOGGER.info("Validating Bootstrap")
        resp = self.prov_obj.bootstrap_validation(self.nd1_obj)
        assert_utils.assert_true(resp, "Bootstrap Validation Failed")

        LOGGER.info("Starting Deploy")
        resp = self.prov_obj.deploy_vm(self.nd1_obj, test_cfg["setup-type"])
        assert_utils.assert_true(resp[0], "Deploy Failed")

        LOGGER.info("Starting Cluster")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmds.CMD_START_CLSTR,
            read_lines=True)[0].strip()
        assert_utils.assert_exact_string(resp, PROV_CFG["cluster_start_msg"])
        time.sleep(test_cfg["cluster_start_delay"])

        LOGGER.info("Starting the post deployment checks")
        test_cfg = PROV_CFG["system"]
        LOGGER.info("Check that all the services are up in hctl")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmds.MOTR_STATUS_CMD, read_lines=True)
        LOGGER.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["offline"], line, "Some services look offline")

        LOGGER.info("Check that all services are up in pcs")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmds.PCS_STATUS_CMD, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["stopped"], line, "Some services are not up")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-21919")
    @CTFailOn(error_handler)
    def test_verify_services_three_node_vm(self):
        """
        Prov test for verification of all services on deployed system
        """
        LOGGER.info("Check that all cortx services are up")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmds.CMD_PCS_STATUS_FULL, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                PROV_CFG["system"]["stopped"],
                line,
                "Some services are not up")

        LOGGER.info("Check that all third party services are up")
        node_obj_list = [self.nd1_obj, self.nd2_obj, self.nd3_obj]
        for node in node_obj_list:
            LOGGER.info(
                "Verifying third party services running on node %s",
                node.hostname)
            node.send_systemctl_cmd(
                command="start", services=[
                    PROV_CFG["services"]["all"][0]])
            for service in PROV_CFG["services"]["all"]:
                resp = node.execute_cmd(
                    cmd=common_cmds.SYSTEM_CTL_STATUS_CMD.format(service),
                    read_lines=False)
                assert_utils.assert_exact_string(
                    str(resp), PROV_CFG["system"]["active"])
            if self.setup_type == "HW":
                for service in PROV_CFG["services"]["hw_specific"]:
                    resp = node.execute_cmd(
                        cmd=common_cmds.SYSTEM_CTL_STATUS_CMD.format(service),
                        read_lines=False)
                    assert_utils.assert_exact_string(
                        str(resp), PROV_CFG["system"]["active"])

        health_obj_list = [self.hlt_obj1, self.hlt_obj2, self.hlt_obj3]
        for node in health_obj_list:
            LOGGER.info(
                "Checking all services are running on respective ports")
            resp = self.prov_obj.verify_services_ports(
                node, PROV_CFG["service_ports"])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Verified all the services running on node %s",
                node.hostname)
