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
HA test suite for Multiple data Pod restart
"""

import logging
import random
import secrets
import time

import pytest

from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from config import HA_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.csm.csm_interface import csm_api_factory

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestMultiDataPodRestart:
    """
    Test suite for Multiple Data Pod Restart
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = []
        cls.password = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.csm_obj = csm_api_factory("rest")
        cls.s3_clean = cls.test_prefix = cls.test_prefix_deg = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.set_type = cls.set_name = cls.last_pod = cls.num_replica = None
        cls.qvalue = cls.kvalue = None
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

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restore_pod = False
        self.s3_clean = dict()
        self.s3acc_name = f"ha_s3acc_{int(time.perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("Get the value for number pods that can go down for cluster")
        resp = self.ha_obj.calculate_multi_value(self.csm_obj, len(self.node_worker_list))
        assert_utils.assert_true(resp[0], resp[1])
        self.qvalue = resp[1]
        LOGGER.info("Getting K value for the cluster")
        resp = self.csm_obj.get_sns_value()
        LOGGER.info("K value for the cluster is: %s", resp[1])
        self.kvalue = resp[1]
        LOGGER.info("Get data pod with prefix %s", const.POD_NAME_PREFIX)
        sts_dict = self.node_master_list[0].get_sts_pods(pod_prefix=const.POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        LOGGER.debug("%s Statefulset: %s", const.POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        self.last_pod = sts_dict[sts][-1]
        self.set_type, self.set_name = self.node_master_list[0].get_set_type_name(
            pod_name=self.last_pod)
        resp = self.node_master_list[0].get_num_replicas(self.set_type, self.set_name)
        assert_utils.assert_true(resp[0], resp)
        self.num_replica = int(resp[1])
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup,
                                                           "num_replica": self.num_replica,
                                                           "set_name": self.set_name})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34091")
    def test_different_data_pods_restart_loop(self):
        """
        This test tests IOs in degraded mode and after data pod restart in loop
        (different data pod down every time)
        """
        LOGGER.info("STARTED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (different data pod down every time)")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34091'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Get data pod list to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        for pod_name in pod_list:
            LOGGER.info("Step 2: Shutdown %s data pod by deleting deployment and "
                        "verify cluster & remaining pods status", pod_name)
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                down_method=const.RESTORE_DEPLOYMENT_K8S, delete_pod=pod_name)
            # Assert if empty dictionary
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            self.deployment_name = resp[1][pod_name]['deployment_name']
            self.deployment_backup = resp[1][pod_name]['deployment_backup']
            self.restore_method = resp[1][pod_name]['method']
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                        "services states are as expected & remaining pods status is online.",
                        pod_name)
            self.restore_pod = True
            LOGGER.info("Step 3: Perform READ/Verify on data written in healthy cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix, skipwrite=True,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: READ/Verify run successfully for data written in healthy cluster.")
            LOGGER.info("Step 4: Run WRITE/READ/Verify in degraded mode")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Create IAM user, create multiple buckets and run IOs")
                users_deg = self.mgnt_ops.create_account_users(nusers=1)
                self.s3_clean.update(users_deg)
                self.test_prefix_deg = 'test-34091-deg'
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                            log_prefix=self.test_prefix_deg,
                                                            skipcleanup=True, setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 4: Successfully ran IOs in degraded mode")
            LOGGER.info("Step 5: Starting pod again by creating deployment using K8s command")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup},
                                           clstr_status=True)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Step 5: Successfully started the pod")
            self.restore_pod = False
            LOGGER.info("Step 6: Run READ/Verify on the written data.")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Run READ/Verify on data written in buckets created in degraded mode.")
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                            log_prefix=self.test_prefix_deg,
                                                            skipwrite=False, skipcleanup=True,
                                                            setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Run READ/Verify on data written in buckets created in healthy cluster.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipwrite=False, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: READ/Verify run successfully.")
            LOGGER.info("Step 7: Run WRITE/READ/Verify again after pod restored")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Run WRITE/READ/Verify in buckets created in degraded mode.")
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                            log_prefix=self.test_prefix_deg,
                                                            skipcleanup=True,
                                                            setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Run WRITE/READ/Verify in buckets created in healthy cluster.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: WRITE/READ/Verify completed successfully.")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Step 8: Create IAM user, create multiple buckets and run IOs")
                users_rst = self.mgnt_ops.create_account_users(nusers=1)
                self.s3_clean.update(users_rst)
                self.test_prefix = 'test-34091-restart'
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                            log_prefix=self.test_prefix,
                                                            skipcleanup=True, setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info("Step 8: Successfully created IAM user and multiple buckets and ran "
                            "IOs")
        LOGGER.info("ENDED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (different data pod down every time)")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34090")
    def test_same_data_pod_restart_loop(self):
        """
        This test tests IOs in degraded mode and after data pod restart in loop
        (same pod down every time)
        """
        LOGGER.info("STARTED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (same pod down every time)")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34090'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Get data pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        loop_count = HA_CFG["common_params"]["loop_count"]
        for loop in range(1, loop_count):
            LOGGER.info("Running loop %s", loop)
            LOGGER.info("Step 2: Shutdown %s data pod by deleting deployment and "
                        "verify cluster & remaining pods status", pod_name)
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                down_method=const.RESTORE_DEPLOYMENT_K8S, delete_pod=pod_name)
            # Assert if empty dictionary
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            self.deployment_name = resp[1][pod_name]['deployment_name']
            self.deployment_backup = resp[1][pod_name]['deployment_backup']
            self.restore_method = resp[1][pod_name]['method']
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                        "services states are as expected & remaining pods status is online.",
                        pod_name)
            self.restore_pod = True
            LOGGER.info("Step 3: Perform READ/Verify on data written in healthy cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix, skipwrite=True,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: READ/Verify run successfully for data written in healthy cluster.")
            LOGGER.info("Step 4: Run WRITE/READ/Verify in degraded mode")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Create IAM user, create multiple buckets and run IOs")
                users_deg = self.mgnt_ops.create_account_users(nusers=1)
                self.s3_clean.update(users_deg)
                self.test_prefix_deg = 'test-34090-deg'
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                            log_prefix=self.test_prefix_deg,
                                                            skipcleanup=True, setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 4: Successfully ran IOs in degraded mode")
            LOGGER.info("Step 5: Starting pod again by creating deployment using K8s command")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup},
                                           clstr_status=True)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Step 5: Successfully started the pod")
            self.restore_pod = False
            LOGGER.info("Step 6: Run READ/Verify on the written data.")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Run READ/Verify on data written in buckets created in degraded mode.")
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                            log_prefix=self.test_prefix_deg,
                                                            skipwrite=False, skipcleanup=True,
                                                            setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Run READ/Verify on data written in buckets created in healthy cluster.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipwrite=False, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: READ/Verify run successfully.")
            LOGGER.info("Step 7: Run WRITE/READ/Verify again after pod restored")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Run WRITE/READ/Verify in buckets created in degraded mode.")
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                            log_prefix=self.test_prefix_deg,
                                                            skipcleanup=True,
                                                            setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Run WRITE/READ/Verify in buckets created in healthy cluster.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: WRITE/READ/Verify completed successfully.")
            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("Step 8: Create IAM user, create multiple buckets and run IOs")
                users_rst = self.mgnt_ops.create_account_users(nusers=1)
                self.s3_clean.update(users_rst)
                self.test_prefix = 'test-34090-restart'
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                            log_prefix=self.test_prefix,
                                                            skipcleanup=True, setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info("Step 8: Successfully created IAM user and multiple buckets and ran "
                            "IOs")
            LOGGER.info("Get recently created data pod name using deployment %s",
                        self.deployment_name)
            pod_name = self.node_master_list[0].get_recent_pod_name(
                deployment_name=self.deployment_name)
        LOGGER.info("ENDED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (same pod down every time)")
