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

"""S3bench test workload suit."""
import logging

import pytest

from commons import configmanager
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.s3_bench import s3bench
from config import CMN_CFG


class TestWorkloadS3Bench:
    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        test_config = "config/cft/test_s3bench_workload.yaml"
        cls.cft_test_cfg = configmanager.get_config_wrapper(fpath=test_config)
        cls.setup_type = CMN_CFG["setup_type"]

    @pytest.mark.longevity
    @pytest.mark.tags("TEST-19658")
    def test_19658(self):
        """Longevity Test with distributed workload"""
        test_cfg = self.cft_test_cfg["test_12345"]
        distribution = test_cfg["workloads_distribution"]
        if self.setup_type == "HW":
            total_obj = 10000
        else:
            total_obj = 1000
        loops = test_cfg["loops"]
        clients = test_cfg["clients"]
        bucket_name = "test-bucket"
        workloads = [(size, int(total_obj * percent / 100)) for size, percent in
                     distribution.items()]
        resp = s3bench.setup_s3bench()
        assert resp, "Could not setup s3bench."

        for loop in range(loops):
            for size, samples in workloads:
                if samples == 0:
                    continue
                if clients > samples:
                    clients = samples
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                       num_clients=clients, num_sample=samples,
                                       obj_name_pref="loadgen_test_", obj_size=size,
                                       skip_cleanup=False, duration=None,
                                       log_file_prefix="TEST-19658")
                self.log.info(
                    f"Loop: {loop} Workload: {samples} objects of {size} with {clients} parallel "
                    f"clients.")
                self.log.info(f"Log Path {resp[1]}")
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload for failed in loop {loop}. Please read log file {resp[1]}"

    @pytest.mark.scalability
    @pytest.mark.tags("TEST-19471")
    def test_19471(self):
        """S3bench Workload test"""
        bucket_name = "test-bucket"
        workloads = [
            "1Kb", "4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
            "1Mb", "4Mb", "8Mb", "16Mb", "32Mb", "64Mb", "128Mb", "256Mb", "512Mb", "1Gb"
        ]
        if self.setup_type == "HW":
            workloads.extend(["4Gb", "8Gb", "16Gb"])
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for workload in workloads:
            resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name, num_clients=1,
                                   num_sample=5, obj_name_pref="loadgen_test_", obj_size=workload,
                                   skip_cleanup=False, duration=None, log_file_prefix="TEST-19471")
            self.log.info(f"json_resp {resp[0]}\n Log Path {resp[1]}")
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"

    @pytest.mark.run(order=2)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-24673")
    def test_24673(self):
        """S3bench Workload test - Sanity check"""
        test_cfg = self.cft_test_cfg["test_24673"]
        bucket_prefix = "test-bucket-24673"
        workloads = [
            "1Kb", "4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
            "1Mb", "4Mb", "8Mb", "16Mb", "32Mb", "64Mb", "128Mb", "256Mb", "512Mb", "1Gb", "2Gb"
        ]
        clients = test_cfg["clients"]
        if self.setup_type == "HW":
            workloads.extend(["4Gb", "8Gb", "16Gb"])
            clients = clients * 5
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for workload in workloads:
            bucket_name = bucket_prefix + "-" + str(workload).lower()
            if "Kb" in workload:
                samples = 500
            elif "Mb" in workload:
                samples = 50
            else:
                samples = 20
            if self.setup_type == "HW":
                samples = samples * 5
            resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name, num_clients=clients,
                                   num_sample=samples, obj_name_pref="test-object-",
                                   obj_size=workload,
                                   skip_cleanup=False, duration=None, log_file_prefix="TEST-24673")
            self.log.info(f"json_resp {resp[0]}\n Log Path {resp[1]}")
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"

    @pytest.mark.run(order=3)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-25016")
    def test_25016(self):
        """S3bench Workload test - Sanity check - Long running Read Operations"""
        test_cfg = self.cft_test_cfg["test_25016"]
        samples = test_cfg["samples"]
        read_loops = test_cfg["read_loops"]
        clients = test_cfg["clients"]
        size = test_cfg["object_size"]
        bucket_name = "test-bucket-25016"
        resp = s3bench.setup_s3bench()
        assert resp, "Could not setup s3bench."

        self.log.info(f"Perform Write Operation on Bucket {bucket_name}:")
        self.log.info(f"Workload: {samples} objects of {size} with {clients} parallel clients.")
        resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                               num_clients=clients, num_sample=samples,
                               obj_name_pref="test_25016", obj_size=size,
                               skip_cleanup=True, duration=None,
                               log_file_prefix="test_25016")

        self.log.info(f"Perform Read Operation in Loop on Bucket {bucket_name}:")
        for loop in range(read_loops):
            self.log.info(
                f"Loop: {loop} Workload: {samples} objects of {size} with {clients} parallel "
                f"clients.")
            skip_cleanup = True
            if loop == read_loops - 1:
                skip_cleanup = False
            resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                   num_clients=clients, num_sample=samples,
                                   obj_name_pref="test_25016", obj_size=size, skip_write=True,
                                   skip_cleanup=skip_cleanup, duration=None,
                                   log_file_prefix="test_25016")
            self.log.info(f"Log Path {resp[1]}")
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for failed in loop {loop}. Please read log file {resp[1]}"
