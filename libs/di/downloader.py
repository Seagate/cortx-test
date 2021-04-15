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
"""Download S3 files in multiple threads and micro threads.
Simulates parallel downloads.
"""
import os
import logging
import boto3
import csv
import errno
import queue
import hashlib
from pathlib import Path
from commons import params
from commons import worker

LOGGER = logging.getLogger(__name__)


class DataIntegrityValidator:

    s3ObjectList = dict()
    failedFiles = list()
    failedFilesServerError = list()

    @classmethod
    def init_s3_conn(cls, users):
        for user, keys in users.items():
            user_name = user
            access_key = keys[0]
            secret_key = keys[1]
            try:
                s3 = boto3.resource('s3',
                                    aws_access_key_id=access_key,
                                    aws_secret_access_key=secret_key,
                                    endpoint_url="https://s3.seagate.com")
            except Exception as e:
                LOGGER.error(
                    f'could not create s3 object for user {user_name} with '
                    f'access key {access_key} secret key {secret_key} exception:{e}')

            cls.s3ObjectList[user_name] = s3

    @staticmethod
    def mkdirs(pth):
        try:
            os.makedirs(pth)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    @staticmethod
    def download_and_compare_chksum(kwargs):
        """ Download file with s3cmd "s3://bucket/ObjectPath" test_output_file
            compare downloaded file's md5sum with prior stored
        """
        try:
            user = kwargs.get('user')
            objectpath = kwargs.get('objectpath')
            bucket = kwargs.get('bucket')
            objcsum = kwargs.get('objcsum')
            accesskey = kwargs.get('accesskey')
            secret = kwargs.get('secret')
            cwd = params.DOWNLOAD_HOME
            basepath = os.path.join(cwd, user)
            objpth = os.path.join(cwd, user, objectpath)
            try:
                if not os.path.exists(basepath):
                    DataIntegrityValidator.mkdirs(basepath)
            except Exception as e:
                LOGGER.error(f"Error while creating directory for user {user}")

            try:
                s3 = DataIntegrityValidator.s3ObjectList[user]
            except Exception as fault:
                print(fault)
                LOGGER.error(f'No S3 Connection for user {kwargs} in S3 sessions list {fault}')
                LOGGER.error(f"Won't be able to download object {kwargs} without connection")
                return
            try:
                s3.meta.client.download_file(bucket, objectpath, objpth)
                LOGGER.info(f'downloaded object : {kwargs}')
            except Exception as e:
                print(e)
                LOGGER.error(f'Final object download failed for {kwargs} with exception {e}')
                DataIntegrityValidator.failedFilesServerError.append(kwargs)
            else:
                print("Downloaded file '{}' from '{}'".format(objectpath, bucket))
                filepath = objpth
                sz = Path(filepath).stat().st_size
                read_sz = 8192
                csum = None
                with open(filepath, 'rb') as fp:
                    file_hash = hashlib.md5()
                    if sz < read_sz:
                        buf = fp.read(sz)
                    else:
                        buf = fp.read(read_sz)
                    while buf:
                        file_hash.update(buf)
                        buf = fp.read(read_sz)
                    csum = file_hash.hexdigest()
                    try:
                        os.unlink(filepath)
                    except Exception as f:
                        rmLocalObject = "rm -rf " + str(filepath)
                        os.system(rmLocalObject)

                if objcsum == csum.strip():
                    LOGGER.info("download object checksum {} matches provided checksum {} for file {}".format(csum, objcsum, objectpath))
                else:
                    LOGGER.error("download object checksum {} does not matches provided checksum {} for file {}".format(csum, objcsum, objectpath))
                    DataIntegrityValidator.failedFiles.append(kwargs)
        except Exception as fault:
            LOGGER.exception(fault)
            LOGGER.error(f'Exception occurred for item {kwargs} with exception {fault}')


    @classmethod
    def verify_data_integrity(cls, users):
        """
        UploadInfo File format supported is
        #user7,user7-8844buckets0,naPcn6qP47SkUPkxbP_PtJUVF1iv.json,7e2db9e2f7621db0ddfde4d294e92eca
        Downloads the file and compare checksum.
        :return:
        """
        workers = worker.Workers()
        workers.wStartWorkers()
        cls.init_s3_conn()
        deletedFiles = list()
        uploadedFiles = list()
        deletedDict = dict()
        summary = dict()
        with open(params.UPLOADED_FILES, newline='') as f:
            reader = csv.reader(f)
            uploadedFiles = list(reader)

        if len(uploadedFiles) == 0:
            print("uploaded data not found, exiting script")
            LOGGER.info("uploaded data not found, exiting script")
            exit(1)

        if os.path.exists(params.deleteOpFileName):
            with open(params.deleteOpFileName, newline='') as f:
                reader = csv.reader(f)
                deletedFiles = list(reader)
        summary['deleted_files'] = len(deletedFiles)

        for f in deletedFiles:
            if len(f) == 4:
                deletedDict[(f[0], f[1], f[2])] = f[3]
            else:
                LOGGER.error("Skipped considering deleted file {}".format(f))

        for i in range(1, params.NUSERS + 1):
            try:
                if not os.path.exists(os.path.join(params.DOWNLOAD_HOME, ManagementOPs.user_prefix + str(i))):
                    cls.mkdirs(os.path.join(params.DOWNLOAD_HOME, ManagementOPs.user_prefix + str(i)))
            except Exception as e:
                LOGGER.error(f"Error while creating directory for user {i}")

        for ix, ent in enumerate(uploadedFiles, 1):
            if (ent[0], ent[1], ent[2]) in deletedDict:
                continue
            workQ = queue.Queue()
            workQ.func = cls.download_and_compare_chksum
            kwargs = dict()
            kwargs['user'] = ent[0]
            kwargs['objectpath'] = ent[2]
            kwargs['bucket'] = ent[1]
            kwargs['objcsum'] = ent[3]
            kwargs['accesskey'] = users.get(ent[0])[0]
            kwargs['secret'] = users.get(ent[0])[1]
            workQ.put(kwargs)
            workers.wEnque(workQ)
            LOGGER.info(f"Enqueued item {ix} for download and checksum compare")
            #if workQ is not None:
            #    workQ.join()
            #workQ = None
        LOGGER.info(f"processed items {ix} for data integrity check")

        summary['failed_files'] = len(cls.failedFiles) + len(cls.failedFilesServerError)
        summary['uploaded_files'] = ix
        summary['checksum_verified'] =  summary['uploaded_files'] - summary['deleted_files']

        if len(cls.failedFiles) > 0:
            keys = cls.failedFiles[0].keys()
            with open(params.FailedFiles, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failedFiles)

        for item in cls.failedFiles:
            LOGGER.error(f'checksum mismatch for {item}')

        for item in cls.failedFilesServerError:
            LOGGER.error(f'Server Error for {item}')

        if len(cls.failedFilesServerError) > 0:
            keys = cls.failedFilesServerError[0].keys()
            with open(params.FailedFilesServerError, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failedFilesServerError)

        workers.wEndWorkers()
        LOGGER.info('Workers shutdown completed successfully')
        LOGGER.info("Test run summary Uploaded files {}  Deleted Files {} ".format(summary['uploaded_files'], summary['deleted_files']))
        LOGGER.info("Failed files were {}  and Checksum verified for Files {} ".format(summary['failed_files'], summary['checksum_verified']))


def FileSHA1(blobfile, blobsize, readcallback):
    cksum = Hash(hint_algo='sha1')

    offset = 0
    cookie = 0
    buflist = ['hello', ]
    while buflist:
        buflist, cookie = readcallback(blobfile, offset, blobsize, cookie)
        for buf in buflist:
            offset += len(buf)
            cksum.update(buf)

    return cksum.digest()


if __name__ == '__main__':
    uploader = Uploader()
    uploader.start()
    downloader = DIChecker()
    downloader.verify_data_integrity()