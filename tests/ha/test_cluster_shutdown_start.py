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
HA test suite for Cluster Shutdown: Immediate.
"""

import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from config import HA_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.di.di_mgmt_ops import ManagementOPs

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
class TestClusterShutdownStart:
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
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = True
        cls.s3_clean = cls.test_prefix = cls.s3bench_cleanup = None
        cls.mgnt_ops = ManagementOPs()

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

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restored = True
        LOGGER.info("Checking if the cluster and all Pods online.")
        # TODO: Will need to check cluster health with health helper once available

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restored:
            LOGGER.info("Cleanup: Check cluster status and start it if not up.")
            # TODO: Will use health helper once available.

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

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29301")
    @CTFailOn(error_handler)
    def test_cluster_shutdown_start(self):
        """
        This test tests the cluster shutdown and start functionality.
        """
        LOGGER.info(
            "STARTED: Test to verify cluster shutdown and restart functionality.")

        LOGGER.info("Step 1: Check the status of the pods running in cluster.")
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: All pods are running.")

        LOGGER.info(
            "Step 2: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-29301', nusers=1,
                                           nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        LOGGER.info("Step 2: IOs are started successfully.")

        LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(operation="shutdown_signal",
                                                     resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster shutdown signal is successful.")

        LOGGER.info(
            "Step 4: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 4: Cluster restarted fine and all Pods online.")

        LOGGER.info("Step 5: Check DI for IOs run before restart.")
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Verified DI for IOs run before restart.")

        LOGGER.info("Step 6: Create new S3 account and perform IOs.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-29301-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs running successfully with new S3 account.")
        self.restored = False

        LOGGER.info(
            "Completed: Test to verify cluster shutdown and restart functionality.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29468")
    @CTFailOn(error_handler)
    def test_cluster_restart_multiple(self):
        """
        This test tests the cluster shutdown and start functionality, in loop
        to check the consistency.
        """
        LOGGER.info(
            "STARTED: Test to verify cluster shutdown and restart functionality in loop.")

        LOGGER.info("Step 1: Check the status of the pods running in cluster.")
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: All pods are running.")

        loop_count = HA_CFG["common_params"]["loop_count"]
        for loop in range(1, loop_count):
            LOGGER.info("Checking cluster restart for %s count", loop)

            LOGGER.info("Step 2: Start IOs (create s3 acc, buckets and upload objects).")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-29468', nusers=1,
                                               nbuckets=10)
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_clean = resp[2]
            LOGGER.info("Step 2: IOs are started successfully.")

            LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
            resp = SystemHealth.cluster_operation_signal(operation="shutdown_signal",
                                                         resource="cluster")
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: Cluster shutdown signal is successful.")

            LOGGER.info("Step 4: Restart the cluster and check cluster status.")
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 4: Cluster restarted fine and all Pods online.")

            LOGGER.info("Step 5: Check DI for IOs run before restart.")
            resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 5: Verified DI for IOs run before restart.")

            LOGGER.info("Step 6: Create new S3 account and perform IOs.")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-29468-new')
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_clean = resp[2]
            resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: IOs running successfully with new S3 account.")
            self.restored = False
            LOGGER.info("Cluster restart was successful for %s count", loop)

        LOGGER.info(
            "Completed: Test to verify cluster shutdown and restart functionality in loop.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29469")
    @CTFailOn(error_handler)
    def test_reads_after_cluster_restart(self):
        """
        This test verifies READs after cluster restart on WRITEs before shutdown
        """
        LOGGER.info("Started: Test to check READs after cluster restart on WRITEs before shutdown.")
        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test_29469'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(
            s3userinfo=list(users.values())[0],
            log_prefix=self.test_prefix,
            skipread=True,
            skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")
        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted fine and all Pods online.")
        LOGGER.info("Step 4: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(
            users.values())[0], log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3bench_cleanup = None
        LOGGER.info("Step 4: Performed READs and verified DI on the written data")
        LOGGER.info("Step 5: Delete all the test objects, buckets and s3 user")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        self.restored = False
        LOGGER.info("Step 5: Deleted all the test objects, buckets and s3 user")
        LOGGER.info(
            "Completed: Test to check READs after cluster restart on WRITEs before shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29470")
    @CTFailOn(error_handler)
    def test_write_after_cluster_restart(self):
        """
        This test verifies WRITEs after cluster restart
        """
        LOGGER.info("Started: Test to check WRITEs after cluster restart.")
        LOGGER.info("STEP 1: Perform IOs with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test_29470'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(
            s3userinfo=list(users.values())[0], log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed IOs with variable sizes objects.")
        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted fine and all Pods online.")
        LOGGER.info("STEP 4: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB). "
            "Verify READs and DI on the written data.")
        resp = self.ha_obj.ha_s3_workload_operation(
            s3userinfo=list(users.values())[0], log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs with variable sizes objects."
                    "Verified READs and verified DI on the written data.")
        self.s3bench_cleanup = None
        LOGGER.info("Step 5: Delete all the test objects, buckets and s3 user")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        self.restored = False
        LOGGER.info("Step 5: Deleted all the test objects, buckets and s3 user")
        LOGGER.info("Completed: Test to check WRITEs after cluster restart.")
