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
Library Methods for DTM0 delivery testing
"""
import logging
import random
import time

from config import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.s3_bench import s3bench


class DTM0TestLib:

    def __init__(cls, access_key=ACCESS_KEY, secret_key=SECRET_KEY):
        """
        Init method
        :param access_key: Access key for S3bench operations.
        :param secret_key: Secret key for S3bench operations.
        """
        cls.log = logging.getLogger(__name__)
        cls.access_key = access_key
        cls.secret_key = secret_key

    def perform_write_op(self, bucket_prefix, object_name, clients, samples, size,
                         log_file_prefix, queue, loop=1):
        """
        Perform Write operations
        :param bucket_prefix: Bucket name
        :param object_name: Object name
        :param clients: No of Client session
        :param samples: No of samples
        :param size: Object size
        :param log_file_prefix: Log file prefix
        :param queue: Multiprocessing Queue to be used for returning values (Boolean,dict)
        :param loop: Loop count for writes
        """
        results = list()
        workload = list()
        log_path = None
        for i in range(loop):
            self.log.info("Perform Write Operations : ")
            bucket_name = bucket_prefix + str(int(time.time()))
            resp = s3bench.s3bench(self.access_key,
                                   self.secret_key, bucket=bucket_name,
                                   num_clients=clients, num_sample=samples,
                                   obj_name_pref=object_name, obj_size=size,
                                   skip_cleanup=True, duration=None,
                                   log_file_prefix=str(log_file_prefix).upper(),
                                   end_point=S3_CFG["s3_url"],
                                   validate_certs=S3_CFG["validate_certs"])
            self.log.info("Workload: %s objects of %s with %s parallel clients.",
                          samples, size, clients)
            self.log.info("Log Path %s", resp[1])
            log_path = resp[1]
            if s3bench.check_log_file_error(resp[1]):
                results.append(False)
                break
            else:
                results.append(True)
                workload.append({'bucket': bucket_name, 'obj_name_pref': object_name,
                                 'num_clients': clients, 'obj_size': size,
                                 'num_sample': samples})
        res = set(results)
        if not res:
            queue.put(False, f"S3bench workload for failed."
                             f" Please read log file {log_path}")
        else:
            queue.put(True, workload)

    def perform_read_op(self, workload_info: list, queue, skipread: bool = True,
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
        for i in range(loop):
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
                self.log.info(f"Workload: %s objects of %s with %s parallel clients ",
                              workload['num_sample'], workload['obj_size'],
                              workload['num_clients'])
                self.log.info(f"Log Path {resp[1]}")
                log_path = resp[1]
                if s3bench.check_log_file_error(resp[1]):
                    results.append(False)
                    break
                else:
                    results.append(True)
        res = set(results)
        if not res:
            queue.put(False, f"S3bench workload for failed."
                             f" Please read log file {log_path}")
        else:
            queue.put(True, f"S3bench workload is successful. Please read log file {log_path}")

    def process_restart(self, master_node, pod_prefix, container_prefix, process,
                        recover_time: int = 30):
        """
        Restart specified Process of specific pod and container
        :param master_node: Master node object
        :param pod_prefix: Pod Prefix
        :param container_prefix: Container Prefix
        :param process: Process to be restarted.
        :param recover_time: Wait time for process to recover
        """
        pod_list = master_node.get_all_pods(pod_prefix=pod_prefix)
        pod_selected = random.randint(1, len(pod_list) - 1)
        self.log.info("Pod selected for m0d process restart : %s", pod_selected)
        container_list = master_node.get_container_of_pod(pod_name=pod_selected,
                                                          container_prefix=container_prefix)
        container = random.randint(1, len(container_list))
        self.log.info("Container selected : %s", container)
        self.log.info("Perform m0d restart")
        resp = master_node.kill_process_in_container(pod_name=pod_selected,
                                                     container=container,
                                                     process_name=process)
        self.log.debug("resp : %s", resp)
        time.sleep(recover_time)
        # TODO : Check if process has started
        self.log.info("Process restarted ")
