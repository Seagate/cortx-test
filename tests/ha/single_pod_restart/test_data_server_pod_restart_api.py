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
HA test suite for Data and server pod restart
"""

import logging
import os
import re
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
from libs.ha.ha_common_api_libs_k8s import HAK8sApiLibs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods
class TestDataServerPodRestartAPI:
    """
    Test suite for Data and server pod restart
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
        cls.ha_api = HAK8sApiLibs()
        cls.random_time = cls.s3_clean = cls.test_prefix = cls.s3_test_obj = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.system_random = secrets.SystemRandom()
        cls.mgnt_ops = ManagementOPs()

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
        cls.test_file = "ha_mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.s3_clean = dict()
        self.restore_pod = self.restore_method = self.deployment_name = self.set_name = None
        self.deployment_backup = None
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.extra_files = list()
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        convert = lambda text: int(text) if text.isdigit() else text
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        LOGGER.info("Get %s and %s pods to be deleted", const.POD_NAME_PREFIX,
                    const.SERVER_POD_NAME_PREFIX)
        self.pod_dict = dict()
        for prefix in [const.POD_NAME_PREFIX, const.SERVER_POD_NAME_PREFIX]:
            self.pod_list = list()
            sts_dict = self.node_master_list[0].get_sts_pods(pod_prefix=prefix)
            sts_list = list(sts_dict.keys())
            LOGGER.debug("%s Statefulset: %s", prefix, sts_list)
            sts = self.system_random.sample(sts_list, 1)[0]
            sts_dict_val = sorted(sts_dict.get(sts), key=alphanum_key)
            self.delete_pod = sts_dict_val[-1]
            LOGGER.info("Pod to be deleted is %s", self.delete_pod)
            self.set_type, self.set_name = self.node_master_list[0].get_set_type_name(
                pod_name=self.delete_pod)
            self.pod_list.append(self.delete_pod)
            self.pod_list.append(self.set_name)
            resp = self.node_master_list[0].get_num_replicas(self.set_type, self.set_name)
            assert_utils.assert_true(resp[0], resp)
            self.num_replica = int((resp[1]))
            self.pod_list.append(self.num_replica)
            self.pod_dict[prefix] = self.pod_list
        LOGGER.info("Create IAM user")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        self.s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                     endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("COMPLETED: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            for pod_prefix in self.pod_dict:
                self.restore_method = self.pod_dict.get(pod_prefix)[-1]
                resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                               restore_method=self.restore_method,
                                               restore_params={
                                                   "deployment_name":
                                                       self.pod_dict.get(pod_prefix)[-2],
                                                   "deployment_backup": self.deployment_backup,
                                                   "num_replica": self.pod_dict.get(pod_prefix)[2],
                                                   "set_name": self.pod_dict.get(pod_prefix)[1]})
                LOGGER.debug("Response: %s", resp)
                assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method}"
                                                  " way")
                LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Removing extra files")
        for file in self.extra_files:
            if os.path.exists(file):
                system_utils.remove_file(file)
        LOGGER.info("Removing all files from %s", self.test_dir_path)
        system_utils.cleanup_dir(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45534")
    def test_chunk_upload_during_data_server_pod_restart(self):
        """
        Verify chunk upload during 1 data pod and 1 server pod restart (using jclient)
        """
        LOGGER.info("STARTED: Verify chunk upload during 1 data pod and 1 server pod restart")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        download_path = os.path.join(self.test_dir_path, "test_chunk_upload" + "_download")
        chunk_obj_path = os.path.join(self.test_dir_path, self.object_name)
        upload_op = Queue()
        workload_info = dict()
        t_t = int(perf_counter_ns())
        bucket_name = f"chunk-upload-bkt-{t_t}"
        object_name = f"chunk-upload-obj-{t_t}"
        LOGGER.info("Step 1: Perform setup steps for jclient")
        jc_obj = JCloudClient()
        resp = self.ha_obj.setup_jclient(jc_obj)
        assert_utils.assert_true(resp, "Failed in setting up jclient")
        LOGGER.info("Step 1: Successfully setup jclient on runner")
        LOGGER.info("Step 2: Create IAM user with name %s, bucket %s and perform chunk upload",
                    self.s3acc_name, self.bucket_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = f'test-45534-{int(perf_counter_ns())}'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.create_bucket_chunk_upload(s3_data=self.s3_clean,
                                                      bucket_name=self.bucket_name,
                                                      file_size=file_size,
                                                      chunk_obj_path=chunk_obj_path,
                                                      background=False)
        self.extra_files.append(chunk_obj_path)
        assert_utils.assert_true(resp, "Failure observed in chunk upload in healthy cluster")
        LOGGER.info("Step 2: Successfully performed chunk upload")
        workload_info[1] = [self.bucket_name, self.object_name]
        LOGGER.info("Calculating checksum of uploaded file %s", chunk_obj_path)
        upld_chksm_hlt = self.ha_obj.cal_compare_checksum(file_list=[chunk_obj_path],
                                                          compare=False)[0]
        LOGGER.info("Step 3: Shutdown one data and one server pod with replica method and verify"
                    " cluster & remaining pods status")
        for pod_prefix in self.pod_dict:
            num_replica = self.pod_dict[pod_prefix][-1] - 1
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                pod_prefix=[pod_prefix], delete_pod=[self.pod_dict.get(pod_prefix)[0]],
                num_replica=num_replica)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1].keys())[0]
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['deployment_name'])
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['method'])
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("successfully shutdown pod %s", self.pod_dict.get(pod_prefix)[0])
            self.restore_pod = True
        LOGGER.info("Step 3: Successfully shutdown one data and one server pod. Verified cluster "
                    "and services states are as expected & remaining pods status is online")
        LOGGER.info("Step 4: Download object which was uploaded in healthy cluster and verify "
                    "checksum")
        resp = self.ha_obj.object_download_jclient(s3_data=self.s3_clean,
                                                   bucket_name=self.bucket_name,
                                                   object_name=self.object_name,
                                                   obj_download_path=download_path)
        LOGGER.info("Download object response: %s", resp)
        self.extra_files.append(download_path)
        assert_utils.assert_true(resp[0], resp[1])
        dnld_chksm = self.ha_obj.cal_compare_checksum(file_list=[download_path], compare=False)[0]
        assert_utils.assert_equal(upld_chksm_hlt, dnld_chksm,
                                  f"Expected checksum: {upld_chksm_hlt},"
                                  f"Actual checksum: {dnld_chksm}")
        LOGGER.info("Step 4: Successfully downloaded object which was uploaded in healthy cluster "
                    "and verified checksum")
        LOGGER.info("Step 5: Start chunk upload in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': bucket_name,
                'file_size': file_size, 'chunk_obj_path': chunk_obj_path, 'output': upload_op}
        thread = threading.Thread(target=self.ha_obj.create_bucket_chunk_upload, kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Waiting for %s sec...", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 5: Successfully started chunk upload in background")
        LOGGER.info("Step 6: Restore data, server pod and check cluster status.")
        for pod_prefix in self.pod_dict:
            self.restore_method = self.pod_dict.get(pod_prefix)[-1]
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={
                                               "deployment_name": self.pod_dict.get(pod_prefix)[-2],
                                               "deployment_backup": self.deployment_backup,
                                               "num_replica": self.pod_dict.get(pod_prefix)[2],
                                               "set_name": self.pod_dict.get(pod_prefix)[1]},
                                           clstr_status=True)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Step 6: Successfully started data, server pod and cluster is online.")
        self.restore_pod = False
        LOGGER.info("Step 7: Verifying response of background chunk upload process")
        self.extra_files.append(chunk_obj_path)
        while True:
            resp = upload_op.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            if isinstance(resp, bool):
                break
        if resp is None:
            assert_utils.assert_true(False, "Background process of chunk upload failed")
        assert_utils.assert_true(resp, "Failure observed in chunk upload during server pod restart")
        LOGGER.info("Step 7: Successfully performed chunk upload during server pod restart")
        LOGGER.info("Step 8: Download object which was uploaded in healthy cluster and in "
                    "background, verify checksum")
        LOGGER.info("Calculating checksum of uploaded file %s", chunk_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[chunk_obj_path],
                                                           compare=False)[0]
        bkt_obj_dict = {self.bucket_name: [self.object_name, upld_chksm_hlt],
                        bucket_name: [object_name, upload_checksum]}
        for bkt_obj in bkt_obj_dict:
            resp = self.ha_obj.object_download_jclient(s3_data=self.s3_clean,
                                                       bucket_name=bkt_obj,
                                                       object_name=bkt_obj_dict[bkt_obj][0],
                                                       obj_download_path=download_path)
            LOGGER.info("Download object response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            dnld_chksm = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                          compare=False)[0]
            assert_utils.assert_equal(bkt_obj_dict[bkt_obj][-1], dnld_chksm,
                                      f"Expected checksum: {upld_chksm_hlt},"
                                      f"Actual checksum: {dnld_chksm}")
        LOGGER.info("Step 8: Successfully downloaded object and verified checksum")
        LOGGER.info("COMPLETED: Verify chunk upload during 1 data pod and 1 server pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45533")
    def test_obj_overwrite_during_data_server_pod_restart(self):
        """
        Verify object overwrite during single data pod and server pod restart
        """
        LOGGER.info("STARTED: Verify object overwrite during single data pod and server pod "
                    "restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        output = Queue()
        event = threading.Event()
        LOGGER.info("Step 1: Create bucket %s and perform upload of object size %s MB and "
                    "Overwrite the object", self.bucket_name, file_size)
        s3_data = {self.bucket_name: [self.object_name, file_size]}
        resp = self.ha_api.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        upld_chcksm = list(resp[1].values())[0][0]
        for checksum in resp[1].values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum doesn't match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 1: %s bucket created, uploaded for object size %s MB and Overwrite of"
                    " object done successfully ", self.bucket_name, file_size)
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_multi"]
        new_s3_data = dict()
        LOGGER.info("Create %s buckets and upload objects for background overwrite during "
                    "pod restart.", bkt_cnt)
        t_t = int(perf_counter_ns())
        for cnt in range(bkt_cnt):
            new_s3_data.update({f"ha-bkt{cnt}-{t_t}": [f"ha-obj{cnt}-{t_t}", file_size]})
        resp = self.ha_api.object_overwrite_dnld(self.s3_test_obj, new_s3_data, iteration=0,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in create new bucket, "
                                          "upload object.")
        LOGGER.info("Step 2: Shutdown one data and one server pod with replica method and verify"
                    " cluster & remaining pods status")
        for pod_prefix in self.pod_dict:
            num_replica = self.pod_dict[pod_prefix][-1] - 1
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                pod_prefix=[pod_prefix], delete_pod=[self.pod_dict.get(pod_prefix)[0]],
                num_replica=num_replica)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1].keys())[0]
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['deployment_name'])
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['method'])
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("successfully shutdown pod %s", self.pod_dict.get(pod_prefix)[0])
            self.restore_pod = True
        LOGGER.info("Step 2: Successfully shutdown one data and one server pod. Verified cluster "
                    "and services states are as expected & remaining pods status is online")
        LOGGER.info("Step 3: Read-Verify already overwritten object in healthy cluster")
        download_path = os.path.join(self.test_dir_path, f"{self.object_name}_download.txt")
        resp = self.s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        assert_utils.assert_true(resp[0], f"Object download failed. Response: {resp[1]}")
        dnld_checksum = self.ha_obj.cal_compare_checksum([download_path], compare=False)[0]
        system_utils.remove_file(file_path=download_path)
        assert_utils.assert_equal(upld_chcksm, dnld_checksum,
                                  "Upload & download checksums doesn't match. Expected: "
                                  f"{upld_chcksm} Actual: {dnld_checksum}")
        LOGGER.info("Step 3: Successfully Read-Verify already overwritten object in healthy "
                    "cluster")
        LOGGER.info("Step 4: Start overwrite operation on buckets created in healthy cluster")
        args = {"s3_test_obj": self.s3_test_obj, "s3_data": new_s3_data, "iteration": 1,
                "random_size": True, "queue": output, "background": True, "event": event}
        thread = threading.Thread(target=self.ha_api.object_overwrite_dnld, kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Started overwrite object in background")
        LOGGER.info("Waiting for %s sec...", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 5: Restore data, server pod and check cluster status.")
        event.set()
        for pod_prefix in self.pod_dict:
            self.restore_method = self.pod_dict.get(pod_prefix)[-1]
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={
                                               "deployment_name": self.pod_dict.get(pod_prefix)[-2],
                                               "deployment_backup": self.deployment_backup,
                                               "num_replica": self.pod_dict.get(pod_prefix)[2],
                                               "set_name": self.pod_dict.get(pod_prefix)[1]},
                                           clstr_status=True)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Step 5: Successfully started data, server pod and cluster is online.")
        self.restore_pod = False
        event.clear()
        thread.join()
        LOGGER.info("Step 6: Verify responses from background process")
        responses = tuple()
        while len(responses) < 3:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not responses:
            assert_utils.assert_true(False, "Failure in background process")
        checksums = responses[1]
        exp_fail_count = responses[2]
        assert_utils.assert_true(responses[0],
                                 "Failures observed in overwrite or download background process")
        assert_utils.assert_false(exp_fail_count, "Failures observed in overwrite or download "
                                                  "in background process while event was set")
        for checksum in checksums.values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum does not match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 6: Successfully verified responses from background process")
        LOGGER.info("Step 7: Read-Verify already overwritten object in healthy cluster")
        download_path = os.path.join(self.test_dir_path, f"{self.object_name}_download.txt")
        resp = self.s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        assert_utils.assert_true(resp[0], f"Object download failed. Response: {resp[1]}")
        dnld_checksum = self.ha_obj.cal_compare_checksum([download_path], compare=False)[0]
        system_utils.remove_file(file_path=download_path)
        assert_utils.assert_equal(upld_chcksm, dnld_checksum, "Upload & download checksums don't "
                                                              f"match. Expected: {upld_chcksm} "
                                                              f"Actual: {dnld_checksum}")
        LOGGER.info("Step 7: Successfully Read-Verify already overwritten object in healthy "
                    "cluster")
        LOGGER.info("Step 8: Overwrite existing object of bucket %s", self.bucket_name)
        resp = self.ha_api.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=True)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        for checksum in resp[1].values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum doesn't match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 8: Successfully overwritten existing object of bucket %s",
                    self.bucket_name)
        LOGGER.info("COMPLETED: Verify object overwrite during single data pod and server pod "
                    "restart")
