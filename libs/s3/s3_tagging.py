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

"""Python Library using boto3 module to perform tagging Operations."""

import logging
from libs.s3.s3_core_lib import S3Lib

LOGGER = logging.getLogger(__name__)


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
