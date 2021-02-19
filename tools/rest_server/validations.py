from datetime import datetime
from http import HTTPStatus

db_keys_int = ["noOfNodes", "testExecutionTime"]
db_keys_array = ["nodesHostname", "testIDLabels", "testTags"]
db_keys_bool = ["latest"]
db_keys_str = ["clientHostname", "OSVersion", "testName", "testID", "testPlanID",
               "testExecutionID", "testType", "testExecutionLabel", "testTeam",
               "testStartTime", "buildType", "buildNo", "logPath", "feature",
               "testResult", "healthCheckResult", "executionType", "testPlanLabel"]
db_keys = db_keys_int + db_keys_array + db_keys_bool + db_keys_str

extra_db_keys_str = ["issueType"]
extra_db_keys_array = ["issueIDs"]
extra_db_keys_bool = ["isRegression", "logCollectionDone"]
extra_db_keys = extra_db_keys_bool + extra_db_keys_array + extra_db_keys_str

mongodb_operators = ["$and", "$nor", "$or"]


cmi_keys_float = ["cmi"]
cmi_keys_string = ["testPlanLabel", "buildType", "buildNo"]

cmi_keys = cmi_keys_float + cmi_keys_string


def check_db_keys(json_data: dict) -> tuple:
    """
    Check if all fields present in request
    Check if unknown fields are not present

    Args:
        json_data: Data from request

    Returns:
        bool, fields
    """
    # Check if mandatory fields are present
    for key in db_keys:
        if key not in json_data:
            return False, key

    # Check if unknown fields are present
    master_set = set(db_keys).union(set(extra_db_keys)).union({"db_username", "db_password"})
    unknown_fields = set(json_data) - master_set
    if unknown_fields:
        return False, unknown_fields

    return True, None


def check_user_pass(json_data: dict) -> bool:
    """
    Check if mandatory username and password present in request

    Args:
        json_data: Data from request

    Returns:
        bool
    """
    if "db_username" in json_data and "db_password" in json_data:
        return True
    return False


def validate_search_fields(json_data: dict) -> (bool, tuple):
    if "query" not in json_data:
        return False, (HTTPStatus.BAD_REQUEST, f"Please provide query key")
    if type(json_data["query"]) != dict:
        return False, (HTTPStatus.BAD_REQUEST,
                       f"Please provide query key as dictionary")
    if "projection" in json_data and type(json_data["projection"]) != dict:
        return False, (HTTPStatus.BAD_REQUEST,
                       f"Please provide projection keys as dictionary")
    for key in json_data["query"]:
        if key not in db_keys and key not in extra_db_keys or key not in mongodb_operators:
            return False, (HTTPStatus.BAD_REQUEST,
                           f"{key} is not correct db field")
    return True, None


def validate_mandatory_db_fields(json_data: dict) -> (bool, tuple):
    """
    Validate format of each element

    Args:
        json_data: Data from request

    Returns:
        On failure returns http status code and message
        On success returns datetime in ISO 8601 format
    """
    for key in db_keys_int:
        if type(json_data[key]) != int:
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be integer")
    for key in db_keys_str:
        if type(json_data[key]) != str:
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be string")
    for key in db_keys_bool:
        if not isinstance(json_data[key], bool):
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be boolean")
    for key in db_keys_array:
        if type(json_data[key]) != list:
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be list")
        else:
            for item in json_data[key]:
                if type(item) != str:
                    return False, (HTTPStatus.BAD_REQUEST, f"{item} in {key} should be string")
    try:
        test_start_time = datetime.fromisoformat(json_data["testStartTime"])
    except ValueError:
        return False, (HTTPStatus.BAD_REQUEST, "testStartTime should be in ISO 8601 format")
    return True, test_start_time


def validate_extra_db_fields(json_data: dict) -> (bool, tuple):
    """
    Validate format of extra fields in request

    Args:
        json_data: Data from request

    Returns:
        On failure returns http status code and message
        On success returns True
    """
    for key in extra_db_keys_bool:
        if key in json_data and type(json_data[key]) != bool:
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be boolean")
    for key in extra_db_keys_str:
        if key in json_data and type(json_data[key]) != str:
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be string")
    for key in extra_db_keys_array:
        if key in json_data and not isinstance(json_data[key], list):
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be list")
        if key in json_data:
            for item in json_data[key]:
                if not isinstance(item, str):
                    return False, (HTTPStatus.BAD_REQUEST, f"{item} in {key} should be string")
    return True, None


def validate_update_request(json_data: dict) -> (bool, tuple):
    """
    Validate format of fields in update request

    Args:
        json_data: Data from request

    Returns:
        On failure returns http status code and message
        On success returns True
    """
    update_keys = ["filter", "update"]
    for key in update_keys:
        if key not in json_data:
            return False, (HTTPStatus.BAD_REQUEST, f"Please provide {update_keys} keys")
    for key in update_keys:
        if type(json_data[key]) != dict:
            return False, (HTTPStatus.BAD_REQUEST,
                           f"Please provide {update_keys} keys as dictionary")
    for key in json_data["filter"]:
        if key not in db_keys and key not in extra_db_keys:
            return False, (HTTPStatus.BAD_REQUEST,
                           f"{key} is not correct db field")
    return True, None


def check_add_cmi_request_fields(json_data: dict):
    """
    Check if all fields present in request
    Check if unknown fields are not present

    Args:
        json_data: Data from request

    Returns:
        bool, fields
    """
    # Check if mandatory fields are present
    for key in cmi_keys:
        if key not in json_data:
            return False, key

    # Check if unknown fields are present
    master_set = set(cmi_keys).union({"db_username", "db_password"})
    unknown_fields = set(json_data) - master_set
    if unknown_fields:
        return False, unknown_fields

    return True, None


def validate_add_cmi_request_fields(json_data: dict):
    """Validate fields in Add CMI request"""
    for key in cmi_keys_float:
        if not isinstance(json_data[key], float):
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be float")
    for key in cmi_keys_string:
        if not isinstance(json_data[key], str):
            return False, (HTTPStatus.BAD_REQUEST, f"{key} should be string")
    return True, None
