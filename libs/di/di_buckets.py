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

"""The module validates the S3 bucket's data uploaded by Seagate's s3bench.
The data can be verified after interleaved executions as well.
"""
import os
import queue
import logging
import csv
import hashlib
import re
import base64
from pathlib import Path
from libs.di.di_base import _init_s3_conn
from libs.di.di_params import DOWNLOAD_HOME
from commons.worker import Workers

LOGGER = logging.getLogger(__name__)

pool = list()
FailedFiles = list()
FailedFilesCSV = "FailedFiles.csv"


def compare_checksum_after_download(user, keys, bucket, nworkers):
    """
    List the objects from specified bucket or global bucket and download and verifies the
    checksum. This function supports DI/downloading of data uploaded from Seagate's S3bench.
    :param bucket: bucket name
    :param user: username
    :param keys: access key and secret list
    :return:
    """
    user_name = user
    access_key = keys[0]
    secret_key = keys[1]
    s3 = _init_s3_conn(access_key, secret_key, user_name)
    test_bucket = s3.Bucket(bucket)
    for ix in range(nworkers):
        try:
            if not os.path.exists(os.path.join(DOWNLOAD_HOME, "ps", str(ix))):
                _path = os.mkdirs(os.path.join(DOWNLOAD_HOME, "ps", str(ix)))
        except (OSError, Exception) as exec:
            LOGGER.error(str(exec))
            LOGGER.error(f"Error while creating directory for process {ix}")

    workers = Workers()
    workers.start_workers()
    counter = 0
    for my_bucket_object in test_bucket.objects.all():
        workQ = queue.Queue()
        workQ.func = download_and_compare
        kwargs = dict()
        kwargs['key'] = key = my_bucket_object.key
        pat = re.compile('^.*_([A-Z2-7]+)_[0-9]+$')
        match = re.search(pat, key)
        if match:
            checksum = match.group(1)
        kwargs['s3'] = pool[counter % nworkers]
        kwargs['bucket'] = 'test-bucket1'
        kwargs['objcsum'] = checksum
        kwargs['accesskey'] = keys[0]
        kwargs['secret'] = keys[1]
        kwargs['pid'] = counter % nworkers
        workQ.put(kwargs)
        workers.wenque(workQ)
        counter += 1

    if len(FailedFiles) > 0:
        keys = FailedFiles[0].keys()
        with open(FailedFilesCSV, 'w', newline='') as fp:
            wr = csv.DictWriter(fp, keys)
            wr.writerows(FailedFiles)
    workers.end_workers()
    LOGGER.info('Workers shutdown completed successfully')


def download_and_compare(kwargs):
    """
    Downloads files complying to format
    <prefix>_<b32encoded checksum>_seqno
    prefix = s3bench's default or user specified
    Go lang b32encoded sha512 checksum is dismantled and padded to decode from python
    seqno is a numeric value.

    """
    try:
        s3 = kwargs.get('s3')
        key = kwargs.get('key')
        pid = kwargs.get('pid')
        bucket = kwargs.get('bucket')
        objcsum = kwargs.get('objcsum')
        cwd = DOWNLOAD_HOME
        objectpath = os.path.join(cwd, "ps", str(pid), key)
        LOGGER.info(f'Send download request for {key}')
        try:
            s3.meta.client.download_file(bucket, key, objectpath)
            LOGGER.info(f'download object successful : {key}')
        except Exception as e:
            LOGGER.exception(e)
            print(e)
            LOGGER.error(f'Download failed for {kwargs} with exception {e}')
            FailedFiles.append(kwargs)
        else:
            if len(objcsum) % 8:  # check the length of hash to find the padding needed
                if len(objcsum) % 8 == 7:
                    objcsum = objcsum + '='
            objsum_dec = objcsum
            objhash = base64.b32decode(objsum_dec)
            print("Downloaded '{}' from '{}'".format(objectpath, bucket))
            filepath = objectpath
            sz = Path(filepath).stat().st_size
            read_sz = 8192
            csum = None
            with open(filepath, 'rb') as fp:
                file_hash = hashlib.sha512()
                if sz < read_sz:
                    buf = fp.read(sz)
                else:
                    buf = fp.read(read_sz)
                while buf:
                    file_hash.update(buf)
                    buf = fp.read(read_sz)
                csum = file_hash.digest()
                try:
                    os.unlink(filepath)
                except (OSError, Exception) as fault:
                    LOGGER.error('Unlink unsuccessful with fault %s using rm.', fault)
                    rmLocalObject = "rm -rf " + str(filepath)
                    os.system(rmLocalObject)

            if objhash == csum.strip():
                LOGGER.info("download object checksum {} matches provided c"
                            "hecksum {} for file {}".format(csum, objcsum, objectpath))
            else:
                LOGGER.error(
                    "download object checksum {} does not matches provided "
                    "checksum {} for file {}".format(csum, objcsum, objectpath))
                FailedFiles.append(kwargs)
    except Exception as fault:
        LOGGER.exception(fault)
        LOGGER.error(f'Exception occurred for item {kwargs} with exception {fault}')
