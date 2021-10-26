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
import csv
import time
import os
import logging
import random
import boto3
from boto3.exceptions import S3UploadFailedError, ResourceNotExistsError
from botocore.exceptions import ClientError
from botocore.client import Config
from locust import events
from scripts.locust import LOCUST_CFG
from commons.utils import system_utils

LOGGER = logging.getLogger(__name__)

OBJ_NAME = LOCUST_CFG['default']['OBJ_NAME']
GET_OBJ_PATH = LOCUST_CFG['default']['GET_OBJ_PATH']


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
        s3_cert_path = os.getenv(
            'CA_CERT', LOCUST_CFG['default']['S3_CERT_PATH'])
        max_pool_connections = int(
            LOCUST_CFG['default']['MAX_POOL_CONNECTIONS'])
        self.bucket_list = list()

        self.s3_client = session.client(
            service_name="s3",
            verify=s3_cert_path,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            config=Config(max_pool_connections=max_pool_connections))

        self.s3_resource = session.resource(
            service_name="s3",
            verify=s3_cert_path,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            config=Config(max_pool_connections=max_pool_connections))

        self.checksumfile = LOCUST_CFG["default"]["CHECKSUM_FILE"]

    def store_checksum(self, bucket, object, checksum):
        with open(self.checksumfile, "a", newline='') as checksum_f:
            w = csv.writer(checksum_f)
            w.writerow((bucket, object, checksum))

    def get_checksum(self):
        data = {}
        with open(self.checksumfile, "r") as checksum_f:
            raw = list(csv.reader(checksum_f))
        for item in raw:
            bucket, obj, checksum = item[0], item[1], item[2]
            if bucket in data:
                data[bucket].update({obj: checksum})
            else:
                data.update({bucket: {obj: checksum}})
        return data

    @staticmethod
    def create_file(object_size: int):
        """
        Creates file of random size from the given range
        :param object_size: object file size
        """
        with open(OBJ_NAME, 'wb') as fout:
            fout.write(os.urandom(object_size))

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

    def get_objects(self, bucket_name):
        bucket = self.s3_resource.Bucket(bucket_name)
        objects = [obj.key for obj in bucket.objects.all()]
        return objects

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
                events.request_success.fire(
                    request_type="put",
                    name="create_bucket",
                    response_time=self.total_time(start_time),
                    response_length=10
                )
            except ClientError as error:
                LOGGER.error("Create bucket failed with error: %s", error)
                events.request_failure.fire(
                    request_type="put",
                    name="create_bucket",
                    response_time=self.total_time(start_time),
                    response_length=10,
                    exception=error
                )
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
                if bucket in self.bucket_list:
                    self.bucket_list.pop(bucket)
                LOGGER.info("Deleted bucket : %s", bucket)
                events.request_success.fire(
                    request_type="delete",
                    name="delete_bucket",
                    response_time=self.total_time(start_time),
                    response_length=10,
                )
            except ClientError as error:
                LOGGER.error("Delete bucket failed with error: %s", error)
                events.request_failure.fire(
                    request_type="delete",
                    name="delete_bucket",
                    response_time=self.total_time(start_time),
                    response_length=10,
                    exception=error
                )

    def put_object(self, bucket_name: str, object_size: int):
        """
        Method to put object of given size into given bucket
        :param bucket_name: Name of the bucket
        :param object_size: Size of the object
        """
        self.delete_local_obj(OBJ_NAME)
        self.create_file(object_size)
        obj_name = "test_obj{0}".format(str(time.time()))
        checksum = system_utils.calculate_checksum(OBJ_NAME)[1]
        self.store_checksum(bucket_name, obj_name, checksum)
        LOGGER.info("Uploading object %s into bucket %s checksum %s",
                    obj_name, bucket_name, checksum)
        start_time = time.time()
        try:
            self.s3_client.upload_file(OBJ_NAME, bucket_name, obj_name)
            events.request_success.fire(
                request_type="put",
                name="put_object",
                response_time=self.total_time(start_time),
                response_length=10
            )
        except (ClientError, S3UploadFailedError, FileNotFoundError) as error:
            LOGGER.error("Upload object failed with error: %s", error)
            events.request_failure.fire(
                request_type="put",
                name="put_object",
                response_time=self.total_time(start_time),
                response_length=10,
                exception=error
            )

    def download_object(self, bucket_name: str):
        """
        Method to download any random object from the given bucket
        :param bucket_name: Name of the bucket
        """
        start_time = time.time()
        try:
            bucket = self.s3_resource.Bucket(bucket_name)
            objects = [obj.key for obj in bucket.objects.all()]
            if len(objects) > 1:
                self.delete_local_obj(GET_OBJ_PATH)
                obj_name = random.choice(objects)
                LOGGER.info(
                    "Starting downloading the object %s form bucket %s",
                    obj_name,
                    bucket)
                if obj_name in self.get_objects(bucket_name):
                    bucket.download_file(obj_name, GET_OBJ_PATH)
                    LOGGER.info(
                        "The %s has been downloaded successfully at %s ",
                        obj_name,
                        GET_OBJ_PATH)
                    events.request_success.fire(
                        request_type="get",
                        name="download_object",
                        response_time=self.total_time(start_time),
                        response_length=10
                    )
                    checksums = self.get_checksum()
                    checksum = system_utils.calculate_checksum(GET_OBJ_PATH)[1]
                    if checksums[bucket_name][obj_name] != checksum:
                        LOGGER.error("Stored Checksum: %s & Calculated Checksum: %s",
                                     checksums[bucket_name][obj_name], checksum)
                    else:
                        LOGGER.info("Object %s bucket %s downloaded successfully, checksum %s",
                                    obj_name, bucket_name, checksum)
                else:
                    LOGGER.info(
                        "The %s has been already downloaded and deleted successfully from %s ",
                        obj_name, bucket_name)
        except self.s3_client.exceptions.NoSuchKey:
            LOGGER.info(
                "Download object is not possible as key is not present on %s",
                bucket_name)
        except ClientError as error:
            if "HeadObject operation: Not Found" not in error.args[0]:
                LOGGER.error("Download object failed with error: %s", error)
                events.request_failure.fire(
                    request_type="get",
                    name="download_object",
                    response_time=self.total_time(start_time),
                    response_length=10,
                    exception=error
                )

    def delete_object(self, bucket_name: str):
        """
        Method to delete any random object from given bucket
        :param bucket_name: Name of the bucket
        """
        start_time = time.time()
        try:
            bucket = self.s3_resource.Bucket(bucket_name)
            objects = [obj.key for obj in bucket.objects.all()]
            if len(objects) > 1:
                obj_name = random.choice(objects)
                LOGGER.info(
                    "Deleting object %s from the bucket %s",
                    obj_name,
                    bucket)
                if obj_name in self.get_objects(bucket_name):
                    self.s3_resource.Object(bucket_name, obj_name).delete()
                    events.request_success.fire(
                        request_type="delete",
                        name="delete_object",
                        response_time=self.total_time(start_time),
                        response_length=10
                    )
                    LOGGER.info(
                        "%s object deleted succesfully from the bucket %s",
                        obj_name, bucket)
                else:
                    LOGGER.info(
                        "The %s has been already deleted successfully from %s",
                        obj_name, bucket_name)
        except ResourceNotExistsError as error:
            LOGGER.error("Delete object failed with error: %s", error)
            events.request_failure.fire(
                request_type="delete",
                name="delete_object",
                response_time=self.total_time(start_time),
                response_length=10,
                exception=error
            )
