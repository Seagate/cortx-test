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

from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils

# check and set pytest logging level as Globals.LOG_LEVEL
LOGGER = logging.getLogger(__name__)


class ServerOSLogsCollectLib:

    """
    collect 2 log on each node
    copy all logs to local from each node
    remove logs from each node
    """

    def __init__(self, cmn_cfg):
        """
        Initialize connection to Nodes or Pods.
        :param cmn_cfg: Common config
        """
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.machine_node_list = list()
        for node in self.nodes:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            self.machine_node_list.append(node_obj)

    def collect_logs(self, path):
        """
        function to collect dmesgs and journalctl logs
        :param path: local path to copy files from server machines
        """
        dmesgs_cmd = 'dmesg > {}_dmesg.log'
        journalctl_cmd = 'journalctl > {}_journalctl.log'
        for machine in self.machine_node_list:
            dmesgs_path = "{}_dmesg.log".format(machine.hostname)
            journalctl_path = "{}_journalctl.log".format(machine.hostname)

            LOGGER.info("Executing cmd on machine %s", machine.hostname)
            machine.execute_cmd(cmd=dmesgs_cmd.format(machine.hostname))
            machine.execute_cmd(cmd=journalctl_cmd.format(machine.hostname))

            LOGGER.info("Copying logs from machine %s", machine.hostname)
            resp_cp = machine.copy_file_to_local(remote_path=dmesgs_path, local_path=path)
            assert_utils.assert_true(resp_cp[0], resp_cp[1])
            resp_cp = machine.copy_file_to_local(remote_path=journalctl_path, local_path=path)
            assert_utils.assert_true(resp_cp[0], resp_cp[1])

            LOGGER.info("Removing logs from machine %s", machine.hostname)
            machine.remove_remote_file(filename=dmesgs_path)
            machine.remove_remote_file(filename=journalctl_path)
