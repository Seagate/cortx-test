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
import threading
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import constants as const
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
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
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
        self.s3_clean = dict()
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.extra_files = list()
        self.restore_pod = self.restore_method = self.deployment_name = self.set_name = None
        self.deployment_backup = None
        self.num_replica = 1
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Get %s pod to be deleted", const.SERVER_POD_NAME_PREFIX)
        sts_dict = self.node_master_list[0].get_sts_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        LOGGER.debug("%s Statefulset: %s", const.SERVER_POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        self.delete_pod = sts_dict[sts][-1]
        LOGGER.info("Pod to be deleted is %s", self.delete_pod)
        self.set_type, self.set_name = self.node_master_list[0].get_set_type_name(
            pod_name=self.delete_pod)
        if self.set_type == const.STATEFULSET:
            resp = self.node_master_list[0].get_num_replicas(self.set_type, self.set_name)
            assert_utils.assert_true(resp[0], resp)
            self.num_replica = int(resp[1])
        else:
            self.num_replica = 1
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
                                                               self.deployment_backup,
                                                           "num_replica": self.num_replica,
                                                           "set_name": self.set_name})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Removing extra files")
        for file in self.extra_files:
            system_utils.remove_file(file)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
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
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod by making replicas=0 and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        if self.set_type == const.STATEFULSET:
            self.set_name = resp[1][pod_name]['deployment_name']
        elif self.set_type == const.REPLICASET:
            self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
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
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
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
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod by making replicas=0 and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        if self.set_type == const.STATEFULSET:
            self.set_name = resp[1][pod_name]['deployment_name']
        elif self.set_type == const.REPLICASET:
            self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
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
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
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
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod by making replicas=0 and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        if self.set_type == const.STATEFULSET:
            self.set_name = resp[1][pod_name]['deployment_name']
        elif self.set_type == const.REPLICASET:
            self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
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
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore server pod by {self.restore_method} "
                                          "way OR the cluster is not online")
        LOGGER.info("Step 4: Successfully started server pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 5: Perform WRITE/READs/verify DI on buckets created in healthy mode.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully run WRITE/READ/Verify on buckets created in healthy "
                    "mode")
        LOGGER.info("Step 6: Perform WRITE/READs/verify DI on buckets created in degraded mode.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully run WRITE/READs/Verify on buckets created in degraded "
                    "mode")
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

    # pylint: disable=too-many-branches
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44839")
    def test_deletes_after_server_pod_restart(self):
        """
        This test tests DELETEs after server pod restart
        """
        LOGGER.info("STARTED: Test to verify DELETEs after server pod restart.")
        wr_output = Queue()
        del_output = Queue()
        deg_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 100
        deg_bucket = 50
        event = threading.Event()
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes.")
        LOGGER.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-44839'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Step 1: Successfully performed WRITEs with variable object sizes.")
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod by making replicas=0 and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        if self.set_type == const.STATEFULSET:
            self.set_name = resp[1][pod_name]['deployment_name']
        elif self.set_type == const.REPLICASET:
            self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        LOGGER.info("Step 3: Perform DELETEs on %s buckets in degraded cluster", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        remain_bkt = s3_test_obj.bucket_list()[1]
        new_bkt = wr_bucket - del_bucket
        assert_utils.assert_equal(len(remain_bkt), new_bkt,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(remain_bkt)} number of buckets")
        LOGGER.info("Step 3: Successfully Performed DELETEs on %s buckets", del_bucket)
        LOGGER.info("Step 4: Create %s buckets and put variable size objects.", deg_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': deg_bucket, 'output': deg_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        deg_resp = tuple()
        while len(deg_resp) != 3:
            deg_resp = deg_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data.update(deg_resp[0])  # Contains s3 data for passed buckets
        buckets_deg = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets_deg), wr_bucket, f"Failed to create {wr_bucket} "
                                                               "number of buckets."
                                                               f"Created {len(buckets_deg)} "
                                                               "number of buckets")
        LOGGER.info("Step 4: Successfully performed WRITEs with variable object sizes.")
        LOGGER.info("Step 5: Restore server pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore server pod by {self.restore_method} "
                                          "way OR the cluster is not online")
        LOGGER.info("Step 5: Successfully started server pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 6: Perform DELETEs again on %s buckets with restarted pod", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        remain_bkt = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(remain_bkt), new_bkt - del_bucket + deg_bucket,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{new_bkt}. Remaining {len(remain_bkt)} number of buckets")
        LOGGER.info("Step 6: Successfully Performed DELETEs on %s buckets", del_bucket)
        LOGGER.info("Step 7: Perform READs and verify on remaining buckets")
        rd_output = Queue()
        new_s3data = dict()
        for bkt in remain_bkt:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = tuple()
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
        LOGGER.info("Step 7: Successfully verified READs and DI check for remaining buckets: %s",
                    remain_bkt)
        LOGGER.info("Step 8: Again create %s buckets and put variable size objects and perform "
                    "delete on %s buckets", wr_bucket, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        new_bkts = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(new_bkts) - len(remain_bkt), wr_bucket,
                                  f"Failed to create {wr_bucket} number of buckets. Created "
                                  f"{len(new_bkts) - len(remain_bkt)} number of buckets")
        LOGGER.info("Perform DELETEs on %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets1 = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets1), wr_bucket - del_bucket + len(remain_bkt),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket + len(remain_bkt)}. Remaining {len(buckets1)} "
                                  "number of buckets")
        LOGGER.info("Step 8: Successfully performed WRITEs with variable object sizes "
                    "and DELETEs on %s buckets", del_bucket)
        LOGGER.info("Step 9: Perform READs and verify on remaining buckets")
        for bkt in buckets1:
            if bkt in s3_data:
                new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = tuple()
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
        LOGGER.info("Step 9: Successfully verified READs and DI check for remaining buckets: %s",
                    buckets1)
        LOGGER.info("ENDED: Test to verify DELETEs after server pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44835")
    def test_reads_during_server_pod_restart(self):
        """
        This test verifies reads during server pod restart
        """
        LOGGER.info("STARTED: Test to verify READs during server pod restart.")
        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        LOGGER.info("Step 1: Perform WRITEs/READs-Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-44835-hlt'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs-Verify with variable sizes objects.")
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod by making replicas=0 and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        if self.set_type == const.STATEFULSET:
            self.set_name = resp[1][pod_name]['deployment_name']
        elif self.set_type == const.REPLICASET:
            self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        LOGGER.info("Step 3: Perform WRITEs/READs-Verify with variable object sizes and create "
                    "new bucket in degraded mode")
        self.test_prefix_deg = 'test-44835-deg'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed WRITEs/READs-Verify with variable object sizes and create "
                    "new bucket in degraded mode")
        LOGGER.info("Step 4: Perform READs and verify DI on the data in background of healthy "
                    "cluster")
        self.test_prefix = 'test-44835-hlt'
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                'output': output, 'setup_s3bench': False}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Successfully started READs and verified DI on the written data in "
                    "background of healthy cluster")
        LOGGER.info("Step 5: Starting pod again by statefulset")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 5: Successfully started the pod by statefulset")
        self.restore_pod = False
        event.clear()
        thread.join()
        LOGGER.info("Step 6: Verifying responses from background processes")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        LOGGER.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses["fail_res"])
        LOGGER.debug("Fail logs list: %s", fail_logs)
        pass_logs1 = fail_logs1 = list()
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs + pass_logs1)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs + fail_logs1)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 6: Successfully completed READs and verified DI on the written data in "
                    "background of healthy cluster")
        LOGGER.info("Step 7: Perform READ-Verify on data written in degraded mode")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READ-Verify on data written in degraded mode")
        LOGGER.info("Step 8: Perform WRITEs/READs-Verify after server pod restart")
        self.test_prefix = 'test-44835-rstrt'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully ran IOs after server pod restart")
        LOGGER.info("ENDED: Test to verify continuous READs during data pod restart.")
