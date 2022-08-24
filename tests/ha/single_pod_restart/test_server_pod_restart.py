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
import time
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
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
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
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
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
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
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
        del_bucket = wr_bucket - HA_CFG["s3_bucket_data"]["no_bck_writes"]
        new_bkt = wr_bucket - del_bucket
        deg_bucket = HA_CFG["s3_bucket_data"]["degraded_bucket"]
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
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
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
        LOGGER.info("Step 7: Successfully verify READs and DI check for remaining buckets: %s",
                    remain_bkt)
        LOGGER.info("Step 8: Again create %s buckets and put variable size objects and perform "
                    "delete on %s buckets", wr_bucket, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for updated buckets
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
        LOGGER.info("Step 9: Successfully verify READs and DI check for remaining buckets: %s",
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
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        LOGGER.info("Step 3: Create new buckets and perform WRITEs/READs-Verify with variable "
                    "object sizes")
        self.test_prefix_deg = 'test-44835-deg'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed WRITEs/READs-Verify with variable object")
        LOGGER.info("Step 4: Perform READs and verify DI on the data written in healthy cluster "
                    "in background")
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                'output': output, 'setup_s3bench': False}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Successfully started READs and verify DI on data written in healthy"
                    " cluster in background ")
        LOGGER.info("Step 5: Restart the pod with replica method and check cluster status")
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
        LOGGER.info("Step 5: Successfully restart the pod with replica method and checked "
                    "cluster status")
        self.restore_pod = False
        event.clear()
        thread.join()
        LOGGER.info("Step 6: Verifying responses from background processes")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        LOGGER.debug("Pass logs list: %s \nFail logs list: %s", pass_logs, fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")
        LOGGER.info("Step 6: Successfully completed READs and verify DI on the data written in "
                    "healthy cluster in background")
        LOGGER.info("Step 7: Perform READ-Verify on data written in step3")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READ-Verify on data written in step3")
        LOGGER.info("Step 8: Perform WRITEs/READs-Verify after server pod restart")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-44835-rstrt'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully ran IOs after server pod restart")
        LOGGER.info("ENDED: Test to verify READs during server pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34261")
    def test_server_pod_restart_kubectl_delete(self):
        """
        Verify IOs during pod restart (kubectl delete)
        """
        LOGGER.info("STARTED: Verify IOs during server pod restart (kubectl delete)")
        del_bucket = HA_CFG["bg_bucket_ops"]["no_del_buckets"]
        del_output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        t_t = int(perf_counter_ns())

        LOGGER.info("Perform IOs with variable object sizes during server pod restart")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"], max_attempts=1)
        LOGGER.info("Step 1.1: Perform WRITEs on %s buckets for background DELETEs", del_bucket)
        test_prefix_del = f'test-del-34261-{t_t}'
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        written_bck = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(written_bck), del_bucket,
                                  f"Failed to create {del_bucket} number of buckets."
                                  f"Created {len(written_bck)} number of buckets")
        LOGGER.info("Step 1.1: Performed WRITEs on %s buckets for background DELETEs", del_bucket)

        LOGGER.info("Step 1.2: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = f'test-read-34261-{t_t}'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1.2: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Step 2: Start WRITEs, READs and DELETEs with variable object sizes "
                    "during server pod restart using kubectl delete")
        LOGGER.info("Step 2.1: Start WRITEs with variable object sizes in background")
        test_prefix_write = f'test-write-34261-{t_t}'
        output_wr = Queue()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 2, 'nsamples': 10, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False, 'event_set_clr': event_set_clr}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        LOGGER.info("Step 2.1: Successfully started WRITEs with variable sizes objects"
                    " in background")

        LOGGER.info("Step 2.2: Start READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False, 'event_set_clr': event_set_clr}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        LOGGER.info("Step 2.2: Successfully started READs and verify DI on the written data in "
                    "background")

        LOGGER.info("Step 2.3: Starting DELETEs of %s buckets in background", del_bucket)
        del_buckets = written_bck.copy()
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': del_buckets,
                'bkts_to_del': del_bucket, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_wri.start()
        thread_rd.start()
        thread_del.start()
        LOGGER.info("Step 2.3: Successfully started DELETEs of %s buckets in background",
                    del_bucket)
        LOGGER.info("Step 2: Started WRITEs, READs and DELETEs with variable object sizes "
                    "during server pod restart using kubectl delete")
        LOGGER.info("Waiting for %s seconds", HA_CFG["common_params"]["10sec_delay"])
        time.sleep(HA_CFG["common_params"]["10sec_delay"])

        LOGGER.info("Step 3: Restart the server pod by kubectl delete.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = self.system_random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        event.set()
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to delete pod {pod_name} by kubectl delete")
        LOGGER.info("Step 3: Successfully restarted pod %s by kubectl delete", pod_name)

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in good state")
        event.clear()
        thread_wri.join()
        thread_rd.join()
        thread_del.join()

        LOGGER.info("Background WRITEs, READs and DELETEs threads joined successfully.")
        LOGGER.info("Step 5: Verify responses from background processes")
        LOGGER.info("Step 5.1: Verify status for In-flight WRITEs")
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "WRITEs before and after pod deletion are "
                                                "expected to pass. Logs which contain failures:"
                                                f" {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        LOGGER.debug("WRITEs Response for fail logs: %s", resp)
        # TODO: Need to change following condition once we start getting failures for background
        #  IOs during pod deletion and re-test
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs), "Some In-flight WRITEs are "
                                                                 "expected to fail. No failure is"
                                                                 f"observed in {resp[1]}")
        LOGGER.info("Step 5.1: Verified status for In-flight WRITEs")

        LOGGER.info("Step 5.2: Verifying responses from READs background process")
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"READs/VerifyDI before and after pod deletion are "
                                  "expected to pass. Logs which contain failures:"
                                  f" {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        LOGGER.info("READs Response for fail logs: %s", resp[1])
        # TODO: Need to change following condition once we start getting failures for background
        #  IOs during pod deletion and re-test
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs), "Some In-flight READs are "
                                                                 "expected to fail. No failure is"
                                                                 f"observed in {resp[1]}")
        LOGGER.info("Step 5.2: Verified responses from READs background process")

        LOGGER.info("Step 5.3: Verifying responses from DELETEs background process")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do DELETEs")
        event_del_bkt = del_resp[0]  # Contains buckets when event was set
        fail_del_bkt = del_resp[1]  # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_del_bkt), "Expected pass, buckets which failed in "
                                                     f"DELETEs before and after pod deletion:"
                                                     f" {fail_del_bkt}.")
        # TODO: Uncomment following once we start getting failures for background IOs during pod
        #  deletion and re-test
        # assert_utils.assert_true(len(event_del_bkt), "Expected FAIL when event was set")
        LOGGER.info("Failed buckets while in-flight DELETEs operation : %s", event_del_bkt)
        LOGGER.info("Step 5.3: Verified responses from DELETEs background process")
        LOGGER.info("Step 5: Verified responses from background processes")

        LOGGER.info("Step 6: Start IOs (create IAM user, buckets and upload objects) after pod "
                    "restart by kubectl delete")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34261'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully IOs completed after pod restart by kubectl delete")
        LOGGER.info("COMPLETED: Verify IOs during server pod restart (kubectl delete)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44837")
    def test_writes_during_server_pod_restart(self):
        """
        Verify WRITEs during server pod restart
        """
        LOGGER.info("STARTED: Test to verify Writes during server pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-44837'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        LOGGER.info("Step 3: Start WRITEs with variable object sizes in background")
        self.test_prefix_deg = 'test-44837-deg'
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix_deg,
                'skipread': True, 'skipcleanup': True, 'nclients': 2, 'nsamples': 30,
                'setup_s3bench': False, 'output': output}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 3: Started WRITEs with variable sizes objects in background.")
        LOGGER.info("Waiting for %s seconds", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 4: Restart the pod with replica method and check cluster status")
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
        LOGGER.info("Step 4: Successfully restart the pod with replica method and checked "
                    "cluster status")
        self.restore_pod = False
        event.clear()
        thread.join()
        LOGGER.info("Step 5: Verifying writes from background process")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "WRITEs before and after pod deletion are "
                                                "expected to pass.Logs which contain failures:"
                                                f"{resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs), "Some In-flight WRITEs are "
                                                                 "expected to fail. Logs which "
                                                                 f"contain passed IOs: {resp[1]}")
        LOGGER.info("Step 5: Successfully completed writes in background")
        LOGGER.info("Step 6: Read/Verify data written in background process")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix_deg,
                                                    skipwrite=True, skipcleanup=True,
                                                    nsamples=30, nclients=30, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Read/Verify successfully on data written in background")
        LOGGER.info("Step 7: Run READ/Verify on data written in healthy cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Read/Verify successful on data written in healthy cluster")
        LOGGER.info("Step 8: Create new IAM user and run IOs on cluster with restarted pod")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-44837-restart'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: IOs completed successfully.")
        LOGGER.info("ENDED: Test to verify writes during server pod restart.")

    # pylint: disable=multiple-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44840")
    def test_deletes_during_server_pod_restart(self):
        """
        This test tests DELETEs during server pod restart
        """
        LOGGER.info("STARTED: Test to verify DELETEs during server pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users_org = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-44840-org'
        self.s3_clean.update(users_org)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects")
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        event = threading.Event()  # Event to be used to send when server pod restart start
        LOGGER.info("Step 3: Perform WRITEs with variable object sizes for DELETEs")
        wr_output = Queue()
        del_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - HA_CFG["s3_bucket_data"]["no_bck_writes"]
        LOGGER.info("Create IAM user account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix_deg = 'test-44840-deg'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix_deg, 'test_dir_path': self.test_dir_path,
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
        LOGGER.info("Step 3: Successfully performed WRITEs with variable object sizes.")
        LOGGER.info("Step 4: Start Continuous DELETEs in background on %s buckets", del_bucket)
        get_random_buck = self.system_random.sample(buckets, del_bucket)
        args = {'test_prefix': self.test_prefix_deg, 'test_dir_path': self.test_dir_path,
                'bkt_list': get_random_buck, 'skipput': True, 'skipget': True,
                'bkts_to_del': del_bucket, 'output': del_output}
        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Successfully started continuous DELETEs in background on %s buckets",
                    del_bucket)
        LOGGER.info("Step 5: Restart the pod with replica method and check cluster status")
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
        self.restore_pod = False
        LOGGER.info("Step 5: Successfully restart the pod with replica method and checked "
                    "cluster status")
        event.clear()
        thread.join()
        LOGGER.info("Step 6: Verify status for In-flight DELETEs while pod was restarting are "
                    "successful & check the remaining buckets.")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  "Bucket deletion failed in server pod restart process"
                                  f"{fail_del_bkt} {event_del_bkt}")
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(wr_bucket - del_bucket, len(buckets),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(buckets)} number of buckets")
        LOGGER.info("Step 6: Verified status for In-flight DELETEs while pod was restarting are "
                    "successful & remaining buckets count is %s", len(buckets))
        LOGGER.info("Step 7: Verify read/DI check on the remaining %s buckets.", buckets)
        rd_output = Queue()
        new_s3data = dict()
        for bkt in buckets:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix_deg, 'test_dir_path': self.test_dir_path,
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
        LOGGER.info("Step 7: Successfully verified READs & DI check for remaining buckets: %s",
                    buckets)
        LOGGER.info("Step 8: Check READ/Verify on data written in healthy mode and delete buckets")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: READ/Verify on data written in healthy mode was successful and "
                    "buckets deleted.")
        LOGGER.info("Step 9: Create IAM user with multiple buckets and run IOs when "
                    "server pod %s is restarted.", pod_name)
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-44840-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, nsamples=2,
                                                    nclients=2, setup_s3bench=False,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created IAM user with multiple buckets and ran IOs.")
        LOGGER.info("COMPLETED: Test to verify continuous DELETEs during server pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44838")
    def test_read_write_during_server_pod_restart(self):
        """
        Verify READ/WRITEs during server pod restart
        """
        LOGGER.info("STARTED: Test to verify READ/WRITE during server pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        LOGGER.info("Create 2 set of buckets to be used for writes and reads")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        test_prefix_read = 'test-44838-read'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipcleanup=True,
                                                    nsamples=5, nclients=5, skipread=True)
        assert_utils.assert_true(resp[0], resp[1])
        test_prefix_write = 'test-44838-write'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_write, skipcleanup=True,
                                                    nsamples=5, nclients=5, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        event = threading.Event()  # Event to be used to send intimation of server pod restart
        LOGGER.info("Step 3: create new buckets and start READ/WRITEs/VERIFY with variable object"
                    " sizes in background")
        LOGGER.info("Step 3.1: Start WRITEs with variable object sizes in background")
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 5, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 3.1: Successfully started WRITEs with variable sizes objects"
                    " in background")
        LOGGER.info("Step 3.2: Start READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 2, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 3.2: Successfully started READs and verify on the written data in "
                    "background")
        LOGGER.info("Step 3: Successfully started READ/WRITEs/VERIFY with variable object sizes"
                    " in background")
        LOGGER.info("Waiting for %s seconds", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 4: Restart the pod with replica method and check cluster status")
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
        self.restore_pod = False
        LOGGER.info("Step 4: Successfully restart the pod with replica method and checked "
                    "cluster status")
        event.clear()
        thread_wri.join()
        thread_rd.join()
        LOGGER.info("Step 5.1: Verify status for In-flight WRITEs while %s server pod "
                    "restarted ", pod_name)
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"WRITEs before and after pod restart are "
                                                f"expected to pass. Logs which contain "
                                                f"failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "In-flight WRITEs logs contain failures:"
                                                f" {resp[1]}")
        LOGGER.info("Step 5.1: Verified status for In-flight WRITEs while %s server pod "
                    "restarted", pod_name)
        LOGGER.info("Step 5.2: Verify status for In-flight READs/Verify DI while %s"
                    " server pod restarted.", pod_name)
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"READs/VerifyDI logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "READs/VerifyDI logs which contain failure:"
                                                f" {resp[1]}")
        LOGGER.info("Step 5.2: Verified status for In-flight READs/VerifyDI while %s "
                    " server pod restarted.", pod_name)
        LOGGER.info("Step 6: Create new IAM user and run IOs on cluster with restarted pod")
        users_rst = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users_rst)
        self.test_prefix = 'test-44838-restart'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs completed successfully.")
        LOGGER.info("ENDED: Test to verify READs/WRITE during server pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44841")
    def test_ios_during_server_pod_restart(self):
        """
        This test tests READs/WRITEs/DELETEs in loop during server pod restart
        """
        LOGGER.info("STARTED: Test to verify READs/WRITEs/DELETEs in loop during server pod "
                    "restart")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users_org = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-44841'
        self.s3_clean.update(users_org)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        num_replica = self.num_replica - 1
        LOGGER.info("Step 2: Shutdown server pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], delete_pod=[self.delete_pod],
            num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete server pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        event = threading.Event()  # Event to be used to send when server pod restart start
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 3.1: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        remaining_bkt = HA_CFG["s3_bucket_data"]["no_bck_writes"]
        del_bucket = wr_bucket - remaining_bkt
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]['accesskey']
        secret_key = list(users.values())[0]['secretkey']
        test_prefix_del = 'test-delete-44841'
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           "number of buckets")
        s3_data = wr_resp[0]
        LOGGER.info("Step 3.1: Successfully performed WRITEs with variable object sizes on %s "
                    "buckets for parallel DELETEs.", wr_bucket)
        LOGGER.info("Step 3.2: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = 'test-read-44841'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3.2: Performed WRITEs with variable sizes objects for parallel READs.")
        LOGGER.info("Step 4: Starting three independent background threads for READs, WRITEs & "
                    "DELETEs.")
        LOGGER.info("Step 4.1: Start continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = s3_data.keys()
        get_random_buck = self.system_random.sample(bucket_list, del_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 4.1: Successfully started DELETEs in background for %s buckets",
                    del_bucket)
        LOGGER.info("Step 4.2: Perform WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-44841'
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 4.2: Successfully started WRITEs with variable sizes objects in "
                    "background")
        LOGGER.info("Step 4.3: Perform READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 4.3: Successfully started READs and verify on the written data in "
                    "background")
        LOGGER.info("Step 4: Successfully starting three independent background threads for READs,"
                    " WRITEs & DELETEs.")
        LOGGER.info("Wait for %s seconds for all background operations to start",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 5: Restart the pod with replica method and check cluster status")
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
        LOGGER.info("Step 5: Successfully restart the pod with replica method and checked "
                    "cluster status")
        self.restore_pod = False
        event.clear()
        LOGGER.info("Step 6: Verify status for In-flight READs/WRITEs/DELETEs while server pod %s "
                    "was restarted.", pod_name)
        LOGGER.info("Waiting for background IOs thread to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 6.1: Verify status for In-flight DELETEs")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  "Bucket deletion failed in server pod restart process "
                                  f"{fail_del_bkt} {event_del_bkt}")
        rem_bkts_aftr_del = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equals(len(rem_bkts_aftr_del), wr_bucket - del_bucket,
                                   "All buckets are expected to be deleted while server pod "
                                   "restarted")
        LOGGER.info("Step 6.1: Verified status for In-flight DELETEs")
        LOGGER.info("Step 6.2: Verify status for In-flight WRITEs")
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "WRITEs before and after pod deletion are "
                                                "expected to pass.Logs which contain failures:"
                                                f"{resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "In-flight WRITEs Logs which contain failures: "
                                                f"{resp[1]}")
        LOGGER.info("Step 6.2: Verified status for In-flight WRITEs")
        LOGGER.info("Step 6.3: Verify status for In-flight READs/Verify DI")
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "READs/VerifyDI logs which contain failures:"
                                                f"{resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "READs/VerifyDI Logs which contain failures: "
                                                f"{resp[1]}")
        LOGGER.info("Step 6.3: Verified status for In-flight READs/Verify DI")
        LOGGER.info("Step 6: Verified status for In-flight READs/WRITEs/DELETEs while server pod "
                    "%s was restarted.", pod_name)
        LOGGER.info("Step 7: Verify READ/Verify for data written in healthy cluster and delete "
                    "buckets")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Verified READ/Verify on data written in healthy mode and deleted "
                    "buckets")
        LOGGER.info("COMPLETED: Test to verify READs/WRITEs/DELETEs in loop during server "
                    "pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44854")
    def test_server_pod_restart_kubectl_delete_retries(self):
        """
        Verify IOs with retries during pod restart (kubectl delete)
        """
        LOGGER.info("STARTED: Verify IOs with retries during server pod restart (kubectl delete)")
        del_bucket = HA_CFG["bg_bucket_ops"]["no_del_buckets"]
        del_output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        t_t = int(perf_counter_ns())

        LOGGER.info("Perform IOs with variable object sizes during server pod restart")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Step 1.1: Perform WRITEs on %s buckets for background DELETEs", del_bucket)
        test_prefix_del = f'test-44854-del-{t_t}'
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        written_bck = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(written_bck), del_bucket,
                                  f"Failed to create {del_bucket} number of buckets."
                                  f"Created {len(written_bck)} number of buckets")
        LOGGER.info("Step 1.1: Performed WRITEs on %s buckets for background DELETEs", del_bucket)

        LOGGER.info("Step 1.2: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = f'test-44854-read-{t_t}'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1.2: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Step 2: Start WRITEs, READs and DELETEs with variable object sizes "
                    "during server pod restart using kubectl delete")
        LOGGER.info("Step 2.1: Start WRITEs with variable object sizes in background")
        test_prefix_write = f'test-44854-write-{t_t}'
        output_wr = Queue()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 2, 'nsamples': 10, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False, 'event_set_clr': event_set_clr,
                'max_retries': HA_CFG["common_params"]["io_retry_count"]}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread

        LOGGER.info("Step 2.2: Start READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False, 'event_set_clr': event_set_clr,
                'max_retries': HA_CFG["common_params"]["io_retry_count"]}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread

        LOGGER.info("Step 2.3: Starting DELETEs of %s buckets in background", del_bucket)
        del_buckets = written_bck.copy()
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': del_buckets,
                'bkts_to_del': del_bucket, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_wri.start()
        thread_rd.start()
        thread_del.start()
        LOGGER.info("Step 2: Started WRITEs, READs-Verify and DELETEs with variable object sizes "
                    "during server pod restart using kubectl delete")
        LOGGER.info("Waiting for %s seconds", HA_CFG["common_params"]["10sec_delay"])
        time.sleep(HA_CFG["common_params"]["10sec_delay"])

        LOGGER.info("Step 3: Restart the server pod by kubectl delete.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = self.system_random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        event.set()
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to delete pod {pod_name} by kubectl delete")
        LOGGER.info("Step 3: Successfully restarted pod %s by kubectl delete", pod_name)

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in good state")
        event.clear()
        thread_wri.join()
        thread_rd.join()
        thread_del.join()

        LOGGER.info("Background WRITEs, READs and DELETEs threads joined successfully.")
        LOGGER.info("Step 5: Verify responses from background processes")
        LOGGER.info("Step 5.1: Verify status for In-flight WRITEs")
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), "WRITEs before and after pod deletion are "
                                                "expected to pass. Logs which contain failures:"
                                                f" {resp[1]}. Logs for IOs when event was clear: "
                                                f"{pass_logs}. Logs for IOs when event was set:"
                                                f" {fail_logs}")
        LOGGER.info("Step 5.1: Verified status for In-flight WRITEs")

        LOGGER.info("Step 5.2: Verifying responses from READs background process")
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"READs/VerifyDI before and after pod deletion are "
                                  "expected to pass. Logs which contain failures:"
                                  f" {resp[1]}. Logs for IOs when event was clear: {pass_logs}. "
                                  f"Logs for IOs when event was set: {fail_logs}")
        LOGGER.info("Step 5.2: Verified responses from READs background process")

        LOGGER.info("Step 5.3: Verifying responses from DELETEs background process")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do DELETEs")
        event_del_bkt = del_resp[0]  # Contains buckets when event was set
        fail_del_bkt = del_resp[1]  # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  "Expected all pass, Buckets which failed in DELETEs before and "
                                  f"after pod deletion: {fail_del_bkt}. Buckets which failed in "
                                  f"DELETEs during pod deletion: {event_del_bkt}.")
        LOGGER.info("Step 5.3: Verified responses from DELETEs background process")
        LOGGER.info("Step 5: Verified responses from background processes")

        LOGGER.info("Step 6: Start IOs (create IAM user, buckets and upload objects) after pod "
                    "restart by kubectl delete")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-44854'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully IOs completed after pod restart by kubectl delete")
        LOGGER.info("COMPLETED: Verify IOs during server pod restart (kubectl delete)")
