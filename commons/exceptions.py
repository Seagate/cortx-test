# -*- coding: utf-8 -*-
# !/usr/bin/python
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
""" Exception module to declare CTException class. """

import logging

from pprint import pformat
from commons import errorcodes as errcodes

log = logging.getLogger(__name__)


class CTException(Exception):
    """
    Exception class for CT failures.
    """

    def __init__(self, ct_error, msg, **kwargs) -> None:
        """
        Create an CTException.
        :param ct_error: CTError object.
        :param msg      : String error message from user.
        :param **kwargs : All other keyword arguments will be stored in self.kwargs.
        :raises TypeError: If ctp_error is not a CTError object.
        """
        super().__init__()
        if not isinstance(ct_error, errcodes.CTError):
            raise TypeError("'ct_error' has to be of type 'CTError'!")

        self.ct_error = ct_error
        self.message = msg
        self.kwargs = kwargs  # Dictionary of 'other' information

    def __str__(self):
        """
        Return human-readable string representation of this exception
        """
        return "CTException: EC({})\nError Desc: {}\nError Message:" \
               " {}\nOther info:\n{}".format(self.ct_error.code,
                                             self.ct_error.desc,
                                             self.message,
                                             pformat(self.kwargs))
