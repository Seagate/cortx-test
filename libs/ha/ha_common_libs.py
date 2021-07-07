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
HA utility methods
"""
import os
import logging
import time
from commons import commands as common_cmd
from commons.utils import system_utils
from commons.exceptions import CTException
from commons import errorcodes as err
from commons import pswdmanager
from commons.constants import Rest as Const
from config import CMN_CFG, HA_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
LOGGER = logging.getLogger(__name__)


class HALibs:
    """
    This class contains common utility methods for HA related operations.
    """

    def __init__(self):
        self.system_health = SystemHealth()
        self.setup_type = CMN_CFG["setup_type"]
        self.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        self.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        self.bmc_user = CMN_CFG["bmc"]["username"]
        self.bmc_pwd = CMN_CFG["bmc"]["password"]
        self.t_power_on = HA_CFG["common_params"]["power_on_time"]
        self.t_power_off = HA_CFG["common_params"]["power_off_time"]

    @staticmethod
    def check_csm_service(node_object, srvnode_list, sys_list):
        """
        Helper function to know the node where CSM service is running.
        :param node_object: node object for the node to execute command
        :param srvnode_list: list of srvnode names
        :param sys_list: List of system objects
        :return: boolean, system_object/error
        """
        try:
            if len(srvnode_list) == 0 or len(sys_list) == 0:
                raise ValueError("srvnode_list or sys_list list is empty")
            res = node_object.execute_cmd(
                common_cmd.CMD_PCS_SERV.format("csm_agent"))
            data = str(res, 'UTF-8')
            for index, srvnode in enumerate(srvnode_list):
                if srvnode in data:
                    LOGGER.info("CSM running on: {}".format(srvnode))
                    sys_obj = sys_list[index]
                    return True, sys_obj
        except IOError as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.check_csm_service.__name__,
                         error)
            return False, error

    @staticmethod
    def check_service_other_nodes(node_id, num_nodes, node_list):
        """
        Helper function to get services status on nodes which are online.
        :param node_id: node which is down to be skipped
        :param num_nodes: number of nodes in the cluster
        :param node_list: list of nodes in the cluster
        :return: boolean
        """
        try:
            for node in range(num_nodes):
                if node != node_id:
                    node_name = "srvnode-{}".format(node + 1)
                    LOGGER.info("Checking services on: {}".format(node_name))
                    res = node_list[node].execute_cmd(
                        common_cmd.CMD_PCS_GREP.format(node_name))
                    data = str(res, 'UTF-8')
                    for line in data:
                        if "FAILED" in line or "Stopped" in line:
                            return False
            return True
        except IOError as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.check_service_other_nodes.__name__,
                         error)
            return False

    @staticmethod
    def verify_node_health_status(
            sys_obj,
            status: list):
        """
        This method will verify node status with health show node command response
        :param sys_obj: System object
        :param status: Expected status value for node
        :return: bool, Response Message
        """
        try:
            sys_obj.open_connection()
            sys_obj.login_cortx_cli()
            resp = sys_obj.check_health_status(
                common_cmd.CMD_HEALTH_SHOW.format("node"))
            if not resp[0]:
                raise ValueError("Failed to get node health ")
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for health check for all nodes: %s",
                resp_table)
            for index, item in enumerate(resp_table):
                if item[2] != status[index].lower():
                    return False, f"Node-{int(item[1])+1}'s health status is {item[2]}"
                LOGGER.info("Node-%s's health status is %s",
                            int(item[1]) + 1, item[2])
            return True, "All node status is as expected"
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.verify_node_health_status.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error
        finally:
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection()

    @staticmethod
    def verify_csr_health_status(
            sys_obj,
            status: str):
        """
        This method will Get and verify cluster, site and rack status with health show
        cluster command response
        :param sys_obj: System object
        :param status: Expected status for cluster, site and rack
        :return: bool, Response Message
        """
        try:
            sys_obj.open_connection()
            sys_obj.login_cortx_cli()
            resp = sys_obj.check_health_status(
                common_cmd.CMD_HEALTH_SHOW.format("cluster"))
            if not resp[0]:
                raise ValueError("Failed to get cluster health ")
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for health check for all nodes: %s",
                resp_table)
            for item in resp_table[:3]:
                if item[2] != status.lower():
                    return False, f"{item[0]}'s health status is {item[2]}"
                LOGGER.info("%s's health status is %s", item[0], item[2])
            return True, "Cluster, site and rack health status is as expected"
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.verify_csr_health_status.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error
        finally:
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection()

    @staticmethod
    def polling_host(
            max_timeout: int,
            host: str,
            exp_resp: bool):
        """
        Helper function to poll for host ping response.
        :param max_timeout: Max timeout allowed for expected response from ping
        :param host: Host to ping
        :param exp_resp: Expected resp True/False for host state Reachable/Unreachable
        :return: bool
        """

        poll = time.time() + max_timeout  # max timeout
        while poll > time.time():
            time.sleep(20)
            resp = system_utils.check_ping(host)
            if resp == exp_resp:
                return True
        return False

    @staticmethod
    def get_iface_ip_list(node_list: list, num_nodes: int):
        """
        Helper function to get ip and interfaces for private data network ports.
        :param node_list: List of nodes in cluster
        :param num_nodes: Number of nodes in cluster
        :return: interface list, ip list
        :rtype: list,list
        """
        try:
            iface_list = []
            private_ip_list = []
            LOGGER.info(
                "Execute command to gte private data IPs for all nodes.")
            resp_ip = node_list[0].execute_cmd(
                common_cmd.CMD_HOSTS, read_lines=True)
            LOGGER.debug("Response for /etc/hosts: {}".format(resp_ip))
            for node in range(num_nodes):
                for line in resp_ip:
                    if "srvnode-{}.data.private".format(node + 1) in line:
                        ip = line.split()[0]
                        private_ip_list.append(ip)
                        res = node_list[node].execute_cmd(
                            common_cmd.CMD_IFACE_IP.format(ip), read_lines=True)
                        ifname = res[0].replace(':', '')
                        iface_list.append(ifname)

            return iface_list, private_ip_list
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.get_iface_ip_list.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error

    def host_power_on(self, host: str, bmc_obj=None):
        """
        Helper function for host power on
        :param host: Host to be power on
        :param bmc_obj: BMC object
        :rtype: boolean from polling_host() response
        """

        if self.setup_type == "VM":
            vm_name = host.split(".")[0]
            resp = system_utils.execute_cmd(
                common_cmd.CMD_VM_POWER_ON.format(
                    self.vm_username, self.vm_password, vm_name))
            if not resp[0]:
                raise CTException(err.CLI_COMMAND_FAILURE, msg=f"VM power on command not executed")
        else:
            bmc_obj.bmc_node_power_on_off(bmc_obj.get_bmc_ip(), self.bmc_user, self.bmc_pwd, "on")

        LOGGER.info("Check if %s is powered on.", host)
        # SSC cloud is taking time to on VM host hence timeout
        resp = self.polling_host(max_timeout=self.t_power_on, host=host, exp_resp=True)
        return resp

    def host_safe_unsafe_power_off(self, host: str, bmc_obj=None, node_obj=None, is_safe: bool = False):
        """
        Helper function for safe/unsafe host power off
        :param host: Host to be power off
        :param bmc_obj: BMC object
        :param node_obj: Node object
        :param is_safe: Power off host with safe/unsafe shutdown
        :rtype: boolean from polling_host() response
        """
        if is_safe:
            resp = node_obj.execute_cmd(cmd="shutdown now", exc=False)
            LOGGER.debug("Response for shutdown: {}".format(resp))
        else:
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                if not resp[0]:
                    raise CTException(err.CLI_COMMAND_FAILURE, msg=f"VM power off command not executed")
            else:
                bmc_obj.bmc_node_power_on_off(bmc_obj.get_bmc_ip(), self.bmc_user, self.bmc_pwd, "off")

        LOGGER.info("Check if %s is powered off.", host)
        # SSC cloud is taking time to off VM host hence timeout
        resp = self.polling_host(
            max_timeout=self.t_power_off, host=host, exp_resp=False)
        return resp

    def status_nodes_online(self, node_obj, srvnode_list, sys_list, no_nodes: int):
        """
        Helper function to check that all nodes are shown online in cortx cli/REST
        :param node_obj: Node object to execute command
        :param srvnode_list: List of srvnode names
        :param sys_list: List of system objects
        :param no_nodes: Number of nodes in system
        :rtype: None
        """
        try:
            LOGGER.info("Get the node which is running CSM service.")
            resp = self.check_csm_service(node_obj, srvnode_list, sys_list)
            if not resp[0]:
                raise CTException(err.CLI_COMMAND_FAILURE, resp[1])

            sys_obj = resp[1]
            LOGGER.info("Check all nodes health status is online in CLI and REST")
            check_rem_node = ["online" for _ in range(no_nodes)]
            cli_resp = self.verify_node_health_status(
                sys_obj, status=check_rem_node)
            if not cli_resp[0]:
                raise CTException(err.HA_BAD_NODE_HEALTH, cli_resp[1])
            LOGGER.info("CLI response for nodes health status. %s", cli_resp[1])
            rest_resp = self.system_health.verify_node_health_status_rest(exp_status=check_rem_node)
            if not rest_resp[0]:
                raise CTException(err.HA_BAD_NODE_HEALTH, rest_resp[1])
            LOGGER.info("REST response for nodes health status. %s", rest_resp[1])
        except Exception as error:
            LOGGER.error("%s %s: %s",
                     Const.EXCEPTION_ERROR,
                     HALibs.status_nodes_online.__name__,
                     error)
