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

from commons.commands import KILL_CMD, K8S_APPLY_FILE
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

    def collect_stats(self, dir_path):
        """
        function to collect top command stats
        :param dir_path: directory path for stats file
        """
        profile_file_path = "scripts/io_stability/profiling.yaml"
        collection_script_path = "scripts/io_stability/collect-k8s-stats.sh"
        self.master_node_list[0].copy_file_to_remote(profile_file_path)
        self.master_node_list[0].copy_file_to_remote(collection_script_path)
        self.master_node_list[0].execute_cmd(K8S_APPLY_FILE.format(profile_file_path))
        cmd = f"collect-k8s-stats.sh {dir_path}"
        self.master_node_list[0].execute_cmd(cmd=cmd)

    def stop_collection(self):
        """function to get pid and kill it on server"""
        proc = "collect-k8s-stats"
        res = self.master_node_list[0].execute_cmd("echo $(pgrep {})".format(proc))
        LOGGER.info(f'{proc} PID {res}')
        self.master_node_list[0].execute_cmd(cmd=KILL_CMD.format(res))

    def copy_files(self, remote_path, local_path):
        """
        get top stats file to local path
        """
        resp = self.master_node_list[0].copy_file_to_local(remote_path=remote_path,
                                                           local_path=local_path)
        if not resp[0]:
            return resp[0]
        return True
