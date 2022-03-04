#!/usr/bin/python  # pylint: disable=C0302
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
HA disk failure recovery utility methods
"""
import logging
import json

from commons import commands as common_cmd
from commons import constants as common_const
from commons.utils import assert_utils

LOGGER = logging.getLogger(__name__)


class DiskFailureRecoveryLib:
    """
    This class common utility methods for disk failure recovery.
    """

    def __init__(self):
        self.hax_container = common_const.HAX_CONTAINER_NAME

    @staticmethod
    def get_byte_count_hctl(health_obj, byte_count_type: str):
        """
        This function is used to get different byte counts using hctl status command
        :param health_obj: Health object for master nodes
        :param byte_count_type: type of byte count (critical,damaged,degraded and healthy)
        :rtype byte count
        """
        resp = health_obj.hctl_status_json()
        temp = resp['byte_count'][0]
        return temp[byte_count_type]

    def fail_disk_using_hctl(self, pod_obj, node_name: str, device: str, status: str):
        """
            This function is used to change the disk status(online, offline etc)
            using hctl command
            :param pod_obj: Object for master nodes
            :param node_name: name of the node from which status of the disk will be changed
            :param device: name of disk of which status will be changed
            :param status: status of the disk
            :rtype bool
        """
        resp = pod_obj.get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        pod_name = resp[1]
        cmd = common_cmd.CHANGE_DISK_STATE_USING_HCTL.replace("node_val", str(node_name)). \
            replace("device_val", str(device)).replace("status_val", str(status))
        out = pod_obj.send_k8s_cmd(operation="exec", pod=pod_name,
                                   namespace=common_const.NAMESPACE,
                                   command_suffix=f"-c {self.hax_container}"
                                                  f" -- {cmd}",
                                   decode=True)
        return json.loads(out)

    def sns_repair(self, pod_obj, option: str, pod_name: str = None):
        """
            This function will start the sns repair
            :param pod_obj: Object for master nodes
            :param option: Options supported in sns repair cmd, start stop etc
            :param pod_name: name of the pod in which sns repair will start
            :rtype bool
        """
        if pod_name is None:
            resp = pod_obj.get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)
            assert_utils.assert_true(resp[0], resp[1])
            pod_name = resp[0]
        cmd = common_cmd.SNS_REPAIR_CMD.format(option)
        out = pod_obj.send_k8s_cmd(operation="exec", pod=pod_name,
                                   namespace=common_const.NAMESPACE,
                                   command_suffix=f"-c {self.hax_container}"
                                    f" -- {cmd}", decode=True)
        return out
