# !/usr/bin/python
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

"""Global constant module."""

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


class _Final:
    """
    Assign the object attribute its value.

    The object from which the name attribute is to be removed.
    The object whose attributes need to be processed.
    Maintain uniqueness across module.
    """

    class _ConstError(Exception):
        pass

    class _NameError(NameError):
        pass

    class _AttributeError(AttributeError):
        pass

    def __len__(self):
        return len(self.__dict__)

    def __setattr__(self, name: Any, value: Any) -> None:
        """
        Assign the object attribute its value.

        The object whose attributes need to be processed.
        :param name: object attribute which has to be assigned.
        :param value: value with which variable is to be assigned.
        :return: If name already defined then another value cant be assigned
        and will raise error.
        """
        if name in self.__dict__:
            try:
                raise self._ConstError
            except self._ConstError:
                LOGGER.error("Error: Can't rebind const %s", str(name))
        else:
            self.__dict__[name] = value

    def __getattr__(self, name: Any) -> None:
        """
        Access the attribute value of an object and also not allowing in case of unavailability.

        :param name: The attribute of object.
        :type name: attribute.
        :return: Object value if value is available, default value in case attribute is not present
                 and returns AttributeError in case attribute is not present and default value is
                 not specified.
        """
        try:
            if name not in self.__dict__:
                raise AttributeError
        except AttributeError:
            if name not in ["_pytestfixturefunction", "__bases__", "__test__"]:
                LOGGER.error("Error: const %s not present/binded", str(name))

    def __delattr__(self, name: Any) -> None:
        """
        The object from which the name attribute is to be removed.

        :param name: name of the attribute which is to be removed.
        :type name: attribute.
        :return: For any case name attribute is defined or not, it will not be allowed to unbind
                 and catching exception.
        """
        try:
            if name in self.__dict__:
                raise self._ConstError
            raise self._NameError
        except self._ConstError:
            LOGGER.error("Error: Can't unbind const %s", str(name))
        except self._NameError:
            LOGGER.error("Error: const %s not binded", str(name))
