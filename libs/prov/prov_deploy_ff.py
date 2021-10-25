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
Provisioner utiltiy methods for Deployment using Factory and Field Method
"""
import logging
import time
from configparser import ConfigParser, SectionProxy

from commons import commands as common_cmd
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG

LOGGER = logging.getLogger(__name__)


class ProvDeployFFLib:
    """
    This class contains utility methods for all the operations related
    to Deployment using FF.
    """

    @staticmethod
    def deployment_prereq(nd_obj: Node):
        """
        Deployment prerequisites checks to be executed on each node.
        param: nd_obj : node object for command to be executed.
        """
        try:
            prereq_cfg = PROV_CFG["deploy_ff"]["prereq"]
            LOGGER.info(
                "Starting the prerequisite checks on node %s",
                nd_obj.hostname)
            LOGGER.info("Check that the host is pinging")
            nd_obj.execute_cmd(cmd=
                               common_cmd.CMD_PING.format(nd_obj.hostname), read_lines=True)

            LOGGER.info("Checking number of volumes present")
            count = nd_obj.execute_cmd(cmd=common_cmd.CMD_LSBLK, read_lines=True)
            LOGGER.info("No. of disks : %s", count[0])
            assert_utils.assert_greater_equal(int(
                count[0]), prereq_cfg["min_disks"],
                "Need at least 4 disks for deployment")

            LOGGER.info("Checking OS release version")
            resp = nd_obj.execute_cmd(cmd=
                                      common_cmd.CMD_OS_REL,
                                      read_lines=True)[0].strip()
            LOGGER.info("OS Release Version: %s", resp)
            assert_utils.assert_in(resp, prereq_cfg["os_release"],
                                   "OS version is different than expected.")

            LOGGER.info("Checking kernel version")
            resp = nd_obj.execute_cmd(cmd=
                                      common_cmd.CMD_KRNL_VER,
                                      read_lines=True)[0].strip()
            LOGGER.info("Kernel Version: %s", resp)
            assert_utils.assert_in(
                resp,
                prereq_cfg["kernel"],
                "Kernel Version is different than expected.")

            LOGGER.info("Checking network interfaces")
            resp = nd_obj.execute_cmd(cmd=common_cmd.CMD_GET_NETWORK_INTERFACE, read_lines=True)
            LOGGER.info("Network Interfaces: %s", resp)
            assert_utils.assert_greater_equal(len(resp), 3,
                                              "Network Interfaces should be more than 3")

            LOGGER.info("Stopping Puppet service")
            nd_obj.execute_cmd(cmd=common_cmd.SYSTEM_CTL_STOP_CMD.format(common_cmd.PUPPET_SERV),
                               read_lines=True)

            LOGGER.info("Disabling Puppet service")
            nd_obj.execute_cmd(cmd=common_cmd.SYSTEM_CTL_DISABLE_CMD.format(common_cmd.PUPPET_SERV),
                               read_lines=True)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.deployment_prereq.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "deployment_prereq Successful!!"

    @staticmethod
    def cortx_prepare(nd_obj: Node, build: str, build_url: str):
        """
        Installs Cortx packages(RPM)
        param: nd_obj: Node object to execute commands on
        param: build_branch: Branch of the build to be deployed
        param: build_url: Build URL
        """
        try:
            LOGGER.info("Download the install.sh script to the node")
            install_sh_path = f"{build_url}iso/install-2.0.0-{build}.sh"
            resp = nd_obj.execute_cmd(cmd=common_cmd.CMD_GET_PROV_INSTALL.format(install_sh_path),
                                      read_lines=True)
            LOGGER.debug("Downloaded install.sh : %s", resp)
            time.sleep(10)

            LOGGER.info("Installs CORTX packages (RPM) and their dependencies ")
            resp = nd_obj.execute_cmd(cmd=common_cmd.CMD_INSTALL_CORTX_RPM.format(build_url),
                                      read_lines=True)
            LOGGER.debug("Installed RPM's : %s", resp)
            time.sleep(10)

            LOGGER.info("Initialize command shell env")
            nd_obj.execute_cmd(cmd=common_cmd.CORTX_SETUP_HELP, read_lines=True)
            time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.cortx_prepare.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "cortx_prepare Successful!!"

    @staticmethod
    def configure_server(nd_obj: Node, node_no: int):
        """
        Configure Server
        param: nd_obj: node object for commands to be executed on
        param: node_no : Node number
        """
        try:
            LOGGER.info("Configure Server")
            srvnode = "srvnode-{}".format(node_no)
            nd_obj.execute_cmd(cmd=common_cmd.CMD_SERVER_CFG.format(srvnode, CMN_CFG["setup_type"]),
                               read_lines=True)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.configure_server.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "configure_server Successful!!"

    @staticmethod
    def configure_network(nd_obj: Node, network_trans: str):
        """
        Configure  Network Interfaces
        param: nd_obj: node object for commands to be executed on
        param: network_trans: Network Transport type
        """
        try:
            LOGGER.info("Configure Network ")
            LOGGER.info("Configure Network transport")
            nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_TRANSPORT.format(
                network_trans), read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Management Interface")
            nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_INTERFACE.format(
                "eth0", "management"), read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Data Interface")
            nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_INTERFACE.format(
                "eth1", "data"), read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Private Interface")
            nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_INTERFACE.format(
                "eth3", "private"), read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure BMC Interface")
            nd_obj.execute_cmd(cmd=common_cmd.NETWORK_CFG_BMC.format("127.0.0.1",
                                                                     CMN_CFG["bmc"]["username"],
                                                                     CMN_CFG["bmc"]["password"]),
                               read_lines=True)
            time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.configure_network.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "configure_network Successful!!"

    @staticmethod
    def configure_storage(nd_obj: Node,  node_config: SectionProxy):
        """
        Configure Storage
        param: nd_obj: node object for commands to be executed on
        param: node_no: Node number
        param: node_config: Section of particular Node from config.ini
        """
        try:
            LOGGER.info("Configure Storage")

            LOGGER.info("Configure Storage name")
            encl_name = "enclosure1"
            nd_obj.execute_cmd(cmd=common_cmd.STORAGE_CFG_NAME.format(encl_name), read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Storage Config")
            for cnt_type in ["primary", "secondary"]:
                nd_obj.execute_cmd(cmd=common_cmd.STORAGE_CFG_CONT.format(cnt_type),
                                   read_lines=True)
                time.sleep(10)

            LOGGER.info("Configure CVG")
            for key in node_config.keys():
                if ".data_devices" in key:
                    cvg_no = key.split(".")[2]
                    data_devices = node_config[f"storage.cvg.{cvg_no}.data_devices"]
                    meta_devices = node_config[f"storage.cvg.{cvg_no}.metadata_devices"]
                    nd_obj.execute_cmd(cmd=common_cmd.STORAGE_CFG_CVG.format(cvg_no, data_devices,
                                                                             meta_devices),
                                       read_lines=True)
                    time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.configure_storage.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "configure_storage Successful!!"

    @staticmethod
    def configure_security(nd_obj: Node, cert_path: str):
        """
        Configure Security
        param: nd_obj: node object for commands to be executed on
        param: cert_path: Certification file path (stx.pem)
        """
        try:
            LOGGER.info("Configure Security")
            nd_obj.execute_cmd(cmd=common_cmd.SECURITY_CFG.format(cert_path, read_lines=True))
            time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.configure_security.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "configure_security Successful!!"

    @staticmethod
    def configure_feature(nd_obj: Node, feature_conf: dict):
        """
        Configure Feature specific config setting
        param:  nd_obj: node object for commands to be executed on
        param: feature_conf: Feature config and its respective values.
        """
        try:
            LOGGER.info("Configure Feature")
            for key, val in feature_conf.items():
                nd_obj.execute_cmd(cmd=common_cmd.FEATURE_CFG.format(key, val), read_lines=True)
                time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.configure_feature.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "configure_feature Successful!!"

    @staticmethod
    def setup_node(nd_obj: Node):
        """
        Initialize and Finalize node configuration
        param:  nd_obj: node object for commands to be executed on
        param: nd_no: srvnode number
        """
        try:
            LOGGER.info("Initialize Node")
            nd_obj.execute_cmd(cmd=common_cmd.INITIALIZE_NODE, read_lines=True)
            time.sleep(10)

            LOGGER.info("Setup Node signature")
            nd_obj.execute_cmd(cmd=common_cmd.SET_NODE_SIGN.format("HP1_5U84"),
                               read_lines=True)
            time.sleep(10)

            LOGGER.info("Finalize Node Configuration")
            nd_obj.execute_cmd(cmd=common_cmd.NODE_FINALIZE, read_lines=True)
            time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.setup_node.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "setup_node Successful!!"

    def factory_manufacturing(self, nd_obj: Node, nd_no: int, node_config: SectionProxy, **kwargs):
        """
        Perform Factory Manufacturing Procedure
        param: nd_obj: node object for commands to be executed on
        param: nd_no: Node number
        param: node_config: Section of Node from config.ini
        param: network_trans: Network Transport protocol - (lnet/libfabric)
        param: security_path: Certification file path (stx.pem)
        """
        deploy_ff_cfg = PROV_CFG["deploy_ff"]
        network_trans = kwargs.get("network_trans", deploy_ff_cfg["network_trans"])
        security_path = kwargs.get("security_path", deploy_ff_cfg["security_path"])
        s3_service_instances = kwargs.get("s3_service_instances",
                                          deploy_ff_cfg["feature_config"]["'cortx>software>s3>service>instances'"])
        s3_io_max_units = kwargs.get("s3_service_instances",
                                     deploy_ff_cfg["feature_config"]["'cortx>software>s3>io>max_units'"])
        motr_client_instances = kwargs.get("s3_service_instances",
                                           deploy_ff_cfg["feature_config"]["'cortx>software>motr>service>client_instances'"])

        feature_conf = {"'cortx>software>s3>service>instances'": s3_service_instances,
                        "'cortx>software>s3>io>max_units'": s3_io_max_units,
                        "'cortx>software>motr>service>client_instances'": motr_client_instances}

        resp = self.configure_server(nd_obj, nd_no)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.configure_network(nd_obj, network_trans)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.configure_storage(nd_obj, node_config)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.configure_security(nd_obj, security_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.configure_feature(nd_obj, feature_conf)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.setup_node(nd_obj)
        assert_utils.assert_true(resp[0], resp[1])

        return True, "factory_manufacturing successful!!"

    @staticmethod
    def field_deployment_node(nd_obj: Node, nd_no: int):
        """
        Perform Field Deployment Procedure
        param: nd_obj: node object for commands to be executed on
        param: nd_no: Node number
        """
        try:
            deploy_ff_cfg = PROV_CFG["deploy_ff"]
            LOGGER.info("Field Deployment")
            LOGGER.info("Prepare Node")
            LOGGER.info("Configure Server Identification")
            nd_obj.execute_cmd(cmd=common_cmd.PREPARE_NODE.format(1, 1, nd_no), read_lines=True)
            time.sleep(10)

            LOGGER.info("Prepare Network")
            nd_obj.execute_cmd(cmd=
            common_cmd.PREPARE_NETWORK.format(
                CMN_CFG["nodes"][nd_no - 1]["hostname"],
                deploy_ff_cfg["search_domains"], deploy_ff_cfg["dns_servers"]),
                read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Network")
            ips = {"management": CMN_CFG["nodes"][nd_no - 1]["ip"],
                   "data": CMN_CFG["nodes"][nd_no - 1]["public_data_ip"],
                   "private": CMN_CFG["nodes"][nd_no - 1]["private_data_ip"]}

            for network_type, ip_addr in ips.items():
                netmask = nd_obj.execute_cmd(cmd=common_cmd.CMD_GET_NETMASK.format(ip_addr))
                netmask = netmask.strip().decode("utf-8")
                gateway = "0.0.0.0"
                if network_type == "management":
                    gateway = deploy_ff_cfg["gateway_lco"]
                nd_obj.execute_cmd(cmd=common_cmd.PREPARE_NETWORK_TYPE.format(network_type,
                                                                              ip_addr, netmask,
                                                                              gateway),
                                   read_lines=True)
                time.sleep(10)

            LOGGER.info("Configure Firewall")
            nd_obj.execute_cmd(cmd=
            common_cmd.CFG_FIREWALL.format(
                deploy_ff_cfg["firewall_url"]),
                read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Network Time Server")
            nd_obj.execute_cmd(cmd=common_cmd.CFG_NTP.format("UTC"), read_lines=True)
            time.sleep(10)

            LOGGER.info("Node Finalize")
            nd_obj.execute_cmd(cmd=common_cmd.NODE_PREP_FINALIZE, read_lines=True)
            time.sleep(10)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.field_deployment_node.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "field_deployment_node Successful!!"

    @staticmethod
    def cluster_definition(nd1_obj: Node, hostnames: str, build_url: str, timeout: int = 1800):
        """
        Cluster Definition
        param: nd1_obj : Object of node class for primary node
        param: hostnames: Space seperated String of hostnames for all nodes
        param: build_url: Build URL used for deployment
        param: timeout: timeout for command completion
        """
        try:
            LOGGER.info("Hostname : %s", hostnames)
            nd1_obj.connect(shell=True)
            channel = nd1_obj.shell_obj
            output = ""
            current_output = ""
            start_time = time.time()
            cmd = "".join(
                [common_cmd.CLUSTER_CREATE.format(hostnames, CMN_CFG["csm"]["mgmt_vip"], build_url),
                 "\n"])
            LOGGER.info("Command : %s", cmd)
            LOGGER.info("no of nodes: %s", len(CMN_CFG["nodes"]))
            channel.send(cmd)
            passwd_counter = 0
            while (time.time() - start_time) < timeout:
                time.sleep(30)
                if channel.recv_ready():
                    current_output = channel.recv(9999).decode("utf-8")
                    output = output + current_output
                    LOGGER.info(current_output)
                if "Enter root user password for srvnode" in current_output \
                        and passwd_counter < len(CMN_CFG["nodes"]):
                    pswd = "".join([CMN_CFG["nodes"][passwd_counter]["password"], "\n"])
                    channel.send(pswd)
                    passwd_counter += 1
                elif "cortx_setup command Failed" in output:
                    LOGGER.error(current_output)
                    break
                elif "Environment set up!" in output:
                    LOGGER.info("Cluster created")
                    break
            else:
                return False, "Cortx Definition Failed"

            if "cortx_setup command Failed" in output:
                return False, output
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.cluster_definition.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, output

    @staticmethod
    def define_storage_set(nd1_obj: Node, srvnames: str, storage_set_name: str,
                           deploy_config: ConfigParser):
        """
        Configure Storage Set
        param: nd1_obj: Primary node object
        param: srvnames: String of logical names for all nodes
        param: storage_set_name: Storage set name to be assigned
        param: deploy_config: Config.ini path
        """
        try:
            LOGGER.info("Create Storage Set")
            nd1_obj.execute_cmd(cmd=
            common_cmd.STORAGE_SET_CREATE.format(
                storage_set_name,
                len(CMN_CFG["nodes"])), read_lines=True)
            time.sleep(30)

            LOGGER.info("Add nodes to Storage Set")
            nd1_obj.execute_cmd(cmd=common_cmd.STORAGE_SET_ADD_NODE.format(
                storage_set_name, srvnames),
                read_lines=True)
            time.sleep(10)

            LOGGER.info("Add Enclosure to Storage Set")
            nd1_obj.execute_cmd(cmd=common_cmd.STORAGE_SET_ADD_ENCL.format(
                storage_set_name, srvnames),
                read_lines=True)
            time.sleep(10)

            LOGGER.info("Add Durability Config")
            for cfg_type in ["sns", "dix"]:
                data = deploy_config["srvnode_default"][f"storage.durability.{cfg_type}.data"]
                parity = deploy_config["srvnode_default"][f"storage.durability.{cfg_type}.parity"]
                spare = deploy_config["srvnode_default"][f"storage.durability.{cfg_type}.spare"]
                nd1_obj.execute_cmd(cmd=common_cmd.STORAGE_SET_CONFIG.format(
                    storage_set_name, cfg_type, data, parity,
                    spare),
                    read_lines=True)
                time.sleep(10)

        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.define_storage_set.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error

        return True, "define_storage_set Successful!!"

    @staticmethod
    def config_cluster(nd_obj1: Node) -> tuple:
        """
        This method deploys cortx and 3rd party software components on given VM setup
        :param nd_obj1: Host object of the primary node
        :return: True/False and deployment status
        """
        components = [
            "foundation",
            "iopath",
            "controlpath",
            "ha"]
        for comp in components:
            LOGGER.info("Deploying %s component", comp)
            try:
                nd_obj1.execute_cmd(
                    cmd=common_cmd.CLUSTER_CFG_COMP.format(comp), read_lines=True)
            except Exception as error:
                LOGGER.error(
                    "An error occurred in %s:",
                    ProvDeployFFLib.config_cluster.__name__)
                if isinstance(error.args[0], list):
                    LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
                else:
                    LOGGER.error(error.args[0])
                return False, error

        return True, "Deployment Completed"

    def field_deployment_cluster(self, nd1_obj: Node, hostnames: str, srvnodes: str,
                                 deploy_cfg: ConfigParser, build_url: str):
        """
        Create, configure and start the Cluster
        param: nd1_obj: Primary node object
        param: hostnames: Space separated hostnames of all node
        param: srvnodes: Space separated names of all node
        param: deploy_cfg: Config.ini file path
        param: build_url: Build to be deployed
        """
        try:
            deploy_ff_cfg = PROV_CFG["deploy_ff"]

            LOGGER.info("Cluster Definition")
            resp = self.cluster_definition(nd1_obj, hostnames, build_url)
            assert_utils.assert_true(resp[0], resp[1])
            time.sleep(10)

            LOGGER.info("Cluster Show")
            resp = nd1_obj.execute_cmd(cmd=common_cmd.CORTX_CLUSTER_SHOW,read_lines=True)
            time.sleep(10)
            LOGGER.debug("Resp: %s",resp)

            LOGGER.info("Define Storage Set")
            resp = self.define_storage_set(nd1_obj, srvnodes,
                                           deploy_ff_cfg["storage_set_name"], deploy_cfg)
            assert_utils.assert_true(resp[0], resp[1])
            time.sleep(10)

            LOGGER.info("Prepare Cluster")
            nd1_obj.execute_cmd(cmd=common_cmd.CLUSTER_PREPARE, read_lines=True)
            time.sleep(10)

            LOGGER.info("Configure Cluster")
            resp = self.config_cluster(nd1_obj)
            assert_utils.assert_true(resp[0], "Deploy Failed")
            time.sleep(10)

            LOGGER.info("Starting Cluster")
            resp = nd1_obj.execute_cmd(
                cmd=common_cmd.CMD_START_CLSTR,
                read_lines=True)[0].strip()
            assert_utils.assert_exact_string(resp, deploy_ff_cfg["cluster_start_msg"])
            time.sleep(deploy_ff_cfg["cluster_start_delay"])
            # LOGGER.info("START COMMAND : %s", resp)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.field_deployment_cluster.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error

        return True, "field_deployment_cluster Successful!!"

    @staticmethod
    def post_deploy_check(nd1_obj: Node):
        """
        Post deployment status checks
        param: nd1_obj: primary node object
        """
        try:
            resp = nd1_obj.execute_cmd(
                cmd=common_cmd.CMD_STATUS_CLSTR, read_lines=True)
            LOGGER.info("STATUS COMMAND : %s", resp)
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployFFLib.post_deploy_check.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error

        return True, "post_deploy_check Successful!!"

    @staticmethod
    def reset_deployment_check(nd1_obj: Node):
        resp = nd1_obj.execute_cmd(
            cmd=common_cmd.CLSTR_RESET_COMMAND, read_lines=True)
        LOGGER.info("Cluster Reset COMMAND : %s", resp)

    @staticmethod
    def reset_h_check(nd1_obj: Node):
        resp = nd1_obj.execute_cmd(
            cmd=common_cmd.CLSTR_RESET_H_COMMAND, read_lines=True)
        LOGGER.info("Cluster Reset COMMAND : %s", resp)

    @staticmethod
    def cluster_show(nd1_obj: Node):
        resp = nd1_obj.execute_cmd(
            cmd=common_cmd.CORTX_CLUSTER_SHOW, read_lines=True)
        LOGGER.info("Cluster Reset COMMAND : %s", resp)

    def deploy_3node_vm_ff(self, build, build_url, deploy_config_file):
        """
        Perform Deployment Using factory and field method
        param: deploy_config_file : Deployment config file (config.ini)
        """

        LOGGER.info("Starting Deployment with Build:\n %s", build_url)
        deploy_cfg = ConfigParser()
        deploy_cfg.read(deploy_config_file)

        node_list = []
        hostnames_list = []
        srvnodes_list = []

        for node in range(len(CMN_CFG["nodes"])):
            node_list.append(Node(hostname=CMN_CFG["nodes"][node]["hostname"],
                                  username=CMN_CFG["nodes"][node]["username"],
                                  password=CMN_CFG["nodes"][node]["password"]))
            hostnames_list.append(CMN_CFG["nodes"][node]["hostname"])
            srvnodes_list.append("srvnode-" + str(node + 1))
        nd1_obj = node_list[0]

        LOGGER.info("Starting Deployment on nodes:%s", hostnames_list)
        hostnames = " ".join(hostnames_list)
        srvnodes = " ".join(srvnodes_list)

        for nd_no, nd_obj in enumerate(node_list, start=1):
            resp = self.deployment_prereq(nd_obj)
            assert_utils.assert_true(resp[0], resp[1])

            resp = self.cortx_prepare(nd_obj, build, build_url)
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Perform Factory Manufacturing")
            resp = self.factory_manufacturing(nd_obj, nd_no, deploy_cfg["srvnode-" + str(nd_no)])
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Perform Field Deployment")
            resp = self.field_deployment_node(nd_obj, nd_no)
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Deploy Cluster")
        resp = self.field_deployment_cluster(nd1_obj, hostnames, srvnodes, deploy_cfg, build_url)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Starting the post deployment checks")
        resp = self.post_deploy_check(nd1_obj)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Deployment Successful!!")
        return True
