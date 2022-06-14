# -*- coding: utf-8 -*-
# !/usr/bin/python
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
"""Exception module to declare CTException class."""

import logging

from pprint import pformat
from commons import errorcodes as errcodes

LOGGER = logging.getLogger(__name__)


class CTException(Exception):
    """Exception class for CT failures."""

    def __init__(self, ct_error, msg=None, **kwargs) -> None:
        """
        Create an CTException.
        :param ct_error: CTError object.
        :param msg      : String error message from user.
        :param **kwargs : All other keyword arguments will be stored in self.kwargs.
        :raises TypeError: If ctp_error is not a CTError object.
        """
        super().__init__()
        if not isinstance(ct_error, errcodes.CTError):
            raise ct_error from AssertionError

        self.ct_error = ct_error
        self.message = msg
        self.kwargs = kwargs  # Dictionary of 'other' information

    def __str__(self):
        """Return human-readable string representation of this exception"""
        return "CTException: EC({})\nError Desc: {}\nError Message:" \
               " {}\nOther info:\n{}".format(self.ct_error.code,
                                             self.ct_error.desc,
                                             self.message,
                                             pformat(self.kwargs))


class CortxTestException(Exception):
    """Intended for use to raise test errors with using error codes."""

    def __init__(self, msg=None) -> None:
        """
        Create a test exception
        :param msg: String error message from user.
        """
        super().__init__()
        self.message = msg

    def __str__(self):
        """Representation of this exception."""
        return f"TestException: with Error Message {self.message}:"


class EncodingNotSupported(Exception):
    """Intended for use to raise encoding errors."""

    def __init__(self, msg=None) -> None:
        """
        Create a encoding exception
        :param msg: String error message from user.
        """
        super().__init__()
        self.message = msg

    def __str__(self):
        """Representation of this exception."""
        return f"EncodingException: with Error Message {self.message}:"
