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


def make_sessions(func):
    """
        Decorator used to decorate any function which needs to be parallelized.
        After the input of the function should be a list in which each element is an instance of input fot the normal function.
        You can also pass in keyword arguments separately.
        :param func: function
            The instance of the function that needs to be parallelized.
        :return: function
    """

    @wraps(func)
    def spawn(*args, **kwargs):
        """

        :param number_of_workers:
            The number of session need to run simultaneously
        :return:
        """
        # the number of threads that can be max-spawned.
        # If the number of threads are too high, then the overhead of creating the threads will be significant.
        number_of_cpu = int(os.cpu_count())
        print("Number of CPU Cores",number_of_cpu)
        number_of_workers = kwargs.get("number_of_workers", 1)
        if len(args) < number_of_workers:
            # If the length of the list is low, we would only require those many number of threads.
            # Here we are avoiding creating unnecessary threads
            number_of_workers = len(args)

        if number_of_workers:
            if number_of_workers == 1:
                # If the length of the list that needs to be parallelized is 1, there is no point in
                # parallelize the function.
                # So we run it serially.
                result = [func(args[0])]
            else:
                # Core Code, where we are creating max number of threads and running the decorated function in parallel.
                result = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=number_of_workers) as executer:
                    bag = {executer.submit(func, i): i for i in args}
                    for future in concurrent.futures.as_completed(bag):
                        result.append(future.result())
                        print("\n------------Running------------\n", future.result())
        else:
            result = []
        return result

    return spawn
