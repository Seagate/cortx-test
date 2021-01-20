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
# Python library contains methods which allows you to perform bucket ACL
# operations using boto3.

import copy
import logging
import boto3
from libs.s3.s3_core_lib import Acl
from commons.exceptions import CTException
from commons import errorcodes as err
from commons.utils.config_utils import read_yaml
from commons.helpers.s3_helper import S3Helper

try:
    s3hobj = S3Helper()
except ImportError as err:
    s3hobj = S3Helper.get_instance()

s3_conf = read_yaml("config/s3/s3_config.yaml")[1]
logger = logging.getLogger(__name__)


class S3AclTestLib(Acl):
    """
    This Class initialising s3 connection and including methods for bucket and object
    ACL operations.
    """

    def __init__(
            self,
            access_key: str = s3hobj.get_local_keys()[0],
            secret_key: str = s3hobj.get_local_keys()[1],
            endpoint_url: str = s3_conf["s3_url"],
            s3_cert_path: str = s3_conf["s3_cert_path"],
            region: str = s3_conf["region"],
            aws_session_token: str = None,
            debug: bool = s3_conf["debug"]) -> None:
        """This method initializes members of S3AclTestLib and its parent class
        :param access_key: access key
        :param secret_key: secret key
        :param endpoint_url: endpoint url
        :param s3_cert_path: s3 certificate path
        :param region: region
        :param aws_session_token: aws_session_token
        :param debug: debug mode
        """
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            region,
            aws_session_token,
            debug)

    def get_object_acl(self, bucket: str, object_key: str) -> dict:
        """
        Getting object acl attributes
        :param bucket: Name of the bucket
        :param object_key: Key of object
        :return: (Boolean, response)
        """
        try:
            logger.info("Getting object acl.")
            object_acl = super().get_object_acl(bucket, object_key)
            logger.debug(object_acl)
            response = {"Owner": object_acl.owner, "Grants": object_acl.grants}
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.get_object_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def get_bucket_acl(self, bucket_name: str) -> tuple:
        """
        Retrieving bucket acl attributes
        :param bucket_name: Name of the bucket
        :return: (Boolean, response)
        """
        try:
            logger.info("Getting bucket acl.")
            bucket_acl = super().get_bucket_acl(bucket_name)
            logger.debug(bucket_acl)
            response = bucket_acl.owner, bucket_acl.grants
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.get_bucket_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def put_object_acl(
            self,
            bucket_name: str,
            object_name: str,
            acl: dict) -> bool:
        """
        Set the access control list of an Amazon s3 object.
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param acl: Dictionary defining the ACL consisting of grants and permissions
        :return: (Boolean, response)
        """
        try:
            logger.info("Applying acl to existing object")
            response = super().put_object_acl(bucket_name, object_name, acl)
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.put_object_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def put_object_acp(
            self,
            bucket_name: str,
            object_name: str,
            acp: dict) -> dict:
        """
        Set the access control policy of an Amazon s3 object.
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param acp: Dictionary defining the ACP consisting of grants and permissions
        :return: response
        """
        try:
            logger.info("Applying acl to existing object")
            response = super().put_object_acp(bucket_name, object_name, acp)
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.put_object_acp.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def add_grantee(
            self,
            bucket_name: str,
            object_name: str,
            grantee_id: str,
            permission: str) -> dict:
        """
        Add a grantee with given ACL permission to a object present in a bucket
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
                    "Type": "CanonicalUser",
                },
                "Permission": permission,
            }
            # If we don't want to modify the original ACL variable, then we
            # must do a deepcopy
            modified_acl = copy.deepcopy(acl)
            modified_acl["Grants"].append(new_grant)
            logger.info(modified_acl)
            response = super().put_object_acp(bucket_name, object_name, modified_acl)
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.add_grantee.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def put_object_canned_acl(
            self,
            bucket_name: str,
            key: str,
            acl: str = None,
            access_control_policy: dict = None,
            grant_full_control: str = None,
            grant_read: str = None,
            grant_read_acp: str = None,
            grant_write: str = None,
            grant_write_acp: str = None) -> dict:
        """
        To set the access control list (ACL) permissions
        for an object that already exists in a bucket
        :param bucket_name: Name of the bucket.
        :param key: Name of the existing object.
        :param acl: The canned ACL to apply to the object.
                     eg. 'private'|'public-read'|'public-read-write'|
                    'authenticated-read'|'aws-exec-read'|
                    'bucket-owner-read'|'bucket-owner-full-control'
        :param access_control_policy: Contains the elements
        that set the ACL permissions for an object per grantee.
        :param grant_full_control: Gives the grantee READ,
        READ_ACP, and WRITE_ACP permissions on the object.
        :param grant_read: Allows grantee to read the object data and its metadata.
        :param grant_read_acp: Allows grantee to read the object ACL.
        :param grant_write: Allows grantee to create,
        overwrite, and delete any object in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
        :return: dict
        """
        try:
            logger.info("Setting canned acl to existing object")
            response = super().put_object_canned_acl(
                bucket_name,
                key,
                acl,
                access_control_policy,
                grant_full_control,
                grant_read,
                grant_read_acp,
                grant_write,
                grant_write_acp)
            logger.info(response)
        except BaseException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.put_object_canned_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def put_object_with_acl2(
            self,
            bucket_name: str,
            key: str,
            file_path: str,
            grant_full_control: str,
            grant_read: str) -> dict:
        """
        To set both grant_full_control, grant_read acl while adding an object to a bucket.
        :param bucket_name: Name of the bucket
        :param key: Name of the object
        :param file_path: Path of the file
        :param grant_full_control: Gives the grantee
        READ, READ_ACP, and WRITE_ACP permissions on the object.
        :param grant_read: Allows grantee to read the object data and its metadata.
        :return: dict
        """
        try:
            logger.info("Setting acl to new object")
            response = super().put_object_with_acl2(
                bucket_name, key, file_path, grant_full_control, grant_read)
            logger.info(response)
        except BaseException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.put_object_with_acl2.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def put_object_with_acl(
            self,
            bucket_name: str,
            key: str,
            file_path: str,
            acl: str = None,
            grant_full_control: str = None,
            grant_read: str = None,
            grant_read_acp: str = None,
            grant_write_acp: str = None) -> dict:
        """
        To set acl while adding an object to a bucket.
        :param bucket_name: Name of the bucket
        :param key: Name of the object
        :param acl: The canned ACL to apply to the object.
                    eg. 'private'|'public-read'|'public-read-write'|
                    'authenticated-read'|'aws-exec-read'|
                    'bucket-owner-read'|'bucket-owner-full-control'
        :param file_path: Path of the file
        :param grant_full_control: Gives the grantee
        READ, READ_ACP, and WRITE_ACP permissions on the object.
        :param grant_read: Allows grantee to read the object data and its metadata.
        :param grant_read_acp: Allows grantee to read the object ACL.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
        :return: dict
        """
        try:
            logger.info("Setting acl to new object")
            response = super().put_object_with_acl(bucket_name, key, file_path, acl,
                                                   grant_full_control, grant_read, grant_read_acp, grant_write_acp)
            logger.info(response)
        except BaseException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.put_object_with_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def create_bucket_with_acl(
            self,
            bucket_name: str,
            acl: str = None,
            grant_full_control: str = None,
            grant_read: str = None,
            grant_read_acp: str = None,
            grant_write: str = None,
            grant_write_acp: str = None) -> dict:
        """
        Create bucket with given acl and grant permissions.
        :param bucket_name: Name of the bucket
        :param acl: The canned ACL to apply to the bucket.
        e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'
        :param grant_full_control: Allows grantee the read,
        write, read ACP, and write ACP permissions on the bucket.
        :param grant_read: Allows grantee to list the objects in the bucket.
        :param grant_read_acp: Allows grantee to read the bucket ACL.
        :param grant_write: Allows grantee to create,
        overwrite, and delete any object in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: dict
        """
        try:
            logger.info("Setting acl while creating object")
            response = super().create_bucket_with_acl(bucket_name, acl, grant_full_control,
                                                      grant_read, grant_read_acp, grant_write, grant_write_acp)
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.create_bucket_with_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    def put_bucket_acl(
            self,
            bucket_name: str,
            acl: str = None,
            access_control_policy: dict = None,
            grant_full_control: str = None,
            grant_read: str = None,
            grant_read_acp: str = None,
            grant_write: str = None,
            grant_write_acp: str = None) -> bool:
        """
        Sets the permissions on a bucket using access control lists (ACL).
        :param bucket_name: Name of the bucket
        :param acl: The canned ACL to apply to the bucket.
        e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'
        :param access_control_policy: Contains the elements that
        set the ACL permissions for an object per grantee.
        :param grant_full_control: Allows grantee the read, write,
        read ACP, and write ACP permissions on the bucket.
        :param grant_read: Allows grantee to list the objects in the bucket.
        :param grant_read_acp: Allows grantee to read the bucket ACL.
        :param grant_write: Allows grantee to create,
        overwrite, and delete any object in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
        :return: True or False
        """
        try:
            logger.info("Setting acl while creating object")
            response = super().put_bucket_acl(
                bucket_name,
                acl,
                access_control_policy,
                grant_full_control,
                grant_read,
                grant_read_acp,
                grant_write,
                grant_write_acp)
            logger.info(response)
        except Exception as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.put_bucket_acl.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
        return True, response

    @staticmethod
    def get_bucket_acl_using_iam_credentials(
            access_key: str, secret_key: str, bucket_name: str) -> tuple:
        """
        Retrieving bucket acl attributes using iam credentials
        :param access_key: ACCESS_KEY of the iam account
        :param secret_key: SECRET_KEY of the iam account
        :param bucket_name: Name of bucket
        :return: Bucket ACL or error
        :rtype: (Boolean, tuple/str)
        """
        logger.info(
            f"Retrieving {bucket_name} acl attrs using {access_key}, {secret_key}.")
        s3_iam_resource = boto3.resource(
            "s3",
            verify=s3_conf['s3_cert_path'],
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=s3_conf['s3_url'],
            region_name=s3_conf['region'])
        try:
            bucket_acl = s3_iam_resource.BucketAcl(bucket_name)
            response = bucket_acl.owner, bucket_acl.grants
            logger.info(response)
            return True, response
        except BaseException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in ",
                    S3AclTestLib.get_bucket_acl_using_iam_credentials.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
