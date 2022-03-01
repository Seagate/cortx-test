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

"""Python Library to perform bucket operations using boto3 module."""

import logging
from libs.io.s3api.s3_restapi import S3RestApi

LOGGER = logging.getLogger(__name__)


class S3Bucket(S3RestApi):
    """Class for bucket operations."""

    async def create_bucket(self, bucket_name: str) -> dict:
        """
        Creating Bucket.

        :param bucket_name: Name of the bucket.
        :return: Response of create bucket.
        """
        async with self.get_client() as client:
            response = await client.create_bucket(Bucket=bucket_name)
            LOGGER.debug("create_bucket:%s, Response: %s", bucket_name, response)

        return response

    async def list_buckets(self) -> list:
        """
        Listing all the buckets.

        :return: Response of bucket list.
        """
        async with self.get_client() as client:
            buckets = await client.list_buckets()
            LOGGER.debug(buckets)
            response = [bucket["Name"] for bucket in buckets["Buckets"]]
            LOGGER.debug("list_buckets: Response: %s", response)

        return response

    async def head_bucket(self, bucket_name: str) -> dict:
        """
        To determine if a bucket exists and have a permission to access it.

        :param bucket_name: Name of the bucket.
        :return: Response of head bucket.
        """
        async with self.get_client() as client:
            response = await client.head_bucket(Bucket=bucket_name)
            LOGGER.debug("head_bucket: %s, Response: %s", bucket_name,response)

        return response

    async def get_bucket_location(self, bucket_name: str) -> dict:
        """
        Getting Bucket Location.

        :param bucket_name: Name of the bucket.
        :return: Response of bucket location.
        """
        async with self.get_client() as client:
            LOGGER.debug("BucketName: %s", bucket_name)
            response = await client.get_bucket_location(Bucket=bucket_name)
            LOGGER.debug("get_bucket_location: %s, Response: %s", bucket_name, response)

        return response

    async def delete_bucket(self, bucket_name: str, force: bool = False) -> dict:
        """
        Deleting the empty bucket or deleting the buckets along with objects stored in it.

        :param bucket_name: Name of the bucket.
        :param force: Value for delete bucket with object or without object.
        :return: Response of delete bucket.
        """
        async with self.get_client() as client:
            if force:
                LOGGER.debug("This might cause data loss as you have opted for bucket deletion"
                             " with objects in it")
                # list s3 objects using paginator
                paginator = client.get_paginator('list_objects')
                async for result in paginator.paginate(Bucket=bucket_name):
                    for content in result.get('Contents', []):
                        await client.delete_object(Bucket=bucket_name, Key=content['Key'])
                LOGGER.debug("All objects deleted successfully.")
            response = await client.delete_bucket(Bucket=bucket_name)
            LOGGER.debug("Bucket '%s' deleted successfully. Response: %s", bucket_name, response)

        return response
