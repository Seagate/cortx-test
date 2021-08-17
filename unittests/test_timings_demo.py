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
    test_tkt = request.node.own_markers[0].args[0]
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

    tp_tkt = request.config.getoption("--tp_ticket")
    build = request.config.getoption("--build")
    te_tkt = request.config.getoption("--te_tkt")
    function_name = request.node.name
    Globals.records.update({function_name: records})
    payload = {
        "buildNo": build,
        "logs": logs,
        "testID": test_tkt,
        "testPlanID": tp_tkt,
        "testExecutionID": te_tkt,
        "testStartTime": start_time,
        "nodeRebootTime": bucket_creation_time,
    }
    create_timings_db_entry(payload)
