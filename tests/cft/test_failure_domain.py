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

"""Failure Domain Test Suite."""
import configparser
import logging
import os
import time
from multiprocessing import Process

import pytest

from commons import commands as common_cmd
from commons import configmanager
from commons import pswdmanager
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG, HA_CFG
from libs.prov.provisioner import Provisioner


class TestFailureDomain:
    """Test Failure Domain (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        test_config = "config/cft/test_failure_domain.yaml"
        cls.cft_test_cfg = configmanager.get_config_wrapper(fpath=test_config)
        cls.setup_type = CMN_CFG["setup_type"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            cls.host_list.append(CMN_CFG["nodes"][node]["host"])
            cls.node_list.append(Node(hostname=CMN_CFG["nodes"][node]["hostname"],
                                      username=CMN_CFG["nodes"][node]["username"],
                                      password=CMN_CFG["nodes"][node]["password"]))
        cls.nd1_obj = cls.node_list[0]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.test_config_template = cls.cft_test_cfg["deployment_template"]

        cls.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        cls.build = os.getenv("Build", None)
        cls.build_branch = os.getenv("Build_Branch", "stable")
        if cls.build:
            if cls.build_branch == "stable" or cls.build_branch == "main":
                cls.build = "{}/{}".format(cls.build, "prod")
        else:
            cls.build = "last_successful_prod"
        os_version = cls.nd1_obj.execute_cmd(cmd=common_cmd.CMD_OS_REL,
                                      read_lines=True)[0].strip()
        version = "centos-" + str(os_version.split()[3])
        cls.build_url = cls.cft_test_cfg["test_deployment_ff"]["build_url"].format(
            cls.build_branch, version, cls.build)

    def setup_method(self):
        """Revert the VM's before starting the deployment tests"""
        self.log.info("Reverting all the VM before deployment")
        revert_proc = []
        for host in self.host_list:
            p = Process(target=self.revert_vm_snapshot(host))
            p.start()
            revert_proc.append(p)
        for p in revert_proc:
            p.join()

    def revert_vm_snapshot(self, host):
        """Revert VM snapshot
           host: VM name """
        resp = system_utils.execute_cmd(cmd=common_cmd.CMD_VM_REVERT.format(
            self.vm_username, self.vm_password, host), read_lines=True)

        assert_utils.assert_true(resp[0], resp[1])

    def deploy_3node_vm(self, config_file_path: str = None, expect_failure: bool = False):
        """
        Deploy 3 node using jenkins job
        """
        test_cfg = self.cft_test_cfg["test_deployment"]
        self.log.info("Adding data required for the jenkins job execution")
        parameters = dict()

        parameters['Client_Node'] = os.getenv("Client_Node", None)
        parameters['Git_Repo'] = os.getenv("Git_Repo", 'https://github.com/Seagate/cortx-test.git')
        parameters['Git_Branch'] = os.getenv("Git_Branch", 'dev')
        parameters['Cortx_Build'] = os.getenv("Build", None)
        parameters['Cortx_Build_Branch'] = os.getenv("Build_Branch", "stable")

        parameters['Target_Node'] = CMN_CFG["setupname"]
        parameters['Node1_Hostname'] = CMN_CFG["nodes"][0]["hostname"]
        parameters['Node2_Hostname'] = CMN_CFG["nodes"][1]["hostname"]
        parameters['Node3_Hostname'] = CMN_CFG["nodes"][2]["hostname"]
        parameters['HOST_PASS'] = CMN_CFG["nodes"][0]["password"]
        parameters['MGMT_VIP'] = CMN_CFG["csm"]["mgmt_vip"]
        parameters['ADMIN_USR'] = CMN_CFG["csm"]["csm_admin_user"]["username"]
        parameters['ADMIN_PWD'] = CMN_CFG["csm"]["csm_admin_user"]["password"]
        parameters['Skip_Deployment'] = test_cfg["skip_deployment"]
        parameters['Skip_Preboarding'] = test_cfg["skip_preboarding"]
        parameters['Skip_Onboarding'] = test_cfg["skip_onboarding"]
        parameters['Skip_S3_Configuration'] = test_cfg["skip_s3_configure"]

        self.log.info("Parameters for jenkins job : %s", parameters)

        if config_file_path is not None and os.path.exists(config_file_path):
            self.log.info("Retrieving the config details for deployment from provided config file")
            with open(config_file_path, 'r') as file:
                parameters['Provisioner_Config'] = file.read()
        else:
            self.log.error(
                "Config file not provided, Deployment to be proceeded with defaults values")
            assert_utils.assert_true(False, "Config File not provided for deployment")

        output = Provisioner.build_job(test_cfg["jenkins_job_name"], parameters,
                                       test_cfg["jenkins_token"],
                                       test_cfg["jenkins_job_url"])
        self.log.info("Jenkins Build URL: %s", output['url'])
        self.log.info("Result : %s", output['result'])
        if not expect_failure:
            assert_utils.assert_equal(output['result'], "SUCCESS",
                                      "Job is not successful, please check the url.")
        else:
            assert_utils.assert_equal(output['result'], "FAILURE",
                                      "Job is successful, expected to fail")

    def configure_server(self, nd_obj, node_no):
        self.log.info("Configure Server")
        srvnode = "srvnode-{}".format(node_no)
        nd_obj.execute_cmd(cmd=common_cmd.CMD_SERVER_CFG.format(srvnode, CMN_CFG["setup_type"]),
                           read_lines=True)

    def configure_network(self, nd_obj, nd_no):
        self.log.info("Configure Network ")
        self.log.info("Configure Network transport")
        nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_TRANSPORT.format(
            self.cft_test_cfg["test_deployment_ff"]["network_trans"]), read_lines=True)

        self.log.info("Configure Management Interface")
        nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_INTERFACE.format(
            CMN_CFG["nodes"][nd_no]["ip"], "management"), read_lines=True)

        self.log.info("Configure Data Interface")
        nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_INTERFACE.format(
            CMN_CFG["nodes"][nd_no]["public_data_ip"], "data"), read_lines=True)

        self.log.info("Configure Private Interface")
        nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_INTERFACE.format(
            CMN_CFG["nodes"][nd_no]["private_data_ip"], "private"),
            read_lines=True)

        self.log.info("Configure BMC Interface")
        # default details for VM
        nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_BMC.format("127.0.0.1", "admin", "admin"),
                           read_lines=True)

    def configure_storage(self, nd_obj, node_no, node_config):
        self.log.info("Configure Storage")
        self.log.info("Configure Storage Config")
        for cnt_type in ["primary", "secondary"]:
            nd_obj.execute_cmd(cmd=common_cmd.STORAGE_CFG_CONT.format(cnt_type), read_lines=True)

        self.log.info("Configure Storage name")
        encl_name = "Enclosure" + str(node_no)
        nd_obj.execute_cmd(cmd=common_cmd.STORAGE_CFG_NAME.format(encl_name), read_lines=True)

        self.log.info("Configure CVG")
        for key in node_config.keys():
            if ".data_devices" in key:
                cvg_no = key.split(".")[2]
                data_devices = node_config[f"storage.cvg.{cvg_no}.data_devices"]
                meta_devices = node_config[f"storage.cvg.{cvg_no}.metadata_devices"]
                nd_obj.execute_cmd(cmd=common_cmd.STORAGE_CFG_CVG.format(cvg_no, data_devices,
                                                                         meta_devices),
                                   read_lines=True)

    def factory_manufacturing(self, nd_obj, nd_no, node_config):
        self.configure_server(nd_obj, nd_no)
        self.configure_network(nd_obj, nd_no)
        self.configure_storage(nd_obj, nd_no, node_config)
        self.log.info("Configure Security")
        nd_obj.execute_cmd(cmd=
        common_cmd.SECURITY_CFG.format(
            self.cft_test_cfg["test_deployment_ff"]["security_path"]), read_lines=True)

        self.log.info("Configure Feature")
        for key, val in self.cft_test_cfg["test_deployment_ff"]["feature_config"].items():
            nd_obj.execute_cmd(cmd=common_cmd.FEATURE_CFG.format(key, val), read_lines=True)

        self.log.info("Initialize Node")
        nd_obj.execute_cmd(cmd=common_cmd.INITIALIZE_NODE, read_lines=True)

        self.log.info("Setup Node signature")
        nd_obj.execute_cmd(cmd=common_cmd.SET_NODE_SIGN.format("srvnode-" + str(nd_no)),
                           read_lines=True)

        self.log.info("Finalize Node Configuration")
        nd_obj.execute_cmd(cmd=common_cmd.NODE_FINALIZE, read_lines=True)

    def field_deployment_node(self, nd_obj, nd_no):
        self.log.info("Field Deployment")
        self.log.info("Prepare Node")
        self.log.info("Configure Server Identification")
        nd_obj.execute_cmd(cmd=common_cmd.PREPARE_NODE.format(1, 1, nd_no), read_lines=True)

        self.log.info("Prepare Network")
        nd_obj.execute_cmd(cmd=
        common_cmd.PREPARE_NETWORK.format(
            self.cft_test_cfg["test_deployment_ff"]["dns_servers"],
            self.cft_test_cfg["test_deployment_ff"]["search_domains"]), read_lines=True)

        self.log.info("Configure Network")
        ips = {"management": CMN_CFG["nodes"][nd_no]["ip"],
               "data": CMN_CFG["nodes"][nd_no]["public_data_ip"],
               "private": CMN_CFG["nodes"][nd_no]["private_data_ip"]}

        for network_type, ip_addr in ips.items():
            netmask = nd_obj.execute_cmd(cmd=common_cmd.CMD_GET_NETMASK.format(ip_addr))
            gateway = "0.0.0.0"
            if network_type == "management":
                gateway = "10.230.240.1"
            nd_obj.execute_cmd(cmd=common_cmd.PREPARE_NETWORK_TYPE.format(network_type,
                                                                          ip_addr, netmask,
                                                                          gateway),
                               read_lines=True)

        self.log.info("Configure Firewall")
        nd_obj.execute_cmd(cmd=
        common_cmd.CFG_FIREWALL.format(
            self.cft_test_cfg["test_deployment_ff"]["firewall_url"]), read_lines=True)

        self.log.info("Configure Network Time Server")
        nd_obj.execute_cmd(cmd=common_cmd.CFG_NTP.format("UTC"), read_lines=True)

        self.log.info("Node Finalize")
        nd_obj.execute_cmd(cmd=common_cmd.NODE_PREP_FINALIZE, read_lines=True)

    def config_cluster(self, node_obj, setup_type: str) -> tuple:
        """
        This method deploys cortx and 3rd party software components on given VM setup
        :param node_obj: Host object of the primary node
        :param setup_type: Type of setup e.g., single, 3_node etc
        :return: True/False and deployment status
        """
        components = [
            "foundation",
            "iopath",
            "controlpath",
            "ha"]
        for comp in components:
            self.log.info("Deploying %s component", comp)
            try:
                node_obj.execute_cmd(
                    cmd=common_cmd.CMD_DEPLOY_VM.format(
                        setup_type, comp), read_lines=True)
            except Exception as error:
                self.log.error(
                    "An error occurred in %s:",
                    TestFailureDomain.config_cluster.__name__)
                if isinstance(error.args[0], list):
                    self.log.error("\n".join(error.args[0]).replace("\\n", "\n"))
                else:
                    self.log.error(error.args[0])
                return False, error

        return True, "Deployment Completed"

    def config_storage_set(self, nd1_obj, hostnames: str, deploy_config):
        """
        Configure Storage Set
        """
        self.log.info("Create Storage Set")
        nd1_obj.execute_cmd(cmd=
        common_cmd.STORAGE_SET_CREATE.format(
            self.cft_test_cfg["test_deployment_ff"]["storage_set_name"],
            self.num_nodes), read_lines=True)
        self.log.info("Add nodes to Storage Set")
        nd1_obj.execute_cmd(cmd=common_cmd.STORAGE_SET_ADD_NODE.format(
            self.cft_test_cfg["test_deployment_ff"]["storage_set_name"], hostnames),
            read_lines=True)
        self.log.info("Add Enclosure to Storage Set")
        nd1_obj.execute_cmd(cmd=common_cmd.STORAGE_SET_ADD_ENCL.format(
            self.cft_test_cfg["test_deployment_ff"]["storage_set_name"], hostnames),
            read_lines=True)
        self.log.info("Add Durability Config")
        for cfg_type in ["sns", "dix"]:
            data = deploy_config["srvnode_default"][f"storage.durability.{cfg_type}.data"]
            parity = deploy_config["srvnode_default"][f"storage.durability.{cfg_type}.parity"]
            spare = deploy_config["srvnode_default"][f"storage.durability.{cfg_type}.parity"]
            nd1_obj.execute_cmd(cmd=common_cmd.STORAGE_SET_CONFIG.format(
                self.cft_test_cfg["test_deployment_ff"]["storage_set_name"], cfg_type, data, parity,
                spare),
                read_lines=True)

    def deploy_3node_vm_ff(self, deploy_config_file):
        """
        Using factory and field method
        """
        self.log.info(
            "Starting Deployment on nodes:%s", self.host_list)
        self.log.info("Starting Deployment with Build:\n %s", self.build_url)
        test_cfg = self.cft_test_cfg["3-node-vm"]
        deploy_cfg = configparser.ConfigParser()
        deploy_cfg.read(deploy_config_file)

        for nd_no, nd_obj in enumerate(self.node_list, start=1):
            self.log.info(
                "Starting the prerequisite checks on node %s",
                nd_obj.hostname)
            self.log.info("Check that the host is pinging")
            nd_obj.execute_cmd(cmd=
                               common_cmd.CMD_PING.format(nd_obj.hostname), read_lines=True)

            self.log.info("Checking number of volumes present")
            count = nd_obj.execute_cmd(cmd=common_cmd.CMD_LSBLK, read_lines=True)
            self.log.info("No. of disks : %s", count[0])
            assert_utils.assert_greater_equal(int(
                count[0]), test_cfg["prereq"]["min_disks"],
                "Need at least 4 disks for deployment")

            self.log.info("Checking OS release version")
            resp = nd_obj.execute_cmd(cmd=
                                      common_cmd.CMD_OS_REL,
                                      read_lines=True)[0].strip()
            self.log.info("OS Release Version: %s", resp)
            assert_utils.assert_in(resp, test_cfg["prereq"]["os_release"],
                                      "OS version is different than expected.")

            self.log.info("Checking kernel version")
            resp = nd_obj.execute_cmd(cmd=
                                      common_cmd.CMD_KRNL_VER,
                                      read_lines=True)[0].strip()
            self.log.info("Kernel Version: %s", resp)
            assert_utils.assert_in(
                resp,
                test_cfg["prereq"]["kernel"],
                "Kernel Version is different than expected.")

            self.log.info("Checking network interfaces")
            resp = nd_obj.execute_cmd(cmd=common_cmd.CMD_GET_NETWORK_INTERFACE, read_lines=True)
            self.log.info("Network Interfaces: %s", resp)
            assert_utils.assert_greater_equal(len(resp), 3,
                                              "Network Interfaces should be more than 3")

            self.log.info("Stopping Puppet service")
            nd_obj.execute_cmd(cmd=common_cmd.SYSTEM_CTL_STOP_CMD.format(common_cmd.PUPPET_SERV),
                               read_lines=True)

            self.log.info("Disabling Puppet service")
            nd_obj.execute_cmd(cmd=common_cmd.SYSTEM_CTL_DISABLE_CMD.format(common_cmd.PUPPET_SERV),
                               read_lines=True)

            self.log.info("Download the install.sh script to the node")
            resp = nd_obj.execute_cmd(cmd=common_cmd.CMD_GET_PROV_INSTALL.format(self.build_branch),
                                      read_lines=True)
            self.log.debug("Downloaded install.sh : %s", resp)

            self.log.info("Installs CORTX packages (RPM) and their dependencies ")
            resp = nd_obj.execute_cmd(cmd=common_cmd.CMD_INSTALL_CORTX_RPM.format(self.build_url),
                                      read_lines=True)
            self.log.debug("Installed RPM's : %s", resp)

            self.log.info("Perform Factory Manufacturing")
            self.factory_manufacturing(nd_obj, nd_no, deploy_cfg["srvnode-" + str(nd_no)])

            self.log.info("Perform Field Deployment")
            self.field_deployment_node(nd_obj, nd_no)

        self.log.info("Cluster Definition")
        hostnames = ""
        for node in range(self.num_nodes):
            hostnames = " ".join(CMN_CFG["nodes"][node]["hostname"])
        self.nd1_obj.execute_cmd(cmd=
                                 common_cmd.CLUSTER_CREATE.format(hostnames, self.mgmt_vip,
                                                                  self.build_url), read_lines=True)

        self.log.info("Configure Storage Set")
        self.config_storage_set(self.nd1_obj, hostnames, deploy_cfg)

        self.log.info("Prepare Cluster")
        self.nd1_obj.execute_cmd(cmd=common_cmd.CLUSTER_PREPARE, read_lines=True)

        self.log.info("Configure Cluster")
        resp = self.config_cluster(self.nd1_obj, test_cfg["setup-type"])
        assert_utils.assert_true(resp[0], "Deploy Failed")

        self.log.info("Starting Cluster")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmd.CMD_START_CLSTR,
            read_lines=True)[0].strip()
        assert_utils.assert_exact_string(resp, self.cft_test_cfg["cluster_start_msg"])
        time.sleep(test_cfg["cluster_start_delay"])

        self.log.info("Starting the post deployment checks")
        test_cfg = self.cft_test_cfg["system"]
        self.log.info("Check that all the services are up in hctl")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmd.MOTR_STATUS_CMD, read_lines=True)
        self.log.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["offline"], line, "Some services look offline")

        self.log.info("Check that all services are up in pcs")
        resp = self.nd1_obj.execute_cmd(
            cmd=common_cmd.PCS_STATUS_CMD, read_lines=True)
        self.log.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["stopped"], line, "Some services are not up")

    @pytest.mark.run(order=1)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-23540")
    def test_23540(self):
        """Perform deployment,preboarding, onboarding,s3 configuration with 4+2+0 config"""
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              )
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_3node_vm_ff(resp[1])

    @pytest.mark.run(order=4)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 1, [6, 2, 0])])
    @pytest.mark.tags("TEST-22901")
    def test_22901(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Perform deployment with Invalid config and expect failure
        datapool : N+K+S : 6+2+0, data device per cvg: 1
        """
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]),
                                                              skip_disk_count_check=True
                                                              )
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_3node_vm_ff(resp[1])

    @pytest.mark.run(order=5)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(1, 7, [8, 2, 0])])
    @pytest.mark.tags("TEST-26959")
    def test_26959(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """ Test Deployment using following config
        N+K+S: 8+2+0
        CVG’s per node : 1
        Data Devices per CVG: 7
        Metadata Device per CVG : 1
        """
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp[1])
        self.deploy_3node_vm_ff(resp[1])

    @pytest.mark.run(order=8)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [3, 2, 0])])
    @pytest.mark.tags("TEST-26960")
    def test_26960(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 3+2+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_3node_vm_ff(resp[1])

    @pytest.mark.run(order=12)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [8, 4, 0])])
    @pytest.mark.tags("TEST-26961")
    def test_26961(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 8+4+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_3node_vm_ff(resp[1])

    @pytest.mark.run(order=16)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [10, 5, 0])])
    @pytest.mark.tags("TEST-26962")
    def test_26962(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 10+5+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_3node_vm_ff(resp[1])
