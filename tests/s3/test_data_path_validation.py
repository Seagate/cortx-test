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

"""Data Path validation tests module."""

import os
import logging
from time import perf_counter_ns

import pytest
from commons import commands as cmd
from commons.constants import const
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from commons.helpers.health_helper import Health
from config import CMN_CFG as CM_CFG
from config.s3 import S3_CFG
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench as s3bench_obj


class TestDataPathValidation:
    """Data Path Test suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        perform the cleanup.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.obj_prefix = "dpv-obj"
        self.bkt_name_prefix = "dpv-bkt"
        self.bucket_name = "dpv-bkt{}".format(perf_counter_ns())
        self.object_name = "dpv-obj{}".format(perf_counter_ns())
        self.cmd_msg = "core."
        self.log_file = []
        self.nodes = CM_CFG["nodes"]
        self.health_obj = Health(hostname=self.nodes[0]["hostname"],
                                 username=self.nodes[0]["username"],
                                 password=self.nodes[0]["password"])
        self.test_file = "bkt-dp{}.txt".format(perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestDataPathValidation")
        self.file_path = os.path.join(self.test_dir_path, self.test_file)
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("Test file path: %s", self.file_path)
        self.log.info("Check s3 bench tool installed.")
        res = system_utils.path_exists(s3bench_obj.S3_BENCH_PATH)
        assert_utils.assert_true(
            res, f"S3bench tools not installed: {s3bench_obj.S3_BENCH_PATH}")
        self.access_key, self.secret_key = S3H_OBJ.get_local_keys()
        self.log.info("ENDED: Setup operations")
        yield
        self.log.info("STARTED: Teardown operations")
        self.log.info("Deleting files created during execution")
        self.log_file.append(self.file_path)
        for file in self.log_file:
            if os.path.exists(file):
                system_utils.remove_file(file)
        self.log.info("Created files deleted")
        self.log.info("Delete bucket and it's resources.")
        resp = self.s3_obj.bucket_list()
        if self.bucket_name in resp[1]:
            resp = self.s3_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted bucket and it's resources.")
        self.log.info("ENDED: Teardown operations")

    def create_bucket(self, bkt_name):
        """
        create a new bucket.

        :param bkt_name: bucket ame
        :return: bucket_name
        """
        self.log.info("Step 1: Prepare fresh setup with EES/EOS stack")
        self.log.info("Step 2: Creating a bucket with name : %s", bkt_name)
        res = self.s3_obj.create_bucket(bkt_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_in(bkt_name, res[1], res)

        return bkt_name

    def put_object(self, object_name, bucket_name, obj_size, b_size):
        """
        upload a given size object in already created bucket.

        :param obj_size: object size
        :param object_name: NAme of object
        :param bucket_name: bucket in which object need to be uploaded
        :param b_size: block size.
        """
        self.log.info("Create file and upload object %s.", object_name)
        cmd_create_file = cmd.CREATE_FILE.format(
            "/dev/zero", self.file_path, b_size, obj_size)
        resp = system_utils.run_local_cmd(cmd_create_file)
        self.log.info(resp)
        assert_utils.assert_true(os.path.exists(self.file_path), resp)
        res = self.s3_obj.object_upload(bucket_name,
                                        object_name,
                                        self.file_path)
        assert_utils.assert_true(res[0], res[1])
        resp = self.s3_obj.object_list(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            object_name,
            resp[1],
            f"Failed to upload object {object_name}")

    def run_s3bench(self, obj_prefix, bucket):
        """
        concurrent users operations using S3bench.

        yum install go
        go get github.com/igneous-systems/s3bench
        git clone https://github.com/igneous-systems/s3bench at /root/go/src/
        :param obj_prefix: object prefix
        :param bucket: already created bucket name
        :type bucket: str
        :return: None
        """
        self.log.info("concurrent users TC using S3bench")
        res = s3bench_obj.s3bench(
            access_key=self.access_key,
            secret_key=self.secret_key,
            bucket=bucket,
            end_point=S3_CFG['s3_url'],
            num_clients=100,
            num_sample=100,
            obj_name_pref=obj_prefix,
            obj_size="4Kb",
            log_file_prefix=obj_prefix,
            validate_certs=S3_CFG["validate_certs"])
        self.log.debug(res)
        self.log_file.append(res[1])
        resp = system_utils.validate_s3bench_parallel_execution(
            log_dir=s3bench_obj.LOG_DIR, log_prefix=obj_prefix)
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-8735')
    @pytest.mark.parametrize("obj_size, block_size", [(1, 1)])
    def test_1696(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 1 byte object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with object size %s byte",
            obj_size)
        bucket = self.create_bucket(self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, b_size=block_size)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with object size %s byte",
            obj_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-8736')
    @pytest.mark.parametrize("obj_size, block_size", [(1000, 1)])
    def test_1697(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 1 KB object size."""
        self.test_1696(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-8737')
    @pytest.mark.parametrize("obj_size, block_size", [(1, "1M")])
    def test_1698(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 1 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with object size %s MB",
            obj_size)
        bucket = self.create_bucket(self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, b_size=block_size)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with object size %s MB",
            obj_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-8738')
    @pytest.mark.parametrize("obj_size, block_size", [(10, "1M")])
    def test_1699(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 10 MB object size."""
        self.test_1698(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-8739')
    @pytest.mark.parametrize("obj_size, block_size", [(100, "1M")])
    def test_1700(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 100 MB object size."""
        self.test_1698(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-8740')
    @pytest.mark.parametrize("obj_size, block_size", [(1000, "1M")])
    def test_1701(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 1 GB object size."""
        self.test_1698(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8741')
    @pytest.mark.parametrize("obj_size, block_size", [(10000, "1M")])
    def test_1702(self, obj_size, block_size):
        """Validate Data-Path on fresh system with 10 GB object size."""
        self.test_1698(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8742')
    @pytest.mark.parametrize("obj_size, block_size", [(1, 1)])
    def test_1703(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 1 byte object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with object size %s byte",
            obj_size)
        bucket = self.create_bucket(self.bucket_name)
        self.run_s3bench(self.obj_prefix, self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, b_size=block_size)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with object size %s byte",
            obj_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8743')
    @pytest.mark.parametrize("obj_size, block_size", [(1000, 1)])
    def test_1704(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 1 KB object size."""
        self.test_1703(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8744')
    @pytest.mark.parametrize("obj_size, block_size", [(1, "1M")])
    def test_1705(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 1 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with object size %s MB",
            obj_size)
        bucket = self.create_bucket(self.bucket_name)
        self.run_s3bench(self.obj_prefix, self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, b_size=block_size)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with object size %s MB",
            obj_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8745')
    @pytest.mark.parametrize("obj_size, block_size", [(10, "1M")])
    def test_1706(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 10 MB object size."""
        self.test_1705(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8746')
    @pytest.mark.parametrize("obj_size, block_size", [(100, "1M")])
    def test_1707(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 100 MB object size."""
        self.test_1705(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8729')
    @pytest.mark.parametrize("obj_size, block_size", [(1000, "1M")])
    def test_1708(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 1 GB object size."""
        self.test_1705(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8730')
    @pytest.mark.parametrize("obj_size, block_size", [(10000, "1M")])
    def test_1709(self, obj_size, block_size):
        """Validate Data-Path on loaded system with 10 GB object size."""
        self.test_1705(obj_size, block_size)

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8731')
    @pytest.mark.parametrize("obj_size, requests",
                             [("8Mb", [100, 500, 1200, 1500])])
    def test_1745(self, obj_size, requests):
        """Gradual increase of concurrent client sessions with single client on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with single client on single bucket")
        self.log.info("obj_size: %s, requests: %s", obj_size, requests)
        self.log.info("Step 1: Create bucket with name %s.", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.bucket_list()
        assert_utils.assert_in(self.bucket_name, resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with 100 client and "
            "gradually increase request.")
        for request_load in requests:
            self.log.info("I/O with %s request", request_load)
            res = s3bench_obj.s3bench(
                access_key=self.access_key,
                secret_key=self.secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG["s3_url"],
                num_clients=1,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                log_file_prefix=f"TEST-8731_s3bench_{request_load}",
                validate_certs=S3_CFG["validate_certs"])
            self.log.debug(res)
            resp = system_utils.validate_s3bench_parallel_execution(
                s3bench_obj.LOG_DIR, f"TEST-8731_s3bench_{request_load}")
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Successfully performed concurrent I/O with 100 client and"
            "gradually increasing requests.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_utils.assert_true(
            res, f"Failed to check is motr online: resp: {res}")
        for crash_cmd in const.CRASH_COMMANDS[0]:
            for nid in range(len(self.nodes)):
                res_cmd = system_utils.run_remote_cmd(
                    crash_cmd,
                    CM_CFG["nodes"][nid]["hostname"],
                    CM_CFG["nodes"][nid]["username"],
                    CM_CFG["nodes"][nid]["password"])
                assert_utils.assert_not_in(self.cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with single client on single bucket")

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8732')
    @pytest.mark.parametrize("obj_size, requests, num_clients",
                             [("8Mb", [10, 50, 100, 500], [10, 10, 12, 20])])
    def test_1746(self, obj_size, requests, num_clients):
        """Gradual increase of concurrent client sessions with multiple clients on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
        self.log.info(
            "obj_size: %s, requests: %s, num_clients: %s",
            obj_size,
            requests,
            num_clients)
        self.log.info("Step 1: Create bucket with name %s.", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.bucket_list()
        assert_utils.assert_in(self.bucket_name, resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with multiple client increasing "
            "request on single bucket.")
        for client, request_load in zip(num_clients, requests):
            res = s3bench_obj.s3bench(
                access_key=self.access_key,
                secret_key=self.secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG["s3_url"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                log_file_prefix=f"TEST-8732_s3bench_{request_load}",
                validate_certs=S3_CFG["validate_certs"])
            self.log.debug(res)
            resp = system_utils.validate_s3bench_parallel_execution(
                s3bench_obj.LOG_DIR, f"TEST-8732_s3bench_{request_load}")
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: completed concurrent I/O with multiple client and increasing"
            " request on single bucket.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_utils.assert_true(
            res, f"Failed to check is_motr_online: resp: {res}")
        self.log.info("Crash commands: %s", const.CRASH_COMMANDS[0])
        for crash_cmd in const.CRASH_COMMANDS[0]:
            self.log.info(cmd)
            for nid in range(len(self.nodes)):
                res_cmd = system_utils.run_remote_cmd(
                    crash_cmd,
                    CM_CFG["nodes"][nid]["hostname"],
                    CM_CFG["nodes"][nid]["username"],
                    CM_CFG["nodes"][nid]["password"])
                assert_utils.assert_not_in(self.cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8733')
    @pytest.mark.parametrize("obj_size, requests, num_clients",
                             [("8Mb", [100, 100, 100, 200], [1, 2, 3, 4])])
    def test_1747(self, obj_size, requests, num_clients):
        """Gradual increase of concurrent client sessions with multiple clients on buckets."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on multiple buckets")
        self.log.info(
            "obj_size: %s, requests: %s, num_clients: %s",
            obj_size,
            requests,
            num_clients)
        self.log.info("Step 1: Creating %s buckets.", 5)
        bkt_list = []
        for bkt in range(5):
            bucket_name = "{}{}".format(
                self.bkt_name_prefix, perf_counter_ns())
            resp = self.s3_obj.create_bucket(bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = self.s3_obj.bucket_list()
        for bkt in bkt_list:
            assert_utils.assert_in(
                bkt, resp[1], f"Failed to create bucket: {bkt} in {resp[1]}")
        self.log.info("Step 1: Successfully created buckets: %s.", bkt_list)
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and "
            "request on multiple buckets.")
        for client, request_load, bkt in zip(num_clients, requests, bkt_list):
            s3bench_obj.s3bench(
                access_key=self.access_key,
                secret_key=self.secret_key,
                bucket=bkt,
                end_point=S3_CFG["s3_url"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                log_file_prefix=f"TEST-8733_s3bench_{request_load}",
                validate_certs=S3_CFG["validate_certs"])
            resp = system_utils.validate_s3bench_parallel_execution(
                s3bench_obj.LOG_DIR, f"TEST-8733_s3bench_{request_load}")
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Completed concurrent I/O with increasing client and"
            " request on multiple buckets.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_utils.assert_true(
            res, f"Failed to check is_motr_online: resp: {res}")
        for crash_cmd in const.CRASH_COMMANDS[0]:
            for nid in range(len(self.nodes)):
                res_cmd = system_utils.run_remote_cmd(
                    crash_cmd,
                    CM_CFG["nodes"][nid]["hostname"],
                    CM_CFG["nodes"][nid]["username"],
                    CM_CFG["nodes"][nid]["password"])
                assert_utils.assert_not_in(self.cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        if bkt_list:
            resp = self.s3_obj.delete_multiple_buckets(bkt_list)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on multiple buckets")

    @pytest.mark.s3_ops
    @pytest.mark.s3_data_path
    @pytest.mark.tags('TEST-8734')
    @pytest.mark.parametrize("obj_size, requests, num_clients",
                             [("8Mb", [120, 150], [10, 2])])
    def test_1748(self, obj_size, requests, num_clients):
        """Test burst I/O with single client on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
        self.log.info(
            "obj_size: %s, requests: %s, num_clients: %s",
            obj_size,
            requests,
            num_clients)
        self.log.info("Step 1: Create bucket.")
        bkt_list = []
        for bkt in range(2):
            bucket_name = "{}{}".format(
                self.bkt_name_prefix, perf_counter_ns())
            resp = self.s3_obj.create_bucket(bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = self.s3_obj.bucket_list()
        for bkt in bkt_list:
            assert_utils.assert_in(
                bkt, resp[1], f"Failed to create bucket: {bkt} in {resp[1]}")
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and request.")
        for client, request_load, bkt in zip(num_clients, requests, bkt_list):
            s3bench_obj.s3bench(
                access_key=self.access_key,
                secret_key=self.secret_key,
                bucket=bkt,
                end_point=S3_CFG["s3_url"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                log_file_prefix=f"TEST-8734_s3bench_{request_load}",
                validate_certs=S3_CFG["validate_certs"])
            resp = system_utils.validate_s3bench_parallel_execution(
                s3bench_obj.LOG_DIR, f"TEST-8734_s3bench_{request_load}")
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and request.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_utils.assert_true(
            res, f"Failed to check is_motr_online: resp: {res}")
        for crash_cmd in const.CRASH_COMMANDS[0]:
            for nid in range(len(self.nodes)):
                res_cmd = system_utils.run_remote_cmd(
                    crash_cmd,
                    CM_CFG["nodes"][nid]["hostname"],
                    CM_CFG["nodes"][nid]["username"],
                    CM_CFG["nodes"][nid]["password"])
                assert_utils.assert_not_in(self.cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        if bkt_list:
            resp = self.s3_obj.delete_multiple_buckets(bkt_list)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
