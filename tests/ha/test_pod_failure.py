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
HA test suite for Pod Failure
"""

import logging
import os
import random
import secrets
import threading
import time
from multiprocessing import Process
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import constants as const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import create_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
class TestPodFailure:
    """
    Test suite for Pod Failure
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
        cls.s3_clean = cls.test_prefix = cls.random_time = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()

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
            make_dirs(cls.test_dir_path)
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
        self.restore_pod = self.restore_method = self.deployment_name = None
        self.deployment_backup = None
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
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
                remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32443")
    @CTFailOn(error_handler)
    def test_degraded_reads_safe_pod_shutdown(self):
        """
        This test tests degraded reads before and after safe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded reads before and after safe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32443'
        self.s3_clean = users
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
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info(
            "ENDED: Test to verify degraded reads before and after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23553")
    @CTFailOn(error_handler)
    def test_degraded_reads_unsafe_pod_shutdown(self):
        """
        This test tests degraded reads before and after unsafe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded reads before and after unsafe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-23553'
        self.s3_clean = users
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
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info(
            "ENDED: Test to verify degraded reads before and after unsafe pod shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23552")
    @CTFailOn(error_handler)
    def test_degraded_writes_safe_pod_shutdown(self):
        """
        This test tests degraded writes before and after safe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded writes before and after safe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes. 0B + (1KB - "
                    "512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-23552'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in online state")

        LOGGER.info("Step 6: Perform WRITEs, READs and verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully performed WRITEs, READs and verify DI on the written "
                    "data")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-23552', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info(
            "ENDED: Test to verify degraded writes before and after safe pod shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26440")
    @CTFailOn(error_handler)
    def test_degraded_writes_unsafe_pod_shutdown(self):
        """
        This test tests degraded writes before and after unsafe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded writes before and after unsafe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes. "
                    "0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-26440'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in online state")

        LOGGER.info("Step 6: Perform WRITEs, READs and verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully performed WRITEs, READs and verify DI on the written "
                    "data")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26440', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info(
            "ENDED: Test to verify degraded writes before and after unsafe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26444")
    @CTFailOn(error_handler)
    def test_degraded_deletes_safe_pod_shutdown(self):
        """
        This test tests degraded deletes before and after safe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded deletes before and after safe pod shutdown.")
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
        bucket_num = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 1: Create %s buckets and perform WRITEs with variable size objects.",
                    bucket_num)
        buckets = [f"test-26444-bucket-{i}-{str(int(time.time()))}" for i in range(bucket_num + 1)]
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=bucket, skipread=True, skipcleanup=True,
                nsamples=1, nclients=1)
            assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(bucket_num, len(resp[1]), resp)
        LOGGER.info("Step 1: Sucessfully created %s buckets & "
                    "perform WRITEs with variable size objects.", bucket_num)
        LOGGER.info("Step 2: Shutdown/Delete the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be Shutdown/Deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)
        LOGGER.info("Shutdown/Delete pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS
        LOGGER.info("Step 3: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster is in degraded state")
        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on pod %s are in offline "
                    "state", pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")
        LOGGER.info("Step 6: Perform DELETEs on random %s buckets", bucket_num-10)
        for _ in range(bucket_num-10+1):
            del_bucket = buckets.pop(self.system_random.randrange(len(buckets)))
            resp = s3_test_obj.delete_bucket(bucket_name=del_bucket, force=True)
            assert_utils.assert_true(resp[0], resp)
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(10, len(resp[1]), resp)
        LOGGER.info("Step 6: Successfully performed DELETEs on random %s buckets", bucket_num-10)
        LOGGER.info("Step 7: Perform READs on the remaining 10 buckets and delete the same.")
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=bucket, skipwrite=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully performed READs on the remaining 10 buckets.")
        LOGGER.info("COMPLETED: Test to verify degraded deletes before & after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26644")
    @CTFailOn(error_handler)
    def test_degraded_deletes_unsafe_pod_shutdown(self):
        """
        This test tests degraded deletes before and after unsafe pod shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded deletes before and after unsafe pod shutdown.")
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
        bucket_num = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 1: Create %s buckets and perform WRITEs with variable size objects.",
                    bucket_num)
        buckets = [f"test-26644-bucket-{i}-{int(perf_counter_ns())}" for i in range(bucket_num + 1)]
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=bucket, skipread=True, skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(bucket_num, len(resp[1]), resp)
        LOGGER.info("Step 1: Sucessfully created %s buckets & "
                    "perform WRITEs with variable size objects.", bucket_num)
        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Delete Deployment for %s pod response: %s", pod_name, resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by Delete Deployment")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        LOGGER.info("Step 3: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster is in degraded state")
        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on %s are in offline "
                    "state", pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")
        LOGGER.info("Step 6: Perform DELETEs on random %s buckets", bucket_num-10)
        for _ in range(bucket_num - 10 + 1):
            del_bucket = buckets.pop(self.system_random.randrange(len(buckets)))
            resp = s3_test_obj.delete_bucket(bucket_name=del_bucket, force=True)
            assert_utils.assert_true(resp[0], resp)
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(10, len(resp[1]), resp)
        LOGGER.info("Step 6: Successfully performed DELETEs on random 140 buckets")
        LOGGER.info("Step 7: Perform READs on the remaining 10 buckets.")
        for bucket in buckets:
            resp = self.ha_obj.ha_s3_workload_operation(
                s3userinfo=self.s3_clean, log_prefix=bucket, skipwrite=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully performed READs on the remaining 10 buckets.")
        LOGGER.info(
            "COMPLETED: Test to verify degraded deletes before and after unsafe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32444")
    @CTFailOn(error_handler)
    def test_continuous_reads_during_pod_down(self):
        """
        This test tests degraded reads while pod is going down
        """
        LOGGER.info("STARTED: Test to verify degraded reads during pod is going down.")
        event = threading.Event()

        LOGGER.info("Step 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32444'
        self.s3_clean = users
        output = Queue()
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    nsamples=50, log_prefix=self.test_prefix,
                                                    skipread=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data in background")
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 50, 'skipwrite': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()

        LOGGER.info("Step 2: Successfully started READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 3: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        event.set()
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")
        event.clear()

        thread.join()
        responses = output.get()
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) < len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")

        LOGGER.info("Step 2: Successfully completed READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32444-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify degraded reads during pod is going down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32455")
    @CTFailOn(error_handler)
    def test_pod_shutdown_delete_deployment(self):
        """
        Verify IOs before and after data pod failure; pod shutdown by deleting deployment.
        """
        LOGGER.info(
            "STARTED: Verify IOs before and after data pod failure; pod shutdown "
            "by deleting deployment.")

        LOGGER.info(
            "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32455')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} "
                                           f"by deleting deployment")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info(
            "Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32455-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 6: IOs completed Successfully.")

        LOGGER.info(
            "Completed: Verify IOs before and after data pod failure; pod shutdown "
            "by deleting deployment.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32456")
    @CTFailOn(error_handler)
    def test_pod_shutdown_kubectl_delete(self):
        """
        Verify IOs before and after data pod failure; pod shutdown deleting pod
        using kubectl delete.
        """
        LOGGER.info(
            "STARTED: Verify IOs before and after data pod failure, "
            "pod shutdown by deleting pod using kubectl delete.")

        LOGGER.info(
            "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32456')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Shutdown the data pod by kubectl delete.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by kubectl delete")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by kubectl delete",
                    pod_name)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32456-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 6: IOs completed successfully.")

        LOGGER.info(
            "Completed: Verify IOs before and after data pod failure, "
            "pod shutdown by deleting pod using kubectl delete.")

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26445")
    @CTFailOn(error_handler)
    def test_continuous_deletes_during_pod_down(self):
        """
        This test tests continuous DELETEs during data pod down by deleting deployment
        """
        LOGGER.info("STARTED: Test to verify continuous DELETEs during data pod down by "
                    "deleting deployment.")
        event = threading.Event()
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = {'s3_acc': {'accesskey': resp[1]["access_key"],
                                    'secretkey': resp[1]["secret_key"],
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=resp[1]["access_key"], secret_key=resp[1]["secret_key"],
                                endpoint_url=S3_CFG["s3_url"])
        bucket_num = HA_CFG["s3_bucket_data"]["no_bck_background_deletes"]
        s3data = {}
        workload = HA_CFG["s3_bucket_data"]["workload_sizes_mbs"]
        LOGGER.info("Step 1: Create %s buckets and put variable size object.", bucket_num)
        for count in range(bucket_num):
            # Workload size in Mb to be uploaded in each bucket
            size_mb = self.system_random.choice(workload)
            bucket_name = f"test-26445-bucket{count}-{size_mb}-{int(perf_counter_ns())}"
            object_name = f"obj_{bucket_name}_{size_mb}"
            file_path = os.path.join(self.test_dir_path, f"{bucket_name}.txt")
            resp = s3_test_obj.create_bucket_put_object(bucket_name, object_name, file_path,
                                                        self.system_random.choice(workload))
            assert_utils.assert_true(resp[0], resp[1])
            upload_chm = self.ha_obj.cal_compare_checksum(file_list=[file_path], compare=False)[0]
            s3data.update({bucket_name: (object_name, upload_chm)})
        LOGGER.info("Step 1: Created %s buckets and uploaded variable size object.", bucket_num)
        LOGGER.info("Step 2: Verify %s has %s buckets created",
                    self.s3_clean['s3_acc']["user_name"], bucket_num)
        buckets = s3_test_obj.bucket_list()
        assert_utils.assert_equal(bucket_num, len(buckets[1]), buckets)
        LOGGER.info("Step 2: Verified %s has %s buckets created",
                    self.s3_clean['s3_acc']["user_name"], bucket_num)
        output = Queue()
        bucket_list = list(s3data.keys())
        LOGGER.info("Step 3: Start Continuous DELETEs in background")
        get_random_buck = random.sample(bucket_list, (bucket_num - 10))
        remain_buck = list(set(bucket_list) - set(get_random_buck))
        args = {'s3_test_obj': s3_test_obj, 's3bucklist': get_random_buck, 'output': output}
        thread = threading.Thread(target=self.ha_obj.delete_s3_bucket_data,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 3: Successfully started DELETEs in background")

        LOGGER.info("Step 4: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        event.set()
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 4: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 5: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 5: Cluster is in degraded state")

        LOGGER.info("Step 6: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod %s are in offline state", pod_name)

        LOGGER.info("Step 7: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Services status on remaining pod are in online state")
        event.clear()
        thread.join()
        responses = output.get()
        assert_utils.assert_false(len(responses['pass_buck_del']),
                                  f"Bucket deletion failed when cluster was online"
                                  f"{responses['pass_buck_del']}")
        LOGGER.info("Step 8: Verify status for In-flight DELETEs while pod is going down "
                    "and Download and verify checksum on remaining/FailedToDelete buckets.")
        failed_buck = responses['fail_buck_del']
        LOGGER.info("Get the buckets from expected failed buckets list which FailedToDelete")
        remain_buck.extend(failed_buck)
        for bucket_name in remain_buck:
            download_file = self.test_file + str(s3data[bucket_name][0])
            download_path = os.path.join(self.test_dir_path, download_file)
            resp = s3_test_obj.object_download(
                bucket_name, s3data[bucket_name][0], download_path)
            LOGGER.info("Download object response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                                 compare=False)[0]
            assert_utils.assert_equal(s3data[bucket_name][1], download_checksum,
                                      f"Failed to match checksum: {s3data[bucket_name][1]},"
                                      f" {download_checksum}")
        LOGGER.info("Step 8: Verified status for In-flight DELETEs while pod is going down"
                    "and downloaded and verified checksum for remaining/FailedToDelete buckets.")

        LOGGER.info("Cleaning up s3 user data")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26445', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")
        LOGGER.info("ENDED: Test to verify Continuous DELETEs during data pod down by delete "
                    "deployment.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26441")
    @CTFailOn(error_handler)
    def test_continuous_writes_during_pod_down(self):
        """
        This test tests Continuous WRITEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify Continuous WRITEs during data pod down by delete "
                    "deployment.")
        event = threading.Event()
        LOGGER.info("Step 1: Perform Continuous WRITEs with variable object sizes. 0B + (1KB - "
                    "512MB) during data pod down by delete deployment.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-26441'
        self.s3_clean = users
        output = Queue()

        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 30, 'skipread': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started WRITES in background")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)

        LOGGER.info("Deleting pod %s", pod_name)
        event.set()
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod %s are in offline state", pod_name)

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")
        event.clear()
        thread.join()
        responses = output.get()
        LOGGER.info("Step 6: Verify status for In-flight WRITEs while pod is going down "
                    "should be failed/error.")
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Expected Pass, But Logs which contain failures:"
                                                f" {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) < len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")
        LOGGER.info("Step 6: Verified status for In-flight WRITEs while pod is going down is "
                    "failed/error.")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26441', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")
        LOGGER.info("ENDED: Test to verify Continuous WRITEs during data pod down by delete "
                    "deployment.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32454")
    @CTFailOn(error_handler)
    def test_io_operation_pod_shutdown_scale_replicas(self):
        """
        Verify IOs before and after data pod failure; pod shutdown by making replicas=0
        """
        LOGGER.info(
            "STARTED: Verify IOs before and after data pod failure; pod shutdown "
            "by making replicas=0")

        LOGGER.info(
            "Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32454')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 1: IOs are completed successfully.")

        LOGGER.info("Step 2: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be shutdown")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)
        LOGGER.info("Shutdown pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to shutdown pod {pod_name} by making "
                                  "replicas=0")
        LOGGER.info("Step 2: Successfully shutdown pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info(
            "Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32454-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean = resp[2]
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        LOGGER.info("Step 6: IOs are completed successfully.")

        LOGGER.info(
            "Completed: Verify IOs before and after data pod failure; pod shutdown "
            "by making replicas 0")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32447")
    @CTFailOn(error_handler)
    def test_mpu_during_pod_unsafe_shutdown(self):
        """
        This test tests multipart upload during data pod shutdown (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify multipart upload during data pod shutdown by delete "
                    "deployment")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts))
        random.shuffle(part_numbers)
        output = Queue()
        failed_parts = dict()
        parts_etag = list()
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size, 'total_parts': total_parts,
                'multipart_obj_path': self.multipart_obj_path, 'part_numbers': part_numbers,
                'parts_etag': parts_etag, 'output': output}
        prc = Process(target=self.ha_obj.start_random_mpu, kwargs=args)
        prc.start()
        LOGGER.info("Step 1: Started multipart upload of 5GB object in background")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 3: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Verified cluster status is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services on %s are in offline state", pod_name)

        LOGGER.info("Step 5: Check services status on remaining pods %s are in online state",
                    pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pods %s are in online state",
                    pod_list.remove(pod_name))
        prc.join()
        if output.empty():
            assert_utils.assert_true(False, "Background process failed to do multipart upload")
        res = output.get()
        mpu_id = None
        if isinstance(res[0], dict):
            failed_parts = res[0]
            parts_etag = res[1]
            mpu_id = res[2]
        elif isinstance(res[0], list):
            LOGGER.info("All the parts are uploaded successfully")
            parts_etag = res[0]
            mpu_id = res[1]

        if bool(failed_parts):
            LOGGER.info("Step 6: Upload parts which failed while stopping pod.")
            resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                        bucket_name=self.bucket_name,
                                                        object_name=self.object_name,
                                                        part_numbers=list(failed_parts.keys()),
                                                        remaining_upload=True, parts=failed_parts,
                                                        mpu_id=mpu_id, parts_etag=parts_etag)

            assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
            LOGGER.info("Step 6: Successfully uploaded remaining parts")

        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 7: Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        if not res[0] or len(res[1]["Parts"]) != total_parts:
            assert_utils.assert_true(False, res)
        LOGGER.info("Step 7: Listed parts of multipart upload: %s", res[1])

        LOGGER.info("Step 8: Completing multipart upload and check upload size is %s",
                    file_size * const.Sizes.MB)
        res = self.s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                            self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        LOGGER.info("Step 8: Multipart upload completed and verified upload object size is %s",
                    obj_size)

        LOGGER.info("Step 9: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 9: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 10: Create multiple buckets and run IOs and verify DI one the same")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32447', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 10: Successfully created multiple buckets and ran IOs")

        LOGGER.info("COMPLETED: Test to verify multipart upload during data pod shutdown by delete "
                    "deployment")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32449")
    @CTFailOn(error_handler)
    def test_partial_mpu_after_pod_unsafe_shutdown(self):
        """
        This test tests degraded partial multipart upload after data pod unsafe shutdown
        by deleting deployment
        """
        LOGGER.info(
            "STARTED: Test to verify degraded partial multipart upload after data pod unsafe "
            "shutdown by deleting deployment")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = random.sample(list(range(1, total_parts+1)), total_parts//2)
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        create_file(self.multipart_obj_path, file_size)
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

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
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                            endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=part_numbers,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=self.multipart_obj_path)
        mpu_id = resp[1]
        object_path = resp[2]
        parts_etag1 = resp[3]
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        LOGGER.info("Step 1: Successfully completed partial multipart upload")

        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 3: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 4: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Verified cluster status is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pod %s are in offline "
                    "state", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services on %s are in offline state", pod_name)

        LOGGER.info("Step 6: Check services status on remaining pods %s are in online state",
                    pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services status on remaining pods %s are in online state",
                    pod_list.remove(pod_name))

        LOGGER.info("Step 7: Upload remaining parts")
        remaining_parts = list(filter(lambda i: i not in part_numbers, range(1, total_parts+1)))
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=remaining_parts,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)

        assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
        parts_etag2 = resp[3]
        LOGGER.info("Step 7: Successfully uploaded remaining parts")

        etag_list = parts_etag1 + parts_etag2
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])

        LOGGER.info("Step 8: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 8: Listed parts of multipart upload: %s", res[1])

        LOGGER.info("Step 9: Completing multipart upload Completing multipart upload and check "
                    "upload size is %s", file_size * const.Sizes.MB)
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        if self.object_name not in res[1]:
            assert_utils.assert_true(False, res)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        LOGGER.info("Step 9: Multipart upload completed and verified upload size is %s",
                    file_size * const.Sizes.MB)

        LOGGER.info("Step 10: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 10: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 11: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32449', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 11: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify degraded partial multipart upload after data pod unsafe "
            "shutdown by deleting deployment")
