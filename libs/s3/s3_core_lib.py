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

"""Python Library using boto3 module to perform Bucket and object Operations."""

import logging
import os
from typing import Union

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from commons.constants import S3_ENGINE_RGW
from config import S3_CFG, CMN_CFG

LOGGER = logging.getLogger(__name__)


class S3Rest:
    """Basic Class for Creating Boto3 REST API Objects."""

    def __init__(self,
                 access_key: str = None,
                 secret_key: str = None,
                 endpoint_url: str = None,
                 s3_cert_path: Union[str, bool] = None,
                 **kwargs) -> None:
        """
        Initialize members of S3Lib.

        Different instances need to be created as per different parameter values like access_key,
        secret_key etc.
        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        init_s3_connection = kwargs.get("init_s3_connection", True)
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            region = kwargs.get("region", "default")
        else:
            region = kwargs.get("region", None)
        aws_session_token = kwargs.get("aws_session_token", None)
        debug = kwargs.get("debug", S3_CFG["debug"])
        config = Config(retries={'max_attempts': 6})
        self.use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
        val_cert = kwargs.get("validate_certs", S3_CFG["validate_certs"])
        self.s3_cert_path = s3_cert_path if val_cert else False
        self.cmd_endpoint = f" --endpoint-url {endpoint_url}" \
                            f"{'' if val_cert else ' --no-verify-ssl'}"
        if val_cert and not os.path.exists(S3_CFG["s3_cert_path"]):
            raise IOError(f'Certificate path {S3_CFG["s3_cert_path"]} does not exists.')
        if debug:
            self.enable_debug_mode()
        try:
            if init_s3_connection:
                self.s3_resource = boto3.resource("s3",
                                                  use_ssl=self.use_ssl,
                                                  verify=self.s3_cert_path,
                                                  aws_access_key_id=access_key,
                                                  aws_secret_access_key=secret_key,
                                                  endpoint_url=endpoint_url,
                                                  region_name=region,
                                                  aws_session_token=aws_session_token,
                                                  config=config)
                self.s3_client = boto3.client("s3",
                                              use_ssl=self.use_ssl,
                                              verify=self.s3_cert_path,
                                              aws_access_key_id=access_key,
                                              aws_secret_access_key=secret_key,
                                              endpoint_url=endpoint_url,
                                              region_name=region,
                                              aws_session_token=aws_session_token,
                                              config=config)
            else:
                LOGGER.info("Skipped: create s3 client, resource object with boto3.")
        except ClientError as error:
            if "unreachable network" not in str(error):
                LOGGER.critical(error)

    def __del__(self):
        """Destroy all core objects."""
        try:
            del self.s3_client
            del self.s3_resource
        except NameError as error:
            LOGGER.warning(error)

    @staticmethod
    def enable_debug_mode():
        """Enable the boto3 debug mode."""
        boto3.set_stream_logger(name="botocore")


class S3Lib(S3Rest):
    """Class initialising s3 connection and including methods for bucket and object operations."""

    def create_bucket(self, bucket_name: str = None) -> dict:
        """
        Create s3 bucket.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        response = self.s3_resource.create_bucket(Bucket=bucket_name)
        LOGGER.debug("Response: %s", str(response))

        return response

    def bucket_list(self) -> list:
        """
        List all s3 buckets.

        :return: response.
        """
        response = [bucket.name for bucket in self.s3_resource.buckets.all()]
        LOGGER.info(response)

        return response

    def put_object_with_all_kwargs(self, **kwargs):
        """
        Put object to the s3 bucket.

        :return: response.
        """
        LOGGER.debug("input for put_object are: %s ", kwargs)
        response = self.s3_client.put_object(**kwargs)
        LOGGER.debug("output: %s ", response)
        return response

    def put_object(self,
                   bucket_name: str = None,
                   object_name: str = None,
                   file_path: str = None,
                   **kwargs) -> dict:
        """
        Put object to the s3 bucket (mainly small file).

        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param file_path: Path of the file
        :keyword content_md5: base64-encoded MD5 digest of message
        :return: response.
        """
        m_key = kwargs.get("m_key", None)
        m_value = kwargs.get("m_value", None)
        metadata = kwargs.get("metadata", None)  # metadata dict.
        content_md5 = kwargs.get("content_md5")  # base64-encoded 128-bit MD5 digest of the message.
        LOGGER.debug("bucket_name: %s, object_name: %s, file_path: %s, m_key: %s, m_value: %s",
                     bucket_name, object_name, file_path, m_key, m_value)
        with open(file_path, "rb") as data:
            if m_key:
                response = self.s3_client.put_object(Bucket=bucket_name, Key=object_name,
                                                     Body=data, Metadata={m_key: m_value})
            elif metadata:
                response = self.s3_client.put_object(Bucket=bucket_name, Key=object_name,
                                                     Body=data, Metadata=metadata)
            elif content_md5:
                response = self.s3_client.put_object(Bucket=bucket_name, Key=object_name,
                                                     Body=data, ContentMD5=content_md5)
            else:
                response = self.s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=data)
            LOGGER.debug(response)

        return response

    def object_upload(self, bucket_name: str = None, object_name: str = None,
                      file_path: str = None) -> str:
        """
        Upload object to the s3 bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        self.s3_resource.meta.client.upload_file(
            file_path, bucket_name, object_name)

        return file_path

    def object_list(self, bucket_name: str = None) -> list:
        """
        List all objects from s3 bucket.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        bucket = self.s3_resource.Bucket(bucket_name)
        response_obj = [obj.key for obj in bucket.objects.all()]
        LOGGER.debug(response_obj)

        return response_obj

    def list_objects_with_prefix(self, bucket_name: str = None, prefix: str = None,
                                 maxkeys: int = None) -> list:
        """
        List all objects of a s3 bucket having specified prefix.

        :param bucket_name: Name of the bucket
        :param prefix: Object prefix used while uploading an object to bucket
        :param maxkeys: Sets the maximum number of keys returned to the response.
        :return: List of objects of a bucket having specified prefix.
        """
        resp = None
        if prefix:
            resp = self.s3_client.list_objects(Bucket=bucket_name, Prefix=prefix)
        if maxkeys:
            resp = self.s3_client.list_objects(Bucket=bucket_name, MaxKeys=maxkeys)
        LOGGER.debug("Resp is : %s", str(resp))
        obj_lst = [obj['Key'] for obj in resp['Contents']]
        LOGGER.debug(obj_lst)

        return obj_lst

    def head_bucket(self, bucket_name: str = None) -> dict:
        """
        To determine if a bucket exists, and you have a permission to access it.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        response_bucket = self.s3_resource.meta.client.head_bucket(Bucket=bucket_name)
        # Since we are getting http response from head bucket, we have appended
        # bucket name for validation.
        response_bucket["BucketName"] = bucket_name
        LOGGER.debug(response_bucket)

        return response_bucket

    def delete_object(self, bucket_name: str = None, obj_name: str = None) -> dict:
        """
        Delete object from s3 bucket.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of object.
        :return: response.
        """
        LOGGER.debug("BucketName: %s, ObjectName: %s", bucket_name, obj_name)
        resp_obj = self.s3_resource.Object(bucket_name, obj_name)
        response = resp_obj.delete()
        logging.debug(response)
        LOGGER.info("Object Deleted Successfully")

        return response

    def bucket_location(self, bucket_name: str = None) -> dict:
        """
        Get the s3 bucket location.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        LOGGER.debug("BucketName: %s", bucket_name)
        response = self.s3_resource.meta.client.get_bucket_location(Bucket=bucket_name)
        LOGGER.debug(response)

        return response

    def object_info(self, bucket_name: str = None, key: str = None) -> dict:
        """
        Retrieve metadata from an object without returning the object itself.

        you must have READ access to the object.
        :param bucket_name: Name of the bucket.
        :param key: Key of object.
        :return: response.
        """
        response = self.s3_resource.meta.client.head_object(Bucket=bucket_name, Key=key)
        LOGGER.debug(response)

        return response

    def object_download(self, bucket_name: str = None, obj_name: str = None, file_path: str = None,
                        **kwargs) -> str:
        """
        Download object of the required s3 bucket.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        self.s3_resource.Bucket(bucket_name).download_file(obj_name, file_path, **kwargs)
        LOGGER.debug("The %s has been downloaded successfully at mentioned file path %s",
                     obj_name, file_path)

        return file_path

    def delete_bucket(self, bucket_name: str = None, force: bool = False) -> dict:
        """
        Delete the empty bucket or delete the bucket along with objects stored in it.

        :param bucket_name: Name of the bucket.
        :param force: Value for delete bucket with object or without object.
        :return: response.
        """
        bucket = self.s3_resource.Bucket(bucket_name)
        if force:
            self.object_list(bucket_name)
            LOGGER.info("This might cause data loss as you have opted for bucket deletion with "
                        "objects in it")
            response = bucket.objects.all().delete()
            LOGGER.debug("Objects deleted successfully from bucket %s, response: %s",
                         bucket_name, response)
            self.object_list(bucket_name)
        response = bucket.delete()
        LOGGER.debug("Bucket '%s' deleted successfully. Response: %s", bucket_name, response)

        return response

    def get_bucket_size(self, bucket_name: str = None) -> dict:
        """
        Get size of the s3 bucket.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        # total_size = 0
        LOGGER.info("Getting bucket size")
        response = self.s3_resource.Bucket(bucket_name)
        LOGGER.debug(response)

        return response

    def get_object(self, bucket: str = None, key: str = None, ranges: str = None) -> dict:
        """
        Get object or byte range of the object.

        :param bucket: Name of the bucket.
        :param key: Key of object.
        :param ranges: Byte range to be retrieved
        :return: response.
        """
        if ranges:
            response = self.s3_client.get_object(Bucket=bucket, Key=key, Range=ranges)
        else:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
        LOGGER.debug(response)

        return response

    def put_object_with_storage_class(self, bucket_name: str = None, object_name: str = None,
                                      file_path: str = None, storage_class: str = None) -> dict:
        """
        Add an object to a bucket with specified storage class.

        :param bucket_name: Bucket name to which the PUT operation was initiated.
        :param object_name: Name of an object to be put to the bucket.
        :param file_path: Path of the file to be created and uploaded to bucket.
        :param storage_class: The type of storage to use for the object.
        e.g.'STANDARD'|'REDUCED_REDUNDANCY'|'STANDARD_IA'|'ONEZONE_IA'|'INTELLIGENT_TIERING'|
        'GLACIER'|'DEEP_ARCHIVE'
        :return: response.
        """
        LOGGER.debug("bucket_name: %s, object_name: %s, file_path: %s, storage_class: %s",
                     bucket_name, object_name, file_path, storage_class)
        with open(file_path, "rb") as data:
            response = self.s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=data,
                                                 StorageClass=storage_class)
            LOGGER.debug(response)

        return response
