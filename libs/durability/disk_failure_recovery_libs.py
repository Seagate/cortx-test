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
import random

from commons import commands as common_cmd
from commons import constants as common_const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from config.s3 import S3_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from scripts.s3_bench import s3bench

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
                if values['type'] == 'data_node':
                    hostname = str(values['hostname'].split('svc')[1]).replace('-', '', 1)
                    if hostname in worker_node.hostname:
                        for cvg in values['storage']['cvg']:
                            return_dict[cvg['name']] = cvg['devices']
                        break
            return True, return_dict
        except KeyError as err:
            LOGGER.error("Exception while retrieving CVG details : %s", err)
            return False, err

    def get_all_nodes_disks(self, master_obj: LogicalNode, worker_obj: list) -> tuple:
        """
        Return the unique list of disks available on all worker nodes.
        :param master_obj: Node Object of Master
        :param worker_obj: list of worker node object
        :return : tuple(bool,dict)
                 dict of format
                 {'disk1': ['ssc-vm-g4-rhev4-1059.colo.seagate.com', 'cvg-01', '/dev/sdh'],
                  'disk2': ['ssc-vm-g4-rhev4-1059.colo.seagate.com', 'cvg-02', '/dev/sdd']}
        """
        return_dict = {}
        cntr = 1
        for node in worker_obj:
            resp = self.retrieve_cvg_from_node(master_obj, node)
            if not resp[0]:
                return resp
            try:
                for cvg in resp[1]:
                    disk_list = resp[1][cvg]['data']
                    for disk in disk_list:
                        val = [node.hostname, cvg, disk]
                        return_dict['disk' + str(cntr)] = val
                        cntr += 1
            except KeyError as err:
                LOGGER.error("Exception while retrieving disk details : %s", err)
                return False, err
        return True, return_dict

    def fail_disk(self, disk_fail_cnt: int, master_obj: LogicalNode,worker_obj: list,
                   pod_name: str, on_diff_cvg: bool = False, on_same_cvg = False) -> tuple:
        """
        Return the unique list of failed disks.
        :param disk_fail_cnt: Number of disks to be failed
        :param master_obj: Node Object of Master
        :param worker_obj: list of worker node object
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
        resp = self.get_all_nodes_disks(master_obj, worker_obj)
        if not resp[0]:
            return resp
        all_disks = resp[1]
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
            resp = self.change_disk_status_hctl(master_obj, pod_name, all_disks[selected_disk][0],
                                                all_disks[selected_disk][2], "failed")
            LOGGER.info("fail disk command resp: %s", resp)
            failed_disks_dict['disk' + str(cnt)] = all_disks[selected_disk]
            all_disks.pop(selected_disk)
        return True, failed_disks_dict

    def get_user_data_space_in_bytes(self, master_obj: LogicalNode, memory_percent: int) -> tuple:
        """
        Retrieve the available user data space in bytes to attain the given memory percent
        :param master_obj: Logical node object of Master
        :param memory_percent: Expected Memory Percentage to achieve.
        :return : (boolean, int)
        """
        # Get available data disk space
        health_obj = Health(master_obj.hostname, master_obj.username, master_obj.password)
        total_cap, avail_cap, used_cap = health_obj.get_sys_capacity()
        current_usage_per = int(used_cap / total_cap * 100)

        if memory_percent > current_usage_per:
            # Get SNS configuration to retrieve available user data space
            durability_values = self.retrieve_durability_values(master_obj, 'sns')
            if not durability_values[0]:
                LOGGER.error("Error in retrieving SNS values")
                return durability_values
            sns_values = {key: int(value) for key, value in durability_values[1].items()}
            LOGGER.debug("Durability Values (SNS) %s", sns_values)
            data_sns = sns_values['data']
            sum_sns = sum(sns_values.values())
            LOGGER.debug("Current usage : %s Expected disk usage : %s", current_usage_per,
                         memory_percent)
            write_percent = memory_percent - current_usage_per
            expected_writes = (write_percent * total_cap) / 100
            user_data_writes = data_sns / sum_sns * expected_writes
            LOGGER.info("User writes to be performed %s bytes to attain %s full disk space",
                        user_data_writes, memory_percent)
            return True, user_data_writes
        else:
            LOGGER.info("Current Memory usage(%s) is already more than expected memory usage(%s)",
                        current_usage_per, memory_percent)
            return True, 0

    @staticmethod
    def perform_near_full_sys_writes(s3userinfo, user_data_writes, bucket_prefix: str) -> list:
        """
        Perform write operation till the memory if filled to given percentage
        :param s3userinfo: S3user dictionary with access/secret key
        :param user_data_writes: Write operation to be performed for specific bytes
        :param bucket_prefix: Bucket prefix for the data written
        :return : list of dictionary
                format : [{'bucket': bucket_name, 'obj_name_pref': obj_name, 'num_clients': client,
                     'obj_size': obj_size, 'num_sample': sample}]
        """
        workload = [1, 16, 128, 256, 512]  # workload in mb
        mb = 1024 * 1024
        client = 10
        workload = [each * mb for each in workload]  # convert to bytes
        each_workload_byte = user_data_writes / len(workload)
        return_list = []
        for obj_size in workload:
            samples = int(each_workload_byte / obj_size)
            if samples > 0:
                bucket_name = f'{bucket_prefix}-{obj_size}b'
                obj_name = f'obj_{obj_size}'
                resp = s3bench.s3bench(s3userinfo['accesskey'],
                                       s3userinfo['secretkey'],
                                       bucket=bucket_name,
                                       num_clients=client,
                                       num_sample=samples,
                                       obj_name_pref=obj_name, obj_size=obj_size,
                                       skip_cleanup=False, duration=None,
                                       log_file_prefix=f"workload_{obj_size}mb",
                                       end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                LOGGER.info(f"Workload: %s objects of %s with %s parallel clients ", samples,
                            obj_size, client)
                LOGGER.info(f"Log Path {resp[1]}")
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload for failed for {obj_size}. Please read log file {resp[1]}"
                return_list.append(
                    {'bucket': bucket_name, 'obj_name_pref': obj_name, 'num_clients': client,
                     'obj_size': obj_size, 'num_sample': samples})
            else:
                continue
        return return_list

    @staticmethod
    def perform_near_full_sys_operations(s3userinfo, workload_info: list, skipread: bool = True,
                                         validate: bool = True, skipcleanup: bool = False):
        """
        Perform Read/Validate/Delete operations on the workload info using s3bench
        :param s3userinfo: S3user dictionary with access/secret key
        :param workload_info: S3bench workload info of performed writes
        :param skipread: Skip reading objects created if True
        :param validate: perform checksum validation on read data is True
        :param skipcleanup: Skip deleting objects created if True
        """
        for each in workload_info:
            resp = s3bench.s3bench(s3userinfo['accesskey'],
                                   s3userinfo['secretkey'],
                                   bucket=each['bucket'],
                                   num_clients=each['num_clients'],
                                   num_sample=each['num_sample'],
                                   obj_name_pref=each['obj_name_pref'], obj_size=each['obj_size'],
                                   skip_cleanup=skipcleanup,
                                   skip_write=True,
                                   skip_read=skipread,
                                   validate=validate,
                                   log_file_prefix=f"read_workload_{each['obj_size']}mb",
                                   end_point=S3_CFG["s3_url"],
                                   validate_certs=S3_CFG["validate_certs"])
            LOGGER.info(f"Workload: %s objects of %s with %s parallel clients ", each['num_sample'],
                        each['obj_size'], each['num_clients'])
            LOGGER.info(f"Log Path {resp[1]}")
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload failed for {each['obj_size']}. Please read log file {resp[1]}"
