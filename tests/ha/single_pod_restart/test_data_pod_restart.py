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
HA test suite for single data Pod restart
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
from libs.ha.ha_common_api_libs_k8s import HAK8sApiLibs
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods
class TestDataPodRestart:
    """
    Test suite for single Data Pod Restart
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.setup_type = CMN_CFG["setup_type"]
        cls.username = []
        cls.password = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.ha_api = HAK8sApiLibs()
        cls.s3_clean = cls.test_prefix = cls.test_prefix_deg = cls.set_name = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.multipart_obj_path = cls.set_name = cls.version_etag = None
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
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restore_pod = False
        self.s3_clean = dict()
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.extra_files = list()
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("Get %s pod to be deleted", const.POD_NAME_PREFIX)
        sts_dict = self.node_master_list[0].get_sts_pods(pod_prefix=const.POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        LOGGER.debug("%s Statefulset: %s", const.POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        self.delete_pod = sts_dict[sts][-1]
        LOGGER.info("Pod to be deleted is %s", self.delete_pod)
        self.set_type, self.set_name = self.node_master_list[0].get_set_type_name(
            pod_name=self.delete_pod)
        resp = self.node_master_list[0].get_num_replicas(self.set_type, self.set_name)
        assert_utils.assert_true(resp[0], resp)
        self.num_replica = int(resp[1])
        LOGGER.info("Create IAM user")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        self.s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                     endpoint_url=S3_CFG["s3_url"])
        self.s3_ver = S3VersioningTestLib(access_key=access_key, secret_key=secret_key,
                                          endpoint_url=S3_CFG["s3_url"], region=S3_CFG["region"])
        LOGGER.info("Created IAM user")
        if self.setup_type == "VM":
            self.f_size = str(HA_CFG["5gb_mpu_data"]["file_size_512M"]) + "M"
        else:
            self.f_size = str(HA_CFG["5gb_mpu_data"]["file_size"]) + "M"
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
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
        LOGGER.info("Removing all files from %s", self.test_dir_path)
        if os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34072")
    def test_reads_after_pod_restart(self):
        """
        This test tests READs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify READs after data pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34072'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("STEP 3: Perform READs/Verify on data written in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs/Verify on data written in healthy cluster.")
        LOGGER.info("Step 4: Perform WRITEs/READs/Verify with variable object sizes.")
        if CMN_CFG["dtm0_disabled"]:
            self.test_prefix_deg = 'test-34072-deg'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipcleanup=True, setup_s3bench=False)
        else:
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 5: Restore pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way "
                                          "OR the cluster is not online")
        LOGGER.info("Step 5: Successfully started the pod and cluster is online.")
        self.restore_pod = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 6: Perform READs and verify DI on the written data in degraded "
                        "cluster with new buckets and objects.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipwrite=True, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Successfully run READ/Verify on data written in degraded cluster "
                        "with new buckets and objects.")
        LOGGER.info("Step 6: Perform READs and verify DI on the written data with buckets created "
                    "in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully run READ/Verify on data written with buckets created "
                    "in healthy cluster")
        LOGGER.info("ENDED: Test to verify READs after data pod restart.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34074")
    def test_write_after_pod_restart(self):
        """
        This test tests WRITEs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify WRITEs after data pod restart.")

        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34074'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Perform WRITEs with variable object sizes")
        if CMN_CFG["dtm0_disabled"]:
            self.test_prefix_deg = 'test-34074-deg'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipread=True, skipcleanup=True,
                                                        setup_s3bench=False)
        else:
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix, skipread=True,
                                                        skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed WRITEs with variable sizes objects.")
        LOGGER.info("Step 4: Restore pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way "
                                          "OR the cluster is not online")
        LOGGER.info("Step 4: Successfully started the pod and cluster is online.")
        self.restore_pod = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 5: Perform READs and verify DI on the written data in degraded "
                        "cluster with new buckets and objects.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipwrite=True, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 5: Successfully run READ/Verify on data written in degraded cluster "
                        "with new buckets and objects.")
        LOGGER.info("Step 5: Perform READs and verify DI on the written data with buckets created "
                    "in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully run READ/Verify on data written with buckets created "
                    "in healthy cluster")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 6: Create new IAM user and buckets, Perform WRITEs-READs-Verify "
                        "with variable object sizes.")
            users = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix = 'test-34074-restart'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Performed WRITEs-READs-Verify with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify WRITEs after data pod restart.")

    # pylint: disable=multiple-statements
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds not supported in DTM0")
    @pytest.mark.tags("TEST-34077")
    def test_deletes_after_pod_restart(self):
        """
        This test tests DELETEs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify DELETEs after data pod restart.")
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
        self.test_prefix = 'test-34077'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")

        LOGGER.info("Step 1: Successfully performed WRITEs with variable object sizes.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Perform DELETEs on %s buckets in degraded cluster", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
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
        deg_resp = ()
        while len(deg_resp) != 3:
            deg_resp = deg_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data.update(deg_resp[0])  # Contains s3 data for passed buckets
        buckets_deg = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets_deg), deg_bucket, f"Failed to create {deg_bucket} "
                                                                "number of buckets."
                                                                f"Created {len(buckets_deg)} "
                                                                "number of buckets")
        LOGGER.info("Step 4: Successfully performed WRITEs with variable object sizes.")
        LOGGER.info("Step 5: Restore pod and check cluster status.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way "
                                          "OR the cluster is not online")
        LOGGER.info("Step 5: Successfully started the pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 6: Perform DELETEs again on %s buckets with restarted pod", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        remain_bkt = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(remain_bkt), new_bkt - del_bucket + deg_bucket,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{new_bkt}. Remaining {len(remain_bkt)} number of buckets")
        LOGGER.info("Step 6: Successfully Performed DELETEs on %s buckets", del_bucket)
        LOGGER.info("Step 7: Perform READs and verify on remaining buckets")
        rd_output = Queue()
        new_s3data = {}
        for bkt in remain_bkt:
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
        LOGGER.info("Step 7: Successfully verified READs and DI check for remaining buckets: %s",
                    remain_bkt)
        LOGGER.info("Step 8: Again create %s buckets and put variable size objects and perform "
                    "delete on %s buckets", wr_bucket, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
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
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets1 = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets1), wr_bucket - del_bucket + len(remain_bkt),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket + len(remain_bkt)}. Remaining {len(buckets1)} number"
                                  " of buckets")
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
        LOGGER.info("Step 9: Successfully verified READs and DI check for remaining buckets: %s",
                    buckets1)
        LOGGER.info("ENDED: Test to verify DELETEs after data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34073")
    def test_reads_during_pod_restart(self):
        """
        This test tests continuous reads during pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous READs during data pod restart.")
        output = Queue()
        output1 = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        LOGGER.info("Step 1: Perform WRITEs/READs-Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34073-hlt'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs-Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Perform READ-Verify on data written in Step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed WRITEs/READs-Verify with variable sizes objects.")
        LOGGER.info("Step 4: Perform WRITEs/READs-Verify with variable object sizes.")
        if CMN_CFG["dtm0_disabled"]:
            self.test_prefix = 'test-34073-deg'

        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs/READs-Verify with variable object sizes.")
        LOGGER.info("Step 5: Perform READs and verify DI on the data in background")
        self.test_prefix = 'test-34073-hlt'
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                'output': output, 'setup_s3bench': False}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        thread1 = None
        if CMN_CFG["dtm0_disabled"]:
            self.test_prefix = 'test-34073-deg'
            args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                    'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                    'output': output1, 'setup_s3bench': False}
            thread1 = threading.Thread(target=self.ha_obj.event_s3_operation,
                                       args=(event,), kwargs=args)
            thread1.daemon = True  # Daemonize thread
            thread1.start()
        LOGGER.info("Step 5: Successfully started READs and verified DI on the written data in "
                    "background")
        LOGGER.info("Step 6: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 6: Successfully started the pod and cluster is online")
        self.restore_pod = False
        event.clear()
        thread.join()
        if CMN_CFG["dtm0_disabled"]:
            thread1.join()
        LOGGER.info("Step 7: Verifying responses from background processes")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        pass_logs1 = fail_logs1 = list()
        if CMN_CFG["dtm0_disabled"]:
            responses1 = dict()
            while len(responses1) != 2:
                responses1 = output1.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            pass_logs1 = list(x[1] for x in responses1["pass_res"])
            fail_logs1 = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs + pass_logs1)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs + fail_logs1)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 7: Successfully completed READs and verified DI on the written data in "
                    "background")
        LOGGER.info("Step 8: Perform WRITEs/READs-Verify")
        if CMN_CFG["dtm0_disabled"]:
            self.test_prefix = 'test-34073-rstrt'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully ran IOs")
        LOGGER.info("ENDED: Test to verify continuous READs during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Bucket CRUDs not supported in DTM0Int0")
    @pytest.mark.tags("TEST-34079")
    def test_ios_during_pod_restart(self):
        """
        This test tests READs/WRITEs/DELETEs in loop during data pod restart
        """
        LOGGER.info("STARTED: Test to verify READs/WRITEs/DELETEs in loop during data pod restart")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users_org = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34079'
        self.s3_clean.update(users_org)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        event = threading.Event()  # Event to be used to send when data pod restart start
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 3: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        remaining_bkt = 10
        del_bucket = wr_bucket - remaining_bkt
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]['accesskey']
        secret_key = list(users.values())[0]['secretkey']
        test_prefix_del = 'test-delete-34079'
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
        LOGGER.info("Step 3: Successfully performed WRITEs with variable object sizes on %s "
                    "buckets for parallel DELETEs.", wr_bucket)
        LOGGER.info("Step 4: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = 'test-read-34079'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs with variable sizes objects for parallel READs.")
        LOGGER.info("Starting three independent background threads for READs, WRITEs & DELETEs.")
        LOGGER.info("Step 5: Start continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = s3_data.keys()
        get_random_buck = self.system_random.sample(bucket_list, del_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 5: Successfully started DELETEs in background for %s buckets", del_bucket)
        LOGGER.info("Step 6: Perform WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-34079'
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 6: Successfully started WRITEs with variable sizes objects in background")
        LOGGER.info("Step 7: Perform READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 6: Successfully started READs and verify on the written data in "
                    "background")
        LOGGER.info("Wait for %s seconds for all background operations to start",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 7: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 7: Successfully started the pod and cluster is online")
        self.restore_pod = False
        event.clear()
        LOGGER.info("Step 8: Verify status for In-flight READs/WRITEs/DELETEs while data pod %s "
                    "was restarted.", pod_name)
        LOGGER.info("Waiting for background IOs thread to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 8.1: Verify status for In-flight DELETEs")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        fail_del_bkt = del_resp[1]
        rem_bkts_aftr_del = s3_test_obj.bucket_list()[1]
        assert_utils.assert_false(len(fail_del_bkt),
                                  "Bucket deletion failed when cluster was degraded"
                                  f" {fail_del_bkt}")
        assert_utils.assert_equals(len(rem_bkts_aftr_del), del_bucket,
                                 "All buckets are expected to be deleted while pod restarted")
        LOGGER.info("Step 8.1: Verified status for In-flight DELETEs")
        LOGGER.info("Step 8.2: Verify status for In-flight WRITEs")
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8.2: Verified status for In-flight WRITEs")
        LOGGER.info("Step 8.3: Verify status for In-flight READs/Verify DI")
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8.3: Verified status for In-flight READs/Verify DI")
        LOGGER.info("Step 8: Verified status for In-flight READs/WRITEs/DELETEs while data pod %s "
                    "was restarted.", pod_name)
        LOGGER.info("Step 9: Verify READ/Verify for data written in healthy cluster and delete "
                    "buckets")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Verified READ/Verify on data written in healthy mode and deleted "
                    "buckets")
        LOGGER.info("COMPLETED: Test to verify READs/WRITEs/DELETEs in loop during data "
                    "pod restart")

    # pylint: disable=multiple-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Bucket CRUDs not supported with DTM0Int0")
    @pytest.mark.tags("TEST-34078")
    def test_deletes_during_pod_restart(self):
        """
        This test tests DELETEs during pod restart
        """
        LOGGER.info("STARTED: Test to verify DELETEs during data pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users_org = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34078-org'
        self.s3_clean.update(users_org)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        event = threading.Event()  # Event to be used to send when data pod restart start
        LOGGER.info("Step 3: Perform WRITEs with variable object sizes for DELETEs")
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
        self.test_prefix_deg = 'test-34078'
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
                'bkt_list': get_random_buck, 'skipput': True, 'skipget': True, 'bkts_to_del':
                    del_bucket, 'output': del_output}
        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Successfully started continuous DELETEs in background on %s buckets",
                    del_bucket)
        LOGGER.info("Step 5: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 5: Successfully started the pod again and cluster is online")
        self.restore_pod = False
        event.clear()
        thread.join()
        LOGGER.info("Step 6: Verify status for In-flight DELETEs while pod was"
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
        LOGGER.info("Step 6: Verified status for In-flight DELETEs while pod was"
                    "restarting are successful & remaining buckets count is %s", len(buckets))
        LOGGER.info("Step 7: Verify read on the remaining %s buckets.", buckets)
        rd_output = Queue()
        new_s3data = {}
        for bkt in buckets:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix_deg, 'test_dir_path': self.test_dir_path,
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
        LOGGER.info("Step 7: Successfully verified READs & DI check for remaining buckets: %s",
                    buckets)
        LOGGER.info("Step 8: Check READ/Verify on data written in healthy mode and delete buckets")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: READ/Verify on data written in degraded mode was successful and "
                    "buckets deleted.")
        LOGGER.info("COMPLETED: Test to verify continuous DELETEs during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34075")
    def test_writes_during_pod_restart(self):
        """
        Verify WRITEs during data pod restart
        """
        LOGGER.info("STARTED: Test to verify Writes during data pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34075'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        LOGGER.info("Step 3: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Start WRITEs with variable object sizes in background")
        log_prefix = self.test_prefix
        if CMN_CFG["dtm0_disabled"]:
            self.test_prefix_deg = 'test-34075-deg'
            log_prefix = self.test_prefix_deg
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': log_prefix,
                'skipread': True, 'skipcleanup': True, 'nclients': 1, 'nsamples': 30,
                'setup_s3bench': False}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 3: Started WRITEs in degraded mode with variable sizes objects in "
                    "background.")
        LOGGER.info("Step 4: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 4: Successfully started the pod and cluster is online")
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
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 5: Successfully completed Writes in background")
        LOGGER.info("Step 6: Read/Verify data written in background process")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=log_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Read/Verify successfully on data written in background")
        LOGGER.info("Step 7: Run READ/Verify on data written in healthy cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Read/Verify successful on data written in healthy cluster")
        LOGGER.info("Step 8: Run IOs on cluster with restarted pod")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new ISM user and multiple buckets")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34075-restart'
            log_prefix = self.test_prefix
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=log_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: IOs completed successfully.")
        LOGGER.info("ENDED: Test to verify Writes during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34076")
    def test_read_write_during_pod_restart(self):
        """
        Verify READ/WRITEs during data pod restart
        """
        LOGGER.info("STARTED: Test to verify READ/WRITE during data pod restart.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        LOGGER.info("Create 2 set of buckets to be used for writes and reads")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        test_prefix_read = 'test-34076-read'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipcleanup=True,
                                                    nsamples=2, nclients=5, skipread=True)
        assert_utils.assert_true(resp[0], resp[1])
        test_prefix_write = 'test-34076-write'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_write, skipcleanup=True,
                                                    nsamples=2, nclients=5, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        event = threading.Event()  # Event to be used to send intimation of pod restart
        LOGGER.info("Step 3: Start READ/WRITEs/VERIFY with variable object sizes in background")
        if CMN_CFG["dtm0_disabled"]:
            test_prefix_write = 'test-34076-deg-write'
        LOGGER.info("Step 3.1: Start WRITEs with variable object sizes in background")
        output_wr = Queue()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 2, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False, 'event_set_clr': event_set_clr}
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
                'output': output_rd, 'setup_s3bench': False, 'event_set_clr': event_set_clr}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 3.2: Successfully started READs and verify on the written data in "
                    "background")
        LOGGER.info("Waiting for %s seconds", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 4: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 4: Successfully started the pod and cluster is online")
        self.restore_pod = False
        event.clear()
        thread_wri.join()
        thread_rd.join()
        LOGGER.info("Step 5.1: Verify status for In-flight WRITEs while %s data pod "
                    "restarted ", pod_name)
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"WRITEs logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"WRITEs logs which contain failures: {resp[1]}")
        LOGGER.info("Step 5.1: Verified status for In-flight WRITEs while %s data pod "
                    "restarted", pod_name)
        LOGGER.info("Step 5.2: Verify status for In-flight READs/Verify DI while %s"
                    " data pod restarted.", pod_name)
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"READs/VerifyDI logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"READs/VerifyDI logs which contain failures: {resp[1]}")
        LOGGER.info("Step 5.2: Verified status for In-flight READs/VerifyDI while %s "
                    " date pod restarted.", pod_name)
        LOGGER.info("Step 6: Run IOs on cluster with restarted pod")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user and multiple buckets")
            users_rst = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users_rst)
            self.test_prefix = 'test-34076-restart'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read,
                                                    skipcleanup=True, setup_s3bench=False,
                                                    nsamples=2, nclients=5)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_write,
                                                    skipcleanup=True, setup_s3bench=False,
                                                    nsamples=2, nclients=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs completed successfully.")
        LOGGER.info("ENDED: Test to verify READs/WRITE during data pod restart.")

    # pylint: disable=multiple-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Need method for particular pod down")
    @pytest.mark.tags("TEST-34088")
    def test_ios_rc_node_restart(self):
        """
        This test tests IOs before and after RC data pod restart
        """
        LOGGER.info("STARTED: Test to verify IOs before & after RC data pod restart")

        workload_info = dict()
        LOGGER.info("Step 1: Start IOs with variable object sizes")
        LOGGER.info("Create IAM user")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34088'
        workload_info[1] = [users, self.test_prefix]
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: IOs completed Successfully")

        LOGGER.info("Step 2: Get the RC node data pod and shutdown the same.")
        rc_node = self.ha_obj.get_rc_node(self.node_master_list[0])
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        self.node_name = list(rc_info.values())[0]
        LOGGER.info("RC Node is running on %s node", self.node_name)
        LOGGER.info("Get the data pod running on %s node", self.node_name)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        rc_datapod = None
        for pod_name, node in data_pods.items():
            if node == self.node_name:
                rc_datapod = pod_name
                break
        LOGGER.info("RC node %s has data pod: %s ", self.node_name, rc_datapod)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[rc_datapod])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True

        LOGGER.info("Step 3: READ-Verify data written in healthy cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully performed READ-Verify data written in healthy cluster")

        LOGGER.info("Step 4: Start IOs after pod shutdown by making replicas=0.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34088-deg'
            workload_info[2] = [users, self.test_prefix]
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Successfully IOs completed after pod shutdown by making replicas=0.")

        LOGGER.info("Step 5: Starting pod again by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 5: Successfully started the pod again by making replicas=1 and checked "
                    "cluster status")
        self.restore_pod = False

        LOGGER.info("Step 6: READ-Verify data written in healthy and degraded cluster")
        skipcleanup = not CMN_CFG["dtm0_disabled"]
        for value in workload_info.values():
            user = value[0]
            prefix = value[1]
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(user.values())[0],
                                                        log_prefix=prefix, setup_s3bench=False,
                                                        skipcleanup=skipcleanup, skipwrite=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully performed READ-Verify data written in healthy and "
                    "degraded cluster")

        LOGGER.info("Step 7: Start IOs again after data pod restart by making replicas=1.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-34088-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=skipcleanup, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully IOs completed after data pod restart by making "
                    "replicas=1.")
        LOGGER.info("COMPLETED: Test to verify IOs before & after RC data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34087")
    def test_ios_safe_shutdown_pod_restart(self):
        """
        This test tests IOs before and after data pod restart, pod shutdown with replica method
        """
        LOGGER.info("STARTED: Test to verify IOs before and after data pod restart (pod shutdown "
                    "by making replicas=0).")

        workload_info = dict()
        LOGGER.info("Step 1: Start IOs with variable object sizes")
        LOGGER.info("Create IAM user")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34087'
        workload_info[1] = [users, self.test_prefix]
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Successfully IOs completed with variable object sizes")

        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True

        LOGGER.info("Step 3: READ-Verify data written in healthy cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully performed READ-Verify data written in healthy cluster")

        LOGGER.info("Step 4: Start IOs after pod shutdown by making replicas=0.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34087-deg'
            workload_info[2] = [users, self.test_prefix]
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Successfully IOs completed after pod shutdown by making replicas=0.")

        LOGGER.info("Step 5: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 5: Successfully started the pod again and cluster is online")
        self.restore_pod = False

        LOGGER.info("Step 6: READ-Verify data written in healthy and degraded cluster")
        skipcleanup = not CMN_CFG["dtm0_disabled"]
        for value in workload_info.values():
            user = value[0]
            prefix = value[1]
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(user.values())[0],
                                                        log_prefix=prefix,
                                                        skipwrite=True, skipcleanup=skipcleanup,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully performed READ-Verify data written in healthy and "
                    "degraded cluster")

        LOGGER.info("Step 7: Start IOs again after data pod restart by making replicas=1.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-34087-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=skipcleanup, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully IOs completed after data pod restart by making "
                    "replicas=1.")
        LOGGER.info("COMPLETED: Test to verify IOs before and after data pod restart (pod shutdown "
                    "by making replicas=0).")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32456")
    def test_pod_shutdown_kubectl_delete(self):
        """
        Verify IOs before and after data pod failure; pod shutdown deleting pod
        using kubectl delete.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure, "
                    "pod shutdown by deleting pod using kubectl delete.")

        LOGGER.info("STEP 1: Create IAM user and perform WRITEs-READs-Verify with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32456'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod by kubectl delete.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to delete pod {pod_name} by kubectl delete")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by kubectl delete", pod_name)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=60)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in healthy state.")

        LOGGER.info("Step 4: READs-Verify-DELETE data written in healthy cluster")
        skipcleanup = not CMN_CFG["dtm0_disabled"]
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipwrite=True, skipcleanup=skipcleanup,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed READs-Verify-DELETE on data written in healthy cluster")

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 5: Create new user and perform WRITEs-READs-Verify-DELETEs with "
                        "variable object sizes.")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-32456-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    setup_s3bench=False, skipcleanup=skipcleanup)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Completed: Verify IOs before and after data pod failure, "
                    "pod shutdown by deleting pod using kubectl delete.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36003")
    def test_reads_after_pod_restart_ros(self):
        """
        This test tests READs after data pod restart (F-26A Read Only Scope)
        """
        LOGGER.info("STARTED: Test to verify READs after data pod restart.")
        LOGGER.info("Step 1: Perform WRITEs/READs/Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-36003'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Perform READs & Verify DI on written variable object sizes. "
                    "on degraded cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs & Verify DI on written variable object sizes. "
                    "on degraded cluster")
        LOGGER.info("Step 4: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 4: Successfully started the pod and cluster is online")
        self.restore_pod = False
        LOGGER.info("Step 5: Perform READs & verify DI on written variable object sizes. "
                    "after pod restart on online cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed READs & verified DI on written variable object sizes. "
                    "after pod restart on online cluster")
        LOGGER.info("Step 6: Perform WRITEs/READs/Verify with variable object sizes after pod "
                    "restarted.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users_rst = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_rst = 'test-36003-rst'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                        log_prefix=test_prefix_rst,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify READs after data pod restart.")

    # pylint: disable=multiple-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36004")
    def test_reads_during_pod_restart_ros(self):
        """
        This test tests continuous reads during pod restart (F-26A Read Only Scope)
        """
        LOGGER.info("STARTED: Test to verify continuous READs during data pod restart.")

        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart
        LOGGER.info("Step 1: Perform WRITEs/READs/Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-36004'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nclients=20, nsamples=20)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        LOGGER.info("Step 3: Perform READs and verify DI on the written data in background during "
                    "pod restart using %s method", self.restore_method)
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 2, 'nsamples': 20, 'skipwrite': True, 'skipcleanup': True,
                'output': output, 'setup_s3bench': False}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        # TODO Need to update timing once we get stability in degraded IOs performance
        time.sleep(HA_CFG["common_params"]["degraded_wait_delay"])
        LOGGER.info("Step 3: Successfully started READs and verify DI on the written data in "
                    "background")
        LOGGER.info("Step 4: Starting pod again and checking cluster status")
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
        LOGGER.info("Step 4: Successfully started the pod and cluster is online")
        self.restore_pod = False
        LOGGER.info("Step 5: Check read/verify running in background.")
        event.clear()
        thread.join()
        LOGGER.debug("Event is cleared and thread has joined.")
        LOGGER.info("Verifying responses from background process")
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not responses:
            assert_utils.assert_true(False, "Background S3bench Failures")
        LOGGER.debug("Background S3bench responses : %s", responses)
        if not responses["pass_res"]:
            assert_utils.assert_true(False,
                                     "No background IOs response while event was cleared")
        nonbkgrd_logs = list(x[1] for x in responses["pass_res"])
        if not responses["fail_res"]:
            assert_utils.assert_true(False,
                                     "No background IOs response while event was set")
        bkgrd_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=nonbkgrd_logs)
        assert_utils.assert_false(len(resp[1]), "Non Background Logs which contain failures"
                                                f": {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=bkgrd_logs)
        assert_utils.assert_false(len(resp[1]), "Background Logs which contain failures:"
                                                f" {resp[1]}")
        LOGGER.info("Step 5: Successfully completed READs and verified DI on the written data in "
                    "background during pod restart using %s method", self.restore_method)
        LOGGER.info("Step 6: Perform WRITEs/READs/Verify with variable object sizes after pod "
                    "restarted.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users_rst = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_rst = 'test-36003-rst'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                        log_prefix=test_prefix_rst,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify continuous READs during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45641")
    def test_obj_ver_suspension_data_pod_restart(self):
        """
        Verify bucket versioning suspension before and after data pod restart
        """
        LOGGER.info("STARTED: Test to verify bucket versioning suspension before & after "
                    "data pod restart.")
        event = threading.Event()
        LOGGER.info("Step 1: Create bucket and upload object %s of %s size. Enable versioning "
                    "on %s.", self.object_name, self.f_size, self.bucket_name)
        self.extra_files.append(self.multipart_obj_path)
        args = {'chk_null_version': True, 'is_unversioned': True, 'file_path':
            self.multipart_obj_path, 'enable_ver': True, 's3_ver': self.s3_ver}
        resp = self.ha_api.crt_bkt_put_obj_enbl_ver(event, self.s3_test_obj, self.bucket_name,
                                                    self.object_name, **args)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Created bucket and uploaded object %s of %s size. Enabled "
                    "versioning on %s.", self.object_name, self.f_size, self.bucket_name)
        self.version_etag.update({self.bucket_name: []})
        self.version_etag[self.bucket_name].extend(resp[1])
        self.version_etag.update({"obj_name": self.object_name})
        self.version_etag.update({"s3_ver": self.s3_ver})
        self.is_ver = True
        bucket_list = list()
        bucket_list.append(self.bucket_name)
        LOGGER.info("Step 2: Upload same object %s after enabling versioning. List & verify "
                    "the VersionID for the same for %s.", self.object_name, self.bucket_name)
        args = {'file_path': self.multipart_obj_path}
        resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, self.bucket_name,
                                               self.object_name, **args)
        assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
        self.version_etag[self.bucket_name].extend(resp[1])
        resp = self.ha_api.list_verify_version(self.s3_ver, self.bucket_name, self.version_etag[
            self.bucket_name])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Uploaded same object %s after enabling versioning. Listed & verified"
                    " the VersionID for the same for %s.", self.object_name, self.bucket_name)

        LOGGER.info("Step 3: Suspend versioning on %s.", self.bucket_name)
        resp = self.s3_ver.put_bucket_versioning(bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Suspended versioning on %s.", self.bucket_name)

        LOGGER.info("Step 4: Get versions of %s with & without specifying VersionID & verify etags "
                    "for %s.", self.object_name, self.bucket_name)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=self.bucket_name, obj_name=self.object_name,
                                               ver_etag=self.version_etag[self.bucket_name])
        assert_utils.assert_true(resp[0], f"Get Object with specifying versionID failed {resp[1]}")
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        latest_vetag = self.version_etag[self.bucket_name][-1]
        latest_v = list(latest_vetag.keys())[0]
        etag = list(latest_vetag.values())[0]
        if resp[1]["VersionId"] != latest_v:
            assert_utils.assert_true(False, "Get Object without specifying VersionID does not "
                                            f"match with latest {latest_v} {resp[1]}")
        if resp[1]["ETag"] != etag:
            assert_utils.assert_true(False, "Etag without specifying VersionID does not match with "
                                            f"etag {etag} {resp[1]}")
        LOGGER.info("Step 4: Got versions of %s with & without specifying VersionID & verified "
                    "etags for %s.", self.object_name, self.bucket_name)

        LOGGER.info("Step 5: Shutdown data pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=self.num_replica - 1)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete data pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 5: Successfully shutdown data pod %s. Verified cluster and services "
                    "states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 6: Get versions of %s with & without specifying VersionID & verify "
                    "etags for %s.", self.object_name, self.bucket_name)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=self.bucket_name, obj_name=self.object_name,
                                               ver_etag=self.version_etag[self.bucket_name])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        latest_vetag = self.version_etag[self.bucket_name][-1]
        latest_v = list(latest_vetag.keys())[0]
        etag = list(latest_vetag.values())[0]
        if resp[1]["VersionId"] != latest_v:
            assert_utils.assert_true(False, "Get Object without specifying VersionID does not "
                                            f"match with latest {latest_v} {resp[1]}")
        if resp[1]["ETag"] != etag:
            assert_utils.assert_true(False, "Etag without specifying VersionID does not match with "
                                            f"etag {etag} {resp[1]}")
        LOGGER.info("Step 6: Got versions of %s with & without specifying VersionID & verified "
                    "etags for %s", self.object_name, self.bucket_name)

        new_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
        download_path = os.path.join(self.test_dir_path, self.test_file + "_new")
        self.extra_files.append(download_path)
        LOGGER.info("Step 7: Create new bucket and upload object %s of %s size. Enable "
                    "versioning on %s.", self.object_name, self.f_size, new_bucket)
        args = {'chk_null_version': True, 'is_unversioned': True, 'file_path': download_path,
                'enable_ver': True, 's3_ver': self.s3_ver}
        resp = self.ha_api.crt_bkt_put_obj_enbl_ver(event, self.s3_test_obj, new_bucket,
                                                    self.object_name, **args)
        assert_utils.assert_true(resp[0], resp[1])
        self.version_etag.update({new_bucket: []})
        self.version_etag[new_bucket].extend(resp[1])
        bucket_list.append(new_bucket)
        LOGGER.info("Step 7: Created bucket and uploaded object %s of %s size. Enabled "
                    "versioning on %s.", self.object_name, self.f_size, new_bucket)

        LOGGER.info("Step 8: Upload same object %s after enabling versioning. List & verify "
                    "the VersionID for the same for %s.", self.object_name, new_bucket)
        args = {'file_path': download_path}
        resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, new_bucket,
                                               self.object_name, **args)
        assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
        self.version_etag[new_bucket].extend(resp[1])
        resp = self.ha_api.list_verify_version(self.s3_ver, new_bucket,
                                               self.version_etag[new_bucket])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Uploaded same object %s after enabling versioning. Listed & verified "
                    "the VersionID for the same for %s.", self.object_name, new_bucket)

        LOGGER.info("Step 9: Get versions of %s with & without specifying VersionID & verify "
                    "etags for %s.", self.object_name, new_bucket)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=new_bucket, obj_name=self.object_name,
                                               ver_etag=self.version_etag[new_bucket])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        resp = self.s3_test_obj.get_object(new_bucket, self.object_name)
        latest_vetag = self.version_etag[new_bucket][-1]
        latest_v = list(latest_vetag.keys())[0]
        etag = list(latest_vetag.values())[0]
        if resp[1]["VersionId"] != latest_v:
            assert_utils.assert_true(False, "Get Object without specifying VersionID does not "
                                            f"match with latest {latest_v} {resp[1]}")
        if resp[1]["ETag"] != etag:
            assert_utils.assert_true(False, "Etag without specifying VersionID does not match with "
                                            f"etag {etag} {resp[1]}")
        LOGGER.info("Step 9: Got versions of %s with & without specifying VersionID & verified "
                    "etags for %s", self.object_name, new_bucket)
        LOGGER.info("Step 10: Restart data pod with replica method and check cluster status")
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
        LOGGER.info("Step 10: Successfully restart data pod with replica method & checked "
                    "cluster status")
        LOGGER.info("Step 11: Get versions of %s with & without specifying VersionID & verify "
                    "etags for %s.", self.object_name, new_bucket)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=new_bucket, obj_name=self.object_name,
                                               ver_etag=self.version_etag[new_bucket])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        resp = self.s3_test_obj.get_object(new_bucket, self.object_name)
        latest_vetag = self.version_etag[new_bucket][-1]
        latest_v = list(latest_vetag.keys())[0]
        etag = list(latest_vetag.values())[0]
        if resp[1]["VersionId"] != latest_v:
            assert_utils.assert_true(False, "Get Object without specifying VersionID does not "
                                            f"match with latest {latest_v} {resp[1]}")
        if resp[1]["ETag"] != etag:
            assert_utils.assert_true(False, "Etag without specifying VersionID does not match with"
                                            f" etag {etag} {resp[1]}")
        LOGGER.info("Step 11: Got versions of %s with & without specifying VersionID & verified "
                    "etag for %s", self.object_name, new_bucket)
        LOGGER.info("Step 12: Suspend versioning on %s.", new_bucket)
        resp = self.s3_ver.put_bucket_versioning(bucket_name=new_bucket, status="Suspended")
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 12: Suspended versioning on %s.", new_bucket)
        LOGGER.info("Step 13: Upload same object %s after suspending versioning and verify its "
                    "null for %s.", self.object_name, new_bucket)
        args = {'file_path': download_path, 'chk_null_version': True, 'is_unversioned': True}
        resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, new_bucket,
                                               self.object_name, **args)
        assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
        self.version_etag[new_bucket].extend(resp[1])
        LOGGER.info("Step 13: Uploaded same object %s after suspending versioning and verified its "
                    "null for %s.", self.object_name, new_bucket)

        LOGGER.info("Step 14: Verify existing versions are remained intact")
        for bucket in bucket_list:
            resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                                   bkt_name=bucket, obj_name=self.object_name,
                                                   ver_etag=self.version_etag[bucket])
            assert_utils.assert_true(resp[0], f"Get object with versionID failed {resp[1]} for"
                                              f" {bucket}")
        LOGGER.info("Step 14: Verified existing versions are remained intact")
        LOGGER.info("COMPLETED: Test to verify bucket versioning suspension before & after data "
                    "pod restart.")
