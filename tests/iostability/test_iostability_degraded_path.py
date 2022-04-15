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
"""Test Suite for IO stability Happy Path workloads."""
import logging
import os
import random
import time
from datetime import datetime, timedelta

import pytest

from commons import configmanager
from commons.constants import K8S_SCRIPTS_PATH, POD_NAME_PREFIX
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils, system_utils, support_bundle_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from conftest import LOG_DIR
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


class TestIOWorkloadDegradedPath:
    """Test suite for IO Stability in Degraded path."""

    @classmethod
    def setup_class(cls):
        """Setup class."""
        cls.log = logging.getLogger(__name__)
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.master_node_list = []
        cls.worker_node_list = []
        cls.hlth_master_list = []
        for node in CMN_CFG['nodes']:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            if node["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
                cls.hlth_master_list.append(Health(hostname=node["hostname"],
                                                   username=node["username"],
                                                   password=node["password"]))
            else:
                cls.worker_node_list.append(node_obj)
        cls.ha_obj = HAK8s()
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/iostability_test.yaml")
        cls.setup_type = CMN_CFG["setup_type"]
        cls.s3t_obj = S3TestLib(access_key=ACCESS_KEY, secret_key=SECRET_KEY)
        cls.test_completed = False

    def teardown_class(self):
        """Teardown class"""
        if not self.test_completed:
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                                   scripts_path=K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)

    def execute_workload_distribution(self, distribution, clients, total_obj,
                                      duration_in_days, log_file_prefix, buckets_created=None):
        """Execution given workload distribution.
        :param distribution: Distribution of object size
        :param clients: No of clients
        :param total_obj: total number of objects per iteration
        :param duration_in_days: Duration expected of the test run
        :param log_file_prefix: Log file prefix for s3bench
        :param buckets_created: Buckets already created to be used for IO operations.
        """
        workloads = [(size, int(total_obj * percent / 100)) for size, percent in
                     distribution.items()]
        end_time = datetime.now() + timedelta(days=duration_in_days)
        loop = 0
        while datetime.now() < end_time:
            for size, samples in workloads:
                bucket_name = f"{log_file_prefix}-bucket-{loop}-{str(int(time.time()))}".lower()
                skip_cleanup = False
                if buckets_created is not None:
                    bucket_name = buckets_created[loop % len(buckets_created)]
                    skip_cleanup = True
                if samples == 0:
                    continue
                cur_clients = clients
                if cur_clients > samples:
                    cur_clients = samples
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                       num_clients=cur_clients, num_sample=samples,
                                       obj_name_pref="object-", obj_size=size,
                                       skip_cleanup=skip_cleanup, duration=None,
                                       log_file_prefix=log_file_prefix, end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                self.log.info("Loop: %s Workload: %s objects of %s with %s parallel clients.",
                              loop, samples, size, clients)
                self.log.info("Log Path %s", resp[1])
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload failed in loop {loop}. Please read log file {resp[1]}"
                system_utils.remove_file(resp[1])
                if skip_cleanup:
                    self.log.info("Delete Created Objects")
                    resp = self.s3t_obj.object_list(bucket_name=bucket_name)
                    obj_list = resp[1]
                    while len(obj_list):
                        if len(obj_list) > 1000:
                            self.s3t_obj.delete_multiple_objects(bucket_name, obj_list=obj_list[0:1000])
                            obj_list = obj_list[1000:]
                        else:
                            self.s3t_obj.delete_multiple_objects(bucket_name=bucket_name, obj_list=obj_list)
                            obj_list = []
                    self.log.info("Objects deletion completed")
            loop += 1

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40172")
    def test_object_crud_single_pod_failure(self):
        """Perform Object CRUD operations in degraded mode in loop using S3bench for 7 days"""
        self.log.info("Step 1: Create 50 buckets in healthy mode ")
        bucket_creation_healthy_mode = self.test_cfg['test_40172']['bucket_creation_healthy_mode']
        bucket_list = None
        if bucket_creation_healthy_mode:
            resp = self.s3t_obj.create_multiple_buckets(50, 'test-40172')
            bucket_list = resp[1]
            self.log.info("Step 1: Bucket created in healthy mode ")
        else:
            self.log.info("Step 1: Skipped bucket creation in healthy mode ")

        self.log.info("Step 2: Shutdown the data pod safely by making replicas=0")
        self.log.info("Get pod name to be deleted")
        pod_list = self.master_node_list[0].get_all_pods(pod_prefix=POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.master_node_list[0].get_pod_hostname(pod_name=pod_name)

        self.log.info("Deleting pod %s", pod_name)
        resp = self.master_node_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        self.log.info("Step 2: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)

        self.log.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        assert_utils.assert_false(resp[0], resp)
        self.log.info("Step 3: Cluster is in degraded state")

        self.log.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        self.log.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        self.log.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        self.log.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 5: Services of pod are in online state")

        self.log.info("Step 6: Perform IO's using S3bench")
        duration_in_days = self.test_cfg['test_40172']['duration_days']
        workload_distribution = self.test_cfg['workloads_distribution']

        clients = (len(self.worker_node_list) - 1) * self.test_cfg['sessions_per_node_vm']
        total_obj = 10000
        if self.setup_type == 'HW':
            clients = (len(self.worker_node_list) - 1) * self.test_cfg['sessions_per_node_hw']
        self.execute_workload_distribution(distribution=workload_distribution, clients=clients,
                                           total_obj=total_obj, duration_in_days=duration_in_days,
                                           log_file_prefix='test-40172',
                                           buckets_created=bucket_list)
        self.test_completed = True
