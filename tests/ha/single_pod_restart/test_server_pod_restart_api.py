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
class TestServerPodRestartAPI:
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
        cls.multipart_obj_path = None
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
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} "
                                              "way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Removing extra files")
        for file in self.extra_files:
            system_utils.remove_file(file)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44842")
    def test_mpu_after_server_pod_restart(self):
        """
        This test tests multipart upload after server pod restart.
        """
        LOGGER.info("STARTED: Test to verify multipart upload after server pod restart.")
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
        LOGGER.info("Step 3: Download the uploaded object %s in healthy cluster & verify checksum",
                    self.object_name)
        resp = self.ha_obj.dnld_obj_verify_chcksm(s3_test_obj, self.bucket_name, self.object_name,
                                                  download_path_1, upload_checksum_1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully downloaded the object %s & verified the checksum",
                    self.object_name)
        object_name_1 = f"ha-mp-obj-{int(perf_counter_ns())}"
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
        LOGGER.info("Step 5: Start server pod again by statefulset")
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
                                          f"way")
        self.restore_pod = False
        LOGGER.info("Step 5: Successfully started server pod again by statefulset")
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
        LOGGER.info("COMPLETED: Test to verify multipart upload after server pod restart.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-44844")
    def test_partial_mpu_after_server_pod_restart(self):
        """
        This test tests partial multipart upload after server pod restart
        """
        LOGGER.info("STARTED: Test to verify partial multipart upload after server pod restart.")
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
        num_replica = self.num_replica - 1
        LOGGER.info("Step 3: Shutdown server pod by making replicas=0 and verify cluster & "
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
        LOGGER.info("Step 3: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
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
        LOGGER.info("Step 6: Start server pod again by statefulset")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                       self.deployment_backup,
                                                       "num_replica": self.num_replica,
                                                       "set_name": self.set_name},
                                       clstr_status=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore server pod by {self.restore_method}"
                                          "way")
        self.restore_pod = False
        LOGGER.info("Step 6: Successfully started server pod again by statefulset")
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
        LOGGER.info("COMPLETED: Test to verify partial multipart upload after server pod restart.")
