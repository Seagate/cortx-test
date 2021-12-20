#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
HA test suite for Pod restart
"""

import logging
import os
import random
import time
from time import perf_counter_ns

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestPodRestart:
    """
    Test suite for Pod Restart
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = []
        cls.password = []
        cls.host_master_list = []
        cls.node_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = cls.random_time = cls.s3_clean = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = random.SystemRandom()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.host_master_list.append(cls.host)
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
            else:
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
        if not os.path.exists(cls.test_dir_path):
            resp = system_utils.make_dirs(cls.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        cls.multipart_obj_path = os.path.join(cls.test_dir_path, cls.test_file)

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restored = True
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("Precondition: Run IOs on healthy cluster & Verify DI on the same.")
        resp = self.ha_obj.perform_ios_ops(prefix_data=f'ha-pod-restart-{int(perf_counter_ns())}')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Ran IOs on healthy cluster & Verified DI on the same.")
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restored:
            LOGGER.info("Cleanup: Check cluster status and start it if not up.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            if not resp[0]:
                resp = self.ha_obj.restart_cluster(self.node_master_list[0])
                assert_utils.assert_true(resp[0], resp[1])
            if self.s3_clean:
                LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
                resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
                assert_utils.assert_true(resp[0], resp[1])
            if os.path.exists(self.test_dir_path):
                system_utils.remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34072")
    @CTFailOn(error_handler)
    def test_reads_after_pod_restart(self):
        """
        This test tests READs after data pod restart
        """

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34074")
    @CTFailOn(error_handler)
    def test_write_after_pod_restart(self):
        """
        This test tests WRITEs after data pod restart
        """

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34077")
    @CTFailOn(error_handler)
    def test_deletes_after_pod_restart(self):
        """
        This test tests DELETEs after data pod restart
        """

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34080")
    @CTFailOn(error_handler)
    def test_mpu_after_pod_restart(self):
        """
        This test tests multipart upload after data pod restart
        """

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34082")
    @CTFailOn(error_handler)
    def test_partial_mpu_after_pod_restart(self):
        """
        This test tests partial multipart upload after data pod restart
        """

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34083")
    @CTFailOn(error_handler)
    def test_copy_obj_after_pod_restart(self):
        """
        This test tests copy object after data pod restart
        """