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

"""Methods to collect various logs such as dmesgs and journal"""

import logging
import os
from datetime import datetime

from commons.commands import CMD_DMESGS, CMD_JOURNALCTL
from commons.helpers.pods_helper import LogicalNode

# check and set pytest logging level as Globals.LOG_LEVEL
LOGGER = logging.getLogger(__name__)


class ServerOSLogsCollectLib:

    """
    This class contains common methods to collect dmesgs and journalctl logs
    """

    def __init__(self, cmn_cfg):
        """
        Initialize connection to Nodes or Pods.
        :param cmn_cfg: Common config
        """
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.node_list = list()
        for node in self.nodes:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            self.node_list.append(node_obj)

    def collect_logs(self, path):
        """
        function to collect dmesgs and journalctl logs
        :param path: local path to copy files from server nodes
        """
        time_stamp = str(datetime.now().strftime("%m_%d_%Y_%H_%M_%S"))
        for node in self.node_list:
            dmesgs_file = f"{node.hostname}_{time_stamp}_dmesg.log"
            journalctl_file = f"{node.hostname}_{time_stamp}_journalctl.log"
            dmesgs_path = f"/tmp/{dmesgs_file}_dmesg.log"
            journalctl_path = f"/tmp/{journalctl_file}_journalctl.log"
            LOGGER.info("Executing cmd on node %s", node.hostname)
            node.execute_cmd(cmd=CMD_DMESGS.format(dmesgs_path))
            node.execute_cmd(cmd=CMD_JOURNALCTL.format(journalctl_path))

            LOGGER.info("Copying logs from node %s", node.hostname)
            resp_cp = node.copy_file_to_local(remote_path=dmesgs_path,
                                              local_path=os.path.join(path, dmesgs_file))
            if not resp_cp[0]:
                return resp_cp[0]
            resp_cp = node.copy_file_to_local(remote_path=journalctl_path,
                                              local_path=os.path.join(path, journalctl_file))
            if not resp_cp[0]:
                return resp_cp[0]
            LOGGER.info("Removing logs from node %s", node.hostname)
            node.remove_remote_file(filename=dmesgs_path)
            node.remove_remote_file(filename=journalctl_path)
        return True
