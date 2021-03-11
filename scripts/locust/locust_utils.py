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
# Utility methods written for use accross all the locust test scenarios

import time
import os
import logging
import configparser
import random
import boto3
from botocore.client import Config
from locust import events

LOGGER = logging.getLogger(__name__)

locust_cfg = configparser.ConfigParser()
locust_cfg.read('scripts/locust/locust_config.ini')

OBJ_NAME = locust_cfg['default']['OBJ_NAME']
GET_OBJ_PATH = locust_cfg['default']['GET_OBJ_PATH']


class LocustUtils:
    """
    Locust Utility methods
    """
    def __init__(self):
        session = boto3.session.Session()
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        endpoint_url = locust_cfg['default']['ENDPOINT_URL']
        s3_cert_path = locust_cfg['default']['S3_CERT_PATH']
        max_pool_connections = int(locust_cfg['default']['MAX_POOL_CONNECTIONS'])

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

    @staticmethod
    def create_file(object_size: int):
        """
        Creates file of random size from the given range
        :param object_size: object file size
        """
        with open(OBJ_NAME, 'wb') as fout:
            fout.write(os.urandom(object_size))

    def create_buckets(self, bucket_count: int) -> list:
        """
        Method to create number of buckets equal to given bucket count
        :param bucket_count: number of buckets to be created
        :return: list of created buckets
        """
        bucket_list = list()
        for i in range(bucket_count):
            bucket_name = "locust-bucket{}".format(str(time.time()))
            start_time = time.time()
            LOGGER.info("Creating bucket: {}".format(bucket_name))
            try:
                resp = self.s3_client.create_bucket(Bucket=bucket_name)
                bucket_list.append(bucket_name)
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                    request_type="put",
                    name="create_bucket",
                    response_time=total_time,
                    response_length=len(resp)
                )
            except Exception as error:
                total_time = int((time.time() - start_time) * 1000)
                LOGGER.error("Create bucket failed with error: %s", error)
                events.request_failure.fire(
                    request_type="put",
                    name="create_bucket",
                    response_time=total_time,
                    exception=error
                )
        LOGGER.info("Buckets Created: %s", bucket_list)
        return bucket_list

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
                LOGGER.info("Deleted bucket : {}".format(bucket))
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                    request_type="delete",
                    name="delete_bucket",
                    response_time=total_time,
                    response_length=10,
                )
            except Exception as error:
                total_time = int((time.time() - start_time) * 1000)
                LOGGER.error("Delete bucket failed with error: %s", error)
                events.request_failure.fire(
                    request_type="delete",
                    name="delete_bucket",
                    response_time=total_time,
                    exception=error
                )

    def put_object(self, bucket: str, object_size: int):
        """
        Method to put object of given size into given bucket
        :param bucket: Name of the bucket
        :param object_size: Size of the object
        """
        if os.path.exists(OBJ_NAME):
            try:
                os.remove(OBJ_NAME)
            except OSError as error:
                LOGGER.error(error)
        self.create_file(object_size)
        obj_name = "test_obj{0}".format(str(time.time()))
        LOGGER.info("Uploading object {0} into bucket {1}".format(obj_name, bucket))
        start_time = time.time()
        try:
            self.s3_client.upload_file(OBJ_NAME, bucket, obj_name)
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                    request_type="put",
                    name="put_object",
                    response_time=total_time,
                    response_length=10
                    )
        except Exception as error:
            total_time = int((time.time() - start_time) * 1000)
            LOGGER.error("Upload object failed with error: %s", error)
            events.request_failure.fire(
                request_type="put",
                name="put_object",
                response_time=total_time,
                exception=error
            )

    def download_object(self, bucket: str):
        """
        Method to download any random object from the given bucket
        :param bucket: Name of the bucket
        """
        bucket = self.s3_resource.Bucket(bucket)
        objects = [obj.key for obj in bucket.objects.all()]
        if len(objects) > 1:
            start_time = time.time()
            if os.path.exists(GET_OBJ_PATH):
                try:
                    os.remove(GET_OBJ_PATH)
                except OSError as error:
                    LOGGER.error(error)
            obj_name = random.choice(objects)
            LOGGER.info("Starting downloading the object %s form bucket %s", obj_name, bucket)
            try:
                resp = self.s3_resource.Bucket(bucket).download_file(obj_name, GET_OBJ_PATH)
                LOGGER.info("The %s has been downloaded successfully at %s ", obj_name, GET_OBJ_PATH)
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                    request_type="get",
                    name="download_object",
                    response_time=total_time,
                    response_length=len(resp)
                )
            except Exception as error:
                total_time = int((time.time() - start_time) * 1000)
                LOGGER.error("Download object failed with error: %s", error)
                events.request_failure.fire(
                    request_type="get",
                    name="download_object",
                    response_time=total_time,
                    exception=error
                )

    def delete_object(self, bucket: str):
        """
        Method to delete any random object from given bucket
        :param bucket: Name of the bucket
        """
        bucket = self.s3_resource.Bucket(bucket)
        objects = [obj.key for obj in bucket.objects.all()]
        if len(objects) > 1:
            start_time = time.time()
            obj_name = random.choice(objects)
            LOGGER.info("Deleting object %s from the bucket %s", obj_name, bucket)
            try:
                resp = self.s3_resource.Object(bucket, obj_name).delete()
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                    request_type="delete",
                    name="delete_object",
                    response_time=total_time,
                    response_length=len(resp)
                )
            except Exception as error:
                total_time = int((time.time() - start_time) * 1000)
                LOGGER.error("Download object failed with error: %s", error)
                events.request_failure.fire(
                    request_type="delete",
                    name="delete_object",
                    response_time=total_time,
                    exception=error
                )
