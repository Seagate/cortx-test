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
import copy
import logging
import os
import random
import re
import secrets
import time

import yaml

from commons import constants as const
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from config import CMN_CFG
from config import DTM_CFG
from config import HA_CFG
from config import S3_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


class DTMRecoveryTestLib:
    """
        This class contains common utility methods for DTM related operations.
    """

    def __init__(self, access_key=ACCESS_KEY, secret_key=SECRET_KEY, max_attempts=6):
        """
        Init method
        :param access_key: Access key for S3bench operations.
        :param secret_key: Secret key for S3bench operations.
        """
        self.log = logging.getLogger(__name__)
        self.ha_obj = HAK8s()
        self.access_key = access_key
        self.secret_key = secret_key
        self.s3t_obj = S3TestLib(access_key=self.access_key, secret_key=self.secret_key,
                                 max_attempts=max_attempts)
        self.setup_type = CMN_CFG["setup_type"]
        self.system_random = secrets.SystemRandom()

    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-arguments
    def perform_write_op(self, bucket_prefix, object_prefix, no_of_clients, no_of_samples,
                         log_file_prefix, queue, obj_size: str = None, loop: int = 1,
                         created_bucket: list = None, retry: int = None, **kwargs):
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
        :param created_bucket: List of pre created buckets(Should be greater or equal to loop count)
        :param retry: Retry count for IOs
        """
        results = list()
        workload = list()
        log_path = None
        skip_read = kwargs.get("skip_read", True)
        skip_cleanup = kwargs.get("skip_cleanup", True)
        validate = kwargs.get("validate", False)
        obj_size_list = copy.deepcopy(HA_CFG["s3_bench_workloads"])
        if self.setup_type == "HW":
            obj_size_list.extend(HA_CFG["s3_bench_large_workloads"])
        for iter_cnt in range(loop):
            self.log.info("Iteration count: %s", iter_cnt)
            self.log.info("Perform Write Operations : ")
            bucket_name = bucket_prefix + str(int(time.time_ns()))
            if created_bucket:
                bucket_name = created_bucket[iter_cnt]
            object_size = self.system_random.choice(obj_size_list) if obj_size is None else obj_size
            resp = s3bench.s3bench(self.access_key,
                                   self.secret_key, bucket=bucket_name,
                                   num_clients=no_of_clients, num_sample=no_of_samples,
                                   obj_name_pref=object_prefix, obj_size=object_size,
                                   skip_read=skip_read, validate=validate,
                                   skip_cleanup=skip_cleanup, duration=None,
                                   log_file_prefix=str(log_file_prefix).upper(),
                                   end_point=S3_CFG["s3_url"],
                                   validate_certs=S3_CFG["validate_certs"],
                                   max_retries=retry)
            self.log.info("Workload: %s objects of %s with %s parallel clients.",
                          no_of_samples, object_size, no_of_clients)
            self.log.info("Log Path %s", resp[1])
            log_path = resp[1]
            if s3bench.check_log_file_error(resp[1]):
                results.append(False)
                break
            else:
                results.append(True)
                workload.append({'bucket': bucket_name, 'obj_name_pref': object_prefix,
                                 'num_clients': no_of_clients, 'obj_size': object_size,
                                 'num_sample': no_of_samples})
        if all(results):
            queue.put([True, workload])
        else:
            queue.put([False, f"S3bench workload for failed."
                              f" Please read log file {log_path}"])

    def perform_ops(self, workload_info: list, queue, skipread: bool = True,
                    validate: bool = True, skipcleanup: bool = False, loop: int = 1,
                    retry: int = None):
        """
        Perform read operations
        :param workload_info: List Workload to read/validate/delete
        :param queue: Multiprocessing Queue to be used for returning values (Boolean,dict)
        :param skipread: Skip read
        :param validate: Validate checksum
        :param skipcleanup: Skip Cleanup
        :param loop: Loop count for performing reads in iteration.
        :param retry: Retry count for IOs
        """
        results = list()
        for iter_cnt in range(loop):
            self.log.info("Iteration count: %s", iter_cnt)
            for workload in workload_info:
                if not skipread or validate:
                    resp = s3bench.s3bench(self.access_key,
                                           self.secret_key,
                                           bucket=workload['bucket'],
                                           num_clients=workload['num_clients'],
                                           num_sample=workload['num_sample'],
                                           obj_name_pref=workload['obj_name_pref'],
                                           obj_size=workload['obj_size'],
                                           skip_cleanup=True,
                                           skip_write=True,
                                           skip_read=skipread,
                                           validate=validate,
                                           log_file_prefix=f"read_workload_{workload['obj_size']}",
                                           end_point=S3_CFG["s3_url"],
                                           validate_certs=S3_CFG["validate_certs"],
                                           max_retries=retry)
                    self.log.info("Workload: %s objects of %s with %s parallel clients ",
                                  workload['num_sample'], workload['obj_size'],
                                  workload['num_clients'])
                    self.log.info("Log Path %s", resp[1])
                    if s3bench.check_log_file_error(resp[1]):
                        self.log.error("Error found in log path: %s", resp[1])
                        results.append(False)
                        break
                    else:
                        results.append(True)
                if not skipcleanup:
                    # Delete all objects from the bucket
                    resp = self.s3t_obj.object_list(bucket_name=workload['bucket'])
                    obj_list = resp[1]
                    del_res = True
                    for obj in obj_list:
                        try:
                            self.s3t_obj.delete_object(bucket_name=workload['bucket'], obj_name=obj)
                        except CTException as error:
                            self.log.error("Error while deleting object %s from bucket %s : %s",
                                           obj, workload['bucket'], error)
                            del_res = False
                    results.append(del_res)
                    if not del_res:
                        self.log.error("Observed deletion error for bucket %s.", workload['bucket'])
                        break
                    self.log.info("Objects deletion completed for bucket %s", workload['bucket'])

        if all(results):
            queue.put([True, "Workload successful."])
        else:
            queue.put([False, "Workload failed."])

    def set_proc_restart_duration(self, master_node, pod, container, delay,
                                  file_path=DTM_CFG['delay_file_path']):
        """
        Set the process restart delay in '/etc/cortx/proc_delay'
        This is set to control the time interval for process to restart after killing it.
        :param master_node: Master node object
        :param pod: Pod Selected
        :param container: Container Selected
        :param delay: interval for process to restart after killing it.(in Seconds)
        :param file_path: File path within the container
        """
        local_path = '/root/proc_delay'
        self.log.info("Modify the restart delay to %s", delay)
        master_node.write_file(local_path, str(delay))
        master_node.copy_file_to_container(local_path, pod, file_path, container)

    # pylint: disable-msg=too-many-locals
    def process_restart_with_delay(self, master_node, health_obj, pod_prefix, container_prefix,
                                   process,
                                   check_proc_state: bool = False, proc_state: str =
                                   const.DTM_RECOVERY_STATE, restart_cnt: int = 1,
                                   proc_restart_delay: int = 600):
        """
        Restart specified Process of specific pod and container
        :param master_node: Master node object
        :param health_obj: Health object of the master node
        :param pod_prefix: Pod Prefix
        :param container_prefix: Container Prefix
        :param process: Process to be restarted.
        :param check_proc_state: Flag to check process state
        :param proc_state: Expected state of the process
        :param restart_cnt: Count to restart process from randomly selected pod (Restart once
        previously restarted process recovers)
        :param proc_restart_delay: Delay in seconds to restart the process after killing it.
        return : boolean
        """

        self.log.info("Get process IDs of %s", process)
        resp = self.get_process_ids(health_obj=health_obj, process=process)
        if not resp[0]:
            return resp[0]
        process_ids = resp[1]
        delay = resp[2]
        for i_i in range(restart_cnt):
            self.log.info("Restarting %s process for %s time", process, i_i + 1)
            self.log.info("Selecting Pod and container for restart")
            pod_selected, container = master_node.select_random_pod_container(pod_prefix,
                                                                              container_prefix)
            self.set_proc_restart_duration(master_node, pod_selected, container, proc_restart_delay)
            try:
                self.log.info("Kill %s from %s pod %s container ", process, pod_selected, container)
                resp = master_node.kill_process_in_container(pod_name=pod_selected,
                                                             container_name=container,
                                                             process_name=process)
                self.log.debug("Resp : %s", resp)
                self.log.info("Sleep till %s", proc_restart_delay)
                # added 20 seconds delay for container to restart.
                time.sleep(proc_restart_delay + 20)
                self.set_proc_restart_duration(master_node, pod_selected, container, 0)
            except (ValueError, IOError) as ex:
                self.log.error("Exception Occurred during killing process : %s", ex)
                self.set_proc_restart_duration(master_node, pod_selected, container, 0)
                return False

            self.log.info("Polling hctl status to check if all services are online")
            resp = self.ha_obj.poll_cluster_status(pod_obj=master_node, timeout=300)
            if not resp[0]:
                return resp[0]

            if check_proc_state:
                self.log.info("Check process states")
                resp = self.poll_process_state(master_node=master_node, pod_name=pod_selected,
                                               container_name=container, process_ids=process_ids,
                                               status=proc_state)
                if not resp:
                    self.log.error("Failed during polling status of process")
                    return False
                self.log.info("Process %s restarted successfully", process)

            if restart_cnt > 1:
                time.sleep(delay)

        return True

    def multi_process_restart_with_delay(self, master_node, health_obj, pod_prefix,
                                         container_prefix, process,
                                         check_proc_state: bool = False,
                                         proc_state: str = const.DTM_RECOVERY_STATE,
                                         k_value: int = 1, proc_restart_delay: int = 300,
                                         kill_restart_delay: int = 120):
        """
        Restart specified Process of specific pod and container
        :param master_node: Master node object
        :param health_obj: Health object of the master node
        :param pod_prefix: Pod Prefix
        :param container_prefix: Container Prefix
        :param process: Process to be restarted.
        :param check_proc_state: Flag to check process state
        :param proc_state: Expected state of the process
        :param k_value: number of processes to be restarted
        :param kill_restart_delay: Delay in seconds to restart the process after killing it.
        :param proc_restart_delay: Delay in seconds to restart the process after killing it.
        return : boolean
        """
        copy_pod_container = dict
        self.log.info("Get process IDs of %s", process)
        resp = self.get_process_ids(health_obj=health_obj, process=process)
        if not resp[0]:
            return resp[0]
        process_ids = resp[1]
        pod_list = master_node.get_all_pods(pod_prefix=pod_prefix)
        self.log.info("k_value:: %s", k_value)
        for i_i in range(k_value):
            self.log.info("Restart count for %s process %s in a cluster", i_i + 1, process)
            self.log.info("Selecting Pod and container for restart")
            pod_prefix = pod_list.pop(random.SystemRandom().randint(0, len(pod_list) - 1))
            pod_selected, container = master_node.select_random_pod_container(pod_prefix,
                                                                              container_prefix,
                                                                              specific_pod=True)
            self.set_proc_restart_duration(master_node, pod_selected, container, proc_restart_delay)
            try:
                self.log.info("Kill %s from %s pod %s container ", process, pod_selected, container)
                resp = master_node.kill_process_in_container(pod_name=pod_selected,
                                                             container_name=container,
                                                             process_name=process)
                copy_pod_container.update(pod_selected, container)
                self.log.debug("Resp : %s", resp)
                self.log.info("Sleep till %s", kill_restart_delay)
                time.sleep(kill_restart_delay)
                self.set_proc_restart_duration(master_node, pod_selected, container, 0)
            except (ValueError, IOError) as ex:
                self.log.error("Exception Occurred during killing process : %s", ex)
                self.set_proc_restart_duration(master_node, pod_selected, container, 0)
                return False

        self.log.info("Polling hctl status to check if all services are online")
        resp = self.ha_obj.poll_cluster_status(pod_obj=master_node, timeout=300)
        if not resp[0]:
            return resp[0]

        if check_proc_state:
            for pod, container in copy_pod_container.items():
                self.log.info("Check process states")
                resp = self.poll_process_state(master_node=master_node, pod_name=pod,
                                               container_name=container, process_ids=process_ids,
                                               status=proc_state)
                if not resp:
                    self.log.error("Failed during polling status of process")
                    return False
                self.log.info("Process %s restarted successfully", process)
        return True

    def get_process_state(self, master_node, pod_name, container_name, process_ids: list):
        """
        Function to get given process state
        :param master_node: Object of master node
        :param pod_name: Name of the pod on which container is residing
        :param container_name: Name of the container inside which process is running
        :param process_ids: List of Process IDs
        :return: bool, dict
        e.g. (True, {'0x19': 'M0_CONF_HA_PROCESS_STARTED', '0x28': 'M0_CONF_HA_PROCESS_STARTED'})
        """
        process_state = dict()
        self.log.info("Get processes running inside container %s of pod %s", container_name,
                      pod_name)
        resp = master_node.get_all_cluster_processes(pod_name=pod_name,
                                                     container_name=container_name)
        self.log.info("Extract list of processes having IDs %s", process_ids)
        compile_exp = re.compile('/(.*?):{"state"')
        process_list = [(ele, p_id) for ele in resp for p_id in process_ids
                        if p_id == compile_exp.findall(ele)[0]]
        if len(process_ids) != len(process_list):
            return False, f"All process IDs {process_ids} are not found. " \
                          f"All processes running in container are: {resp}"
        compile_exp = re.compile('"state": "(.*?)"')
        for i_i in process_list:
            stat = compile_exp.findall(i_i[0])[0]
            process_state[i_i[1]] = stat.split('_')[-1]

        return True, process_state

    def poll_process_state(self, master_node, pod_name, container_name, process_ids,
                           status: str = const.DTM_RECOVERY_STATE, timeout: int = 300):
        """
        Helper function to poll the process states
        :param master_node: Object of master node
        :param pod_name: Name of the pod on which container is residing
        :param container_name: Name of the container inside which process is running
        :param process_ids: List of Process IDs
        :param status: Expected status of process
        :param timeout: Poll timeout
        :return: Bool
        """
        resp = False
        process_state = None
        self.log.info("Polling process states")
        start_time = int(time.time())
        while timeout > int(time.time()) - start_time:
            time.sleep(60)
            resp, process_state = self.get_process_state(master_node=master_node, pod_name=pod_name,
                                                         container_name=container_name,
                                                         process_ids=process_ids)
            if not resp:
                self.log.info("Failed to get process states for process with IDs %s. "
                              "process_state dict: %s", process_ids, process_state)
                return resp
            self.log.debug("Process states: %s", process_state)
            states = list(process_state.values())
            resp = all(ele == status for ele in states)
            if resp:
                self.log.debug("Time taken by process to recover is %s seconds",
                               int(time.time()) - start_time)
                break

        self.log.info("State of process is : %s", process_state)
        return resp

    @staticmethod
    def get_process_ids(health_obj, process):
        """
        Function to get process IDs of given process
        :param health_obj: Health object of the master node
        :param process: Name of the process
        :return: bool, list
        """
        switcher = {
            'm0d': {'svc': const.M0D_SVC, 'delay': DTM_CFG["m0d_delay_restarts"]},
            'radosgw': {'svc': const.SERVER_SVC, 'delay': DTM_CFG["rgw_delay_restarts"]}
        }
        resp, fids = health_obj.hctl_status_get_svc_fids()
        if not resp:
            return resp, "Failed to get process IDs"
        svc = switcher[process]['svc']
        delay = switcher[process]['delay']
        fids = fids[svc]
        return True, fids, delay

    def perform_object_overwrite(self, bucket_name, object_name, iteration, object_size, queue):
        """
        Function to overwrite same object with random object generated for each iteration
        :param bucket_name : Pre created Bucket name for creating object
        :param object_name : object name to create and overwrite
        :param iteration: Number of time to overwrite same object
        :param object_size : Maximum object size that can be created (size in MB)
        :param queue: Multiprocessing Queue to be used for returning values (Boolean,str)
        """
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists")
            system_utils.make_dirs(TEST_DATA_FOLDER)

        self.log.info("Bucket Name : %s", bucket_name)
        self.log.info("Object Name : %s", object_name)
        self.log.info("Total Iteration : %s", iteration)
        self.log.info("Max Object size : %sMB", object_size)
        ret_resp = True, "Overwrites successful."
        for i_i in range(iteration):
            self.log.info("Iteration : %s", i_i+1)
            file_size = random.SystemRandom().randint(0, object_size)  # in mb
            file_path = os.path.join(TEST_DATA_FOLDER, object_name)

            self.log.info("Creating a file with name %s", object_name)
            system_utils.create_file(file_path, file_size, "/dev/urandom", '1M')

            self.log.info("Retrieving checksum of file %s", object_name)
            resp = system_utils.get_file_checksum(file_path)
            if not resp[0]:
                ret_resp = resp
                break
            chksm_before_put_obj = resp[1]

            self.log.info("Uploading a object %s to a bucket %s", object_name, bucket_name)
            _ = self.s3t_obj.put_object(bucket_name, object_name, file_path)

            self.log.info("Removing local file from client and downloading object")
            system_utils.remove_file(file_path)
            resp = self.s3t_obj.get_object(bucket=bucket_name, key=object_name)
            with open(file_path, "wb") as data:
                data.write(resp[1]['Body'].read())

            self.log.info("Verifying checksum of downloaded file")
            resp = system_utils.get_file_checksum(file_path)
            if not resp[0]:
                ret_resp = resp
                break

            chksm_after_dwnld_obj = resp[1]
            if chksm_after_dwnld_obj != chksm_before_put_obj:
                ret_resp = False, f"Checksum does not match, Expected {chksm_before_put_obj} " \
                                  f"Received {chksm_after_dwnld_obj}"
                break

            self.log.info("Delete downloaded file")
            system_utils.remove_file(file_path)
        queue.put(ret_resp)

    def perform_copy_objects(self, workload, que):
        """
        function to perform copy object for dtm test case in background
        :param workload: Python dict containing source and destination bucket and object
        :param que: Multiprocessing Queue to be used for returning values (Boolean,dict)
        """
        failed_obj_name = list()
        for obj_name in workload["obj_list"]:
            try:
                self.s3t_obj.copy_object(source_bucket=workload["source_bucket"],
                                         source_object=obj_name,
                                         dest_bucket=workload["dest_bucket"], dest_object=obj_name)

            except CTException as error:
                self.log.exception("Error: %s", error)
                failed_obj_name.append(obj_name)
        if len(failed_obj_name) > 0:
            que.put([False, f"Copy Object operation failed for {failed_obj_name}"])
        else:
            que.put([True, "Copy Object operation successful"])

    def edit_deployments_for_delay(self, master_node: LogicalNode, deployment_name, service_name):
        """
        Edit deployment for Specified pod and service.
        Append the sleep command for controlled restart of test.
        :param master_node: Logical node object for Master node
        :param deployment_name: Deployment name retrieved from kubectl get deployment
        :param service_name: Service name whose start command is to be modified.
        :return Tuple
        """
        self.log.info("Modifying deployment for %s pod and %s service", deployment_name,
                      service_name)
        delay_file = DTM_CFG['delay_file_path']
        cmd = f"/bin/bash -c '[ -e {delay_file} ] && sleep $(cat {delay_file})';"
        update_done = False
        resp = master_node.backup_deployment(deployment_name)
        if not resp[0]:
            return resp
        remote_path = resp[1]

        # modify deployment
        local_path = os.path.join("/root", f'{deployment_name}.yaml')
        master_node.copy_file_to_local(remote_path=remote_path, local_path=local_path)
        with open(local_path) as soln:
            conf = yaml.safe_load(soln)
            for each in conf['spec']['template']['spec']['containers']:
                if service_name in each['args'][1]:
                    if cmd not in each['args'][1]:
                        new_cmd = each['args'][1] + '; ' + cmd
                        each['args'][1] = new_cmd
                    update_done = True
        if not update_done:
            return False, f"Could not find {service_name} service in {deployment_name}."

        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(local_path, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False, sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        master_node.copy_file_to_remote(local_path, remote_path)
        os.remove(local_path)
        self.log.info("Apply Deployment")
        resp = master_node.apply_k8s_deployment(remote_path)
        return resp
