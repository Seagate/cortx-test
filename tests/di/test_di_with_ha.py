#!/usr/bin/python # pylint: disable=C0302
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
DI test Suite with HA/Cluster scenarios.
"""

import logging
import os
import random
import time
from time import perf_counter_ns

import pytest
from commons.constants import MB
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs, remove_file
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di import di_lib
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.di.fi_adapter import S3FailureInjection
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902 disable=no-member
@pytest.mark.usefixtures("restart_s3server_with_fault_injection")
class TestDICheckHA:
    """
    Test suite for DI with HA scenarios.
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
        cls.host_master_list = list()
        cls.host_worker_list = list()
        cls.node_master_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = True
        cls.s3_clean = cls.test_prefix = cls.s3bench_cleanup = cls.random_time = cls.s3ios = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = random.SystemRandom()
        cls.di_err_lib = DIErrorDetection()
        cls.fi_adapter = S3FailureInjection(cmn_cfg=CMN_CFG)
        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.host_master_list.append(cls.host)
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
            else:
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_test_obj = S3TestLib()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "DITestMultipartUpload")
        if not os.path.exists(cls.test_dir_path):
            resp = make_dirs(cls.test_dir_path)
            LOGGER.info("Created dir %s", cls.test_dir_path)

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        self.edtl = DIErrorDetection()
        # pylint: disable=maybe-no-member
        self.data_corruption_status = False
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = "{}_{}".format("di_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "di-fi-bkt-{}".format(self.random_time)
        self.object_name = "di-fi-obj-{}".format(self.random_time)
        self.file_path = os.path.join(self.test_dir_path, di_lib.get_random_file_name())
        LOGGER.info("Done: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if self.data_corruption_status:
            self.log.info("Disabling data corruption")
            self.fi_adapter.disable_data_block_corruption()
        if os.path.exists(self.test_dir_path):
            self.log.debug("Deleting existing file: %s", str(self.file_path))
            remove_file(self.file_path)
            remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.lc
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-22926")
    def test_reads_after_cluster_restart_22926(self):
        """
        Induce data corruption and verify READs before and after cluster restart .
        """
        size = 16 * MB
        LOGGER.info("Started: DI Flag(S3_READ_DI) enabled and corrupted file flags error during"
                    " read even after node/cluster reboots.")
        LOGGER.info("STEP 1: Perform WRITEs with 10 MB file")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            pytest.skip()
        self.test_prefix = 'TEST-22926'

        LOGGER.info("Step 1: Create a bucket.")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Step 1a: Created a bucket with name : %s", self.bucket_name)
        self.s3_clean = True
        LOGGER.info("Step 2: Create a corrupted file.")
        self.edtl.create_file(size, first_byte='z', name=self.file_path)
        # file_checksum = system_utils.calculate_checksum(self.file_path, binary_bz64=False)[1]
        LOGGER.info("Step 2a: created a file with corrupted flag at location %s", self.file_path)
        LOGGER.info("Step 3: enable data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            LOGGER.info("Step 3a: enabled data corruption")
            self.data_corruption_status = True
        else:
            LOGGER.info("Step 3b: failed to enable data corruption")
            assert False
        LOGGER.info("Step 4: Put object in a bucket.")
        self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                    object_name=self.object_name,
                                    file_path=self.file_path)
        LOGGER.info("Step 5: Verify get object.")
        try:
            resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        except CTException as error:
            self.log.error('get object failed %s', error)

        LOGGER.info("Step 5a: Verified read (Get) of an object whose metadata is corrupted.")
        LOGGER.info("Step 6: Send the cluster shutdown signal through CSM REST.")
        resp = SystemHealth.cluster_operation_signal(operation="shutdown_signal",
                                                     resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 8: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8a: Cluster restarted fine and all Pods online.")
        LOGGER.info("Step 9: Perform READs and verify DI on the written data")
        try:
            resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        except CTException as error:
            self.log.error('get object failed %s', error)
        self.s3bench_cleanup = None
        LOGGER.info("Step 5: Delete all the test objects, buckets and s3 user")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = None
        self.restored = False
        LOGGER.info("Step 5: Deleted all the test objects, buckets and s3 user")
        LOGGER.info("Completed: DI Flag(S3_READ_DI) enabled and corrupted file flags error during"
                    " read even after node/cluster reboots.")
