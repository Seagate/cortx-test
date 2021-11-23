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

"""Python Library using boto3 module to perform multipart Operations."""

import logging
from libs.s3.s3_core_lib import S3Lib

LOGGER = logging.getLogger(__name__)


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
            object_name: str = None,
            part_number_marker: int = 0) -> dict:
        """
        list parts of a specific multipart upload.
        :param mpu_id: Multipart upload ID
        :param bucket: Name of the bucket
        :param object_name: Name of the object
        :param part_number_marker: next part number in case parts greater than 1000.
        :return: response
        """
        if part_number_marker:
            response = self.s3_client.list_parts(
                Bucket=bucket, Key=object_name, UploadId=mpu_id,
                PartNumberMarker=part_number_marker)
        else:
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

    def list_multipart_uploads_with_keymarker(
            self,
            bucket: str = None,
            keymarker: str = None) -> dict:
        """
        List all initiated multipart uploads.
        :param bucket: Name of the bucket.
        :keymarker: key marker of more than >1000 mpu
        :return: response.
        """
        result = self.s3_client.list_multipart_uploads(Bucket=bucket, KeyMarker=keymarker)
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
