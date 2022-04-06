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
#

"""S3 Bench Unit Tests."""
import logging
import shutil
import os
import unittest
import sys
from scripts.s3_bench import s3bench as sb
from commons.utils.config_utils import read_yaml
from libs.s3 import s3_test_lib
from libs.s3 import ACCESS_KEY, SECRET_KEY

sys.path.append("...")

S3_TEST_OBJ = s3_test_lib.S3TestLib()


class TestS3Bench(unittest.TestCase):
    """S3 Bench lib unittest suite."""

    def setUp(self):
        """
        Function will be invoked before test suit execution.

        It will perform prerequisite test steps if any
        Defined var for log, config, creating common account or bucket
        """
        self.ut_cm_cfg = read_yaml("config/scripts/test_s3bench_cfg.yaml")[1]
        logging.basicConfig(filename="s3bench-unittest.log", filemode="w", level=logging.DEBUG)
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.ut_cfg = self.ut_cm_cfg["s3bench_ut"]
        if not os.path.exists(self.ut_cfg["common_path"]):
            os.mkdir(self.ut_cfg["common_path"])
        self.log.info("ENDED: Setup operations")

    def tearDown(self):
        """
        Function will be invoked after test suit.

        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        self.log.info("STARTED: Teardown operations")
        ut_cfg = self.ut_cm_cfg["s3bench_ut"]
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                ut_cfg["bkt_prefix"])]
        self.log.info("bucket-list: %s", pref_list)
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("Deleting Common dir and files...")
        if os.path.exists(ut_cfg["common_path"]):
            shutil.rmtree(ut_cfg["common_path"])
        self.log.info("ENDED: Teardown operations")

    def test_00_create_log_file(self):
        """test_00 create_log_file."""
        resp = sb.setup_s3bench()
        self.assertTrue(resp, resp)

    def test_01_create_log_file(self):
        """test_01 create_log_file."""
        test_cfg = self.ut_cfg["test_01"]
        resp = sb.create_log(
            resp=test_cfg["resp_msg"],
            log_file_prefix=test_cfg["temp_path"], client=10, samples=5, size=10)
        res = os.path.exists(resp)
        self.assertTrue(res, test_cfg["err_msg"].format(res))

    def test_02_s3bench(self):
        """test_02_s3bench."""
        test_cfg = self.ut_cfg["test_02"]
        S3_TEST_OBJ.create_bucket(test_cfg["bucket_name"])
        access, secret = ACCESS_KEY, SECRET_KEY
        resp = sb.s3bench(
            access,
            secret,
            test_cfg["bucket_name"],
            test_cfg["end_point"],
            test_cfg["num_clients"],
            test_cfg["num_sample"],
            test_cfg["obj_name_pref"],
            test_cfg["obj_size"],
            test_cfg["duration"],
            test_cfg["verbose"])
        self.assertIsNotNone(resp[0], resp)
        self.assertEqual(
            resp[0][0]["numSamples"], str(
                test_cfg["num_sample"]), resp)
        res = os.path.exists(resp[1])
        self.assertTrue(res, test_cfg["err_msg"].format(res))

    def test_03_create_json_resp(self):
        """test_03_create_json_resp."""
        test_cfg = self.ut_cfg["test_03"]
        dummy_resp = [
            'Test parameters\nendpoint(s):      [https://s3.seagate.com]\nbucket:           '
            'dd-bucket\nobjectNamePrefix: loadgen_test_\nobjectSize:       0.0763 MB\nnumClients: '
            '      40\nnumSamples:       200\nverbose:       %!d(bool=false)\n\n\nGenerating '
            'in-memory sample data... Done (684.718s)\n\nRunning Write test...\n\nRunning Read '
            'test...\n\nTest parameters\nendpoint(s):      [https://s3.seagate.com]\nbucket:      '
            '     dd-bucket\nobjectNamePrefix: loadgen_test_\nobjectSize:       '
            '0.0763 MB\nnumClients:       40\nnumSamples:       200\nverbose:       '
            '%!d(bool=false)\n\n\nResults Summary for Write Operation(s)\nTotal Transferred: '
            '15.259 MB\nTotal Throughput:  0.36 MB/s\nTotal Duration:    42.434 s\nNumber of '
            'Errors:  0\n------------------------------------\nWrite times Max:       '
            '15.592 s\nWrite times 99th %ile: 15.589 s\nWrite times 90th %ile: 12.726 s\nWrite '
            'times 75th %ile: 10.481 s\nWrite times 50th %ile: 7.367 s\nWrite times 25th %ile: '
            '5.842 s\nWrite times Min:       1.719 s\n\n\nResults Summary for Read Operation(s)\n'
            'Total Transferred: 15.259 MB\nTotal Throughput:  1.23 MB/s\nTotal Duration:    '
            '12.395 s\nNumber of Errors:  0\n------------------------------------\nRead times Max:'
            '       4.764 s\nRead times 99th %ile: 4.575 s\nRead times 90th %ile: 3.328 s\nRead '
            'times 75th %ile: 2.706 s\nRead times 50th %ile: 2.066 s\nRead times 25th %ile: 1.710 '
            's\nRead times Min:       0.462 s\n\n\nCleaning up 200 objects...\nDeleting a batch of'
            ' 200 objects in range {0, 199}... '
            'Succeeded\nSuccessfully deleted 200/200 objects in 4.188868341s']
        resp = sb.create_json_reps(dummy_resp)
        self.assertEqual(resp[0]["bucket"], test_cfg["bucket_name"], resp)
        resp = sb.create_json_reps([])
        self.assertEqual(resp, [], resp)


if __name__ == '__main__':
    unittest.main()
