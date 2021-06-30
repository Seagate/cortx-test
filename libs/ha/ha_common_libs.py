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
import logging
import time
from commons import commands as common_cmd
from commons.utils import system_utils
LOGGER = logging.getLogger(__name__)


class HALibs:
    """
    This class contains common utility methods for HA related operations.
    """

    @staticmethod
    def check_csm_service(node_object, srvnode_list, sys_list):
        """
        Helper function to know the node where CSM service is running.
        :param node_object: node object for the node to execute command
        :param srvnode_list: list of srvnode names
        :param sys_list: List of system objects
        :return: system_object
        """
        if len(srvnode_list) == 0 or len(sys_list) == 0:
            raise ValueError("srvnode_list or sys_list list is empty")
        res = node_object.execute_cmd(
            common_cmd.CMD_PCS_SERV.format("csm_agent"))
        data = str(res, 'UTF-8')
        for index, srvnode in enumerate(srvnode_list):
            if srvnode in data:
                LOGGER.info("CSM running on: {}".format(srvnode))
                sys_obj = sys_list[index]
                break
        return sys_obj

    @staticmethod
    def check_service_other_nodes(node_id, num_nodes, node_list):
        """
        Helper function to get services status on nodes which are online.
        :param node_id: node which is down to be skipped
        :param num_nodes: number of nodes in the cluster
        :param node_list: list of nodes in the cluster
        :return: boolean
        """
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

    @staticmethod
    def verify_node_health_status(
            response: list,
            status: str,
            node_id: int = None):
        """
        This method will verify node status with health show node command response
        :param response: List Response for health status command
        :param status: Expected status value for node
        :param node_id: Expected status value for specific node_id
        :return: bool, Response Message
        """
        if node_id:
            return response[node_id][2] == status.lower(), f"Node {node_id} is {response[node_id][2]}"

        for item in response:
            if item[2] != status.lower():
                return False, f"Node {item[1 + 1]} status is {item[2]}"
        return True, f"All node status are {status}"

    @staticmethod
    def polling_host(max_timeout: int, host_index: int, exp_resp: bool, host_list: list):
        """
        Helper function to poll for host ping response.
        :param max_timeout: Max timeout allowed for expected response from ping
        :param host_index: Host to ping
        :param exp_resp: Expected resp True/False for host state Reachable/Unreachable
        :param host_list: Host list for hosts in current cluster
        :return: bool
        """

        poll = time.time() + max_timeout  # max timeout
        while poll > time.time():
            time.sleep(20)
            resp = system_utils.check_ping(host_list[host_index])
            if resp == exp_resp:
                return True
        return False

    @staticmethod
    def get_iface_ip_list(node_list: list, num_nodes: int):
        """
        Helper function to get ip and intrefaces for private data network ports.
        :param node_list: List of nodes in cluster
        :param num_nodes: Number of nodes in cluster
        :return: interface list, ip list
        :rtype: list,list
        """
        iface_list = []
        private_ip_list = []
        LOGGER.info("Execute command to gte private data IPs for all nodes.")
        resp_ip = node_list[0].execute_cmd(common_cmd.CMD_HOSTS, read_lines=True)
        LOGGER.debug("Response for /etc/hosts: {}".format(resp_ip))
        for node in range(num_nodes):
            for line in resp_ip:
                if "srvnode-{}.data.private".format(node + 1) in line:
                    ip = line.split()[0]
                    private_ip_list.append(ip)
                    res = node_list[node].execute_cmd(common_cmd.CMD_IFACE_IP.format(ip),
                                                           read_lines=True)
                    ifname = res[0].replace(':', '')
                    iface_list.append(ifname)

        return iface_list, private_ip_list

