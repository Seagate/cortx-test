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

"""Python Library to perform multipart operations using boto3 module."""

import logging
import os

from src.commons import cal_percent
from src.io.s3api.s3_restapi import S3RestApi

logger = logging.getLogger(__name__)


class S3MultiParts(S3RestApi):
    """Class for Multipart operations."""

    async def create_multipart_upload(self, bucket_name: str, obj_name: str) -> dict:
        """
        Request to initiate a multipart upload.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :return: Response of create multipart upload.
        """
        async with self.get_client() as client:
            response = await client.create_multipart_upload(Bucket=bucket_name, Key=obj_name)
            logger.debug(
                "create_multipart_upload: %s/%s, Response: %s",
                bucket_name,
                obj_name,
                response)

        return response

    async def upload_part(self, body: bytes, bucket_name: str, object_name: str, **kwargs) -> dict:
        """
        Upload parts of a specific multipart upload.

        :param body: content of the object.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :upload_id: upload id of the multipart upload.
        :part_number: part number to be uploaded.
        :return: response of upload part.
        """
        upload_id = kwargs.get("upload_id")
        part_number = kwargs.get("part_number")
        async with self.get_client() as client:
            response = await client.upload_part(
                Body=body, Bucket=bucket_name, Key=object_name,
                UploadId=upload_id, PartNumber=part_number)
            logging.debug("upload_part: %s/%s", bucket_name, object_name, response)

        return response

    async def list_parts(self, mpu_id: str, bucket_name: str, object_name: str) -> list:
        """
        list parts of a specific multipart upload.

        :param mpu_id: Multipart upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :return: Response of list parts.
        """
        parts = list()
        async with self.get_client() as client:
            paginator = client.get_paginator('list_parts')
            async for result in paginator.paginate(
                    Bucket=bucket_name, Key=object_name, UploadId=mpu_id):
                for content in result.get('Parts', []):
                    parts.append(content)
            logger.debug("list_parts: %s/%s, parts: %s", bucket_name, object_name, parts)

        return parts

    async def complete_multipart_upload(
            self,
            mpu_id: str,
            parts: list,
            bucket: str,
            object_name: str) -> dict:
        """
        Complete a multipart upload, s3 creates an object by concatenating the parts.

        :param mpu_id: Multipart upload ID.
        :param parts: Uploaded parts in sorted ordered.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :return: response of complete multipart upload.
        """
        logger.debug("initiated complete multipart upload")
        async with self.get_client() as client:
            response = await client.complete_multipart_upload(
                Bucket=bucket,
                Key=object_name,
                UploadId=mpu_id,
                MultipartUpload={"Parts": parts})
            logger.debug(
                "complete_multipart_upload: %s/%s, response: %s",
                bucket,
                object_name,
                response)

        return response

    async def list_multipart_uploads(self, bucket_name: str) -> list:
        """
        List all initiated multipart uploads.

        :param bucket_name: Name of the bucket.
        :return: response of list multipart uploads.
        """
        uploads = list()
        async with self.get_client() as client:
            paginator = client.get_paginator('list_multipart_uploads')
            async for result in paginator.paginate(Bucket=bucket_name):
                for content in result.get('Uploads', []):
                    uploads.append(content)
            logger.debug("list_multipart_uploads: %s, Uploads: %s", bucket_name, uploads)

        return uploads

    async def abort_multipart_upload(self,
                                     bucket_name: str,
                                     object_name: str,
                                     upload_id: str) -> dict:
        """
        Abort multipart upload for given upload_id.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param upload_id: Name of the object.
        :return: Response of abort multipart upload.
        """
        async with self.get_client() as client:
            response = await client.abort_multipart_upload(
                Bucket=bucket_name, Key=object_name, UploadId=upload_id)
            logger.debug("abort_multipart_upload: %s, Response: %s", bucket_name, response)

        return response

    async def upload_part_copy(self, copy_source: str, bucket_name: str,
                               object_name: str, **kwargs) -> dict:
        """
        Upload parts of a specific multipart upload from existing object.

        :param copy_source: source of part copy.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :upload_id: upload id of the multipart upload.
        :part_number: part number to be uploaded.
        :return: response of the upload part copy.
        """
        upload_id = kwargs.get("upload_id")
        part_number = kwargs.get("part_number")
        async with self.get_client() as client:
            response = await client.upload_part_copy(
                Bucket=bucket_name, Key=object_name,
                UploadId=upload_id, PartNumber=part_number,
                CopySource=copy_source)
            logging.debug("upload_part_copy: copy source: %s to %s/%s, Response: %s",
                          copy_source, bucket_name, object_name, response)

        return response

    async def upload_parts(self,
                           mpu_id: int,
                           bucket_name: str,
                           object_name: str,
                           multipart_obj_path: str,
                           total_parts: int) -> list:
        """
        Upload parts for a specific multipart upload ID.

        :param mpu_id: Multipart Upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param total_parts: No. of parts to be uploaded.
        :param multipart_obj_path: Path of object file.
        :return: (Boolean, List of uploaded parts).
        """
        parts = list()
        uploaded_bytes = 0
        if not os.path.exists(multipart_obj_path):
            raise IOError("File path '%s' does not exists.", multipart_obj_path)
        multipart_obj_size = os.stat(multipart_obj_path).st_size
        single_part_size = multipart_obj_size // int(total_parts)
        async with open(multipart_obj_path, "rb") as file_pointer:
            i = 1
            while True:
                data = file_pointer.read(single_part_size)
                logger.info("data_len %s", str(len(data)))
                if not data:
                    break
                part = await self.upload_part(
                    data, bucket_name, object_name, upload_id=mpu_id, part_number=i)
                logger.debug("Part : %s", str(part))
                parts.append({"PartNumber": i, "ETag": part["ETag"]})
                uploaded_bytes += len(data)
                logger.debug(
                    "{0} of {1} uploaded ({2:.2f}%)".format(
                        uploaded_bytes,
                        multipart_obj_size *
                        1048576,
                        cal_percent(
                            uploaded_bytes,
                            multipart_obj_size *
                            1048576)))
                i += 1
        logger.info("upload_parts: %s/%s, Parts: %s", bucket_name, object_name, parts)

        return parts
