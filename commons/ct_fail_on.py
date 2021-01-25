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

import pytest
from commons.exceptions import CTException


class ct_fail_on(object):
    """
    This class has implemented to use as a decorator.
    Usage : decorate the avocado testMethod with this class decorator 
            if the test method generates the specified exception. It will mark test as failure and
            execute the handler function which was provide with argument.
    Note  : 1. If exception has not provided, default CTException will be considered.
    """

    def __init__(self, routine_func, exception_type=CTException, routine_params=None):
        """
        exception_type : exception to handled
        routine_func : function which need to be called as an exception handler(routine)
        routine_param : Arguments for exception handler function(routine)
        routine_params will be tuple containing the object attribute names in string format
        """
        self.exception = exception_type
        self.routine_func = routine_func
        self.routine_params = routine_params
        self.routine_param_values = []

    def __call__(self, fn):
        def __wrap(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except BaseException as exc:
                raise exc
            except self.exception as details:
                # Here CT exception caught and calling the failure routine functions with the parameters
                if self.routine_params:
                    for i in self.routine_params:
                        # Here args[0] will be the decorated function obj
                        # TestError: if the object attribute is not found
                        try:
                            self.routine_param_values.append(getattr(args[0], i))
                        except AttributeError as e:
                            raise (str(e))
                self.routine_func(details, *self.routine_param_values)

        return __wrap
