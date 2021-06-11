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
import re
import time
import multiprocessing as mp
from boto3.s3.transfer import TransferConfig
from commons.utils import config_utils
from commons.worker import Workers
from commons import params
from libs.di import di_base
from libs.di import data_man
from libs.di import data_generator
from commons.params import USER_JSON

uploadObjects = []
LOGGER = logging.getLogger(__name__)


class Uploader:
    """Simulates Uploads client upto 10k."""
    tsfrConfig = TransferConfig(multipart_threshold=1024 * 1024 * 16,
                                max_concurrency=320,
                                multipart_chunksize=1024 * 1024 * 16,
                                use_threads=True)

    def __init__(self):
        self.change_manager = data_man.DataManager()
        self.eventual_stop = mp.Event()

    def upload(self, user, keys, buckets, files_count, prefs):
        user_name = user.replace('_', '-')
        timestamp = time.strftime(params.DT_PATTERN_PREFIX)
        s3connections = di_base.init_s3_conn(user_name=user_name,
                                             keys=keys,
                                             nworkers=params.NWORKERS)
        pool_len = len(s3connections)

        workers = Workers()
        workers.start_workers(func=self._upload)

        for bucket in buckets:
            for ix in range(files_count):
                workQ = queue.Queue()
                workQ.func = self._upload
                kwargs = dict()
                kwargs['user'] = user
                kwargs['bucket'] = bucket
                kwargs['s3connections'] = s3connections
                kwargs['pool_len'] = pool_len
                kwargs['file_number'] = ix
                kwargs['prefs'] = prefs
                workQ.put(kwargs)
                workers.wenque(workQ)
                LOGGER.info(f"Enqueued item {ix} for download and checksum compare")
            LOGGER.info(f"processed items {ix} to upload for user {user}")
        workers.end_workers()
        LOGGER.info('Upload Workers shutdown completed successfully')
        if len(uploadObjects) > 0:
            with open(params.UPLOADED_FILES, 'a', newline='') as fp:
                wr = csv.writer(fp, quoting=csv.QUOTE_NONE, delimiter=',', quotechar='', escapechar='\\')
                fcntl.flock(fp, fcntl.LOCK_EX)
                wr.writerows(uploadObjects)
                fcntl.flock(fp, fcntl.LOCK_UN)
        LOGGER.info(f'Upload completed for user {user}')

    def _upload(self, kwargs):
        bucket = kwargs['bucket']
        m = kwargs['file_number']
        s3connections = kwargs['s3connections']
        pool_len = kwargs['pool_len']
        user_name = kwargs['user']
        prefs = kwargs['prefs']
        prefix = prefs.get('prefix_dir', 'test-1')  # todo revisit

        # todo get random compression ratio and process prefs
        # get random size
        if not self.eventual_stop.is_set():
            seed = data_generator.DataGenerator.get_random_seed()
            size = random.sample(data_generator.SMALL_BLOCK_SIZES, 1)[0]
            gen = data_generator.DataGenerator(c_ratio=2)
            buf, csum = gen.generate(size, seed=seed)
            file_path = gen.save_buf_to_file(buf, csum, 1024 * 1024, prefix)
            s3 = s3connections[random.randint(0, pool_len - 1)]
            try:
                s3.meta.client.upload_file(str(file_path),
                                           bucket,
                                           os.path.basename(file_path),
                                           Config=Uploader.tsfrConfig)
                print(f'uploaded file {file_path} for user {user_name}')
            except Exception as e:
                LOGGER.info(f'{file_path} in bucket {bucket} Upload caught exception: {e}')
            else:
                LOGGER.info(f'{file_path} in bucket {bucket} Upload Done')
                with open(file_path, 'rb') as fp:
                    md5sum = hashlib.md5(fp.read()).hexdigest()
                obj_name = os.path.basename(file_path)
                stat_info = os.stat(file_path)
                row_data = [user_name, bucket, obj_name, md5sum]
                uploadObjects.append(row_data)
                file_object = {
                    'name': obj_name, 'checksum': md5sum, 'seed': seed,
                    'size': size,
                    'mtime': stat_info.st_mtime
                }
                self.change_manager.add_file_to_bucket(
                    user_name, bucket, file_object)

    def start(self, users, buckets, files_count, prefs):
        LOGGER.info(f'Starting uploads for users {users}')
        # check if users comply to specific schema
        users_home = params.LOG_DIR
        users_path = os.path.join(users_home, USER_JSON)
        config_utils.create_content_json(
            users_path, users, ensure_ascii=False)  # need test name prefix
        self.jobs = []

        for user, udict in users.items():
            keys = [udict['accesskey'], udict['secretkey']]
            buckets = udict["buckets"]
            p = mp.Process(target=self.upload, args=(
                user, keys, buckets, files_count, prefs))
            self.jobs.append(p)
        for p in self.jobs:
            if not self.eventual_stop.is_set():
                p.start()

        for p in self.jobs:
            if p.is_alive():
                LOGGER.info("started joining")
                p.join()
        LOGGER.info(f'Upload started for all users {users}')

    def get_eventual_stop(self):
        return self.eventual_stop

    def set_eventual_stop(self, stop):
        self.eventual_stop.set()

    def stop(self, stop_spawining=False):
        if stop_spawining:
            self.set_eventual_stop(stop_spawining)
