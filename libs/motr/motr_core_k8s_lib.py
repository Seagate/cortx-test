#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
Python library contains methods which provides the services endpoints.
"""

import json
import logging
import os
import time
from random import SystemRandom
from string import Template

from libs.motr import TEMP_PATH
from libs.motr import FILE_BLOCK_COUNT
from libs.motr.layouts import BSIZE_LAYOUT_MAP
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from config import CMN_CFG
from config import di_cfg
from commons import commands as common_cmd
from commons import constants as common_const
from commons.params import LOG_DIR, LATEST_LOG_FOLDER
from commons.utils import system_utils
from commons.utils import config_utils
from commons.utils import assert_utils
from commons.helpers.pods_helper import LogicalNode
from commons.helpers.health_helper import Health

log = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class MotrCoreK8s():
    """ Motr Kubernetes environment test library """

    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.profile_fid = None
        self.cortx_node_list = None
        self.master_node_list = []
        self.worker_node_list = []
        self.worker_node_objs = []
        for node in range(len(CMN_CFG["nodes"])):
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                self.master_node = CMN_CFG["nodes"][node]["hostname"]
                self.master_uname = CMN_CFG["nodes"][node]["username"]
                self.master_passwd = CMN_CFG["nodes"][node]["password"]
                self.node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                            username=CMN_CFG["nodes"][node]["username"],
                                            password=CMN_CFG["nodes"][node]["password"])
                self.master_node_list.append(self.node_obj)
                self.health_obj = Health(hostname=CMN_CFG["nodes"][node]["hostname"],
                                         username=CMN_CFG["nodes"][node]["username"],
                                         password=CMN_CFG["nodes"][node]["password"])
            else:
                self.worker_node_list.append(CMN_CFG["nodes"][node]["hostname"])
                self.worker_node_objs.append(LogicalNode(
                    hostname=CMN_CFG["nodes"][node]["hostname"],
                    username=CMN_CFG["nodes"][node]["username"],
                    password=CMN_CFG["nodes"][node]["password"]))
        self.node_dict = self._get_cluster_info
        self.node_pod_dict = self.get_node_pod_dict()
        self.ha_obj = HAK8s()
        self.dtm_obj = DTMRecoveryTestLib()


    @property
    def _get_cluster_info(self):
        """
        Returns all the cortx nodes endpoints in a dict format
        """
        motr_client_pod = self.node_obj.get_pod_name(
            pod_prefix=common_const.CLIENT_POD_NAME_PREFIX)[1]
        node_dict = {}
        if self.cortx_node_list is None:
            self.cortx_node_list = []
        response = self.node_obj.send_k8s_cmd(
            operation="exec", pod=motr_client_pod, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME}"
                           f" -- {common_cmd.HCTL_STATUS_CMD_JSON}",
            decode=True)
        cluster_info = json.loads(response)
        if cluster_info is not None:
            self.profile_fid = cluster_info["profiles"][0]["fid"]
            nodes_data = cluster_info["nodes"]
            for node in nodes_data:
                if 'client' in node['name']:
                    nodename = node["name"]
                    self.cortx_node_list.append(nodename)
                    node_dict[nodename] = {}
                    node_dict[nodename][common_const.MOTR_CLIENT] = []
                    for svc in node["svcs"]:
                        if svc["name"] == "hax":
                            node_dict[nodename]['hax_fid'] = svc["fid"]
                            node_dict[nodename]['hax_ep'] = svc["ep"]
                        if svc["name"] == common_const.MOTR_CLIENT:
                            node_dict[nodename][common_const.MOTR_CLIENT].append(
                                {"ep": svc["ep"], "fid": svc["fid"]})
        return node_dict

    def get_node_pod_dict(self):
        """
        Returns all the node and motr client pod names in dict format
        """
        node_pod_dict = self.get_pods_by_node()
        return node_pod_dict

    def get_pods_by_node(self, prefix=common_const.CLIENT_POD_NAME_PREFIX,
                         namespace=common_const.NAMESPACE):
        """Retrieves all pods by nodes with given pod name prefix."""
        node_pod_dict = {}
        cmd = "| grep \"{}\" |awk '{{print $1}}'".format(prefix)
        response = self.node_obj.send_k8s_cmd(
            operation="get", pod="pods", namespace=namespace,
            command_suffix=f"{cmd}", decode=True)
        pod_list = [node.strip() for node in response.split('\n')]
        for pod_name in pod_list:
            node_name = self.get_node_name_from_pod_name(pod_name)
            node_pod_dict[node_name] = pod_name
        return node_pod_dict

    def get_primary_cortx_node(self):
        """
        To get the primary cortx client node name

        :returns: Primary(RC) client node name in the cluster
        :rtype: str
        """
        motr_client_pod = self.node_obj.get_pod_name(
            pod_prefix=common_const.CLIENT_POD_NAME_PREFIX)[1]
        rc_node_cmd = " | awk -F ' '  '/(RC)/ { print $1 }'"
        primary_cortx_node = self.node_obj.send_k8s_cmd(
            operation="exec", pod=motr_client_pod, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                           f"-- {common_cmd.MOTR_STATUS_CMD} {rc_node_cmd}",
            decode=True)
        data_pod_name = primary_cortx_node.split('.')[0]
        k8_node_cmd = "| grep \"{}\" | awk '{{print $7}}'".format(data_pod_name)
        primary_k8s_node = self.node_obj.send_k8s_cmd(
            operation="get", pod="pods -o wide", namespace=common_const.NAMESPACE,
            command_suffix=f"{k8_node_cmd}", decode=True)
        client_pod_cmd = "| grep \"{}\" | awk '{{print $1}}' | grep \"{}\"".format(
            primary_k8s_node, common_const.CLIENT_POD_NAME_PREFIX)
        primary_client_pod = self.node_obj.send_k8s_cmd(
            operation="get", pod="pods -o wide", namespace=common_const.NAMESPACE,
            command_suffix=f"{client_pod_cmd}", decode=True)
        return primary_client_pod + '.' + common_const.CORTX_CLIENT_SVC_POSTFIX

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
        for key in self.node_dict:
            if key == cortx_node:
                return self.node_dict[key]
        return None

    def get_number_of_motr_clients(self):
        """
        To get the number of motr_clients in a node
        :returns: Number of motr_clients present in given node
        :rtype: integer
        """
        return len(self.node_dict[list(self.node_pod_dict.keys())[0]]["motr_client"])

    def get_node_name_from_pod_name(self, motr_client_pod):
        """
        To get Node name from Motr client_pod
        :param motr_client_pod: Name of the motr client pod
        :type: str
        :returns: Corresponding Node name
        :rtype: str
        """
        cmd = "hctl status  | grep {} | awk 'FNR <= 1'".format(motr_client_pod)
        node_name = self.node_obj.send_k8s_cmd(
            operation="exec", pod=motr_client_pod, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                           f"-- {cmd}",
            decode=True)
        return node_name.strip()

    def m0crate_run(self, local_file_path, remote_file_path, cortx_node):
        """
        To run the m0crate utility on specified cortx_node
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
        result = self.node_obj.copy_file_to_container(remote_file_path, pod_node,
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

        cmd = common_cmd.CREATE_FILE.format("/dev/urandom", file, b_size, count)  # nosec
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("DD Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    # pylint: disable=too-many-arguments
    def cp_cmd(self, b_size, count, obj, layout, file, node, client_num=None, di_g=False):
        """
        M0CP command creation

        :b_size: Block size
        :count: Block count
        :obj: Object ID
        :layout: Layout ID
        :file: Output file name
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on motr_client
        :di_g: DI mode flag
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        if di_g:
            cmd = Template(common_cmd.M0CP_G).substitute(
                ep=node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
                hax_ep=node_dict["hax_ep"],
                fid=node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
                prof_fid=self.profile_fid, bsize=b_size.lower(),
                count=count, obj=obj, layout=layout, file=file)
        else:
            cmd = common_cmd.M0CP.format(
                node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
                node_dict["hax_ep"],
                node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
                self.profile_fid, b_size.lower(),
                count, obj, layout, file)  # nosec
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("CP Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def cp_update_cmd(self, **kwargs):
        """
        M0CP update command with -G option which introduces corruption.

        :b_size: Block size
        :count: Block count
        :obj: Object ID
        :layout: Layout ID
        :file: Output file name
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on motr_client
        """
        b_size = kwargs.get('b_size')
        count = kwargs.get('count')
        obj = kwargs.get('obj')
        layout = kwargs.get('layout')
        file = kwargs.get('file')
        node = kwargs.get('node')
        offset = kwargs.get('offset')
        client_num = kwargs.get('client_num', None)
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        cmd = Template(common_cmd.M0CP_U_G).substitute(
            ep=node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
            hax_ep=node_dict["hax_ep"],
            fid=node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
            prof_fid=self.profile_fid, bsize=b_size.lower(),
            count=count, obj=obj, layout=layout, off=offset, file=file)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("CP Update Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    # pylint: disable=too-many-arguments
    def cat_cmd(self, b_size, count, obj, layout, file, node, client_num=None, di_g=False):
        """
        M0CAT command creation

        :b_size: Block size
        :count: Block count
        :obj: Object ID
        :layout: Layout ID
        :file: Output file name
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on motr_client
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        if di_g:
            cmd = common_cmd.M0CAT_G.format(
                node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
                node_dict["hax_ep"],
                node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
                self.profile_fid,
                b_size.lower(),
                count,
                obj,
                layout,
                file
            )
        else:
            cmd = common_cmd.M0CAT.format(
                node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
                node_dict["hax_ep"],
                node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
                self.profile_fid,
                b_size.lower(),
                count,
                obj,
                layout,
                file,
            )
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=False, exc=False)

        log.info("CAT Resp: %s", resp)
        if di_g:
            if b'-5' in resp:
                assert_utils.assert_in(b'Checksum validation failed for Obj',
                                       resp,f'"{cmd}" The m0cat operation failed'
                                       f' as expected for corrupt block')
            else:
                assert_utils.assert_not_in(b'ERROR' or b"Error", resp,
                                           f'"{cmd}" Failed, Please check the log')
        else:
            assert_utils.assert_not_in(b'ERROR' or b"Error", resp,
                                       f'"{cmd}" Failed, Please check the log')

    def unlink_cmd(self, obj, layout, node, client_num=None):
        """
        M0UNLINK command creation

        :obj: Object ID
        :layout: Layout ID
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on motr_client
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        cmd = common_cmd.M0UNLINK.format(node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
                                         node_dict["hax_ep"],
                                         node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
                                         self.profile_fid, obj, layout)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("UNLINK Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def diff_cmd(self, file1, file2, node):
        """
        DD command for creating new file

        :file1: first file
        :file2: second file
        :node: compare files on which node
        """
        diff_utils_install = common_cmd.CMD_INSTALL_TOOL.format("diffutils") + " -y"
        cmd = common_cmd.DIFF.format(file1, file2)
        cmd_list = [diff_utils_install, cmd]
        for cmd in cmd_list:
            resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                              namespace=common_const.NAMESPACE,
                                              command_suffix=
                                              f"-c {common_const.HAX_CONTAINER_NAME} "
                                              f"-- {cmd}", decode=True)
            log.info("DIFF Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def md5sum_cmd(self, file1, file2, node, **kwargs):
        """
        MD5SUM command creation

        :file1: first file
        :file2: second file
        :node: compare files on which node
        """
        flag = kwargs.get("flag", None)
        cmd = common_cmd.MD5SUM.format(file1, file2)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("MD5SUM Resp: %s", resp)
        chksum = resp.split()
        if flag:
            if chksum[0] != chksum[2]:
                log.info("Checksum is mismatched ")
            assert_utils.assert_not_equal(chksum[0], chksum[2],
                                          f'{cmd}, Checksum did not match')
        else:
            assert_utils.assert_equal(chksum[0], chksum[2], f'Failed {cmd}, Checksum did not match')

            assert_utils.assert_not_in("ERROR" or "Error", resp,
                                       f'"{cmd}" Failed, Please check the log')


    def get_md5sum(self, file, node):
        """
        Get MD5SUM of a file from hax container

        :param file: Absolute Path of the file inside hax container
        :param node: Cortx node where the file is present
        :returns: md5sum of the file
        :rtype: str
        """

        cmd = common_cmd.GET_MD5SUM.format(file)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("Resp: %s", resp)
        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')
        chksum = resp.split()[0]
        return chksum

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

    def kv_cmd(self, param, node, client_num=None):
        """
        M0KV command creation

        :param: Input Parameters
        :node: on which node m0cp cmd need to perform
        :client_num: perform operation on motr_client
        """
        if client_num is None:
            client_num = 0
        node_dict = self.get_cortx_node_endpoints(node)
        cmd = common_cmd.M0KV.format(node_dict[common_const.MOTR_CLIENT][client_num]["ep"],
                                     node_dict["hax_ep"],
                                     node_dict[common_const.MOTR_CLIENT][client_num]["fid"],
                                     self.profile_fid, param)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=self.node_pod_dict[node],
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)

        log.info("Resp: %s", resp)

        assert_utils.assert_not_in("ERROR" or "Error", resp,
                                   f'"{cmd}" Failed, Please check the log')

    def shutdown_cluster(self):
        """
        This will shutdown cluster and update the node_pod dict
        """
        resp = self.ha_obj.restart_cluster(self.node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        log.info("Cluster restarted fine and all Pods online.")
        # Updating the node_pod dict after cluster shutdown
        self.node_pod_dict = self.get_node_pod_dict()

    def switch_cluster_to_degraded_mode(self):
        """
        restart m0d container to reflect metadata change.
        Method is generic enough to kick m0d restart.
        :return:
        """
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            self.node_obj,
            self.health_obj)
        assert_utils.assert_true(resp[0], "Failed in shutdown or expected cluster check")
        log.info("Deleted pod : %s", list(resp[1].keys())[0])

    def restart_m0d_container(self, pod_prefix: str = common_const.POD_NAME_PREFIX,
                              container_prefix: str = common_const.MOTR_CONTAINER_PREFIX):
        """
        restart m0d container to reflect metadata change.
        Method is generic enough to kick m0d restart.
        :return:
        """
        pod_list = self.node_obj.get_all_pods(pod_prefix=pod_prefix)
        # prefer 0th pod and 0th container for running m0scripts
        pod = pod_list[0]
        containers = self.node_obj.get_container_of_pod(
            pod_name=pod, container_prefix=container_prefix)
        log.info("Perform restart of 0th M0d container")
        container = containers[0]
        resp = self.node_obj.restart_container_in_pod(
            pod_name=pod, container_name=container)
        self.log.debug("Container restarted with new PID: %s", resp)

    def update_m0crate_config(self, config_file, node):
        """
        This will modify the m0crate workload config yaml with the node details
        param: confile_file: Path of m0crate workload config yaml
        param: node: Cortx node on which m0crate utility to be executed
        """
        m0cfg = config_utils.read_yaml(config_file)[1]
        node_enpts = self.get_cortx_node_endpoints(node)
        # modify m0cfg and write back to file
        m0cfg['MOTR_CONFIG']['MOTR_HA_ADDR'] = node_enpts['hax_ep']
        m0cfg['MOTR_CONFIG']['PROF'] = self.profile_fid
        m0cfg['MOTR_CONFIG']['PROCESS_FID'] = node_enpts[common_const.MOTR_CLIENT][0]['fid']
        m0cfg['MOTR_CONFIG']['MOTR_LOCAL_ADDR'] = node_enpts[common_const.MOTR_CLIENT][0]['ep']
        b_size = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['BLOCK_SIZE']
        source_file = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['SOURCE_FILE']
        file_size = source_file.split('/')[-1]
        count = self.byte_conversion(file_size) // self.byte_conversion(b_size)
        self.dd_cmd(b_size.upper(), str(count), source_file, node)
        config_utils.write_yaml(config_file, m0cfg, backup=False, sort_keys=False)

    def run_motr_io(self, node, bsize_layout_map=BSIZE_LAYOUT_MAP, block_count=FILE_BLOCK_COUNT,
                    run_m0cat=True, delete_objs=True):
        """
        Run m0cp, m0cat and m0unlink on a node for all the motr clients and returns the objects
        :param: str node: Cortx node on which utilities to be executed
        :param: dict bsize_layout_map: mapping of block size and layout for IOs to run
        :param: list block_count: List containing the integer values. If block count is 1,
                then size of object file will vary from 4K to 32M,
                i.e multiple of supported object block sizes
        :param: bool run_m0cat: if True, will also run m0cat and compares the md5sum
        :param: bool delete_objs: if True, will delete the created objects
        :return: object dictionary containing objects block size, count, md5sum and delete flag
                {'10:20':{'block_size':'4k', 'deleted': False, 'count': 4,
                'md5sum': '2322f8a66f9eab2925e90182bad21dae'},
                '10:21':{'block_size':'8k', 'deleted': False, 'count': 2,
                'md5sum': 'bcf5e0570940a834455b6c5d449af5a7'}
                }
        :rtype: dict
        """
        object_dict = {}
        infile = TEMP_PATH + '/input'
        outfile = TEMP_PATH + '/output'
        try:
            for count in block_count:
                for b_size in bsize_layout_map.keys():
                    object_id = str(SystemRandom().randint(1, 9999)) + ":" + \
                                str(SystemRandom().randint(1, 9999))
                    object_dict[object_id] = {'block_size': b_size}
                    object_dict[object_id]['deleted'] = False
                    object_dict[object_id]['count'] = count
                    self.dd_cmd(b_size, str(count), infile, node)
                    self.cp_cmd(b_size, str(count), object_id, bsize_layout_map[b_size],
                                infile, node)
                    if run_m0cat:
                        self.cat_cmd(b_size, str(count), object_id,
                                     bsize_layout_map[b_size], outfile, node)
                        md5sum = self.get_md5sum(outfile, node)
                        object_dict[object_id]['md5sum'] = md5sum
                        self.md5sum_cmd(infile, outfile, node)
                    if delete_objs:
                        self.unlink_cmd(object_id, bsize_layout_map[b_size], node)
                        object_dict[object_id]['deleted'] = True
            return object_dict
        except Exception as exc:
            log.exception("Test has failed with execption: %s", exc)
            raise exc

    def run_io_in_parallel(self, node, bsize_layout_map=BSIZE_LAYOUT_MAP,
                           block_count=FILE_BLOCK_COUNT, run_m0cat=True, delete_objs=True,
                           return_dict=None):
        """
        :param: str node: Cortx node on which utilities to be executed
        :param: dict bsize_layout_map: mapping of block size and layout for IOs to run
        :param: list block_count: List containing the integer values. If block count is 1,
                then size of object file will vary from 4K to 32M,
                i.e multiple of supported object block sizes
        :param: bool run_m0cat: if True, will also run m0cat and compares the md5sum
        :param: bool delete_objs: if True, will delete the created objects
        :param: dict return_dict: contains the return value from for node
        """
        if return_dict is None:
            return_dict = {}
        try:
            obj_dict = self.run_motr_io(node, bsize_layout_map, block_count, run_m0cat, delete_objs)
            return_dict[node] = obj_dict
            return return_dict
        except (OSError, AssertionError, IOError) as exc:
            return_dict[node] = exc
            return return_dict

    def run_m0crate_in_parallel(self, local_file_path, remote_file_path,
                                cortx_node, return_dict=None):
        """
        Run motr m0crate in parallel using this function with the help of multiprocessing
        :param: str local_file_path: Absolute workload file(yaml) path on the client
        :param: str remote_file_path: Absolute workload file(yaml) path on the master node
        :param: str cortx_node: Node where the m0crate utility will run
        :param: dict return_dict: contains the return value from for node
        """
        if return_dict is None:
            return_dict = {}
        try:
            self.m0crate_run(local_file_path, remote_file_path, cortx_node)
            return return_dict
        except (OSError, AssertionError, IOError) as exc:
            return_dict[cortx_node] = exc
            return return_dict

    def close_connections(self):
        """Close connections to target nodes."""
        if CMN_CFG["product_family"] in ('LR', 'LC') and \
                CMN_CFG["product_type"] == 'K8S':
            for conn in self.master_node_list + self.worker_node_list:
                if isinstance(conn, LogicalNode):
                    conn.disconnect()

    def dump_m0trace_log(self, filepath, node):
        """ This method is used to parse the m0trace logs on all the data pods,
        filepath: m0trace log path
        node: client pod
        """
        list_trace = common_cmd.LIST_M0TRACE
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=str(self.node_pod_dict[node]),
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {list_trace}", decode=True)
        latest_trace_file = resp.split("\n")[-1]
        log.debug("Resp: %s", latest_trace_file)
        cmd = Template(common_cmd.M0TRACE).substitute(trace=latest_trace_file, file=filepath)
        resp = self.node_obj.send_k8s_cmd(operation="exec", pod=str(self.node_pod_dict[node]),
                                          namespace=common_const.NAMESPACE,
                                          command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                                         f"-- {cmd}", decode=True)
        log.info("Resp of trace: %s", resp)
        return filepath

    def read_m0trace_log(self, filepath):
        """
        This method reads the log and fetch tfid belongs to DATA and PARITY block
        returns dict of tfid with DATA and PARITY.
        """
        tfid_list = []
        checksum_dict = {}
        data_blk = 0
        parity_blk = 0
        local_path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER, filepath)
        self.master_node_list[0].copy_file_to_local(filepath, local_path)
        cmd = Template(common_cmd.GREP_DP_BLOCK_FID).substitute(file=filepath)
        resp = self.master_node_list[0].execute_cmd(cmd, read_lines=True)
        log.debug("output of m0trace utility %s", resp)
        lines = str(resp).split("\\n")
        for line in lines:
            if "tfid" in line:
                tfid_list.append(line)  # append the target fid in the list.
            if '[P]' in line:
                if tfid_list:
                    tfid = tfid_list.pop()
                    tfid = tfid.split(" ")
                    fid = tfid[-1][1:-1]  # fetch target fid and strip the <>
                    dict_schema = {"PARITY"+str(parity_blk): fid}  # create dictionary
                    checksum_dict.update(dict_schema)
                    parity_blk=parity_blk+1
            if "[D]" in line:
                if tfid_list:
                    tfid = tfid_list.pop()
                    tfid = tfid.split(" ")
                    fid = tfid[-1][1:-1]  # fetch target fid and strip the <>
                    dict_schema = {"DATA"+str(data_blk): fid}  # create dictionary
                    checksum_dict.update(dict_schema)
                    data_blk=data_blk+1
        log.debug("DICT is %s", checksum_dict)
        return checksum_dict

    def switch_to_degraded_mode(self):
        """
        This method kill's m0d process and make setup to degraded mode
        returns boolean True and pod and container on which m0d was killed
        """
        process = common_const.PID_WATCH_LIST[0]
        pod_selected, container = self.master_node_list[0].select_random_pod_container(
            common_const.POD_NAME_PREFIX, common_const.MOTR_CONTAINER_PREFIX)
        self.dtm_obj.set_proc_restart_duration(
            self.master_node_list[0], pod_selected, container, di_cfg['wait_time_m0d_restart'])
        try:
            log.info("Kill %s from %s pod %s container ", process, pod_selected, container)
            resp = self.master_node_list[0].kill_process_in_container(pod_name=pod_selected,
                                                                      container_name=container,
                                                                      process_name=process)
            log.debug("Resp : %s", resp)
            time.sleep(5)
            return True, pod_selected, container
        except (ValueError, IOError) as ex:
            log.error("Exception Occurred during killing process : %s", ex)
            self.dtm_obj.set_proc_restart_duration(self.master_node_list[0],
                                                   pod_selected, container, 0)
            return False, pod_selected, container
