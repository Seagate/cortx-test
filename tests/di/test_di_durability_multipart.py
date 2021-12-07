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

"""
F-23B : Data Durability/Integrity test module for Multipart Files.
"""

import os
import logging
import pytest
import secrets
from time import perf_counter_ns
from boto3.s3.transfer import TransferConfig
from commons.constants import PROD_FAMILY_LC
from commons.constants import PROD_FAMILY_LR
from commons.constants import PROD_TYPE_K8S
from commons.constants import PROD_TYPE_NODE
from commons.helpers.node_helper import Node
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.exceptions import CTException
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER, VAR_LOG_SYS
from config import di_cfg
from config import CMN_CFG
from libs.s3 import S3_CFG
from commons.constants import const
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3 import cortxcli_test_lib
from libs.di.di_feature_control import DIFeatureControl
from libs.di.data_generator import DataGenerator
from libs.di.fi_adapter import S3FailureInjection
from libs.di import di_lib
from libs.di.di_mgmt_ops import ManagementOPs
from libs.s3.s3_cmd_test_lib import S3CmdTestLib


@pytest.fixture(scope="class", autouse=False)
def setup_multipart_fixture(request):
    """
    Yield fixture to setup pre requisites and teardown them.
    Part before yield will be invoked prior to each test case and
    part after yield will be invoked after test call i.e as teardown.
    """
    request.cls.log = logging.getLogger(__name__)
    request.cls.log.info("STARTED: Setup test operations.")
    request.cls.secure_range = secrets.SystemRandom()
    request.cls.s3_test_obj = S3TestLib()
    request.cls.s3_mp_test_obj = S3MultipartTestLib()
    request.cls.hostnames = list()
    request.cls.connections = list()
    request.cls.nodes = CMN_CFG["nodes"]
    if request.cls.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
            request.cls.cmn_cfg["product_type"] == PROD_TYPE_NODE:
        for node in request.cls.nodes:
            node_obj = Node(hostname=node["hostname"],
                            username=node["username"],
                            password=node["password"])
            node_obj.connect()
            request.cls.connections.append(node_obj)
            request.cls.hostnames.append(node["hostname"])
    elif request.cls.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
            request.cls.cmn_cfg["product_type"] == PROD_TYPE_K8S:
        request.cls.log.error("Product family: LC")
        # Add k8s masters
        for node in request.cls.nodes:
            if node["node_type"].lower() == "master":
                node_obj = LogicalNode(hostname=node["hostname"],
                                       username=node["username"],
                                       password=node["password"])
                request.cls.connections.append(node_obj)
                request.cls.hostnames.append(node["hostname"])

    request.cls.account_name = di_lib.get_random_account_name()
    s3_acc_passwd = di_cfg.s3_acc_passwd
    request.cls.s3_account = ManagementOPs.create_s3_user_csm_rest(request.cls.account_name,
                                                                   s3_acc_passwd)
    request.cls.bucket_name = di_lib.get_random_bucket_name()
    # create bucket

    request.cls.acc_del = False
    request.cls.log.info("ENDED: setup test operations.")
    yield
    request.cls.log.info("STARTED: Teardown operations")
    request.cls.log.info("Deleting the file created locally for object")
    if system_utils.path_exists(request.cls.file_path):
        system_utils.remove_dirs(request.cls.test_dir_path)
    request.cls.log.info("Local file was deleted")
    request.cls.log.info("ENDED: Teardown operations")


@pytest.mark.usefixtures("setup_multipart_fixture")
class TestDICheckMultiPart:
    """DI Test suite for F23B Multipart files."""

    def setup_method(self):
        """
        Test method level setup.
        """
        self.log = logging.getLogger(__name__)
        self.test_dir_path = os.path.join(
            VAR_LOG_SYS, TEST_DATA_FOLDER, "TestDataDurability")
        self.file_path = os.path.join(self.test_dir_path, di_lib.get_random_file_name())
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)

        self.log.info("ENDED: setup test data.")

    def teardown_method(self):
        """
        Test method level teardown.
        """
        self.log.info("STARTED: Teardown of test data")
        self.log.info("Deleting all buckets/objects created during TC execution")
        resp = self.s3_test_obj.bucket_list()
        if self.bucket_name in resp[1]:
            resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("All the buckets/objects deleted successfully")
        if self.s3_account:
            self.log.debug(f"Deleting the s3 account {self.s3_account}")
            ManagementOPs.delete_s3_user_csm_rest(self.account_name)
        self.log.info("Deleted the s3 accounts and users")
        self.log.info("ENDED: Teardown method")

    @pytest.fixture(scope="function", autouse=False)
    def create_testdir_cleanup(self):
        """
        Yield fixture to setup pre requisites and teardown them.
        Part before yield will be invoked prior to each test case and
        part after yield will be invoked after test call i.e as teardown.
        """
        self.test_dir_path = os.path.join(
            VAR_LOG_SYS, TEST_DATA_FOLDER, "TestDataDurability")
        self.file_path = os.path.join(self.test_dir_path, di_lib.get_random_file_name())
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)

        self.log.info("ENDED: setup test data.")
        yield
        self.log.info("STARTED: Teardown of test data")
        self.log.info("Deleting the file created locally for object")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_dirs(self.test_dir_path)
        self.log.info("Local file was deleted")
        self.log.info("Deleting all buckets/objects created during TC execution")

        resp = self.s3_test_obj.bucket_list()
        if self.bucket_name in resp[1]:
            resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("Deleting the IAM accounts and users")
        self.log.debug(self.s3_account)
        if self.s3_account:
            for acc in self.s3_account:
                self.cli_obj = cortxcli_test_lib.CortxCliTestLib()
                resp = self.cli_obj.login_cortx_cli(
                    username=acc, password=self.s3acc_passwd)
                self.log.debug("Deleting %s account", acc)
                self.cli_obj.delete_all_iam_users()
                self.cli_obj.logout_cortx_cli()
                self.cli_obj.delete_account_cortxcli(
                    account_name=acc, password=self.s3acc_passwd)
                self.log.info("Deleted %s account successfully", acc)
        self.log.info("Deleted the IAM accounts and users")
        self.cli_obj.close_connection()
        self.hobj.disconnect()
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22501')
    def test_verify_data_integrity_with_correct_checksum_22501(self):
        """
        Test to verify object integrity during an upload with correct checksum.
        Specify checksum and checksum algorithm or ETAG during
        PUT(SHA1, MD5 with and without digest, CRC ( check multi-part)).

        Multi part Put
        with data 64 MB file
        provide correct etag during put
        Verify that get does not fail with internal error
        ** Check CRC/checksum passed header. or s3 logs, Motr logs
        Verify checksum at client side


        """
        self.log.info("STARTED: Verify data integrity check during read with correct checksum.")
        self.log.info("Step 1: Create a bucket.")
        self.s3_test_obj.create_bucket(self.bucket_name)
        self.log.info("Step 1: Created a bucket.")
        self.log.info("Step 2: Put and object with checksum algo or ETAG.")
        system_utils.create_file(self.file_path, 8)
        file_checksum = system_utils.calculate_checksum(self.file_path, filter_resp=True)[1]
        res = self.s3_test_obj.put_object_with_all_kwargs(
            Bucket=self.bucket_name, Key=self.object_name, Body=self.file_path,
            ServerSideEncryption='AES256')
        assert_utils.assert_equal(res["ResponseMetadata"]["HTTPStatusCode"], 200, res)
        self.log.info(
            "Step 2: Put and object with md5 checksum.")
        res = self.s3_test_obj.put_object(
            self.bucket_name, self.object_name, self.file_path,
            content_md5=file_checksum)
        assert_utils.assert_true(
            res[0], f"Failed to put an object with md5 checksum and reason is:{res}")
        self.log.info(
            "Step 3: Put an object with checksum, checksum algo or ETAG.")
        self.log.info(
            "ENDED: Test to verify object integrity during an upload with correct checksum."
            "Specify checksum and checksum algorithm or ETAG during PUT(SHA1, MD5 with and without"
            "digest, CRC ( check multi-part))")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22912')
    def test_22912(self):
        """
        Test to verify object integrity during the the upload with correct checksum.
        Specify checksum and checksum algorithm or ETAG during
        PUT(MD5 with and without digest, CRC ( check multi-part))
        """
        self.log.info("STARTED: Corrupt checksum of an object 256KB to 31 MB "
                      "(at s3 checksum) and verify read (Get).")
        read_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.read_param)
        if read_flag[0]:
            pytest.skip()
        self.log.info("Step 1: create a file")
        buff, csm = self.data_gen.generate(size=1024 * 1024 * 5,
                                           seed=self.data_gen.get_random_seed())
        location = self.data_gen.save_buf_to_file(fbuf=buff, csum=csm, size=1024 * 1024 * 5,
                                                  data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a file at location %s", location)
        self.log.info("Step 2: enable checksum feature")
        # to do enabling checksum feature
        self.log.info("Step 3: upload a file with incorrect checksum")
        self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                    object_name=self.object_name,
                                    file_path=location)
        self.s3_test_obj.object_download(file_path=self.file_path,
                                         obj_name=self.object_name,
                                         bucket_name=self.bucket_name)
        self.log.info("Step 4: verify download object fails with 5xx error code")
        # to do verify object download failure
        self.log.info("ENDED: Corrupt checksum of an object 256KB to 31 MB "
                      "(at s3 checksum) and verify read (Get).")

    @pytest.mark.skip(reason="not tested hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29814')
    def test_29814(self):
        """
        Corrupt data chunk checksum of an multi part object 32 MB to 128 MB (at s3 checksum)
        and verify read (Get).
        """
        self.log.info("Started: Corrupt data chunk checksum of an multi part object 32 MB to 128 "
                      "MB (at s3 checksum) and verify read (Get).")
        if self.di_err_lib.validate_default_config():
            pytest.skip()
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a corrupted file at location %s", location)
        self.log.info("Step 2: enabling data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.log.info("Step 2: enabled data corruption")
        else:
            self.log.info("Step 2: failed to enable data corruption")
            assert False
        self.log.info("Step 3: upload a file using multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        parts = list()
        res_sp_file = system_utils.split_file(filename=location, size=25, split_count=5,
                                              random_part_size=False)
        i = 0
        while i < 5:
            with open(res_sp_file[i]["Output"], "rb") as file_pointer:
                data = file_pointer.read()
            resp = self.s3_mp_test_obj.upload_part(body=data,
                                                   bucket_name=self.bucket_name,
                                                   object_name=self.object_name,
                                                   upload_id=mpu_id, part_number=i + 1)
            parts.append({"PartNumber": i + 1, "ETag": resp[1]["ETag"]})
            i += 1
        self.s3_mp_test_obj.complete_multipart_upload(mpu_id=mpu_id, parts=parts,
                                                      bucket=self.bucket_name,
                                                      object_name=self.object_name)
        self.log.info("Step 4: verify download object fails with 5xx error code")
        # resp = self.s3_test_obj.object_download(file_path=self.file_path,
        #                                         bucket_name=self.bucket_name,
        #                                         obj_name=self.object_name)
        # to do verify object download failure
        self.log.info("Ended: Corrupt data chunk checksum of an multi part object 32 MB to 128 "
                      "MB (at s3 checksum) and verify read (Get).")

    @pytest.mark.skip(reason="not tested hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29815')
    def test_29815(self):
        """
        Corrupt data chunk checksum of an multi part object 32 MB to 128 MB (at s3 checksum)
        and verify range read (Get).
        """
        self.log.info("Started: Corrupt data chunk checksum of an multi part object 32 MB to 128 "
                      "MB (at s3 checksum) and verify range read (Get).")
        if self.di_err_lib.validate_default_config():
            pytest.skip()
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a corrupted file at location %s", location)
        self.log.info("Step 2: enabling data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.log.info("Step 2: enabled data corruption")
        else:
            self.log.info("Step 2: failed to enable data corruption")
            assert False
        self.log.info("Step 3: upload a file using multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        parts = list()
        res_sp_file = system_utils.split_file(filename=location, size=25, split_count=5,
                                              random_part_size=False)
        i = 0
        while i < 5:
            with open(res_sp_file[i]["Output"], "rb") as file_pointer:
                data = file_pointer.read()
            resp = self.s3_mp_test_obj.upload_part(body=data,
                                                   bucket_name=self.bucket_name,
                                                   object_name=self.object_name,
                                                   upload_id=mpu_id, part_number=i + 1)
            parts.append({"PartNumber": i + 1, "ETag": resp[1]["ETag"]})
            i += 1
        self.s3_mp_test_obj.complete_multipart_upload(mpu_id=mpu_id, parts=parts,
                                                      bucket=self.bucket_name,
                                                      object_name=self.object_name)
        self.log.info("Step 4: verify download object fails with 5xx error code")
        # resp = self.s3_mp_test_obj.get_byte_range_of_object(bucket_name=self.bucket_name,
        #                                                     my_key=self.object_name,
        #                                                     start_byte=8888,
        #                                                     stop_byte=9999)
        # to do verify object download failure
        self.log.info("Ended: Corrupt data chunk checksum of an multi part object 32 MB to 128 "
                      "MB (at s3 checksum) and verify range read (Get).")
