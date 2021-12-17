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
        # args = {'s3_test_obj': s3_test_obj, 's3bucklist': get_random_buck, 'output': output}
        # thread = threading.Thread(target=self.ha_obj.delete_s3_bucket_data,
        #                           args=(event,), kwargs=args)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': output}

        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
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
        assert_utils.assert_false(len(responses['fail_del_bkt']),
                                  f"Bucket deletion failed when cluster was online"
                                  f"{responses['pass_buck_del']}")
        LOGGER.info("Step 8: Verify status for In-flight DELETEs while pod is going down "
                    "and Download and verify checksum on remaining/FailedToDelete buckets.")
        failed_buck = responses['event_del_bkt']
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

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26442")
    @CTFailOn(error_handler)
    def test_continuous_reads_writes_during_pod_down(self):
        """
        This test tests Continuous READs and WRITEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify Continuous READs and WRITEs during data pod down by "
                    "delete deployment.")
        event = threading.Event()
        LOGGER.info("Step 1: Perform Continuous READs and WRITEs with variable object sizes. 0B + ("
                    "1KB - 512MB) during data pod down by delete deployment.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-26442'
        self.s3_clean = users
        output = Queue()

        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 30, 'skipcleanup': True, 'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started READs and WRITES in background")

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
        LOGGER.info("Step 6: Verify status for In-flight READs and WRITEs while pod is going down "
                    "should be failed/error.")
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Expected all pass, But Logs which contain "
                                                f"failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) < len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")
        LOGGER.info("Step 6: Verified status for In-flight READs and WRITEs while pod is going "
                    "down is failed/error.")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26442-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")
        LOGGER.info("ENDED: Test to verify Continuous READs and WRITEs during data pod down by "
                    "delete deployment.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26446")
    @CTFailOn(error_handler)
    def test_continuous_writes_deletes_during_pod_down(self):
        """
        This test tests Continuous WRITEs and DELETEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify Continuous WRITEs and DELETEs during data pod down by "
                    "delete deployment.")
        event = threading.Event()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = HA_CFG["bg_bucket_ops"]["no_del_buckets"]
        wr_output = Queue()
        del_output = Queue()

        LOGGER.info("Creating s3 account")
        users = self.mgnt_ops.create_account_users(nusers=1)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        self.test_prefix = 'test-26446'
        self.s3_clean = users
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])

        LOGGER.info("Step 1: Performing Continuous WRITEs and DELETEs with variable object sizes. "
                    "0B + (1KB - 512MB) during data pod down by delete deployment.")

        LOGGER.info("Starting WRITEs on %s buckets", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        thread1 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj, ), kwargs=args)
        thread1.daemon = True  # Daemonize thread
        thread1.start()
        LOGGER.info("Successfully started WRITEs in background")

        time.sleep(20)
        LOGGER.info("Starting DELETEs of %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        thread2 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj, ), kwargs=args)
        thread2.daemon = True  # Daemonize thread
        thread2.start()
        LOGGER.info("Successfully started DELETEs in background")

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
        thread1.join()
        thread2.join()

        LOGGER.info("Step 1: Verifying responses from WRITEs background process")
        wr_resp = ()
        while len(wr_resp) != 3: wr_resp = wr_output.get()       # pylint: disable=C0321
        s3_data = wr_resp[0]                  # Contains s3 data for passed buckets
        event_put_bkt = wr_resp[1]            # Contains buckets when event was set
        fail_put_bkt = wr_resp[2]             # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_put_bkt), "Expected pass, buckets which failed in "
                                                     f"create/put operations {fail_put_bkt}.")

        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_true(len(buckets), "No buckets found.")

        LOGGER.info("Failed buckets while in-flight create/put operation : %s", event_put_bkt)

        LOGGER.info("Step 1: Verifying responses from DELETEs background process")
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get()      # pylint: disable=C0321
        event_del_bkt = del_resp[0]          # Contains buckets when event was set
        fail_del_bkt = del_resp[1]           # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_del_bkt), "Expected pass, buckets which failed in "
                                                     f"delete operations {fail_del_bkt}.")
        LOGGER.info("Failed buckets while in-flight delete operation : %s", event_del_bkt)
        LOGGER.info("Step 1: Verified responses from WRITEs and DELETEs background processes")

        rd_output = Queue()
        LOGGER.info("Step 6: Verify READs and DI check for remaining buckets: %s", buckets)

        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': s3_data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = ()
        while len(rd_resp) != 4: rd_resp = rd_output.get()        # pylint: disable=C0321
        event_bkt_get = rd_resp[0]
        fail_bkt_get = rd_resp[1]
        event_di_bkt = rd_resp[2]
        fail_di_bkt = rd_resp[3]

        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt), "Expected pass in read and di check "
                                                     "operations. Found failures in READ: "
                                                     f"{fail_bkt_get} {event_bkt_get}"
                                                     f"or DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 6: Successfully verified READs and DI check for remaining buckets: %s",
                    buckets)

        LOGGER.info("Step 7: Deleting remaining buckets.")
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get()        # pylint: disable=C0321
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(event_del_bkt) or len(fail_del_bkt),
                                  f"Failed to delete buckets: {event_del_bkt} and {fail_del_bkt}")

        LOGGER.info("Step 7: Successfully deleted remaining buckets.")

        LOGGER.info("Step 8: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26446-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 8: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify Continuous WRITEs and DELETEs during data pod down by "
                    "delete deployment.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26447")
    @CTFailOn(error_handler)
    def test_continuous_reads_deletes_during_pod_down(self):
        """
        This test tests Continuous READs and DELETEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify Continuous READs and DELETEs during data pod down by "
                    "delete deployment.")
        event = threading.Event()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = HA_CFG["bg_bucket_ops"]["no_del_buckets"]
        wr_output = Queue()
        rd_output = Queue()
        del_output = Queue()

        LOGGER.info("Creating s3 account")
        users = self.mgnt_ops.create_account_users(nusers=1)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        self.test_prefix = 'test-26447'
        self.s3_clean = users
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])

        LOGGER.info("Step 1: Performing Continuous READs and DELETEs with variable object sizes. "
                    "0B + (1KB - 512MB) during data pod down by delete deployment.")

        LOGGER.info("Perform WRITEs on %s buckets", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3: wr_resp = wr_output.get()      # pylint: disable=C0321
        s3_data = wr_resp[0]           # Contains s3 data for passed buckets
        event_put_bkt = wr_resp[1]     # Contains buckets when event was set
        fail_put_bkt = wr_resp[2]      # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_put_bkt) or len(event_put_bkt),
                                  "Expected pass, buckets which failed in create/put operations "
                                  f"{fail_put_bkt} and {event_put_bkt}.")
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_true(len(buckets), "No buckets found.")

        LOGGER.info("Starting READs on %s buckets", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 's3_data': s3_data,
                'di_check': True, 'output': rd_output}

        thread1 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj, ), kwargs=args)
        thread1.daemon = True  # Daemonize thread
        thread1.start()
        LOGGER.info("Successfully started READs in background")

        time.sleep(20)
        LOGGER.info("Starting DELETEs of %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        thread2 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj, ), kwargs=args)
        thread2.daemon = True  # Daemonize thread
        thread2.start()
        LOGGER.info("Successfully started DELETEs in background")

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
        thread1.join()
        thread2.join()

        LOGGER.info("Step 1: Verifying responses from READs background process")
        rd_resp = ()
        while len(rd_resp) != 4: rd_resp = rd_output.get()         # pylint: disable=C0321
        event_bkt_get = rd_resp[0]            # Contains buckets when event was set
        fail_bkt_get = rd_resp[1]             # Contains buckets which failed when event was clear
        event_di_bkt = rd_resp[2]             # Contains buckets when event was set
        fail_di_bkt = rd_resp[3]              # Contains buckets which failed when event was clear

        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt),
                                  "Expected pass, buckets which failed in read are:"
                                  f" {fail_bkt_get} and failed in di check are: {fail_di_bkt}")

        LOGGER.info("Failed buckets while in-flight read operation : %s", event_bkt_get)
        LOGGER.info("Failed buckets while in-flight di check operation : %s", event_di_bkt)

        LOGGER.info("Step 1: Verifying responses from DELETEs background process")
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get()     # pylint: disable=C0321
        event_del_bkt = del_resp[0]          # Contains buckets when event was set
        fail_del_bkt = del_resp[1]           # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_del_bkt), "Expected pass, buckets which failed in "
                                                     f"delete operations {fail_del_bkt}.")
        LOGGER.info("Failed buckets while in-flight delete operation : %s", event_del_bkt)
        LOGGER.info("Step 1: Verified responses from READs and DELETEs background processes")

        LOGGER.info("Step 6: Verify READs and DI check for remaining buckets: %s", buckets)
        remain_bkts = s3_test_obj.bucket_list()[1]
        new_s3data = {}
        for bkt in remain_bkts:
            new_s3data[bkt] = s3_data[bkt]

        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = ()
        while len(rd_resp) != 4: rd_resp = rd_output.get()      # pylint: disable=C0321
        event_bkt_get = rd_resp[0]
        fail_bkt_get = rd_resp[1]
        event_di_bkt = rd_resp[2]
        fail_di_bkt = rd_resp[3]

        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt), "Expected pass in read and di check "
                                                     "operations. Found failures in READ: "
                                                     f"{fail_bkt_get} {event_bkt_get}"
                                                     f"or DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 6: Successfully verified READs and DI check for remaining buckets: %s",
                    buckets)

        LOGGER.info("Step 7: Deleting remaining buckets.")
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get()       # pylint: disable=C0321
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(event_del_bkt) or len(fail_del_bkt),
                                  f"Failed to delete buckets: {event_del_bkt} and {fail_del_bkt}")

        LOGGER.info("Step 7: Successfully deleted remaining buckets.")

        LOGGER.info("Step 8: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26447-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 8: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify Continuous WRITEs and DELETEs during data pod down by "
                    "delete deployment.")
