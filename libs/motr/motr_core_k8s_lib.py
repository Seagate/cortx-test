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
                self.master_uname = CMN_CFG["nodes"][node]["username"]
                self.master_passwd = CMN_CFG["nodes"][node]["password"]
                self.node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                            username=CMN_CFG["nodes"][node]["username"],
                                            password=CMN_CFG["nodes"][node]["password"])
            else:
                self.worker_node_list.append(CMN_CFG["nodes"][node]["hostname"])
        self.node_dict = self._get_cluster_info
        self.node_pod_dict = self.get_node_pod_dict()

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
                if 'data' in node['name']:
                    nodename = node["name"]
                    self.cortx_node_list.append(nodename)
                    node_dict[nodename] = {}
                    node_dict[nodename]['m0client'] = []
                    for svc in node["svcs"]:
                        if svc["name"] == "hax":
                            node_dict[nodename]['hax_fid'] = svc["fid"]
                            node_dict[nodename]['hax_ep'] = svc["ep"]
                        if svc["name"] == "m0_client":
                            node_dict[nodename]['m0client'].append({"ep": svc["ep"], "fid": svc["fid"]})
            return node_dict

    def get_node_pod_dict(self):
        """
        Returns all the node and data pod names in dict format
        """
        node_pod_dict = {}
        cmd = "| awk '/cortx-data/ {print $1}'"
        response = self.node_obj.send_k8s_cmd(
            operation="get", pod="pods", namespace=common_const.NAMESPACE,
            command_suffix=f"{cmd}", decode=True)
        pod_list = [node.strip() for node in response.split('\n')]
        for pod_name in pod_list:
            node_name = self.get_node_name_from_pod_name(pod_name)
            node_pod_dict[node_name] = pod_name
        return node_pod_dict

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
        if cluster_info_dic is None:
            return len(self.node_dict[self.get_primary_cortx_node()]["m0client"])
        else:
            return len(cluster_info_dic[self.get_primary_cortx_node()]["m0client"])

    def get_node_name_from_pod_name(self, data_pod=None):
        """
        To get Node name from data_pod

        :param data_pod: Name of the data pod
        :type: str
        :returns: Corresponding Node name
        :rtype: str
        """
        cmd = "hostname"
        node_name = self.node_obj.send_k8s_cmd(
            operation="exec", pod=data_pod, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                           f"-- {cmd}",
            decode=True)
        return node_name

    def m0crate_run(self, local_file_path, remote_file_path, cortx_node):
        """ To run the m0crate utility on specified cortx_node
        param: local_file_path: Absolute workload file(yaml) path on the client
        param: remote_file_path: Absolute workload file(yaml) path on the master node
        param: cortx_node: Node where the m0crate utility will run
        """
        pod_node = self.get_node_pod_dict()[cortx_node]
        result = self.node_obj.copy_file_to_remote(local_file_path, remote_file_path)
        if not result[0]:
            raise Exception("Copy from {} to {} failed with error: {}".format(local_file_path,
                                                                              remote_file_path,
                                                                              result[1]))
        m0crate_run_cmd = f'm0crate -S {remote_file_path}'
        result = self.node_obj.copy_file_to_container(remote_file_path, pod_node, \
                                                      remote_file_path,
                                                      common_const.HAX_CONTAINER_NAME)
        log.info(result)
        if not result[0]:
            raise Exception("Copy from {} to {} failed with error: \
                             {}".format(local_file_path, common_const.HAX_CONTAINER_NAME,
                                        result[1]))
        cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(pod_node, m0crate_run_cmd)
        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd,
                                                                      self.master_node,
                                                                      self.master_uname,
                                                                      self.master_passwd)
        log.info("%s , %s", result, error1)
        if ret:
            assert False, "Failed with return code {}, Please check the logs".format(ret)
        assert not any((error_str in error1.decode("utf-8") for error_str in
            ['error', 'ERROR', 'Error'])), "Errors found in output {}".format(error1)

    def dd_cmd(self, b_size, count, file, node):
        """
        DD command for creating new file

        :b_size: Block size
        :count: Block count
        :file: Output file name
        :node: on which node file need to create
        """

        cmd = common_cmd.CREATE_FILE.format("/dev/urandom", file, b_size, count)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    # pylint: disable=too-many-arguments
    def cp_cmd(self, b_size, count, obj, layout, file, node, client_num):
        """
        M0CP command creation

        :b_size: Block size
        :count: Block count
        :obj: Object ID
        :layout: Layout ID
        :file: Output file name
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on m0client
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        cmd = common_cmd.M0CP.format(node_dict["m0client"][client_num]["ep"],
                                     node_dict["hax_ep"],
                                     node_dict["m0client"][client_num]["fid"],
                                     self.profile_fid, b_size.lower(),
                                     count, obj, layout, file)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    # pylint: disable=too-many-arguments
    def cat_cmd(self, b_size, count, obj, layout, file, node, client_num):
        """
        M0CAT command creation

        :b_size: Block size
        :count: Block count
        :obj: Object ID
        :layout: Layout ID
        :file: Output file name
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on m0client
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        cmd = common_cmd.M0CAT.format(node_dict["m0client"][client_num]["ep"],
                                      node_dict["hax_ep"],
                                      node_dict["m0client"][client_num]["fid"],
                                      self.profile_fid, b_size.lower(),
                                      count, obj, layout, file)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def unlink_cmd(self, obj, layout, node, client_num):
        """
        M0UNLINK command creation

        :obj: Object ID
        :layout: Layout ID
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on m0client
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        cmd = common_cmd.M0UNLINK.format(node_dict["m0client"][client_num]["ep"],
                                         node_dict["hax_ep"],
                                         node_dict["m0client"][client_num]["fid"],
                                         self.profile_fid, obj, layout)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def diff_cmd(self, file1, file2, node):
        """
        DD command for creating new file

        :file1: first file
        :file2: second file
        :node: compare files on which node
        """

        cmd = common_cmd.DIFF.format(file1, file2)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def md5sum_cmd(self, file1, file2, node):
        """
        MD5SUM command creation

        :file1: first file
        :file2: second file
        :node: compare files on which node
        """

        cmd = common_cmd.MD5SUM.format(file1, file2)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("Resp: %s", resp)
        chksum = resp.split()
        assert_utils.assert_equal(chksum[0], chksum[2], f'Failed {cmd}, Checksum did not match')

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def verify_libfabric_version(self):
        """TO check libfabric version and protocol status"""
        for node in self.node_pod_dict:
            log.info('Checking libfabric rpm')
            cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(self.node_pod_dict[node],
                                                            common_cmd.GETRPM.format("libfab"))
            result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.master_node,
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
            log.info('Checking libfabric version')
            cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(self.node_pod_dict[node],
                                                            common_cmd.LIBFAB_VERSION)     
            result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.master_node,
                                                                          self.master_uname,
                                                                          self.master_passwd)         
            if ret:
                log.info('"%s" Failed, Please check the log', cmd)
                assert False
            if (b"ERROR" or b"Error") in error1:
                log.error('"%s" failed, please check the log', cmd)
                assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                           f'"{cmd}" Failed, Please check the log')
            log.info('Checking libfabric tcp protocol presence')
            cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(self.node_pod_dict[node],
                                                            common_cmd.LIBFAB_TCP)                                    
            result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.master_node,
                                                                          self.master_uname,
                                                                          self.master_passwd)                                                  
            if ret:
                log.info('"%s" Failed, Please check the log', cmd)
                assert False
            if (b"ERROR" or b"Error") in error1:
                log.error('"%s" failed, please check the log', cmd)
                assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                           f'"{cmd}" Failed, Please check the log')
            log.info('Checking libfabric socket protocol presence')
            cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(self.node_pod_dict[node], 
                                                            common_cmd.LIBFAB_SOCKET)                                       
            result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.master_node,
                                                                          self.master_uname,
                                                                          self.master_passwd)		
            if ret:
                log.info('"%s" Failed, Please check the log', cmd)
                assert False
            if (b"ERROR" or b"Error") in error1:
                log.error('"%s" failed, please check the log', cmd)
                assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')
            # Below support verbs for HW is removed from libfabrc code as of now.
            # ...Commenting the same
            """
            log.info('Checking libfabric verbs protocol presence')
            if CMN_CFG["setup_type"] == "HW":
                cmd = common_cmd.K8S_POD_INTERACTIVE_CMD.format(self.node_pod_dict[node],
                                                                common_cmd.LIBFAB_VERBS)                                       
                result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.master_node,
                                                                              self.master_uname,
                                                                              self.master_passwd)                                                           
                if ret:
                    log.info('"%s" Failed, Please check the log', cmd)
                    assert False
                if (b"ERROR" or b"Error") in error1:
                    log.error('"%s" failed, please check the log', cmd)
                    assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')
            """

    @staticmethod
    def byte_conversion(size):
        """ Convert file size of GB/MB/KB into bytes
        :param: size: size of the file in either G, M or K i.e 2G, 1m
        :return: size in bytes
        """
        suffix = ['G', 'M', 'K']
        if size[-1].upper() not in suffix:
            assert_utils.assert_in(size[-1], suffix,
                                   'invalid size')
        if size[-1].upper() == 'G':
            size = int(size[0: -1]) * 1024 * 1024 * 1024
        elif size[-1].upper() == 'M':
            size = int(size[0: -1]) * 1024 * 1024
        elif size[-1].upper() == 'K':
            size = int(size[0: -1]) * 1024
        return size
