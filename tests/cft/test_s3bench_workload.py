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
import time
from multiprocessing import Pool

import pytest

from commons import configmanager
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY, S3H_OBJ
from scripts.s3_bench import s3bench


class TestWorkloadS3Bench:
    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        test_config = "config/cft/test_s3bench_workload.yaml"
        cls.cft_test_cfg = configmanager.get_config_wrapper(fpath=test_config)
        cls.setup_type = CMN_CFG["setup_type"]

    def execute_workload_distribution(self, test, log_file_prefix):
        """Execution given workload distribution.

        :param test: Test name for yaml config
        :param log_file_prefix: Log file prefix for s3bench
        """
        test_cfg = self.cft_test_cfg[test]
        distribution = test_cfg["workloads_distribution"]
        loops = test_cfg["loops"]
        clients = test_cfg["clients"]
        if self.setup_type == "HW":
            total_obj = 10000
        else:
            total_obj = 1000
        workloads = [(size, int(total_obj * percent / 100)) for size, percent in
                     distribution.items()]
        for loop in range(loops):
            for size, samples in workloads:
                bucket_name = f"{log_file_prefix}-bucket-{loop}-{str(int(time.time()))}".lower()
                if samples == 0:
                    continue
                if clients > samples:
                    clients = samples
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                       num_clients=clients, num_sample=samples,
                                       obj_name_pref="loadgen_test_", obj_size=size,
                                       skip_cleanup=False, duration=None,
                                       log_file_prefix=log_file_prefix, end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                self.log.info("Loop: %s Workload: %s objects of %s with %s parallel clients.",
                              loop, samples, size, clients)
                self.log.info("Log Path %s", resp[1])
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload failed in loop {loop}. Please read log file {resp[1]}"

    @pytest.mark.longevity
    @pytest.mark.tags("TEST-19658")
    def test_19658(self):
        """Longevity Test with distributed workload."""
        self.execute_workload_distribution("test_19658", "TEST-19658")

    @pytest.mark.lc
    @pytest.mark.s3_data_path
    @pytest.mark.tags("TEST-39216")
    def test_distributed_workload_39216(self):
        """IO test with distributed workload."""
        self.execute_workload_distribution("test_39216", "TEST-39216")

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
                                   skip_cleanup=False, duration=None, log_file_prefix="TEST-19471",
                                   end_point=S3_CFG["s3_url"],
                                   validate_certs=S3_CFG["validate_certs"])
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
        access_key, secret_key = S3H_OBJ.get_local_keys()
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
            resp = s3bench.s3bench(access_key, secret_key, bucket=bucket_name, num_clients=clients,
                                   num_sample=samples, obj_name_pref="test-object-",
                                   obj_size=workload, end_point=S3_CFG["s3_url"],
                                   skip_cleanup=False, duration=None, log_file_prefix="TEST-24673",
                                   validate_certs=S3_CFG["validate_certs"])
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
        access_key, secret_key = S3H_OBJ.get_local_keys()

        self.log.info("Perform Write Operation on Bucket %s", bucket_name)
        self.log.info("Workload: %s objects of %s with %s parallel clients.", samples, size,
                      clients)
        resp = s3bench.s3bench(access_key, secret_key, bucket=bucket_name,
                               num_clients=clients, num_sample=samples,
                               obj_name_pref="test_25016", obj_size=size,
                               skip_cleanup=True, duration=None,
                               log_file_prefix="test_25016", end_point=S3_CFG["s3_url"],
                               validate_certs=S3_CFG["validate_certs"])
        assert not s3bench.check_log_file_error(resp[1]), f"S3bench write failed for {bucket_name}"

        self.log.info("Perform Read Operation in Loop on Bucket :%s", bucket_name)
        for loop in range(read_loops):
            self.log.info(
                "Loop: %s Workload: %s objects of %s with %s parallel "
                "clients.", loop, samples, size, clients)
            skip_cleanup = True
            if loop == read_loops - 1:
                skip_cleanup = False
            resp = s3bench.s3bench(access_key, secret_key, bucket=bucket_name,
                                   num_clients=clients, num_sample=samples,
                                   obj_name_pref="test_25016", obj_size=size, skip_write=True,
                                   skip_cleanup=skip_cleanup, duration=None,
                                   log_file_prefix="test_25016", end_point=S3_CFG["s3_url"],
                                   validate_certs=S3_CFG["validate_certs"])
            self.log.info("Log Path %s", resp[1])
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for failed in loop {loop}. Please read log file {resp[1]}"

    @pytest.mark.tags("TEST-28376")
    @pytest.mark.scalability
    def test_28376(self):
        """Parallel S3bench workloads on multiple buckets"""
        self.log.info("Started: Parallel S3bench workloads on multiple buckets")
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        pool = Pool(processes=3)
        buckets = [f"test-28991-bucket-{i}-{str(int(time.time()))}" for i in range(3)]
        e_point = S3_CFG["s3_url"]
        validate_certs = S3_CFG["validate_certs"]
        pool.starmap(s3bench.s3bench_workload,
                     [(e_point, buckets[0], "TEST-28376", "2Mb", 32, 400, ACCESS_KEY, SECRET_KEY,
                       validate_certs),
                      (e_point, buckets[1], "TEST-28376", "2Mb", 32, 400, ACCESS_KEY, SECRET_KEY,
                       validate_certs),
                      (e_point, buckets[2], "TEST-28376", "2Mb", 32, 400, ACCESS_KEY, SECRET_KEY,
                       validate_certs)])
        self.log.info("Completed: Parallel S3bench workloads on multiple buckets")

    @pytest.mark.tags("TEST-28377")
    @pytest.mark.scalability
    def test_28377(self):
        """S3bench workloads with varying object size and varying clients"""
        self.log.info("Started: S3bench workloads with varying object size and varying clients")
        bucket_prefix = "test-bucket"
        object_sizes = [
            "1Kb", "4Kb", "16Kb", "64Kb", "256Kb",
            "1Mb", "5Mb", "20Mb", "64Mb", "128Mb", "256Mb", "512Mb"
        ]
        clients = [64, 128, 256]
        sample = 1024
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for object_size in object_sizes:
            for client in clients:
                self.log.info("Workload: 1024 objects of %s with %s parallel clients",
                              object_size, client)
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY,
                                       bucket=f"{bucket_prefix}-{object_size.lower()}-{client}",
                                       num_clients=client, num_sample=sample,
                                       obj_name_pref="loadgen_test_", obj_size=object_size,
                                       skip_cleanup=False, duration=None,
                                       log_file_prefix="TEST-28377", end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                self.log.info(f"json_resp {resp[0]}\n Log Path {resp[1]}")
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload for object size {object_size} with client {client} failed." \
                    f" Please read log file {resp[1]}"
        self.log.info("Completed: S3bench workloads with varying object size and varying clients")
