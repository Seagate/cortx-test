# -*- coding: utf-8 -*-
# !/usr/bin/python
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
"""Demo test for adding timings data into database."""

import time
from datetime import datetime

import pytest

from commons import Globals
from commons.timings_client import create_timings_db_entry
from libs.s3 import s3_test_lib

S3_OBJ = s3_test_lib.S3TestLib()


@pytest.mark.usefixtures("log_cutter")
@pytest.mark.tags("TEST-11733")
def test_11733(request, capture, logger, formatter):
    """Test to measure bucket creation time"""
    start_time = datetime.now().isoformat()
    records = capture.records
    bucket_name = f"TEST-11733-bucket-{str(int(time.time()))}"
    start = time.time()
    logger.debug(f"Creating bucket {bucket_name}")
    resp = S3_OBJ.create_bucket(bucket_name)
    logger.debug(f"Bucket {bucket_name} created")
    end = time.time()
    assert resp[0], resp[1]
    bucket_creation_time = end - start
    logs = []
    for rec in records:
        logs.append((formatter.format(rec) + '\n'))

    function_name = request.node.name
    Globals.records.update({function_name: records})
    payload = {
        "buildNo": request.config.getoption("--build"),
        "logs": logs,
        "testID": request.node.own_markers[0].args[0],
        "testPlanID": request.config.getoption("--tp_ticket"),
        "testExecutionID": request.config.getoption("--te_tkt"),
        "testStartTime": start_time,
        "nodeRebootTime": bucket_creation_time,
    }
    create_timings_db_entry(payload)
