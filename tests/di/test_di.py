# !/usr/bin/env python3
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
"""DI Test Cases."""

import logging
import pytest
from libs.di.di_test_framework import Uploader
from libs.di.di_test_framework import DIChecker
from libs.di.di_mgmt_ops import ManagementOPs
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import DATA_PATH_CFG

LOGGER = logging.getLogger(__name__)


class TestDataIntegrity:
    """ Data Integrity test plan. Log test hooks and actions/events.
    """

    @pytest.mark.di
    @pytest.mark.tags("TEST-0")
    def test_di_sanity(self):
        ops = ManagementOPs()
        users = ops.create_account_users(nusers=4)
        uploader = Uploader()
        uploader.start(users)
        DIChecker.init_s3_conn(users)
        DIChecker.verify_data_integrity(users)

    @pytest.mark.skip
    @pytest.mark.di
    @pytest.mark.tags("TEST-1")
    @CTFailOn(error_handler)
    def test_large_number_s3_connection(self):
        """
        300 * 3, 300 * 6, 300 * 9, 300 * 12
        Assuming scale of 300 connections per node. For 3 node, 6 node cluster, etc.
        :return:
        """
        ops = ManagementOPs()
        users = ops.create_account_users(nusers=4)
        LOGGER.info("Start large number of S3 connections.")
        test_conf = DATA_PATH_CFG["test_1703"]
        bucket = ops.create_buckets(nbuckets=10)
        self.run_s3bench(test_conf, bucket)
        LOGGER.info("ENDED: large # of s3 connections.")

    @pytest.mark.skip
    @pytest.mark.di
    @pytest.mark.tags("TEST-2")
    @CTFailOn(error_handler)
    def test_di_large_number_s3_connection_with_deletes(self):
        ops = ManagementOPs()
        users = ops.create_account_users(nusers=4)
        uploader = Uploader()
        uploader.start(users)
        DIChecker.init_s3_conn(users)
        DIChecker.verify_data_integrity(users)
