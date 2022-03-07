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
import json
import logging

from commons import commands as common_cmd
from commons import constants as common_const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from libs.ha.ha_common_libs_k8s import HAK8s

LOGGER = logging.getLogger(__name__)


class DiskFailureRecoveryLib:
    """
    This class contains common utility methods for disk failure recovery.
    """

    def __init__(self):
        self.hax_container = common_const.HAX_CONTAINER_NAME

    @staticmethod
    def get_byte_count_hctl(health_obj: Health, byte_count_type: str):
        """
        This function is used to get different byte counts using hctl status command
        :param health_obj: Health object for master nodes
        :param byte_count_type: type of byte count (critical,damaged,degraded and healthy)
        :rtype byte count
        """
        resp = health_obj.hctl_status_json()
        temp = resp['byte_count'][0]
        return temp[byte_count_type]

    def change_disk_status_hctl(self, pod_obj: LogicalNode, pod_name: str, node_name: str,
                                device: str, status: str):
        """
        This function is used to change the disk status(online, offline etc)
        using hctl command
        :param pod_obj: Object for master nodes
        :param pod_name: name of the pod
        :param node_name: name of the node from which status of the disk will be changed
        :param device: name of disk of which status will be changed
        :param status: status of the disk
        :rtype Json response of hctl command
        """
        cmd = common_cmd.CHANGE_DISK_STATE_USING_HCTL.replace("node_val", str(node_name)). \
            replace("device_val", str(device)).replace("status_val", str(status))
        out = pod_obj.send_k8s_cmd(operation="exec", pod=pod_name,
                                   namespace=common_const.NAMESPACE,
                                   command_suffix=f"-c {self.hax_container}"
                                                  f" -- {cmd}",
                                   decode=True)
        return json.loads(out)

    def sns_repair(self, pod_obj: LogicalNode, option: str, pod_name: str):
        """
        This function will start the sns repair
        :param pod_obj: Object for master nodes
        :param option: Options supported in sns repair cmd, start stop etc
        :param pod_name: name of the pod in which sns repair will start
        :rtype response of sns repair command
        """
        cmd = common_cmd.SNS_REPAIR_CMD.format(option)
        out = pod_obj.send_k8s_cmd(operation="exec", pod=pod_name,
                                   namespace=common_const.NAMESPACE,
                                   command_suffix=f"-c {self.hax_container}"
                                                  f" -- {cmd}", decode=True)
        return out

    @staticmethod
    def retrieve_durability_values(master_obj: LogicalNode, ec_type: str) -> tuple:
        """
        Return the durability Configuration for Data/Metadata (SNS/DIX) for the cluster
        :param master_obj: Node Object of Master
        :param ec_type: sns/dix
        :return : tuple(bool,dict)
                  dict of format { 'data': '1','parity': '4','spare': '0'}
        """
        resp = HAK8s.get_config_value(master_obj)
        if not resp[0]:
            return resp
        config_data = resp[1]
        try:
            ret = config_data['cluster']['storage_set'][0]['durability'][ec_type.lower()]
            return True, ret
        except KeyError as err:
            LOGGER.error("Exception while retrieving Durability config : %s", err)
            return False, err

    @staticmethod
    def retrieve_cvg_from_node(master_obj: LogicalNode, worker_node: LogicalNode) -> tuple:
        """
        Return the cvg details of the given worker node.
        :param master_obj: Node Object of Master
        :param worker_node: Return the CVG details for this worker node
        :return : tuple(bool,dict)
                 dict of format
                 {'cvg-01': {'data': ['/dev/sde', '/dev/sdf'], 'metadata': ['/dev/sdc'],
                            'num_data': 2, 'num_metadata': 1},
                 'cvg-02': {'data': ['/dev/sdg', '/dev/sdh'], 'metadata': ['/dev/sdd'],
                            'num_data': 2, 'num_metadata': 1}}
        """
        resp = HAK8s.get_config_value(master_obj)
        if not resp[0]:
            return resp
        config_data = resp[1]
        return_dict = {}
        try:
            for key, values in config_data['node'].items():
                hostname = str(values['hostname'].split('svc')[1]).replace('-', '', 1)
                if hostname in worker_node.hostname:
                    for cvg in values['storage']['cvg']:
                        return_dict[cvg['name']] = cvg['devices']
            return True, return_dict
        except KeyError as err:
            LOGGER.error("Exception while retrieving CVG details : %s", err)
            return False, err
