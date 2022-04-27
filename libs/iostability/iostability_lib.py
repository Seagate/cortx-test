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

"""
Utility Method for IO stability testing
"""
import logging
import time
from datetime import datetime, timedelta

from commons.utils import system_utils
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


class IOStabilityLib:

    def __init__(cls, access_key=ACCESS_KEY, secret_key=SECRET_KEY):
        cls.log = logging.getLogger(__name__)
        cls.s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)

    def execute_workload_distribution(self, distribution, clients, total_obj,
                                      duration_in_days, log_file_prefix, buckets_created=None):
        """Execution given workload distribution.
        :param distribution: Distribution of object size
        :param clients: No of clients
        :param total_obj: total number of objects per iteration
        :param duration_in_days: Duration expected of the test run
        :param log_file_prefix: Log file prefix for s3bench
        :param buckets_created: Buckets already created to be used for IO operations.
        """
        workloads = [(size, int(total_obj * percent / 100)) for size, percent in
                     distribution.items()]
        end_time = datetime.now() + timedelta(days=duration_in_days)
        loop = 0
        while datetime.now() < end_time:
            for size, samples in workloads:
                bucket_name = f"{log_file_prefix}-bucket-{loop}-{str(int(time.time()))}".lower()
                skip_cleanup = False
                if buckets_created is not None:
                    bucket_name = buckets_created[loop % len(buckets_created)]
                    skip_cleanup = True
                if samples == 0:
                    continue
                cur_clients = clients
                if cur_clients > samples:
                    cur_clients = samples
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                       num_clients=cur_clients, num_sample=samples,
                                       obj_name_pref="object-", obj_size=size,
                                       skip_cleanup=skip_cleanup, duration=None,
                                       log_file_prefix=str(log_file_prefix).upper(),
                                       end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"])
                self.log.info("Loop: %s Workload: %s objects of %s with %s parallel clients.",
                              loop, samples, size, clients)
                self.log.info("Log Path %s", resp[1])
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload failed in loop {loop}. Please read log file {resp[1]}"
                # delete file if operation successful.
                system_utils.remove_file(resp[1])
                if skip_cleanup:
                    # delete only objects, to be used for degraded mode.
                    self.log.info("Delete Created Objects")
                    resp = self.s3t_obj.object_list(bucket_name=bucket_name)
                    obj_list = resp[1]
                    while len(obj_list):
                        if len(obj_list) > 1000:
                            self.s3t_obj.delete_multiple_objects(bucket_name,
                                                                 obj_list=obj_list[0:1000])
                            obj_list = obj_list[1000:]
                        else:
                            self.s3t_obj.delete_multiple_objects(bucket_name=bucket_name,
                                                                 obj_list=obj_list)
                            obj_list = []
                    self.log.info("Objects deletion completed")
            loop += 1
