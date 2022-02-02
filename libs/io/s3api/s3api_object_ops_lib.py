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

"""Python Library to perform object operations using boto3 module."""

import os
import logging

from libs.io.s3api.s3api_core_lib import S3ApiRest

LOGGER = logging.getLogger(__name__)


class S3Object(S3ApiRest):
    """Class for object operations."""

    def upload_object(self, bucket_name: str = None, object_name: str = None,
                      file_path: str = None) -> dict:
        """
        Uploading object to the Bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        response = self.s3_resource.meta.client.upload_file(file_path, bucket_name, object_name)
        LOGGER.info(response)

        return response

    def list_objects(self, bucket_name: str = None) -> list:
        """
        Listing Objects.

        :param bucket_name: Name of the bucket.
        :return: response.
        """
        bucket = self.s3_resource.Bucket(bucket_name)
        all_objects = [obj.key for obj in bucket.objects.all()]
        LOGGER.debug(all_objects)

        return all_objects

    def delete_object(self, bucket_name: str = None, obj_name: str = None) -> dict:
        """
        Deleting object.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of object.
        :return: response.
        """
        response = self.s3_resource.Object(bucket_name, obj_name).delete()
        logging.debug(response)
        LOGGER.info("Object '%s' deleted Successfully", obj_name)

        return response

    def head_object(self, bucket_name: str = None, key: str = None) -> dict:
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

    def download_object(self, bucket_name: str = None, obj_name: str = None,
                        file_path: str = None) -> str:
        """
        Downloading Object of the required Bucket.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        response = self.s3_resource.Bucket(bucket_name).download_file(obj_name, file_path)
        if os.path.exists(file_path):
            LOGGER.debug("Object '%s' downloaded successfully on '%s'", obj_name, file_path)

        return response

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
        response = self.s3_client.copy_object(
            Bucket=dest_bucket,
            CopySource='/{}/{}'.format(source_bucket, source_object),
            Key=dest_object,
            **kwargs
            )
        LOGGER.debug(response)

        return response
