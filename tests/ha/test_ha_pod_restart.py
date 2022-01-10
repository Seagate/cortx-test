#!/usr/bin/python  # pylint: disable=R0902
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
import threading
import time
from multiprocessing import Process, Queue
from time import perf_counter_ns

import pytest

from commons import constants as const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
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
# pylint: disable=C0302
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
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = cls.random_time = cls.s3_clean = cls.test_prefix = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
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
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
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
                system_utils.remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34072")
    @CTFailOn(error_handler)
    def test_reads_after_pod_restart(self):
        """
        This test tests READs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify READs after data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 5GB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34072'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True, large_workload=True,
                                                    nsamples=1, nclients=1)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, large_workload=True,
                                                    nsamples=1, nclients=1)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify READs after data pod restart.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34074")
    @CTFailOn(error_handler)
    def test_write_after_pod_restart(self):
        """
        This test tests WRITEs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify WRITEs after data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs-READs-Verify with variable object sizes. 0B - 5GB")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34074'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    large_workload=True, nsamples=1, nclients=1)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    large_workload=True, nsamples=1, nclients=1)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed READs and verified DI on the written data")

        LOGGER.info("Step 9: Perform WRITEs-READs-Verify with variable object sizes. (0B - 5GB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34074-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    large_workload=True, nsamples=1, nclients=1)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify WRITEs after data pod restart.")

    # pylint: disable=C0321
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34077")
    @CTFailOn(error_handler)
    def test_deletes_after_pod_restart(self):
        """
        This test tests DELETEs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify DELETEs after data pod restart.")
        wr_output = Queue()
        del_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        event = threading.Event()

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 128MB)")
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-34077'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)

        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3: wr_resp = wr_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]           # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")

        LOGGER.info("Step 5: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB)")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Perform DELETEs on %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        remain_bkt = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(remain_bkt), wr_bucket - del_bucket,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(remain_bkt)} number of buckets")

        LOGGER.info("Step 8: Successfully Performed DELETEs on %s buckets", del_bucket)

        LOGGER.info("Step 9: Perform READs and verify on remaining buckets")
        rd_output = Queue()
        new_s3data = {}
        for bkt in remain_bkt:
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
        LOGGER.info("Step 9: Successfully verified READs and DI check for remaining buckets: %s",
                    remain_bkt)

        LOGGER.info("Step 10: Again create %s buckets and put variable size objects and perform "
                    "delete on %s buckets", wr_bucket, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3: wr_resp = wr_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        new_bkts = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(new_bkts) - len(remain_bkt), wr_bucket,
                                  f"Failed to create {wr_bucket} number of buckets. Created "
                                  f"{len(new_bkts) - len(remain_bkt)} number of buckets")

        LOGGER.info("Perform DELETEs on %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2: del_resp = del_output.get(
            timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets1 = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets1), wr_bucket - del_bucket + len(remain_bkt),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket + len(remain_bkt)}. Remaining {len(buckets1)} number"
                                  " of buckets")

        LOGGER.info("Step 10: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB) and DELETEs on %s buckets", del_bucket)

        LOGGER.info("Step 11: Perform READs and verify on remaining buckets")
        for bkt in buckets1:
            if bkt in s3_data:
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
        LOGGER.info("Step 11: Successfully verified READs and DI check for remaining buckets: %s",
                    buckets1)

        LOGGER.info("ENDED: Test to verify DELETEs after data pod restart.")

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34080")
    @CTFailOn(error_handler)
    def test_mpu_after_pod_restart(self):
        """
        This test tests multipart upload after data pod restart.
        """
        LOGGER.info("STARTED: Test to verify multipart upload after data pod restart.")
        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 5: Create and list buckets. Perform multipart upload for size %s MB in "
                    "total %s parts.", file_size, total_parts)
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
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 5: Sucessfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)

        LOGGER.info("Step 6: Start pod again by creating deployment.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.restore_pod = False
        LOGGER.info("Step 6: Successfully started pod again by creating deployment.")

        LOGGER.info("Step 7: Verify cluster status is in online state")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 8: Download the uploaded object %s & verify checksum", self.object_name)
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 8: Successfully downloaded the object %s & verified the checksum",
                    self.object_name)
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        system_utils.remove_file(self.multipart_obj_path)
        system_utils.remove_file(download_path)

        LOGGER.info("Step 9: Create and list buckets. Perform multipart upload for size %s MB in "
                    "total %s parts.", file_size, total_parts)
        test_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
        test_object = f"ha-mp-obj-{int(perf_counter_ns())}"
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=test_bucket,
                                                         object_name=test_object,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(test_bucket, test_object)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", test_bucket, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 9: Sucessfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)

        LOGGER.info("Step 10: Download the uploaded object %s & verify checksum", test_object)
        resp = s3_test_obj.object_download(test_bucket, test_object, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 10: Successfully downloaded the object %s & verified the checksum",
                    test_object)
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        system_utils.remove_file(self.multipart_obj_path)
        system_utils.remove_file(download_path)
        LOGGER.info("COMPLETED: Test to verify multipart upload after data pod restart.")

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34082")
    @CTFailOn(error_handler)
    def test_partial_mpu_after_pod_restart(self):
        """
        This test tests partial multipart upload after data pod restart
        """
        LOGGER.info("STARTED: Test to verify partial multipart upload after data pod restart.")
        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = random.sample(list(range(1, total_parts + 1)), total_parts // 2)
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        system_utils.create_file(self.multipart_obj_path, file_size)
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

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
        LOGGER.info("Step 5: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially for %s part out of %s", part_numbers, total_parts)
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
        LOGGER.info("Step 5: Successfully completed partial multipart upload for %s part out of "
                    "%s", part_numbers, total_parts)

        LOGGER.info("Step 6: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 6: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 7: Start pod again by creating deployment.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.restore_pod = False
        LOGGER.info("Step 7: Successfully started pod again by creating deployment.")

        LOGGER.info("Step 8: Verify cluster status is in online state")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Verified cluster is in online state. All services are up & running")

        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts + 1))))
        LOGGER.info("Step 9: Upload remaining %s parts out of %s", remaining_parts, total_parts)
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
        LOGGER.info("Step 9: Successfully uploaded remaining %s parts out of %s",
                    remaining_parts, total_parts)

        etag_list = parts_etag1 + parts_etag2
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])

        LOGGER.info("Step 10: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 10: Listed parts of multipart upload: %s", res[1])

        LOGGER.info("Step 11: Completing multipart upload & check upload size is %s", file_size *
                    const.Sizes.MB)
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
        LOGGER.info("Step 11: Multipart upload completed and verified upload size is %s",
                    file_size * const.Sizes.MB)

        LOGGER.info("Step 12: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 12: Successfully downloaded the object and verified the checksum")
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        system_utils.remove_file(self.multipart_obj_path)
        system_utils.remove_file(download_path)
        LOGGER.info("COMPLETED: Test to verify partial multipart upload after data pod restart.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34083")
    @CTFailOn(error_handler)
    def test_copy_obj_after_pod_restart(self):
        """
        This test tests copy object after data pod restart
        """
        LOGGER.info("STARTED: Test to verify copy object after data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        bkt_obj_dict = dict()
        bucket2 = f"ha-bkt2-{int((perf_counter_ns()))}"
        object2 = f"ha-obj2-{int((perf_counter_ns()))}"
        bkt_obj_dict[bucket2] = object2
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
        LOGGER.info("Step 5: Create and list buckets. Upload object to %s & copy object from the"
                    " same bucket to %s and verify copy object etags",
                    self.bucket_name, bucket2)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]
        LOGGER.info("Step 5: Successfully created multiple buckets and uploaded object to %s "
                    "and copied to %s and verified copy object etags", self.bucket_name, bucket2)

        LOGGER.info("Step 6: Start pod again by creating deployment.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.restore_pod = False
        LOGGER.info("Step 6: Successfully started pod again by creating deployment.")

        LOGGER.info("Step 7: Verify cluster status is in online state")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 8: Download the uploaded %s on %s & verify etags.", object2, bucket2)
        resp = s3_test_obj.get_object(bucket=bucket2, key=object2)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object2} of bucket {bucket2}.")
        LOGGER.info("Step 8: Downloaded the uploaded %s on %s & verified etags.", object2, bucket2)

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.pop(bucket2)
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 9: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 10: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 10: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)
        LOGGER.info("COMPLETED: Test to verify copy object after data pod restart.")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34073")
    @CTFailOn(error_handler)
    def test_continuous_reads_during_pod_restart(self):
        """
        This test tests continuous reads during pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous READs during data pod restart.")

        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)

        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 5GB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34073'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True, nclients=1, nsamples=1)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 6: Perform READs and verify DI on the written data in background")
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 1, 'skipwrite': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()

        LOGGER.info("Step 6: Successfully started READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 7: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 7: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        event.clear()
        thread.join()

        LOGGER.info("Verifying responses from background process")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 6: Successfully completed READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34073-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous READs during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34091")
    @CTFailOn(error_handler)
    def test_different_data_pods_restart_loop(self):
        """
        This test tests IOs in degraded mode and after data pod restart in loop
        (different data pod down every time)
        """
        LOGGER.info("STARTED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (different data pod down every time)")

        LOGGER.info("Get data pod list to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)

        for pod in pod_list:
            LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
            pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod)
            LOGGER.info("Deleting pod %s", pod)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod} by deleting deployment"
                                               " (unsafe)")
            LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment "
                        "(unsafe)", pod)
            self.deployment_backup = resp[1]
            self.deployment_name = resp[2]
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S

            LOGGER.info("Step 2: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 2: Cluster is in degraded state")

            LOGGER.info("Step 3: Check services status that were running on pod %s", pod)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod], fail=True,
                                                               hostname=pod_host)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 3: Services of pod are in offline state")

            remain_pod_list = list(filter(lambda x: x != pod, pod_list))
            LOGGER.info("Step 4: Check services status on remaining pods %s",
                        remain_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 4: Services of pod are in online state")

            LOGGER.info("Step 5: Create s3 account, create multiple buckets and run IOs")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34091', nusers=1, nbuckets=10)
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_clean.update(resp[2])
            resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            self.s3_clean.pop(list(resp[2].keys())[0])
            LOGGER.info("Step 5: Successfully created s3 account and multiple buckets and ran IOs")

            LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Step 6: Successfully started the pod")
            self.restore_pod = False

            LOGGER.info("Step 7: Check cluster status")
            resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

            LOGGER.info("Step 8: Create s3 account, create multiple buckets and run IOs")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34091-1', nusers=1, nbuckets=10)
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_clean.update(resp[2])
            resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            self.s3_clean.pop(list(resp[2].keys())[0])
            LOGGER.info("Step 8: Successfully created s3 account and multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (different data pod down every time)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34090")
    @CTFailOn(error_handler)
    def test_same_data_pod_restart_loop(self):
        """
        This test tests IOs in degraded mode and after data pod restart in loop
        (same pod down every time)
        """
        LOGGER.info("STARTED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (same pod down every time)")

        LOGGER.info("Get data pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod)

        loop_count = HA_CFG["common_params"]["loop_count"]
        for loop in range(1, loop_count):
            LOGGER.info("Running loop %s", loop)

            LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
            LOGGER.info("Deleting pod %s", pod)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod} by deleting deployment"
                                               " (unsafe)")
            LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment "
                        "(unsafe)", pod)
            self.deployment_backup = resp[1]
            self.deployment_name = resp[2]
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S

            LOGGER.info("Step 2: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 2: Cluster is in degraded state")

            LOGGER.info("Step 3: Check services status that were running on pod %s", pod)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod], fail=True,
                                                               hostname=pod_host)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 3: Services of pod are in offline state")

            remain_pod_list = list(filter(lambda x: x != pod, pod_list))
            LOGGER.info("Step 4: Check services status on remaining pods %s",
                        remain_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 4: Services of pod are in online state")

            LOGGER.info("Step 5: Create s3 account, create multiple buckets and run IOs")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34090', nusers=1, nbuckets=10)
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_clean.update(resp[2])
            resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            self.s3_clean.pop(list(resp[2].keys())[0])
            LOGGER.info("Step 5: Successfully created s3 account and multiple buckets and ran IOs")

            LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Step 6: Successfully started the pod")
            self.restore_pod = False

            LOGGER.info("Step 7: Check cluster status")
            resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

            LOGGER.info("Step 8: Create s3 account, create multiple buckets and run IOs")
            resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34090-1', nusers=1, nbuckets=10)
            assert_utils.assert_true(resp[0], resp[1])
            di_check_data = (resp[1], resp[2])
            self.s3_clean.update(resp[2])
            resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
            assert_utils.assert_true(resp[0], resp[1])
            self.s3_clean.pop(list(resp[2].keys())[0])
            LOGGER.info("Step 8: Successfully created s3 account and multiple buckets and ran IOs")

            LOGGER.info("Get recently created data pod name using deployment %s",
                        self.deployment_name)
            pod = self.node_master_list[0].get_recent_pod_name(deployment_name=self.deployment_name)
            pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)

        LOGGER.info("ENDED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (same pod down every time)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34081")
    @CTFailOn(error_handler)
    def test_mpu_during_pod_restart(self):
        """
        This test tests multipart upload during data pod restart
        """
        LOGGER.info("STARTED: Test to verify multipart upload during data pod restart")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts))
        random.shuffle(part_numbers)
        output = Queue()
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
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pods %s are in online state", remain_pod_list)

        LOGGER.info("Step 5: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size, 'total_parts': total_parts,
                'multipart_obj_path': self.multipart_obj_path, 'part_numbers': part_numbers,
                'parts_etag': parts_etag, 'output': output}
        prc = Process(target=self.ha_obj.start_random_mpu, kwargs=args)
        prc.start()
        LOGGER.info("Step 5: Started multipart upload of 5GB object in background")

        time.sleep(HA_CFG["common_params"]["5sec_delay"])

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 5: Checking responses from background process")
        prc.join()
        if output.empty():
            assert_utils.assert_true(False, "Background process failed to do multipart upload")

        res = output.get()
        mpu_id = None
        if isinstance(res[0], dict):
            failed_parts = res[0]
            assert_utils.assert_true(False, f"Multipart upload is expected to be passed. Failed "
                                            f"parts : {failed_parts}")
        elif isinstance(res[0], list):
            LOGGER.info("All the parts are uploaded successfully")
            parts_etag = res[0]
            mpu_id = res[1]

        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]
        LOGGER.info("Step 5: Successfully uploaded all the parts of multipart upload.")

        LOGGER.info("Step 8: Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        if not res[0] or len(res[1]["Parts"]) != total_parts:
            assert_utils.assert_true(False, res)
        LOGGER.info("Step 8: Listed parts of multipart upload: %s", res[1])

        LOGGER.info("Step 9: Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                            self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res)
        LOGGER.info("Step 9: Multipart upload completed")

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

        LOGGER.info("Step 11: Create s3 account, create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34081-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 11: Successfully created s3 account and multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify multipart upload during data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34084")
    @CTFailOn(error_handler)
    def test_copy_object_during_pod_restart(self):
        """
        This test tests copy object during data pod restart
        """
        LOGGER.info("STARTED: Test to verify copy object during data pod restart")

        bkt_obj_dict = dict()
        bkt_obj_dict["ha-bkt-{}".format(self.random_time)] = "ha-obj-{}".format(self.random_time)
        output = Queue()

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pods %s are in online state", remain_pod_list)

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

        LOGGER.info("Step 5: Create multiple buckets and upload object to %s and copy to other "
                    "bucket", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]
        LOGGER.info("Step 5: Successfully Created multiple buckets and uploaded object to %s "
                    "and copied to other bucket", self.bucket_name)

        bkt_obj_dict1 = dict()
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        for cnt in range(bkt_cnt):
            bkt_obj_dict1[f"ha-bkt-{cnt}-{perf_counter_ns()}"] = f"ha-obj-{cnt}-{perf_counter_ns()}"
        bkt_obj_dict.update(bkt_obj_dict1)
        LOGGER.info("Step 6: Create multiple buckets and copy object from %s to other buckets in "
                    "background", self.bucket_name)
        args = {'s3_test_obj': s3_test_obj, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict1, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': False,
                'put_etag': put_etag}
        prc = Process(target=self.ha_obj.create_bucket_copy_obj, kwargs=args)
        prc.start()
        LOGGER.info("Step 6: Successfully started background process")

        time.sleep(HA_CFG["common_params"]["1sec_delay"])

        LOGGER.info("Step 7: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 7: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 6: Checking responses from background process")
        prc.join()
        if output.empty():
            LOGGER.error("Failed in Copy Object process")
            assert_utils.assert_true(False, "Expected copy object to be passed")
        else:
            res = output.get()
            put_etag = res[1]
        LOGGER.info("Step 6: Successfully executed copy object in background")

        LOGGER.info("Step 9: Download the uploaded object and verify checksum")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {val} of bucket {key}. Put and "
                                                          f"Get Etag mismatch")
        LOGGER.info("Step 9: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 10: Create s3 account, create multiple buckets and run IOs")
        resp = self.ha_obj.perform_ios_ops(prefix_data='TEST-34084-1', nusers=1, nbuckets=10)
        assert_utils.assert_true(resp[0], resp[1])
        di_check_data = (resp[1], resp[2])
        self.s3_clean.update(resp[2])
        resp = self.ha_obj.perform_ios_ops(di_data=di_check_data, is_di=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop(list(resp[2].keys())[0])
        LOGGER.info("Step 10: Successfully created s3 account and multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify copy object during data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34079")
    @CTFailOn(error_handler)
    def test_ios_during_pod_restart(self):
        """
        This test tests continuous READs/WRITEs/DELETEs in loop during data pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous READs/WRITEs/DELETEs in loop during data "
                    "pod restart")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)
        pod_list.remove(pod_name)
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state", pod_list)

        event = threading.Event()  # Event to be used to send when data pod restart start
        LOGGER.info("Step 5: Perform Continuous READs/WRITEs/DELETEs with variable object sizes. "
                    "0b + - 512Mb) during data pod restart.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34079'
        self.s3_clean = users
        output = Queue()

        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 30, 'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 5: Successfully started READs/WRITEs/DELETEs in background")
        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod again by creating deployment")
        self.restore_pod = False

        LOGGER.info("Step 7: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")
        event.clear()
        thread.join()

        LOGGER.info("Step 8: Verify status for In-flight READs/WRITEs/DELETEs while pod was"
                    "restarting are successful without any failures.")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"IOs during no pod restart contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"IOs during pod restart contain failures: {resp[1]}")
        LOGGER.info("Step 8: Verified status for In-flight READs/WRITEs/DELETEs while pod was"
                    "restarting are successful without any failures.")

        LOGGER.info("COMPLETED: Test to verify continuous READs/WRITEs/DELETEs in loop during data "
                    "pod restart")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34078")
    @CTFailOn(error_handler)
    def test_continuous_deletes_during_pod_restart(self):
        """
        This test tests continuous DELETEs during pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous DELETEs during data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)
        pod_list.remove(pod_name)
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state", pod_list)

        event = threading.Event()  # Event to be used to send when data pod restart start
        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 128MB)")
        wr_output = Queue()
        del_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-34078'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)

        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]           # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Step 5: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB)")

        LOGGER.info("Step 6: Verify %s has %s buckets created", self.s3acc_name, wr_bucket)
        buckets = s3_test_obj.bucket_list()
        assert_utils.assert_equal(wr_bucket, len(buckets[1]), buckets)
        LOGGER.info("Step 6: Verified %s has %s buckets created", self.s3acc_name, wr_bucket)

        LOGGER.info("Step 7: Start Continuous DELETEs in background on %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 7: Successfully started continuous DELETEs in background on %s buckets",
                    del_bucket)

        LOGGER.info("Step 8: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 8: Successfully started the pod again by creating deployment")
        self.restore_pod = False

        LOGGER.info("Step 9: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 9: Verified cluster is in online state. All services are up & running")
        event.clear()
        thread.join()

        LOGGER.info("Step 10: Verify status for In-flight DELETEs while pod was"
                    "restarting are successful & check the remaining buckets.")
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  f"Bucket deletion failed {fail_del_bkt} {event_del_bkt}")
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(wr_bucket - del_bucket, len(buckets),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(buckets)} number of buckets")
        LOGGER.info("Step 10: Verified status for In-flight DELETEs while pod was"
                    "restarting are successful & remaining buckets count is %s", len(buckets))

        LOGGER.info("Step 11: Verify read on the remaining %s buckets.", buckets)
        rd_output = Queue()
        new_s3data = {}
        for bkt in buckets:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = ()
        while len(rd_resp) != 4:
            rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
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
        LOGGER.info("Step 11: Successfully verified READs & DI check for remaining buckets: %s",
                    buckets)
        LOGGER.info("COMPLETED: Test to verify continuous DELETEs during data pod restart.")
