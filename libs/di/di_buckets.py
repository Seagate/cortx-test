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
from commons.params import DOWNLOAD_HOME
from commons.worker import Workers
from commons.constants import NWORKERS
from typing import List

LOGGER = logging.getLogger(__name__)

pool = list()
FailedFiles = list()
FailedFilesCSV = "FailedFiles.csv"


def compare_checksum_after_download(user_name: str,
                                    keys: List,
                                    bucket: str,
                                    nworkers: int = NWORKERS) -> None:
    """
    List the objects from specified bucket or global bucket and download and verifies the
    checksum. This function supports DI/downloading of data uploaded from Seagate's S3bench.
    :param user_name:
    :param nworkers: number of workers
    :param bucket: bucket name
    :param keys: access key and secret list
    :return:
    """
    access_key = keys[0]
    secret_key = keys[1]
    s3 = _init_s3_conn(access_key, secret_key, user_name)
    test_bucket = s3.Bucket(bucket)
    for ix in range(nworkers):
        try:
            if not os.path.exists(os.path.join(DOWNLOAD_HOME, "ps", str(ix))):
                _path = os.mkdirs(os.path.join(DOWNLOAD_HOME, "ps", str(ix)))
        except (OSError, Exception) as fault:
            LOGGER.error(str(fault))
            LOGGER.error(f"Error while creating directory for process {ix}")

    workers = Workers()
    workers.start_workers(nworkers=nworkers)
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
