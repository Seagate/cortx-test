#!/usr/bin/python
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
Library Methods for DTM recovery testing
"""
import logging
import random
import time
import re

from config import S3_CFG, DTM_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.s3_bench import s3bench


class DTMRecoveryTestLib:
    """
        This class contains common utility methods for DTM related operations.
    """

    def __init__(self, access_key=ACCESS_KEY, secret_key=SECRET_KEY):
        """
        Init method
        :param access_key: Access key for S3bench operations.
        :param secret_key: Secret key for S3bench operations.
        """
        self.log = logging.getLogger(__name__)
        self.access_key = access_key
        self.secret_key = secret_key

    # pylint: disable=too-many-arguments
    def perform_write_op(self, bucket_prefix, object_prefix, no_of_clients, no_of_samples, obj_size,
                         log_file_prefix, queue, loop=1):
        """
        Perform Write operations
        :param bucket_prefix: Bucket name
        :param object_prefix: Object name prefix
        :param no_of_clients: No of Client session
        :param no_of_samples: No of samples
        :param obj_size: Object size
        :param log_file_prefix: Log file prefix
        :param queue: Multiprocessing Queue to be used for returning values (Boolean,dict)
        :param loop: Loop count for writes
        """
        results = list()
        workload = list()
        log_path = None
        for iter_cnt in range(loop):
            self.log.info("Iteration count: %s", iter_cnt)
            self.log.info("Perform Write Operations : ")
            bucket_name = bucket_prefix + str(int(time.time()))
            resp = s3bench.s3bench(self.access_key,
                                   self.secret_key, bucket=bucket_name,
                                   num_clients=no_of_clients, num_sample=no_of_samples,
                                   obj_name_pref=object_prefix, obj_size=obj_size,
                                   skip_cleanup=True, duration=None,
                                   log_file_prefix=str(log_file_prefix).upper(),
                                   end_point=S3_CFG["s3_url"],
                                   validate_certs=S3_CFG["validate_certs"])
            self.log.info("Workload: %s objects of %s with %s parallel clients.",
                          no_of_samples, obj_size, no_of_clients)
            self.log.info("Log Path %s", resp[1])
            log_path = resp[1]
            if s3bench.check_log_file_error(resp[1]):
                results.append(False)
                break
            else:
                results.append(True)
                workload.append({'bucket': bucket_name, 'obj_name_pref': object_prefix,
                                 'num_clients': no_of_clients, 'obj_size': obj_size,
                                 'num_sample': no_of_samples})
        if all(results):
            queue.put([True, workload])
        else:
            queue.put([False, f"S3bench workload for failed."
                              f" Please read log file {log_path}"])

    def perform_ops(self, workload_info: list, queue, skipread: bool = True,
                    validate: bool = True, skipcleanup: bool = False, loop=1):
        """
        Perform read operations
        :param workload_info: List Workload to read/validate/delete
        :param queue: Multiprocessing Queue to be used for returning values (Boolean,dict)
        :param skipread: Skip read
        :param validate: Validate checksum
        :param skipcleanup: Skip Cleanup
        :param loop: Loop count for performing reads in iteration.
        """
        results = list()
        log_path = None
        for iter_cnt in range(loop):
            self.log.info("Iteration count: %s", iter_cnt)
            for workload in workload_info:
                resp = s3bench.s3bench(self.access_key,
                                       self.secret_key,
                                       bucket=workload['bucket'],
                                       num_clients=workload['num_clients'],
                                       num_sample=workload['num_sample'],
                                       obj_name_pref=workload['obj_name_pref'],
                                       obj_size=workload['obj_size'],
                                       skip_cleanup=skipcleanup,
                                       skip_write=True,
                                       skip_read=skipread,
                                       validate=validate,
                                       log_file_prefix=f"read_workload_{workload['obj_size']}mb",
                                       end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                self.log.info("Workload: %s objects of %s with %s parallel clients ",
                              workload['num_sample'], workload['obj_size'],
                              workload['num_clients'])
                self.log.info("Log Path %s", resp[1])
                log_path = resp[1]
                if s3bench.check_log_file_error(resp[1]):
                    results.append(False)
                    break
                else:
                    results.append(True)

        if all(results):
            queue.put([True, f"S3bench workload is successful. Last read log file {log_path}"])
        else:
            queue.put([False, f"S3bench workload for failed."
                              f" Please read log file {log_path}"])

    # pylint: disable-msg=too-many-locals
    def process_restart(self, master_node, health_obj, pod_prefix, container_prefix, process,
                        process_ids: list = None, recover_time: int = 30):
        """
        Restart specified Process of specific pod and container
        :param master_node: Master node object
        :param health_obj: Master node health object
        :param pod_prefix: Pod Prefix
        :param container_prefix: Container Prefix
        :param process: Process to be restarted.
        :param process_ids: List of Process IDs
        :param recover_time: Wait time for process to recover
        """
        pod_list = master_node.get_all_pods(pod_prefix=pod_prefix)
        pod_selected = pod_list[random.randint(0, len(pod_list) - 1)]
        self.log.info("Pod selected for m0d process restart : %s", pod_selected)
        container_list = master_node.get_container_of_pod(pod_name=pod_selected,
                                                          container_prefix=container_prefix)
        container = container_list[random.randint(0, len(container_list) - 1)]
        self.log.info("Container selected : %s", container)
        self.log.info("Perform m0d restart")
        resp = master_node.kill_process_in_container(pod_name=pod_selected,
                                                     container_name=container,
                                                     process_name=process)
        self.log.debug("Resp : %s", resp)
        time.sleep(recover_time)

        self.log.info("Check process states")
        resp = self.poll_process_state(master_node=master_node, pod_name=pod_selected,
                                       container_name=container, process_name=process,
                                       process_ids=process_ids)
        if not resp:
            return False, "Failed during polling status of process"

        self.log.info("Process %s restarted successfully", process)

        self.log.info("Check hctl status if all services are online")
        resp = health_obj.is_motr_online()
        return resp

    def get_process_state(self, master_node, pod_name, container_name, process_name,
                          process_ids: list = None):
        """
        Function to get given process state
        :param master_node: Object of master node
        :param pod_name: Name of the pod on which container is residing
        :param container_name: Name of the container inside which process is running
        :param process_name: Name of the process
        :param process_ids: List of Process IDs
        :return: bool, dict
        e.g. (True, {'0x19': 'M0_CONF_HA_PROCESS_STARTED', '0x28': 'M0_CONF_HA_PROCESS_STARTED'})
        """
        process_state = dict()
        self.log.info("Get processes running inside container %s of pod %s", container_name,
                      pod_name)
        resp = master_node.get_all_container_processes(pod_name=pod_name,
                                                       container_name=container_name)
        if process_ids:
            self.log.info("Extract list of %s processes having IDs %s", process_name, process_ids)
            process_list = [(ele, p_id) for ele in resp for p_id in process_ids if p_id in ele
                            and process_name in ele]
            if len(process_ids) != len(process_list):
                return False, f"All process IDs {process_ids} are not found. " \
                              f"All processes running in container are: {resp}"
        else:
            self.log.info("Extract list of %s processes", process_name)
            process_list = [ele for ele in resp if process_name in ele]
        compile_exp = re.compile('"state": "(.*?)"')
        for i_i in process_list:
            process_state[i_i[1]] = compile_exp.findall(i_i[0])[0]

        return True, process_state

    def poll_process_state(self, master_node, pod_name, container_name, process_name,
                           process_ids: list = None, status: str = DTM_CFG['exp_state'],
                           timeout=300):
        """
        Helper function to poll the process states
        :param master_node: Object of master node
        :param pod_name: Name of the pod on which container is residing
        :param container_name: Name of the container inside which process is running
        :param process_name: Name of the process
        :param process_ids: List of Process IDs
        :param status: Expected status of process
        :param timeout: Poll timeout
        :return: Bool
        """
        resp = False
        self.log.info("Polling process states")
        start_time = int(time.time())
        while timeout > int(time.time()) - start_time:
            time.sleep(60)
            resp, process_state = self.get_process_state(master_node=master_node, pod_name=pod_name,
                                                         container_name=container_name,
                                                         process_name=process_name.upper(),
                                                         process_ids=process_ids)
            if not resp:
                self.log.info("Failed to get process states for process %s with IDs %s. "
                              "proccess_state dict: %s", process_name, process_ids, process_state)
                return resp
            states = list(process_state.values())
            resp = all(ele == status for ele in states)
            if resp:
                self.log.debug("Time taken by %s process to recover is %s seconds", process_name,
                               int(time.time()) - start_time)
                break

        self.log.info("State of process %s with process ids %s is %s", process_name, process_ids,
                      status)
        return resp
