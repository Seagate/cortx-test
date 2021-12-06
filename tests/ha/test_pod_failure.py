#!/usr/bin/python # pylint: disable=C0302
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
HA test suite for Cluster Shutdown: Immediate.
"""

import logging
import os
import random
import time
from http import HTTPStatus
from multiprocessing import Process, Queue
from time import perf_counter_ns

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from commons.utils.system_utils import remove_file
from commons.utils.system_utils import create_file
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from commons import constants as const
from commons.helpers.health_helper import Health

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
class TestPODFailure:
    """
    Test suite for Cluster shutdown: Immediate.
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
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.hlth_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = True
        cls.s3_clean = cls.test_prefix = cls.s3bench_cleanup = cls.random_time = cls.s3ios = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
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
                cls.hlth_master_list.append(Health(hostname=cls.host,
                                                   username=cls.username[node],
                                                   password=cls.password[node]))
            else:
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
                cls.hlth_worker_list.append(Health(hostname=cls.host,
                                                   username=cls.username[node],
                                                   password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
        if not os.path.exists(cls.test_dir_path):
            resp = make_dirs(cls.test_dir_path)
        cls.multipart_obj_path = os.path.join(cls.test_dir_path, cls.test_file)

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restored = True
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
        self.restore_pod = self.way_to_restore = self.dploymnt_name = self.dploymnt_backup = None
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           way_to_restore=self.way_to_restore,
                                           restore_params={"deployment_name": self.dploymnt_name,
                                                           "deployment_backup": self.dploymnt_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.way_to_restore} way")
            LOGGER.info("Successfully restored pod by %s way", self.way_to_restore)
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

            # Check if s3bench objects cleanup is required
            if self.s3bench_cleanup:
                for user_info in self.s3bench_cleanup.values():
                    resp = self.ha_obj.ha_s3_workload_operation(
                        s3userinfo=user_info, log_prefix=self.test_prefix,
                        skipwrite=True, skipread=True)
                    assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info("Cleanup: Deleted s3 objects and buckets.")

            if os.path.exists(self.test_dir_path):
                remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32443")
    @CTFailOn(error_handler)
    def test_dgrd_rds_bfr_aftr_safe_pod_shutdown(self):
        """
        This test tests degraded reads before and after safe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded reads before and after safe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test_32443'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed READs and verified DI on the written data")

        LOGGER.info("Step 3: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_name = random.sample(list(self.node_master_list[0].get_all_pods_containers(
            pod_prefix=const.POD_NAME_PREFIX).keys()), 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.dploymnt_name = resp[1]
        self.restore_pod = True
        self.way_to_restore = "scale_replicas"

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        LOGGER.info("Step 6: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3bench_cleanup = None
        LOGGER.info("Step 6: Performed READs and verified DI on the written data")

        LOGGER.info(
            "ENDED: Test to verify degraded reads before and after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23553")
    @CTFailOn(error_handler)
    def test_dgrd_rds_bfr_aftr_unsafe_pod_shutdown(self):
        """
        This test tests degraded reads before and after unsafe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded reads before and after unsafe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test_23553'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed READs and verified DI on the written data")

        LOGGER.info("Step 3: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_name = random.sample(list(self.node_master_list[0].get_all_pods_containers(
            pod_prefix=const.POD_NAME_PREFIX).keys()), 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.dploymnt_backup = resp[1]
        self.dploymnt_name = resp[2]
        self.restore_pod = True
        self.way_to_restore = "k8s"

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        LOGGER.info("Step 6: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3bench_cleanup = None
        LOGGER.info("Step 6: Performed READs and verified DI on the written data")

        LOGGER.info(
            "ENDED: Test to verify degraded reads before and after unsafe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23552")
    @CTFailOn(error_handler)
    def test_dgrd_wrts_bfr_aftr_safe_pod_shutdown(self):
        """
        This test tests degraded writes before and after safe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded writes before and after safe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test_23552'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_name = random.sample(list(self.node_master_list[0].get_all_pods_containers(
            pod_prefix=const.POD_NAME_PREFIX).keys()), 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.dploymnt_name = resp[1]
        self.restore_pod = True
        self.way_to_restore = "scale_replicas"

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed READs and verified DI on the written data")

        LOGGER.info("Step 6: Perform WRITEs, READs and verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3bench_cleanup = None
        LOGGER.info("Step 6: Successfully performed WRITEs, READs and verify DI on the written "
                    "data")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-23552', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleaning up accounts and buckets created in IO operations")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(resp[2])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info(
            "ENDED: Test to verify degraded writes before and after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26440")
    @CTFailOn(error_handler)
    def test_dgrd_wrts_bfr_aftr_unsafe_pod_shutdown(self):
        """
        This test tests degraded writes before and after unsafe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded writes before and after unsafe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test_26440'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_name = random.sample(list(self.node_master_list[0].get_all_pods_containers(
            pod_prefix=const.POD_NAME_PREFIX).keys()), 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.dploymnt_backup = resp[1]
        self.dploymnt_name = resp[2]
        self.restore_pod = True
        self.way_to_restore = "k8s"

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Perform READs and verify DI on the written data.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed READs and verified DI on the written data")

        LOGGER.info("Step 6: Perform WRITEs, READs and verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3bench_cleanup = None
        LOGGER.info("Step 6: Successfully performed WRITEs, READs and verify DI on the written "
                    "data")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26440', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleaning up accounts and buckets created in IO operations")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(resp[2])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info(
            "ENDED: Test to verify degraded writes before and after unsafe pod shutdown.")
