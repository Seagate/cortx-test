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
# Python library contains methods which allows you to perform bucket ACL
#
"""ACL operations using boto3."""

import copy
import logging
import boto3
from botocore.exceptions import ClientError
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.s3_utils import poll
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_acl import Acl

LOGGER = logging.getLogger(__name__)


class S3AclTestLib(Acl):
    """Initialising s3 connection and including methods for bucket and object ACL operations."""

    def __init__(
            self,
            access_key: str = ACCESS_KEY,
            secret_key: str = SECRET_KEY,
            endpoint_url: str = S3_CFG["s3_url"],
            s3_cert_path: str = S3_CFG["s3_cert_path"],
            **kwargs) -> None:
        """
        Method initializes members of S3AclTestLib and its parent class.

        :param access_key: access key
        :param secret_key: secret key
        :param endpoint_url: endpoint url
        :param s3_cert_path: s3 certificate path
        :param region: region
        :param aws_session_token: aws_session_token
        :param debug: debug mode
        """
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        self.sync_delay = S3_CFG["sync_delay"]
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def get_object_acl(
            self,
            bucket: str = None,
            object_key: str = None) -> tuple:
        """
        Getting object acl attributes.

        :param bucket: Name of the bucket
        :param object_key: Key of object
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Getting object acl.")
            object_acl = poll(super().get_object_acl, bucket, object_key, timeout=self.sync_delay)
            LOGGER.debug(object_acl)
            response = {"Owner": object_acl.owner, "Grants": object_acl.grants}
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.get_object_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def get_bucket_acl(self, bucket_name: str = None) -> tuple:
        """
        Retrieving bucket acl attributes.

        :param bucket_name: Name of the bucket
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Getting bucket acl.")
            bucket_acl = poll(super().get_bucket_acl, bucket_name, timeout=self.sync_delay)
            LOGGER.debug(bucket_acl)
            response = bucket_acl.owner, bucket_acl.grants
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.get_bucket_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    # pylint: disable=too-many-arguments
    def copy_object_acl(self,
                        source_bucket: str = None,
                        source_object: str = None,
                        dest_bucket: str = None,
                        dest_object: str = None,
                        acl: str = None) -> tuple:
        """
        Creates a copy of an object that is already stored in Seagate S3 with acl.

        :param source_bucket: The name of the source bucket.
        :param source_object: The name of the source object.
        :param dest_bucket: The name of the destination bucket.
        :param dest_object: The name of the destination object.
        :param acl: The canned ACL to apply to the object.
            ACL='private'|'public-read'|'public-read-write'|'authenticated-read'|'aws-exec-read'|
            'bucket-owner-read'|'bucket-owner-full-control'
        :return: True, dict.
        """
        try:
            response = poll(self.s3_client.copy_object,
                            Bucket=dest_bucket,
                            CopySource=f"/{source_bucket}/{source_object}",
                            Key=dest_object,
                            ACL=acl)

            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.copy_object_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return response, response

    def put_object_acl(
            self,
            bucket_name: str = None,
            object_name: str = None,
            acl: dict = None) -> tuple:
        """
        Set the access control list of an Amazon s3 object.

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param acl: Dictionary defining the ACL consisting of grants and permissions
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Applying acl to existing object")
            response = super().put_object_acl(bucket_name, object_name, acl)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_object_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_object_acp(
            self,
            bucket_name: str = None,
            object_name: str = None,
            acp: dict = None) -> tuple:
        """
        Set the access control policy of an Amazon s3 object.

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param acp: Dictionary defining the ACP consisting of grants and permissions
        :return: response
        """
        try:
            LOGGER.info("Applying acl to existing object")
            response = super().put_object_acp(bucket_name, object_name, acp)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_object_acp.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def add_grantee(
            self,
            bucket_name: str = None,
            object_name: str = None,
            grantee_id: str = None,
            permission: str = None) -> tuple:
        """
        Add a grantee with given ACL permission to a object present in a bucket.

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param grantee_id: Canonical id of account
        :param permission: Permission to apply to a object
                           eg. 'FULL_CONTROL'|'READ'|'WRITE'|'READ_ACP'|
                               'WRITE_ACP'|READ_WRITE'
        :return: response in dict
        """
        try:
            # Get the object's current ACL
            acl = self.get_object_acl(bucket_name, object_name)[1]
            # Add a new grant to the current ACL
            new_grant = {
                "Grantee": {
                    "ID": grantee_id,
                    "Type": "CanonicalUser", },
                "Permission": permission,
            }
            # If we don't want to modify the original ACL variable, then we
            # must do a deepcopy
            modified_acl = copy.deepcopy(acl)
            modified_acl["Grants"].append(new_grant)
            LOGGER.info(modified_acl)
            response = super().put_object_acp(bucket_name, object_name, modified_acl)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.add_grantee.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_object_canned_acl(
            self,
            bucket_name: str = None,
            key: str = None,
            acl: str = None,
            access_control_policy: dict = None,
            **kwargs) -> tuple:
        """
        To set the access control list (ACL) permissions.

        for an object that already exists in a bucket
        :param bucket_name: Name of the bucket.
        :param key: Name of the existing object.
        :param acl: The canned ACL to apply to the object.
                     eg. 'private'|'public-read'|'public-read-write'|
                    'authenticated-read'|'aws-exec-read'|
                    'bucket-owner-read'|'bucket-owner-full-control'
        :param access_control_policy: Contains the elements
        that set the ACL permissions for an object per grantee.
        # :param grant_full_control: Gives the grantee READ,
        # READ_ACP, and WRITE_ACP permissions on the object.
        # :param grant_read: Allows grantee to read the object data and its metadata.
        # :param grant_read_acp: Allows grantee to read the object ACL.
        # :param grant_write: Allows grantee to create,
        # overwrite, and delete any object in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
        :return: dict
        """
        try:
            kwargs["grant_full_control"] = kwargs.get(
                "grant_full_control", None)
            kwargs["grant_read"] = kwargs.get("grant_read", None)
            kwargs["grant_read_acp"] = kwargs.get("grant_read_acp", None)
            kwargs["grant_write"] = kwargs.get("grant_write", None)
            kwargs["grant_write_acp"] = kwargs.get("grant_write_acp", None)
            LOGGER.info("Setting canned acl to existing object")
            response = super().put_object_canned_acl(
                bucket_name,
                key,
                acl=acl,
                access_control_policy=access_control_policy,
                **kwargs)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_object_canned_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_object_with_acl2(
            self,
            bucket_name: str = None,
            key: str = None,
            file_path: str = None,
            **kwargs) -> tuple:
        """
        To set both grant_full_control, grant_read acl while adding an object to a bucket.

        :param bucket_name: Name of the bucket
        :param key: Name of the object
        :param file_path: Path of the file
        # :param grant_full_control: Gives the grantee
        # READ, READ_ACP, and WRITE_ACP permissions on the object.
        # :param grant_read: Allows grantee to read the object data and its metadata.
        :return: dict
        """
        try:
            kwargs["grant_full_control"] = kwargs.get(
                "grant_full_control", None)
            kwargs["grant_read"] = kwargs.get("grant_read", None)
            LOGGER.info("Setting acl to new object")
            response = super().put_object_with_acl2(
                bucket_name, key, file_path, **kwargs)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_object_with_acl2.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_object_with_acl(
            self,
            bucket_name: str = None,
            key: str = None,
            file_path: str = None,
            acl: str = None,
            **kwargs) -> tuple:
        """
        To set acl while adding an object to a bucket.

        :param bucket_name: Name of the bucket
        :param key: Name of the object
        :param acl: The canned ACL to apply to the object.
                    eg. 'private'|'public-read'|'public-read-write'|
                    'authenticated-read'|'aws-exec-read'|
                    'bucket-owner-read'|'bucket-owner-full-control'
        :param file_path: Path of the file
        # :param grant_full_control: Gives the grantee
        # READ, READ_ACP, and WRITE_ACP permissions on the object.
        # :param grant_read: Allows grantee to read the object data and its metadata.
        # :param grant_read_acp: Allows grantee to read the object ACL.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
        :return: dict
        """
        try:
            kwargs["grant_full_control"] = kwargs.get(
                "grant_full_control", None)
            kwargs["grant_read"] = kwargs.get("grant_read", None)
            kwargs["grant_read_acp"] = kwargs.get("grant_read_acp", None)
            kwargs["grant_write_acp"] = kwargs.get("grant_write_acp", None)
            LOGGER.info("Setting acl to new object")
            response = super().put_object_with_acl(bucket_name,
                                                   key=key,
                                                   file_path=file_path,
                                                   acl=acl,
                                                   **kwargs)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_object_with_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def create_bucket_with_acl(
            self,
            bucket_name: str = None,
            acl: str = None,
            **kwargs) -> tuple:
        """
        Create bucket with given acl and grant permissions.

        :param bucket_name: Name of the bucket
        :param acl: The canned ACL to apply to the bucket.
        e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'
        # :param grant_full_control: Allows grantee the read,
        # write, read ACP, and write ACP permissions on the bucket.
        # :param grant_read: Allows grantee to list the objects in the bucket.
        # :param grant_read_acp: Allows grantee to read the bucket ACL.
        # :param grant_write: Allows grantee to create,
        # overwrite, and delete any object in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: dict
        """
        try:
            kwargs["grant_full_control"] = kwargs.get(
                "grant_full_control", None)
            kwargs["grant_read"] = kwargs.get("grant_read", None)
            kwargs["grant_read_acp"] = kwargs.get("grant_read_acp", None)
            kwargs["grant_write"] = kwargs.get("grant_write", None)
            kwargs["grant_write_acp"] = kwargs.get("grant_write_acp", None)
            LOGGER.info("Setting acl while creating object")
            response = super().create_bucket_with_acl(bucket_name,
                                                      acl,
                                                      **kwargs)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.create_bucket_with_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_bucket_acl(
            self,
            bucket_name: str = None,
            acl: str = None,
            access_control_policy: dict = None,
            **kwargs) -> tuple:
        """
        Set the permissions on a bucket using access control lists (ACL).

        :param bucket_name: Name of the bucket
        :param acl: The canned ACL to apply to the bucket.
        e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'
        :param access_control_policy: Contains the elements that
        set the ACL permissions for an object per grantee.
        # :param grant_full_control: Allows grantee the read, write,
        # read ACP, and write ACP permissions on the bucket.
        # :param grant_read: Allows grantee to list the objects in the bucket.
        # :param grant_read_acp: Allows grantee to read the bucket ACL.
        # :param grant_write: Allows grantee to create,
        # overwrite, and delete any object in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: True or False
        """
        try:
            kwargs["grant_full_control"] = kwargs.get(
                "grant_full_control", None)
            kwargs["grant_read"] = kwargs.get("grant_read", None)
            kwargs["grant_read_acp"] = kwargs.get("grant_read_acp", None)
            kwargs["grant_write"] = kwargs.get("grant_write", None)
            kwargs["grant_write_acp"] = kwargs.get("grant_write_acp", None)
            LOGGER.info("Setting acl while creating object")
            response = super().put_bucket_acl(
                bucket_name,
                acl,
                access_control_policy,
                **kwargs)
            LOGGER.info(response)
            if acl == "private":
                bucket_acl = poll(super().get_bucket_acl, bucket_name, timeout=self.sync_delay)
                LOGGER.debug(bucket_acl)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_bucket_acl.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_bucket_multiple_permission(
            self,
            bucket_name: str = None,
            **kwargs) -> tuple:
        """
        Set the permissions on a bucket using access control lists (ACL).

        :param bucket_name: Name of the bucket.
        # :param grant_full_control: Allows grantee the read, write,
        # read ACP, and write ACP permissions on the bucket.
        # :param grant_read: Allows grantee to list the objects in the bucket.
        # :param grant_read_acp: Allows grantee to read the bucket ACL.
        # :param grant_write: Allows grantee to create,
        # overwrite, and delete any object in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: bool, response
        """
        try:
            kwargs["grant_full_control"] = kwargs.get(
                "grant_full_control", None)
            kwargs["grant_read"] = kwargs.get("grant_read", None)
            kwargs["grant_read_acp"] = kwargs.get("grant_read_acp", None)
            kwargs["grant_write"] = kwargs.get("grant_write", None)
            kwargs["grant_write_acp"] = kwargs.get("grant_write_acp", None)
            LOGGER.info("Setting acl while creating object")
            response = super().put_bucket_multiple_permission(
                bucket_name,
                **kwargs)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3AclTestLib.put_bucket_multiple_permission.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    @staticmethod
    def get_bucket_acl_using_iam_credentials(
            access_key: str = None,
            secret_key: str = None,
            bucket_name: str = None) -> tuple:
        """
        Retrieving bucket acl attributes using iam credentials.

        :param access_key: ACCESS_KEY of the iam account
        :param secret_key: SECRET_KEY of the iam account
        :param bucket_name: Name of bucket
        :return: Bucket ACL or error
        :rtype: (Boolean, tuple/str)
        """
        LOGGER.info("Retrieving %s acl attrs using %s, %s.", bucket_name, access_key, secret_key)
        s3_cert_path = S3_CFG['s3_cert_path'] if S3_CFG["validate_certs"] else False
        s3_iam_resource = boto3.resource(
            "s3",
            verify=s3_cert_path,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=S3_CFG['s3_url'],
            region_name=S3_CFG['region'])
        try:
            bucket_acl = poll(s3_iam_resource.BucketAcl, bucket_name, timeout=S3_CFG["sync_delay"])
            response = bucket_acl.owner, bucket_acl.grants
            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3AclTestLib.get_bucket_acl_using_iam_credentials.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error
        finally:
            del s3_iam_resource

        return True, response
