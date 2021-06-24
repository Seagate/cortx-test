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
from commons import commands as common_cmd

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
        :param sys_list: Llst of system objects
        :return: system_object
        """
        res = node_object.execute_cmd(common_cmd.CMD_PCS_SERV.format("csm_agent"))
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
                node_name = "srvnode-{}".format(node+1)
                LOGGER.info("Checking services on: {}".format(node_name))
                res = node_list[node].execute_cmd(common_cmd.CMD_PCS_GREP.format(node_name))
                data = str(res, 'UTF-8')
                for line in data:
                    if "FAILED" in line or "Stopped" in line:
                        return False
        return True
