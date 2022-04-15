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
import time
from datetime import datetime, timedelta

import pytest

from commons import configmanager
from commons.constants import K8S_SCRIPTS_PATH
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import support_bundle_utils, assert_utils, system_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from conftest import LOG_DIR
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.s3_bench import s3bench


class TestIOWorkload:
    """Test suite for IO workloads."""

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

    def teardown_class(self):
        """Teardown class"""
        if not self.test_completed:
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                                   scripts_path=K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)

    def execute_workload_distribution(self, distribution, clients, total_obj,
                                      duration_in_days, log_file_prefix):
        """Execution given workload distribution.
        :param distribution: Distribution of object size
        :param clients: No of clients
        :param total_obj: total number of objects per iteration
        :param duration_in_days: Duration expected of the test run
        :param log_file_prefix: Log file prefix for s3bench
        """
        workloads = [(size, int(total_obj * percent / 100)) for size, percent in
                     distribution.items()]
        end_time = datetime.now() + timedelta(days=duration_in_days)
        loop = 0
        while datetime.now() < end_time:
            for size, samples in workloads:
                bucket_name = f"{log_file_prefix}-bucket-{loop}-{str(int(time.time()))}".lower()
                if samples == 0:
                    continue
                cur_clients = clients
                if cur_clients > samples:
                    cur_clients = samples
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                       num_clients=cur_clients, num_sample=samples,
                                       obj_name_pref="object-", obj_size=size,
                                       skip_cleanup=False, duration=None,
                                       log_file_prefix=log_file_prefix, end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                self.log.info("Loop: %s Workload: %s objects of %s with %s parallel clients.",
                              loop, samples, size, clients)
                self.log.info("Log Path %s", resp[1])
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload failed in loop {loop}. Please read log file {resp[1]}"
                system_utils.remove_file(resp[1])
            loop += 1

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40039")
    def test_bucket_object_crud_s3bench(self):
        """Perform Bucket and  Object CRUD operations in loop using S3bench for 30 days"""
        duration_in_days = self.test_cfg['test_40039']['duration_days']
        workload_distribution = self.test_cfg['workloads_distribution']
        clients = len(self.worker_node_list) * self.test_cfg['sessions_per_node_vm']
        total_obj = 10000
        if self.setup_type == 'HW':
            clients = len(self.worker_node_list) * self.test_cfg['sessions_per_node_hw']
        self.execute_workload_distribution(distribution=workload_distribution, clients=clients,
                                           total_obj=total_obj, duration_in_days=duration_in_days,
                                           log_file_prefix='test-40039')
        self.test_completed = True
