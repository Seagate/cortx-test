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
Module to maintain support bundle utils
"""

import os
import logging
import time
from commons.helpers.node_helper import Node
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

# pylint: disable=too-many-arguments
def create_support_bundle_single_cmd(local_dir, bundle_name, comp_list=None):
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

    LOGGER.info("Checking for available space before SB generate.")
    for node in range(num_nodes):
        res = node_list[node].execute_cmd(cmd="df -h")
        res = res.decode("utf-8")
        LOGGER.info("Available space on srvnode %s : %s", node, res)
    LOGGER.info("Starting support bundle creation")
    command = " ".join([cm_cmd.R2_CMD_GENERATE_SUPPORT_BUNDLE, bundle_name])
    # Form the command if component list is provided in parameters
    if comp_list is not None:
        command = command + ''.join(" -c ")
        command = command + ''.join(comp_list)
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
