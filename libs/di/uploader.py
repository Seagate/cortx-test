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

"""Multithreaded and greenlet based Upload tasks. Upload files and data blobs."""

import os
import queue
import random
import logging
import csv
import fcntl
import hashlib
import multiprocessing as mp
import re
from boto3.s3.transfer import TransferConfig
from commons.utils import config_utils
from commons.worker import Workers
from commons import params
from libs.di import di_base
from libs.di import data_man
from commons.params import USER_JSON


uploadObjects = []
logger = logging.getLogger(__name__)


class Uploader:
    """Simulates Uploads client upto 10k."""
    tsfrConfig = TransferConfig(multipart_threshold=1024 * 1024 * 16,
                                max_concurrency=320,
                                multipart_chunksize=1024 * 1024 * 16,
                                use_threads=True)
    change_manager = None

    @staticmethod
    def upload(user, keys, buckets):

        user_name = user
        Uploader.change_manager = data_man.DataManager(user=user)
        s3connections = di_base.init_s3_conn(user_name=user_name,
                                             keys=keys,
                                             nworkers=params.NWORKERS)
        pool_len = len(s3connections)
        for bucket in buckets:
            try:
                file1 = open(params.DATASET_FILES,"r")
                obj_file_paths = file1.readlines()
            except Exception as e:
                logger.info(f'could not access file {params.DATASET_FILES} exception:{e}')
                return
            else:
                logger.info(f'able to access file {params.DATASET_FILES}')

            workers = Workers()
            workers.start_workers(func=Uploader._upload)

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
                    workers.wenque(workQ)
                    logger.info(f"Enqueued item {ix} for download and checksum compare")
            logger.info(f"processed items {ix} to upload for user {user}")
            workers.end_workers()
            logger.info('Upload Workers shutdown completed successfully')
        if len(uploadObjects) > 0:
            with open(params.UPLOADED_FILES, 'a', newline='') as fp:
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
        each_file_path = params.DATAGEN_HOME + m.group(1)
        s3 = s3connections[random.randint(0, pool_len - 1)]
        try:
            s3.meta.client.upload_file(str(each_file_path),
                                       bucket,
                                       os.path.basename(each_file_path),
                                       Config=Uploader.tsfrConfig)
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
            Uploader.change_manager.add_files_to_bucket(user_name,
                                                        bucket,
                                                        obj_name,
                                                        md5sum,
                                                        size
                                                        )

    @staticmethod
    def start(users):
        logger.info('Starting uploads')
        try:
            os.remove(params.UPLOAD_FINISHED_FILENAME)
        except Exception as e:
            logger.info(f'file not able to remove: {e}')
        try:
            os.remove(params.UPLOADED_FILES)
        except Exception as e:
            logger.info(f'file not able to remove: {e}')
        users_home = params.LOG_DIR
        users_path = os.path.join(users_home, USER_JSON)
        config_utils.create_content_json(users_path, users, ensure_ascii=False)

        jobs = []
        for user,keys in users.items():
            p = mp.Process(target=Uploader.upload, args=(user,keys, uploadObjects))
            jobs.append(p)
        for p in jobs:
            p.start()
        for p in jobs:
            p.join()
        logger.info('Upload Done for all users')
        with open(params.UPLOAD_FINISHED_FILENAME, 'w') as lck:
            pass
