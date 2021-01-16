"""
Cortx-test error codes and descriptions

Provides an error data object to contain the error code and description.
The error object is in the format: NAME_OF_ERROR(code, description).

Helper functions:
    - get_error(): Searches through this module to find error objects based on the provided code or description.
    - validate_ctp_errors(): Checks for duplicate error codes and missing error descriptions.
        If implemented at the end it will validate the codes at runtime. (TBD)
"""

import sys

if sys.version >= '3.7':
    # Use dataclass decorator if running Python 3.7 or newer.
    from dataclasses import dataclass


    @dataclass
    class CTError:
        code: int
        desc: str
else:
    class CTError(object):
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
    gl = globals().copy()
    for _, vi in gl.items():
        if isinstance(vi, CTError):
            if (isinstance(info, int) and info == vi.code) \
                    or (isinstance(info, str) and info.lower() in vi.desc.lower()):
                return vi
    return


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
    gl = globals().copy()
    if code is None:
        for i, vi in gl.items():
            if not isinstance(vi, CTError):
                continue
            if vi.desc is None or vi.desc == '':
                raise Exception("{}({}): Error description cannot be empty!"
                                .format(i, vi.code))
            for j, vj in gl.items():
                if i == j:
                    continue
                if isinstance(vj, CTError) and vj.code == vi.code:
                    raise Exception("{} is duplicate error code for {} and {}"
                                    .format(vj.code, i, j))
    else:
        for _, vi in gl.items():
            if isinstance(vi, CTError) and vi.code == code:
                return False
        return True


# Cortx Test error codes below this line

# Test Case Errors  [1-999]
TEST_FAILED = CTError(1, "Test Failed")
MISSING_PARAMETER = CTError(2, "Missing Parameter")
INVALID_PARAMETER = CTError(3, "Invalid Parameter")

# CT Errors [1000-1999]
CT_CONFIG_ERROR = CTError(1000, "CTP Config Error")

# HTTP and HTTPS Errors
HTTP_ERROR = CTError(2000, "HTTP Error")

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

# Product Configuration DataBase Errors
PCD_SYNTAX_ERROR = CTError(30000, "PCD file Syntax error")
FILE_MISSING = CTError(30001, "File missing")
YAML_SYNTAX_ERROR = CTError(30002, "YAML file syntax error")
INVALID_CONFIG_FILE = CTError(30003, "Invalid configuration file")
FILE_TYPE_NOT_SUP = CTError(30004, "Type file not supported")
PCD_RENDERING_ERROR = CTError(30005, "Error during the rendering process")
PCD_FILE_ERROR = CTError(30006, "PCD file content error")
ENC_PCD_COMPONENT_MAPPING_ERROR = CTError(30007, "PCD Components not mapping to Enclosure Components")

# S3 Errors
S3_ERROR = CTError(0o0001, "S3 Error")

# RAS
RAS_ERROR = CTError(6007, "RAS Error")
