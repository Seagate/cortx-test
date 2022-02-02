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

"""Python Library to perform multipart operations using boto3 module."""

import logging

from libs.io.s3api.s3api_core_lib import S3ApiRest

LOGGER = logging.getLogger(__name__)


class S3MultiParts(S3ApiRest):
    """Class for Multipart operations."""

    def create_multipart_upload(self, bucket_name: str = None, obj_name: str = None) -> dict:
        """
        Request to initiate a multipart upload.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :return: response
        """
        response = self.s3_client.create_multipart_upload(Bucket=bucket_name, Key=obj_name)
        LOGGER.debug("Response: %s", response)

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
        :return:
        """
        upload_id = kwargs.get("upload_id", None)
        part_number = kwargs.get("part_number", None)
        response = self.s3_client.upload_part(
            Body=body, Bucket=bucket_name, Key=object_name,
            UploadId=upload_id, PartNumber=part_number)
        logging.debug(response)

        return response

    def list_parts(
            self,
            mpu_id: str = None,
            bucket: str = None,
            object_name: str = None,) -> dict:
        """
        list parts of a specific multipart upload.

        :param mpu_id: Multipart upload ID
        :param bucket: Name of the bucket
        :param object_name: Name of the object
        :return: response
        """
        response = self.s3_client.list_parts(Bucket=bucket, Key=object_name, UploadId=mpu_id)
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

        :param mpu_id: Multipart upload ID.
        :param parts: Uploaded parts in sorted ordered.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :return: response
        """
        LOGGER.info("initiated complete multipart upload")
        response = self.s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=object_name,
            UploadId=mpu_id,
            MultipartUpload={"Parts": parts})
        LOGGER.debug(response)

        return response

    def list_multipart_uploads(self, bucket: str = None) -> dict:
        """
        List all initiated multipart uploads.

        :param bucket: Name of the bucket.
        :return: response.
        """
        response = self.s3_client.list_multipart_uploads(Bucket=bucket)
        LOGGER.debug(response)

        return response

    def abort_multipart_upload(self, bucket: str = None, object_name: str = None,
                               upload_id: str = None) -> dict:
        """
        Abort multipart upload for given upload_id.

        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :param upload_id: Name of the object.
        :return: response.
        """
        response = self.s3_client.abort_multipart_upload(
            Bucket=bucket, Key=object_name, UploadId=upload_id)
        LOGGER.debug(response)

        return response

    def upload_part_copy(self,
                         copy_source: str = None,
                         bucket_name: str = None,
                         object_name: str = None,
                         **kwargs) -> dict:
        """
        Upload parts of a specific multipart upload from existing object.

        :param copy_source: source of part copy.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :upload_id: upload id of the multipart upload
        :part_number: part number to be uploaded
        :return: response.
        """
        upload_id = kwargs.get("upload_id", None)
        part_number = kwargs.get("part_number", None)
        response = self.s3_client.upload_part_copy(
            Bucket=bucket_name, Key=object_name,
            UploadId=upload_id, PartNumber=part_number,
            CopySource=copy_source)
        logging.debug(response)

        return response
