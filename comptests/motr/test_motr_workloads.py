# -*- coding: utf-8 -*-
# !/usr/bin/python
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

import pytest
import logging
from commons.ct_fail_on import CTFailOn
from libs.motr import motr_test_lib, WORKLOAD_CFG
from commons.errorcodes import error_handler
from commons.utils import system_utils, assert_utils
from config import CMN_CFG
from commons import commands

LOGGER = logging.getLogger(__name__)

class TestExecuteWorkload:
    """Execute Workload Test suite"""

    @pytest.yield_fixture(autouse=True)
    def setup(self):
        LOGGER.info("STARTED: Setup Operation")
        self.workload_config = WORKLOAD_CFG[1]
        self.motr_obj = motr_test_lib.MotrTestLib()
        self.host_list = self.motr_obj.host_list
        self.uname_list = self.motr_obj.uname_list
        self.passwd_list = self.motr_obj.passwd_list
        self.last_endpoint = None
        LOGGER.info("ENDED: Setup Operation")

        yield
        #Perform the clean up for each test.

        LOGGER.info("STARTED: Teardown Operation")
        LOGGER.info("Deleting temp files on node")
        self.motr_obj.delete_remote_files()
        LOGGER.info("ENDED: Teardown Operation")

    def get_batches_runs(self, tc_num):
        batch_list = self.workload_config["workloads"][tc_num]["batch"]
        runs = self.workload_config["workloads"][tc_num]["runs"]
        return batch_list, runs

    @CTFailOn(error_handler)
    def execute_test(self, tc_num):
        batches, runs = self.get_batches_runs(tc_num)
        LOGGER.info(f' batches: "{batches}", runs: "{runs}"')
        for run in range(runs):
            LOGGER.info(f'Executing run {run + 1}:')
            for index, cnt in enumerate(batches):
                cmd = self.motr_obj.get_command_str(batches[index])
                if cmd:
                    LOGGER.info(f'Step {index + 1}: Executing command - "{cmd}"')
                    result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.host_list[0], self.uname_list[0], self.passwd_list[0])
                    if ret:
                        LOGGER.error(f'"{cmd}" failed, please check the log')
                        assert False
                    if (b"ERROR" or b"Error") in error1:
                        LOGGER.error(f'"{cmd}" failed, please check the log')
                        assert_not_in(error1, b"ERROR" or b"Error", '"{cmd}" Failed, Please check the log')
                    LOGGER.info(f"{result},{error1}")

    @pytest.mark.tags("TEST-14882")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14882(self):
        """
        Verify m0cp, m0trunc and m0crate utilities
        """
        LOGGER.info("STARTED: Verify m0cp, m0trunc and m0crate utilities")
        self.execute_test('test_14882')
        LOGGER.info("ENDED: Verify m0cp, m0trunc and m0crate utilities")

    @pytest.mark.tags("TEST-14921")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14921(self):
        """
        Execute m0kv and m0crate utilities
        """
        LOGGER.info("Start: Verify m0kv and m0crate utilities")
        self.execute_test('test_14921')
        LOGGER.info("Stop: Verify m0kv and m0crate utilities")

    @pytest.mark.tags("TEST-14922")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14922(self):
        """
        Execute m0crate workload - 2G with starting object 10:10
        """
        LOGGER.info("Start: Execute m0crate workload - 2G with Starting object 10:10")
        self.execute_test('test_14922')
        LOGGER.info("Stop: Done execution of m0crate workload - 2G with Starting object 10:10")

    @pytest.mark.tags("TEST-14923")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14923(self):
        """
        Execute m0crate workload - 2G with starting object 40:40
        """
        LOGGER.info("Start: Execute m0crate workload - 2G with Starting object 40:40")
        self.execute_test('test_14923')
        LOGGER.info("Stop: Done execution m0crate workload - 2G with Starting object 40:40")

    @pytest.mark.tags("TEST-14924")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14924(self):
        """
        Verify KV operations using m0crate
        """
        LOGGER.info("Start: Verify KV operations using m0crate")
        self.execute_test('test_14924')
        LOGGER.info("Stop: Verify KV operations using m0crate")

    @pytest.mark.tags("TEST-14925")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14925(self):
        """
        execute m0crate workload
        """
        LOGGER.info("Start: execute m0crate workload with different opcode")
        self.execute_test('test_14925')
        LOGGER.info("Stop: execution of m0crate workload")

    @pytest.mark.tags("TEST-14926")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14926(self):
        """
        execute m0crate workload
        """
        LOGGER.info("Start: execute m0crate workload with different opcode")
        self.execute_test('test_14926')
        LOGGER.info("Stop: Done execution of m0crate workload")

    @pytest.mark.tags("TEST-22939")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_22939(self):
        """
        execute m0crate workload - nbjects_10 nthreads_10 block_size_2m
        """
        LOGGER.info("Start: execute m0crate workload - nbjects_10 nthreads_10 block_size_2m")
        self.execute_test('test_22939')
        LOGGER.info("Stop: execute m0crate workload - nbjects_10 nthreads_10 block_size_2m")

    @pytest.mark.tags("TEST-22954")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_22954(self):
        """
        Verify IO path with nobjects_10_nthreads_10 for 4m block size.
        """
        LOGGER.info("Start: Verify IO path with nobjects_10_nthreads_10 for 4m block size.")
        self.execute_test('test_22954')
        LOGGER.info("Stop: Verify IO path with nobjects_10_nthreads_10 for 4m block size.")

    @pytest.mark.tags("TEST-23191")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23191(self):
        """
        Verify KV operations using m0crate
        """
        LOGGER.info("Start: Verify IO path with nobjects_10_nthreads_10 for 8m block size")
        self.execute_test('test_23191')
        LOGGER.info("Stop: Verify IO path with nobjects_10_nthreads_10 for 8m block size")

    @pytest.mark.tags("TEST-23192")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23192(self):
        """
        Verify IO path with nobjects_10_nthreads_10 for 16m block size.
        """
        LOGGER.info("Start: Verify IO path with nobjects_10_nthreads_10 for 16m block size.")
        self.execute_test('test_23192')
        LOGGER.info("Stop: Verify IO path with nobjects_10_nthreads_10 for 16m block size.")

    @pytest.mark.tags("TEST-23193")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23193(self):
        """
        Verify IO path with nobjects_10_nthreads_10 for 32m block size.
        """
        LOGGER.info("Start: Verify IO path with nobjects_10_nthreads_10 for 32m block size.")
        self.execute_test('test_23193')
        LOGGER.info("Stop: Verify IO path with nobjects_10_nthreads_10 for 32m block size.")

    @pytest.mark.tags("TEST-23194")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23194(self):
        """
        Verify IO path with nobjects_10_nthreads_10 for 64m block size.
        """
        LOGGER.info("Start: Verify IO path with nobjects_10_nthreads_10 for 64m block size.")
        self.execute_test('test_23194')
        LOGGER.info("Stop: Verify IO path with nobjects_10_nthreads_10 for 64m block size.")

    @pytest.mark.tags("TEST-23195")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23195(self):
        """
        Verify IO path with nobjects_10_nthreads_10 for 128m block size.
        """
        LOGGER.info("Start: Verify IO path with nobjects_10_nthreads_10 for 128m block size.")
        self.execute_test('test_23195')
        LOGGER.info("Stop: Verify IO path with nobjects_10_nthreads_10 for 128m block size.")

    @pytest.mark.tags("TEST-23196")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23196(self):
        """
        Verify Object creation and then write and read test on the same
        """
        LOGGER.info("Start: Verify Object creation and then write and read test on the same")
        self.execute_test('test_23196')
        LOGGER.info("Stop: Verify Object creation and then write and read test on the same")

    @pytest.mark.tags("TEST-23197")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23197(self):
        """
        Test Data Integrity during Write (m0cp) & Read (m0cat) object operation.
        """
        LOGGER.info("Start: Test Data Integrity during Write (m0cp) & Read (m0cat) object operation.")
        self.execute_test('test_23197')
        LOGGER.info("Stop: Test Data Integrity during Write (m0cp) & Read (m0cat) object operation.")

    @pytest.mark.tags("TEST-23198")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23198(self):
        """
        Verify m0kv command (for motr meta data) to generate file with several FID using option "genf"
        """
        LOGGER.info("Start: Verify m0kv command to generate file with several FID using option genf")
        self.execute_test('test_23198')
        LOGGER.info("Stop: Verify m0kv command to generate file with several FID using option genf")

    @pytest.mark.tags("TEST-23199")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23199(self):
        """
        Verify motr meta data using the m0kv command to create index using single FID using option "index create"
        """
        LOGGER.info("Start: Verify motr meta data using the m0kv command to create index using single FID using option index create")
        self.execute_test('test_23199')
        LOGGER.info("Stop: Verify motr meta data using the m0kv command to create index using single FID using option index create")

    @pytest.mark.tags("TEST-23200")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23200(self):
        """
        Verify the motr meta data using m0kv command to list existing single index using option index list
        """
        LOGGER.info("Start: Verify the motr meta data using m0kv command to list existing single index using option index list")
        self.execute_test('test_23200')
        LOGGER.info("Stop: Verify the motr meta data using m0kv command to list existing single index using option index list")

    @pytest.mark.tags("TEST-23202")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23202(self):
        """
        Verify motr meta data using the m0kv command to lookup multiple index in storage using option index lookup
        """
        LOGGER.info("Start: Verify motr meta data using the m0kv command to lookup multiple index in storage using option index lookup")
        self.execute_test('test_23202')
        LOGGER.info("Stop: Verify motr meta data using the m0kv command to lookup multiple index in storage using option index lookup")

    @pytest.mark.tags("TEST-23203")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23203(self):
        """
        Verify motr meta data using the m0kv command to drop existing index using option index drop
        """
        LOGGER.info("Start: Verify motr meta data using the m0kv command to drop existing index using option index drop")
        self.execute_test('test_23203')
        LOGGER.info("Stop: Verify motr meta data using the m0kv command to drop existing index using option index drop")

    @pytest.mark.tags("TEST-14954")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_14954(self):
        """
        Verify truncate Motr object to a given size
        """
        LOGGER.info("Start: Verify truncate Motr object to a given size with options")
        self.execute_test('test_14954')
        LOGGER.info("Stop: Verify truncate Motr object to a given size with options")

    @pytest.mark.tags("TEST-23205")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23205(self):
        """
        Verify the object deletion from the motr using command m0unlink
        """
        LOGGER.info("Start: Verify the object deletion from the motr using command m0unlink")
        self.execute_test('test_23205')
        LOGGER.info("Stop: Verify the object deletion from the motr using command m0unlink")

    @pytest.mark.tags("TEST-23207")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23207(self):
        """
        Verify object update operation
        """
        LOGGER.info("Start: Verify object update operation")
        self.execute_test('test_23207')
        LOGGER.info("Stop: Verify object update operation")


    @pytest.mark.tags("TEST-23036")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_23036(self):
        """
        Verify different size object m0cp m0cat operation
        """
        LOGGER.info("Start: Verify multiple m0cp/cat operation")
        infile = '/tmp/input'
        outfile = '/tmp/output'
        for j, host in enumerate(self.host_list):
            ret = self.motr_obj.get_cluster_info(host)
            assert_utils.assert_true(ret, "Not able to Fetch cluster INFO. Please check cluster status")
            i = 1
            l, H, P, p = self.motr_obj.get_endpoints(host)
            if self.last_endpoint == l:
                LOGGER.info("Looks like cluster is not fully deployed. Exiting")
                break
            bsize = ['4K', '4K', '4K', '8K', '16K', '64K', '64K', '128K', '4K', '1M', '1M', '4M', '4M', '4M', '4M', '16M',
                     '1M']
            size = ['4k', '4k', '4k', '8k', '16k', '64k', '64k', '128k', '4k', '1m', '1m', '4m', '4m', '4m', '4m', '16m',
                    '1m']
            count = ['1', '2', '4', '4', '4', '2', '4', '4', '250', '2', '4', '2', '3', '4', '8', '4', '1024']
            layout = ['1', '1', '1', '2', '3', '5', '5', '6', '1', '9', '9', '11', '11', '11', '11', '11', '13']
            self.last_endpoint = l
            for bs, s, c, L in zip(bsize, size, count, layout):
                o = str(i) + ":" + str(i)
                ddCmd = commands.CREATE_FILE.format("/dev/urandom", infile, bs, c)
                cpCmd = commands.M0CP.format(l, H, P, p, s, c, o, L, infile)
                catCmd = commands.M0CAT.format(l, H, P, p, s, c, o, L, outfile)
                diffCmd = commands.DIFF.format(infile, outfile)
                mdCmd = commands.MD5SUM.format(infile, outfile)
                unlinkCmd = commands.M0UNLINK.format(l, H, P, p, o, L)
                i = i + 1
                index = i
                batch = [ddCmd, cpCmd, catCmd, diffCmd, mdCmd, unlinkCmd]
                for cmd in batch:
                    if cmd:
                        LOGGER.info(f'Step {index + 1}: Executing command - "{cmd}"')
                        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd, self.host_list[j], self.uname_list[j],
                                                                                      self.passwd_list[j])
                        LOGGER.info(f"{result},{error1}")
                        if ret:
                           LOGGER.info(f'"{cmd}" Failed, Please check the log')
                           assert False
                        if (b"ERROR" or b"Error") in error1:
                           LOGGER.error(f'"{cmd}" failed, please check the log')
                           assert_utils.assert_not_in(error1, b"ERROR" or b"Error", '"{cmd}" Failed, Please check the log')
            LOGGER.info("Stop: Verify multiple m0cp/cat operation")

    @pytest.mark.tags("TEST-22963")
    @pytest.mark.motr_io_load
    @CTFailOn(error_handler)
    def test_22963(self):
        """
        Verify Libfabric is presented on system and basic ping pong operation
        """
        LOGGER.info("Start: Verify object update operation")
        self.motr_obj.verify_libfabric_version()
        self.motr_obj.fi_ping_pong()
        LOGGER.info("Stop: Verify object update operation")

