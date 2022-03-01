#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""S3bench Library for IO driver."""

import json
import logging
import os
import random
import re
import signal
import subprocess
import time
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from typing import Tuple, List, Any

LOGGER = logging.getLogger(__name__)


class S3bench:
    """S3bench class for executing given s3bench workload"""

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(self, access: str, secret: str, endpoint: str, test_id: str, clients: int,
                 samples: int, size_low: int, size_high: int, seed: int, part_high: int = 0,
                 part_low: int = 0, head: bool = True, skip_read: bool = True,
                 skip_write: bool = False, skip_cleanup: bool = False, validate: bool = True,
                 duration: timedelta = None) -> None:
        """S3bench workload tests generate following log files:
        1. {log_file}-report-i.log -> CLI redirection logs
        2. {log_file}-cli-i.log -> Generated by s3bench
        3. s3bench-{log_file}-i.log -> Generated by s3bench

        :param access: access key
        :param secret: secret key
        :param endpoint: endpoint with http or https
        :param test_id: Test ID string, used for log file name
        :param clients: Number of clients or parallel operations
        :param samples: Total number of operation
        :param size_low: Object size in bytes
        :param size_high: Object size in bytes
        :param seed: Can be used to recreate the object size sequence, which is generated randomly
        :param part_high: High part size of Multipart Upload in bytes
        :param part_low: Low part size of Multipart Upload in bytes
        :param head: Head operation
        :param skip_read: Skip read operation
        :param skip_write: Skip write operation
        :param skip_cleanup: Skip cleanup operation
        :param validate: Validate downloaded objects
        :param duration: Duration timedelta object, if not given will run for 100 days
        """
        random.seed(seed)
        if not self.install_s3bench():
            exit(-1)
        self.access_key = access
        self.secret_key = secret
        self.endpoint = endpoint
        self.bucket = f"bucket-{test_id.lower()}"
        self.object_prefix = f"obj-{test_id.lower()}"
        self.num_clients = clients
        self.num_samples = samples
        self.label = f"{test_id.lower()}"
        self.size_low = size_low
        self.size_high = size_high
        self.report_file = f"{self.label}-report"
        self.head = head
        self.skip_read = skip_read
        self.skip_write = skip_write
        self.skip_cleanup = skip_cleanup
        self.validate = validate
        self.part_high = part_high
        self.part_low = part_low
        self.min_duration = 10  # In seconds
        if not duration:
            self.finish_time = datetime.now() + timedelta(hours=int(100 * 24))
        else:
            self.finish_time = datetime.now() + duration
        self.cli_log = f"{self.label}-cli"
        self.cmd = None
        self.results = []
        self.errors = ["with error", "panic", "status code", "fatal error",
                       "flag provided but not defined", "InternalError", "ServiceUnavailable"]

    @staticmethod
    def install_s3bench() -> bool:
        """Install s3bench if already not installed"""
        # ToDo: Moving constants and commands into confi files.
        if os.system("s3bench --help"):
            LOGGER.info("s3bench is not installed. Installing s3bench.")
            if os.system(
                    "wget -O /usr/bin/s3bench https://github.com/Seagate/s3bench/releases/download/v2021-06-28/s3bench.2021-06-28"):
                LOGGER.error("ERROR: Unable to download s3bench binary from github")
                return False
            if os.system("chmod +x /usr/bin/s3bench"):
                LOGGER.error("ERROR: Unable to add execute permission to s3bench")
                return False
            if os.system("s3bench --help"):
                LOGGER.error("ERROR: Unable to install s3bench")
                return False
        return True

    def execute_command(self, duration: float) -> bool:
        """
        Execute s3bench command on local machine for given duration.
        Kill it after given duration if it is not complete
        :param duration: Duration in seconds.
        :return: Subprocess completed returns False or killed due to timeout returns True
        """
        LOGGER.info("Starting: %s wait: %s", self.cmd, duration)
        proc = subprocess.Popen(self.cmd, shell=True, preexec_fn=os.setsid)
        pgid = os.getpgid(proc.pid)
        counter = 0
        # Poll for either process completion or for timeout
        while counter < duration and proc.poll() is None:
            counter = counter + 5
            time.sleep(5)
        if proc.poll() is None:
            LOGGER.info("S3bench workload still running, Terminating.")
            os.killpg(pgid, signal.SIGKILL)
            return True
        LOGGER.info("S3bench workload is complete.")
        return False

    @staticmethod
    def delete_logs(logs: List[str]) -> None:
        """Delete given list of files"""
        for log in logs:
            if os.path.exists(log):
                LOGGER.info("Deleting old log %s", log)
                os.remove(log)
            else:
                LOGGER.info("Old log %s does not exist", log)

    # pylint: disable=too-many-branches,too-many-locals
    def execute_s3bench_workload(self) -> Tuple[bool, Any]:
        """Prepare and execute s3bench workload command
        :return: Tuple of Test Pass/Fail with dict of failures per operation
        """
        i = 0
        while True:
            i = i + 1
            LOGGER.info("Iteration %s", i)
            iter_del = i - 5  # Iteration logs to be deleted
            if iter_del > 0:  # Delete logs
                old_report = f"{self.report_file}-{iter_del}.log"
                old_cli_log = f"{self.cli_log}-{iter_del}.log"
                old_log = f"s3bench-{self.label}-{iter_del}.log"
                self.delete_logs([old_report, old_cli_log, old_log])
            if self.size_high == self.size_low:
                object_size = self.size_low
            else:
                object_size = random.randrange(self.size_low, self.size_high)
            if self.part_high == self.part_low:
                part_size = self.part_high
            else:
                part_size = random.randrange(self.part_low, self.part_high)
            bucket = f"{self.bucket}-{i}-{time.time()}"
            cmd = f"s3bench -accessKey={self.access_key} -accessSecret={self.secret_key} " \
                  f"-endpoint={self.endpoint} -bucket={bucket} -objectSize={object_size}b " \
                  f"-numClients={self.num_clients} -numSamples={self.num_samples} " \
                  f"-objectNamePrefix={self.object_prefix} -multipartSize={part_size}b -t json "

            if self.head:
                cmd = cmd + "-headObj "
            if self.skip_write:
                cmd = cmd + "-skipWrite "
            if self.skip_read:
                cmd = cmd + "-skipRead "
            if self.skip_cleanup:
                cmd = cmd + "-skipCleanup "
            if self.validate:
                cmd = cmd + "-validate"

            report = f"{self.report_file}-{i}.log"
            cli_log = f"{self.cli_log}-{i}.log"
            label = f"{self.label}-{i}"
            self.cmd = f"{cmd} -o {report} -label {label} >> {cli_log} 2>&1"
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                if i == 1:
                    LOGGER.info("s3bench workload did not execute since given duration is less "
                                "than %s seconds.", self.min_duration)
                    return False, None
                LOGGER.info("s3bench workload execution done.")
                return True, None
            LOGGER.info("Remaining test time %s", timedelta_v)
            timeout = self.execute_command(timedelta_sec)
            if timeout:
                LOGGER.info("Terminated s3bench workload due to timeout. Checking results.")
                return self.check_terminated_results(cli_log)
            else:
                status, ops = self.check_log_file_error(report, cli_log)
                if not status:
                    LOGGER.critical("Error found stopping execution")
                    return status, ops
                else:
                    LOGGER.info("No error found continuing execution")

    def check_log_file_error(self, report_file: str, cli_log: str) -> Tuple[bool, dict]:
        """
        Check if errors found in s3bench workload

        :param report_file: Report file name.
        :param cli_log: CLI log file name.
        :return: Tuple of Test Pass/Fail with dict of failures per operation
                  e.g. False, {"Write": 5, "Read":3, "Head":0}
        """
        try:
            report = json.load(open(report_file))
        except JSONDecodeError as e:
            LOGGER.error("Incorrect Json format %s - %s", report_file, e)
            return self.check_terminated_results(cli_log)
        ops = {"Write": 0, "Read": 0, "Validate": 0, "HeadObj": 0}
        error = True
        for test in report["Tests"]:
            operation = test["Operation"]
            errors = test["Errors Count"]
            ops[operation] = errors
            if test["Errors Count"] != 0:
                LOGGER.error(f"ERROR: {operation} operation failed with {errors} errors")
                error = False
            else:
                LOGGER.info(f"{operation} operation passed")
        error_ops = {f"{key} Errors": value for key, value in ops.items()}
        return error, error_ops

    def check_terminated_results(self, cli_log: str) -> Tuple[bool, dict]:
        """Check results if s3bench workload is terminated

        :param cli_log: CLI log file name.
        :return: Tuple of Test Pass/Fail with dict of failures per operation"""
        pattern = r"{0} \| [\d\/\.% \(\)]+ \| [a-z\d ]+ \| errors ([1-9]+)"
        ops = {"Write": 0, "Read": 0, "Validate": 0, "HeadObj": 0}
        error = True
        with open(cli_log) as log_f:
            data = log_f.read()
            for operation in ops:
                ops_pattern = pattern.format(operation)
                matches = re.finditer(ops_pattern, data, re.MULTILINE)
                matches = list(matches)
                if matches:
                    ops[operation] = int(matches[-1].group(1))
                    error = False
            error_ops = {f"{key} Errors": value for key, value in ops.items()}
            errors_pattern = fr"^.*(?:{'|'.join(self.errors)}).*$"
            matches = list(re.finditer(errors_pattern, data, re.MULTILINE))
            if len(matches):
                error_ops["Error String"] = matches[0].group()
                found_strings = set(x.group() for x in list(matches))
                LOGGER.error("S3bench workload failed with %s", found_strings)
                error = False
            return error, error_ops

    def run_check(self):
        """Execute s3bench workload & check failures in output"""
        return self.execute_s3bench_workload()
