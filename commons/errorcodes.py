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
"""
Cortx-test error codes and descriptions.

Provides an error data object to contain the error code and description.
The error object is in the format: NAME_OF_ERROR(code, description).

Helper functions:
    - get_error(): Searches through this module to find error objects based on the provided code
        or description.
    - validate_ct_errors(): Checks for duplicate error codes and missing error descriptions.
        If implemented at the end it will validate the codes at runtime. (TBD)
"""

import sys
import logging
from typing import Any

LOGGER = logging.getLogger(__name__)

if sys.version >= '3.7':
    # Use dataclass decorator if running Python 3.7 or newer.
    from dataclasses import dataclass

    @dataclass
    class CTError:
        """Provides an error data object to contain the error code and description."""

        code: int
        desc: str
else:
    class CTError:
        """Provides an error data object to contain the error code and description."""

        def __init__(self, code, desc):
            """Initializer CTError to initialize error code and description."""
            self.code = code
            self.desc = desc

        def __del__(self):
            """Delete and cleanup objects"""
            del self.code
            del self.desc

        def __str__(self):
            """String representation for CTError class."""
            return f"{self.__class__.__name__}{self.__dict__}"


def get_error(info):
    """
     Retrieve an error from a provided error code or error description.

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


def validate_ct_errors(code=None) -> bool:
    """
    Validate all CT errors by checking error codes and descriptions.

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
                raise Exception(f"{i}({vali.code}): Error description cannot be empty!")
            for j, valj in glob.items():
                if i == j:
                    continue
                if isinstance(valj, CTError) and valj.code == vali.code:
                    raise Exception(f"{valj.code} is duplicate error code for {i} and {j}")
    else:
        for _, vali in glob.items():
            if isinstance(vali, CTError) and vali.code == code:
                return False
        return True
    return None

def error_handler(
        exception_detail: Any,
        error_code: int = 0,
        error_desc: Any = '') -> None:
    """
    Here logic would be developed by the each program.

    from given exception get the code and take the decision to mark test FAIL or ERROR and take
    the action accordingly. here it is considering as cterror code is 1 mark FAIL else ERROR.
    :param exception_detail: detailed exception.
    :param error_code: error code.
    :param error_desc: error description.
    """
    try:
        # check the parameter which are passed as expected type
        assert isinstance(
            error_code, int), 'failure routine parameter var1 must be int'
        assert isinstance(
            error_desc, str), 'failure routine parameter setup msg must be str'
    except AssertionError as a_err:
        raise Exception(str(a_err)) from a_err
    if exception_detail.ct_error.code:
        LOGGER.debug("Test FAILURE")
        # Mark test error in result
        LOGGER.info(error_code)
        LOGGER.info(error_desc)
        raise exception_detail from Exception
    LOGGER.error("Test FAILURE")
    LOGGER.info(error_code)
    LOGGER.info(error_desc)
    raise Exception(str(f"error code not found: {exception_detail.ct_error.code}"))


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
CSM_REST_GET_REQUEST_FAILED: Any = CTError(8109, "CSM-REST GET request failed")
CSM_REST_POST_REQUEST_FAILED: Any = CTError(8109, "CSM-REST POST request failed")
CSM_REST_PUT_REQUEST_FAILED: Any = CTError(8109, "CSM-REST PUT request failed")
CSM_REST_DELETE_REQUEST_FAILED: Any = CTError(8109, "CSM-REST DELETE request failed")


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

# S3 rest error
S3_REST_AUTHENTICATION_ERROR: Any = CTError(8107, "S3-REST Authentication Error")
S3_REST_VERIFICATION_FAILED: Any = CTError(8108, "Unexpected output fetched for S3-REST")
S3_REST_GET_REQUEST_FAILED: Any = CTError(8109, "S3-REST GET request failed")
S3_REST_POST_REQUEST_FAILED: Any = CTError(8109, "S3-REST POST request failed")
S3_REST_PUT_REQUEST_FAILED: Any = CTError(8109, "S3-REST PUT request failed")
S3_REST_DELETE_REQUEST_FAILED: Any = CTError(8109, "S3-REST DELETE request failed")
S3_REST_PATCH_REQUEST_FAILED: Any = CTError(8109, "S3-REST PATCH request failed")

# RAS
RAS_ERROR = CTError(6007, "RAS Error")

# HA
HA_BAD_CLUSTER_HEALTH = CTError(7001, "Cluster Health is not good")
HA_BAD_NODE_HEALTH = CTError(7002, "Node Health is not good")

# Generic
CLIENT_CMD_EXECUTION_FAILED = CTError(9001, "Command failed to execute on client")

# S3 IO OPERATION
S3_STOP_IO_FAILED = CTError(9002, "S3-CLI IO Stop Operation Failed")
S3_DELETE_ACC_REQUEST_FAILED = CTError(9003, "S3-CLI Delete Account Request Failed")
S3_DELETE_BUCKET_REQUEST_FAILED = CTError(9004, "S3-CLI Delete Bucket Request Failed")
S3_LOGGING_FAILED = CTError(9005, "S3-CLI Account Logging Failed")
S3_LOGOUT_FAILED = CTError(9006, "S3-CLI Account Logout Failed")
S3_START_IO_FAILED = CTError(9007, "S3-CLI IO Start Operation Failed")

# DI
S3_SET_FLAG = CTError(9008, "Unable to set flag in s3server config")
MAINTENANCE_MODE = CTError(9009, "Unable to enable maintenance mode using hctl")
UNMAINTENANCE_MODE = CTError(9010, "Unable to disable maintenance mode using hctl")
