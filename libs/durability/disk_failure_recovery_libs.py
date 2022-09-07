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
import copy
import json
import logging
import os
import random
import yaml

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
        temp = resp['bytecount']
        return temp[byte_count_type]

    def change_disk_status_hctl(self, pod_obj: LogicalNode, pod_name: str, data_pod_svc_name: str,
                                device: str, status: str):
        """
        This function is used to change the disk status(online, offline etc)
        using hctl command
        :param pod_obj: Object for master nodes
        :param pod_name: name of the pod
        :param data_pod_svc_name: hostname of the cortx data pod of which disk status
                                    will be changed
        :param device: name of disk of which status will be changed
        :param status: status of the disk
        :rtype Json response of hctl command
        """
        cmd = common_cmd.CHANGE_DISK_STATE_USING_HCTL.replace(
                        "cortx_nod", str(data_pod_svc_name)).replace("device_val", str(device)).\
                        replace("status_val", str(status))
        out = pod_obj.send_k8s_cmd(operation="exec", pod=pod_name,
                                   namespace=common_const.NAMESPACE,
                                   command_suffix=f"-c {self.hax_container}"
                                                  f" -- {cmd}",
                                   decode=True)
        return out

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

    def sns_rebalance(self, pod_obj: LogicalNode, option: str, pod_name: str):
        """
        This function will start the sns rebalance
        :param pod_obj: Object for master nodes
        :param option: Options supported in sns rebalance cmd, start stop etc
        :param pod_name: name of the pod in which sns rebalance will start
        :rtype response of sns rebalance command
        """
        cmd = common_cmd.SNS_REBALANCE_CMD.format(option)
        out = pod_obj.send_k8s_cmd(operation="exec", pod=pod_name,
                                   namespace=common_const.NAMESPACE,
                                   command_suffix=f"-c {self.hax_container}"
                                                  f" -- {cmd}", decode=True)
        return out

    @staticmethod
    def read_solution_config(master_obj: LogicalNode) -> tuple:
        """
        This function read the solution.yaml
        :param master_obj: Node Object of Master
        :return : tuple(bool,dict)
        """
        remote_sol_path = os.path.join(common_const.K8S_SCRIPTS_PATH, "solution.yaml")
        local_path = common_const.LOCAL_SOLUTION_PATH
        result = master_obj.copy_file_to_local(remote_sol_path, local_path)
        if not result[0]:
            raise Exception("Copy from {} to {} failed with error: {}".format(remote_sol_path,
                                                                              local_path,
                                                                              result[1]))
        try:
            with open(local_path, "r", encoding="utf-8") as file_data:
                data = yaml.safe_load(file_data)
        except IOError as error:
            LOGGER.exception("Error: Not able to read local config file")
            return False, error
        return True, data

    def retrieve_durability_values(self, master_obj: LogicalNode, ec_type: str) -> tuple:
        """
        Return the durability Configuration for Data/Metadata (SNS/DIX) for the cluster
        :param master_obj: Node Object of Master
        :param ec_type: sns/dix
        :return : tuple(bool,dict)
                  dict of format { 'data': '1','parity': '4','spare': '0'}
        """
        resp = self.read_solution_config(master_obj)
        if not resp[0]:
            return resp
        config_data = resp[1]
        try:
            ret = config_data['solution']['storage_sets'][0]['durability'][ec_type.lower()]
            data, parity, spare = ret.split('+')
            return True, {'data': data, 'parity': parity, 'spare': spare}
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
                if values['type'] == 'data_node':
                    hostname = str(values['hostname'].split('svc')[1]).replace('-', '', 1)
                    if hostname in worker_node.hostname:
                        for cvg in values['cvg']:
                            return_dict[cvg['name']] = cvg['devices']
                        break
            return True, return_dict
        except KeyError as err:
            LOGGER.error("Exception while retrieving CVG details : %s", err)
            return False, err

    def get_all_nodes_disks(self, master_obj: LogicalNode) -> tuple:
        """
        Return the unique list of disks available on all worker nodes.
        :param master_obj: Node Object of Master
        :return : tuple(bool,dict)
                 dict of format
                 {'disk1': ['ssc-vm-g4-rhev4-1059.colo.seagate.com', 'cvg-01', '/dev/sdh'],
                  'disk2': ['ssc-vm-g4-rhev4-1059.colo.seagate.com', 'cvg-02', '/dev/sdd']}
        """
        resp = self.read_solution_config(master_obj)
        if not resp[0]:
            return resp
        config_data = resp[1]
        return_dict = {}
        cntr = 1
        try:
            cvgs = config_data['solution']['storage_sets'][0]['storage']
            nodes = config_data['solution']['storage_sets'][0]['nodes']
            for node in nodes:
                for cvg in cvgs:
                    cvg_name = cvg['name']
                    data_devices = cvg['devices']['data']
                    for data_device in data_devices:
                        disk_path = data_device['path']
                        val = [node, cvg_name, disk_path]
                        return_dict['disk' + str(cntr)] = val
                        cntr += 1
        except KeyError as err:
                LOGGER.error("Exception while retrieving disk details : %s", err)
                return False, err
        return True, return_dict

    def get_multi_pod_disks(self, master_obj: LogicalNode, health_obj: Health) -> dict:
        """
        Return the unique list of disks available for all the data pods.
        :param master_obj: Node Object of Master
        :param health_obj: Health object of primary node
        :return : dict
                 dict of format
                 {'disk1': ['cortx-data-g1-4.cortx-data-headless.cortx.svc.cluster.local',
                 'cvg-01', '/dev/sdh'],
                  'disk2': ['cortx-data-g0-4.cortx-data-headless.cortx.svc.cluster.local',
                  'cvg-02', '/dev/sdd']}
        """
        resp = self.get_all_nodes_disks(master_obj)
        LOGGER.info(resp)
        if not resp[0]:
            return resp
        all_node_disks = resp[1]
        pod_disk_status = health_obj.hctl_disk_status()
        pod_node_dict = master_obj.get_node_multipod_dict()
        for disk in all_node_disks:
            if all_node_disks[disk][0] in pod_node_dict.keys():
                for pod in pod_node_dict[all_node_disks[disk][0]]:
                    if all_node_disks[disk][2] in pod_disk_status[pod + '.'+ \
                        common_const.CORTX_DATA_SVC_POSTFIX]:
                        all_node_disks[disk][0] = pod + '.'+ common_const.CORTX_DATA_SVC_POSTFIX
        LOGGER.info("Data pod disk mappings: %s", all_node_disks)
        return all_node_disks

    def fail_disk(self, disk_fail_cnt: int, master_obj: LogicalNode, health_obj: Health,
                   pod_name: str, on_diff_cvg: bool = False, on_same_cvg = False) -> tuple:
        """
        Return the unique list of failed disks.
        :param disk_fail_cnt: Number of disks to be failed
        :param master_obj: Node Object of primary node
        :param health_obj: Health object of primary node
        :param pod_name: name of the pod
        :param on_diff_cvg: selects disks from different cvg if set True
        :param on_same_cvg: selects disks from same cvg if set True
        :return : tuple(bool,dict)
                 dict of format
                 {'disk1': ['ssc-vm-g4-rhev4-1059.colo.seagate.com', 'cvg-01', '/dev/sdh'],
                  'disk2': ['ssc-vm-g4-rhev4-1059.colo.seagate.com', 'cvg-02', '/dev/sdd']}
        """

        LOGGER.info("No of disks to be failed: %s", disk_fail_cnt)
        failed_disks_dict = {}
        resp = self.get_multi_pod_disks(master_obj, health_obj)
        all_disks = resp
        LOGGER.info("list of all disks: %s", all_disks)
        if on_diff_cvg:
            one_disk_per_cvg_dict = {}
            for disk in all_disks:
                flg = True
                for val in one_disk_per_cvg_dict:
                    if all_disks[disk][0] in one_disk_per_cvg_dict[val] and \
                            all_disks[disk][1] in one_disk_per_cvg_dict[val]:
                        flg = False
                        break
                if flg:
                    one_disk_per_cvg_dict[disk] = all_disks[disk]
            if len(one_disk_per_cvg_dict) < disk_fail_cnt:
                LOGGER.error(f"for failing only one disk per cvg, number of cvg's: "
                            f"{one_disk_per_cvg_dict} are less than disk fail count: "
                            f"{disk_fail_cnt}")
                return False, "Number of cvg are less than disk fail count"
            all_disks = copy.deepcopy(one_disk_per_cvg_dict)

        if on_same_cvg:
            # select random node and cvg
            same_cvg_disks = {}
            random_disk = random.choice(list(all_disks.values()))
            node = random_disk[0]
            cvg = random_disk[1]
            for key,value in all_disks.items():
                if node == value[0] and cvg == value[1]:
                    same_cvg_disks[key] = value
            all_disks = copy.deepcopy(same_cvg_disks)
        for cnt in range(disk_fail_cnt):
            selected_disk = random.choice(list(all_disks))  # nosec
            LOGGER.info("disk fail loop: %s, disk selected for failure: %s",
                        cnt + 1, all_disks[selected_disk])
            resp = self.change_disk_status_hctl(master_obj, pod_name,
                                all_disks[selected_disk][0],
                                all_disks[selected_disk][2], "failed")
            LOGGER.info("fail disk command resp: %s", resp)
            failed_disks_dict['disk' + str(cnt)] = all_disks[selected_disk]
            all_disks.pop(selected_disk)
        return True, failed_disks_dict
