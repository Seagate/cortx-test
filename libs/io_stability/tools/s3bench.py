import json
import logging
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from typing import Tuple

LOGGER = logging.getLogger(__name__)


class S3bench:
    def __init__(self, access, secret, endpoint, bucket, object_prefix, log_file, clients, samples,
                 object_size, head, skip_read, skip_write, skip_cleanup, validate, duration,
                 multipart="0b"):
        """S3bench class for executing given s3bench workload"""
        if os.system("go run s3bench --help"):
            LOGGER.error("ERROR: s3bench is not installed")
            exit(-1)
        self.access_key = access
        self.secret_key = secret
        self.endpoint = endpoint
        self.bucket = bucket
        self.object_prefix = object_prefix
        self.num_clients = clients
        self.num_samples = samples
        self.label = log_file
        self.object_size = object_size
        self.report_file = f"{self.label}_report"
        self.head = head
        self.skip_read = skip_read
        self.skip_write = skip_write
        self.skip_cleanup = skip_cleanup
        self.validate = validate
        self.multipart_size = multipart
        if not duration:
            self.finish_time = datetime.now() + timedelta(hours=int(100 * 24))
        else:
            hours, minutes = duration.lower().replace("h", ":").replace("m", "").split(":")
            self.finish_time = datetime.now() + timedelta(hours=int(hours), minutes=int(minutes))
        self.cli_log = f"{self.label}_cli"
        self.cmd = None
        self.results = []
        self.errors = ["with error", "panic", "status code",
                       "flag provided but not defined", "InternalError", "ServiceUnavailable"]

    def execute_command(self, duration):
        """
        Execute s3bench command on local machine for given duration.
        Kill it after given duration if it is not complete
        :param duration: timeout.
        :return: bool: Subprocess killed due to timeout
        """
        LOGGER.info("Command: %s", self.cmd)
        proc = subprocess.Popen(self.cmd, shell=True, preexec_fn=os.setsid)
        LOGGER.info("Started: %s wait: %s", self.cmd, duration)
        counter = 0
        # Poll for either process completion or for timeout
        while counter < duration and not proc.poll():
            counter = counter + 5
            time.sleep(5)
        if counter < duration:
            LOGGER.info("S3bench workload terminated before expected duration.")
            return True
        if not proc.poll():
            LOGGER.info("S3bench workload still running, Terminating")
            proc.send_signal(signal.SIGINT)
            return True
        LOGGER.info("S3bench workload is complete")
        return False

    def execute_s3bench_workload(self):
        """Prepare and execute s3bench workload command"""
        cmd = f"go run s3bench -accessKey={self.access_key} -accessSecret={self.secret_key} " \
              f"-endpoint={self.endpoint} -bucket={self.bucket} -numClients={self.num_clients} " \
              f"-numSamples={self.num_samples} -objectNamePrefix={self.object_prefix} " \
              f"-objectSize={self.object_size} -t json "

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
        i = 0
        while True:
            i = i + 1
            LOGGER.info("Iteration %s", i)
            report = f"{self.report_file}-{i}.log"
            cli_log = f"{self.cli_log}-{i}.log"
            label = f"{self.label}-{i}"
            self.cmd = f"{cmd} -o {report} -label {label} >> {cli_log} 2>&1"
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
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

    def check_log_file_error(self, report_file, cli_log) -> Tuple[bool, dict]:
        """
        Check if errors found in s3bench workload

        e.g. return: {"Write": 5, "Read":3, "Head":0}
        """
        try:
            report = json.load(open(report_file))
        except JSONDecodeError as e:
            LOGGER.error("Incorrect Json format %s - %s", report_file, e)
            return self.check_terminated_results(cli_log)
        ops = dict()
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
        return error, ops

    def check_terminated_results(self, cli_log):
        """Check results if s3bench workload is terminated"""
        pattern = fr"^M{0} \| [\d\/\.% \(\)]+ \| [a-z\d ]+ \| errors ([1-9]+)"
        ops = {"Write": 0, "Read": 0, "Validate": 0, "HeadObj": 0}
        error = True
        with open(cli_log) as log_f:
            data = log_f.read()
            errors_pattern = r"|".join(self.errors)
            matches = list(re.finditer(errors_pattern, data, re.MULTILINE))
            if len(matches):
                found_strings = set(x.group() for x in list(matches))
                LOGGER.error("S3bench workload failed with %s", found_strings)
                error = True
            for operation in ops:
                ops_pattern = pattern.format(operation)
                matches = re.finditer(ops_pattern, data, re.MULTILINE)
                matches = list(matches)
                if matches:
                    ops[operation] = matches[-1].group(1)
                    error = False
            return error, ops

    def run_check(self):
        """Execute s3bench workload & check failures in output"""
        return self.execute_s3bench_workload()
