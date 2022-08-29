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
HA test suite for single data Pod restart for API tests
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
from libs.ha.ha_common_api_libs_k8s import HAK8sApiLibs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-lines
class TestDataPodRestartAPI:
    """
    Test suite for single Data Pod Restart for API tests
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.setup_type = CMN_CFG["setup_type"]
        cls.username = list()
        cls.password = list()
        cls.node_master_list = list()
        cls.hlth_master_list = list()
        cls.node_worker_list = list()
        cls.ha_obj = HAK8s()
        cls.ha_api = HAK8sApiLibs()
        cls.s3_clean = cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.multipart_obj_path = cls.set_name = cls.version_etag = cls.extra_files = None
        cls.delete_pod = cls.set_type = cls.num_replica = cls.s3_test_obj = cls.s3_ver = None
        cls.f_size = None
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
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restore_pod = False
        self.s3_clean = dict()
        self.version_etag = dict()
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.extra_files = list()
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
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
    @pytest.mark.tags("TEST-34080")
    def test_mpu_after_pod_restart(self):
        """
        This test tests multipart upload after data pod restart.
        """
        LOGGER.info("STARTED: Test to verify multipart upload after data pod restart.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_path_1 = os.path.join(self.test_dir_path, self.test_file + "_download_1")
        download_path_2 = os.path.join(self.test_dir_path, self.test_file + "_download_2")
        download_path = os.path.join(self.test_dir_path, self.test_file + "_download")
        LOGGER.info("Step 1: Create and list buckets. Perform multipart upload for size %s MB in "
                    "total %s parts.", file_size, total_parts)
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
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
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum_1 = str(resp[2])
        LOGGER.info("Step 1: Successfully performed multipart upload for size %s MB in total %s "
                    "parts.", file_size, total_parts)
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.delete_pod)
        self.restore_pod = True
        LOGGER.info("Step 3: Download the uploaded object %s in healthy cluster & verify checksum",
                    self.object_name)
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, self.bucket_name, self.object_name,
                                                  download_path_1, upload_checksum_1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully downloaded the object %s & verified the checksum",
                    self.object_name)
        object_name_1 = f"ha-mp-obj-{int(perf_counter_ns())}"
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create and list buckets")
            bucket_name_1 = f"ha-mp-bkt-{int(perf_counter_ns())}"
        else:
            bucket_name_1 = self.bucket_name
        LOGGER.info("Step 4: Perform multipart upload for size %s MB in total %s parts.",
                    file_size, total_parts)
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name_1,
                                                         object_name=object_name_1,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(bucket_name_1, object_name_1)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", bucket_name_1, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum_2 = str(resp[2])
        LOGGER.info("Step 4: Successfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)
        LOGGER.info("Step 5: Start pod again and check cluster status")
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
        LOGGER.info("Step 5: Successfully started pod again and cluster is online")

        LOGGER.info("Step 6.1: Download the uploaded object %s in healthy cluster & verify "
                    "checksum", self.object_name)
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, self.bucket_name, self.object_name,
                                                  download_path_1, upload_checksum_1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6.1: Successfully downloaded the object %s & verified the checksum",
                    self.object_name)

        LOGGER.info("Step 6.2: Download the uploaded object %s in degraded cluster & verify "
                    "checksum", object_name_1)
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, bucket_name_1, object_name_1,
                                                  download_path_2, upload_checksum_2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6.2: Successfully downloaded the object %s & verified the checksum",
                    object_name_1)
        LOGGER.info("Step 7: Perform multipart upload for size %s MB in total %s parts.",
                    file_size, total_parts)
        test_object = f"ha-mp-obj-{int(perf_counter_ns())}"
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create and list buckets")
            test_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
        else:
            test_bucket = self.bucket_name
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
        LOGGER.info("Step 7: Successfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)
        LOGGER.info("Step 8: Download the uploaded object %s & verify checksum", test_object)
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, test_bucket, test_object,
                                                  download_path, upload_checksum)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully downloaded the object %s & verified the checksum",
                    test_object)
        self.extra_files.extend((self.multipart_obj_path, download_path, download_path_1,
                                 download_path_2))
        LOGGER.info("COMPLETED: Test to verify multipart upload after data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34082")
    def test_partial_mpu_after_pod_restart(self):
        """
        This test tests partial multipart upload after data pod restart
        """
        LOGGER.info("STARTED: Test to verify partial multipart upload after data pod restart.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = self.system_random.sample(list(range(1, total_parts + 1)), total_parts // 4)
        download_path = os.path.join(self.test_dir_path, self.test_file + "_download")
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        system_utils.create_file(self.multipart_obj_path, file_size)
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]
        LOGGER.info("Step 1: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially for %s part out of %s", part_numbers, total_parts)
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
        LOGGER.info("Step 1: Successfully completed partial multipart upload for %s part out of "
                    "%s", part_numbers, total_parts)
        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])
        LOGGER.info("Step 3: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.delete_pod)
        self.restore_pod = True
        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts + 1))))
        parts_half = self.system_random.sample(remaining_parts, total_parts // 2)
        part_numbers.extend(parts_half)
        LOGGER.info("Step 4: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially for %s part out of %s", parts_half, total_parts)
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=parts_half,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)
        object_path = resp[2]
        parts_etag2 = resp[3]
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        LOGGER.info("Step 4: Successfully completed partial multipart upload for %s part out of "
                    "%s", parts_half, total_parts)
        LOGGER.info("Step 5: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 5: Listed parts of partial multipart upload: %s", res[1])
        LOGGER.info("Step 6: Start pod again and check cluster status")
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
        LOGGER.info("Step 6: Successfully started pod again and cluster is online")
        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts + 1))))
        LOGGER.info("Step 7: Upload remaining %s parts out of %s", remaining_parts, total_parts)
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=remaining_parts,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)
        assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
        parts_etag3 = resp[3]
        LOGGER.info("Step 7: Successfully uploaded remaining %s parts out of %s",
                    remaining_parts, total_parts)
        etag_list = parts_etag1 + parts_etag2 + parts_etag3
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])
        LOGGER.info("Step 8: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 8: Listed parts of multipart upload, Count: %s", len(res[1]["Parts"]))
        LOGGER.info("Step 9: Completing multipart upload & check upload size is %s", file_size *
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
        LOGGER.info("Step 9: Multipart upload completed and verified upload size is %s",
                    file_size * const.Sizes.MB)
        LOGGER.info("Step 10: Download the uploaded object and verify checksum")
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, self.bucket_name, self.object_name,
                                                  download_path, upload_checksum)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Successfully downloaded the object and verified the checksum")
        self.extra_files.extend((self.multipart_obj_path, download_path))
        LOGGER.info("COMPLETED: Test to verify partial multipart upload after data pod restart.")

    # pylint: disable=too-many-branches
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34083")
    def test_copy_obj_after_pod_restart(self):
        """
        This test tests copy object after data pod restart
        """
        LOGGER.info("STARTED: Test to verify copy object after data pod restart.")
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        t_t = int(perf_counter_ns())
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{t_t}"] = f"ha-obj{cnt}-{t_t}"
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
        LOGGER.info("Step 1: Create and list buckets. Upload object to %s & copy object from the"
                    " same bucket to other buckets and verify copy object etags", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully created multiple buckets and uploaded object to %s "
                    "and copied to other buckets and verified copy object etags", self.bucket_name)
        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.delete_pod)
        self.restore_pod = True
        LOGGER.info("Step 3: Download the copied objects & verify etags.")
        for bkt, obj in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=bkt, key=obj)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get "
                                                          f"Etag for object {obj} of bucket "
                                                          f"{bkt}.")
        LOGGER.info("Step 3: Downloaded copied objects & verify etags.")
        bkt_obj_dict1 = bkt_obj_dict.copy()
        t_t = int(perf_counter_ns())
        bucket_name = self.bucket_name
        bkt_op = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create and list buckets")
            bkt_obj_dict.clear()
            for cnt in range(bkt_cnt):
                bkt_obj_dict[f"ha-bkt{cnt}-{t_t}"] = f"ha-obj{cnt}-{t_t}"
            bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}-1"
            bkt_op = True
        else:
            for idx, bkt in enumerate(bkt_obj_dict):
                bkt_obj_dict[bkt] = f"ha-obj{idx}-{t_t}"
        LOGGER.info("Step 4: Copy object from the %s bucket to other buckets and verify copy object"
                    " etags", bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path, bkt_op=bkt_op)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 4: Successfully created multiple buckets and copied object from the %s "
                    "bucket to other buckets and verified copy object etags", self.bucket_name)
        LOGGER.info("Step 5: Start pod again and check cluster status")
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
        LOGGER.info("Step 5: Successfully started pod again and cluster is online")
        LOGGER.info("Step 6: Download the copied objects & verify etags.")
        for bkt, obj in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=bkt, key=obj)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get "
                                                          f"Etag for object {obj} of bucket "
                                                          f"{bkt}.")
        for bkt, obj in bkt_obj_dict1.items():
            resp = s3_test_obj.get_object(bucket=bkt, key=obj)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get "
                                                          f"Etag for object {obj} of bucket "
                                                          f"{bkt}.")
        LOGGER.info("Step 6: Downloaded copied objects & verify etags.")

        t_t = int(perf_counter_ns())
        bucket_name = self.bucket_name
        bkt_op = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create and list buckets")
            bkt_obj_dict.clear()
            for cnt in range(bkt_cnt):
                bkt_obj_dict[f"ha-bkt{cnt}-{t_t}"] = f"ha-obj{cnt}-{t_t}"
            bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}-2"
            bkt_op = True
        else:
            for idx, bkt in enumerate(bkt_obj_dict):
                bkt_obj_dict[bkt] = f"ha-obj{idx}-{t_t}"
        LOGGER.info("Step 7: Perform copy object from already created/uploaded %s bucket to other "
                    "buckets verify copy object etags", bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict, put_etag=put_etag,
                                                  bkt_op=bkt_op)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        LOGGER.info("Step 7: Performed copy object from already created/uploaded %s bucket to other"
                    " buckets verified copy object etags", self.bucket_name)
        LOGGER.info("Step 8: Download the copied objects & verify etags.")
        for bkt, obj in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=bkt, key=obj)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get "
                                                          f"Etag for object {obj} of bucket "
                                                          f"{bkt}.")
        LOGGER.info("Step 8: Downloaded copied objects & verify etags.")
        LOGGER.info("COMPLETED: Test to verify copy object after data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34081")
    def test_mpu_during_pod_restart(self):
        """
        This test tests multipart upload during data pod restart
        """
        LOGGER.info("STARTED: Test to verify multipart upload during data pod restart")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts + 1))
        self.system_random.shuffle(part_numbers)
        output = Queue()
        parts_etag = list()
        download_path = os.path.join(self.test_dir_path, self.test_file + "_download")
        download_path1 = os.path.join(self.test_dir_path, self.test_file + "_download1")
        download_path2 = os.path.join(self.test_dir_path, self.test_file + "_download2")
        event = threading.Event()  # Event to be used to send intimation of pod restart

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
        LOGGER.info("Successfully created IAM user")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 1: Perform multipart upload for size %s MB in total %s parts.",
                    file_size, total_parts)
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
        upload_checksum1 = str(resp[2])
        LOGGER.info("Step 1: Successfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)

        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.delete_pod)
        self.restore_pod = True

        LOGGER.info("Step 3: Download the uploaded object in healthy cluster and verify checksum")
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, self.bucket_name,
                                                  self.object_name, download_path, upload_checksum1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully downloaded the object and verified the checksum")

        object_name_1 = f"ha-mp-obj-{int(perf_counter_ns())}"
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new bucket")
            bucket_name_1 = f"ha-mp-bkt-{int(perf_counter_ns())}"
        else:
            bucket_name_1 = self.bucket_name

        LOGGER.info("Step 4: Start multipart upload of %s MB object in background", file_size)
        args = {'s3_data': self.s3_clean, 'bucket_name': bucket_name_1,
                'object_name': object_name_1, 'file_size': file_size, 'total_parts': total_parts,
                'multipart_obj_path': self.multipart_obj_path, 'part_numbers': part_numbers,
                'parts_etag': parts_etag, 'output': output}
        thread = threading.Thread(target=self.ha_obj.start_random_mpu, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Started multipart upload of %s MB object in background", file_size)

        time.sleep(HA_CFG["common_params"]["60sec_delay"])

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
        LOGGER.info("Step 5: Successfully started the pod and cluster is online")
        self.restore_pod = False

        LOGGER.info("Step 6: Checking responses from background process")
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
        elif exp_failed_parts or failed_parts:
            assert_utils.assert_true(False, "Failed to upload parts when cluster was in good "
                                            f"state. Failed parts: {failed_parts} and "
                                            f"{exp_failed_parts}")
        LOGGER.info("Step 6: Successfully checked background process responses")

        parts_etag = sorted(parts_etag, key=lambda d: d['PartNumber'])
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum2 = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                            compare=False)[0]
        LOGGER.info("Successfully uploaded all the parts of multipart upload.")

        LOGGER.info("Step 7: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, bucket_name_1, object_name_1)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 7: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 8: Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, bucket_name_1,
                                                       object_name_1)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(bucket_name_1)
        assert_utils.assert_in(object_name_1, res[1], res)
        LOGGER.info("Step 8: Multipart upload completed")

        LOGGER.info("Step 9.1: Download the uploaded objects in healthy cluster and verify "
                    "checksum")
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, self.bucket_name, self.object_name,
                                                  download_path, upload_checksum1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9.2: Download the uploaded objects in step 4 and verify checksum")
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, bucket_name_1, object_name_1,
                                                  download_path1, upload_checksum2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully downloaded the objects and verified the checksum")

        object_name_2 = f"ha-mp-obj-{int(perf_counter_ns())}"
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new bucket")
            bucket_name_2 = f"ha-mp-bkt-{int(perf_counter_ns())}"
        else:
            bucket_name_2 = self.bucket_name
        LOGGER.info("Step 10: Again perform multipart upload for size %s MB in total %s parts and "
                    "download the object and verify checksum", file_size, total_parts)
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name_2,
                                                         object_name=object_name_2,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(bucket_name_2, object_name_2)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", bucket_name_2, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Successfully performed multipart upload for size %s MB in total %s parts.",
                    file_size, total_parts)
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, bucket_name_2, object_name_2,
                                                  download_path2, upload_checksum)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Successfully performed multipart upload and downloaded the object "
                    "and verified the checksum")
        self.extra_files.extend((self.multipart_obj_path, download_path, download_path1,
                                 download_path2))
        LOGGER.info("ENDED: Test to verify multipart upload during data pod restart")

    # pylint: disable=too-many-branches
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34084")
    def test_copy_object_during_pod_restart(self):
        """
        This test tests copy object during data pod restart
        """
        LOGGER.info("STARTED: Test to verify copy object during data pod restart")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        t_t = int(perf_counter_ns())
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{t_t}"] = f"ha-obj{cnt}-{t_t}"
        output = Queue()
        event = threading.Event()

        LOGGER.info("Step 1: Create and list buckets. Upload object to %s & copy object from the"
                    " same bucket to other buckets and verify copy object etags", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=self.s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully created multiple buckets and uploaded object to %s "
                    "and copied to other buckets and verified copy object etags", self.bucket_name)

        LOGGER.info("Step 2: Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.delete_pod)
        self.restore_pod = True

        LOGGER.info("Step 3: Download the copied objects & verify etags.")
        for bkt, obj in bkt_obj_dict.items():
            resp = self.s3_test_obj.get_object(bucket=bkt, key=obj)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get "
                                                          f"Etag for object {obj} of bucket "
                                                          f"{bkt}.")
        LOGGER.info("Step 3: Downloaded copied objects & verify etags.")

        bkt_obj_dict1 = bkt_obj_dict.copy()
        t_t = int(perf_counter_ns())
        bucket_name = self.bucket_name
        bkt_op = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create and list buckets")
            bkt_obj_dict.clear()
            for cnt in range(bkt_cnt):
                bkt_obj_dict[f"ha-bkt{cnt}-{t_t}"] = f"ha-obj{cnt}-{t_t}"
            bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}-1"
            bkt_op = True
        else:
            for idx, bkt in enumerate(bkt_obj_dict):
                bkt_obj_dict[bkt] = f"ha-obj{idx}-{t_t}"

        LOGGER.info("Step 4: Copy object from %s to other buckets in background", bucket_name)
        args = {'s3_test_obj': self.s3_test_obj, 'bucket_name': bucket_name, 'put_etag': put_etag,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': bkt_op}
        thread = threading.Thread(target=self.ha_obj.create_bucket_copy_obj, args=(event,),
                                  kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Successfully started background process for copy object")
        # While loop to sync this operation with background thread to achieve expected scenario
        LOGGER.info("Waiting for creation of %s buckets", bkt_cnt)
        bkt_list = list()
        timeout = time.time() + HA_CFG["common_params"]["bucket_creation_delay"]
        while len(bkt_list) < bkt_cnt:
            time.sleep(HA_CFG["common_params"]["20sec_delay"])
            bkt_list = self.s3_test_obj.bucket_list()[1]
            if timeout < time.time():
                LOGGER.error("Bucket creation is taking longer than % sec",
                             HA_CFG["common_params"]["bucket_creation_delay"])
                assert_utils.assert_true(False, "Please check background process logs")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])

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
        LOGGER.info("Step 5: Successfully started the pod and cluster is online")
        self.restore_pod = False
        event.clear()

        LOGGER.info("Step 6: Checking responses from background process")
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
        elif failed_bkts or exp_fail_bkt_obj_dict:
            assert_utils.assert_true(False, "Failed to do copy object when cluster was in degraded "
                                            f"state. Failed buckets: \n{failed_bkts}"
                                            f"\n{exp_fail_bkt_obj_dict}")
        LOGGER.info("Step 6: Successfully completed copy object operation is background")

        LOGGER.info("Step 7.1: Download the objects copied in healthy cluster and verify checksum")
        for key, val in bkt_obj_dict.items():
            resp = self.s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {val} of bucket {key}. Put and "
                                                          f"Get Etag mismatch")
        LOGGER.info("Step 7.1: Download the objects copied in step 4 and verify checksum")
        for key, val in bkt_obj_dict1.items():
            resp = self.s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {val} of bucket {key}. Put and "
                                                          f"Get Etag mismatch")
        LOGGER.info("Step 7: Successfully downloaded the object and verified the checksum")

        t_t = int(perf_counter_ns())
        bucket_name = self.bucket_name
        bkt_op = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create and list buckets")
            bkt_obj_dict.clear()
            for cnt in range(bkt_cnt):
                bkt_obj_dict[f"ha-bkt{cnt}-{t_t}"] = f"ha-obj{cnt}-{t_t}"
            bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}-2"
            bkt_op = True
        else:
            for idx, bkt in enumerate(bkt_obj_dict):
                bkt_obj_dict[bkt] = f"ha-obj{idx}-{t_t}"

        LOGGER.info("Step 8: Perform copy object from %s bucket to other buckets verify copy object"
                    " etags", bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=self.s3_test_obj,
                                                  bucket_name=bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag, bkt_op=bkt_op)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        LOGGER.info("Step 8: Performed copy object from %s bucket to other buckets verified copy "
                    "object etags", bucket_name)

        LOGGER.info("Step 9: Download the copied objects & verify etags.")
        for bkt, obj in bkt_obj_dict.items():
            resp = self.s3_test_obj.get_object(bucket=bkt, key=obj)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag"
                                                          f"for object {obj} of bucket {bkt}.")
        LOGGER.info("Step 9: Downloaded copied objects & verify etags.")

        LOGGER.info("ENDED: Test to verify copy object during data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45641")
    def test_bkt_ver_suspension_data_pod_restart(self):
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

        LOGGER.info("Step 5: Shutdown random data pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=self.num_replica - 1)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.restore_pod = True
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 5: Successfully shutdown data pod %s. Verified cluster and services "
                    "states are as expected & remaining pods status is online.", self.delete_pod)

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

        new_bucket = self.bucket_name
        download_path = self.multipart_obj_path
        if CMN_CFG["dtm0_disabled"]:
            download_path = os.path.join(self.test_dir_path, self.test_file + "_new")
            self.extra_files.append(download_path)
            new_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
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
            LOGGER.info("Step 8: Uploaded same object %s after enabling versioning. Listed & "
                        "verified the VersionID for the same for %s.", self.object_name, new_bucket)

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
                assert_utils.assert_true(False, "Etag without specifying VersionID does not match "
                                                f"with etag {etag} {resp[1]}")
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

        # TODO: Need to check if enabling or disabling versioning is supported or not with dtm
        if CMN_CFG["dtm0_disabled"]:
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
                assert_utils.assert_true(False,
                                         "Etag without specifying VersionID does not match with"
                                         f" etag {etag} {resp[1]}")
            LOGGER.info(
                "Step 11: Got versions of %s with & without specifying VersionID & verified "
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
            LOGGER.info("Step 13: Uploaded same object %s after suspending versioning and verified "
                        "its null for %s.", self.object_name, new_bucket)

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

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45640")
    def test_bkt_ver_during_data_pod_restart(self):
        """
        This test verify bucket versioning during data pod restart
        """
        LOGGER.info("STARTED: Test to verify bucket versioning during data pod restart.")
        event = threading.Event()
        get_output = Queue()
        put_output = Queue()
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

        LOGGER.info("Step 3: Shutdown data pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=self.num_replica - 1)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and services "
                    "states are as expected & remaining pods status is online.", self.delete_pod)

        LOGGER.info("Step 4: Get object versions of %s with VersionID & verify etags for %s.",
                    self.object_name, self.bucket_name)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=self.bucket_name, obj_name=self.object_name,
                                               ver_etag=self.version_etag[self.bucket_name])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        LOGGER.info("Step 4: Got object versions of %s with VersionID & verified etags for %s.",
                    self.object_name, self.bucket_name)

        count = HA_CFG["common_params"]["put_get_version"]
        LOGGER.info("Step 5: Starting background threads for Get and Put version for count %s "
                    "while data pod restarting.", count)
        LOGGER.info("Upload same object %s for %s times for background Get.", self.object_name,
                    count)
        args = {'file_path': self.multipart_obj_path, 'count': count}
        resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, self.bucket_name,
                                               self.object_name, **args)
        assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
        self.version_etag[self.bucket_name].extend(resp[1])
        args = {'file_path': self.multipart_obj_path, 'count': count, 'background': True}
        put_thread = threading.Thread(
            target=self.ha_api.parallel_put_object,
            args=(event, self.s3_test_obj, self.bucket_name, self.object_name, put_output),
            kwargs=args)
        args = {'background': True, 'output': get_output}
        get_thread = threading.Thread(
            target=self.ha_api.parallel_get_object,
            args=(event, self.s3_ver, self.bucket_name, self.object_name,
                  self.version_etag[self.bucket_name]), kwargs=args)
        LOGGER.info("Uploaded same object %s for %s times for background Get.", self.object_name,
                    count)
        put_thread.daemon = True  # Daemonize thread
        get_thread.daemon = True  # Daemonize thread
        put_thread.start()
        get_thread.start()
        event.set()
        LOGGER.info("Step 5: Started background threads for Get and Put Version")

        LOGGER.info("Step 6: Restart data pod with replica method and check cluster status")
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
        event.clear()
        put_thread.join()
        get_thread.join()
        LOGGER.info("Step 6: Successfully restart data pod with replica method & checked "
                    "cluster status.")

        LOGGER.info("Step 7: Verify background Put & Get Version for %s", self.object_name)
        get_resp = tuple()
        put_resp = tuple()
        while len(get_resp) != 2:
            get_resp = get_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        while len(put_resp) != 2:
            put_resp = put_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        assert_utils.assert_false(len(get_resp[1]) or len(put_resp[1]),
                                  "Failure in put or get object during restart"
                                  f"GET resp: {get_resp[1]} PUT resp: {put_resp[1]}")
        self.version_etag[self.bucket_name].extend(put_resp[0])
        LOGGER.info("Step 7: Verified background Put & Get Version for %s", self.object_name)

        LOGGER.info("Step 8: Get object with version IDs & verify etags for %s.", self.bucket_name)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=self.bucket_name, obj_name=self.object_name,
                                               ver_etag=self.version_etag[self.bucket_name])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        LOGGER.info("Step 8: Got object with version IDs & verified etags for %s.",
                    self.bucket_name)

        new_bucket = self.bucket_name
        download_path = self.multipart_obj_path
        if CMN_CFG["dtm0_disabled"]:
            new_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
            download_path = os.path.join(self.test_dir_path, self.test_file + "_new")
            self.extra_files.append(download_path)
            LOGGER.info("Step 9: Create new bucket and upload object %s of %s size. Enable "
                        "versioning on %s.", self.object_name, self.f_size, new_bucket)
            args = {'chk_null_version': True, 'is_unversioned': True, 'file_path': download_path,
                    'enable_ver': True, 's3_ver': self.s3_ver}
            resp = self.ha_api.crt_bkt_put_obj_enbl_ver(event, self.s3_test_obj, new_bucket,
                                                        self.object_name, **args)
            assert_utils.assert_true(resp[0], resp[1])
            self.version_etag.update({new_bucket: []})
            self.version_etag[new_bucket].extend(resp[1])
            LOGGER.info("Step 9: Created bucket and uploaded object %s of %s size. Enabled "
                        "versioning on %s.", self.object_name, self.f_size, new_bucket)

        LOGGER.info("Step 10: Upload same object %s. List & verify the VersionID for "
                    "the same for %s.", self.object_name, new_bucket)
        args = {'file_path': download_path}
        resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, new_bucket,
                                               self.object_name, **args)
        assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
        self.version_etag[new_bucket].extend(resp[1])
        resp = self.ha_api.list_verify_version(self.s3_ver, new_bucket,
                                               self.version_etag[new_bucket])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Uploaded same object %s after enabling versioning. Listed & "
                    "verified VersionID for the same for %s.", self.object_name, new_bucket)

        LOGGER.info("Step 11: Get object versions of %s & verify etags for %s.",
                    self.object_name, new_bucket)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=new_bucket, obj_name=self.object_name,
                                               ver_etag=self.version_etag[new_bucket])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        LOGGER.info("Step 11: Got object versions of %s & verified etags for %s.",
                    self.object_name, new_bucket)
        LOGGER.info("COMPLETED: Test to verify bucket versioning during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45639")
    def test_bkt_ver_after_data_pod_restart(self):
        """
        This test tests bucket versioning after data pod restart
        """
        LOGGER.info("STARTED: Test to verify bucket versioning after data pod restart.")
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

        LOGGER.info("Step 3: Shutdown data pod with replica method and verify cluster & "
                    "remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=self.num_replica - 1)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], f"Failed to shutdown/delete {self.delete_pod} pod")
        self.set_name = resp[1][self.delete_pod]['deployment_name']
        self.restore_method = resp[1][self.delete_pod]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and services "
                    "states are as expected & remaining pods status is online.", self.delete_pod)

        LOGGER.info("Step 4: Get object with version IDs & verify etags for %s.", self.bucket_name)
        resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                               bkt_name=self.bucket_name, obj_name=self.object_name,
                                               ver_etag=self.version_etag[self.bucket_name])
        assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
        LOGGER.info("Step 4: Got object with version IDs & verify etags for %s.", self.bucket_name)

        LOGGER.info("Step 5: Upload same object %s after data pod shutdown. List & verify "
                    "the VersionID for the same for %s.", self.object_name, self.bucket_name)
        args = {'file_path': self.multipart_obj_path}
        resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, self.bucket_name,
                                               self.object_name, **args)
        assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
        self.version_etag[self.bucket_name].extend(resp[1])
        resp = self.ha_api.list_verify_version(self.s3_ver, self.bucket_name, self.version_etag[
            self.bucket_name])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Uploaded same object %s after data pod shutdown. Listed & verified"
                    " the VersionID for the same for %s.", self.object_name, self.bucket_name)

        if CMN_CFG["dtm0_disabled"]:
            new_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
            bucket_list.append(new_bucket)
            download_path = os.path.join(self.test_dir_path, self.test_file + "_new")
            self.extra_files.append(download_path)
            LOGGER.info("Step 6: Create new bucket and upload object %s of %s size. Enable "
                        "versioning on %s.", self.object_name, self.f_size, new_bucket)
            args = {'chk_null_version': True, 'is_unversioned': True, 'file_path': download_path,
                    'enable_ver': True, 's3_ver': self.s3_ver}
            resp = self.ha_api.crt_bkt_put_obj_enbl_ver(event, self.s3_test_obj, new_bucket,
                                                        self.object_name, **args)
            assert_utils.assert_true(resp[0], resp[1])
            self.version_etag.update({new_bucket: []})
            self.version_etag[new_bucket].extend(resp[1])
            LOGGER.info("Step 6: Created bucket and uploaded object %s of %s size. Enabled "
                        "versioning on %s.", self.object_name, self.f_size, new_bucket)

            LOGGER.info("Step 7: Upload same object %s after enabling versioning. List & verify "
                        "the VersionID for the same for %s.", self.object_name, new_bucket)
            args = {'file_path': download_path}
            resp = self.ha_api.parallel_put_object(event, self.s3_test_obj, new_bucket,
                                                   self.object_name, **args)
            assert_utils.assert_true(resp[0], f"Upload Object failed {resp[1]}")
            self.version_etag[new_bucket].extend(resp[1])
            resp = self.ha_api.list_verify_version(self.s3_ver, new_bucket,
                                                   self.version_etag[new_bucket])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: Uploaded same object %s after enabling versioning. Listed & "
                        "verified VersionID for the same for %s.", self.object_name, new_bucket)

            LOGGER.info("Step 8: Get object with version IDs and verify etags for %s.", new_bucket)
            resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                                   bkt_name=new_bucket, obj_name=self.object_name,
                                                   ver_etag=self.version_etag[new_bucket])
            assert_utils.assert_true(resp[0], f"Get Object with versionID failed {resp[1]}")
            LOGGER.info("Step 8: Got object with version IDs and verify etags for %s.", new_bucket)

        LOGGER.info("Step 9: Restart data pod with replica method and check cluster status")
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
        LOGGER.info("Step 9: Successfully restart data pod with replica method & checked "
                    "cluster status")

        LOGGER.info("Step 10: Get object versions of %s buckets with version IDs & verify etags.",
                    bucket_list)
        for bucket in bucket_list:
            resp = self.ha_api.parallel_get_object(event=event, s3_ver_obj=self.s3_ver,
                                                   bkt_name=bucket, obj_name=self.object_name,
                                                   ver_etag=self.version_etag[bucket])
            assert_utils.assert_true(resp[0], f"Get object with versionID failed {resp[1]} for"
                                              f" {bucket}")
        LOGGER.info("Step 10: Got object versions of %s buckets with version IDs & verified etags.",
                    bucket_list)
        LOGGER.info("COMPLETED: Test to verify bucket versioning after data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45637")
    def test_obj_overwrite_data_pod_restart(self):
        """
        Verify object overwrite before and after data pod restart
        """
        LOGGER.info("STARTED: Test to verify object overwrite before and after data pod restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        LOGGER.info("Step 1: Create bucket %s and perform upload of object size %s MB and "
                    "Overwrite the object", self.bucket_name, file_size)
        s3_data = {self.bucket_name: [self.object_name, file_size]}
        resp = self.ha_obj.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        for _, checksum in resp[1].items():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum doesn't match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 1: Create bucket %s and perform upload of object size %s MB and "
                    "Overwrite the object", self.bucket_name, file_size)

        LOGGER.info("Step 2: Shutdown data pod with replica method and verify cluster & "
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
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Overwrite existing object %s of bucket %s.", self.object_name,
                    self.bucket_name)
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 3.1: Create new bucket and overwrite object in new bucket")
            t_t = int(perf_counter_ns())
            bucket_name = f"bucket-{t_t}"
            object_name = f"object-{t_t}"
            s3_data.update({bucket_name: [object_name, file_size]})
        resp = self.ha_obj.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        for checksum in resp[1].values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum does not match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 3: Successfully performed overwrite object operation after %s "
                    "shutdown.", pod_name)

        LOGGER.info("Step 4: Restart the pod with replica method and check cluster status")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way or "
                                          f"cluster status is not good")
        LOGGER.info("Step 4: Successfully restarted the pod with replica method and checked "
                    "cluster status")
        self.restore_pod = False

        LOGGER.info("Step 5: Overwrite existing object %s of bucket %s.", self.object_name,
                    self.bucket_name)
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 5.1: Create new bucket and overwrite object in new bucket")
            t_t = int(perf_counter_ns())
            bucket_name = f"bucket-{t_t}"
            object_name = f"object-{t_t}"
            s3_data.update({bucket_name: [object_name, file_size]})
        resp = self.ha_obj.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        for checksum in resp[1].values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum doesn't match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 5: Successfully performed overwrite object operation after %s "
                    "restart.", pod_name)

        LOGGER.info("ENDED: Test to verify object overwrite before and after data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45638")
    def test_obj_overwrite_during_data_pod_restart(self):
        """
        Verify object overwrite during data pod restart
        """
        LOGGER.info("STARTED: Test to verify object overwrite during data pod restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        output = Queue()
        event = threading.Event()

        LOGGER.info("Step 1: Create bucket %s and perform upload of object size %s MB and "
                    "Overwrite the object", self.bucket_name, file_size)
        s3_data = {self.bucket_name: [self.object_name, file_size]}
        resp = self.ha_obj.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        upld_chcksm = list(resp[1].values())[0][0]
        for checksum in resp[1].values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum doesn't match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 1: Create bucket %s and perform upload of object size %s MB and "
                    "Overwrite the object", self.bucket_name, file_size)

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_multi"]
        before_bkt = dict()
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create %s buckets and upload objects for background overwrite during "
                        "pod restart.", bkt_cnt)
            t_t = int(perf_counter_ns())
            for cnt in range(bkt_cnt):
                before_bkt.update({f"ha-bkt{cnt}-{t_t}": [f"ha-obj{cnt}-{t_t}", file_size]})
            resp = self.ha_obj.object_overwrite_dnld(self.s3_test_obj, before_bkt, iteration=0,
                                                     random_size=False)
            assert_utils.assert_true(resp[0], "Failure observed in create new bucket, "
                                              "upload object.")

        LOGGER.info("Step 2: Shutdown data pod with replica method and verify cluster & "
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
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

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
        new_s3_data = dict()
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 4: Start overwrite operation on new buckets")
            t_t = int(perf_counter_ns())
            for cnt in range(bkt_cnt):
                new_s3_data.update({f"ha-bkt{cnt}-{t_t}": [f"ha-obj{cnt}-{t_t}", file_size]})
        else:
            LOGGER.info("Step 4: Start overwrite operation on buckets created in healthy cluster")
            new_s3_data = before_bkt.copy()
        args = {"s3_test_obj": self.s3_test_obj, "s3_data": new_s3_data, "iteration": 1,
                "random_size": True, "queue": output, "background": True, "event": event}
        thread = threading.Thread(target=self.ha_obj.object_overwrite_dnld, kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 4: Started overwrite object in background")
        LOGGER.info("Waiting for bucket creation for ~ %s sec",
                    HA_CFG["common_params"]["10min_delay"])
        timeout = time.time() + HA_CFG["common_params"]["10min_delay"]
        while True:
            time.sleep(HA_CFG["common_params"]["20sec_delay"])
            bkt_list = self.s3_test_obj.bucket_list()[1]
            if all(item in bkt_list for item in list(new_s3_data.keys())):
                break
            if timeout < time.time():
                LOGGER.error("Bucket creation is taking longer than %s sec",
                             HA_CFG["common_params"]["10min_delay"])
                assert_utils.assert_true(False, "Please check background process logs")
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
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way or "
                                          f"cluster status is not good")
        LOGGER.info("Step 5: Successfully restarted the pod with replica method and checked "
                    "cluster status")
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
        resp = self.ha_obj.object_overwrite_dnld(self.s3_test_obj, s3_data, iteration=1,
                                                 random_size=False)
        assert_utils.assert_true(resp[0], "Failure observed in overwrite method.")
        for checksum in resp[1].values():
            assert_utils.assert_equal(checksum[0], checksum[1],
                                      f"Checksum doesn't match, Expected: {checksum[0]} "
                                      f"Received: {checksum[1]}")
        LOGGER.info("Step 8: Successfully overwritten existing object of bucket %s",
                    self.bucket_name)
        LOGGER.info("ENDED: Test to verify object overwrite during data pod restart")
