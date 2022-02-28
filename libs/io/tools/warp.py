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

"""Warp Library for IO driver."""

import logging
import os
import re
import subprocess
from datetime import timedelta
from typing import Any

LOGGER = logging.getLogger(__name__)


class Warp:
    """Warp class for executing given Warp workload"""
    def __init__(self, operation: str, access: str, secret: str, host: str, test_id: str,
                 concurrent: int, objects: int, size_high: int, random_size: bool = True,
                 duration: timedelta = None) -> None:
        """Log file generated name = log_file.csv.zst file in current directory
        operations can be one of the get, put, stat

        :param operation: Operation e.g. get, put, stat
        :param access: Access key
        :param secret: Secret key
        :param host: Endpoint URL without protocol
        :param test_id: Test ID used as log file name
        :param concurrent: Parallel number of operations
        :param objects: Total number of objects for pool
        :param size_high: Maximum object size in bytes
        :param random_size: Use random object size.
               If True warp uses random object size from 0 to size_high
        :param duration: e.g. 100m10s, if not given will run for 40 days Max allowed by warp
        """
        self.operation = operation
        self.access_key = access
        self.secret_key = secret
        self.host = host
        self.bucket = f"bucket-{test_id}"
        self.concurrent = concurrent
        self.objects = objects
        self.size_high = size_high
        self.log = test_id
        self.log_file = f"{test_id}.csv.zst"
        self.random_size = random_size
        self.duration = duration if duration else timedelta(hours=int(40 * 24))
        self.cmd = None

    @staticmethod
    def install_warp() -> bool:
        """Install Warp if not present"""
        # ToDo: Moving constants and commands into confi files.
        if os.system("warp -v"):
            LOGGER.error("ERROR: warp is not installed. Installing warp tool.")
            if os.system(
                    "yum install -y https://github.com/minio/warp/releases/download/v0.5.5/warp_0.5.5_Linux_x86_64.rpm"):
                LOGGER.error("ERROR: Unable to install warp")
                return False
            if os.system("warp -v"):
                LOGGER.error("ERROR: Unable to install warp")
                return False
        return True

    @staticmethod
    def execute_command(cmd) -> subprocess.CompletedProcess:
        """Execute Command"""
        LOGGER.info("Starting: %s", cmd)
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)

    def execute_workload(self) -> [bool, Any]:
        """Execute Warp command"""
        self.cmd = f"warp {self.operation} --host {self.host} --access-key {self.access_key} " \
                   f"--secret-key {self.secret_key} --duration {self.duration.seconds}s " \
                   f"--objects {self.objects} --concurrent {self.concurrent} " \
                   f"--obj.size {self.size_high}b --benchdata {self.log} " \
                   f"--disable-multipart --analyze.v "
        if self.random_size:
            self.cmd = self.cmd + " --obj.randsize"
        self.execute_command(self.cmd)
        return self.check_errors()

    def check_errors(self) -> [bool, Any]:
        """Check errors in Warp log file

        e.g. return: True, {"PUT": 5, "GET":3, "STAT":0, "DELETE": 0}
        """
        ops = {"PUT": 0, "GET": 0, "STAT": 0, "DELETE": 0}
        error = True
        if not os.path.exists(self.log_file):
            LOGGER.error("%s log file is not present", self.log_file)
            error = False
        else:
            for operation in ops:
                cp = self.execute_command(f"warp analyze {self.log_file} "
                                          f"--analyze.op {operation.upper()} --analyze.v")
                pattern = r"Errors: (\d+)"
                # Grep pattern in cp.stdout
                matches = re.finditer(pattern, cp.stdout, re.MULTILINE)
                matches = list(matches)
                if matches:
                    ops[operation] = matches[-1].group(1)
                    error = False
        return error, ops
