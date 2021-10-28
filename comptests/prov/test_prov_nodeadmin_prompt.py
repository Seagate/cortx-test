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
Prov test file to test nodeadmin field user commands as part of Field Deployment.
"""

import os
import pytest
import logging

from commons.helpers.node_helper import Node
from config import CMN_CFG, PROV_CFG
from commons.utils import assert_utils
from libs.prov.prov_deploy_ff import ProvDeployFFLib
from commons import commands
from libs.prov.provisioner import Provisioner
from configparser import ConfigParser

LOGGER = logging.getLogger(__name__)


class TestProvNodeAdmin:

    @classmethod
    def setup_class(cls):
        """Setup operations for the test file."""
        LOGGER.info("STARTED: Setup Module operations")
        cls.node_list = []
        cls.field_node_list = []
        cls.setup_type = CMN_CFG["setup_type"]
        cls.product_family = CMN_CFG["product_family"]
        cls.product_type = CMN_CFG["product_type"]
        for node in range(len(CMN_CFG["nodes"])):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
            cls.node_list.append(cls.node_obj)
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.test_config_template = PROV_CFG["deploy_ff"]["deployment_template"]
        cls.build_no = os.getenv("Build", None)
        cls.build_branch = os.getenv("Build_Branch", "stable")
        if cls.build_no:
            if cls.build_branch == "stable" or cls.build_branch == "main":
                cls.build = "{}/{}".format(cls.build_no, "prod")
        else:
            cls.build = "last_successful_prod"
        os_version = cls.node_obj.execute_cmd(cmd=commands.CMD_OS_REL,
                                              read_lines=True)[0].strip()
        cls.version = str(os_version.split()[3])
        cls.build_url = PROV_CFG["build_url"].format(
            cls.build_branch, cls.version, cls.build)
        LOGGER.info("Install all RPMs required for deployment.")
        for node_obj in cls.node_list:
            cls.res = ProvDeployFFLib.cortx_prepare(node_obj, cls.build_no, cls.build_url)

        LOGGER.info("Create nodeadmin and support users as part of finalize command.")
        cls.resp = Provisioner.create_deployment_config_universal(cls.test_config_template,
                                                                  cls.node_list,
                                                                  mgmt_vip=cls.mgmt_vip)
        cls.deploy_cfg = ConfigParser()
        cls.deploy_cfg.read(cls.resp[1])
        cls.deploy_ff = ProvDeployFFLib()
        for node_no, node_obj in enumerate(cls.node_list, start=1):

            resp = cls.deploy_ff.factory_manufacturing(nd_obj=node_obj, nd_no=node_no,
                                                       node_config=cls.deploy_cfg["srvnode-" + str(node_no)])
            assert_utils.assert_true(resp[0])
        for node in range(len(CMN_CFG["field_users"]["nodeadmin"])):
            cls.field_hostname = CMN_CFG["field_users"]["nodeadmin"][node]["hostname"]
            cls.field_username = CMN_CFG["field_users"]["nodeadmin"][node]["username"]
            cls.field_default_pwd = CMN_CFG["field_users"]["nodeadmin"][node]["default_password"]
            cls.field_pwd = CMN_CFG["field_users"]["nodeadmin"][node]["password"]
            cls.field_user_node_obj = Node(hostname=cls.field_hostname, username=cls.field_username,
                                           password=cls.field_default_pwd)
            cls.field_node_list.append(cls.field_user_node_obj)
        LOGGER.info("Done: Setup operations finished.")

    @pytest.fixture(scope="module")
    def field_user_node_list(self):
        field_node_list = []
        for node in range(len(CMN_CFG["field_users"]["nodeadmin"])):
            field_hostname = CMN_CFG["field_users"]["nodeadmin"][node]["hostname"]
            field_username = CMN_CFG["field_users"]["nodeadmin"][node]["username"]
            field_pwd = CMN_CFG["field_users"]["nodeadmin"][node]["password"]
            field_user_node_obj = Node(hostname=field_hostname, username=field_username,
                                       password=field_pwd)
            field_node_list.append(field_user_node_obj)
        return field_node_list

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24873")
    def test_24873(self):
        """Verify nodeadmin user reset the password during first login."""
        LOGGER.info("Changing nodeadmin field user password.")
        for field_user_node_obj in self.field_node_list:
            resp = Provisioner.change_field_user_password(field_user_node_obj, new_password=self.field_pwd)
            assert_utils.assert_true(resp)

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24745")
    def test_24745(self, field_user_node_list):
        """Verify server identification command with nodeadmin user."""
        for nd_no, field_user_node_obj in enumerate(field_user_node_list, start=1):
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_PREPARE_NODE.format(1, 1, nd_no))
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24750")
    def test_24750(self, field_user_node_list):
        """Verify nodeadmin user able to configure search domain name and hostname during field deployment."""
        for nd_no, field_user_node_obj in enumerate(field_user_node_list, start=0):
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_PREPARE_NETWORK.format(
                                                                          CMN_CFG["nodes"][nd_no]["hostname"],
                                                                          PROV_CFG["deploy_ff"]["search_domains"],
                                                                          PROV_CFG["deploy_ff"]["dns_servers"]))
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24760")
    def test_24760(self, field_user_node_list):
        """Verify nodeadmin user able to configure static network configuration for management network."""
        network_type = "management"
        for nd_no, field_user_node_obj in enumerate(field_user_node_list, start=0):
            ip_addr = CMN_CFG["nodes"][nd_no]["ip"]
            node_obj = self.node_list[nd_no]
            netmask = node_obj.execute_cmd(cmd=commands.CMD_GET_NETMASK.format(ip_addr))
            netmask = netmask.strip().decode("utf-8")
            gateway = PROV_CFG["deploy_ff"]["gateway_lco"]
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_PREPARE_NETWORK_TYPE.format(
                                                                          network_type,
                                                                          ip_addr, netmask,
                                                                          gateway))
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24880")
    def test_24880(self, field_user_node_list):
        """Verify nodeadmin user able to configure static network configuration for data network."""
        network_type = "data"
        for nd_no, field_user_node_obj in enumerate(field_user_node_list, start=0):
            ip_addr = CMN_CFG["nodes"][nd_no]["public_data_ip"]
            node_obj = self.node_list[nd_no]
            netmask = node_obj.execute_cmd(cmd=commands.CMD_GET_NETMASK.format(ip_addr))
            netmask = netmask.strip().decode("utf-8")
            gateway = "0.0.0.0"
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_PREPARE_NETWORK_TYPE.format(
                                                                          network_type,
                                                                          ip_addr, netmask,
                                                                          gateway))
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24881")
    def test_24881(self, field_user_node_list):
        """Verify nodeadmin user able to configure static network configuration for private network."""
        network_type = "private"
        for nd_no, field_user_node_obj in enumerate(field_user_node_list, start=0):
            ip_addr = CMN_CFG["nodes"][nd_no]["private_data_ip"]
            node_obj = self.node_list[nd_no]
            netmask = node_obj.execute_cmd(cmd=commands.CMD_GET_NETMASK.format(ip_addr))
            netmask = netmask.strip().decode("utf-8")
            gateway = "0.0.0.0"
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_PREPARE_NETWORK_TYPE.format(
                                                                          network_type,
                                                                          ip_addr, netmask,
                                                                          gateway))
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24885")
    def test_24885(self, field_user_node_list):
        """Verify nodeadmin user able to configure firewall during field deployment."""
        for field_user_node_obj in field_user_node_list:
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_CFG_FIREWALL.format(
                                                                          PROV_CFG["deploy_ff"]["firewall_url"]),
                                                                      timeout=300)
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24886")
    def test_24886(self, field_user_node_list):
        """Verify nodeadmin user able to configure time server during field deployment."""
        for field_user_node_obj in field_user_node_list:
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_CFG_NTP.format("UTC"))
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24887")
    def test_24887(self, field_user_node_list):
        """Verify nodeadmin user able to run node finalize command during field deployment."""
        for field_user_node_obj in field_user_node_list:
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(field_user_node_obj,
                                                                      cmd=commands.FIELD_NODE_PREP_FINALIZE)
            assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24962")
    def test_24962(self, field_user_node_list):
        """Verify nodeadmin user able to create cluster."""
        hostnames_list = []
        for node in range(len(CMN_CFG["nodes"])):
            hostnames_list.append(CMN_CFG["nodes"][node]["hostname"])
        hostnames = " ".join(hostnames_list)
        primary_node_obj = field_user_node_list[0]
        resp = self.deploy_ff.cluster_definition(primary_node_obj, hostnames, self.build_url, field_user=True)
        assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24963")
    def test_24963(self, field_user_node_list):
        """Verify nodeadmin user able to returns cluster information."""
        cmd = "cluster show"
        node_obj = field_user_node_list[0]
        resp = self.deploy_ff.execute_cmd_using_field_user_prompt(node_obj,
                                                                  cmd=cmd)
        assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24912")
    def test_24912(self, field_user_node_list):
        """Verify nodeadmin user able to configure storage-set name and count during field deployment."""
        node_obj = field_user_node_list[0]
        resp = self.deploy_ff.execute_cmd_using_field_user_prompt(node_obj,
                                                                  cmd=commands.FIELD_STORAGE_SET_CREATE.format(
                                                                      PROV_CFG["deploy_ff"]["storage_set_name"],
                                                                      len(CMN_CFG["nodes"])
                                                                  ))
        assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24914")
    def test_24914(self, field_user_node_list):
        """
        Verify nodeadmin user able to configure server-logical name and storage-set
        name to node during field deployment.
        """
        srvnodes_list = []
        for node in range(len(CMN_CFG["nodes"])):
            srvnodes_list.append("srvnode-" + str(node + 1))
        srvnodes = " ".join(srvnodes_list)
        node_obj = field_user_node_list[0]
        resp = self.deploy_ff.execute_cmd_using_field_user_prompt(node_obj,
                                                                  cmd=commands.FIELD_STORAGE_SET_ADD_NODE.format(
                                                                      PROV_CFG["deploy_ff"]["storage_set_name"],
                                                                      srvnodes
                                                                  ))
        assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-24915")
    def test_24915(self, field_user_node_list):
        """
        Verify nodeadmin user able to configure server-logical name and storage-set
        name to enclosure during field deployment.
        """
        srvnodes_list = []
        for node in range(len(CMN_CFG["nodes"])):
            srvnodes_list.append("srvnode-" + str(node + 1))
        srvnodes = " ".join(srvnodes_list)
        node_obj = field_user_node_list[0]
        resp = self.deploy_ff.execute_cmd_using_field_user_prompt(node_obj,
                                                                  cmd=commands.FIELD_STORAGE_SET_ADD_ENCL.format(
                                                                      PROV_CFG["deploy_ff"]["storage_set_name"],
                                                                      srvnodes
                                                                  ))
        assert_utils.assert_true(resp[0])

    @pytest.mark.lr
    @pytest.mark.prov
    @pytest.mark.tags("TEST-249156")
    def test_24916(self, field_user_node_list):
        """
        Verify nodeadmin user able to configure server-logical name and storage-set
        name to enclosure during field deployment.
        """
        node_obj = field_user_node_list[0]
        for cfg_type in ["sns", "dix"]:
            data = self.deploy_cfg["srvnode_default"][f"storage.durability.{cfg_type}.data"]
            parity = self.deploy_cfg["srvnode_default"][f"storage.durability.{cfg_type}.parity"]
            spare = self.deploy_cfg["srvnode_default"][f"storage.durability.{cfg_type}.spare"]
            resp = self.deploy_ff.execute_cmd_using_field_user_prompt(node_obj,
                                                                      cmd=commands.FIELD_STORAGE_SET_CONFIG.format(
                                                                          PROV_CFG["deploy_ff"]["storage_set_name"],
                                                                          cfg_type, data, parity, spare))
            assert_utils.assert_true(resp[0])
