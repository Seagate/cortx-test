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
#

"""Test S3 utility library module."""

import os
import time

from commons.utils import s3_utils
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER


class TestS3Utils:
    """Test S3 utility library class."""

    def setup_method(self):
        """Function will be invoked prior to each test case."""
        self.dpath = os.path.join(TEST_DATA_FOLDER, "TestS3Utils")
        self.fpath = os.path.join(self.dpath, "s3utils-{}".format(time.perf_counter_ns()))
        if not system_utils.path_exists(self.dpath):
            system_utils.make_dirs(self.dpath)

    def teardown_method(self):
        """Function will be invoked after each test case."""
        if system_utils.path_exists(self.dpath):
            system_utils.remove_dirs(self.dpath)

    def test_calc_checksum(self):
        """Test calculating an checksum using encryption algorithm."""
        resp = system_utils.create_file(self.fpath, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_utils.calc_checksum(self.fpath, 1024)
        assert_utils.assert_true(resp[0], resp[1])
        

