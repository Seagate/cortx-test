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
#
"""
Contains common functions for S3 Versioning tests.

Checks/validation logic that is common to the test methods across the versioning related test
modules should be extracted out and added to this module to reduce code duplication.

Functions added here can accept cortx-test test libraries as parameters and can contain
assertions as well, with the main aim being to have leaner and cleaner code in the test modules.
"""
import logging
import random

from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils import s3_utils
from config.s3 import S3_CFG
from libs.s3.s3_common_test_lib import create_s3_acc
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI

LOG = logging.getLogger(__name__)


def create_s3_user_get_s3lib_object(user_name: str, email_id: str,
                                    password: str) -> tuple:
    """
    Create an S3 account and return S3 versioning test library object.

    :param str user_name: Name of user to be created.
    :param str email_id: Email id for user creation.
    :param password: user password.
    :return: tuple, returns multiple values such as access_key, secret_key and S3 objects
        which are required to perform further operations.
    """
    access_key, secret_key = create_s3_acc(account_name=user_name, email_id=email_id,
                                           password=password)
    s3_obj = S3VersioningTestLib(access_key=access_key, secret_key=secret_key,
                                 endpoint_url=S3_CFG["s3_url"], region=S3_CFG["region"])
    response = (s3_obj, access_key, secret_key)
    return response

def parse_list_object_versions_response(list_response: dict) -> dict:
    """
    Parse the response object returned from List Object Versions call.

    :param list_response: Response object from List Object Versions call
    :return: dict, with the following format:
        {
            "versions": {
                    "<key_name>": {
                        "<version-id>": {
                            "etag": "Etag",
                            "is_latest": True/False
                        },
                        ...
                    },
                    ...
                }
            "version_count": N
            "deletemarkers": M
            "deletemarker_count": {
                "<key_name>": {
                        "<version-id>": {
                            "is_latest": True/False
                        },
                        ...
                    },
                    ...
                }
            }
        }
    """
    versions = {}
    deletemarkers = {}
    version_count = 0
    deletemarker_count = 0

    print(f"List response: {list_response}")
    if list_response[1].get("Versions"):
        for version in list_response[1].get("Versions"):
            key = version["Key"]
            version_id = version["VersionId"]
            if key not in versions.keys():
                versions[key] = {}
            versions[key][version_id] = {}
            versions[key][version_id]["etag"] = version["ETag"]
            versions[key][version_id]["is_latest"] = version["IsLatest"]
            version_count += 1

    if list_response[1].get("DeleteMarkers"):
        for delete_marker in list_response[1].get("DeleteMarkers"):
            key = delete_marker["Key"]
            version_id = delete_marker["VersionId"]
            if key not in deletemarkers.keys():
                deletemarkers[key] = {}
            deletemarkers[key][version_id] = {}
            deletemarkers[key][version_id]["is_latest"] = delete_marker["IsLatest"]
            deletemarker_count += 1

    response = {
        "versions": versions,
        "version_count": version_count,
        "delete_markers": deletemarkers,
        "deletemarker_count": deletemarker_count,
    }
    print(f"Parsed response: {response}")
    return response


# pylint: disable-msg=too-many-locals
def check_list_object_versions(s3_ver_test_obj: S3VersioningTestLib,
                               bucket_name: str, expected_versions: dict,
                               **kwargs) -> None:
    """
    List all the versions and delete markers present in a bucket and verify the output

    :param s3_ver_test_obj: S3VersioningTestLib object to perform S3 versioning calls
    :param bucket_name: Bucket name for calling List Object Versions
    :param expected_versions: dict containing list of versions, delete markers and flags
        Expected format of the dict -
            {"<key_name1": "versions": {"version_id1": "etag1"} ...},
                           "delete_markers": ["dm_version_id1", ...],
                           "is_latest": "version_id1",
            ...
            }
    :param **kwargs: Optional keyword arguments
        "expected_flags": Dictionary of List Object Versions flags to verify
        "expected_error": Error message string to verify in case, error is expected
        "list_params": Dictionary of query parameters to pass List Object Versions call
    """
    LOG.info("Fetching bucket object versions list")
    expected_flags = kwargs.get("expected_flags", None)
    expected_error = kwargs.get("expected_error", None)
    list_params = kwargs.get("list_params", None)
    try:
        if list_params:
            list_response = s3_ver_test_obj.list_object_versions(bucket_name=bucket_name,
                                                                 **list_params)
        else:
            list_response = s3_ver_test_obj.list_object_versions(bucket_name=bucket_name)
    except CTException as error:
        LOG.error(error)
        list_error = error

    if expected_error is not None:
        assert_utils.assert_in(expected_error, list_error.message, list_error)
        # If error is expected, assert the error message and skip validation of list response
        return

    assert_utils.assert_true(list_response[0], list_response[1])
    if expected_flags is not None:
        for flag_key, flag_value in expected_flags.items():
            assert_utils.assert_in(flag_key, list_response[1])
            assert_utils.assert_equal(flag_value, list_response[1][flag_key])

    if expected_versions is not None:
        LOG.info("Verifying bucket object versions list for expected contents")
        assert_utils.assert_true(list_response[0], list_response[1])
        expected_version_count = 0
        expected_deletemarker_count = 0

        resp_dict = parse_list_object_versions_response(list_response)
        for key in expected_versions.keys():
            for version in expected_versions[key]["versions"].keys():
                assert_utils.assert_in(version, list(resp_dict["versions"][key].keys()))
                # Work on IsLatest flag in ListObjectVersions is WIP (CORTX-30178)
                # is_latest = True if expected_versions[key]["is_latest"] == version else False
                # Uncomment once CORTX-30178 changes are available in main
                # assert_utils.assert_equal(is_latest,
                #                           resp_dict["versions"][key][version]["is_latest"])
                assert_utils.assert_equal(expected_versions[key]["versions"][version],
                                          resp_dict["versions"][key][version]["etag"])
                expected_version_count += 1
            for delete_marker in expected_versions[key]["delete_markers"]:
                assert_utils.assert_in(delete_marker, list(resp_dict["deletemarkers"][key].keys()))
                # Work on IsLatest flag in ListObjectVersions is WIP (CORTX-30178)
                # is_latest = True if key["is_latest"] == delete_marker else False
                # Uncomment once CORTX-30178 changes are available in main
                # assert_utils.assert_in(is_latest,
                #                        resp_dict["deletemarkers"][key][version]["is_latest"])
                expected_deletemarker_count += 1
        assert_utils.assert_equal(expected_version_count, resp_dict["version_count"],
                                  "Unexpected Version entry count in the response")
        assert_utils.assert_equal(expected_deletemarker_count, resp_dict["deletemarker_count"],
                                  "Unexpected DeleteMarker entry count in the response")
        LOG.info("Completed verifying bucket object versions list for expected contents")

def check_list_objects(s3_test_obj: S3TestLib, bucket_name: str,
                       expected_objects: list) -> None:
    """
    List bucket and verify there are single entries for each versioned object

    :param s3_test_obj: S3TestLib object to perform S3 versioning calls
    :param bucket_name: Bucket name for calling List Object Versions
    :param expected_objects: list containing versioned objects that should be present in
        List Objects output
    """
    LOG.info("Fetching bucket object list")
    list_response = s3_test_obj.object_list(bucket_name=bucket_name)
    assert_utils.assert_true(list_response[0], list_response[1])
    LOG.info("Verifying bucket object versions list for expected contents")
    assert_utils.assert_equal(sorted(expected_objects), sorted(list_response[1]),
                              "List Objects response does not contain expected object names")

def check_get_head_object_version(s3_ver_test_obj: S3VersioningTestLib, version_id: str,
                                  bucket_name: str, object_name: str, **kwargs) -> None:
    """
    Verify GET/HEAD Object response for specified version/object

    :param s3_ver_test_obj: S3VersioningTestLib object to perform S3 versioning calls
    :param version_id: Optional version ID for GET/HEAD Object call.
        In case it is not specified, object is retrieved instead of a specific version.
    :param bucket_name: Target bucket name
    :param object_name: Target object name
    :param **kwargs: Optional keyword arguments
        "etag": Expected ETag of the version/object
        "get_error_msg": Error message to verify for GET Object
        "head_error_msg": Error message to verify for HEAD Object
    """
    etag = kwargs.get("etag", None)
    get_error_msg = kwargs.get("get_error_msg", None)
    head_error_msg = kwargs.get("head_error_msg", None)
    LOG.info("Verifying GET Object with VersionId response")
    try:
        if version_id:
            get_response = s3_ver_test_obj.get_object_version(bucket_name, object_name,
                                                              version_id=version_id)
        else:
            get_response = s3_ver_test_obj.get_object(bucket=bucket_name, key=object_name)
        assert_utils.assert_true(get_response[0], get_response[1])
        if version_id:
            assert_utils.assert_equal(get_response[1]["ResponseMetadata"]["VersionId"],
                                      version_id)
        if etag:
            assert_utils.assert_equal(get_response[1]["ResponseMetadata"]["ETag"], etag)
        LOG.info("Successfully performed GET Object: %s", get_response)
    except CTException as error:
        LOG.error(error)
        if not get_error_msg:
            raise CTException(error.S3_CLIENT_ERROR, error.args[0]) from error
        assert_utils.assert_in(get_error_msg, error.message, error.message)
    LOG.info("Verifying HEAD Object with VersionId response")
    try:
        if version_id:
            head_response = s3_ver_test_obj.head_object_version(bucket=bucket_name,
                                                                key=object_name,
                                                                version_id=version_id)
        else:
            head_response = s3_ver_test_obj.object_info(bucket_name=bucket_name,
                                                        key=object_name)
        assert_utils.assert_true(head_response[0], head_response[1])
        if version_id:
            assert_utils.assert_equal(
                head_response[1]["ResponseMetadata"]["VersionId"], version_id)
        if etag:
            assert_utils.assert_equal(head_response[1]["ResponseMetadata"]["ETag"], etag)
        LOG.info("Successfully performed HEAD Object: %s", head_response)
    except CTException as error:
        LOG.error(error)
        if not head_error_msg:
            raise CTException(error.S3_CLIENT_ERROR, error.args[0]) from error
        assert_utils.assert_in(head_error_msg, error.message, error.message)

def download_and_check(s3_test_obj: S3TestLib, bucket_name: str, object_name: str,
                       file_path: str, download_path: str, **kwargs) -> None:
    """
    Download an object/version and verify checksum of it's contents

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param bucket_name: Target bucket name
    :param object_name: Target object name
    :param file_path: File path of the uploaded file
    :param download_path: Path for the downloaded object contents to be saved to.
    :param **kwargs: Optional keyword arguments
        "version_id": Target version ID for GET/HEAD Object call.
            In case it is not specified/None, object is retrieved instead of a specific version.
    """
    version_id = kwargs.get("version_id", None)
    expected_checksum = s3_utils.calc_checksum(file_path)
    if version_id:
        resp = s3_test_obj.object_download(bucket_name, object_name, download_path,
                                           ExtraArgs={'VersionId': version_id})
    else:
        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
    assert_utils.assert_true(resp[0], resp[1])
    download_checksum = s3_utils.calc_checksum(download_path)
    assert_utils.assert_equal(expected_checksum, download_checksum,
                              "Mismatch in object/version contents")

# pylint: disable=too-many-arguments
def upload_versions(s3_test_obj: S3TestLib, s3_ver_test_obj: S3VersioningTestLib,
                    bucket_name: str, file_paths: list, obj_list: dict,
                    pre_obj_list: list = None) -> None:
    """
    Upload objects to a versioning enabled/suspended bucket and return dictionary of uploaded
    versions

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param s3_ver_test_obj: S3VersioningTestLib object to perform S3 versioning calls
    :param bucket_name: Bucket name for calling PUT Object
    :param file_paths: List of file paths that can be used to upload versions
    :param pre_obj_list: List of object names to be uploaded before setting bucket versioning
    :param obj_list: list containing tuples containing object details and state of
        the bucket versioning configuration to be set.

        Expected format of the list -
            [("<bucket-versioning-state>", "obj-name", <version-count>), ...]
                Where "bucket-versioning-state" can be "Enabled" or "Suspended"
        For eg.
            [["Enabled", "key-obj-1", 2], ["Suspended", "key-obj-2", 1]]
    :return: dict, containing details of versions uploaded in the format below
            {"<key_name1": "versions": {"version_id1": "etag1"} ...},
                           "delete_markers": [],
                           "is_latest": "version_id1",
            ...
            }
    """
    LOG.info("Creating bucket")
    resp = s3_test_obj.create_bucket(bucket_name)
    assert_utils.assert_true(resp[0], resp[1])
    versions = {}
    if pre_obj_list:
        LOG.info("Uploading objects before setting bucket versioning state")
        for object_name in pre_obj_list:
            file_path = random.choice(file_paths) #nosec
            res = s3_test_obj.put_object(bucket_name=bucket_name, object_name=object_name,
                                         file_path=file_path)
            assert_utils.assert_true(res[0], res[1])
            
    for versioning_config, object_name, count in obj_list:
        resp = s3_ver_test_obj.put_bucket_versioning(bucket_name=bucket_name,
                                                     status=versioning_config)
        assert_utils.assert_true(resp[0], resp[1])
        for _ in range(count):
            chk_null_version = True if versioning_config == "Enabled" else False
            upload_version(s3_test_obj, bucket_name=bucket_name, file_path=file_path,
                           object_name=object_name, versions_dict=versions,
                           chk_null_version=chk_null_version)
    return versions

# pylint: disable=too-many-arguments
def upload_version(s3_test_obj: S3TestLib, bucket_name: str, object_name: str,
                   file_path: str, versions_dict: dict,
                   chk_null_version: bool = False) -> None:
    """ Upload objects to a versioning enabled/suspended bucket and return dictionary of uploaded
    versions

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param bucket_name: Bucket name for calling PUT Object
    :param object_name: Object name for calling PUT Object
    :param file_path: File path that can be used for PUT Object call
    :param chk_null_version: True, if 'null' version id is expected, else False
    :param versions_dict: Dictionary to be updated with uploaded version metadata
    """
    res = s3_test_obj.put_object(bucket_name=bucket_name, object_name=object_name,
                                 file_path=file_path)
    assert_utils.assert_true(res[0], res[1])
    version_id = res[1].get("VersionId", "null")
    if chk_null_version:
        assert_utils.assert_equal("null", version_id)
    else:
        assert_utils.assert_not_equal("null", version_id)

    if object_name not in versions_dict:
        versions_dict[object_name] = {}
        versions_dict[object_name]["versions"] = {}
        versions_dict[object_name]["delete_markers"] = []
        versions_dict[object_name]["is_latest"] = None

    versions_dict[object_name]["versions"][version_id] = res[1]["ETag"]
    versions_dict[object_name]["is_latest"] = version_id

def empty_versioned_bucket(s3_ver_test_obj: S3VersioningTestLib,
                           bucket_name: str) -> None:
    """
    Delete all versions and delete markers present in a bucket

    :param s3_ver_test_obj: S3VersioningTestLib instance
    :param bucket_name: Name of the bucket to empty
    """
    list_response = s3_ver_test_obj.list_object_versions(bucket_name=bucket_name)
    to_delete = list_response[1].get("Versions", [])
    to_delete.extend(list_response[1].get("DeleteMarkers", []))
    for version in to_delete:
        s3_ver_test_obj.delete_object_version(bucket=bucket_name,
                                              key=version["Key"],
                                              version_id=version["VersionId"])
