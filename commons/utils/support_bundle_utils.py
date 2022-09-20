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
Module to maintain support bundle utils
"""

import os
import logging
import time
from commons.helpers.node_helper import Node
from commons.helpers.pods_helper import LogicalNode
from commons import commands as cm_cmd
from commons import constants as cm_const
from commons.utils import assert_utils
from config import CMN_CFG

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-arguments
def create_support_bundle_individual_cmd(node, username, password, remote_dir, local_dir, component="all"):
    """
    Collect support bundles from various components
    :param node: Node hostname on which support bundle to be generated
    :param username: username of the node
    :param password: password of the node
    :param component: component to create support bundle, default creates for all components
    :param remote_dir: Directory on node where support bundles will be collected
    :param local_dir: Local directory where support bundles will be copied
    :return: True/False and local sb path
    """
    node_obj = Node(hostname=node, username=username, password=password)
    if node_obj.path_exists(remote_dir):
        node_obj.remove_dir(remote_dir)
    node_obj.create_dir_sftp(remote_dir)
    sb_cmds = {"sspl": "/usr/bin/sspl_bundle_generate support_bundle {}",
               "s3": "sh /opt/seagate/cortx/s3/scripts/s3_bundle_generate.sh support_bundle {}",
               "manifest": "/usr/bin/manifest_support_bundle support_bundle {}",
               "hare": "/opt/seagate/cortx/hare/bin/hare_setup support_bundle support_bundle {}",
               "provisioner": "/opt/seagate/cortx/provisioner/cli/provisioner-bundler support_bundle {}",
               "cortx": "cortx support_bundle create support_bundle {}",
               "csm": "cortxcli csm_bundle_generate csm support_bundle {}"
               }

    if component == "all":
        for comp, cmd in sb_cmds.items():
            LOGGER.info("Generating support bundle for %s component on node %s", comp, node)
            node_obj.execute_cmd(cmd.format(remote_dir))
    elif component in sb_cmds:
        LOGGER.info("Generating support bundle for %s component on node %s", component, node)
        node_obj.execute_cmd(sb_cmds[component].format(remote_dir))
    else:
        return False, "Invalid Component"

    LOGGER.info("Copying generated support bundle to local")
    sb_tar_file = "".join([os.path.basename(remote_dir), ".tar"])
    remote_sb_path = os.path.join(os.path.dirname(remote_dir), sb_tar_file)
    local_sb_path = os.path.join(local_dir, sb_tar_file)
    tar_sb_cmd = "tar -cvf {} {}".format(remote_sb_path, remote_dir)
    node_obj.execute_cmd(tar_sb_cmd)
    LOGGER.debug("Copying %s to %s", remote_sb_path, local_sb_path)
    node_obj.copy_file_to_local(remote_sb_path, local_sb_path)

    return True, local_sb_path


# pylint: disable=max-args
# pylint: disable-msg=too-many-statements
# pylint: disable-msg=too-many-locals
def create_support_bundle_single_cmd(local_dir, bundle_name, comp_list=None,
                                     size=None, services=None):
    """
    Collect support bundles from various components using single support bundle cmd
    :param local_dir: Local directory where support bundles will be copied
    :param bundle_name: Name of bundle
    :param comp_list: List of components for SB collection
    :return: boolean
    """
    remote_dir = cm_const.R2_SUPPORT_BUNDLE_PATH
    node_list = []
    num_nodes = len(CMN_CFG["nodes"])
    for node in range(num_nodes):
        host = CMN_CFG["nodes"][node]["hostname"]
        uname = CMN_CFG["nodes"][node]["username"]
        passwd = CMN_CFG["nodes"][node]["password"]
        node_list.append(Node(hostname=host,
                              username=uname, password=passwd))
    for node in range(num_nodes):
        if node_list[node].path_exists(remote_dir):
            node_list[node].remove_dir(remote_dir)
    LOGGER.info("Checking for available space before generating SB.")
    for node in range(num_nodes):
        res = node_list[node].execute_cmd(cmd=cm_cmd.CMD_SPACE_CHK)
        res = res.decode("utf-8")
        LOGGER.info("Available space on srvnode %s : %s", node, res)
    LOGGER.info("Starting support bundle creation")
    command = " ".join([cm_cmd.R2_CMD_GENERATE_SUPPORT_BUNDLE, bundle_name])
    # Form the command if component list, size, services  is provided in parameters
    if comp_list is not None:
        command = command + ''.join(" -c ")
        command = command + ''.join(comp_list)
    if size is not None:
        command = command + ''.join(" --size_limit ")
        command = command + ''.join(size)
    if services is not None:
        command = command + ''.join(" --modules ")
        command = command + ''.join(services)
    resp = node_list[0].execute_cmd(cmd=command)
    LOGGER.debug("Response for support bundle generate: {}".format(resp))
    assert_utils.assert_true(resp[0], resp[1])
    start_time = time.time()
    timeout = 2700
    bundle_id = node_list[0].list_dir(remote_dir)[0]
    LOGGER.info(bundle_id)
    bundle_dir = os.path.join(remote_dir, bundle_id)
    success_msg = "Support bundle generation completed."
    while timeout > time.time() - start_time:
        time.sleep(180)
        LOGGER.info("Checking Support Bundle status")
        status = node_list[0].execute_cmd(
            "support_bundle get_status -b {}".format(bundle_id))
        LOGGER.info(status)
        if 'Success' in str(status):
            LOGGER.info("Support Bundle status Validated")
        if str(status).count(success_msg) == num_nodes:
            LOGGER.info(success_msg)
            for node in range(num_nodes):
                LOGGER.info("Archiving and copying Support bundle from server")
                sb_tar_file = "".join([bundle_id, ".srvnode{}.tar"]).format(node)
                remote_sb_path = os.path.join(remote_dir, sb_tar_file)
                local_sb_path = os.path.join(local_dir, sb_tar_file)
                tar_sb_cmd = "tar -cvf {} {}".format(remote_sb_path, bundle_dir)
                node_list[node].execute_cmd(tar_sb_cmd)
                node_list[node].copy_file_to_local(remote_sb_path, local_sb_path)
            break
    else:
        LOGGER.error("Timeout while generating support bundle")
        return False, bundle_id

    LOGGER.info("Support bundle generated successfully.")
    return True, bundle_id


def collect_crash_files(local_dir):
    """
    Collect all the crash files created at predefined locations.
    param: local_dir: local dir path to copy crash files
    :return: boolean
    """
    node_list = []
    num_nodes = len(CMN_CFG["nodes"])
    for node in range(num_nodes):
        host = CMN_CFG["nodes"][node]["hostname"]
        uname = CMN_CFG["nodes"][node]["username"]
        passwd = CMN_CFG["nodes"][node]["password"]
        node_list.append(Node(hostname=host,
                              username=uname, password=passwd))

    crash_dir1 = "/var/crash"
    crash_dir2 = "/var/log/crash"
    dir_list = [crash_dir1, crash_dir2]
    flag = False

    for node in range(num_nodes):
        for crash_dir in dir_list:
            file_list = node_list[node].list_dir(crash_dir)
            if file_list:
                flag = True
                for file in file_list:
                    remote_path = os.path.join(crash_dir, file)
                    local_path = os.path.join(local_dir, file)
                    node_list[node].copy_file_to_local(remote_path, local_path)
    if flag:
        LOGGER.info("Crash files are generated and copied at %s", local_dir)
    else:
        LOGGER.info("No Crash files are generated.")


def collect_support_bundle_k8s(local_dir_path: str, scripts_path: str = cm_const.K8S_SCRIPTS_PATH):
    """
    Utility function to get the support bundle created with services script and copied to
    client.
    :param local_dir_path: local dir path on client
    :param scripts_path: services scripts path on master node
    :return: Boolean
    """
    num_nodes = len(CMN_CFG["nodes"])
    for node in range(num_nodes):
        if CMN_CFG["nodes"][node]["node_type"] == "master":
            host = CMN_CFG["nodes"][node]["hostname"]
            username = CMN_CFG["nodes"][node]["username"]
            password = CMN_CFG["nodes"][node]["password"]
            m_node_obj = LogicalNode(hostname=host, username=username, password=password)

    if not os.path.exists(local_dir_path):
        os.mkdir(local_dir_path)

    flg = False
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.CLSTR_LOGS_CMD.format(scripts_path), read_lines=True)
    for line in resp:
        if "date" in line:
            out = line.split("date:")[1]
            out2 = out.strip()
            flg = True
            break
    if flg:
        resp1 = m_node_obj.list_dir(scripts_path)
        for file in resp1:
            if out2 in file:
                LOGGER.info("Support bundle filename:%s", file)
                remote_path = os.path.join(scripts_path, file)
                local_path = os.path.join(local_dir_path, file)
                m_node_obj.copy_file_to_local(remote_path, local_path)
                LOGGER.info("Support bundle %s generated and copied to %s path",
                            file, local_dir_path)
                return flg
    LOGGER.info("Support Bundle not generated; response: %s", resp)
    return flg


# pylint: disable-msg=too-many-locals
def collect_crash_files_k8s(local_dir_path: str):
    """
    Collect all the crash files created at predefined locations.
    :param local_dir_path: local dir path on client
    :return: Boolean
    """
    num_nodes = len(CMN_CFG["nodes"])
    for node in range(num_nodes):
        if CMN_CFG["nodes"][node]["node_type"] == "master":
            host = CMN_CFG["nodes"][node]["hostname"]
            username = CMN_CFG["nodes"][node]["username"]
            password = CMN_CFG["nodes"][node]["password"]
            m_node_obj = LogicalNode(hostname=host, username=username, password=password)

    flg = False
    pod_list = m_node_obj.get_all_pods(pod_prefix=cm_const.POD_NAME_PREFIX)
    crash_dir = "/root/crash_dir/"
    if m_node_obj.path_exists(crash_dir):
        m_node_obj.remove_dir(crash_dir)

    for pod in pod_list:
        LOGGER.info("Checking crash files for %s pod", pod)
        resp = m_node_obj.send_k8s_cmd(operation="exec", pod=pod, namespace=cm_const.NAMESPACE,
                                       command_suffix=f"-c {cm_const.HAX_CONTAINER_NAME} -- "
                                                      f"{cm_cmd.CMD_FIND_FILE}",
                                       decode=True)
        if resp:
            flg = True
            file1 = resp.split("/")
            file2 = file1[len(file1) - 1]
            remote_path = os.path.join(crash_dir, file2)
            m_node_obj.execute_cmd(cmd=cm_cmd.K8S_CP_PV_FILE_TO_LOCAL_CMD
                                   .format(pod, resp, remote_path))
            local_path = os.path.join(local_dir_path, file2)
            m_node_obj.copy_file_to_local(remote_path, local_path)

    if flg:
        LOGGER.info("Crash files are generated and copied to %s", local_dir_path)
    else:
        LOGGER.info("No crash files are generated.")


def generate_sb_lc(dest_dir: str, sb_identifier: str,
                   pod_name: str = None, msg: str = "SB", container_name: str = None):
    """
    This function is used to generate support bundle
    :param dest_dir: target directory to create support bundle into
    :param sb_identifier: support bundle identifier
    :param pod_name: name of the pod in which support bundle is generated
    :param msg: Relevant comment to link to support bundle request
    :param container_name: name of the container
    :rtype response of support bundle generate command
    """
    LOGGER.info("Generating support bundle")

    num_nodes = len(CMN_CFG["nodes"])
    for node in range(num_nodes):
        if CMN_CFG["nodes"][node]["node_type"] == "master":
            host = CMN_CFG["nodes"][node]["hostname"]
            username = CMN_CFG["nodes"][node]["username"]
            password = CMN_CFG["nodes"][node]["password"]
            node_obj = LogicalNode(hostname=host, username=username, password=password)

    if pod_name is None:
        pod_list = node_obj.get_all_pods(pod_prefix=cm_const.POD_NAME_PREFIX)
        pod_name = pod_list[0]

    if container_name is None:
        output = node_obj.execute_cmd(cmd=cm_cmd.KUBECTL_GET_POD_CONTAINERS.format(pod_name),
                                      read_lines=True)
        container_list = output[0].split()
        container_name = container_list[0]

    resp = node_obj.send_k8s_cmd(
        operation="exec", pod=pod_name, namespace=cm_const.NAMESPACE,
        command_suffix=f"-c {container_name} -- "
                       f"{cm_cmd.SUPPORT_BUNDLE_LC.format(dest_dir, sb_identifier, msg)}",
        decode=True)
    return resp


def gen_sb_with_param(sb_identifier: str, pod_name: str = None, container_name: str = None,
                      msg: str = "SB", **kwargs):
    """
    This function is used to generate support bundle
    :param sb_identifier: support bundle identifier
    :param pod_name: name of the pod in which support bundle is generated
    :param container_name: name of the container
    :param msg: Relevant comment to link to support bundle request
    :param kwargs: keyword arguments extra parameters while collecting support bundle
    :rtype response of support bundle generate command
    """
    LOGGER.info("Generating support bundle")

    dest_dir = "file://" + cm_const.R2_SUPPORT_BUNDLE_PATH

    for node in CMN_CFG["nodes"]:
        if node["node_type"].lower() == "master":
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])

    if pod_name is None:
        pod_list = node_obj.get_all_pods(pod_prefix=cm_const.POD_NAME_PREFIX)
        pod_name = pod_list[0]

    if container_name is None:
        output = node_obj.execute_cmd(cmd=cm_cmd.KUBECTL_GET_POD_CONTAINERS.format(pod_name),
                                      read_lines=True)
        container_list = output[0].split()
        container_name = container_list[0]
    cmd = cm_cmd.SUPPORT_BUNDLE_LC.format(dest_dir, sb_identifier, msg)

    for param, value in kwargs.items():
        cmd = cmd + " --" + param + " " + value

    resp = node_obj.send_k8s_cmd(
        operation="exec", pod=pod_name, namespace=cm_const.NAMESPACE,
        command_suffix=f"-c {container_name} -- "
                       f"{cmd}",
        decode=True)
    return resp


def sb_status_lc(sb_identifier: str, pod_name: str = None):
    """
    This function is used to get the support bundle status
    :param pod_name: name of the pod in which support bundle is generated
    :param sb_identifier: support bundle identifier
    :rtype response of support bundle status command
    """
    LOGGER.info("Getting support bundle status")

    num_nodes = len(CMN_CFG["nodes"])
    for node in range(num_nodes):
        if CMN_CFG["nodes"][node]["node_type"] == "master":
            host = CMN_CFG["nodes"][node]["hostname"]
            username = CMN_CFG["nodes"][node]["username"]
            password = CMN_CFG["nodes"][node]["password"]
            node_obj = LogicalNode(hostname=host, username=username, password=password)

    if pod_name is None:
        pod_list = node_obj.get_all_pods(pod_prefix=cm_const.POD_NAME_PREFIX)
        pod_name = pod_list[0]

    resp = node_obj.send_k8s_cmd(
        operation="exec", pod=pod_name, namespace=cm_const.NAMESPACE,
        command_suffix=f"-c {cm_const.HAX_CONTAINER_NAME} -- "
                       f"{cm_cmd.SUPPORT_BUNDLE_STATUS_LC.format(sb_identifier)}",
        decode=True)
    return resp


def log_file_size_on_path(pod_name: str, log_path: str):
    """
    Getting log file sizes in MB on given path and pod
    """
    for node in CMN_CFG["nodes"]:
        if node["node_type"] == "master":
            host = node["hostname"]
            username = node["username"]
            password = node["password"]
            m_node_obj = LogicalNode(hostname=host, username=username, password=password)

    LOGGER.info("Getting log file sizes on path: %s of %s pod", log_path, pod_name)
    resp = m_node_obj.send_k8s_cmd(operation="exec", pod=pod_name, namespace=cm_const.NAMESPACE,
                                   command_suffix=f"-- ls -l --block-size=MB {log_path}",
                                   decode=True)
    return resp


def file_with_prefix_exists_on_path(path: str, file_prefix: str):
    """
    This function is used to verify file with prefix exists on given path
    :param path: directory path
    :param file_prefix: file prefix
    :rtype bool
    """
    resp = os.listdir(path)
    for file in resp:
        if file_prefix in str(file):
            return True
    return False
