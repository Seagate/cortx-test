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
import time
import threading
from time import perf_counter_ns
from multiprocessing import Queue

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.pods_helper import LogicalNode
from commons.helpers.health_helper import Health
from commons import constants as const
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from config import HA_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

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
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.hlth_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = cls.random_time = cls.s3_clean = None
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
                cls.hlth_worker_list.append(Health(hostname=cls.host,
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
        pod_name = random.sample(pod_list, 1)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        LOGGER.info("Step 4: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
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
        pod_name = random.sample(pod_list, 1)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        LOGGER.info("Step 4: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
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
        pod_name = random.sample(pod_list, 1)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        LOGGER.info("Step 4: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
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
        while len(wr_resp) != 3: wr_resp = wr_output.get(timeout=60)  # pylint: disable=C0321
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
        while len(del_resp) != 2: del_resp = del_output.get(timeout=60)  # pylint: disable=C0321
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
        while len(rd_resp) != 4: rd_resp = rd_output.get(timeout=60)  # pylint: disable=C0321
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
                    buckets)

        LOGGER.info("Step 10: Again create %s buckets and put variable size objects and perform "
                    "delete on %s buckets", wr_bucket, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3: wr_resp = wr_output.get(timeout=60)  # pylint: disable=C0321
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
        while len(del_resp) != 2: del_resp = del_output.get(timeout=60)  # pylint: disable=C0321
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
        while len(rd_resp) != 4: rd_resp = rd_output.get(timeout=60)  # pylint: disable=C0321
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
        pod_name = random.sample(pod_list, 1)

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
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        LOGGER.info("Step 4: Check services status on remaining pods %s", pod_list.remove(pod_name))
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list.remove(pod_name),
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

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        event.clear()

        thread.join()
        responses = ()
        while len(responses) != 2: responses = output.get(timeout=60)  # pylint: disable=C0321
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain passed IOs: {resp[1]}")
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
