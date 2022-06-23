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
import string
from secrets import SystemRandom
from typing import Union

from commons import error_messages as errmsg
from commons import errorcodes as err
from commons.constants import S3_ENGINE_RGW
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils import s3_utils
from commons.utils import system_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.s3.s3_common_test_lib import create_s3_acc
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib

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
            "delete_markers": M
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
    :keyword "expected_flags": Dictionary of List Object Versions flags to verify
    :keyword "expected_error": Error message string to verify in case, error is expected
    :keyword "list_params": Dictionary of query parameters to pass List Object Versions call
    """
    LOG.info("Fetching bucket object versions list")
    expected_flags = kwargs.get("expected_flags", None)
    expected_error = kwargs.get("expected_error", None)
    list_params = kwargs.get("list_params", None)
    try:
        if list_params:
            list_response = s3_ver_test_obj.list_object_versions(bucket_name=bucket_name,
                                                                 optional_params=list_params)
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
        LOG.info("expected_versions is %s and keys is %s",expected_versions,
                 expected_versions.keys())
        LOG.debug("Expected versions: %s", expected_versions)
        LOG.debug("Actual versions in list reponse: %s", resp_dict)
        for key in expected_versions.keys():
            for version in expected_versions[key]["versions"].keys():
                assert_utils.assert_in(version, list(resp_dict["versions"][key].keys()))
                is_latest = True if expected_versions[key]["is_latest"] == version else False
                actual_is_latest = resp_dict["versions"][key][version]["is_latest"]
                assert_utils.assert_equal(is_latest, actual_is_latest)
                assert_utils.assert_equal(expected_versions[key]["versions"][version],
                                          resp_dict["versions"][key][version]["etag"])
                expected_version_count += 1
            for delete_marker in expected_versions[key]["delete_markers"]:
                if delete_marker != "DMO_DELETEMARKERID_PLACEHOLDER":
                    assert_utils.assert_in(delete_marker,
                                           list(resp_dict["delete_markers"][key].keys()))
                    is_latest = True \
                                if expected_versions[key]["is_latest"] == delete_marker else False
                    actual_is_latest = resp_dict["delete_markers"][key][delete_marker]["is_latest"]
                    assert_utils.assert_equal(is_latest, actual_is_latest)
                else:
                    dm_id = list(resp_dict["delete_markers"][key].keys())[0]
                    assert_utils.assert_not_equal(dm_id, "null",
                                                  "Check DeleteObjects generates non-null delete "
                                                  "marker VersionId in versioning enabled bucket")
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

def check_get_head_object_version(s3_test_obj: S3TestLib, s3_ver_test_obj: S3VersioningTestLib,
                                  bucket_name: str, object_name: str, **kwargs) -> None:
    """
    Verify GET/HEAD Object response for specified version/object

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param s3_ver_test_obj: S3VersioningTestLib object to perform S3 versioning calls
    :param bucket_name: Target bucket name
    :param object_name: Target object name
    :keyword "etag": Expected ETag of the version/object
    :keyword "get_error_msg": Error message to verify for GET Object
    :keyword "head_error_msg": Error message to verify for HEAD Object
    :keyword "version_id": version ID for GET/HEAD Object call. In case it is not specified,
    object is retrieved instead of a specific version.
    """
    etag = kwargs.get("etag", None)
    get_error_msg = kwargs.get("get_error_msg", None)
    head_error_msg = kwargs.get("head_error_msg", None)
    version_id = kwargs.get("version_id", None)
    LOG.info("Verifying GET Object with VersionId response")
    try:
        if version_id:
            get_response = s3_ver_test_obj.get_object_version(bucket_name, object_name,
                                                              version_id=version_id)
        else:
            get_response = s3_test_obj.get_object(bucket=bucket_name, key=object_name,
                                                  skip_polling=True)
        assert_utils.assert_true(get_response[0], get_response[1])
        if version_id:
            assert_utils.assert_equal(get_response[1]["VersionId"], version_id)
        if etag:
            assert_utils.assert_equal(get_response[1]["ETag"], etag)
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
            head_response = s3_test_obj.object_info(bucket_name=bucket_name, key=object_name)
        assert_utils.assert_true(head_response[0], head_response[1])
        if version_id:
            assert_utils.assert_equal(head_response[1]["VersionId"], version_id)
        if etag:
            assert_utils.assert_equal(head_response[1]["ETag"], etag)
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
    :keyword "version_id": Target version ID for GET/HEAD Object call.
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
                    bucket_name: str, file_paths: list, obj_list: list = None,
                    pre_obj_list: list = None) -> dict:
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
                           "version_history": [version_id1],
                           "is_latest": "version_id1",
            ...
            }
    """
    try:
        bucket_exists, _ = s3_test_obj.head_bucket(bucket_name)
        if bucket_exists:
            LOG.info("Bucket exists: %s, skipping bucket creation", bucket_name)
    except CTException as error:
        if errmsg.NOT_FOUND_ERR in error.message:
            LOG.info("Creating bucket: %s", bucket_name)
            resp = s3_test_obj.create_bucket(bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            LOG.error("Encountered exception in HEAD bucket: %s", error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error
    versions = {}
    if pre_obj_list:
        LOG.info("Uploading objects before setting bucket versioning state")
        for object_name in pre_obj_list:
            file_path = SystemRandom().choice(file_paths)   # nosec
            upload_version(s3_test_obj, bucket_name=bucket_name, file_path=file_path,
                           object_name=object_name, versions_dict=versions,
                           is_unversioned=True)

    if obj_list:
        for versioning_config, object_name, count in obj_list:
            resp = s3_ver_test_obj.put_bucket_versioning(bucket_name=bucket_name,
                                                         status=versioning_config)
            assert_utils.assert_true(resp[0], resp[1])
            for _ in range(count):
                file_path = SystemRandom().choice(file_paths)  # nosec
                chk_null_version = False if versioning_config == "Enabled" else True
                upload_version(s3_test_obj, bucket_name=bucket_name, file_path=file_path,
                               object_name=object_name, versions_dict=versions,
                               chk_null_version=chk_null_version)
    return versions


def upload_version(s3_test_obj: Union[S3TestLib, S3MultipartTestLib], bucket_name: str,
                   object_name: str, file_path: str, versions_dict: dict, **kwargs) -> None:
    """ Upload an object(Multipart/Regular) to a versioning enabled/suspended bucket and return
    dictionary of uploaded versions.

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param bucket_name: Bucket name for calling PUT Object
    :param object_name: Object name for calling PUT Object
    :param file_path: File path that can be used for PUT Object call
    :param versions_dict: Dictionary to be updated with uploaded version metadata
    :keyword chk_null_version: True, if 'null' version id is expected, else False
    :keyword is_unversioned: Set to true if object is uploaded to an unversioned bucket
        Can be used for setting up pre-existing objects before enabling/suspending bucket
        versioning
    :keyword is_multipart: True if upload version of object is multipart
    :keyword total_parts: Total number of parts used in multipart upload
    :keyword file_size: Size of the object, multiple of 1MB
    """
    chk_null_version = kwargs.get("chk_null_version", False)
    is_unversioned = kwargs.get("is_unversioned", False)
    is_multipart = kwargs.get("is_multipart", False)
    total_parts = kwargs.get("total_parts", 2)
    file_size = kwargs.get("file_size", 10)
    if is_multipart:
        res = s3_test_obj.complete_multipart_upload_with_di(
            bucket_name, object_name, file_path, total_parts=total_parts, file_size=file_size)
    else:
        if not system_utils.path_exists(file_path):
            system_utils.create_file(file_path, file_size)
        res = s3_test_obj.put_object(bucket_name=bucket_name, object_name=object_name,
                                     file_path=file_path)
    assert_utils.assert_true(res[0], res[1])
    if is_unversioned:
        version_id = "null"
    else:
        version_id = res[1].get("VersionId", "null")
        if chk_null_version:
            assert_utils.assert_equal("null", version_id)
        else:
            assert_utils.assert_not_equal("null", version_id)

    if object_name not in versions_dict:
        versions_dict[object_name] = {}
        versions_dict[object_name]["versions"] = {}
        versions_dict[object_name]["delete_markers"] = []
        versions_dict[object_name]["version_history"] = []
        versions_dict[object_name]["is_latest"] = None
    if version_id == "null":
        if "null" in versions_dict[object_name]["delete_markers"]:
            versions_dict[object_name]["delete_markers"].remove("null")
            versions_dict[object_name]["version_history"].remove("null")
    versions_dict[object_name]["versions"][version_id] = res[1]["ETag"]
    versions_dict[object_name]["version_history"].append(version_id)
    versions_dict[object_name]["is_latest"] = version_id


def delete_version(s3_test_obj: S3TestLib, s3_ver_test_obj: S3VersioningTestLib, bucket_name: str,
                   object_name: str, versions_dict: dict, version_id: str = None,
                   check_deletemarker: bool = False) -> None:
    """ Delete object to a versioning enabled/suspended bucket and return dictionary of uploaded
    versions

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param s3_ver_test_obj: S3VersioningTestLib object to perform S3 calls
    :param bucket_name: Bucket name for calling DELETE Object
    :param object_name: Object name for calling DELETE Object
    :param version_id: Version ID to specify when calling DELETE Object
    :param versions_dict: Dictionary to be updated with uploaded version metadata
    :param check_deletemarker: True, if response needs to be checked for DeleteMarker flag
        else False. Default: False
    """
    if version_id:
        res = s3_ver_test_obj.delete_object_version(bucket=bucket_name, key=object_name,
                                                    version_id=version_id)
    else:
        res = s3_test_obj.delete_object(bucket_name=bucket_name, obj_name=object_name)

    assert_utils.assert_true(res[0], res[1])
    if check_deletemarker:
        assert_utils.assert_true(res[1]["DeleteMarker"], res[1])

    if version_id:
        assert_utils.assert_equal(version_id, res[1]["VersionId"])
        if version_id in versions_dict[object_name]["versions"].keys():
            versions_dict[object_name]["versions"].pop(version_id)
        else:
            versions_dict[object_name]["delete_markers"].remove(version_id)

        versions_dict[object_name]["version_history"].remove(version_id)
        if version_id == versions_dict[object_name]["is_latest"]:
            if len(versions_dict[object_name]["version_history"]) == 0:
                versions_dict[object_name]["is_latest"] = None
            else:
                versions_dict[object_name]["is_latest"] =  \
                    versions_dict[object_name]["version_history"][-1]
    else:
        dm_count = len(versions_dict[object_name]["delete_markers"])
        if S3_ENGINE_RGW != CMN_CFG["s3_engine"] or dm_count == 0:
            # Additional delete markers are not placed for an object in RGW
            dm_id = res[1]["VersionId"]
            if dm_id == "null":
                # Remove null version id from version list and history if it exists
                if "null" in versions_dict[object_name]["versions"].keys():
                    versions_dict[object_name]["versions"].pop("null")
                    versions_dict[object_name]["version_history"].remove("null")
            versions_dict[object_name]["delete_markers"].append(dm_id)
            versions_dict[object_name]["version_history"].append(dm_id)
            versions_dict[object_name]["is_latest"] = dm_id


# pylint: disable=too-many-branches
# pylint: disable-msg=too-many-statements
def delete_objects(s3_test_obj: S3TestLib, bucket_name: str, versions_dict: dict,
                   obj_ver_list: list, quiet: bool = False,
                   is_versioned: bool = True, expected_error: str = None) -> None:
    """
    Delete multiple objects with versioning support and check response.

    :param s3_test_obj: S3TestLib object to perform S3 calls
    :param bucket_name: Bucket name for calling DELETE Objects
    :param versions_dict: Dictionary to be updated with deleted key/version metadata
    :param obj_ver_list: List of tuples with key and version id details for DeleteObjects call
    :param quiet: Enable quiet mode when performing DeleteObjects
    :param is_versioned: Set to true if bucket versioning is enabled, False if Suspended
    :param expected_error: Error message string to verify in case, error is expected
    """
    dmo_list = []
    for obj, ver in obj_ver_list:
        if ver is not None:
            dmo_list.append({"Key": obj, "VersionId": ver})
        else:
            dmo_list.append({"Key": obj})
    try:
        resp = s3_test_obj.delete_multiple_objects(bucket_name=bucket_name, quiet=quiet,
                                                   prepared_obj_list=dmo_list)
    except CTException as error:
        LOG.error(error)
        dmo_error = error
    if expected_error is not None:
        assert_utils.assert_in(expected_error, dmo_error.message, dmo_error)
        # If error is expected, check the error message and skip the further validation
        return
    assert_utils.assert_true(resp[0], resp[1])
    delete_result = sorted(resp[1]["Deleted"])
    if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
        assert_utils.assert_equal(sorted(dmo_list), delete_result,
                                  "DeleteObjects returned unexpected DeleteResult response")
    else:
        trimmed_delete_result = []
        for entry in delete_result:
            obj = entry["Key"]
            v_id = entry.get("VersionId", None)
            if v_id is None:
                trimmed_delete_result.append({"Key": obj})
            else:
                trimmed_delete_result.append({"Key": obj, "VersionId": v_id})
        assert_utils.assert_equal(sorted(dmo_list), trimmed_delete_result,
                                  "DeleteObjects returned unexpected DeleteResult response")
    update_versions_dict_dmo(versions_dict, delete_result, is_versioned)


def update_versions_dict_dmo(versions_dict: dict, delete_result: list, is_versioned: bool = True):
    """
    Update versions dictionary for DeleteResult returned by DeleteObjects call.

    :param versions_dict: Dictionary to be updated with deleted key/version metadata
    :param is_versioned: Set to true if bucket versioning is enabled, False if Suspended
    :param delete_result: DeleteResult returned in DeleteObjects call
    """
    for delete_entry in delete_result:
        obj = delete_entry["Key"]
        ver = delete_entry("VersionId", None)
        if ver is not None:
            if ver in versions_dict[obj]["versions"].keys():
                versions_dict[obj]["versions"].pop(ver)
            else:
                versions_dict[obj]["delete_markers"].remove(ver)

            versions_dict[obj]["version_history"].remove(ver)
            if ver == versions_dict[obj]["is_latest"]:
                versions_dict[obj]["is_latest"] =  versions_dict[obj]["version_history"][-1]
        else:
            if is_versioned:
                if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
                    # DeleteMarker not returned in response for RGW
                    dm_id = "DMO_DELETEMARKERID_PLACEHOLDER"
                else:
                    dm_id = delete_entry["DeleteMarkerVersionId"]
            else:
                dm_id = "null"

            if dm_id == "null":
                # Remove null version id from version list and history if it exists
                if "null" in versions_dict[obj]["versions"].keys():
                    versions_dict[obj]["versions"].pop("null")
                    versions_dict[obj]["version_history"].remove("null")
            versions_dict[obj]["delete_markers"].append(dm_id)
            versions_dict[obj]["version_history"].append(dm_id)
            versions_dict[obj]["is_latest"] = dm_id


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
        s3_ver_test_obj.delete_object_version(bucket=bucket_name, key=version["Key"],
                                              version_id=version["VersionId"])


def get_tag_key_val_pair(key_ran: tuple = (1, 128), val_ran: tuple = (0, 256),
                         uni_char: str = "+-=._:/@") -> dict:
    """
    Get random string for TAG's key-value pair within given length range

    :param key_ran: Length Limit for Key: Minimum 1, Maximum 128.
    :param val_ran: Length Limit for Value: Minimum 0, Maximum 256.
    :param uni_char: Allowed unique characters
    :return: dict {key,val}
    """
    tag_char = string.ascii_letters + string.digits + uni_char
    key_len = SystemRandom().randrange(key_ran[0], key_ran[1]+1)
    key = ''.join([SystemRandom().choice(tag_char) for _ in range(key_len)])
    val_len = SystemRandom().randrange(val_ran[0], val_ran[1]+1)
    val = ''.join([SystemRandom().choice(tag_char) for _ in range(val_len)])
    return {'Key': key, 'Value': val}


def put_object_tagging(s3_tag_test_obj: S3TaggingTestLib, s3_ver_test_obj: S3VersioningTestLib,
                       bucket_name: str, object_name: str, version_tag: dict, **kwargs) -> tuple:
    """
    Set the supplied/generated tag_set to an object that already exists in a bucket.

    :param s3_tag_test_obj: S3TaggingTestLib instance
    :param s3_ver_test_obj: S3VersioningTestLib instance
    :param bucket_name: Name of the bucket.
    :param object_name: Name of the object.
    :param version_tag: Dictionary to be updated with uploaded TagSet data
    :keyword version_id: Version ID associated with given object
    :keyword versions_dict: Dictionary to to fetch the latest version ID in case of un-versioned
    bucket when NO version ID specified for Put object Tag
    :keyword tag_count: Count of TAGs to be generated and put to given object
    :keyword tag_key_ran: Length Limit for Key: Minimum 1, Maximum 128.
    :keyword tag_val_ran: Length Limit for Value: Minimum 0, Maximum 256.
    :keyword tag_overrides: Specific TAG
    :return: tuple for lib call response
    """
    version_id = kwargs.get("version_id", None)
    versions_dict = kwargs.get("versions_dict", None)
    tag_count = kwargs.get("tag_count", 1)
    tag_key_ran = kwargs.get("tag_key_ran", [(1, 128)])
    tag_val_ran = kwargs.get("tag_val_ran", [(0, 256)])
    tag_overrides = kwargs.get("tag_overrides", None)  # Use this List of {Key: val} if not random

    tag_set = []
    if tag_overrides is None:
        for tag_no in range(tag_count):
            try:
                key_temp = tag_key_ran[tag_no]
                val_temp = tag_val_ran[tag_no]
            except IndexError:
                key_temp = (1, 128)
                val_temp = (0, 256)
            tag_set.append(get_tag_key_val_pair(key_ran=key_temp, val_ran=val_temp))
    else:
        tag_set = tag_overrides

    try:
        if version_id is not None:
            resp = s3_ver_test_obj.put_obj_tag_ver(bucket_name=bucket_name,
                                                   object_name=object_name,
                                                   version=version_id, tags={'TagSet': tag_set})
            version_tag[object_name][version_id] = tag_set
        else:
            resp = s3_tag_test_obj.set_object_tag(bucket_name=bucket_name, obj_name=object_name,
                                                  tags={'TagSet': tag_set})
            # Get the latest version ID to which put object tag is updated when no version ID
            # specified
            if versions_dict is not None:
                version_id = versions_dict[object_name]["version_history"][-1]
                version_tag[object_name][version_id] = tag_set
    except CTException as error:
        LOG.exception(error)
        return False, error
    return resp


def get_object_tagging(s3_tag_test_obj: S3TaggingTestLib, s3_ver_test_obj: S3VersioningTestLib,
                       bucket_name: str = None, object_name: str = None, **kwargs) -> tuple:
    """
    Get the tag set value for object with or without version ID.

    :param s3_tag_test_obj: S3TaggingTestLib instance
    :param s3_ver_test_obj: S3VersioningTestLib instance
    :param bucket_name: Name of the bucket.
    :param object_name: Name of the object.
    :keyword version_id: Version ID associated with given object
    :return: tuple for lib call response
    """
    version_id = kwargs.get("version_id", None)
    try:
        if version_id is not None:
            resp = s3_ver_test_obj.get_obj_tag_ver(bucket_name=bucket_name,
                                                   object_name=object_name, version=version_id)
        else:
            resp = s3_tag_test_obj.get_object_tags(bucket_name=bucket_name, obj_name=object_name)
    except CTException as error:
        LOG.exception(error)
        return False, error
    return resp


def delete_object_tagging(s3_tag_test_obj: S3TaggingTestLib, s3_ver_test_obj: S3VersioningTestLib,
                          bucket_name: str = None, object_name: str = None, **kwargs) -> tuple:
    """
    DELETE the tag set value for object with or without version ID.

    :param s3_tag_test_obj: S3TaggingTestLib instance
    :param s3_ver_test_obj: S3VersioningTestLib instance
    :param bucket_name: Name of the bucket.
    :param object_name: Name of the object.
    :keyword version_id: Version ID associated with given object
    :return: tuple for lib call response
    """
    version_id = kwargs.get("version_id", None)
    try:
        if version_id is not None:
            resp = s3_ver_test_obj.delete_obj_tag_ver(bucket_name=bucket_name,
                                                      object_name=object_name, version=version_id)
        else:
            resp = s3_tag_test_obj.delete_object_tagging(bucket_name=bucket_name,
                                                         obj_name=object_name)
    except CTException as error:
        LOG.exception(error)
        return False, error
    return resp

def initiate_upload_list_mpu(self, bucket_name, object_name, **kwargs):
    """
    This initialises multipart, upload parts, list parts, complete mpu and return the
    response and mpu id
    """
    is_part_upload = kwargs.get("is_part_upload", False)
    is_lst_mpu = kwargs.get("is_lst_mpu", False)
    parts = kwargs.get("parts", None)
    res = self.s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
    mpu_id = res[1]["UploadId"]
    parts_details = []
    if is_part_upload and is_lst_mpu:
        self.log.info("Uploading parts")
        resp = self.s3_mp_test_obj.upload_parts_parallel(mpu_id, bucket_name,
                                                          object_name, parts=parts)
        assert_utils.assert_not_in("VersionId", resp[1])
        for i in resp[1]['Parts']:
            parts_details.append({"PartNumber": i['PartNumber'],
                                  "ETag": i["ETag"]})
        sorted_lst = sorted(parts_details, key=lambda x: x['PartNumber'])
        res = self.s3_mp_test_obj.list_parts(mpu_id, bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_in("VersionId", resp[1])
        self.log.info("List Multipart uploads")
        return mpu_id, resp, sorted_lst
    return mpu_id
