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
disk near full data storage utility methods
"""
import logging

from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.durability.disk_failure_recovery_libs import DiskFailureRecoveryLib
from scripts.s3_bench import s3bench

LOGGER = logging.getLogger(__name__)


class NearFullStorage:
    """
    This class contains common utility methods to create pre filled near full storage.
    """

    @staticmethod
    def get_user_data_space_in_bytes(master_obj: LogicalNode, memory_percent: int) -> tuple:
        """
        Retrieve the available user data space in bytes to attain the given memory percent
        :param master_obj: Logical node object of Master
        :param memory_percent: Expected Memory Percentage to achieve.
        :return : (boolean, int)
        """
        # Get available data disk space
        health_obj = Health(master_obj.hostname, master_obj.username, master_obj.password)
        total_cap, avail_cap, used_cap = health_obj.get_sys_capacity()
        current_usage_per = round(used_cap / total_cap * 100)

        if memory_percent > current_usage_per:
            # Get SNS configuration to retrieve available user data space
            durability_values = DiskFailureRecoveryLib.retrieve_durability_values(master_obj, 'sns')
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
    def perform_near_full_sys_writes(s3userinfo, user_data_writes, bucket_prefix: str,
                                     **kwargs) -> tuple:
        """
        Perform write operation till the memory is filled to given percentage
        :param s3userinfo: S3user dictionary with access/secret key
        :param user_data_writes: Write operation to be performed for specific bytes
        :param bucket_prefix: Bucket prefix for the data written
        :return : list of dictionary
                format : [{'bucket': bucket_name, 'obj_name_pref': obj_name, 'num_clients':
                client, 'obj_size': obj_size, 'num_sample': sample}]
        """
        client = kwargs.get("client", 10)
        workload = [128, 256, 512]  # workload in mb
        if CMN_CFG["setup_type"] == "HW":
            workload.extend([1024, 2048, 3072, 4096])

        mb = 1024 * 1024
        workload = [each * mb for each in workload]  # convert to bytes
        each_workload_byte = user_data_writes / len(workload)
        return_list = []
        for obj_size in workload:
            samples = int(each_workload_byte / obj_size)
            if samples > 0:
                temp_client = client
                if temp_client > samples:
                    temp_client = samples
                bucket_name = f'{bucket_prefix}-{obj_size}b'
                obj_name = f'obj_{obj_size}'
                resp = s3bench.s3bench(s3userinfo['accesskey'],
                                       s3userinfo['secretkey'],
                                       bucket=bucket_name,
                                       num_clients=temp_client,
                                       num_sample=samples,
                                       obj_name_pref=obj_name, obj_size=f"{obj_size}b",
                                       skip_cleanup=True, duration=None,
                                       log_file_prefix=f"workload_{obj_size}b",
                                       end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                LOGGER.info(f"Workload: %s objects of %s with %s parallel clients ", samples,
                            obj_size, temp_client)
                LOGGER.info(f"Log Path {resp[1]}")
                if s3bench.check_log_file_error(resp[1]):
                    return False, f"S3bench workload for failed for {obj_size}." \
                                  f" Please read log file {resp[1]}"
                return_list.append(
                    {'bucket': bucket_name, 'obj_name_pref': obj_name, 'num_clients': temp_client,
                     'obj_size': obj_size, 'num_sample': samples})
            else:
                continue
        return True, return_list

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
                                   obj_name_pref=each['obj_name_pref'],
                                   obj_size=f"{each['obj_size']}b",
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
            if s3bench.check_log_file_error(resp[1]):
                return False, f"S3bench workload for failed for {each['obj_size']}." \
                              f" Please read log file {resp[1]}"
        return True, f'S3bench workload successful'
