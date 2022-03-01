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

"""S3bench test workload suit."""

import logging
import os
import time

import pytest

from commons import commands
from commons import configmanager
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench

S3T_OBJ = S3TestLib()


class TestWorkloadS3Bench:
    """
    Test suits for S3 AWS workload
    """
    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        test_config = "config/cft/test_s3bench_workload.yaml"
        cls.cft_test_cfg = configmanager.get_config_wrapper(fpath=test_config)
        cls.setup_type = CMN_CFG["setup_type"]
        cls.bucket_name = "{}{}".format("blackboxs3bkt", time.perf_counter_ns())
        cls.object_name = "{}{}".format("blackboxs3obj", time.perf_counter_ns())
        cls.file_name = "{}{}".format("blackboxs3file", time.perf_counter_ns())
        cls.test_dir_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestAwsCliS3Api")
        if not os.path.exists(cls.test_dir_path):
            os.makedirs(cls.test_dir_path)
        cls.file_path = os.path.join(cls.test_dir_path, cls.file_name)
        cls.downloaded_file = "{}{}".format("get_blackboxs3obj", time.perf_counter_ns())
        cls.downloaded_file_path = os.path.join(cls.test_dir_path, cls.downloaded_file)
        cls.buckets_list = list()

    @pytest.mark.motr_sanity
    @pytest.mark.tags("TEST-23041")
    @CTFailOn(error_handler)
    def test_23041(self):
        """S3bench Workload test"""
        bucket_name = "test-bucket"
        if self.setup_type == "HW":
            workloads = ["4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
                         "1Mb", "4Mb", "8Mb", "16Mb", "32Mb", "64Mb", "128Mb"]
            num_sample = 40000
            num_clients = 256
        else:
            workloads = ["4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
                         "1Mb", "4Mb", "8Mb", "16Mb"]
            num_sample = 8000
            num_clients = 128
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for workload in workloads:
            resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                   num_clients=num_clients, num_sample=num_sample,
                                   obj_name_pref="s3workload_test_", obj_size=workload,
                                   skip_cleanup=False, duration=None, log_file_prefix="TEST-23041")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"

    @pytest.mark.motr_sanity
    @pytest.mark.tags("TEST-25612")
    @CTFailOn(error_handler)
    def test_download_object_from_bucket_25612(self):
        """download an object using aws cli."""
        for i in range(1, 16):
            self.log.info("Step: %d AWS upload and download Object size %d Mb", i, i)
            bucket_name = "{}{}".format("blackboxs3bkt", time.perf_counter_ns())
            resp = S3T_OBJ.create_bucket_awscli(bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            file_status, output = system_utils.create_file(fpath=self.file_path, count=i)
            assert_utils.assert_true(file_status, output)
            before_checksum = system_utils.calculate_checksum(self.file_path)
            self.log.info("File path: %s, before_checksum: %s", self.file_path, before_checksum)
            self.log.info("Uploading objects to bucket using awscli")
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                    self.file_path,
                    bucket_name,
                    self.object_name))
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(bucket_name))
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_exact_string(resp[1], self.object_name)
            self.log.info("Downloading object from bucket using awscli")
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_DOWNLOAD_OBJECT.format(
                    bucket_name,
                    self.object_name,
                    self.downloaded_file_path))
            assert_utils.assert_true(resp[0], resp[1])
            download_checksum = system_utils.calculate_checksum(
                self.downloaded_file_path)
            self.log.info("File path: %s, before_checksum: %s", self.downloaded_file_path,
                          before_checksum)
            assert_utils.assert_equals(before_checksum, download_checksum,
                                       f"Downloaded file is not same as uploaded:"
                                       f" {before_checksum}," f" {download_checksum}")
            system_utils.remove_file(self.downloaded_file_path)
            self.buckets_list.append(bucket_name)
            self.log.info("Removing object from bucket using awscli")
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_REMOVE_OBJECTS.format(
                    bucket_name,
                    self.object_name))
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Removing bucket using awscli")
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_DELETE_BUCKET.format(bucket_name))
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Successfully downloaded object from bucket using awscli")
