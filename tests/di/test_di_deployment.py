#!/usr/bin/python
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

"""DI tests with multiple EC deployment (k8s based Cortx) Test Suite."""
from __future__ import division

import logging
import os
import random
import time

import pytest

from commons.constants import MB, \
    MULTIPART_UPLOAD_SIZES_IN_MB, NORMAL_UPLOAD_SIZES_IN_MB
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_PATH
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.di.fi_adapter import S3FailureInjection
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3 import S3H_OBJ
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib


class TestDIDeployment:
    """Test DI with multiple Durability Config"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.di_err_lib = DIErrorDetection()
        cls.fi_adapter = S3FailureInjection(cmn_cfg=CMN_CFG)
        cls.test_dir_path = os.path.join(TEST_DATA_PATH, "TestDI")
        cls.F_PATH = cls.test_dir_path + "/temp.txt"

    def setup_method(self):
        """Destroy the cortx cluster before starting the deployment tests"""
        self.log.info("Destroy the cluster from master node")
        resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0], self.worker_node_list)
        assert_utils.assert_true(resp[0], resp[1])

    def teardown_method(self):
        """
        Test method level teardown.
        """
        if system_utils.path_exists(self.test_dir_path):
            self.log.debug("Deleting test data dir: %s",self.test_dir_path)
            system_utils.remove_dirs(self.test_dir_path)

    def basic_io_with_fi(self, bucket_name, s3t_obj, first_byte='f'):
        """
        Perform Simple Object IO with DI Fault Injection enabled,
        expects Internal Error for each object.
        param: bucket_name : Bucket name to perform IO
        param: s3t_obj : Object of S3TestLib
        param: first_byte: First byte for error injection
        return: None
        """
        self.log.info("Creating bucket %s", bucket_name)
        resp = s3t_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Perform IO operations and expect error")
        for each in NORMAL_UPLOAD_SIZES_IN_MB:
            obj_name = f'obj-{each}mb-{str(int(time.time()))}'
            location = self.di_err_lib.create_corrupted_file(size=each * MB, first_byte=first_byte,
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Uploading object %s in bucket %s", obj_name, bucket_name)
            s3t_obj.put_object(bucket_name=bucket_name, object_name=obj_name,
                               file_path=location)
            try:
                self.log.info("Download object %s and expect Internal Error", obj_name)
                s3t_obj.object_download(bucket_name=bucket_name, obj_name=obj_name,
                                        file_path=self.F_PATH)
                assert_utils.assert_true(False,
                                         "Download object Successful, expected Internal Error")
            except CTException as exc:
                assert_utils.assert_in("InternalError", str(exc.message))

            # delete created as well as downloaded file
            if system_utils.path_exists(location):
                system_utils.remove_file(location)
            if system_utils.path_exists(self.F_PATH):
                system_utils.remove_file(self.F_PATH)

        self.log.info("Delete Bucket")
        s3t_obj.delete_bucket(bucket_name=bucket_name, force=True)

    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-arguments
    def do_multipart_upload(self, s3t_obj: S3TestLib, s3_mp_test_obj: S3MultipartTestLib,
                            bucket_name, object_name, object_size, part_size=6):
        """
        Initiate multipart upload with object name on bucket, upload parts and complete it.
        Create file with size of object_size and split into multiple parts of part_size each
        Assumes bucket is already created.
        param: s3t_obj : Object of S3 testlib
        param: s3_mp_test_obj: Object of S3MultipartTestLib
        param: bucket_name : Bucket name for performing object upload
        param: object_name: Object name
        param: object_size: object_size in MB
        param: part_size: Part Size in MB
        """
        self.log.info("Initiating multipart upload")
        res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)

        self.log.info("Uploading parts into bucket")
        parts = []
        no_of_parts, last_part_size = divmod(object_size, part_size)
        total_parts = no_of_parts + 1 if last_part_size != 0 else no_of_parts
        corrupt_part = random.SystemRandom().randrange(start=1, stop=total_parts)

        part_number = 0
        while object_size > 0:
            if object_size < part_size:
                part_size = object_size

            object_size = object_size - part_size
            part_number = part_number + 1
            if part_number == corrupt_part:
                first_byte = 'f'
                self.log.info("Corrupted Part : %s", part_number)
            else:
                first_byte = 'a'
            location = self.di_err_lib.create_corrupted_file(size=part_size * MB,
                                                             first_byte=first_byte,
                                                             data_folder_prefix=self.test_dir_path)
            with open(location, "rb") as file_pointer:
                data = file_pointer.read()
                self.log.info("data : %s", chr(data[0]))

            self.log.info("Part No : %s Part Size : %s File:  %s", part_number, part_size, location)
            resp, resp_data = s3_mp_test_obj.upload_part(body=data, bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         upload_id=mpu_id, part_number=part_number)
            assert_utils.assert_true(resp, resp_data)
            parts.append({"PartNumber": part_number, "ETag": resp_data["ETag"]})

        self.log.info("Uploaded parts into bucket: %s", parts)

        self.log.info("Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts, bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        res = s3t_obj.object_list(bucket_name)
        assert_utils.assert_in(object_name, res[1], res[1])
        self.log.info("Multipart upload completed")

        return mpu_id, parts

    def multipart_io_with_fi(self, s3t_obj, s3_mp_obj, bucket_name):
        """
        Perform Multipart IO operations with fault injection enabled.
        expects Internal Error/Closed Connection for each object.
        param: s3t_obj : Object of S3TestLib
        param: s3_mp_obj : Object of S3MultipartTestLib
        param: bucket_name : Bucket name to perform IO
        return: None
        """
        self.log.info("Creating bucket %s", bucket_name)
        resp = s3t_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

        for each in MULTIPART_UPLOAD_SIZES_IN_MB[2:]:
            self.log.info("**** MULTIPART OBJECT SIZE IN MB : %s", each)
            obj_name = f"obj-{each}mb-{str(int(time.time()))}"
            self.do_multipart_upload(s3t_obj=s3t_obj, s3_mp_test_obj=s3_mp_obj,
                                     bucket_name=bucket_name,
                                     object_name=obj_name, object_size=each)

            self.log.info(f'Download the object and expect error response')

            try:
                resp = s3t_obj.get_object(bucket_name, obj_name)
            except CTException as exc:
                self.log.error("Exception : %s", exc)
                assert_utils.assert_in("InternalError", str(exc.message))
            else:
                self.log.info(f'Check the uploaded and downloaded object size')
                uploaded_obj_size = resp[1]["ContentLength"]
                self.log.info('size of uploaded object %s is: %s bytes', obj_name,
                              uploaded_obj_size)
                try:
                    content = resp[1]["Body"].read()
                    self.log.info('size of downloaded object %s is: %s bytes', obj_name,
                                  len(content))
                except Exception as error:
                    self.log.error('downloaded object is not complete: %s', error)
                else:
                    if uploaded_obj_size == len(content):
                        assert_utils.assert_false(True,
                                                  "uploaded and downloaded object size is same. "
                                                  "after corruption downloaded object size should"
                                                  " be less than uploaded object")

        self.log.info("Delete Bucket")
        s3t_obj.delete_bucket(bucket_name=bucket_name, force=True)

    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-22496')
    def test_22496(self):
        """
        Test Checksum validation for multiple Erasure Coding scheme.
        """
        num_nodes = len(self.worker_node_list)
        self.log.info("Number of worker nodes : %s", num_nodes)
        config_list = self.deploy_lc_obj.get_durability_config(num_nodes)
        for config in config_list:
            self.log.info("Perform Deployment with config SNS (%s+%s+%s) and DIX (%s+%s+%s)",
                          config["sns_data"], config["sns_parity"], config["sns_spare"],
                          config["dix_data"], config["dix_parity"], config["dix_spare"])

            self.deploy_lc_obj.test_deployment(sns_data=config["sns_data"],
                                               sns_parity=config["sns_parity"],
                                               sns_spare=config["sns_spare"],
                                               dix_data=config["dix_data"],
                                               dix_parity=config["dix_parity"],
                                               dix_spare=config["dix_spare"],
                                               cvg_count=config["cvg_count"],
                                               data_disk_per_cvg=config["data_disk_per_cvg"],
                                               master_node_list=self.master_node_list,
                                               worker_node_list=self.worker_node_list,
                                               setup_k8s_cluster_flag=True,
                                               cortx_cluster_deploy_flag=True,
                                               setup_client_config_flag=True,
                                               run_basic_s3_io_flag=False,
                                               run_s3bench_workload_flag=False,
                                               destroy_setup_flag=False)

            self.log.info("Validate if Default values are set for Data Integrity")
            resp = self.di_err_lib.validate_default_config()
            self.log.debug("resp : %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_false(resp[1], "Default values for Data Integrity flags not set")

            access_key, secret_key = S3H_OBJ.get_local_keys()
            s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)
            self.log.info("Step to Perform basic IO operations")
            bucket_name = "bucket-" + str(int(time.time()))
            self.deploy_lc_obj.basic_io_write_read_validate(s3t_obj, bucket_name)

            self.log.info("Step to Perform S3bench IO")
            bucket_name = "bucket-" + str(int(time.time()))
            self.deploy_lc_obj.io_workload(access_key=access_key, secret_key=secret_key,
                                           bucket_prefix=bucket_name)

            self.log.info("Step to Destroy setup")
            resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0], self.worker_node_list)
            assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-33650')
    def test_33650(self):
        """
        Test Checksum validation with DI fault injection for multiple Erasure Coding scheme.
        """
        num_nodes = len(self.worker_node_list)
        self.log.info("Number of worker nodes : %s", num_nodes)

        config_list = self.deploy_lc_obj.get_durability_config(num_nodes)
        for config in config_list:
            self.log.info("Perform Deployment with config SNS (%s+%s+%s) and DIX (%s+%s+%s)",
                          config["sns_data"], config["sns_parity"], config["sns_spare"],
                          config["dix_data"], config["dix_parity"], config["dix_spare"])

            self.deploy_lc_obj.test_deployment(sns_data=config["sns_data"],
                                               sns_parity=config["sns_parity"],
                                               sns_spare=config["sns_spare"],
                                               dix_data=config["dix_data"],
                                               dix_parity=config["dix_parity"],
                                               dix_spare=config["dix_spare"],
                                               cvg_count=config["cvg_count"],
                                               data_disk_per_cvg=config["data_disk_per_cvg"],
                                               master_node_list=self.master_node_list,
                                               worker_node_list=self.worker_node_list,
                                               setup_k8s_cluster_flag=True,
                                               cortx_cluster_deploy_flag=True,
                                               setup_client_config_flag=True,
                                               run_basic_s3_io_flag=False,
                                               run_s3bench_workload_flag=False,
                                               destroy_setup_flag=False)

            self.log.info("Validate if Default values are set for Data Integrity")
            resp = self.di_err_lib.validate_default_config()
            self.log.debug("resp : %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_false(resp[1], "Default values for Data Integrity flags not set")

            # Get configured AWS keys
            access_key, secret_key = S3H_OBJ.get_local_keys()
            s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)

            self.log.info("Enable Fault Injection")
            resp = self.fi_adapter.set_fault_injection(flag=True)
            assert_utils.assert_true(resp[0], resp[1])

            self.log.info("Enable di_data_corrupted_on_write")
            status = self.fi_adapter.enable_data_block_corruption()
            if status:
                self.log.info("Enabled data corruption: di_data_corrupted_on_write", )
            else:
                self.log.info("Failed to enable data corruption: di_data_corrupted_on_write")
                assert False

            self.log.info("Perform IO operation (Single object)")
            self.basic_io_with_fi(s3t_obj=s3t_obj, bucket_name="test-33650-simple-io")

            s3_mp_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key)
            self.log.info("Perform IO operation (Multipart Object)")
            bucket_name = "test-mpu-" + str(int(time.time()))
            self.multipart_io_with_fi(s3t_obj=s3t_obj, s3_mp_obj=s3_mp_obj,
                                      bucket_name=bucket_name)

            self.log.info("Disable Fault Injection")
            resp = self.fi_adapter.set_fault_injection(flag=False)
            assert_utils.assert_true(resp[0], resp[1])

            self.log.info("Step to Destroy setup")
            resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0], self.worker_node_list)
            assert_utils.assert_true(resp[0], resp[1])
