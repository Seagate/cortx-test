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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""IO TestSet Process Schedular"""

import sched
import time
from concurrent.futures import ProcessPoolExecutor

scheduler = sched.scheduler(time.time)

test_results = {}


def job_schedular(test_suite):
    """

    :param test_suite:
    :return:
    """
    test_suite = eval(test_suite)
    method_list = [method for method in dir(test_suite) if method.startswith('__') is False]
    print("Suite {} and Methods {}".format(test_suite, method_list))
    # second event with delay of  seconds
    start_time = 1
    for func in method_list:
        scheduler.enter(start_time, 1, getattr(test_suite, func))
        start_time += 1
    # executing the events
    scheduler.run()

    # returning execution results
    return test_results


def main(suite_list, workers):
    """

    :param suite_list:
    :param workers:
    """
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = executor.map(job_schedular, suite_list)
    for result in results:
        print(result)
