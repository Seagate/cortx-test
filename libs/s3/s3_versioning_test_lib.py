#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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
#
"""Python Test Library using boto3 module to perform Object Versioning Operations."""

import logging

from botocore.exceptions import ClientError
from commons import errorcodes as err
from commons.exceptions import CTException

from config.s3 import S3_CFG
from commons.utils import assert_utils
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_versioning import Versioning

LOGGER = logging.getLogger(__name__)


class S3VersioningTestLib(Versioning):
    """Class initialising s3 connection and including methods for versioning operations."""

    def __init__(self,
                 access_key: str = ACCESS_KEY,
                 secret_key: str = SECRET_KEY,
                 endpoint_url: str = S3_CFG["s3_url"],
                 s3_cert_path: str = S3_CFG["s3_cert_path"],
                 **kwargs) -> None:
        """
        This method initializes members of S3VersioningTestLib and its parent class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def put_bucket_versioning(self,
                              bucket_name: str = None,
                              status: str = "Enabled") -> tuple:
        """
        Set/Update the versioning configuration of a bucket.

        :param bucket_name: Target bucket for the PUT Bucket Versioning call.
        :param status: Versioning status to be set, supported values - "Enabled" or "Suspended"
            Default = "Enabled"
        :return: response
        """
        LOGGER.info("Setting bucket versioning configuration")
        try:
            response = super().put_bucket_versioning(
                bucket_name=bucket_name, status=status)
            LOGGER.info("Successfully set bucket versioning configuration: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.put_bucket_versioning.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_bucket_versioning(self,
                              bucket_name: str = None) -> tuple:
        """
        Get the versioning configuration of a bucket.

        :param bucket_name: Target bucket for the GET Bucket Versioning call.
        :return: response
        """
        LOGGER.info("Fetching bucket versioning configuration")
        try:
            response = super().get_bucket_versioning(bucket_name=bucket_name)
            LOGGER.info("Successfully fetched bucket versioning configuration: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.get_bucket_versioning.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def list_object_versions(self,
                             bucket_name: str = None) -> tuple:
        """
        List all the versions and delete markers present in a bucket.

        :param bucket_name: Target bucket for the List Object Versions call.
        :return: response
        """
        LOGGER.info("Fetching bucket object versions list")
        try:
            response = super().list_object_versions(bucket_name=bucket_name)
            LOGGER.info("Successfully fetched bucket object versions list: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.list_object_versions.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_object_version(self,
                           bucket: str = None,
                           key: str = None,
                           version_id: str = None) -> tuple:
        """
        Get a version of an object.

        :param bucket: Target bucket for GET Object with VersionId call.
        :param key: Target key for GET Object with VersionId call.
        :param version_id: Target version ID for GET Object with VersionId call.
        :return: (Boolean, response)
        """
        LOGGER.info("Getting the version of the object")
        try:
            response = super().get_object_version(
                bucket=bucket, key=key, version_id=version_id)
            LOGGER.info("Successfully retrieved the version of the object: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.get_object_version.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def head_object_version(self,
                            bucket: str = None,
                            key: str = None,
                            version_id: str = None) -> tuple:
        """
        Get the metadata of an object's version.

        :param bucket: Target bucket for HEAD Object with VersionId call.
        :param key: Target key for HEAD Object with VersionId call.
        :param version_id: Target version ID for HEAD Object with VersionId call.
        :return: (Boolean, response)
        """
        LOGGER.info("Getting the metadata of the object's version")
        try:
            response = super().head_object_version(
                bucket=bucket, key=key, version_id=version_id)
            LOGGER.info("Successfully retrieved object version's metadata: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.head_object_version.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def delete_object_version(self,
                              bucket: str = None,
                              key: str = None,
                              version_id: str = None) -> tuple:
        """
        Delete an object's version

        :param bucket: Target bucket for DELETE Object with VersionId call.
        :param key: Target key for DELETE Object with VersionId call.
        :param version_id: Target version ID for DELETE Object with VersionId call.
        :return: (Boolean, response)
        """
        LOGGER.info("Deleting the object's version")
        try:
            response = super().delete_object_version(
                bucket=bucket, key=key, version_id=version_id)
            LOGGER.info("Successfully deleted the object's version: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.delete_object_version.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def check_list_object_versions(self,
                                   bucket_name: str = None,
                                   expected_versions: dict = None) -> None:
        """
        List all the versions and delete markers present in a bucket and verify the output

        :param bucket_name: Bucket name for calling List Object Versions
        :param expected_versions: dict containing list of version tuples, ordered from the latest
            to oldest version created i.e. latest version is at index 0 and oldest at index n-1
            for an object having n versions.

            Expected format of the dict -
                dict keys should be the object name
                tuple for version should have the format (<VersionId>, "version", <ETag>)
                tuple for delete marker should have the format (<VersionId>, "deletemarker", None)

            For eg.
                {"object1": [(<obj1-version-id-2>, 'deletemarker', None),
                             (<obj1-version-id-1>, 'version', <etag1>)],
                 "object2": [(<obj2-version-id-1>, 'version', <etag2>)]}
        """
        LOGGER.info("Fetching bucket object versions list")
        try:
            list_response = super().list_object_versions(bucket_name=bucket_name)
            LOGGER.info("Successfully fetched bucket object versions list: %s", list_response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.check_list_object_versions.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        LOGGER.info("Verifying bucket object versions list for expected contents")
        assert_utils.assert_true(list_response[0], list_response[1])
        actual_versions = list_response["Versions"]
        actual_deletemarkers = list_response["DeleteMarkers"]
        ver_idx = 0
        dm_idx = 0
        for key in sorted(expected_versions.keys()):
            expected_islatest = True
            for expected_version in expected_versions[key]:
                if expected_version[1] == "version":
                    actual_version = actual_versions[ver_idx]
                    assert_utils.assert_equal(
                        actual_version["ETag"], expected_version[2], "Version ETag mismatch")
                    ver_idx = ver_idx + 1
                else:
                    actual_version = actual_deletemarkers[dm_idx]
                    dm_idx = dm_idx + 1
                assert_utils.assert_equal(
                    actual_version["IsLatest"], expected_islatest, "Version IsLatest mismatch")
                assert_utils.assert_equal(
                    actual_version["VersionId"], expected_version[0], "Version VersionId mismatch")
                if expected_islatest:
                    expected_islatest = False
        assert_utils.assert_equal(
            len(actual_versions), ver_idx, "Unexpected Version entry count in the response")
        assert_utils.assert_equal(
            len(actual_deletemarkers), dm_idx, "Unexpected DeleteMarker entry count in the response")
        LOGGER.info("Completed verifying bucket object versions list for expected contents")

    def check_list_objects(self,
                           bucket_name: str = None,
                           expected_objects: list = None) -> None:
        """
        List bucket and verify there are single entries for each versioned object

        :param bucket_name: Bucket name for calling List Object Versions
        :param expected_objects: list containing versioned objects that should be present in
            List Objects output
        """
        LOGGER.info("Fetching bucket object list")
        try:
            list_response = super().list_objects_with_prefix(bucket_name=bucket_name, maxkeys=1000)
            LOGGER.info("Successfully fetched object list: %s", list_response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3VersioningTestLib.check_list_objects.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        LOGGER.info("Verifying bucket object versions list for expected contents")
        assert_utils.assert_true(list_response[0], list_response[1])
        actual_objects = [o["Key"] for o in list_response[1]["Contents"]]
        assert_utils.assert_equal(sorted(actual_objects),
                                  sorted(expected_objects),
                                  "List Objects response does not contain expected object names")
