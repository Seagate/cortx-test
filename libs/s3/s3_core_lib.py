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
import logging
import boto3
import boto3.s3

from commons import commands
from commons.utils.system_utils import run_local_cmd, create_file

LOGGER = logging.getLogger(__name__)


class S3Lib:
    """Class initialising s3 connection and including methods for bucket and object operations."""

    def __init__(self,
                 access_key: str = None,
                 secret_key: str = None,
                 endpoint_url: str = None,
                 s3_cert_path: str = None,
                 **kwargs) -> None:
        """
        method initializes members of S3Lib.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        region = kwargs.get("region", None)
        aws_session_token = kwargs.get("aws_session_token", None)
        debug = kwargs.get("debug", False)
        if debug:
            # Uncomment to enable debug
            boto3.set_stream_logger(name="botocore")
        try:
            self.s3_resource = boto3.resource(
                "s3",
                verify=s3_cert_path,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
                region_name=region,
                aws_session_token=aws_session_token)
            self.s3_client = boto3.client("s3", verify=s3_cert_path,
                                          aws_access_key_id=access_key,
                                          aws_secret_access_key=secret_key,
                                          endpoint_url=endpoint_url,
                                          region_name=region,
                                          aws_session_token=aws_session_token)
        except Exception as Err:
            if "unreachable network" not in str(Err):
                LOGGER.critical(Err)

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
        if force:
            LOGGER.info(
                "This might cause data loss as you have opted for bucket deletion with "
                "objects in it")
            bucket.objects.all().delete()
            LOGGER.debug(
                "Bucket : %s , got deleted successfully with objects in it",
                bucket_name)
        response = bucket.delete()
        logging.debug(response)

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


class Multipart(S3Lib):
    """Class containing methods to implement multipart functionality."""

    def create_multipart_upload(self,
                                bucket_name: str = None,
                                obj_name: str = None,
                                m_key: str = None,
                                m_value: str = None) -> dict:
        """
        Request to initiate a multipart upload.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param m_key: Key for metadata.
        :param m_value:  Value for metadata.
        :return: response
        """
        if m_key:
            response = self.s3_client.create_multipart_upload(
                Bucket=bucket_name, Key=obj_name, Metadata={m_key: m_value})
        else:
            response = self.s3_client.create_multipart_upload(
                Bucket=bucket_name, Key=obj_name)
        LOGGER.debug("Response: %s", str(response))

        return response

    def upload_part(self,
                    body: str = None,
                    bucket_name: str = None,
                    object_name: str = None,
                    **kwargs) -> dict:
        """
        Upload parts of a specific multipart upload.

        :param body: content of the object.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :keyword content_md5: base64-encoded MD5 digest of message
        :return:
        """
        upload_id = kwargs.get("upload_id", None)
        part_number = kwargs.get("part_number", None)
        content_md5 = kwargs.get("content_md5", None)
        if content_md5:
            response = self.s3_client.upload_part(
                Body=body, Bucket=bucket_name, Key=object_name,
                UploadId=upload_id, PartNumber=part_number,
                ContentMD5=content_md5)
        else:
            response = self.s3_client.upload_part(
                Body=body, Bucket=bucket_name, Key=object_name,
                UploadId=upload_id, PartNumber=part_number)
        logging.debug(response)

        return response

    def list_parts(
            self,
            mpu_id: str = None,
            bucket: str = None,
            object_name: str = None) -> dict:
        """
        list parts of a specific multipart upload.

        :param mpu_id: Multipart upload ID
        :param bucket: Name of the bucket
        :param object_name: Name of the object
        :return: response
        """
        response = self.s3_client.list_parts(
            Bucket=bucket, Key=object_name, UploadId=mpu_id)
        LOGGER.debug(response)

        return response

    def complete_multipart_upload(
            self,
            mpu_id: str = None,
            parts: list = None,
            bucket: str = None,
            object_name: str = None) -> dict:
        """
        Complete a multipart upload, s3 creates an object by concatenating the parts.

        :param mpu_id: Multipart upload ID
        :param parts: Uploaded parts
        :param bucket: Name of the bucket
        :param object_name: Name of the object
        :return: response
        """
        LOGGER.info("initiated complete multipart upload")
        result = self.s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=object_name,
            UploadId=mpu_id,
            MultipartUpload={"Parts": parts})
        LOGGER.debug(result)

        return result

    def list_multipart_uploads(self, bucket: str = None) -> dict:
        """
        List all initiated multipart uploads.

        :param bucket: Name of the bucket.
        :return: response.
        """
        result = self.s3_client.list_multipart_uploads(Bucket=bucket)
        LOGGER.debug(result)

        return result

    def abort_multipart_upload(
            self,
            bucket: str = None,
            object_name: str = None,
            upload_id: str = None) -> dict:
        """
        Abort multipart upload for given upload_id.

        After aborting a multipart upload, you cannot upload any part using that upload ID again.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :param upload_id: Name of the object.
        :return: response.
        """
        response = self.s3_client.abort_multipart_upload(
            Bucket=bucket, Key=object_name, UploadId=upload_id)
        LOGGER.debug(response)

        return response

    def get_object(
            self,
            bucket: str = None,
            key: str = None,
            ranges: str = None) -> dict:
        """
        Getting byte range of the object.

        :param bucket: Name of the bucket.
        :param key: Key of object.
        :param ranges: Range in bytes.
        :return: response.
        """
        response = self.s3_client.get_object(
            Bucket=bucket, Key=key, Range=ranges)
        LOGGER.debug(response)

        return response


class Tagging(S3Lib):
    """Class containing methods to implement bucket and object tagging functionality."""

    def set_bucket_tags(self, bucket_name: str = None,
                        tag_set: dict = None) -> dict:
        """
        Set one or multiple tags to a bucket.

        :param bucket_name: Name of the bucket.
        :param tag_set: Tags set.
        :return: response.
        """
        bucket_tagging = self.s3_resource.BucketTagging(bucket_name)
        response = bucket_tagging.put(Tagging=tag_set)
        LOGGER.debug(response)

        return response

    def get_bucket_tagging(self, bucket_name: str = None) -> dict:
        """
        Get bucket tagging.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        response = self.s3_client.get_bucket_tagging(Bucket=bucket_name)
        LOGGER.debug(response)

        return response

    def delete_bucket_tagging(self, bucket_name: str = None) -> dict:
        """
        Delete all bucket tags.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        bucket_tagging = self.s3_resource.BucketTagging(bucket_name)
        response = bucket_tagging.delete()
        LOGGER.debug(response)

        return response

    def put_object_tagging(
            self,
            bucket: str = None,
            key: str = None,
            tags: dict = None) -> dict:
        """
        Set the supplied tag-set to an object that already exists in a bucket.

        :param bucket: Name of the bucket.
        :param key: Key for object tagging.
        :param tags: Tag for the object.
        :return: response.
        """
        response = self.s3_client.put_object_tagging(
            Bucket=bucket, Key=key, Tagging=tags)
        LOGGER.debug(response)

        return response

    def get_object_tagging(
            self,
            bucket: str = None,
            obj_name: str = None) -> dict:
        """
        Return the tag-set of an object.

        :param bucket: Name of the bucket.
        :param obj_name: Name of the object.
        :return: response.
        """
        response = self.s3_client.get_object_tagging(
            Bucket=bucket, Key=obj_name)
        LOGGER.debug(response)

        return response

    def delete_object_tagging(
            self,
            bucket_name: str = None,
            obj_name: str = None) -> dict:
        """
        Remove the tag-set from an existing object.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :return: response.
        """
        response = self.s3_client.delete_object_tagging(
            Bucket=bucket_name, Key=obj_name)
        LOGGER.debug(response)

        return response

    def put_object_with_tagging(self,
                                bucket_name: str = None,
                                object_name: str = None,
                                data: str = None,
                                **kwargs) -> dict:
        """
        Putting Object to the Bucket (mainly small file) with tagging and metadata.

        :param data:  handle of file path.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :return: response.
        """
        tag = kwargs.get("tag", None)
        meta = kwargs.get("meta", None)
        if meta:
            response = self.s3_resource.Bucket(bucket_name).put_object(
                Key=object_name, Body=data, Tagging=tag, Metadata=meta)
        else:
            response = self.s3_resource.Bucket(bucket_name).put_object(
                Key=object_name, Body=data, Tagging=tag)
        LOGGER.debug(response)

        return response


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
        :param grant_full_control: Gives the grantee READ, READ_ACP, and WRITE_ACP permissions
         on the object.
        :param grant_read: Allows grantee to read the object data and its metadata.
        :param grant_read_acp: Allows grantee to read the object ACL.
        :param grant_write: Allows grantee to create, overwrite, and delete any object
        in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
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
        :param grant_full_control: Gives the grantee READ, READ_ACP, and WRITE_ACP permissions
         on the object.
        :param grant_read: Allows grantee to read the object data and its metadata.
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
        :param grant_full_control: Gives the grantee. READ, READ_ACP, and WRITE_ACP permissions
         on the object.
        :param grant_read: Allows grantee to read the object data and its metadata.
        :param grant_read_acp: Allows grantee to read the object ACL.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable object.
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

    def create_bucket_with_acl(self,
                               bucket_name: str = None,
                               acl: str = None,
                               **kwargs) -> dict:
        """
        Create bucket with given acl and grant permissions.

        :param bucket_name: Name of the bucket.
        :param acl: The canned ACL to apply to the bucket.
                    e.g.'private'|'public-read'|'public-read-write'|'authenticated-read'.
        :param grant_full_control: Allows grantee the read, write, read ACP, and write ACP
         permissions on the bucket.
        :param grant_read: Allows grantee to list the objects in the bucket.
        :param grant_read_acp: Allows grantee to read the bucket ACL.
        :param grant_write: Allows grantee to create, overwrite, and delete any object
         in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
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
        :param grant_full_control: Allows grantee the read, write, read ACP, and write ACP
         permissions on the bucket.
        :param grant_read: Allows grantee to list the objects in the bucket.
        :param grant_read_acp: Allows grantee to read the bucket ACL.
        :param grant_write: Allows grantee to create, overwrite, and delete any object
         in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
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
        :param grant_full_control: Allows grantee the read, write, read ACP, and write ACP
         permissions on the bucket.
        :param grant_read: Allows grantee to list the objects in the bucket.
        :param grant_read_acp: Allows grantee to read the bucket ACL.
        :param grant_write: Allows grantee to create, overwrite, and delete any object
         in the bucket.
        :param grant_write_acp: Allows grantee to write the ACL for the applicable bucket.
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


class BucketPolicy(S3Lib):
    """Class containing methods to implement bucket policy functionality."""

    def get_bucket_policy(self, bucket_name: str = None) -> tuple:
        """
        Retrieve policy of the specified s3 bucket.

        :param bucket_name: Name of s3 bucket
        :return: Returns the policy of a specified s3 bucket
        and Success if successful, None and error message if failed.
        """
        response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
        LOGGER.debug(response)

        return response

    def put_bucket_policy(
            self,
            bucket_name: str = None,
            bucket_policy: dict = None) -> dict:
        """
        Apply s3 bucket policy to specified s3 bucket.

        :param bucket_name: Name of s3 bucket
        :param bucket_policy: Bucket policy
        :return: Returns status and status message
        """
        self.s3_client.put_bucket_policy(
            Bucket=bucket_name, Policy=bucket_policy)

        return bucket_policy

    def delete_bucket_policy(self, bucket_name: str = None) -> dict:
        """
        Function will delete the policy applied to the specified S3 bucket.

        :param bucket_name: Name of s3 bucket.
        :return: Returns status and response of delete bucket policy operation.
        """
        LOGGER.debug("BucketName: %s", bucket_name)
        resp = self.s3_client.delete_bucket_policy(Bucket=bucket_name)
        LOGGER.debug("Bucket policy delete resp : %s", str(resp))
        resp["BucketName"] = bucket_name

        return resp


class S3LibCmd(S3Lib):
    """Class containing methods to implement aws cmd functionality."""

    @staticmethod
    def upload_object_cli(
            bucket_name: str = None,
            object_name: str = None,
            file_path: str = None) -> tuple:
        """
        Uploading Object to the Bucket using aws cli.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        cmd = commands.S3_UPLOAD_FILE_CMD.format(
            file_path, bucket_name, object_name)
        response = run_local_cmd(cmd, flg=True)
        LOGGER.debug("Response: %s", str(response))

        return response

    @staticmethod
    def upload_folder_cli(
            bucket_name: str = None,
            folder_path: str = None,
            profile_name: str = None) -> tuple:
        """
        Uploading folder to the Bucket using aws cli.

        :param bucket_name: Name of the bucket.
        :param folder_path: Path of the folder.
        :param profile_name: AWS profile name.
        :return: response.
        """
        cmd = commands.S3_UPLOAD_FOLDER_CMD.format(
            folder_path, bucket_name, profile_name)
        response = run_local_cmd(cmd, flg=True)
        LOGGER.debug("Response: %s", str(response))

        return response

    @staticmethod
    def download_bucket_cli(
            bucket_name: str = None,
            folder_path: str = None,
            profile_name: str = None) -> tuple:
        """
        Downloading s3 objects to a local directory recursively using awscli.

        :param bucket_name: Name of the bucket.
        :param folder_path: Folder path.
        :param profile_name: AWS profile name.
        :return: download bucket cli response.
        """
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        cmd = commands.S3_DOWNLOAD_BUCKET_CMD.format(
            bucket_name, folder_path, profile_name)
        response = run_local_cmd(cmd, flg=True)
        LOGGER.debug("Response: %s", str(response))

        return response
