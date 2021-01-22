# !/usr/bin/python
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

import sys
import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


class _final:
    """
    - Assign the object attribute its value.
    - The object from which the name attribute is to be removed.
    - The object whose attributes need to be processed.
    - Maintain uniqueness across module.
    """

    class _ConstError(Exception):
        pass

    class _NameError(NameError):
        pass

    class _AttributeError(AttributeError):
        pass

    def __setattr__(self, name: Any, value: Any) -> None:
        """
        Assign the object attribute its value.
        The object whose attributes need to be processed.
        :param name: object attribute which has to be assigned.
        :type name: attribute.
        :param value: value with which variable is to be assigned.
        :type value: attribute value.
        :return: If name already defined then another value cant be assigned and will raise error.
        """
        if name in self.__dict__:
            try:
                raise self._ConstError
            except self._ConstError:
                LOGGER.error(f"Error: Can't rebind const {name}")
        else:
            self.__dict__[name] = value

    def __getattr__(self, name: Any) -> None:
        """
        Access the attribute value of an object and also not allowing in case of unavailability of the name.
        The object whose attributes need to be processed.
        :param name: The attribute of object.
        :type name: attribute.
        :return: Object value if value is available, default value in case attribute is not present
                 and returns AttributeError in case attribute is not present and default value is not specified.
        """
        try:
            if name not in self.__dict__:
                raise AttributeError
        except AttributeError:
            LOGGER.error(f"Error: const {name} not present/binded")

    def __delattr__(self, name: Any) -> None:
        """
        The object from which the name attribute is to be removed.
        :param name: name of the attribute which is to be removed.
        :type name: attribute.
        :return: For any case name attribute is defined or not, it will not be allowed to unbind and catching exception.
        """
        try:
            if name in self.__dict__:
                raise self._ConstError
            else:
                raise self._NameError
        except self._ConstError:
            LOGGER.error(f"Error: Can't unbind const {name}")
        except self._NameError:
            LOGGER.error(f"Error: const {name} not binded")


sys.modules[__name__] = _final()  # type: ignore
