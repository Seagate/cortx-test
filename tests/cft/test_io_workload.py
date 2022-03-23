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
"""Test Suite for IO workloads."""
import time

import pytest

from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_test_lib import S3TestLib


class TestIOWorkload:
    """Test suite for IO workloads."""

    @classmethod
    def setup_class(cls):
        """Setup class."""
        cls.prov_obj = ProvDeployK8sCortxLib()
        cls.s3t_obj = S3TestLib()

    @pytest.mark.lc
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-39180")
    def test_39180(self):
        """Basic IO test."""
        bucket_name = f'bucket-test-39180-{int(time.time())}'
        self.prov_obj.basic_io_write_read_validate(bucket_name=bucket_name, s3t_obj=self.s3t_obj)
