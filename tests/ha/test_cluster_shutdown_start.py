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
import os
import random
import time
from time import perf_counter_ns
from http import HTTPStatus

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.di.di_mgmt_ops import ManagementOPs
from libs.s3.s3_common_test_lib import S3BackgroundIO

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
        cls.s3_clean = cls.test_prefix = cls.s3bench_cleanup = cls.random_time = cls.s3ios = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.mgnt_ops = ManagementOPs()
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
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
        cls.multipart_obj_path = os.path.join(cls.test_dir_path, cls.test_file)

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restored = True
        LOGGER.info("Checking if the cluster and all Pods online.")
        LOGGER.info("Check the status of the pods running in cluster.")
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
        LOGGER.info("Creating a bucket with name : %s", self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        LOGGER.info("Created a bucket with name : %s", self.bucket_name)
        LOGGER.info("Setting up S3 background IO")
        self.s3ios = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        LOGGER.info("All pods are running.")
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
            LOGGER.info("Cleanup: Cleanup S3 background IO artifacts")
            self.s3ios.cleanup()
        LOGGER.info("Teardown completed")

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
    @pytest.mark.tags("TEST-29472")
    @CTFailOn(error_handler)
    def test_mpu_with_cluster_restart_29472(self):
        """
        This test tests multipart upload and download with cluster restart
        """
        LOGGER.info(
            "STARTED: Test to verify multipart upload and download with cluster restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]

        LOGGER.info("Step 1: Do multipart upload for 5GB object")
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=self.bucket_name,
                                                         object_name=self.object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(operation="shutdown_signal",
                                                     resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Cluster shutdown signal sent successfully.")

        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted successfully and all Pods are online.")

        LOGGER.info("Step 4: Download the uploaded object and verify checksum")
        resp = s3_test_obj.get_object(bucket=self.bucket_name, key=self.object_name)
        LOGGER.info("Get object response: %s", resp)
        # TODO: Add checksum verification
        LOGGER.info("Step 4: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 5: Create new bucket and multipart upload and then download 5GB object")
        bucket_name = "mp-bkt-{}".format(self.random_time)
        object_name = "mp-obj-{}".format(self.random_time)
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        resp = s3_test_obj.get_object(bucket=bucket_name, key=object_name)
        LOGGER.info("Get object response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Successfully created bucket and did multipart upload and download "
                    "with 5GB object")

        LOGGER.info("ENDED: Test to verify multipart upload and download with cluster restart")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29474")
    @CTFailOn(error_handler)
    def test_partial_mpu_bfr_aftr_clstr_rstrt_29474(self):
        """
        This test tests partial multipart upload before and after cluster restart
        """
        LOGGER.info(
            "STARTED: Test to verify partial multipart upload before and after cluster restart")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = random.sample(range(1, total_parts), total_parts//2)

        LOGGER.info("Step 1: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially")
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=part_numbers,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=self.multipart_obj_path)
        parts = resp[2]
        mpu_id = resp[1]
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        LOGGER.info("Step 1: Successfully completed partial multipart upload")

        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        if not res[0] or res[1]["Parts"].sort() != part_numbers.sort():
            assert_utils.assert_true(res[0], res)
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(operation="shutdown_signal",
                                                     resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster shutdown signal sent successfully.")

        LOGGER.info("Step 4: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Cluster restarted successfully and all Pods are online.")

        LOGGER.info("Step 5: Upload remaining parts")
        remaining_parts = list(filter(lambda i: i not in part_numbers, range(1, total_parts)))

        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=remaining_parts,
                                                    remaining_upload=True, parts=parts,
                                                    mpu_id=mpu_id)

        assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
        LOGGER.info("Step 5: Successfully uploaded remaining parts")
        LOGGER.info("Step 6: Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        if not res[0] or len(res[1]["Parts"]) != total_parts:
            assert_utils.assert_true(False, res)
        LOGGER.info("Step 6: Listed parts of multipart upload: %s", res[1])
        LOGGER.info("Step 7: Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(mpu_id, parts, self.bucket_name,
                                                            self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        if self.object_name not in res[1]:
            assert_utils.assert_true(False, res)
        LOGGER.info("Step 7: Multipart upload completed")

        LOGGER.info("Step 8: Download the uploaded object and verify checksum")
        resp = s3_test_obj.get_object(bucket=self.bucket_name, key=self.object_name)
        LOGGER.info("Get object response: %s", resp)
        # TODO: Add checksum verification
        LOGGER.info("Step 8: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-29474', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify partial multipart upload before and after cluster "
                    "restart")

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

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29471")
    @CTFailOn(error_handler)
    def test_delete_after_cluster_restart(self):
        """
        This test verifies DELETEs after cluster restart
        """
        LOGGER.info("Started: Test to check DELETEs after cluster restart.")
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        LOGGER.info("Step 1: Create 150 buckets and run IOs on variable size objects.")
        buckets = [f"test-29471-bucket-{i}-{str(int(time.time()))}" for i in range(151)]
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=bucket, skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Sucessfully created 150 buckets & ran IOs on variable size objects.")
        LOGGER.info("Step 2: Verify %s has 150 buckets created", self.s3_clean["user_name"])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(150, len(resp[1]), resp)
        LOGGER.info("Step 2: Verified %s has 150 buckets created", self.s3_clean["user_name"])
        LOGGER.info("Step 3: Verify DI on bucket objects and delete 50 buckets")
        for _ in range(51):
            del_bucket = buckets.pop(self.system_random.randrange(len(buckets)))
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=del_bucket, skipread=True, skipwrite=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Sucessfully verified DI on objects & deleted 50 buckets")
        LOGGER.info("Step 4: Verify %s has 100 buckets are remaining", self.s3_clean["user_name"])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(100, len(resp[1]), resp)
        LOGGER.info("Step 4: Verified %s has 100 buckets are remaining", self.s3_clean["user_name"])
        LOGGER.info("Step 5: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 6: Restart the cluster & check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Cluster restarted fine & all Pods are online.")
        LOGGER.info("Step 7: Verify %s has 100 buckets are remaining", self.s3_clean["user_name"])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(100, len(resp[1]), resp)
        LOGGER.info("Step 7: Verified %s has 100 buckets are remaining", self.s3_clean["user_name"])
        LOGGER.info("Step 8: Delete %s's remaining 100 buckets", self.s3_clean["user_name"])
        for rem_bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=rem_bucket, skipread=True, skipwrite=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Sucessfully deleted %s's remaining 100 buckets",
                    self.s3_clean["user_name"])
        LOGGER.info("Step 9: Create 50 buckets. Run IOs & verify DI. Delete created buckets.")
        buckets = [f"test-29471-bucket-{i}-{str(int(time.time()))}" for i in range(51)]
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.s3_clean, log_prefix=bucket)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Sucessfully created 50 buckets. "
                    "Ran IOs & verified DI. Deleted 50 buckets.")
        LOGGER.info("Step 10: Verify %s has 0 buckets remaining", self.s3_clean["user_name"])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(0, len(resp[1]), resp)
        LOGGER.info("Step 10: Verified %s has 0 buckets remaining", self.s3_clean["user_name"])
        LOGGER.info("Completed: Test to check DELETEs after cluster restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29478")
    @CTFailOn(error_handler)
    def test_ios_during_cluster_restart(self):
        """
        This test verifies IOs during cluster restart
        """
        LOGGER.info("Started: Test to check IOs during cluster restart.")
        LOGGER.info("Step 1. Start parallel S3 IO for 3 minutes duration.")
        self.s3ios.start(log_prefix="TEST-29478_s3bench_ios", duration="0h3m")
        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 3: Shutdown the cluster and check the cluster status.")
        resp = self.ha_obj.cortx_stop_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(CMN_CFG["delay_60sec"])
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 3: Sucessfully shutdown the cluster and verified pods are offline.")
        LOGGER.info("Step 4: Check the parallel s3 IO status while cluster restart in progress")
        # TODO: Need to debug s3bench log file once logs are available with failures
        LOGGER.info("Step 5: Start the cluster and verify all pods are running.")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(CMN_CFG["delay_60sec"])
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Sucessfully started the cluster and verified pods are online.")
        LOGGER.info("Step 6. Stop parallel S3.")
        self.s3ios.stop()
        LOGGER.info("Step 7: Create new s3 account through CSM rest with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Step 7: Created new s3 account through CSM rest with name %s", self.s3acc_name)
        LOGGER.info("Step 8: Create 10 buckets and run S3 IOs on variable size objects.")
        buckets = [f"test-29478-bucket-{i}-{str(int(time.time()))}" for i in range(11)]
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=bucket, skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Created 10 buckets and ran S3 IOs on variable size objects.")
        LOGGER.info("Step 9: Verify %s has 10 buckets created", self.s3_clean["user_name"])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(10, len(resp[1]), resp)
        LOGGER.info("Step 9: Verified %s has 10 buckets created", self.s3_clean["user_name"])
        LOGGER.info("Completed: Test to check IOs during cluster restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29481")
    @CTFailOn(error_handler)
    def test_cluster_shutdown_signal_negative_rest_resp(self):
        """
        This test verifies CSM REST API responses - negative scenario (REST API options validation)
        """
        LOGGER.info("Started: Test to check CSM REST API responses - REST API options validation.")
        LOGGER.info("STEP 1: Perform IOs with variable object sizes")
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        self.test_prefix = 'test_29481'
        resp = self.ha_obj.ha_s3_workload_operation(
            s3userinfo=self.s3_clean, log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed IOs with variable sizes objects.")
        LOGGER.info("Step 2: Verify REST API cluster shutdown signal with bad request body")
        resp = SystemHealth.cluster_operation_signal(
            operation="xyz_signal", resource="cluster", expected_response=HTTPStatus.BAD_REQUEST)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified REST API cluster shutdown signal with bad request body.")
        LOGGER.info("Step 3: Verify REST API cluster shutdown signal with unauthorized request")
        resp = SystemHealth.cluster_operation_signal(
            operation="xyz_signal",
            resource="cluster",
            expected_response=HTTPStatus.UNAUTHORIZED,
            login_as={"username": self.s3acc_name,
                      "password": S3_CFG["CliConfig"]["s3_account"]["password"]})
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Verified REST API cluster shutdown signal with unauthorized request")
        LOGGER.info("Step 4: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 5: Shutdown the cluster and make it unavailable.")
        resp = self.ha_obj.cortx_stop_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(CMN_CFG["delay_60sec"])
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 5: Sucessfully shutdown the cluster.")
        LOGGER.info("Step 6: Verify REST API cluster shutdown signal to unavailable resource")
        resp = SystemHealth.cluster_operation_signal(
            operation="shutdown_signal",
            resource="cluster",
            expected_response=HTTPStatus.INTERNAL_SERVER_ERROR)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Verified REST API cluster shutdown signal with unavailable resource")
        LOGGER.info("Step 7: Start the cluster and verify all pods are running.")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(CMN_CFG["delay_60sec"])
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Sucessfully started the cluster and verified all pods are running.")
        LOGGER.info("Completed: Test to check CSM REST API responses - "
                    "REST API options validation.")
