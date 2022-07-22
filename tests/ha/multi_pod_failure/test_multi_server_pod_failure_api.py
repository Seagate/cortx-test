#!/usr/bin/python
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
HA test suite for Multiple Server Pods Failure
"""

import logging
import os
import secrets
import threading
import time
from multiprocessing import Queue
from time import perf_counter_ns
import pytest

from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestMultiServerPodFailureAPI:
    """
    Test suite for Multiple Server Pods Failure
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = []
        cls.password = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.pod_name_list = []
        cls.ha_obj = HAK8s()
        cls.s3_clean = cls.test_prefix = cls.random_time = cls.multipart_obj_path = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.deploy = cls.kvalue = None
        cls.pod_dict = dict()
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
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
        cls.rest_obj = S3AccountOperations()
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.deploy = False
        self.s3_clean = dict()
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        LOGGER.info("Get the value of K for the given cluster.")
        resp = self.ha_obj.get_config_value(self.node_master_list[0])
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            LOGGER.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        LOGGER.info("The cluster has %s parity pods", self.kvalue)
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{self.random_time}"
        self.object_name = f"ha-mp-obj-{self.random_time}"
        self.restore_pod = self.restore_method = self.deployment_name = None
        self.deployment_backup = None
        if not os.path.exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created IAM users and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if self.restore_pod:
            for pod_name in self.pod_name_list:
                if len(self.pod_dict.get(pod_name)) == 2:
                    deployment_name = self.pod_dict.get(pod_name)[1]
                    deployment_backup = None
                else:
                    deployment_name = self.pod_dict.get(pod_name)[2]
                    deployment_backup = self.pod_dict.get(pod_name)[1]
                resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                               restore_method=self.restore_method,
                                               restore_params={"deployment_name": deployment_name,
                                                               "deployment_backup":
                                                                   deployment_backup})
                LOGGER.debug("Response: %s", resp)
                assert_utils.assert_true(resp[0], "Failed to restore pod by "
                                                  f"{self.restore_method} way")
                LOGGER.info("Successfully restored pod %s by %s way",
                            pod_name, self.restore_method)
        if os.path.exists(self.test_dir_path):
            sysutils.remove_dirs(self.test_dir_path)
        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40581")
    def test_copy_object_kserver_pods_fail(self):
        """
        Test to Verify copy object when all K server pods are down - unsafe shutdown.
        """
        LOGGER.info("STARTED: Test to Verify copy object when all K server pods "
                    "down - unsafe shutdown.")
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{self.random_time}"] = \
                f"ha-obj{cnt}-{self.random_time}"
        event = threading.Event()
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 1: Create and list buckets and perform upload and copy "
                    "object from %s bucket to other buckets ", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Create Bucket copy "
                                          f"object failed with: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully created and listed buckets and performed upload and copy"
                    "object from %s bucket to other buckets", self.bucket_name)
        LOGGER.info("Step 2: Shutdown random %s (K) server pods by deleting deployment (unsafe)"
                    " and verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], down_method=const.RESTORE_DEPLOYMENT_K8S,
            kvalue=self.kvalue)
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])
            pod_data.append(resp[1][pod_name]['deployment_name'])
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown random %s (K) server pod %s. Verified cluster "
                    "and services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)
        LOGGER.info("Step 3: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 3: Successfully download the uploaded objects & verify etags")
        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 4: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        LOGGER.info("Step 4: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)
        LOGGER.info("Step 5: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 5: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)
        LOGGER.info("COMPLETED: Test to Verify copy object when all K server pods "
                    "down - unsafe shutdown.")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40582")
    def test_mpu_after_kserver_pods_fail(self):
        """
        This test tests multipart upload after all K server pods down - unsafe shutdown
        """
        LOGGER.info("STARTED: Test to verify multipart upload after all K server pods "
                    "down - unsafe shutdown.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        LOGGER.info("Step 1: Create bucket and perform multipart upload of size %sMB.",
                    file_size)
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
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
        LOGGER.debug("Uploaded object of size %s for %s", obj_size, self.bucket_name)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 1: Successfully performed multipart upload for size %sMB.",
                    file_size)
        LOGGER.info("Step 2: Shutdown random %s (K) server pods by deleting deployment (unsafe)"
                    " and verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], down_method=const.RESTORE_DEPLOYMENT_K8S,
            kvalue=self.kvalue)
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])
            pod_data.append(resp[1][pod_name]['deployment_name'])
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown random %s (K) server pod %s. Verified cluster "
                    "and services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)
        LOGGER.info("Step 3: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 3: Successfully downloaded the object and verified the checksum")
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        sysutils.remove_file(self.multipart_obj_path)
        sysutils.remove_file(download_path)
        LOGGER.info("Step 4: Create new bucket again and do multipart upload. "
                    "Download the object & verify checksum.")
        bucket_name = f"mp-bkt-{self.random_time}"
        object_name = f"mp-obj-{self.random_time}"
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
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum1 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum1, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum1},"
                                  f" {download_checksum1}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum1, download_checksum1)
        LOGGER.info("Step 4: Successfully created bucket and did multipart upload. "
                    "Downloaded the object & verified the checksum.")
        LOGGER.info("COMPLETED: Test to verify multipart upload after all K server pods "
                    "down - unsafe shutdown.")

    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40584")
    def test_part_mpu_till_kserver_pods_fail(self):
        """
        This test tests partial multipart upload after each server pod is failed till K
        pods and complete upload after all K server pods are down - unsafe shutdown
        """
        LOGGER.info("STARTED: Test to verify partial multipart upload after each server pod is "
                    "failed till K pods and complete upload after all K server pods "
                    "down - unsafe shutdown")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = self.kvalue * 5 + HA_CFG["5gb_mpu_data"]["total_parts"]
        parts = list(range(1, total_parts + 1))
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        sysutils.create_file(self.multipart_obj_path, file_size)
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
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
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        uploading_parts = self.system_random.sample(parts, 10)
        LOGGER.info("Step 1: Perform partial multipart upload for %s parts out of total %s",
                    uploading_parts, len(parts))
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=uploading_parts,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=self.multipart_obj_path)
        mpu_id = resp[1]
        object_path = resp[2]
        parts_etag1 = resp[3]
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        LOGGER.info("Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(uploading_parts, part_n["PartNumber"])
        LOGGER.info("Listed parts of partial multipart upload: %s", res[1])
        LOGGER.info("Step 1: Successfully performed partial multipart upload for %s parts out "
                    "of total %s", uploading_parts, len(parts))
        parts = [ele for ele in parts if ele not in uploading_parts]
        LOGGER.info("Step 2: Shutdown %s (K) server pods one by one, verify cluster, remaining "
                    "pods status and Start multipart upload for %s size object in %s parts with "
                    "every data server shutdown", self.kvalue, file_size * const.Sizes.MB,
                    total_parts)
        for count in range(1, self.kvalue+1):
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                pod_prefix=[const.SERVER_POD_NAME_PREFIX],
                down_method=const.RESTORE_DEPLOYMENT_K8S)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1])[0]
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])
            pod_data.append(resp[1][pod_name]['deployment_name'])
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.restore_pod = True
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("Deleted %s server pod %s by deleting deployment (unsafe)", count,
                        pod_name)
            uploading_parts = self.system_random.sample(parts, 10)
            LOGGER.info("Step 3: Perform partial multipart upload for %s parts out of total %s",
                        uploading_parts, len(parts))
            resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                        bucket_name=self.bucket_name,
                                                        object_name=self.object_name,
                                                        part_numbers=uploading_parts,
                                                        remaining_upload=True, mpu_id=mpu_id,
                                                        multipart_obj_size=file_size,
                                                        total_parts=total_parts,
                                                        multipart_obj_path=object_path)
            assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
            LOGGER.info("Listing parts of partial multipart upload")
            res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
            assert_utils.assert_true(res[0], res)
            for part_n in res[1]["Parts"]:
                assert_utils.assert_list_item(uploading_parts, part_n["PartNumber"])
            LOGGER.info("Listed parts of partial multipart upload: %s", res[1])
            parts_etag1.extend(resp[3])
            parts = [ele for ele in total_parts if ele not in uploading_parts]
            LOGGER.info("Step 3: Successfully performed partial multipart upload for %s parts out "
                        "of total %s", uploading_parts, len(parts))
        LOGGER.info("Step 2: Shutdown %s (K) server pods one by one successfully, verify cluster, "
                    "services states are as expected & remaining pods status is online and "
                    "performed multipart upload for %s size object in %s parts with every data "
                    "server shutdown pod shutdown", self.kvalue, file_size * const.Sizes.MB,
                    total_parts)
        LOGGER.info("Step 4: Upload remaining parts")
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=parts,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)
        assert_utils.assert_true(resp[0], f"Failed to upload remaining parts {resp[1]}")
        parts_etag2 = resp[3]
        etag_list = parts_etag1 + parts_etag2
        LOGGER.info("Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(parts, part_n["PartNumber"])
        LOGGER.info("Listed parts of partial multipart upload: %s", len(res[1]["Parts"]))
        LOGGER.info("Step 4: Successfully uploaded remaining parts")
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])
        LOGGER.info("Step 5: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 5: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))
        LOGGER.info("Step 6: Completing multipart upload & verified upload size is %s",
                    file_size * const.Sizes.MB)
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
        LOGGER.info("Step 6: Multipart upload completed & verified upload size is %s",
                    file_size * const.Sizes.MB)
        LOGGER.info("Step 7: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 7: Successfully downloaded the object and verified the checksum")
        LOGGER.info("Step 8: Perform WRITEs-READs-Verify-DELETEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40584-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0], nsamples=2,
                                                    log_prefix=self.test_prefix, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify partial multipart upload after each server pod is "
                    "failed till K pods and complete upload after all K server pods "
                    "down - unsafe shutdown")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40571")
    def test_chunk_upload_during_kserver_pods_fail(self):
        """
        Test chunk upload during k server pods going down using delete deployment (using jclient)
        """
        LOGGER.info("STARTED: Test chunk upload during k server pods going down by delete "
                    "deployment (using jclient)")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        download_file = "test_chunk_upload" + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        chunk_obj_path = os.path.join(self.test_dir_path, self.object_name)
        output = Queue()
        event = threading.Event()
        LOGGER.info("Step 1: Perform setup steps for jclient")
        jc_obj = JCloudClient()
        resp = self.ha_obj.setup_jclient(jc_obj)
        assert_utils.assert_true(resp, "Failed in setting up jclient")
        LOGGER.info("Step 1: Successfully setup jcloud/jclient on runner")
        LOGGER.info("Step 2: Create IAM user with name %s, bucket %s and start chunk upload in "
                    "background", self.s3acc_name, self.bucket_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'file_size': file_size, 'chunk_obj_path': chunk_obj_path, 'output': output}
        thread = threading.Thread(target=self.ha_obj.create_bucket_chunk_upload, kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started chuck upload in background")
        LOGGER.info("Waiting for %s seconds to start chunk upload",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 3: Shutdown random %s (K) server pods by deleting deployment (unsafe)"
                    " and verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], down_method=const.RESTORE_DEPLOYMENT_K8S,
            kvalue=self.kvalue, event=event)
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])
            pod_data.append(resp[1][pod_name]['deployment_name'])
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown random %s (K) server pod %s. Verified cluster "
                    "and services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)
        LOGGER.info("Step 4: Verifying response of background process")
        thread.join()
        while True:
            resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            if isinstance(resp, bool):
                break
        if resp is None:
            assert_utils.assert_true(False, "Background process of chunk upload failed")
        LOGGER.info("Step 4: Successfully verified response of background process")
        if not resp:
            LOGGER.info("Step 5: Chunk upload failed in between, trying chunk upload again")
            self.ha_obj.create_bucket_chunk_upload(s3_data=self.s3_clean,
                                                   bucket_name=self.bucket_name,
                                                   file_size=file_size,
                                                   chunk_obj_path=chunk_obj_path,
                                                   output=output,
                                                   bkt_op=False)
            while True:
                resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
                if isinstance(resp, bool):
                    break
            if not resp or resp is None:
                assert_utils.assert_true(False, "Retried chunk upload failed")
            LOGGER.info("Step 5: Retried chunk upload completed successfully")
        LOGGER.info("Calculating checksum of file %s", chunk_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[chunk_obj_path],
                                                           compare=False)[0]
        LOGGER.info("Step 6: Download object and verify checksum")
        resp = self.ha_obj.object_download_jclient(s3_data=self.s3_clean,
                                                   bucket_name=self.bucket_name,
                                                   object_name=self.object_name,
                                                   obj_download_path=download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Step 6: Successfully downloaded object and verified checksum")
        LOGGER.info("ENDED: Test chunk upload during k server pods going down by delete "
                    "deployment (unsafe)")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40585")
    def test_mpu_during_kserver_pods_fail(self):
        """
        This test tests multipart upload during server pods failure till K pods down - unsafe
        shutdown
        """
        LOGGER.info("STARTED: Test to verify multipart upload during server pods failure till K"
                    " pods by delete deployment")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = self.kvalue * 5 + HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts + 1))
        self.system_random.shuffle(part_numbers)
        output = Queue()
        parts_etag = list()
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        event = threading.Event()  # Event to be used to send intimation of server pod shutdown
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
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
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 1: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size,
                'total_parts': total_parts, 'multipart_obj_path': self.multipart_obj_path,
                'part_numbers': part_numbers, 'parts_etag': parts_etag, 'output': output}
        thread = threading.Thread(target=self.ha_obj.start_random_mpu, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Started multipart upload of 5GB object in background")
        LOGGER.info("Waiting for %s seconds for multipart upload to start in  background",
                    HA_CFG["common_params"]["60sec_delay"])
        time.sleep(HA_CFG["common_params"]["60sec_delay"])
        LOGGER.info("Step 2: Shutdown random %s (K) server pods one by one while continuous "
                    "multipart upload in background by deleting deployment (unsafe) and verify"
                    " cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], down_method=const.RESTORE_DEPLOYMENT_K8S,
            kvalue=self.kvalue, event=event)
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])
            pod_data.append(resp[1][pod_name]['deployment_name'])
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown random %s (K) server pod %s one by one while "
                    "continuous multipart upload in background. Verified cluster and services "
                    "states are as expected & remaining pods status is online.", self.kvalue,
                    self.pod_name_list)
        LOGGER.info("Step 3: Checking response from background multipart upload process")
        thread.join()
        responses = tuple()
        while len(responses) < 4:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not responses:
            assert_utils.assert_true(False, "Background process failed to do multipart upload")
        exp_failed_parts = responses[0]
        failed_parts = responses[1]
        parts_etag = responses[2]
        mpu_id = responses[3]
        LOGGER.debug("Responses received from background process:\nexp_failed_parts: "
                     "%s\nfailed_parts: %s\nparts_etag: %s\nmpu_id: %s", exp_failed_parts,
                     failed_parts, parts_etag, mpu_id)
        if len(exp_failed_parts) == 0 and len(failed_parts) == 0:
            LOGGER.info("All the parts are uploaded successfully")
        elif failed_parts:
            assert_utils.assert_true(False, "Failed to upload parts when some server pods are "
                                            f"down in cluster .Failed parts: {failed_parts}")
        elif exp_failed_parts:
            LOGGER.info("Step 3.1: Upload expected failed remaining parts")
            resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                        bucket_name=self.bucket_name,
                                                        object_name=self.object_name,
                                                        part_numbers=exp_failed_parts,
                                                        remaining_upload=True,
                                                        multipart_obj_size=file_size,
                                                        total_parts=total_parts,
                                                        multipart_obj_path=self.multipart_obj_path,
                                                        mpu_id=mpu_id)
            assert_utils.assert_true(resp[0],
                                     f"Failed to upload expected failed remaining parts {resp[1]}")
            parts_etag1 = resp[3]
            parts_etag = parts_etag + parts_etag1
            LOGGER.info("Step 3.1: Successfully uploaded expected failed remaining parts")
        LOGGER.info("Step 3: Successfully checked background process responses")
        parts_etag = sorted(parts_etag, key=lambda d: d['PartNumber'])
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]
        LOGGER.info("Step 4: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 4: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))
        LOGGER.info("Step 5: Completing multipart upload and check upload size is %s",
                    file_size * const.Sizes.MB)
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        LOGGER.info("Step 5: Multipart upload completed and verified upload object size is %s",
                    obj_size)
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
        LOGGER.info("COMPLETED: Test to verify multipart upload during server pods failure "
                    "till K pods by delete deployment")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40583")
    def test_copy_object_during_kserver_pods_fail(self):
        """
        Test to Verify copy object during server pods failure till K pods
        down - unsafe shutdown.
        """
        LOGGER.info("STARTED: Verify copy object during server pods failure "
                    "till K pods down - unsafe shutdown")
        bkt_obj_dict = dict()
        output = Queue()
        bkt_obj_dict[f"ha-bkt-{perf_counter_ns()}"] = f"ha-obj-{perf_counter_ns()}"
        event = threading.Event()
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 1: Create bucket, upload an object and copy to the bucket")
        # This is done just to get put_etag for further ops.
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp[1])
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully created bucket, uploaded and copied an object "
                    "to the bucket")
        bkt_obj_dict.clear()
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_multi"]
        for cnt in range(bkt_cnt):
            rd_time = perf_counter_ns()
            s3_test_obj.create_bucket(f"ha-bkt{cnt}-{rd_time}")
            bkt_obj_dict[f"ha-bkt{cnt}-{rd_time}"] = f"ha-obj{cnt}-{rd_time}"
        LOGGER.info("Step 2: Create multiple buckets and copy object from %s to other buckets in "
                    "background", self.bucket_name)
        args = {'s3_test_obj': s3_test_obj, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': False,
                'put_etag': put_etag}
        thread = threading.Thread(target=self.ha_obj.create_bucket_copy_obj, args=(event,),
                                  kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started background process for copy object")
        # While loop to sync this operation with background thread to achieve expected scenario
        LOGGER.info("Waiting for creation of %s buckets", bkt_cnt)
        bkt_list = list()
        timeout = time.time() + HA_CFG["common_params"]["bucket_creation_delay"]
        while len(bkt_list) < bkt_cnt:
            time.sleep(HA_CFG["common_params"]["20sec_delay"])
            bkt_list = s3_test_obj.bucket_list()[1]
            if timeout < time.time():
                LOGGER.error("Bucket creation is taking longer than 3 mins")
                assert_utils.assert_true(False, "Please check background process logs")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        LOGGER.info("Step 3: Shutdown random %s (K) server pods by deleting deployment (unsafe)"
                    " and verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            pod_prefix=[const.SERVER_POD_NAME_PREFIX], down_method=const.RESTORE_DEPLOYMENT_K8S,
            kvalue=self.kvalue, event=event)
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])
            pod_data.append(resp[1][pod_name]['deployment_name'])
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown random %s (K) server pod %s. Verified cluster "
                    "and services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)
        LOGGER.info("Step 4: Checking responses from background process")
        thread.join()
        responses = tuple()
        while len(responses) < 3:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not responses:
            assert_utils.assert_true(False, "Background process failed to do copy object")
        put_etag = responses[0]
        exp_fail_bkt_obj_dict = responses[1]
        failed_bkts = responses[2]
        LOGGER.debug("Responses received from background process:\nput_etag: "
                     "%s\nexp_fail_bkt_obj_dict: %s\nfailed_bkts: %s", put_etag,
                     exp_fail_bkt_obj_dict, failed_bkts)
        if len(exp_fail_bkt_obj_dict) == 0 and len(failed_bkts) == 0:
            LOGGER.info("Copy object operation for all the buckets completed successfully. ")
        elif failed_bkts:
            assert_utils.assert_true(False, "Failed to do copy object when cluster has "
                                            f"some failures.Failed buckets: {failed_bkts}")
        elif exp_fail_bkt_obj_dict:
            LOGGER.info("Step 4.1: Retrying copy object to buckets %s",
                        list(exp_fail_bkt_obj_dict.keys()))
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=exp_fail_bkt_obj_dict,
                                                      bkt_op=False, put_etag=put_etag)
            assert_utils.assert_true(resp[0], f"copy object failed buckets are: {resp[1]}")
            put_etag = resp[1]
        LOGGER.info("Step 4: Checked responses from background process")
        LOGGER.info("Step 5: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 5: Successfully download the uploaded objects & verify etags")
        bucketnew = f"ha-bkt-new-{int((perf_counter_ns()))}"
        objectnew = f"ha-obj-new-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucketnew] = objectnew
        LOGGER.info("Step 6: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucketnew)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], f"Already created/uploaded copy "
                                          f"object failed buckets are: {resp[1]}")
        LOGGER.info("Step 6: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucketnew)
        LOGGER.info("Step 7: Download the uploaded %s on %s & "
                    "verify etags.", objectnew, bucketnew)
        resp = s3_test_obj.get_object(bucket=bucketnew, key=objectnew)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG "
                                                      f"for object {objectnew} of bucket "
                                                      f"{bucketnew}.")
        LOGGER.info("Step 7: Downloaded the uploaded %s on %s & verified etags.", objectnew,
                    bucketnew)
        LOGGER.info("COMPLETED: Verify copy object during server pods failure till K pods down - "
                    "unsafe shutdown")
