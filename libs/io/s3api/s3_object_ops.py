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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""Python Library to perform object operations using boto3 module."""
import hashlib
import logging
import os
from typing import List

from libs.io.s3api.s3_restapi import S3RestApi

logger = logging.getLogger(__name__)


class S3Object(S3RestApi):
    """Class for object operations."""

    async def upload_object(self, bucket: str, key: str, file_path: str) -> dict:
        """
        Uploading object to the Bucket.

        :param bucket: Name of the bucket.
        :param key: Name of the object.
        :param file_path: Path of the file.
        :return: Response of the upload s3 object.
        """
        async with self.get_client() as s3client:
            with open(file_path, "rb") as body:
                response = await s3client.put_object(Body=body, Bucket=bucket, Key=key)
            logger.info("%s s3://%s/%s Response: %s", S3Object.upload_object.__name__, bucket, key,
                        response)
            return response

    async def list_objects(self, bucket: str) -> list:
        """
        Listing Objects.

        :param bucket: Name of the bucket.
        :return: Response of the list objects.
        """
        async with self.get_client() as s3client:
            paginator = s3client.get_paginator('list_objects')
            async for result in paginator.paginate(Bucket=bucket):
                objects = [c for c in result.get('Contents', [])]
                logger.info("%s s3://%s Objects: %s", S3Object.list_objects.__name__, bucket,
                            objects)
                return objects

    async def delete_object(self, bucket: str, key: str) -> dict:
        """
        Deleting object.

        :param bucket: Name of the bucket.
        :param key: Name of object.
        :return: Response of delete object.
        """
        async with self.get_client() as s3client:
            response = await s3client.delete_object(Bucket=bucket, Key=key)
            logger.info("%s s3://%s/%s Response: %s", S3Object.delete_object.__name__, bucket,
                        key, response)
            return response

    async def delete_objects(self, bucket: str, keys: List[str]) -> dict:
        """
        Deleting object.

        :param bucket: Name of the bucket.
        :param keys: List of object names.
        :return: Response of delete object.
        """
        objects = [{'Key': key} for key in keys]
        logger.info("Deleting %s", keys)
        async with self.get_client() as s3client:
            response = await s3client.delete_objects(Bucket=bucket, Delete={'Objects': objects})
            logger.info("%s s3://%s Response: %s", S3Object.delete_objects.__name__, bucket,
                        response)
            return response

    async def head_object(self, bucket: str, key: str) -> dict:
        """
        Retrieve metadata from an object without returning the object itself.

        :param bucket: Name of the bucket.
        :param key: Name of object.
        :return: Response of head object.
        """
        async with self.get_client() as s3client:
            response = await s3client.head_object(Bucket=bucket, Key=key)
            logger.info("%s s3://%s/%s Response: %s", S3Object.head_object.__name__, bucket, key,
                        response)
            return response

    async def get_object(self, bucket: str, key: str, ranges: str = "") -> dict:
        """
        Getting object or byte range of the object.

        :param bucket: Name of the bucket.
        :param key: Name of object.
        :param ranges: Byte range to be retrieved
        :return: response.
        """
        async with self.get_client() as s3client:
            response = await s3client.get_object(Bucket=bucket, Key=key, Range=ranges)
            logger.info("%s s3://%s/%s Response: %s", S3Object.get_object.__name__, bucket, key,
                        response)
            return response

    async def download_object(self, bucket: str, key: str, file_path: str,
                              chunk_size: int = 1024) -> dict:
        """
        Downloading Object of the required Bucket.

        :param bucket: Name of the bucket.
        :param key: Name of object.
        :param file_path: Path of the file.
        :param chunk_size: Download object in chunk sizes.
        :return: Response of download object.
        """
        async with self.get_client() as s3client:
            response = await s3client.get_object(Bucket=bucket, Key=key)
            logger.info("%s s3://%s/%s Response %s", S3Object.download_object.__name__, bucket, key,
                        response)
            async with response['Body'] as stream:
                chunk = await stream.read(chunk_size)
                logger.debug(chunk)
                while len(chunk) > 0:
                    with open(file_path, "wb+") as file_obj:
                        file_obj.write(chunk)
                    chunk = await stream.read(chunk_size)
        if os.path.exists(file_path):
            logger.info("%s s3://%s/%s Path: %s Response %s", S3Object.download_object.__name__,
                        bucket, key, file_path, response)
        return response

    async def copy_object(self, src_bucket: str, src_key: str, des_bucket: str, des_key: str,
                          **kwargs) -> dict:
        """
        Creates a copy of an object that is already stored in S3.

        :param src_bucket: The name of the source bucket.
        :param src_key: The name of the source object.
        :param des_bucket: The name of the destination bucket.
        :param des_key: The name of the destination object.
        :return: Response of copy object.
        """
        async with self.get_client() as s3client:
            response = await s3client.copy_object(Bucket=des_bucket,
                                                  CopySource=f'/{src_bucket}/{src_key}',
                                                  Key=des_key, **kwargs)
            logger.info("%s s3://%s/%s to s3://%s/%s Response %s", S3Object.copy_object.__name__,
                        src_bucket, src_key, des_bucket, des_key, response)
            return response

    async def get_s3object_checksum(self, bucket: str, key: str, chunk_size: int = 1024) -> str:
        """
        Read object in chunk and calculate md5sum.
        Do not store the object in local storage.

        :param bucket: The name of the s3 bucket.
        :param key: Name of object.
        :param chunk_size: size to read the content of s3 object.
        """
        async with self.get_client() as s3client:
            response = await s3client.get_object(Bucket=bucket, Key=key)
            logger.info("%s s3://%s/%s Response %s", S3Object.get_s3object_checksum.__name__,
                        bucket, key, response)
            async with response['Body'] as stream:
                chunk = await stream.read(chunk_size)
                file_hash = hashlib.sha256()
                logger.debug(chunk)
                while len(chunk) > 0:
                    file_hash.update(chunk)
                    chunk = await stream.read(chunk_size)
        sha256_digest = file_hash.hexdigest()
        logger.info("%s s3://%s/%s SHA-256 %s", S3Object.get_s3object_checksum.__name__, bucket,
                    key, sha256_digest)
        return sha256_digest

    @staticmethod
    def checksum_file(file_path: str, chunk_size: int = 1024 * 1024):
        """
        Calculate checksum of given file_path by reading file chunk_size at a time.
        :param file_path: Local file path
        :param chunk_size: single chunk size to read the content of given file
        """
        with open(file_path, 'rb') as f_obj:
            file_hash = hashlib.sha256()
            chunk = f_obj.read(chunk_size)
            logger.debug(chunk)
            while len(chunk) > 0:
                file_hash.update(chunk)
                chunk = f_obj.read(chunk_size)
        return file_hash.hexdigest()
