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

"""Python Library to perform object operations using boto3 module."""

import os
import logging
import hashlib

from libs.io.s3api.s3_restapi import S3RestApi

LOGGER = logging.getLogger(__name__)


class S3Object(S3RestApi):
    """Class for object operations."""

    def upload_object(self, bucket_name: str, object_name: str, file_path: str) -> dict:
        """
        Uploading object to the Bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: Response of the upload s3 object.
        """
        response = self.s3_resource.meta.client.upload_file(file_path, bucket_name, object_name)
        LOGGER.debug(response)

        return response

    def list_objects(self, bucket_name: str) -> list:
        """
        Listing Objects.

        :param bucket_name: Name of the bucket.
        :return: Response of the list objects.
        """
        bucket = self.s3_resource.Bucket(bucket_name)
        objects = [obj.key for obj in bucket.objects.all()]
        LOGGER.debug(objects)

        return objects

    def delete_object(self, bucket_name: str, obj_name: str) -> dict:
        """
        Deleting object.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of object.
        :return: Response of delete object.
        """
        response = self.s3_resource.Object(bucket_name, obj_name).delete()
        logging.debug(response)
        LOGGER.debug("Object '%s' deleted Successfully", obj_name)

        return response

    def head_object(self, bucket_name: str, key: str) -> dict:
        """
        Retrieve metadata from an object without returning the object itself.

        you must have READ access to the object.
        :param bucket_name: Name of the bucket.
        :param key: Key of object.
        :return: Response of head object.
        """
        response = self.s3_resource.meta.client.head_object(Bucket=bucket_name, Key=key)
        LOGGER.debug(response)

        return response

    def get_object(self, bucket: str = None, key: str = None, ranges: str = None) -> dict:
        """
        Getting object or byte range of the object.

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

    def download_object(self, bucket_name: str, obj_name: str, file_path: str) -> dict:
        """
        Downloading Object of the required Bucket.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param file_path: Path of the file.
        :return: Response of download object.
        """
        response = self.s3_resource.Bucket(bucket_name).download_file(obj_name, file_path)
        if os.path.exists(file_path):
            LOGGER.debug("Object '%s' downloaded successfully on '%s'", obj_name, file_path)

        return response

    def copy_object(self,
                    source_bucket: str,
                    source_object: str,
                    dest_bucket: str,
                    dest_object: str,
                    **kwargs) -> tuple:
        """
        Copy of an object that is already stored in Seagate S3 with different permissions.

        :param source_bucket: The name of the source bucket.
        :param source_object: The name of the source object.
        :param dest_bucket: The name of the destination bucket.
        :param dest_object: The name of the destination object.
        :param kwargs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services
        /s3.html#S3.Client.copy_object
        :return: Response of copy object.
        """
        response = self.s3_client.copy_object(
            Bucket=dest_bucket,
            CopySource='/{}/{}'.format(source_bucket, source_object),
            Key=dest_object,
            **kwargs
        )
        LOGGER.debug(response)

        return response

    def get_s3object_checksum(self, bucket_name: str, object_name: str, chunk_size: int) -> str:
        """
        Read object in chunk and calculate md5sum.

        :param bucket_name: The name of the s3 bucket.
        :param object_name: The name of the s3 object.
        :param chunk_size: size to read the content of s3 object.
        """
        file_obj = self.s3_resource.Object(bucket_name, object_name).get()['Body']
        file_hash = hashlib.sha256()
        content = file_obj.read(chunk_size)
        file_hash.update(content)
        while content:
            content = file_obj.read(chunk_size)
            if content:
                file_hash.update(content)

        return file_hash.hexdigest()
