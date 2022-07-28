# -*- coding: utf-8 -*-
# !/usr/bin/python
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
#
"""Methods to collect top command stats from server"""

import logging
import os.path
from multiprocessing import Process

from commons.commands import KILL_CMD
from commons.constants import COLLECTION_FILE
from commons.constants import COLLECTION_SCRIPT_PATH
from commons.constants import PROFILE_FILE
from commons.constants import PROFILE_FILE_PATH
from commons.helpers.pods_helper import LogicalNode

# check and set pytest logging level as Globals.LOG_LEVEL
LOGGER = logging.getLogger(__name__)


class TopStatsCollection:
    """
    This class contains common methods to collect stats of top cmd from k8s system
    """
    def __init__(self, cmn_cfg):
        """
        Initialize connection to Nodes or Pods.
        :param cmn_cfg: Common config
        """
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.master_node_list = list()
        for node in self.nodes:
            if node["node_type"].lower() == "master":
                node_obj = LogicalNode(hostname=node["hostname"],
                                       username=node["username"],
                                       password=node["password"])
                self.master_node_list.append(node_obj)

    @staticmethod
    def exe_cmd(node: LogicalNode, cmd: str):
        """function to execute command collection
        :param node: Object of Logical node
        :param cmd: command to be executed on worker node
        """
        LOGGER.debug("executing top cmd for stat collection")
        node.execute_cmd(cmd=cmd)

    def collect_stats(self, dir_path):
        """
        function to collect top command stats
        :param dir_path: directory path for stats file
        :return: Boolean (status of cmd execution)
        """
        resp = self.master_node_list[0].copy_file_to_remote(PROFILE_FILE_PATH, PROFILE_FILE)
        if not resp[0]:
            return resp[0]
        resp = self.master_node_list[0].copy_file_to_remote(COLLECTION_SCRIPT_PATH, COLLECTION_FILE)
        if not resp[0]:
            return resp[0]
        self.master_node_list[0].apply_k8s_deployment(PROFILE_FILE)
        if not resp[0]:
            return resp[0]
        cmd = f"chmod +x {COLLECTION_FILE} && ./{COLLECTION_FILE} {dir_path}"
        proc = Process(target=self.exe_cmd, args=(self.master_node_list[0], cmd))
        proc.start()
        cmd = f'pgrep "/bin/sh ./{COLLECTION_FILE} {dir_path}" -fx'
        pids = str(self.master_node_list[0].execute_cmd(f"echo $({cmd})"))
        LOGGER.debug("pids of processes %s", pids)
        list_pids = pids.split()
        res = []
        for pid in list_pids:
            res.append(''.join(filter(lambda j: j.isdigit(), pid)))
        LOGGER.debug("list of pids %s", res)
        if not res:
            LOGGER.info("Process IDs of cmd %s is empty", cmd)
            return False
        return True

    def stop_collection(self, dir_path):
        """function to get pid and kill it on server"""

        cmd = f'pgrep "/bin/sh ./{COLLECTION_FILE} {dir_path}" -fx'
        pids = str(self.master_node_list[0].execute_cmd(f"echo $({cmd})"))
        LOGGER.debug("pids of processes %s", pids)
        list_pids = pids.split()
        res = []
        for pid in list_pids:
            res.append(''.join(filter(lambda j: j.isdigit(), pid)))
        LOGGER.debug("list of pids %s", res)
        if not res:
            LOGGER.info("Process IDs of cmd %s is empty", cmd)
            return False
        for pid in res:
            self.master_node_list[0].execute_cmd(cmd=KILL_CMD.format(pid))
        return True

    def copy_remove_files_from_remote(self, dir_path, local_path):
        """
        function to copy files from dir and remove dir from remote
        """
        ls_dir = self.master_node_list[0].list_dir(remote_path=dir_path)
        LOGGER.debug("ls of remote dir %s", ls_dir)
        for file in ls_dir:
            resp = self.master_node_list[0].copy_file_to_local(os.path.join(dir_path, file),
                                                               os.path.join(local_path, file))
            if not resp:
                LOGGER.info("copy of file %s failed", file)
                return resp
        LOGGER.debug("removing dir from path of remote %s", dir_path)
        resp = self.master_node_list[0].delete_dir_sftp(dpath=dir_path)
        return resp
