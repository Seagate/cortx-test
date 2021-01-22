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

#!/usr/bin/env python3
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
from libs.di.di_lib import init_loghandler
from libs.di import di_params
from libs.di.di_mgmt_ops import ManagementOPs

CM_CFG = di_lib.read_yaml("config/common_config.yaml")
S3_CFG = di_lib.read_yaml("config/s3/s3_config.yaml")


SCRIPT_HOME = os.getcwd()
logger = logging.getLogger(__name__)
uploadObjects = []
users = {"user1":["AKIAvVRBu_qhRc2eOpMJwXOBjQ","cT1tEIKo8SztEBpqHF5OroZkqda7kpph7DFQfZAz"],
         "user2":["AKIAwxH4rqnwRqmXoX5HzyV8xA","C5dBsRcL73wLyLEZr858nymh2h70abFvxINNSkRa"],
         "user3":["AKIAql9gSmpcQnGyuHbiziTzng","Ow6mYLCji2nBMCrMZDzG7/u2tu9WX0FjFI0ihOlG"],
         "user4":["AKIA3iswZrw0R7mKtHJZizImKg","TcvKJRfJnYS8H4f53B2g0urn/8+7uFG44vStPiwt"],
         "user5":["AKIAZxC27C5kSRKomFywnCUE_A","OLkz+6+eyV1IsXA2HBx6wtmRdihW0o/wktoCLCZf"],
         "user6":["AKIA1s420Uw3RnWuRH_jU5YL9g","JUq17VoBHInxd2Oftec592v/nVuNXlT185KsPc/N"],
         "user7":["AKIAvzZoU96eQPucwPCYvD7kWw","D7A+mEI/hu+0EAe02dZYbPZFD9BcmBPvdB5yaRRy"],
         "user8":["AKIAdLhZ3gGSSCW3Ul1ECrjq2g","OKGEDDWS4D+ohrOf0w8nYcgCXGZ0GE2WTVL6zAOC"],
         "user9":["AKIA5Hx6gvLNTCuOAc7k6MYQ0w","+xx/Y6IJWDQEGLzclUIwNVeSa3DfX09jGbbhi+M+"],
         "user10":["AKIARmsEWm0NTvi2NJ5HD4sIzw","TlIjEvDS2Q4LoEXbESqhyJ/CdC531f5Za4Bbwcmy"]}


class Uploader(object):
    tsfrConfig = TransferConfig(multipart_threshold=1024 * 1024 * 16,
                                max_concurrency=10,
                                multipart_chunksize=1024 * 1024 * 16,
                                use_threads=True)
    @staticmethod
    def upload(user, keys, nbuckets=4):

        user_name = user
        access_key = keys[0]
        secret_key = keys[1]
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        buckets = [user_name + '-' + timestamp + '-bucket' + str(i) for i in range(nbuckets)]
        s3connections = list()
        for ix in range(di_lib.NWORKERS):
            try:
                s3 = boto3.resource('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                    endpoint_url="https://s3.seagate.com")
            except Exception as e:
                logger.info(f'could not create s3 object for user {user_name} with access key {access_key} secret key {secret_key} exception:{e}')
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

            try:

                s3.create_bucket(Bucket=bucket)
            except Exception as e:
                logger.info(f'could not create create bucket {bucket} exception:{e}')
            else:
                logger.info(f'create bucket {bucket} Done')

            workers = Workers()
            workers.wStartWorkers()

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
    def start():
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


class DIChecker(object):

    s3ObjectList = dict()
    failedFiles = list()
    failedFilesServerError = list()

    @classmethod
    def init_s3_conn(cls):
        for user, keys in users.items():
            user_name = user
            access_key = keys[0]
            secret_key = keys[1]
            try:
                s3 = boto3.resource('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                    endpoint_url="https://s3.seagate.com")
            except Exception as e:
                logger.error(
                    f'could not create s3 object for user {user_name} with access key {access_key} secret key {secret_key} exception:{e}')

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
            cwd = di_params.DOWNLOAD_HOME
            basepath = os.path.join(cwd, user)
            objpth = os.path.join(cwd, user, objectpath)
            try:
                if not os.path.exists(basepath):
                    DIChecker.mkdirs(basepath)
            except Exception as e:
                logger.error(f"Error while creating directory for user {user}")

            try:
                s3 = DIChecker.s3ObjectList[user]
            except Exception as fault:
                print(fault)
                logger.error(f'No S3 Connection for user {kwargs} in S3 sessions list {fault}')
                logger.error(f"Won't be able to download object {kwargs} without connection")
                return
            try:
                s3.meta.client.download_file(bucket, objectpath, objpth)
                logger.info(f'downloaded object : {kwargs}')
            except Exception as e:
                print(e)
                logger.error(f'Final object download failed for {kwargs} with exception {e}')
                DIChecker.failedFilesServerError.append(kwargs)
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
                    logger.info("download object checksum {} matches provided checksum {} for file {}".format(csum, objcsum, objectpath))
                else:
                    logger.error("download object checksum {} does not matches provided checksum {} for file {}".format(csum, objcsum, objectpath))
                    DIChecker.failedFiles.append(kwargs)
        except Exception as fault:
            logger.exception(fault)
            logger.error(f'Exception occurred for item {kwargs} with exception {fault}')


    @classmethod
    def verify_data_integrity(cls):
        """
        UploadInfo File format supported is
        #user7,user7-8844buckets0,naPcn6qP47SkUPkxbP_PtJUVF1iv.json,7e2db9e2f7621db0ddfde4d294e92eca
        Downloads the file and compare checksum.
        :return:
        """
        workers = di_lib.Workers()
        workers.wStartWorkers()
        cls.init_s3_conn()
        deletedFiles = list()
        uploadedFiles = list()
        deletedDict = dict()
        summary = dict()
        with open(di_params.UPLOADED_FILES, newline='') as f:
            reader = csv.reader(f)
            uploadedFiles = list(reader)

        if len(uploadedFiles) == 0:
            print("uploaded data not found, exiting script")
            logger.info("uploaded data not found, exiting script")
            exit(1)

        if os.path.exists(di_params.deleteOpFileName):
            with open(di_params.deleteOpFileName, newline='') as f:
                reader = csv.reader(f)
                deletedFiles = list(reader)
        summary['deleted_files'] = len(deletedFiles)

        for f in deletedFiles:
            if len(f) == 4:
                deletedDict[(f[0], f[1], f[2])] = f[3]
            else:
                logger.error("Skipped considering deleted file {}".format(f))

        for i in range(1, di_params.NUSERS + 1):
            try:
                if not os.path.exists(os.path.join(di_params.DOWNLOAD_HOME, ManagementOPs.user_prefix + str(i))):
                    DIChecker.mkdirs(os.path.join(di_params.DOWNLOAD_HOME, ManagementOPs.user_prefix + str(i)))
            except Exception as e:
                logger.error(f"Error while creating directory for user {i}")

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
            logger.info(f"Enqueued item {ix} for download and checksum compare")
            #if workQ is not None:
            #    workQ.join()
            #workQ = None
        logger.info(f"processed items {ix} for data integrity check")

        summary['failed_files'] = len(cls.failedFiles) + len(cls.failedFilesServerError)
        summary['uploaded_files'] = ix
        summary['checksum_verified'] =  summary['uploaded_files'] - summary['deleted_files']

        if len(cls.failedFiles) > 0:
            keys = cls.failedFiles[0].keys()
            with open(di_params.FailedFiles, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failedFiles)

        for item in cls.failedFiles:
            logger.error(f'checksum mismatch for {item}')

        for item in cls.failedFilesServerError:
            logger.error(f'Server Error for {item}')

        if len(cls.failedFilesServerError) > 0:
            keys = cls.failedFilesServerError[0].keys()
            with open(di_params.FailedFilesServerError, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failedFilesServerError)

        workers.wEndWorkers()
        logger.info('Workers shutdown completed successfully')
        logger.info("Test run summary Uploaded files {}  Deleted Files {} ".format(summary['uploaded_files'], summary['deleted_files']))
        logger.info("Failed files were {}  and Checksum verified for Files {} ".format(summary['failed_files'], summary['checksum_verified']))


if __name__ == '__main__':

    uploader = Uploader()
    uploader.start()
    downloader = DIChecker()
    downloader.verify_data_integrity()