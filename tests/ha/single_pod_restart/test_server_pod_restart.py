#!/usr/bin/python  # pylint: disable=too-many-instance-attributes
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
HA test suite for single server pod restart
"""

import logging
import os
import secrets
from time import perf_counter_ns

import pytest

from commons import constants as const
from commons.helpers.health_helper import Health
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


# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods
class TestServerPodRestart:
    """
    Test suite for single server pod restart
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = list()
        cls.password = list()
        cls.node_master_list = list()
        cls.hlth_master_list = list()
        cls.node_worker_list = list()
        cls.ha_obj = HAK8s()
        cls.s3_clean = cls.test_prefix = cls.test_prefix_deg = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.restore_node = cls.multipart_obj_path = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
                cls.hlth_master_list.append(Health(hostname=cls.host,
                                                   username=cls.username[node],
                                                   password=cls.password[node]))
            else:
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "ha_mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restore_pod = False
        self.s3_clean = dict()
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.extra_files = list()
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Removing extra files")
        for file in self.extra_files:
            system_utils.remove_file(file)
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34089")
    def test_io_server_pod_restart(self):
        """
        Verify IOs before and after server pod restart (setting replica=0 and 1)
        """
        LOGGER.info("STARTED: Verify IOs before and after server pod restart "
                    "(setting replica=0 and 1)")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34089'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects")
        LOGGER.info("Step 2: Shutdown random server pod by making replica=0 and verify cluster"
                    " & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX])
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("STEP 3: Perform READs/Verify on data written in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs/Verify on data written in healthy cluster.")
        LOGGER.info("Step 4: Perform WRITEs/READs/Verify with variable object sizes and new "
                    "buckets in degraded mode")
        self.test_prefix_deg = 'test-34072-deg'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs/READs/Verify with variable sizes objects in "
                    "degraded mode")
        LOGGER.info("Step 5: Restore server pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore server pod by {self.restore_method} "
                                          "way OR the cluster is not online")
        LOGGER.info("Step 5: Successfully started the server pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 6: Perform READs and verify DI on the written data in degraded mode")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully run READ/Verify on data written in degraded mode")
        LOGGER.info("Step 7: Perform READs and verify DI on the written data in healthy cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully run READ/Verify on data written in healthy cluster ")
        LOGGER.info("Step 8: Create IAM user with multiple buckets and run IOs after server pod "
                    "restart by making replicas=1.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34089-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully IOs completed after server pod restart by making "
                    "replicas=1.")
        LOGGER.info("COMPLETED: Verify IOs before and after server pod restart "
                    "(setting replica=0 and 1)")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44834")
    def test_reads_after_server_pod_restart(self):
        """
        This test tests READs after server pod restart
        """
        LOGGER.info("STARTED: Test to verify READs after server pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-44834'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random server pod by deleting deployment and verify cluster"
                    " & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, pod_prefix=[const.SERVER_POD_NAME_PREFIX])
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("STEP 3: Perform READs/Verify on data written in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs/Verify on data written in healthy cluster.")
        LOGGER.info("Step 4: Perform WRITEs/READs/Verify with variable object sizes and create "
                    "bucket in degraded mode")
        self.test_prefix_deg = 'test-44834-deg'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs/READs/Verify with variable sizes objects in "
                    "degraded mode")
        LOGGER.info("Step 5: Restore server pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore server pod by {self.restore_method} "
                                          "way OR the cluster is not online")
        LOGGER.info("Step 5: Successfully started server pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 6: Perform READs and verify DI on the written data in degraded mode")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully run READ/Verify on data written in degraded mode")
        LOGGER.info("Step 7: Perform READ/Verify on data written in healthy mode")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully run READ/Verify on data written in healthy mode")
        LOGGER.info("Step 8: Start IOs again after server pod restart by delete deployment")
        self.test_prefix = 'test-44834-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully IOs completed after server pod restart by delete "
                    "deployment")
        LOGGER.info("ENDED: Test to verify READs after server pod restart.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44836")
    def test_write_after_server_pod_restart(self):
        """
        This test tests WRITEs after server pod restart
        """
        LOGGER.info("STARTED: Test to verify WRITEs after server pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-44836'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random server pod by deleting deployment and verify cluster"
                    " & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, pod_prefix=[const.SERVER_POD_NAME_PREFIX])
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Perform WRITEs/Read/Verify with variable object sizes and new bucket "
                    "in degraded mode")
        self.test_prefix_deg = 'test-44836-deg'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed WRITEs/Read/Verify with variable sizes objects in degraded "
                    "mode")
        LOGGER.info("Step 4: Restore server pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore server pod by {self.restore_method} "
                                          "way OR the cluster is not online")
        LOGGER.info("Step 4: Successfully started server pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 5: Perform WRITE/READs/verify DI on the written data in healthy mode.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully run WRITE/READ/Verify on data written in healthy mode")
        LOGGER.info("Step 6: Perform WRITE/READs/verify DI on the written data in degraded mode.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully run WRITE/READs/Verify on data written in degraded mode")
        LOGGER.info("Step 7: Create new IAM user and buckets, Perform WRITEs-READs-Verify with "
                    "variable object sizes after server pod restart")
        users = self.mgnt_ops.create_account_users(nusers=1)
        test_prefix = 'test-44836-restart'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed WRITEs-READs-Verify with variable sizes objects after "
                    "server pod restart")
        LOGGER.info("ENDED: Test to verify WRITEs after server pod restart.")
