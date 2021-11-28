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
"""
Utility methods written for use accross all the locust test scenarios
"""
import logging
import os
import time
from distutils.util import strtobool

import boto3
from boto3.exceptions import Boto3Error
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError, ConnectionClosedError
from locust import events

from commons.utils import system_utils
from core.runner import InMemoryDB
from scripts.locust import LOCUST_CFG

LOGGER = logging.getLogger(__name__)

OBJ_NAME = LOCUST_CFG['default']['OBJ_NAME']
GET_OBJ_PATH = LOCUST_CFG['default']['GET_OBJ_PATH']
OBJECT_CACHE = InMemoryDB(1024*1024)


class LocustUtils:
    """
    Locust Utility methods
    """

    def __init__(self):
        session = boto3.session.Session()
        access_key = os.getenv(
            'AWS_ACCESS_KEY_ID',
            LOCUST_CFG['default']['ACCESS_KEY'])
        secret_key = os.getenv(
            'AWS_SECRET_ACCESS_KEY',
            LOCUST_CFG['default']['SECRET_KEY'])
        endpoint_url = os.getenv(
            'ENDPOINT_URL', LOCUST_CFG['default']['ENDPOINT_URL'])
        self.use_ssl = bool(strtobool(os.getenv('USE_SSL')))
        if os.getenv('CA_CERT').lower() == "false":
            self.s3_cert_path = False
        else:
            self.s3_cert_path = os.getenv('CA_CERT')
        LOGGER.info("use_ssl: %s s3_cert_path: %s", self.use_ssl, self.s3_cert_path)
        max_pool_connections = int(
            LOCUST_CFG['default']['MAX_POOL_CONNECTIONS'])
        self.bucket_list = list()
        self.empty_buckets = list()

        self.s3_client = session.client(
            service_name="s3",
            use_ssl=self.use_ssl,
            verify=self.s3_cert_path,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            config=Config(max_pool_connections=max_pool_connections))

        self.s3_resource = session.resource(
            service_name="s3",
            use_ssl=self.use_ssl,
            verify=self.s3_cert_path,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            config=Config(max_pool_connections=max_pool_connections))

    @staticmethod
    def delete_checksum(bucket, object_key):
        """Delete checksum from local DB"""
        global OBJECT_CACHE
        # LOGGER.info("delete_checksum %s/%s", bucket, object_key)
        OBJECT_CACHE.delete(f"{bucket}/{object_key}")

    @staticmethod
    def store_checksum(bucket, object_key, checksum):
        """Store checksum in local DB"""
        global OBJECT_CACHE
        # LOGGER.info("store_checksum %s/%s", bucket, object_key)
        OBJECT_CACHE.store(f"{bucket}/{object_key}", checksum)

    @staticmethod
    def pop_one_random():
        """Pop one random object entry from local DB"""
        global OBJECT_CACHE
        bucket_object, crc = OBJECT_CACHE.pop_one()
        if not bucket_object or not crc:
            return False, False, False
        bucket = bucket_object.split("/")[0]
        object_name = bucket_object.split("/")[1]
        return bucket, object_name, crc

    @staticmethod
    def create_file(object_size: int):
        """
        Creates file of random size from the given range
        :param object_size: object file size
        """
        new_obj = GET_OBJ_PATH + str(time.time())
        with open(new_obj, 'wb') as fout:
            fout.write(os.urandom(object_size))
        return new_obj

    @staticmethod
    def delete_local_obj(object_path: str):
        if system_utils.path_exists(object_path):
            try:
                system_utils.remove_file(object_path)
            except OSError as error:
                LOGGER.error(error)

    @staticmethod
    def total_time(start_time: float) -> float:
        """
        Method to calculate total time for a request to be completed
        :param start_time: Time when request was initialized
        :return: Total time take by request
        """
        return int((time.time() - start_time) * 1000)

    def create_buckets(self, bucket_count: int):
        """
        Method to create number of buckets equal to given bucket count
        :param bucket_count: number of buckets to be created
        """
        for _ in range(bucket_count):
            bucket_name = "locust-bucket{}".format(str(time.time()))
            start_time = time.time()
            LOGGER.info("Creating bucket: %s", bucket_name)
            try:
                self.s3_client.create_bucket(Bucket=bucket_name)
                self.bucket_list.append(bucket_name)
                events.request_success.fire(request_type="put", name="create_bucket",
                                            response_time=self.total_time(start_time),
                                            response_length=10)
            except (Boto3Error, BotoCoreError, ClientError, ConnectionClosedError) as error:
                LOGGER.error("Bucket creation %s failed: %s", bucket_name, error)
                events.request_failure.fire(request_type="put", name="create_bucket",
                                            response_time=self.total_time(start_time),
                                            response_length=10, exception=error)
        LOGGER.info("Buckets Created: %s", self.bucket_list)

    def delete_buckets(self, bucket_list: list):
        """
        Method to delete buckets from the given list along with objects in it
        :param bucket_list: list of buckets to be deleted forcefully
        """
        LOGGER.info("Bucket list: %s", bucket_list)
        for bucket in bucket_list:
            start_time = time.time()
            try:
                bucket = self.s3_resource.Bucket(bucket)
                bucket.objects.all().delete()
                bucket.delete()
            except (Boto3Error, BotoCoreError, ClientError, ConnectionClosedError) as error:
                LOGGER.error("Bucket deletion %s failed: %s", bucket, error)
                events.request_failure.fire(request_type="delete", name="delete_bucket",
                                            response_time=self.total_time(start_time),
                                            response_length=10, exception=error)
            else:
                if bucket in self.bucket_list:
                    self.bucket_list.pop(bucket)
                LOGGER.info("Deleted bucket : %s", bucket)
                events.request_success.fire(request_type="delete", name="delete_bucket",
                                            response_time=self.total_time(start_time),
                                            response_length=10)

    def put_object(self, bucket_name: str, object_size: int):
        """
        Method to put object of given size into given bucket
        :param bucket_name: Name of the bucket
        :param object_size: Size of the object
        """
        object_name = self.create_file(object_size)
        checksum = system_utils.calculate_checksum(object_name)[1]
        log_prefix = f"{bucket_name}/{object_name}"
        LOGGER.info("Uploading %s checksum %s", log_prefix, checksum)
        start_time = time.time()
        try:
            self.s3_client.upload_file(object_name, bucket_name, object_name)
        except (Boto3Error, BotoCoreError, ClientError, ConnectionClosedError) as error:
            LOGGER.error("Upload object %s failed: %s", log_prefix, error)
            events.request_failure.fire(request_type="put", name="put_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10, exception=error)
        else:
            events.request_success.fire(request_type="put", name="put_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10)
            self.store_checksum(bucket_name, object_name, checksum)
        self.delete_local_obj(object_name)

    def head_object(self):
        """Method to head random object"""
        bucket_name, object_name, checksum_original = self.pop_one_random()
        log_prefix = f"{bucket_name}/{object_name}"
        if not bucket_name or not object_name or not checksum_original:
            LOGGER.info("Nothing to head")
            return
        LOGGER.info("Starting head object %s", log_prefix)
        start_time = time.time()
        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=object_name)
        except (Boto3Error, BotoCoreError, ClientError, ConnectionClosedError) as error:
            LOGGER.error("Head object %s failed: %s", log_prefix, error)
            events.request_failure.fire(request_type="head", name="head_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10, exception=error)
        else:
            events.request_success.fire(request_type="head", name="head_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10)
            self.store_checksum(bucket_name, object_name, checksum_original)

    def download_object(self):
        """
        Method to download any random object from the given bucket
        """
        start_time = time.time()
        download_path = GET_OBJ_PATH + str(start_time)
        self.delete_local_obj(download_path)
        bucket_name, object_name, checksum_original = self.pop_one_random()
        log_prefix = f"{bucket_name}/{object_name}"
        if not bucket_name or not object_name or not checksum_original:
            LOGGER.info("Nothing to download")
            return
        try:
            LOGGER.info("Starting object download %s", log_prefix)
            bucket = self.s3_resource.Bucket(bucket_name)
            bucket.download_file(object_name, download_path)
        except (Boto3Error, BotoCoreError, ClientError, ConnectionClosedError) as error:
            LOGGER.error("Download object %s failed: %s", log_prefix, error)
            events.request_failure.fire(request_type="get", name="download_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10, exception=error)
        else:
            self.store_checksum(bucket_name, object_name, checksum_original)
            LOGGER.info("Downloaded successfully object %s at %s", log_prefix, download_path)
            events.request_success.fire(request_type="get", name="download_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10)
            checksum = system_utils.calculate_checksum(download_path)[1]
            if checksum_original != checksum:
                LOGGER.error("Checksum does not matched for %s. Stored Checksum %s "
                             "Calculated Checksum %s", log_prefix, checksum_original, checksum)
            else:
                LOGGER.info("Checksum matched for %s. Stored Checksum %s Calculated Checksum %s",
                            log_prefix, checksum_original, checksum)
            self.delete_local_obj(download_path)

    def delete_object(self):
        """
        Method to delete any random object from given bucket
        """
        start_time = time.time()
        bucket_name, object_name, checksum_original = self.pop_one_random()
        if not bucket_name or not object_name or not checksum_original:
            LOGGER.info("Nothing to delete")
            return
        log_prefix = f"{bucket_name}/{object_name}"
        LOGGER.info("Deleting object %s", log_prefix)
        try:
            self.s3_resource.Object(bucket_name, object_name).delete()
        except (Boto3Error, BotoCoreError, ClientError, ConnectionClosedError) as error:
            LOGGER.error("Deletion object %s failed: %s", log_prefix, error)
            events.request_failure.fire(request_type="delete", name="delete_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10, exception=error)
            self.store_checksum(bucket_name, object_name, checksum_original)
        else:
            events.request_success.fire(request_type="delete", name="delete_object",
                                        response_time=self.total_time(start_time),
                                        response_length=10)
            LOGGER.info("Deleted successfully %s", log_prefix)
            self.delete_checksum(bucket_name, object_name)
