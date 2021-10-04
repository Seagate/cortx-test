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

"""Intel ISA workload suit."""
from __future__ import absolute_import

import logging
import os

import pytest

from commons import configmanager
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from libs.ha.ha_common_libs import HALibs
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


class TestIntelISAIO:
    """
    Test suite for Intel ISA - IO tests.
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup Module operations")
        test_config = "config/cft/test_intel_isa_workload.yaml"
        cls.test_config = configmanager.get_config_wrapper(fpath=test_config)
        cls.access_key, cls.secret_key = S3H_OBJ.get_local_keys()
        cls.s3t_obj = S3TestLib(access_key=cls.access_key, secret_key=cls.secret_key)
        cls.setup_type = CMN_CFG["setup_type"]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.ha_obj = HALibs()
        cls.node_list = []
        cls.hlt_list = []
        cls.reset_s3config = False
        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname,
                                       password=cls.passwd))
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.uname, password=cls.passwd))
            cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestIntelISAIO")
            if not os.path.exists(cls.test_dir_path):
                os.makedirs(cls.test_dir_path)
            cls.log.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        self.log.info("STARTED: Setup Operations")
        self.reset_s3config = False
        self.log.info("Checking if all nodes are reachable and PCS clean.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        self.log.info("All nodes are reachable and PCS looks clean.")
        self.log.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        """
        self.log.info("STARTED: Teardown Operations")
        if self.reset_s3config:
            self.log.info("Set S3_MOTR_IS_READ_VERIFY to false on all the %s nodes", self.num_nodes)
            for node in range(self.num_nodes):
                S3H_OBJ.update_s3config(section="S3_MOTR_CONFIG",
                                        parameter=self.test_config["test_basic_io"][
                                            "parity_check_flag"],
                                        value=False,
                                        host=CMN_CFG["nodes"][node]["hostname"],
                                        username=CMN_CFG["nodes"][node]["username"],
                                        password=CMN_CFG["nodes"][node]["password"]
                                        )
            self.log.info("Restart the cluster")
            self.ha_obj.restart_cluster(self.node_list[0], self.hlt_list)

        self.log.info("Deleting all buckets/objects created during TC execution")
        resp = self.s3t_obj.bucket_list()
        for bucket_name in resp[1]:
            if self.test_config["test_bucket_prefix"] in bucket_name:
                resp = self.s3t_obj.delete_bucket(bucket_name, force=True)
                assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Teardown Operations")

    def teardown_class(self):
        """Delete test data directory"""
        self.log.info("STARTED: Class Teardown")
        if system_utils.path_exists(self.test_dir_path):
            resp = system_utils.remove_dirs(self.test_dir_path)
            assert_utils.assert_true(resp, f"Unable to remove {self.test_dir_path}")
            self.log.info(
                "removed path: %s, resp: %s",
                self.test_dir_path,
                resp)

    def write_read_validate_file(self, bucket_name, test_file, count, block_size):
        """
        Create test_file with file_size(count*blocksize) and upload to bucket_name
        validate checksum after download and deletes the file
        """
        file_path = os.path.join(self.test_dir_path, test_file)

        self.log.info("Creating a file with name %s", test_file)
        system_utils.create_file(file_path, count, "/dev/urandom", block_size)

        self.log.info("Retrieving checksum of file %s", test_file)
        resp1 = system_utils.get_file_checksum(file_path)
        assert_utils.assert_true(resp1[0], resp1[1])
        chksm_before_put_obj = resp1[1]

        self.log.info("Uploading a object %s to a bucket %s", test_file, bucket_name)
        resp = self.s3t_obj.put_object(bucket_name, test_file, file_path)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Validate upload of object %s ", test_file)
        resp = self.s3t_obj.object_list(bucket_name)
        assert_utils.assert_in(test_file, resp[1], f"Failed to upload create {test_file}")

        self.log.info("Removing local file from client and downloading object")
        system_utils.remove_file(file_path)
        resp = self.s3t_obj.object_download(bucket_name, test_file, file_path)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Verifying checksum of downloaded file with old file should be same")
        resp = system_utils.get_file_checksum(file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(chksm_before_put_obj, chksm_after_dwnld_obj)

        self.log.info("Delete the file from the bucket")
        self.s3t_obj.delete_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Delete downloaded file")
        system_utils.remove_file(file_path)

    def basic_io_with_parity_check_enabled(self, bucket_name, skip_parity_check: bool = True):
        """
        Set the read verify flag to true
        Restart the S3 and motr services
        """
        basic_io_config = self.test_config["test_basic_io"]

        if skip_parity_check:
            self.log.info("Step 1: Set the S3_MOTR_IS_READ_VERIFY flag to true on all the nodes")
            for node in range(self.num_nodes):
                S3H_OBJ.update_s3config(section="S3_MOTR_CONFIG",
                                        parameter=basic_io_config["parity_check_flag"],
                                        value=True,
                                        host=CMN_CFG["nodes"][node]["hostname"],
                                        username=CMN_CFG["nodes"][node]["username"],
                                        password=CMN_CFG["nodes"][node]["password"]
                                        )
                self.reset_s3config = True
            self.log.info("Step 2: Restart the cluster")
            self.ha_obj.restart_cluster(self.node_list[0], self.hlt_list)

        self.log.info("Step 3: Creating bucket %s", bucket_name)
        resp = self.s3t_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 4: Perform write/read/validate/delete with multiples object sizes. ")
        for b_size, max_count in basic_io_config["io_upper_limits"].items():
            for count in range(0, max_count):
                test_file = "basic_io_" + str(count) + str(b_size)
                if str(b_size).lower() == "kb":
                    block_size = "1K"
                else:
                    block_size = "1M"
                self.write_read_validate_file(bucket_name, test_file, count, block_size)

        self.log.info("Step 5: Delete bucket %s", bucket_name)
        resp = self.s3t_obj.delete_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

    def io_workload(self, bucket_prefix):
        """
        S3 bench workload test executed for each of Erasure coding config
        """
        workloads = [
            "1Kb", "4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
            "1Mb", "4Mb", "8Mb", "16Mb", "32Mb", "64Mb", "128Mb", "256Mb", "512Mb", "1Gb", "2Gb"
        ]
        clients = self.test_config["test_io_workload"]["clients"]
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for workload in workloads:
            bucket_name = bucket_prefix + "-" + str(workload).lower()
            if "Kb" in workload:
                samples = 50
            elif "Mb" in workload:
                samples = 10
            else:
                samples = 5
            resp = s3bench.s3bench(self.access_key, self.secret_key, bucket=bucket_name,
                                   num_clients=clients,
                                   num_sample=samples, obj_name_pref="test-object-",
                                   obj_size=workload,
                                   skip_cleanup=False, duration=None, log_file_prefix=bucket_prefix)
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"

    @pytest.mark.run(order=6)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26963")
    def test_26963(self):
        """ Basic IO test
            N+K+S: 8+2+0
            CVG’s per node : 1
            Data Devices per CVG: 7
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26963")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=9)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26964")
    def test_26964(self):
        """ Basic IO test
            N+K+S: 3+2+0
            CVG’s per node : 2
            Data Devices per CVG: 3
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26964")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=13)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26967")
    def test_26967(self):
        """ Basic IO test
            N+K+S: 8+4+0
            CVG’s per node : 2
            Data Devices per CVG: 3
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26967")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=17)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26968")
    def test_26968(self):
        """ Basic IO test
            N+K+S: 10+5+0
            CVG’s per node : 2
            Data Devices per CVG: 3
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("269638")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=7)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26969")
    def test_26969(self):
        """
        S3bench IO workload test
        N+K+S: 8+2+0
        CVG’s per node : 1
        Data Devices per CVG: 7
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26969")
        self.io_workload(bucket_name)

    @pytest.mark.run(order=10)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26970")
    def test_26970(self):
        """
        S3bench IO workload test
        N+K+S: 3+2+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26970")
        self.io_workload(bucket_name)

    @pytest.mark.run(order=14)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26971")
    def test_26971(self):
        """
        S3bench IO workload test
        N+K+S: 8+4+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26971")
        self.io_workload(bucket_name)

    @pytest.mark.run(order=18)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26972")
    def test_26972(self):
        """
        S3bench IO workload test
        N+K+S: 10+5+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26972")
        self.io_workload(bucket_name)
