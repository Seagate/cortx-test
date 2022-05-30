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

"""Python Library using boto3 module to perform ACL Operations."""

import logging
import os

from commons.utils.system_utils import create_file
from libs.s3.s3_core_lib import S3Lib

LOGGER = logging.getLogger(__name__)


class Acl(S3Lib):
    """Class containing methods to implement bucket and object ACL functionality."""

    def get_object_acl(
            self,
            bucket: str = None,
            object_key: str = None) -> dict:
        """
        Getting object acl attributes.

        :param bucket: Name of the bucket.
        :param object_key: Key of object.
        :return: response.
        """
        response = self.s3_resource.ObjectAcl(bucket, object_key)
        LOGGER.debug(response)

        return response

    def get_bucket_acl(self, bucket_name: str = None) -> dict:
        """
        Retrieving bucket acl attributes.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        response = self.s3_resource.BucketAcl(bucket_name)
        LOGGER.debug(response)

        return response

    def put_object_acp(
            self,
            bucket_name: str = None,
            object_name: str = None,
            acp: dict = None) -> dict:
        """
        Set the access control list of an s3 object.

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param acp: Dictionary defining the ACP consisting of grants and permissions
        :return: response.
        """
        # Set the ACL
        response = self.s3_client.put_object_acl(
            Bucket=bucket_name, Key=object_name, AccessControlPolicy=acp)

        return response

    def put_object_acl(
            self,
            bucket_name: str = None,
            object_name: str = None,
            acl: dict = None) -> dict:
        """
        Set the access control list of an s3 object.

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param acl: Dictionary defining the ACL consisting of grants and permissions
        :return: response.
        """
        # Set the ACL
        response = self.s3_client.put_object_acl(
            Bucket=bucket_name, Key=object_name, ACL=acl)

        return response

    # pylint: disable-msg=too-many-branches
    def put_object_canned_acl(self,
            bucket_name: str = None,
            key: str = None,
            acl: str = None,
            access_control_policy: str = None,
            **kwargs) -> dict:
        """
        set the access control list (ACL) permissions for an object.

        Object already exists in a bucket.
        :param bucket_name: Name of the bucket.
        :param key: Name of the existing object.
        :param acl: The canned ACL to apply to the object.
                     eg. 'private'|'public-read'|'public-read-write'|
                    'authenticated-read'|'aws-exec-read'|
                    'bucket-owner-read'|'bucket-owner-full-control'
        :param access_control_policy: Contains the elements that set the ACL permissions
        for an object per grantee.
        # :param grant_full_control: Gives the grantee READ, READ_ACP, and WRITE_ACP permissions
        #  on the object.
        # :param grant_read: Allows grantee to read the object data and its metadata.
        # :param grant_read_acp: Allows grantee to read the object ACL.
        # :param grant_write: Allows grantee to create, overwrite, and delete any object
        # in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
        :return: dict.
        """
        grant_full_control = kwargs.get("grant_full_control", None)
        grant_read = kwargs.get("grant_read", None)
        grant_read_acp = kwargs.get("grant_read_acp", None)
        grant_write = kwargs.get("grant_write", None)
        grant_write_acp = kwargs.get("grant_write_acp", None)
        LOGGER.info("Setting acl to existing object.")
        if grant_full_control:
            if acl:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, ACL=acl, GrantFullControl=grant_full_control)
            else:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, GrantFullControl=grant_full_control)
        elif grant_read:
            if acl:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, ACL=acl, GrantRead=grant_read)
            else:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, GrantRead=grant_read)
        elif grant_read_acp:
            if acl:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, ACL=acl, GrantReadACP=grant_read_acp)
            else:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, GrantReadACP=grant_read_acp)
        elif grant_write:
            if acl:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, ACL=acl, GrantWrite=grant_write)
            else:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, GrantWrite=grant_write)
        elif grant_write_acp:
            if acl:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, ACL=acl, GrantWriteACP=grant_write_acp)
            else:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, GrantWriteACP=grant_write_acp)
        elif access_control_policy:
            if acl:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name, Key=key, ACL=acl,
                    AccessControlPolicy=access_control_policy)
            else:
                response = self.s3_client.put_object_acl(
                    Bucket=bucket_name,
                    Key=key,
                    AccessControlPolicy=access_control_policy,
                    GrantFullControl=grant_full_control)
        else:
            response = self.s3_client.put_object_acl(
                Bucket=bucket_name, Key=key, ACL=acl)
        LOGGER.debug(response)

        return response

    def put_object_with_acl2(self,
            bucket_name: str = None,
            key: str = None,
            file_path: str = None,
            **kwargs) -> dict:
        """
        To set both grant_full_control, grant_read acl while adding an object to a bucket.

        :param bucket_name: Name of the bucket.
        :param key: Name of the object.
        :param file_path: Path of the file.
        # :param grant_full_control: Gives the grantee READ, READ_ACP, and WRITE_ACP permissions
        #  on the object.
        # :param grant_read: Allows grantee to read the object data and its metadata.
        :return: dict.
        """
        grant_full_control = kwargs.get("grant_full_control", None)
        grant_read = kwargs.get("grant_read", None)
        response = self.s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=file_path,
            GrantFullControl=grant_full_control,
            GrantRead=grant_read)

        return response

    # pylint: disable-msg=too-many-branches
    def put_object_with_acl(self,
            bucket_name: str = None,
            key: str = None,
            file_path: str = None,
            acl: str = None,
            **kwargs) -> dict:
        """
        To set acl while adding an object to a bucket.

        :param bucket_name: Name of the bucket.
        :param key: Name of the object.
        :param acl: The canned ACL to apply to the object.
                    eg. 'private'|'public-read'|'public-read-write'|
                    'authenticated-read'|'aws-exec-read'|
                    'bucket-owner-read'|'bucket-owner-full-control'
        :param file_path: Path of the file.
        # :param grant_full_control: Gives the grantee. READ, READ_ACP, and WRITE_ACP permissions
        #  on the object.
        # :param grant_read: Allows grantee to read the object data and its metadata.
        # :param grant_read_acp: Allows grantee to read the object ACL.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
        :return: dict
        """
        grant_full_control = kwargs.get("grant_full_control", None)
        grant_read = kwargs.get("grant_read", None)
        grant_read_acp = kwargs.get("grant_read_acp", None)
        grant_write_acp = kwargs.get("grant_write_acp", None)

        if not os.path.exists(file_path):
            create_file(file_path, 5)
        LOGGER.info("Putting object")
        if grant_full_control:
            if acl:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_path,
                    ACL=acl,
                    GrantFullControl=grant_full_control)
            else:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_path,
                    GrantFullControl=grant_full_control)
        elif grant_read:
            if acl:
                response = self.s3_client.put_object(
                    Bucket=bucket_name, Key=key, Body=file_path, ACL=acl, GrantRead=grant_read)
            else:
                response = self.s3_client.put_object(
                    Bucket=bucket_name, Key=key, Body=file_path, GrantRead=grant_read)
        elif grant_read_acp:
            if acl:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_path,
                    ACL=acl,
                    GrantReadACP=grant_read_acp)
            else:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_path,
                    GrantReadACP=grant_read_acp)
        elif grant_write_acp:
            if acl:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_path,
                    ACL=acl,
                    GrantWriteACP=grant_write_acp)
            else:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_path,
                    GrantWriteACP=grant_write_acp)
        else:
            response = self.s3_client.put_object(
                Bucket=bucket_name, Key=key, Body=file_path, ACL=acl)

        return response

    # pylint: disable-msg=too-many-branches
    def create_bucket_with_acl(self,
            bucket_name: str = None,
            acl: str = None,
            **kwargs) -> dict:
        """
        Create bucket with given acl and grant permissions.

        :param bucket_name: Name of the bucket.
        :param acl: The canned ACL to apply to the bucket.
                    e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'.
        # :param grant_full_control: Allows grantee the read, write, read ACP, and write ACP
        #  permissions on the bucket.
        # :param grant_read: Allows grantee to list the objects in the bucket.
        # :param grant_read_acp: Allows grantee to read the bucket ACL.
        # :param grant_write: Allows grantee to create, overwrite, and delete any object
        #  in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: dict
        """
        grant_full_control = kwargs.get("grant_full_control", None)
        grant_read = kwargs.get("grant_read", None)
        grant_read_acp = kwargs.get("grant_read_acp", None)
        grant_write = kwargs.get("grant_write", None)
        grant_write_acp = kwargs.get("grant_write_acp", None)
        if grant_full_control:
            if acl:
                response = self.s3_client.create_bucket(
                    ACL=acl, Bucket=bucket_name, GrantFullControl=grant_full_control)
            elif grant_read:
                response = self.s3_client.create_bucket(
                    Bucket=bucket_name, GrantFullControl=grant_full_control, GrantRead=grant_read)
            else:
                response = self.s3_client.create_bucket(
                    Bucket=bucket_name, GrantFullControl=grant_full_control)
        elif grant_read:
            if acl:
                response = self.s3_client.create_bucket(
                    ACL=acl, Bucket=bucket_name, GrantRead=grant_read)
            else:
                response = self.s3_client.create_bucket(
                    Bucket=bucket_name, GrantRead=grant_read)
        elif grant_read_acp:
            if acl:
                response = self.s3_client.create_bucket(
                    ACL=acl, Bucket=bucket_name, GrantReadACP=grant_read_acp)
            else:
                response = self.s3_client.create_bucket(
                    Bucket=bucket_name, GrantReadACP=grant_read_acp)
        elif grant_write:
            if acl:
                response = self.s3_client.create_bucket(
                    ACL=acl, Bucket=bucket_name, GrantWrite=grant_write)
            else:
                response = self.s3_client.create_bucket(
                    Bucket=bucket_name, GrantWrite=grant_write)
        elif grant_write_acp:
            if acl:
                response = self.s3_client.create_bucket(
                    ACL=acl, Bucket=bucket_name, GrantWriteACP=grant_write_acp)
            else:
                response = self.s3_client.create_bucket(
                    Bucket=bucket_name, GrantWriteACP=grant_write_acp)
        else:
            response = self.s3_client.create_bucket(
                ACL=acl, Bucket=bucket_name)

        return response

    def put_bucket_acl(self,
            bucket_name: str = None,
            acl: str = None,
            access_control_policy: dict = None,
            **kwargs) -> bool:
        """
        Set the permissions on a bucket using access control lists (ACL).

        :param bucket_name: Name of the bucket
        :param acl: The canned ACL to apply to the bucket.
                    e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'
        :param access_control_policy: Contains the elements that set the ACL permissions
         for an object per grantee.
        # :param grant_full_control: Allows grantee the read, write, read ACP, and write ACP
        #  permissions on the bucket.
        # :param grant_read: Allows grantee to list the objects in the bucket.
        # :param grant_read_acp: Allows grantee to read the bucket ACL.
        # :param grant_write: Allows grantee to create, overwrite, and delete any object
        #  in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: True or False
        """
        grant_full_control = kwargs.get("grant_full_control", None)
        grant_read = kwargs.get("grant_read", None)
        grant_read_acp = kwargs.get("grant_read_acp", None)
        grant_write = kwargs.get("grant_write", None)
        grant_write_acp = kwargs.get("grant_write_acp", None)
        if grant_full_control:
            if acl:
                response = self.s3_client.put_bucket_acl(
                    ACL=acl, Bucket=bucket_name, GrantFullControl=grant_full_control)
            else:
                response = self.s3_client.put_bucket_acl(
                    Bucket=bucket_name, GrantFullControl=grant_full_control)
        elif grant_read:
            if acl:
                response = self.s3_client.put_bucket_acl(
                    ACL=acl, Bucket=bucket_name, GrantRead=grant_read)
            else:
                response = self.s3_client.put_bucket_acl(
                    Bucket=bucket_name, GrantRead=grant_read)
        elif grant_read_acp:
            if acl:
                response = self.s3_client.put_bucket_acl(
                    ACL=acl, Bucket=bucket_name, GrantReadACP=grant_read_acp)
            else:
                response = self.s3_client.put_bucket_acl(
                    Bucket=bucket_name, GrantReadACP=grant_read_acp)
        elif grant_write:
            if acl:
                response = self.s3_client.put_bucket_acl(
                    ACL=acl, Bucket=bucket_name, GrantWrite=grant_write)
            else:
                response = self.s3_client.put_bucket_acl(
                    Bucket=bucket_name, GrantWrite=grant_write)
        elif grant_write_acp:
            if acl:
                response = self.s3_client.put_bucket_acl(
                    ACL=acl, Bucket=bucket_name, GrantWriteACP=grant_write_acp)
            else:
                response = self.s3_client.put_bucket_acl(
                    Bucket=bucket_name, GrantWriteACP=grant_write_acp)
        elif access_control_policy:
            if acl:
                response = self.s3_client.put_bucket_acl(
                    ACL=acl, AccessControlPolicy=access_control_policy, Bucket=bucket_name)
            else:
                response = self.s3_client.put_bucket_acl(
                    AccessControlPolicy=access_control_policy, Bucket=bucket_name)
        else:
            response = self.s3_client.put_bucket_acl(
                ACL=acl, Bucket=bucket_name)

        return response

    def put_bucket_multiple_permission(self,
            bucket_name: str = None,
            **kwargs) -> bool:
        """
        Set the permissions on a bucket using access control lists (ACL).

        :param bucket_name: Name of the bucket
        # :param grant_full_control: Allows grantee the read, write, read ACP, and write ACP
        #  permissions on the bucket.
        # :param grant_read: Allows grantee to list the objects in the bucket.
        # :param grant_read_acp: Allows grantee to read the bucket ACL.
        # :param grant_write: Allows grantee to create, overwrite, and delete any object
        #  in the bucket.
        # :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: True or False
        """
        grantee = {}
        grant_full_control = kwargs.get("grant_full_control", None)
        grant_read = kwargs.get("grant_read", None)
        grant_read_acp = kwargs.get("grant_read_acp", None)
        grant_write = kwargs.get("grant_write", None)
        grant_write_acp = kwargs.get("grant_write_acp", None)

        if grant_full_control:
            grantee["GrantFullControl"] = grant_full_control
        if grant_read:
            grantee["GrantRead"] = grant_read
        if grant_read_acp:
            grantee["GrantReadACP"] = grant_read_acp
        if grant_write:
            grantee["GrantWrite"] = grant_write
        if grant_write_acp:
            grantee["GrantWriteACP"] = grant_write_acp
        response = self.s3_client.put_bucket_acl(Bucket=bucket_name, **grantee)

        return response
