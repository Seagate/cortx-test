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
#

"""Python Library using boto3 module to perform Bucket and object Operations."""

import os
import sys
import logging
import threading
import boto3
import boto3.s3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from typing import Union
from commons import commands
from commons.utils.system_utils import run_local_cmd, create_file
from config.s3 import S3_CFG

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
        method initializes members of S3Lib.

        Different instances need to be create as per different parameter values like access_key,
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
            # Uncomment to enable debug
            boto3.set_stream_logger(name="botocore")
        try:
            if init_s3_connection:
                self.s3_resource = boto3.resource(
                    "s3",
                    use_ssl=self.use_ssl,
                    verify=self.s3_cert_path,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    endpoint_url=endpoint_url,
                    region_name=region,
                    aws_session_token=aws_session_token,
                    config=config)
                self.s3_client = boto3.client("s3", use_ssl=self.use_ssl,
                                              verify=self.s3_cert_path,
                                              aws_access_key_id=access_key,
                                              aws_secret_access_key=secret_key,
                                              endpoint_url=endpoint_url,
                                              region_name=region,
                                              aws_session_token=aws_session_token,
                                              config=config)
            else:
                LOGGER.info("Skipped: create s3 client, resource object with boto3.")
        except Exception as Err:
            if "unreachable network" not in str(Err):
                LOGGER.critical(Err)

    def __del__(self):
        """Destroy all core objects."""
        try:
            del self.s3_client
            del self.s3_resource
        except NameError as error:
            LOGGER.warning(error)


class S3Lib(S3Rest):
    """Class initialising s3 connection and including methods for bucket and object operations."""

    def create_bucket(self, bucket_name: str = None) -> dict:
        """
        Creating Bucket.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        response = self.s3_resource.create_bucket(Bucket=bucket_name)
        LOGGER.debug("Response: %s", str(response))

        return response

    def bucket_list(self) -> list:
        """
        Listing all the buckets.

        :return: response.
        """
        response = [bucket.name for bucket in self.s3_resource.buckets.all()]
        LOGGER.info(response)

        return response

    def put_object_with_all_kwargs(self, **kwargs):
        """
        Putting Object to the Bucket.
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
        Putting Object to the Bucket (mainly small file).

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
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=object_name,
                    Body=data,
                    Metadata={
                        m_key: m_value})
            elif metadata:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=object_name,
                    Body=data,
                    Metadata=metadata)
            elif content_md5:
                response = self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=object_name,
                    Body=data,
                    ContentMD5=content_md5)
            else:
                response = self.s3_client.put_object(
                    Bucket=bucket_name, Key=object_name, Body=data)
            LOGGER.debug(response)

        return response

    def object_upload(self,
                      bucket_name: str = None,
                      object_name: str = None,
                      file_path: str = None) -> str:
        """
        Uploading Object to the Bucket.

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
        Listing Objects.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        bucket = self.s3_resource.Bucket(bucket_name)
        response_obj = [obj.key for obj in bucket.objects.all()]
        LOGGER.debug(response_obj)

        return response_obj

    def list_objects_with_prefix(
            self,
            bucket_name: str = None,
            prefix: str = None,
            maxkeys: int = None) -> list:
        """
        Listing objects of a bucket having specified prefix.

        :param bucket_name: Name of the bucket
        :param prefix: Object prefix used while uploading an object to bucket
        :param maxkeys: Sets the maximum number of keys returned in the response.
        :return: List of objects of a bucket having specified prefix.
        """
        resp = None
        if prefix:
            resp = self.s3_client.list_objects(
                Bucket=bucket_name, Prefix=prefix)
        if maxkeys:
            resp = self.s3_client.list_objects(
                Bucket=bucket_name, MaxKeys=maxkeys)
        LOGGER.debug("Resp is : %s", str(resp))
        obj_lst = [obj['Key'] for obj in resp['Contents']]
        LOGGER.debug(obj_lst)

        return obj_lst

    def head_bucket(self, bucket_name: str = None) -> dict:
        """
        To determine if a bucket exists and you have permission to access it.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        response_bucket = self.s3_resource.meta.client.head_bucket(
            Bucket=bucket_name)
        # Since we are getting http response from head bucket, we have appended
        # bucket name for validation.
        response_bucket["BucketName"] = bucket_name
        LOGGER.debug(response_bucket)

        return response_bucket

    def delete_object(self, bucket_name: str = None,
                      obj_name: str = None) -> dict:
        """
        Deleting Object.

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
        Getting Bucket Location.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        LOGGER.debug("BucketName: %s", bucket_name)
        response = self.s3_resource.meta.client.get_bucket_location(
            Bucket=bucket_name)
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
        response = self.s3_resource.meta.client.head_object(
            Bucket=bucket_name, Key=key)
        LOGGER.debug(response)

        return response

    def object_download(self,
                        bucket_name: str = None,
                        obj_name: str = None,
                        file_path: str = None,
                        **kwargs) -> str:
        """
        Downloading Object of the required Bucket.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        self.s3_resource.Bucket(bucket_name).download_file(obj_name, file_path, **kwargs)
        LOGGER.debug(
            "The %s has been downloaded successfully at mentioned file path %s",
            obj_name,
            file_path)

        return file_path

    def delete_bucket(
            self,
            bucket_name: str = None,
            force: bool = False) -> dict:
        """
        Deleting the empty bucket or deleting the buckets along with objects stored in it.

        :param bucket_name: Name of the bucket.
        :param force: Value for delete bucket with object or without object.
        :return: response.
        """
        bucket = self.s3_resource.Bucket(bucket_name)
        self.object_list(bucket_name)
        if force:
            LOGGER.info(
                "This might cause data loss as you have opted for bucket deletion with "
                "objects in it")
            response = bucket.objects.all().delete()
            LOGGER.debug(
                "Objects deleted successfully from bucket %s, response: %s", bucket_name, response)
            self.object_list(bucket_name)
        response = bucket.delete()
        LOGGER.debug("Bucket '%s' deleted successfully. Response: %s", bucket_name,response)

        return response

    def get_bucket_size(self, bucket_name: str = None) -> dict:
        """
        Getting size of bucket.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        # total_size = 0
        LOGGER.info("Getting bucket size")
        response = self.s3_resource.Bucket(bucket_name)
        LOGGER.debug(response)

        return response

    def get_object(self, bucket: str = None, key: str = None) -> dict:
        """
        Getting byte range of the object.

        :param bucket: Name of the bucket.
        :param key: Key of object.
        :return: response.
        """
        response = self.s3_client.get_object(
            Bucket=bucket, Key=key)
        LOGGER.debug(response)

        return response

    def put_object_with_storage_class(self,
                                      bucket_name: str = None,
                                      object_name: str = None,
                                      file_path: str = None,
                                      storage_class: str = None) -> dict:
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
        LOGGER.debug(
            "bucket_name: %s, object_name: %s, file_path: %s, storage_class: %s",
            bucket_name,
            object_name,
            file_path,
            storage_class)
        with open(file_path, "rb") as data:
            response = self.s3_client.put_object(
                Bucket=bucket_name,
                Key=object_name,
                Body=data,
                StorageClass=storage_class)
            LOGGER.debug(response)

        return response
