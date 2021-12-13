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
Python library contains methods which provides the services endpoints.
"""

import json
import logging
from config import CMN_CFG
from commons.utils import assert_utils
from commons.utils import system_utils
from commons import commands as common_cmd
from commons import constants as common_const
from commons.helpers.pods_helper import LogicalNode


log = logging.getLogger(__name__)

class MotrCoreK8s():
    
    def __init__(self):
        self.profile_fid = None
        self.cortx_node_list = None
        self.worker_node_list = []
        for node in range(len(CMN_CFG["nodes"])):
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                self.master_node = CMN_CFG["nodes"][node]["hostname"]
                self.node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            else:
                self.worker_node_list.append(CMN_CFG["nodes"][node]["hostname"])
        self.node_dict = self._get_cluster_info
        
    
    @property
    def _get_cluster_info(self):
        """
        Returns all the cortx nodes endpoints in a dict format
        """
        data_pod = self.node_obj.get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)[1]
        node_dict = {}
        if self.cortx_node_list is None:
            self.cortx_node_list = []
        response = self.node_obj.send_k8s_cmd(
            operation="exec", pod=data_pod, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME}"
            f" -- {common_cmd.HCTL_STATUS_CMD_JSON}",
            decode=True)
        cluster_info = json.loads(response)
        if cluster_info is not None:
            self.profile_fid = cluster_info["profiles"][0]["fid"]
            nodes_data = cluster_info["nodes"]
            for node in nodes_data:
                nodename = node["name"]
                self.cortx_node_list.append(nodename)
                node_dict[nodename] = {}
                node_dict[nodename]['m0client'] = []
                for svc in node["svcs"]:
                    if svc["name"] == "hax":
                        node_dict[nodename]['hax_fid'] = svc["fid"]
                        node_dict[nodename]['hax_ep'] = svc["ep"]
                    if svc["name"] == "m0_client":
                        node_dict[nodename]['m0client'].append({"ep":svc["ep"], "fid":svc["fid"]})
            return node_dict

    def get_data_pod_list(self):
        """
        Returns all the data pod names
        """
        cmd = "| awk '/cortx-data-pod/ {print $1}'"
        response = self.node_obj.send_k8s_cmd(
            operation="get", pod="pods", namespace=common_const.NAMESPACE,
            command_suffix=f"{cmd}", decode=True)
        return [node.strip() for node in response.split('\n')]

    def get_primary_cortx_node(self):
        """ 
        To get the primary cortx node name

        :returns: Primary(RC) node name in the cluster
        :rtype: str
        """
        data_pod = self.node_obj.get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)[1]
        cmd = " | awk -F ' '  '/(RC)/ { print $1 }'"
        primary_cortx_node = self.node_obj.send_k8s_cmd(
            operation="exec", pod=data_pod, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
            f"-- {common_cmd.MOTR_STATUS_CMD} {cmd}",
            decode=True)
        return primary_cortx_node

    def get_cortx_node_endpoints(self, cortx_node=None):
        """ 
        To get the endpoints details of the cortx node
        
        :param cortx_node: Name of the cortx node
        :type: str
        :returns: Dict of a cortx node containing the endpoints details
        :rtype: dict
        """
        if cortx_node:
            if cortx_node not in self.cortx_node_list:
                raise ValueError(
                    "Node must be one of %r." % str(self.cortx_node_list))
        else:
            cortx_node = self.get_primary_cortx_node()
        for node in self.node_dict.keys():
            if node == cortx_node:
                return self.node_dict[node]
        return None

    def get_number_of_m0clients(self, cluster_info_dic=None):
        """
        To get the number of m0clients in a node

        :param cluster_info_dic- Dictionray containing cluster info
        :type: dictionary
        :returns: Number of m0clients present in given node
        :rtype: integer
        """
        if cluster_info_dic == None:
           return len(self.node_dict[self.get_primary_cortx_node()]["m0client"])
        else:
           return len(cluster_info_dic[self.get_primary_cortx_node()]["m0client"])
        return None

    def m0crate_run(self, local_file_path, remote_file_path, cortx_node):
        """ To run the m0crate utility on specified cortx_node
        param: local_file_path: workload file(yaml) path on the client
        param: remote_file_path: workload file(yaml) path inside container
        param: cortx_node: Node where the m0crate utility will run
        """
        result = self.node_obj.copy_file_to_remote(local_file_path, remote_file_path)
        if result[0] is False:
            raise Exception("Copy from {} to {} failed with error: {}".format(local_file_path, remote_file_path, result[1]))
        m0crate_run_cmd = f'm0crate -S {remote_file_path}'
        result = self.node_obj.copy_file_to_container(remote_file_path, cortx_node, 
                    remote_file_path.rsplit("/", 1)[0],common_const.HAX_CONTAINER_NAME)
        if result[0] is False:
            raise Exception("Copy from {} to {} failed with error: {}".format(local_file_path,
                 common_const.HAX_CONTAINER_NAME, result[1]))
        cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(cortx_node, m0crate_run_cmd)
        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd,
                                                                      self.master_node,
                                                                      self.master_uname,
                                                                      self.master_passwd)
        log.info("%s , %s", result, error1)
        if ret:
            log.info('"%s" Failed, Please check the log', cmd)
            assert False
        if (b"ERROR" or b"Error") in error1:
            log.error('"%s" failed, please check the log', cmd)
            assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')
        
        
