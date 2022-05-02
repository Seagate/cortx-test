#!/usr/bin/python # pylint: disable=C0302
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
#

"""
Test suite for testing Single Process Restart with DTM enabled.
"""
import logging
import multiprocessing
import os
import random
import time

import pytest

from commons import configmanager
from commons.constants import K8S_SCRIPTS_PATH, POD_NAME_PREFIX, MOTR_CONTAINER_NAME_PREFIX
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import support_bundle_utils, assert_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from conftest import LOG_DIR
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.s3_bench import s3bench


class TestSingleProcessRestart:
    """Test Class for Single Process Restart."""

    @classmethod
    def setup_class(cls):
        """Setup class."""

        cls.log = logging.getLogger(__name__)
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.master_node_list = []
        cls.worker_node_list = []
        for node in CMN_CFG['nodes']:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            if node["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/iostability_test.yaml")
        cls.setup_type = CMN_CFG["setup_type"]
        cls.test_completed = False
        cls.health_obj = Health(cls.master_node_list[0].hostname,
                                cls.master_node_list[0].username,
                                cls.master_node_list[0].password)
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/test_dtm0_config.yaml")
        cls.m0d_process = 'm0d'
        cls.restart_wait_time_secs = 10

    def teardown_method(self):
        """Teardown class method."""
        if not self.test_completed:
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                                   scripts_path=K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)
        # TODO : Redeploy setup after test completion.

    def perform_write_op(self, s3userinfo, bucket_name, object_name, clients, samples, size,
                         log_file_prefix, que=None):
        """
        Perform Write operations
        :param s3userinfo: S3 user info
        :param bucket_name: Bucket name
        :param object_name: Object name
        :param clients: No of Client session
        :param samples: No of samples
        :param size: Object size
        :param log_file_prefix: Log file prefix
        :param que: Multiprocessing Queue to be used for returning values
        return: Tuple in case Que is none.
        """
        self.log.info("Perform Write Operations : ")
        resp = s3bench.s3bench(s3userinfo['accesskey'],
                               s3userinfo['secretkey'], bucket=bucket_name,
                               num_clients=clients, num_sample=samples,
                               obj_name_pref=object_name, obj_size=size,
                               skip_cleanup=True, duration=None,
                               log_file_prefix=str(log_file_prefix).upper(),
                               end_point=S3_CFG["s3_url"],
                               validate_certs=S3_CFG["validate_certs"])
        self.log.info("Workload: %s objects of %s with %s parallel clients.",
                      samples, size, clients)
        self.log.info("Log Path %s", resp[1])

        if que:
            if s3bench.check_log_file_error(resp[1]):
                que.put(False, f"S3bench workload for failed."
                               f" Please read log file {resp[1]}")
            else:
                que.put(True, f"S3bench workload is successful. Please read log file {resp[1]}")

        if s3bench.check_log_file_error(resp[1]):
            return False, f'S3bench workload failed during writes. Please read log file {resp[1]}'
        return True, {'bucket': bucket_name, 'obj_name_pref': object_name, 'num_clients': clients,
                      'obj_size': size, 'num_sample': samples}

    def perform_read_op(self, s3userinfo, workload_info: dict, skipread: bool = True,
                        validate: bool = True, skipcleanup: bool = False, que=None):
        """
        Perform read operations
        :param s3userinfo: S3 user info
        :param workload_info: Workload to read/validate/delet
        :param skipread: Skip read
        :param validate: Validate checksum
        :param skipcleanup: Skip Cleanup
        :param que: Multiprocessing Queue to be used for returning values
        return: Tuple in case Que is none.
        """
        resp = s3bench.s3bench(s3userinfo['accesskey'],
                               s3userinfo['secretkey'],
                               bucket=workload_info['bucket'],
                               num_clients=workload_info['num_clients'],
                               num_sample=workload_info['num_sample'],
                               obj_name_pref=workload_info['obj_name_pref'],
                               obj_size=workload_info['obj_size'],
                               skip_cleanup=skipcleanup,
                               skip_write=True,
                               skip_read=skipread,
                               validate=validate,
                               log_file_prefix=f"read_workload_{workload_info['obj_size']}mb",
                               end_point=S3_CFG["s3_url"],
                               validate_certs=S3_CFG["validate_certs"])
        self.log.info(f"Workload: %s objects of %s with %s parallel clients ",
                      workload_info['num_sample'], workload_info['obj_size'],
                      workload_info['num_clients'])
        self.log.info(f"Log Path {resp[1]}")
        if que:
            if s3bench.check_log_file_error(resp[1]):
                que.put(False, f"S3bench workload for failed."
                               f" Please read log file {resp[1]}")
            else:
                que.put(True, f"S3bench workload is successful. Please read log file {resp[1]}")
        if s3bench.check_log_file_error(resp[1]):
            return False, "S3bench workload failed,Please read log file {resp[1]}"
        return True, f'S3bench workload successful'

    @pytest.mark.lc
    @pytest.mark.dtm0
    @pytest.mark.tags("TEST-41223")
    def test_delete_during_m0d_restart(self):
        """Verify DELETE during m0d restart."""
        self.log.info("STARTED: Verify DELETE during m0d restart.")
        bucket_name = 'bucket-test-41223'
        object_name = 'object-test-41223'
        test_41223_cfg = self.test_cfg['test_41223']

        s3userinfo = dict()
        s3userinfo['accesskey'] = ACCESS_KEY
        s3userinfo['secretkey'] = SECRET_KEY
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform write Operations :")
        resp = self.perform_write_op(s3userinfo=s3userinfo, bucket_name=bucket_name,
                                     object_name=object_name,
                                     clients=test_41223_cfg['clients'],
                                     samples=test_41223_cfg['samples'],
                                     size=test_41223_cfg['size'],
                                     log_file_prefix=test_41223_cfg['log_file_prefix'])
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 2: Perform Delete Operations :")
        proc_read_op = multiprocessing.Process(target=self.perform_read_op, args=(s3userinfo,
                                                                                  que,
                                                                                  workload_info,
                                                                                  True,
                                                                                  True,
                                                                                  False))
        proc_read_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Read Operations")
        pod_list = self.master_node_list[0].get_all_pods(pod_prefix=POD_NAME_PREFIX)
        pod_selected = random.randint(1, len(pod_list) - 1)
        self.log.info("Pod selected for m0d process restart : %s", pod_selected)
        container_list = self.master_node_list[0].get_container_of_pod(pod_name=pod_selected,
                                                                       container_prefix=MOTR_CONTAINER_NAME_PREFIX)
        container = random.randint(1, len(container_list))
        self.log.info("Container selected : %s", container)
        self.log.info("Perform m0d restart")
        resp = self.master_node_list[0].kill_process_in_container(pod_name=pod_selected,
                                                                  container=container,
                                                                  process_name=self.m0d_process)
        self.log.debug("resp : %s", resp)
        time.sleep(self.restart_wait_time_secs)

        self.log.info("Step 4: Check hctl status if all services are online")
        resp = self.health_obj.is_motr_online()
        assert_utils.assert_true(resp, 'All services are not online.')

        self.log.info("Step 5: Wait for Read Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify Delete during m0d restart using pkill -9")
