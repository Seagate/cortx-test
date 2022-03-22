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
#
#

"""
s3 worker Library.

This module consists of following method
make_sessions  is a decorator method and be used to spawn sessions

"""

import concurrent.futures
import logging
import os
import timeit
from functools import wraps

import psutil

logger = logging.getLogger(__name__)


def make_sessions(func):
    """
        Decorator used to decorate any function which needs to be parallelized.
        function, each element is an instance of input for the normal function.
        keyword arguments consists of number of workers need to be created separately.
        :param func: function
            The instance of the function that needs to be parallelized.
        :return: function
    """

    @wraps(func)
    def spawn(*args, **kwargs):
        """
        :param args : Varying input data
        :param kwargs :number_of_workers:
            The number of session need to run simultaneously
        :return: list
        """
        # the number of threads that can be max-spawned.
        # If the number of threads are high, overhead of creating the threads will be significant.
        number_of_cpu = int(os.cpu_count())
        logger.info("Number of CPU Cores", number_of_cpu)
        logger.info('RAM memory % used:', psutil.virtual_memory()[2])
        # Default we are keeping max concurrent workers equal to number of cpu cores
        # For e.g. if there are N CPUs then for dul core system total Cores will be N*2
        args = args[0] if type(args[0]) in (list, tuple) else args
        max_concurrent_workers = kwargs.get("number_of_workers", number_of_cpu * 2)
        if len(args) < max_concurrent_workers:
            # If the length of the list is low, we would only require those many number of threads.
            # Here we are avoiding creating unnecessary threads
            max_concurrent_workers = len(args)
        logger.info("Executing with {} Workers".format(max_concurrent_workers))
        start = timeit.default_timer()
        if max_concurrent_workers:
            # Create max number of threads and running the decorated function in parallel.
            result = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_workers) as exe:
                bag = {exe.submit(func, i): i for i in args}
                for future in concurrent.futures.as_completed(bag):
                    result.append(future.result())
                    logger.info("\n------------Session Running------------\n", future.result())
        else:
            result = []

        stop = timeit.default_timer()
        logger.info('Total Execution Time is: ', stop - start)
        return result

    return spawn
