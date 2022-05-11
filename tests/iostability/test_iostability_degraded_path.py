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

import pytest

from commons import configmanager
from commons.constants import K8S_SCRIPTS_PATH, POD_NAME_PREFIX
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils, support_bundle_utils
from config import CMN_CFG
from conftest import LOG_DIR
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.iostability.iostability_lib import IOStabilityLib
from libs.s3.s3_test_lib import S3TestLib


class TestIOWorkloadDegradedPath:

    """Test Class for IO Stability in Degraded path."""

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
        cls.s3t_obj = S3TestLib()
        cls.iolib = IOStabilityLib()
        cls.test_completed = False

    def teardown_method(self):
        """Teardown method."""
        if not self.test_completed:
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                                   scripts_path=K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40172")
    def test_object_crud_single_pod_failure(self):
        """Perform Object CRUD operations in degraded mode in loop using S3bench for 7 days."""
        self.log.info("STARTED: Test for Object CRUD operations in degraded mode in loop using "
                      "S3bench for 7 days")

        self.log.info("Step 1: Create 50 buckets in healthy mode ")
        bucket_creation_healthy_mode = self.test_cfg['test_40172']['bucket_creation_healthy_mode']
        bucket_list = None
        if bucket_creation_healthy_mode:
            resp = self.s3t_obj.create_multiple_buckets(50, 'test-40172')
            bucket_list = resp[1]
            self.log.info("Step 1: Bucket created in healthy mode ")
        else:
            self.log.info("Step 1: Skipped bucket creation in healthy mode ")

        self.log.info("Step 2: Shutdown the data pod safely by making replicas=0,"
                      "check degraded status.")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(self.master_node_list[0],
                                                            self.hlth_master_list[0])
        assert_utils.assert_true(resp[0], "Failed in shutdown or expected cluster check")
        self.log.info("Deleted pod : %s", list(resp[1].keys())[0])

        self.log.info("Step 3: Perform IO's using S3bench")
        duration_in_days = self.test_cfg['degraded_path_durations_days']
        workload_distribution = self.test_cfg['workloads_distribution']

        clients = (len(self.worker_node_list) - 1) * self.test_cfg['sessions_per_node_vm']
        total_obj = 10000
        if self.setup_type == 'HW':
            clients = (len(self.worker_node_list) - 1) * self.test_cfg['sessions_per_node_hw']
        self.iolib.execute_workload_distribution(distribution=workload_distribution,
                                                 clients=clients,
                                                 total_obj=total_obj,
                                                 duration_in_days=duration_in_days,
                                                 log_file_prefix='test-40172',
                                                 buckets_created=bucket_list)
        self.test_completed = True
        self.log.info("ENDED: Test for Object CRUD operations in degraded mode in loop using "
                      "S3bench for 7 days")
