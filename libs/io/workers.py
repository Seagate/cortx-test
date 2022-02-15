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
#
#

"""
io_schedular Library.

This module consists of following classes
io schedular  is a Public class and can be used to create objects and using
functionality of io scheduling operations.

Below classes are protected and private and need to be used for internal purpose

"""

import concurrent.futures
import os
from functools import wraps

import psutil
import timeit


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
        print("Number of CPU Cores", number_of_cpu)
        print('RAM memory % used:', psutil.virtual_memory()[2])
        # Default we are keeping max concurrent workers equal to number of cpu cores
        # For e.g. if there are N CPUs then for dul core system total Cores will be N*2
        args = args[0] if type(args[0]) in (list, tuple) else args
        max_concurrent_workers = kwargs.get("number_of_workers", number_of_cpu*2)
        if len(args) < max_concurrent_workers:
            # If the length of the list is low, we would only require those many number of threads.
            # Here we are avoiding creating unnecessary threads
            max_concurrent_workers = len(args)
        print("Executing with {} Workers".format(max_concurrent_workers))
        start = timeit.default_timer()
        if max_concurrent_workers:
            # Create max number of threads and running the decorated function in parallel.
            result = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_workers) as exe:
                bag = {exe.submit(func, i): i for i in args}
                for future in concurrent.futures.as_completed(bag):
                    result.append(future.result())
                    print("\n------------Session Running------------\n", future.result())
        else:
            result = []

        stop = timeit.default_timer()
        print('Total Execution Time is: ', stop - start)
        return result

    return spawn
