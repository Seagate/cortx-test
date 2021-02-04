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
"""
Cortx-test error codes and descriptions.

Provides an error data object to contain the error code and description.
The error object is in the format: NAME_OF_ERROR(code, description).

Helper functions:
    - get_error(): Searches through this module to find error objects based on the provided code
        or description.
    - validate_ctp_errors(): Checks for duplicate error codes and missing error descriptions.
        If implemented at the end it will validate the codes at runtime. (TBD)
"""

import sys
from typing import Any

if sys.version >= '3.7':
    # Use dataclass decorator if running Python 3.7 or newer.
    from dataclasses import dataclass


    @dataclass
    class CTError:
        """
        Provides an error data object to contain the error code and description.
        """
        code: int
        desc: str
else:
    class CTError:
        """
        Provides an error data object to contain the error code and description.
        """

        def __init__(self, code, desc):
            self.code = code
            self.desc = desc

        def __str__(self):
            return "{}{}".format(self.__class__.__name__, self.__dict__)


def get_error(info):
    """ Retrieve an error from a provided error code or error description.

    :param info: Error code (int) or message (str) needed to search with.
    :return: The corresponding error or None.
    """
    glob = globals().copy()
    for _, val in glob.items():
        if isinstance(val, CTError):
            if (isinstance(info, int) and info == val.code) or (
                    isinstance(info, str) and info.lower() in val.desc.lower()):
                return val
    return None


def validate_ctp_errors(code=None):
    """ Validate all CTP errors by checking error codes and descriptions.
    Check if an error code is already used for a different error.
    Check if an error is missing its description.
    If no code is provided it will go through all the errors in the file and compare the codes.

    :param code: Error code (int) to validate.
    :return: Nothing if no error code is provided.
    :return: True if the code is not used. False if it is already used by a different error.
    :raises Exception: If an error code is used in more than one error.
    """
    glob = globals().copy()
    if code is None:
        for i, vali in glob.items():
            if not isinstance(vali, CTError):
                continue
            if vali.desc is None or vali.desc == '':
                raise Exception("{}({}): Error description cannot be empty!"
                                .format(i, vali.code))
            for j, valj in glob.items():
                if i == j:
                    continue
                if isinstance(valj, CTError) and valj.code == vali.code:
                    raise Exception("{} is duplicate error code for {} and {}"
                                    .format(valj.code, i, j))
    else:
        for _, vali in glob.items():
            if isinstance(vali, CTError) and vali.code == code:
                return False
        return True


# Cortx Test error codes below this line

# Test Case Errors  [1-999]
TEST_FAILED = CTError(1, "Test Failed")
MISSING_PARAMETER = CTError(2, "Missing Parameter")
INVALID_PARAMETER = CTError(3, "Invalid Parameter")

# CT Errors [1000-1999]
CT_CONFIG_ERROR = CTError(1000, "CTP Config Error")
CT_SINGLETON_NOT_INITIALIZED = CTError(1001, "CTP Config Error")

# HTTP and HTTPS Errors
HTTP_ERROR = CTError(2000, "HTTP Error")

# RAS CT Errors
CONTROLLER_ERROR = CTError(6000, "CONTROLLER Error")

# CLI Errors
CLI_ERROR = CTError(24000, "CLI Error")
CLI_INVALID_COMMAND = CTError(24001, "CLI Invalid Command")
CLI_INVALID_ACCESS_METHOD = CTError(24002, "CLI Invalid Access Method")
CLI_COMMAND_FAILURE = CTError(24003, "CLI Command Failure")
CLI_CONTROLLER_NOT_READY = CTError(24004, "CLI Controller Not Ready")
CLI_NETWORK_VALIDATION_ERROR = CTError(24005, "CLI Network Validation Error")
CLI_INVALID_NETWORK_PARAMETER = CTError(24006, "CLI Invalid Network Parameter")
CLI_SYSTEM_NOT_READY = CTError(24007, "CLI System Not Ready")
CLI_SYSTEM_CHECK_MISSING_PARAMETER = CTError(24008, "CLI System Check Missing Parameter")
CLI_STATUS_FAILED = CTError(24009, "CLI Response Status Failed")
CLI_LOGIN_FAILED = CTError(24010, "CLI Authentication Unsuccessful")
CLI_MC_NOT_READY = CTError(24011, "CLI MC Not Ready")
CLI_CONTROLLER_CHECK_MISSING_PARAMETER = CTError(24012, "CLI Controller Check Missing Parameter")

# CSM
CSM_REST_AUTHENTICATION_ERROR: Any = CTError(8107, "CSM-REST Authentication Error")
CSM_REST_VERIFICATION_FAILED: Any = CTError(8108, "Unexpected output fetched for CSM-REST")


# Product Configuration DataBase Errors
PCD_SYNTAX_ERROR = CTError(30000, "PCD file Syntax error")
FILE_MISSING = CTError(30001, "File missing")
YAML_SYNTAX_ERROR = CTError(30002, "YAML file syntax error")
INVALID_CONFIG_FILE = CTError(30003, "Invalid configuration file")
FILE_TYPE_NOT_SUP = CTError(30004, "Type file not supported")
PCD_RENDERING_ERROR = CTError(30005, "Error during the rendering process")
PCD_FILE_ERROR = CTError(30006, "PCD file content error")
ENC_PCD_COMPONENT_MAPPING_ERROR = CTError(
    30007, "PCD Components not mapping to Enclosure Components")
INVALID_OPTION_VALUE = CTError(30008, "Invalid option and value type ")

# S3 Errors
S3_SERVER_ERROR = CTError(5007, "S3 Server Error")
S3_CLIENT_ERROR = CTError(4007, "S3 Client Error")
S3_ERROR = CTError(0o0001, "S3 Error")


# RAS
RAS_ERROR = CTError(6007, "RAS Error")
