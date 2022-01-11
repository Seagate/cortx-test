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
from commons import commands as cmd
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import create_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from commons.utils.system_utils import remove_file
from commons.utils import system_utils as sysutils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=R0904
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
        cls.ha_obj = HAK8s()
        cls.restored = True
        cls.s3_clean = cls.test_prefix = cls.random_time = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.restore_node = cls.node_name = None
        cls.restore_ip = cls.node_iface = cls.new_worker_obj = cls.node_ip = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()
        cls.motr_obj = MotrCoreK8s()

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
        self.restore_node = False
        self.restore_ip = False
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
            if self.restore_node:
                LOGGER.info("Cleanup: Power on the %s down node.", self.node_name)
                resp = self.ha_obj.host_power_on(host=self.node_name)
                assert_utils.assert_true(resp, "Host is not powered on")
            if self.restore_ip:
                LOGGER.info("Cleanup: Get the network interface up for %s ip", self.node_ip)
                self.new_worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(self.node_iface, "up"),
                                                read_lines=True)
                resp = sysutils.check_ping(host=self.node_ip)
                assert_utils.assert_true(resp, "Interface is still not up.")
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
        LOGGER.info("STARTED: Test to verify degraded reads before and after safe pod shutdown.")

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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)[0]

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded reads before and after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23553")
    @CTFailOn(error_handler)
    def test_degraded_reads_unsafe_pod_shutdown(self):
        """
        This test tests degraded reads before and after unsafe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded reads before and after unsafe pod shutdown.")

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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)[0]

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded reads before and after unsafe pod shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23552")
    @CTFailOn(error_handler)
    def test_degraded_writes_safe_pod_shutdown(self):
        """
        This test tests degraded writes before and after safe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded writes before and after safe pod shutdown.")

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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
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

        LOGGER.info("ENDED: Test to verify degraded writes before and after safe pod shutdown.")

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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on pod %s are in offline "
                    "state", pod_name)
        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")
        LOGGER.info("Step 6: Perform DELETEs on random %s buckets", bucket_num - 10)
        for _ in range(bucket_num - 10 + 1):
            del_bucket = buckets.pop(self.system_random.randrange(len(buckets)))
            resp = s3_test_obj.delete_bucket(bucket_name=del_bucket, force=True)
            assert_utils.assert_true(resp[0], resp)
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(10, len(resp[1]), resp)
        LOGGER.info("Step 6: Successfully performed DELETEs on random %s buckets", bucket_num - 10)
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on %s are in offline "
                    "state", pod_name)
        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")
        LOGGER.info("Step 6: Perform DELETEs on random %s buckets", bucket_num - 10)
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

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32444")
    @CTFailOn(error_handler)
    def test_continuous_reads_during_pod_down(self):
        """
        This test tests degraded reads while pod is going down
        """
        LOGGER.info("STARTED: Test to verify degraded reads during pod is going down.")
        event = threading.Event()  # Event to be used to send intimation of pod deletion

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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")
        event.clear()

        thread.join()
        responses = {}
        while len(responses) != 2: responses = output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32455')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32455-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
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

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32456')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Shutdown the data pod by kubectl delete.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32456-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 6: IOs completed successfully.")

        LOGGER.info(
            "Completed: Verify IOs before and after data pod failure, "
            "pod shutdown by deleting pod using kubectl delete.")

    # pylint: disable=C0321
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
        event = threading.Event()  # Event to be used to send intimation of pod deletion
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 7: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Services status on remaining pod are in online state")
        event.clear()
        thread.join()
        del_resp = ()
        while len(del_resp) != 2: del_resp = output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt),
                                  f"Bucket deletion failed when cluster was online"
                                  f"{fail_del_bkt}")
        LOGGER.info("Step 8: Verify status for In-flight DELETEs while pod is going down "
                    "and Download and verify checksum on remaining/FailedToDelete buckets.")
        failed_buck = event_del_bkt
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
        self.s3_clean.pop(list(resp[2].keys())[0])

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-26445', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")
        LOGGER.info("ENDED: Test to verify Continuous DELETEs during data pod down by delete "
                    "deployment.")

    # pylint: disable=C0321
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
        event = threading.Event()  # Event to be used to send intimation of pod deletion
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")
        event.clear()
        thread.join()
        responses = {}
        while len(responses) != 2: responses = output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32454')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs are completed successfully.")

        LOGGER.info("Step 2: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be shutdown")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32454-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 6: IOs are completed successfully.")

        LOGGER.info(
            "Completed: Verify IOs before and after data pod failure; pod shutdown "
            "by making replicas 0")

    # pylint: disable=C0321
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
        event = threading.Event()  # Event to be used to send intimation of pod deletion
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")

        event.clear()
        thread.join()
        responses = {}
        while len(responses) != 2: responses = output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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

    # pylint: disable=C0321
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
        event = threading.Event()  # Event to be used to send intimation of pod deletion
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
                                   args=(event, s3_test_obj,), kwargs=args)
        thread1.daemon = True  # Daemonize thread
        thread1.start()
        LOGGER.info("Successfully started WRITEs in background")

        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        LOGGER.info("Starting DELETEs of %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        thread2 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj,), kwargs=args)
        thread2.daemon = True  # Daemonize thread
        thread2.start()
        LOGGER.info("Successfully started DELETEs in background")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")
        event.clear()
        thread1.join()
        thread2.join()

        LOGGER.info("Step 1: Verifying responses from WRITEs background process")
        wr_resp = ()
        while len(wr_resp) != 3: wr_resp = wr_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        event_put_bkt = wr_resp[1]  # Contains buckets when event was set
        fail_put_bkt = wr_resp[2]  # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_put_bkt), "Expected pass, buckets which failed in "
                                                     f"create/put operations {fail_put_bkt}.")

        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_true(len(buckets), "No buckets found.")

        LOGGER.info("Failed buckets while in-flight create/put operation : %s", event_put_bkt)

        LOGGER.info("Step 1: Verifying responses from DELETEs background process")
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]  # Contains buckets when event was set
        fail_del_bkt = del_resp[1]  # Contains buckets which failed when event was clear
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
        while len(rd_resp) != 4: rd_resp = rd_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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
        while len(del_resp) != 2: del_resp = del_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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
        event = threading.Event()  # Event to be used to send intimation of pod deletion
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
        while len(wr_resp) != 3: wr_resp = wr_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        event_put_bkt = wr_resp[1]  # Contains buckets when event was set
        fail_put_bkt = wr_resp[2]  # Contains buckets which failed when event was clear
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

        time.sleep(HA_CFG["common_params"]["20sec_delay"])
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")
        event.clear()
        thread1.join()
        thread2.join()

        LOGGER.info("Step 1: Verifying responses from READs background process")
        rd_resp = ()
        while len(rd_resp) != 4: rd_resp = rd_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        event_bkt_get = rd_resp[0]  # Contains buckets when event was set
        fail_bkt_get = rd_resp[1]  # Contains buckets which failed when event was clear
        event_di_bkt = rd_resp[2]  # Contains buckets when event was set
        fail_di_bkt = rd_resp[3]  # Contains buckets which failed when event was clear

        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt),
                                  "Expected pass, buckets which failed in read are:"
                                  f" {fail_bkt_get} and failed in di check are: {fail_di_bkt}")

        LOGGER.info("Failed buckets while in-flight read operation : %s", event_bkt_get)
        LOGGER.info("Failed buckets while in-flight di check operation : %s", event_di_bkt)

        LOGGER.info("Step 1: Verifying responses from DELETEs background process")
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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
        while len(rd_resp) != 4: rd_resp = rd_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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
        while len(del_resp) != 2: del_resp = del_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
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

        LOGGER.info("ENDED: Test to verify Continuous READs and DELETEs during data pod down by "
                    "delete deployment.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32445")
    @CTFailOn(error_handler)
    def test_degraded_mpu_after_safe_pod_shutdown(self):
        """
        This test tests degraded multipart upload after data pod safe shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded multipart upload after data pod safe shutdown.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 1: Create and list buckets and perform multipart upload for size 5GB.")
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=self.bucket_name,
                                                         object_name=self.object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size*const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 1: Sucessfully performed multipart upload for size 5GB.")

        LOGGER.info("Step 2: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 3: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Verified cluster status is in degraded state")

        LOGGER.info("Step 4: Verify services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services of %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Verify services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Verified services on remaining pods are in online state")

        LOGGER.info("Step 6: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 6: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        remove_file(self.multipart_obj_path)
        remove_file(download_path)

        LOGGER.info("Step 7: Create new bucket and multipart upload and then download 5GB object")
        bucket_name = "mp-bkt-{}".format(self.random_time)
        object_name = "mp-obj-{}".format(self.random_time)
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        upload_checksum1 = resp[2]
        result = s3_test_obj.object_info(bucket_name, object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size*const.Sizes.MB)

        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum1 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum1, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum1},"
                                  f" {download_checksum1}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum1, download_checksum1)
        LOGGER.info("Step 7: Successfully created bucket and did multipart upload and download "
                    "with 5GB object")
        LOGGER.info(
            "COMPLETED: Test to verify degraded multipart upload after data pod safe shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32446")
    @CTFailOn(error_handler)
    def test_degraded_mpu_after_unsafe_pod_shutdown(self):
        """
        This test tests degraded multipart upload after data pod unsafe shutdown
        """
        LOGGER.info(
            "STARTED: Test to verify degraded multipart upload after data pod unsafe shutdown.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 1: Create and list buckets and perform multipart upload for size 5GB.")
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=self.bucket_name,
                                                         object_name=self.object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size*const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 1: Sucessfully performed multipart upload for size 5GB.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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

        LOGGER.info("Step 4: Verify services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services of %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Verify services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Verified services on remaining pods are in online state")

        LOGGER.info("Step 6: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 6: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        remove_file(self.multipart_obj_path)
        remove_file(download_path)

        LOGGER.info("Step 7: Create new bucket and multipart upload and then download 5GB object")
        bucket_name = "mp-bkt-{}".format(self.random_time)
        object_name = "mp-obj-{}".format(self.random_time)
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        upload_checksum1 = resp[2]
        result = s3_test_obj.object_info(bucket_name, object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size*const.Sizes.MB)
        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum1 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum1, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum1},"
                                  f" {download_checksum1}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum1, download_checksum1)
        LOGGER.info("Step 7: Successfully created bucket and did multipart upload and download "
                    "with 5GB object")
        LOGGER.info(
            "COMPLETED: Test to verify degraded multipart upload after data pod unsafe shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32459")
    @CTFailOn(error_handler)
    def test_control_pod_failover(self):
        """
        Verify IOs before and after control pod failure, pod shutdown by making worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after control pod failure, "
                    "pod shutdown by making worker node down.")

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32459')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Check the node which has the control pod running and shutdown"
                    "the node.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        control_pods = self.node_master_list[0].get_pods_node_fqdn(const.CONTROL_POD_NAME_PREFIX)
        control_pod_name = list(control_pods.keys())[0]
        node_fqdn = control_pods.get(control_pod_name)
        self.node_name = node_fqdn
        LOGGER.info("Control pod %s is hosted on %s node", control_pod_name, node_fqdn)
        LOGGER.info("Get the data pod running on %s node", node_fqdn)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        data_pod_name = None
        for pod_name, node in data_pods.items():
            if node == node_fqdn:
                data_pod_name = pod_name
        LOGGER.info("%s node has data pod: %s", node_fqdn, data_pod_name)
        LOGGER.info("Shutdown the node: %s", node_fqdn)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where control pod was running.", node_fqdn)
        self.restore_node = True

        LOGGER.info("Step 3: Check cluster status is in degraded state.")
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on pod %s are in offline "
                    "state", data_pod_name)
        pod_list.remove(data_pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 6: Check for control pod failed over node.")
        control_pods_new = \
            self.node_master_list[0].get_pods_node_fqdn(const.CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(control_pods_new,
                                 "Control pod has not failed over to any other node.")
        control_pod_name_new = list(control_pods_new.keys())[0]
        node_fqdn_new = control_pods_new.get(control_pod_name_new)
        LOGGER.info("Step 6: %s pod has been failed over to %s node",
                    control_pod_name_new, node_fqdn_new)

        LOGGER.info("Step 7: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32459-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(
            di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: IOs completed successfully.")

        LOGGER.info("COMPLETED: Verify IOs before and after control pod failure, "
                    "pod shutdown by making worker node down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32460")
    @CTFailOn(error_handler)
    def test_ha_pod_failover(self):
        """
        Verify IOs before and after ha pod failure, pod shutdown by making worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after HA pod failure, "
                    "pod shutdown by making worker node down.")

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32460')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Check the node which has the ha pod running and shutdown"
                    "the node.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        ha_pods = self.node_master_list[0].get_pods_node_fqdn(const.HA_POD_NAME_PREFIX)
        ha_pod_name = list(ha_pods.keys())[0]
        node_fqdn = ha_pods.get(ha_pod_name)
        self.node_name = node_fqdn
        LOGGER.info("HA pod %s is hosted on %s node", ha_pod_name, node_fqdn)
        LOGGER.info("Get the data pod running on node %s", node_fqdn)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        data_pod_name = None
        for pod_name, node in data_pods.items():
            if node == node_fqdn:
                data_pod_name = pod_name
        LOGGER.info("%s node has data pod: %s", node_fqdn, data_pod_name)
        LOGGER.info("Shutdown the node: %s", node_fqdn)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where HA pod was running.", node_fqdn)
        self.restore_node = True

        LOGGER.info("Step 3: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on pod %s are in offline "
                    "state", data_pod_name)

        pod_list.remove(data_pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 6: Check for HA pod failed over node.")
        ha_pods_new = self.node_master_list[0].get_pods_node_fqdn(const.HA_POD_NAME_PREFIX)
        assert_utils.assert_true(ha_pods_new, "HA pod has not failed over to any other node.")
        ha_pod_name_new = list(ha_pods_new.keys())[0]
        node_fqdn_new = ha_pods_new.get(ha_pod_name_new)
        LOGGER.info("Step 6: %s pod has been failed over to %s node",
                    ha_pod_name_new, node_fqdn_new)

        LOGGER.info("Step 7: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32460-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: IOs completed successfully.")

        LOGGER.info("COMPLETED: Verify IOs before and after HA pod failure, "
                    "pod shutdown by making worker node down.")

    # pylint: disable=C0321
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
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services on %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pods %s are in online state", pod_list)
        prc.join()
        res = ()
        while output.empty(): res = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
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

        LOGGER.info("Step 10: Create multiple buckets and run IOs and verify DI on the same")
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
                    "partially for %s parts out of total %s", part_numbers, total_parts)
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
        LOGGER.info("Step 1: Successfully completed partial multipart upload for %s parts out of "
                    "total %s", part_numbers, total_parts)

        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 3: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services on %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services status on remaining pods %s are in online state", pod_list)

        LOGGER.info("Step 7: Upload remaining parts")
        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts+1))))
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

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32450")
    @CTFailOn(error_handler)
    def test_degraded_copy_object_safe_pod_shutdown(self):
        """
        Verify degraded copy object after data pod down - pod shutdown (make replicas=0)
        """
        LOGGER.info(
            "STARTED: Verify degraded copy object after data pod down - pod shutdown "
            "(make replicas=0) ")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = {}
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{self.random_time}"] =\
            f"ha-obj{cnt}-{self.random_time}"

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

        LOGGER.info("Step 1: Create and list buckets and perform upload and copy "
                    "object from %s bucket to other buckets, download objects "
                    "and verify etags", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully create and list buckets and perform upload and copy"
                    "object from %s bucket to other buckets, download objects "
                    "and verify etags", self.bucket_name)

        LOGGER.info("Step 2: Shutdown the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be shutdown")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {key} of bucket {val}. "
                                                          "Put and Get Etag mismatch")
        LOGGER.info("Step 6: Successfully download the uploaded objects & verify etags")

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 7: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 8: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 8: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)

        LOGGER.info(
            "COMPLETED: Verify degraded copy object after data pod down - pod shutdown "
            "(make replicas=0) ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32451")
    @CTFailOn(error_handler)
    def test_degraded_copy_object_unsafe_pod_shutdown(self):
        """
        Verify degraded copy object after data pod down - pod unsafe
        shutdown (by deleting deployment)
        """
        LOGGER.info(
            "STARTED: Verify degraded copy object after data pod down - "
            "pod unsafe shutdown (by deleting deployment) ")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = {}
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{self.random_time}"] = \
                f"ha-obj{cnt}-{self.random_time}"

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

        LOGGER.info("Step 1: Create and list buckets and perform upload and copy "
                    "object from %s bucket to other buckets, download objects "
                    "and verify etags", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully create and list buckets and perform upload and copy"
                    "object from %s bucket to other buckets, download objects "
                    "and verify etags", self.bucket_name)

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

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

        LOGGER.info("Step 4: Verify services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services of %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Verify services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Verified services on remaining pods are in online state")

        LOGGER.info("Step 6: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {key} of bucket {val}. "
                                                          "Put and Get Etag mismatch")
        LOGGER.info("Step 6: Successfully download the uploaded objects & verify etags")

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 7: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 8: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 8: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)

        LOGGER.info(
            "COMPLETED: Verify degraded copy object after data pod down - "
            "pod unsafe shutdown (by deleting deployment) ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32458")
    @CTFailOn(error_handler)
    def test_pod_fail_node_down(self):
        """
        Verify IOs before and after data pod failure, pod shutdown by making worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node down.")

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32458')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Shutdown data pod by shutting node on which its hosted.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        resp = self.ha_obj.get_data_pod_no_ha_control(data_pod_list, self.node_master_list[0])
        data_pod_name = resp[0]
        server_pod_name = resp[1]
        data_node_fqdn = resp[2]
        srv_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        self.node_name = data_node_fqdn
        LOGGER.info("Shutdown the node: %s", data_node_fqdn)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=data_node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where data pod was running.", data_node_fqdn)
        self.restore_node = True

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        LOGGER.info("Check services on %s data pod", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Check services on %s server pod", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name], fail=True,
                                                           hostname=srv_pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of data and server pods are in offline state")

        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")

        LOGGER.info("Step 6: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32458-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 6: IOs completed successfully.")

        LOGGER.info("COMPLETED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32457")
    @CTFailOn(error_handler)
    def test_pod_fail_node_nw_down(self):
        """
        Verify IOs before and after data pod failure, pod shutdown
        by making worker node network down.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node network down.")

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32457')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs completed successfully.")

        LOGGER.info("Step 2: Shutdown data pod by making network down of node "
                    "on which its hosted.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        resp = self.ha_obj.get_data_pod_no_ha_control(data_pod_list, self.node_master_list[0])
        data_pod_name = resp[0]
        server_pod_name = resp[1]
        data_node_fqdn = resp[2]
        srv_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        LOGGER.info("Get the ip of the host from the node %s", data_node_fqdn)
        resp = self.ha_obj.get_nw_iface_node_down(host_list=self.host_worker_list,
                                                  node_list=self.node_worker_list,
                                                  node_fqdn=data_node_fqdn)
        self.node_ip = resp[1]
        self.node_iface = resp[2]
        self.new_worker_obj = resp[3]
        assert_utils.assert_true(resp[0], "Node network is still up")
        LOGGER.info("Step 2: %s Node's network is down.", data_node_fqdn)
        self.restore_ip = True

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        LOGGER.info("Check services on %s data pod", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Check services on %s server pod", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name], fail=True,
                                                           hostname=srv_pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of data and server pods are in offline state")

        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")

        LOGGER.info("Step 6: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32457-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 6: IOs completed successfully.")

        LOGGER.info("COMPLETED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node network down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32452")
    @CTFailOn(error_handler)
    def test_degraded_copy_object_during_pod_shutdown(self):
        """
        Verify copy object during data pod shutdown (delete deployment)
        """
        LOGGER.info("STARTED: Verify copy object during data pod shutdown (delete deployment) ")

        bkt_obj_dict = {}
        output = Queue()

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

        LOGGER.info("Step 1: Create bucket, upload an object to one of the bucket ")
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully create bucket, upload an object to one of the bucket")

        bkt_obj_dict = {f"ha-bkt-{int((perf_counter_ns()))}": f"ha-obj-{int((perf_counter_ns()))}"}
        LOGGER.info("Step 2: Create multiple buckets and copy object from %s to other buckets in "
                    "background", self.bucket_name)
        args = {'s3_test_obj': s3_test_obj, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': False,
                'put_etag': put_etag}
        prc = Process(target=self.ha_obj.create_bucket_copy_obj, kwargs=args)
        prc.start()
        LOGGER.info("Step 2: Successfully started background process")

        LOGGER.info("Step 3: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting "
                                           "deployment (unsafe)")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by deleting "
                    "deployment (unsafe)", pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Verify services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Verified services of %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Verify services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Verified services on remaining pods are in online state")

        prc.join()
        if output.empty():
            LOGGER.error("Failed in Copy Object process")
            LOGGER.info("Retrying copy object to bucket %s", list(bkt_obj_dict.keys())[0])
            resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=bkt_obj_dict,
                                                      file_path=self.multipart_obj_path,
                                                      bkt_op=False, put_etag=put_etag)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            res = output.get()
            put_etag = res[1]

        LOGGER.info("Step 7: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {key} of bucket {val}. "
                                                          "Put and Get Etag mismatch")
        LOGGER.info("Step 7: Successfully download the uploaded objects & verify etags")

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 8: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 9: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 9: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)

        LOGGER.info("COMPLETED: Verify copy object during data pod shutdown (delete deployment)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32461")
    @CTFailOn(error_handler)
    def test_server_pod_failure(self):
        """
        Verify IOs before and after server pod failure (pod shutdown by making replicas=0)
        """
        LOGGER.info("STARTED: Verify IOs before and after server pod failure; pod shutdown by "
                    "making replicas=0")

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32461')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: IOs are completed successfully.")

        LOGGER.info("Step 2: Shutdown the server pod safely by making replicas=0")
        LOGGER.info("Get server pod name to be shutdown")
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        server_pod_name = random.sample(server_pod_list, 1)
        LOGGER.info("Shutdown pod %s", server_pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=server_pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to shutdown Server pod {server_pod_name} "
                                           "by making replicas=0")
        LOGGER.info("Step 2: Successfully shutdown pod %s by making replicas=0", server_pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name],
                                                           fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of %s are in offline state", server_pod_name)

        server_pod_list.remove(server_pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", server_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Start IOs on degraded cluster.")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-32461-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 6: IOs are completed successfully.")

        LOGGER.info("Completed: Verify IOs before and after server pod failure; pod shutdown "
                    "by making replicas 0")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-33209")
    @CTFailOn(error_handler)
    def test_rc_pod_failover(self):
        """
        Verify IOs before and after pod failure by making RC node down
        """
        LOGGER.info("STARTED: Verify IOs before & after pod failure by making RC node down")

        LOGGER.info("Step 1: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-33209')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 1: Successfully completed IOs.")

        LOGGER.info("Step 2: Get the RC node and shutdown the same.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        rc_node = self.motr_obj.get_primary_cortx_node()
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        self.node_name = list(rc_info.values())[0]
        LOGGER.info("RC Node is running on %s node", self.node_name)
        LOGGER.info("Get the data pod running on %s node", self.node_name)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        server_pods = self.node_master_list[0].get_pods_node_fqdn(const.SERVER_POD_NAME_PREFIX)
        rc_datapod = rc_serverpod = None
        for pod_name, node in data_pods.items():
            if node == self.node_name:
                rc_datapod = pod_name
                break
        for server_pod, node in server_pods.items():
            if node == self.node_name:
                rc_serverpod = server_pod
                break
        LOGGER.info("RC node %s has data pod: %s and server pod : %s", self.node_name,
                    rc_datapod, rc_serverpod)
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=rc_datapod)
        LOGGER.info("Shutdown the RC node: %s", self.node_name)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_name)
        assert_utils.assert_true(resp, f"{self.node_name} is not powered off")
        LOGGER.info("Step 2: Sucessfully shutdown RC node %s.", self.node_name)
        self.restore_node = True

        LOGGER.info("Step 3: Check services status that were running on RC node %s's data pod %s "
            "and server pod %s are in offline state", self.node_name, rc_datapod, rc_serverpod)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[rc_datapod, rc_serverpod],
                                                           fail=True, hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Checked services status that were running on RC node %s's data pod %s "
                    "and server pod %s are in offline state", self.node_name, rc_datapod,
                    rc_serverpod)

        pod_list.remove(rc_datapod)
        server_list.remove(rc_serverpod)
        online_pods = pod_list + server_list
        LOGGER.info("Step 4: Check services status on remaining pods %s are in online state",
                    online_pods)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=online_pods, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 5: Check services status on remaining pods %s are in online state",
                    online_pods)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=online_pods, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 6: Check for RC node failed over node.")
        rc_node = self.motr_obj.get_primary_cortx_node()
        assert_utils.assert_true(len(rc_node), "Couldn't fine new RC failover node")
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        LOGGER.info("Step 6: RC node has been failed over to %s node", list(rc_info.values())[0])

        LOGGER.info("Step 7: Start IOs (create s3 acc, buckets and upload objects).")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-33209-1')
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 7: Successfully completed IOs.")

        LOGGER.info("COMPLETED: Verify IOs before & after pod failure by making RC node down")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34827")
    @CTFailOn(error_handler)
    def test_background_io_during_control_pod_restart(self):
        """
        Test control pod deletion should not affect existing user I/O
        """
        LOGGER.info("STARTED: Test control pod deletion should not affect existing user I/O")

        LOGGER.info("Step 1: Perform Continuous READs and WRITEs during control pod down")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34827'
        self.s3_clean = users
        event = threading.Event()
        output = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 10, 'skipcleanup': False, 'output': output}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started READs and WRITES in background")

        LOGGER.info("Step 2: Find & Delete the control pod")
        control_pods = self.node_master_list[0].get_pods_node_fqdn(const.CONTROL_POD_NAME_PREFIX)
        control_pod_name = list(control_pods.keys())[0]
        LOGGER.debug("Control pod %s", control_pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=control_pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(
            resp[0], f"Failed to delete pod {control_pod_name} by deleting deployment (unsafe)")
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    control_pod_name)

        LOGGER.info("Step 3: Verify status for In-flight READs and WRITEs while pod is down")
        event.clear()
        thread.join()
        responses = {}
        while len(responses) != 2: responses = output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Expected all pass, But Logs which contain "
                                                f"failures: {resp[1]}")
        assert_utils.assert_false(len(fail_logs),
                                 f"Logs which contain failures IOs: {fail_logs}")
        LOGGER.info("Step 3: Verified status for In-flight READs and WRITEs while pod is down")

        LOGGER.info("Step 4: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("COMPLETED: Test control pod deletion should not affect existing user I/O")
