# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""Multithreaded and greenlet Upload tasks. Upload files and data blobs."""

import os
import sys
import queue
import random
import logging
import csv
import fcntl
import hashlib
import multiprocessing as mp
import boto3
import re
import json
import time
import errno
from pathlib import Path
from boto3.s3.transfer import TransferConfig
from libs.di import di_lib
from libs.di.di_lib import Workers
from libs.di import di_params
from libs.di.di_mgmt_ops import ManagementOPs
from commons.cortxlogging import init_loghandler
from config import CMN_CFG
from config import S3_CFG


SCRIPT_HOME = os.getcwd()
uploadObjects = []
logger = logging.getLogger(__name__)


class Uploader:
    """Simulates Uploads client upto 10k."""
    tsfrConfig = TransferConfig(multipart_threshold=1024 * 1024 * 16,
                                max_concurrency=10,
                                multipart_chunksize=1024 * 1024 * 16,
                                use_threads=True)

    @staticmethod
    def upload(user, keys, buckets):

        user_name = user
        access_key = keys[0]
        secret_key = keys[1]
        #timestamp = time.strftime("%Y%m%d-%H%M%S")
        #buckets = [user_name + '-' + timestamp + '-bucket' + str(i) for i in range(nbuckets)]
        s3connections = list()
        for ix in range(di_lib.NWORKERS):
            try:
                s3 = boto3.resource('s3', aws_access_key_id=access_key,
                                    aws_secret_access_key=secret_key,
                                    endpoint_url="https://s3.seagate.com")
            except Exception as e:
                logger.info(f'could not create s3 object for user {user_name} with '
                            f'access key {access_key} secret key {secret_key} exception:{e}')
                return
            else:
                s3connections.append(s3)
        pool_len = len(s3connections)
        for bucket in buckets:
            try:
                file1 = open(di_params.DATASET_FILES,"r")
                obj_file_paths = file1.readlines()
            except Exception as e:
                logger.info(f'could not access file {di_params.DATASET_FILES} exception:{e}')
                return
            else:
                logger.info(f'able to access file {di_params.DATASET_FILES}')

            # try:
            #
            #     s3.create_bucket(Bucket=bucket)
            # except Exception as e:
            #     logger.info(f'could not create create bucket {bucket} exception:{e}')
            # else:
            #     logger.info(f'create bucket {bucket} Done')
            #
            workers = Workers()
            workers.wStartWorkers(func=Uploader._upload)

            for ix, each_line in enumerate(obj_file_paths):
                reg = '\(\'(.+)\''
                m = re.search(reg, each_line)
                if m:
                    workQ = queue.Queue()
                    workQ.func = Uploader._upload
                    kwargs = dict()
                    kwargs['user'] = user
                    kwargs['bucket'] = bucket
                    kwargs['s3connections'] = s3connections
                    kwargs['pool_len'] = pool_len
                    kwargs['match'] = m
                    workQ.put(kwargs)
                    workers.wEnque(workQ)
                    logger.info(f"Enqueued item {ix} for download and checksum compare")
            logger.info(f"processed items {ix} to upload for user {user}")
            workers.wEndWorkers()
            logger.info('Upload Workers shutdown completed successfully')
        if len(uploadObjects) > 0:
            with open(di_params.UPLOADED_FILES, 'a', newline='') as fp:
                wr = csv.writer(fp, quoting=csv.QUOTE_NONE, delimiter=',', quotechar='',escapechar='\\')
                fcntl.flock(fp, fcntl.LOCK_EX)
                wr.writerows(uploadObjects)
                fcntl.flock(fp, fcntl.LOCK_UN)
        logger.info(f'Upload completed for user {user}')

    @staticmethod
    def _upload(kwargs):
        bucket = kwargs['bucket']
        m = kwargs['match']
        s3connections = kwargs['s3connections']
        pool_len = kwargs['pool_len']
        user_name = kwargs['user']
        each_file_path = di_params.DATAGEN_HOME + m.group(1)
        s3 = s3connections[random.randint(0, pool_len - 1)]
        try:
            s3.meta.client.upload_file(str(each_file_path), bucket, os.path.basename(each_file_path))
            #                           Config=Uploader.tsfrConfig)
            print(f'uploaded file {each_file_path} for user {user_name}')
        except Exception as e:
            logger.info(f'{each_file_path} in bucket {bucket} Upload caught exception: {e}')
        else:
            logger.info(f'{each_file_path} in bucket {bucket} Upload Done')
            with open(each_file_path, 'rb') as fp:
                md5sum = hashlib.md5(fp.read()).hexdigest()
            obj_name = os.path.basename(each_file_path)
            row_data = [user_name, bucket, obj_name, md5sum]
            uploadObjects.append(row_data)

    @staticmethod
    def start(users):
        logger.info('Starting uploads')
        try:
            os.remove(di_params.uploadFinishedFileName)
        except Exception as e:
            logger.info(f'file not able to remove: {e}')
        try:
            os.remove(di_params.UPLOADED_FILES)
        except Exception as e:
            logger.info(f'file not able to remove: {e}')

        di_lib.create_iter_content_json(SCRIPT_HOME, users)

        jobs = []
        for user,keys in users.items():
            p = mp.Process(target=Uploader.upload, args=(user,keys, uploadObjects))
            jobs.append(p)
        for p in jobs:
            p.start()
        for p in jobs:
            p.join()
        logger.info('Upload Done for all users')
        #with open(di_params.uploadFinishedFileName, 'w') as f:
        #    pass

