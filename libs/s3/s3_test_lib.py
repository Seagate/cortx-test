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
"""Library contains methods which allows to perform bucket and object operations using boto3."""

import logging
import os
import time
from random import randint
from time import perf_counter

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError

from commons import commands
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.s3_utils import poll
from commons.utils.system_utils import create_file
from commons.utils.system_utils import run_local_cmd
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.s3_bucket_policy_test_lib import S3BucketPolicyTestLib
from libs.s3.s3_core_lib import S3Lib

LOGGER = logging.getLogger(__name__)


class S3TestLib(S3Lib):
    """Class initialising s3 connection and including methods for S3 core operations."""

    def __init__(self,
                 access_key: str = ACCESS_KEY,
                 secret_key: str = SECRET_KEY,
                 endpoint_url: str = S3_CFG["s3_url"],
                 s3_cert_path: str = S3_CFG["s3_cert_path"],
                 **kwargs) -> None:
        """
        Initialize members of S3TestLib and its parent class.

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
        super().__init__(access_key,
                         secret_key,
                         endpoint_url,
                         s3_cert_path,
                         **kwargs)

    def create_bucket(self, bucket_name: str = None) -> tuple:
        """
        Creating Bucket.

        :param bucket_name: Name of the bucket
        :return: True, response if bucket created else False, response.
        """
        try:
            start_time = perf_counter()
            response = super().create_bucket(bucket_name)
            LOGGER.debug("Create bucket response %s", str(response))
            end_time = perf_counter()
            LOGGER.info(
                "############# BUCKET CREATION TIME : %f #############",
                (end_time - start_time))
            status = bool(bucket_name == response.name)  # get response status
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.create_bucket.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return status, response.name

    def bucket_list(self) -> tuple:
        """
        Listing all the buckets.

        :return: List of buckets.
        """
        try:
            response = super().bucket_list()
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.bucket_list.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error
        return True, response

    def bucket_count(self) -> tuple:
        """
        Count total number of buckets present.

        :return: bucket count.
        """
        try:
            LOGGER.info("Counting number of buckets")
            response = super().bucket_list()
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.bucket_count.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, len(response)

    def put_object(
            self,
            bucket_name: str = None,
            object_name: str = None,
            file_path: str = None,
            **kwargs) -> tuple:
        """
        Putting Object to the Bucket (mainly small file).

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param file_path: Path of the file
        :keyword content_md5: base64-encoded MD5 digest of message
        :return: (Boolean, object of put object method)
        """
        kwargs["m_key"] = kwargs.get("m_key", None)
        kwargs["m_value"] = kwargs.get("m_value", None)
        # base64-encoded 128-bit MD5 digest of the message.
        kwargs["content_md5"] = kwargs.get("content_md5", None)
        LOGGER.info("Putting object")
        try:
            response = super().put_object(bucket_name, object_name, file_path, **kwargs)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.put_object.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def copy_object(self,
                    source_bucket: str = None,
                    source_object: str = None,
                    dest_bucket: str = None,
                    dest_object: str = None,
                    **kwargs) -> tuple:
        """
        Copy of an object that is already stored in Seagate S3 with different permissions.

        :param source_bucket: The name of the source bucket.
        :param source_object: The name of the source object.
        :param dest_bucket: The name of the destination bucket.
        :param dest_object: The name of the destination object.
        :param kwargs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services
        /s3.html#S3.Client.copy_object
        :return: True, dict.
        """
        try:
            response = self.s3_client.copy_object(
                Bucket=dest_bucket,
                CopySource=f'/{source_bucket}/{source_object}',
                Key=dest_object,
                **kwargs
            )
            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.copy_object.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def object_upload(
            self,
            bucket_name: str = None,
            object_name: str = None,
            file_path: str = None) -> tuple:
        """
        Uploading Object(small(KB)/large(GB)) to the Bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: (Boolean, response)
        """
        LOGGER.info("Uploading object")
        try:
            response = super().object_upload(bucket_name, object_name, file_path)
            LOGGER.info("Successfully uploaded an object: %s", response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.object_upload.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def object_list(self, bucket_name: str = None) -> tuple:
        """
        Listing Objects.

        :param bucket_name: Name of the bucket.
        :return: (Boolean, list of objects)
        """
        LOGGER.info("Listing Objects from bucket: %s", bucket_name)
        try:
            response = super().object_list(bucket_name)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.object_list.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def head_bucket(self, bucket_name: str = None) -> tuple:
        """
        To determine if a bucket exists and you have permission to access it.

        :param bucket_name: Name of the bucket.
        :return: (Boolean, response)
        """
        LOGGER.info("Listing head bucket")
        try:
            response = super().head_bucket(bucket_name)
            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.head_bucket.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def delete_object(self, bucket_name: str = None, obj_name: str = None) -> tuple:
        """
        Deleting Object.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of object.
        :return: (Boolean, response)
        """
        LOGGER.info("Deleting object.")
        try:
            LOGGER.debug(
                "BucketName: %s, ObjectName: %s", bucket_name, obj_name)
            response = super().delete_object(bucket_name, obj_name)
            LOGGER.info("Object Deleted Successfully.")
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.delete_object.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def bucket_location(self, bucket_name: str = None) -> tuple:
        """
        Getting Bucket Location.

        :param bucket_name: Name of the bucket.
        :return: (Boolean, response)
        """
        LOGGER.info("Showing Bucket Location of the requested bucket")
        LOGGER.debug("BucketName: %s", bucket_name)
        try:
            response = super().bucket_location(bucket_name)
            LOGGER.debug(
                "The bucket location of %s is %s", bucket_name, response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.bucket_location.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def object_info(self, bucket_name: str = None, key: str = None) -> tuple:
        """
        Retrieve metadata from an object without returning the object itself.

        You must have READ access to the object.
        :param bucket_name: Name of the bucket.
        :param key: Key of object.
        :return: (Boolean, response)
        """
        LOGGER.info(
            "Showing Object Info of a requested object in a particular bucket")
        try:
            response = super().object_info(bucket_name, key)
            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.object_info.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def object_download(
            self,
            bucket_name: str = None,
            obj_name: str = None,
            file_path: str = None,
            **kwargs) -> tuple:
        """
        Downloading Object of the required Bucket using range read

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param file_path: Path of the file.
        :return: (Boolean, downloaded path)
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            LOGGER.info("Starting downloading the object")

            response = super().object_download(bucket_name, obj_name, file_path, **kwargs)
            LOGGER.debug(
                "The %s has been downloaded successfully at mentioned file path %s",
                obj_name,
                file_path)
            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.object_download.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def delete_bucket(self, bucket_name: str = None, force: bool = False) -> tuple:
        """
        Deleting the empty bucket or deleting the buckets along with objects stored in it.

        :param bucket_name: Name of the bucket.
        :param force: Value for delete bucket with object or without object
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("You have opted to delete buckets.")
            start_time = perf_counter()
            if force:
                LOGGER.info("Trying polling mechanism as bucket is getting deleted forcefully.")
                response = poll(super().delete_bucket, bucket_name, force)
            else:
                response = super().delete_bucket(bucket_name, force)
            end_time = perf_counter()
            LOGGER.debug(response)
            LOGGER.info(
                "############# BUCKET DELETION TIME : %f #############",
                (end_time - start_time))
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.delete_bucket.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def get_bucket_size(self, bucket_name: str = None) -> tuple:
        """
        Getting size of bucket.

        :param bucket_name: Name of the bucket.
        :return: (Boolean, size of bucket in int)
        """
        total_size = 0
        try:
            LOGGER.info("Getting bucket size")
            bucket = super().get_bucket_size(bucket_name)
            for each_object in bucket.objects.all():
                total_size += each_object.size
                LOGGER.info(each_object.size)
            LOGGER.info("Total size: %s", total_size)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.get_bucket_size.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, total_size

    def delete_multiple_objects(
            self,
            bucket_name: str = None,
            obj_list: list = None,
            quiet: bool = False,
            prepared_obj_list: list = None) -> tuple:
        """
        Delete multiple objects from a single bucket.

        :param bucket_name: Name of bucket.
        :param obj_list: List of objects to be deleted.
        :param quiet: It enables a quiet mode.
        :param prepared_obj_list: Override DeleteObjects Objects list generation,
            list assigned is passed as-is to DeleteObjects call, expected format:
                [{'Key': 'string', 'VersionId': 'string'}, ...]
                where 'VersionId' is optional
        :return: True and response or False and error.
        :rtype: (boolean, dict/str)
        """
        try:
            LOGGER.info("deleting multiple objects")
            if prepared_obj_list:
                objects = prepared_obj_list
            else:
                objects = []
                for key in obj_list:
                    obj_d = dict()
                    obj_d["Key"] = key
                    objects.append(obj_d)
            if quiet:
                response = self.s3_client.delete_objects(
                    Bucket=bucket_name, Delete={
                        "Objects": objects, "Quiet": True})
            else:
                response = self.s3_client.delete_objects(
                    Bucket=bucket_name, Delete={"Objects": objects})
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.delete_multiple_objects.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def delete_multiple_buckets(self, bucket_list: list = None) -> tuple:
        """
        Delete multiple empty/non-empty buckets.

        :param bucket_list: List of bucket names.
        :return: True or False and deleted and non-deleted buckets.
        """
        LOGGER.info("Deleting multiple empty/non-empty buckets")
        response_dict = {"Deleted": [], "CouldNotDelete": []}
        for bucket in bucket_list:
            response = self.delete_bucket(bucket, True)
            if response[0]:
                response_dict["Deleted"].append(bucket)
            else:
                LOGGER.error(
                    "Error in %s: %s",
                    S3TestLib.delete_multiple_buckets.__name__,
                    response[1])
                response_dict["CouldNotDelete"].append(bucket)
        if response_dict["CouldNotDelete"]:
            LOGGER.error("Failed to delete bucket")
            return False, response_dict

        return True, response_dict

    def delete_all_buckets(self) -> tuple:
        """
        Delete all empty/non-empty buckets.

        :return: response from delete_multiple_buckets.
        """
        all_buckets = self.bucket_list()
        response = self.delete_multiple_buckets(all_buckets[1])

        return True, response

    def create_multiple_buckets_with_objects(
            self,
            bucket_count: int = None,
            file_path: str = None,
            obj_count: int = 1) -> tuple:
        """
        Create given number of buckets and upload one object to each bucket.

        :param bucket_count: No. of buckets to create.
        :param file_path: Path of file to upload.
        :param obj_count: No. of objects to create into each bucket.
        :return: list of created buckets.
        """
        response = []
        obj_list = []
        try:
            for count in range(int(bucket_count)):
                bucket_name = f"bvtbucket-{str(count)}-{str(time.time())}"
                resp_bucket = self.create_bucket(bucket_name)
                for obj in range(obj_count):
                    object_name = f"auto-obj-{str(obj)}-{bucket_name}"
                    self.object_upload(bucket_name, object_name, file_path)
                    obj_list.append(object_name)
                response.append({"Bucket": resp_bucket, "Objects": obj_list})
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3TestLib.create_multiple_buckets_with_objects.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def create_multiple_buckets(self, bucket_count: int, bucket_prefix: str) -> tuple:
        """
        Create given number of buckets with specified prefix.

        :param bucket_count: No. of buckets to create.
        :param bucket_prefix: Prefix for bucket name.
        :return: list of created buckets.
        """
        response = []
        try:
            for count in range(bucket_count):
                bucket_name = f"{bucket_prefix}-{str(count)}-{str(time.time())}"
                resp_bucket = self.create_bucket(bucket_name)
                if not resp_bucket[0]:
                    LOGGER.error('Bucket name does not match as requested,'
                                 ' Expected : %s, Received : %s', bucket_name, resp_bucket[1])
                    raise Exception('Bucket name does not match')
                response.append(resp_bucket[1])
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3TestLib.create_multiple_buckets.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_random_size_objects(self,
                                bucket_name: str = None,
                                object_name: str = None,
                                min_size: int = None,
                                max_size: int = None,
                                **kwargs) -> tuple:
        """
        Put random size objects into the bucket.

        :param bucket_name: Name of bucket.
        :param object_name: Name of object.
        :param min_size: Minimum size of object in MB.
        :param max_size: Maximum size of object in MB.
        :keyword: delete_file: enables the flag to delete the file
        :return: True or False and list of objects or error.
        """
        object_count = kwargs.get("object_count", None)
        file_path = kwargs.get("file_path", None)
        delete_file = kwargs.get("delete_file", True)
        objects_list = []
        try:
            for obj in range(int(object_count)):
                objects = f"{object_name}_{str(obj)}_{str(time.time())}"
                if os.path.exists(file_path):
                    os.remove(file_path)
                with open(file_path, 'wb') as fout:
                    fout.write(
                        os.urandom(
                            randint(  # nosec
                                1024000 *
                                int(min_size),
                                1024000 *
                                int(max_size))))
                LOGGER.info(
                    "Uploading object of size %d", os.path.getsize(file_path))
                self.s3_resource.meta.client.upload_file(
                    file_path, bucket_name, objects)
                LOGGER.info(
                    "Uploaded object %s to the bucket %s",
                    objects,
                    bucket_name)
                objects_list.append(objects)
                if delete_file:
                    os.remove(file_path)
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3TestLib.put_random_size_objects.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, objects_list

    def create_bucket_put_object(self,
                                 bucket_name: str = None,
                                 object_name: str = None,
                                 file_path: str = None,
                                 mb_count: int = None) -> tuple:
        """
        The function will create a bucket and uploads an object to it.

        :param bucket_name: Name of bucket to be created.
        :param object_name: Name of an object to be put to the bucket.
        :param file_path: Path of the file to be created and uploaded to bucket.
        :param mb_count: Size of file in MBs.
        :return: (Boolean, Response).
        """
        response = []
        try:
            LOGGER.debug("Creating a bucket with name %s", str(bucket_name))
            create_bucket = self.create_bucket(bucket_name)
            LOGGER.debug("Created a bucket with name %s", str(bucket_name))
            LOGGER.info("Check bucket is empty")
            resp = self.object_list(bucket_name)
            if resp[1]:
                raise CTException(err.S3_SERVER_ERROR, f"Bucket is not empty {(resp[1])}")
            LOGGER.info("Verified that bucket was empty")
            LOGGER.debug("Creating a file %s", str(file_path))
            create_file(file_path, mb_count)
            LOGGER.debug("Created a file %s", str(file_path))
            LOGGER.debug(
                "Uploading an object %s to bucket %s",
                object_name,
                bucket_name)
            put_object = self.put_object(bucket_name, object_name, file_path)
            LOGGER.debug(
                "Uploaded an object %s to bucket %s", object_name, bucket_name)
            response.append({"Bucket": create_bucket, "Objects": put_object})
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3TestLib.create_bucket_put_object.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def get_object(
            self,
            bucket: str = None,
            key: str = None,
            ranges: str = None,
            **kwargs) -> tuple:
        """
        Retrieve object from specified S3 bucket.

        :param key: Key of the object to get.
        :param ranges: Byte range to be retrieved
        :param bucket: The bucket name containing the object.
        :keyword raise_exec: raise an exception in default case.
        :keyword skip_polling: Skip retry for GET Object, in case of failures
        :return: (Boolean, Response)
        """
        raise_exec = kwargs.get("raise_exec", True)
        skip_polling = kwargs.get("skip_polling", False)
        try:
            LOGGER.info("Retrieving object from a bucket")
            if not skip_polling:
                response = poll(super().get_object, bucket, key, ranges)
            else:
                response = super().get_object(bucket, key, ranges)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.get_object.__name__,
                         error)
            if raise_exec:
                raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error
            if error.response['Error']['Code'] == 'NoSuchKey':
                LOGGER.info('No object found - returning empty')
                return False, {}
            return False, error.response
        return True, response

    def list_objects_with_prefix(
            self,
            bucket_name: str = None,
            prefix: str = None,
            maxkeys: int = None) -> tuple:
        """
        Listing objects of a bucket having specified prefix.

        :param bucket_name: Name of the bucket
        :param prefix: Object prefix used while uploading an object to bucket
        :param maxkeys: Sets the maximum number of keys returned in the response.
        :return: List of objects of a bucket having specified prefix.
        """
        LOGGER.info("Listing Objects in a particular bucket having properties")
        try:
            response = super().list_objects_with_prefix(
                bucket_name, prefix=prefix, maxkeys=maxkeys)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.list_objects_with_prefix.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def list_objects_details(
            self,
            bucket_name: str = None, ) -> tuple:
        """
        Listing objects of a bucket with details.

        :param bucket_name: Name of the bucket
        :return: bool, response dict.
        """
        try:
            response = self.s3_client.list_objects(
                Bucket=bucket_name)
            LOGGER.debug(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.list_objects_details.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_object_with_storage_class(self,
                                      bucket_name: str = None,
                                      object_name: str = None,
                                      file_path: str = None,
                                      storage_class: str = None) -> tuple:
        """
        Add an object to a bucket with specified storage class.

        :param str bucket_name: Bucket name to which the PUT operation was initiated
        :param str object_name: Name of an object to be put to the bucket
        :param str file_path: Path of the file to be created and uploaded to bucket
        :param str storage_class: The type of storage to use for the object
        e.g.'STANDARD'|'REDUCED_REDUNDANCY'|'STANDARD_IA'|'ONEZONE_IA'|'INTELLIGENT_TIERING'|
        'GLACIER'|'DEEP_ARCHIVE'
        :return: (Boolean, Response)
        """
        LOGGER.info(
            "Uploading an object to a bucket with specified storage class.")
        LOGGER.debug(
            "bucket_name: %s, object_name: %s, file_path: %s, storage_class: %s",
            bucket_name,
            object_name,
            file_path,
            storage_class)
        try:
            response = super().put_object_with_storage_class(
                bucket_name, object_name, file_path, storage_class)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TestLib.put_object_with_storage_class.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def create_bucket_awscli(self, bucket_name: str):
        """
        Method to create a bucket using awscli.

        :param bucket_name: Name of the bucket
        :return: True/False and output of command execution
        """
        LOGGER.info("Creating a bucket with name: %s", bucket_name)
        success_msg = f"make_bucket: {bucket_name}"
        cmd = commands.CMD_AWSCLI_CREATE_BUCKET.format(bucket_name) + self.cmd_endpoint
        response = run_local_cmd(cmd=cmd, chk_stderr=True)[1]
        LOGGER.info("Response returned: %s", response)
        cmd = commands.CMD_AWSCLI_LIST_BUCKETS + self.cmd_endpoint
        buckets_list = run_local_cmd(cmd=cmd, chk_stderr=True)[1]
        if success_msg in response and bucket_name in buckets_list:
            return True, response

        return False, response

    def delete_bucket_awscli(self, bucket_name: str, force: bool = False):
        """
        Method to delete a bucket using awscli.

        :param bucket_name: Name of the bucket
        :param force: True for forcefully deleting bucket containing objects
        :return: True/False and output of command execution
        """
        LOGGER.info("Deleting bucket: %s", bucket_name)
        success_msg = f"remove_bucket: {bucket_name}"
        delete_bkt_cmd = commands.CMD_AWSCLI_DELETE_BUCKET + self.cmd_endpoint
        if force:
            delete_bkt_cmd = " ".join([delete_bkt_cmd, "--force"])
        response = run_local_cmd(cmd=delete_bkt_cmd.format(bucket_name), chk_stderr=True)[1]
        LOGGER.info("Response returned: %s", response)
        cmd = commands.CMD_AWSCLI_LIST_BUCKETS + self.cmd_endpoint
        buckets_list = run_local_cmd(cmd=cmd, chk_stderr=True)[1]
        if success_msg in response and bucket_name not in buckets_list:
            return True, response

        return False, response


class S3LibNoAuth(S3TestLib, S3AclTestLib, S3BucketPolicyTestLib):
    """
    Class initialising s3 connection.

    Including methods for bucket and object without authentication operations.
    """

    def __init__(self,
                 access_key: str = None,
                 secret_key: str = None,
                 endpoint_url: str = S3_CFG["s3_url"],
                 s3_cert_path: str = None,
                 **kwargs) -> None:
        """S3 connection initializer for bucket and object without authentication."""
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        s3_cert_path = s3_cert_path if s3_cert_path else S3_CFG["s3_cert_path"]
        val_cert = kwargs.get("validate_certs", S3_CFG["validate_certs"])
        s3_cert_path = s3_cert_path if val_cert else False
        super().__init__(access_key,
                         secret_key,
                         endpoint_url,
                         s3_cert_path,
                         **kwargs)
        self.s3_client = boto3.client(
            "s3",
            verify=s3_cert_path,
            endpoint_url=endpoint_url,
            config=Config(
                signature_version=UNSIGNED))
        self.s3_resource = boto3.resource(
            "s3",
            verify=s3_cert_path,
            endpoint_url=endpoint_url,
            config=Config(
                signature_version=UNSIGNED))
