#!/usr/bin/env python3
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
"""DI checker test case. Eventually we want to delete this file."""

import os
import sys
import queue
import logging
import csv
import hashlib
import multiprocessing as mp
import boto3
import re
import time
import errno
from pathlib import Path
from boto3.s3.transfer import TransferConfig
from commons import worker
from libs.di import di_params
from libs.di.di_mgmt_ops import ManagementOPs
from commons.utils import config_utils
from commons import params
from commons import cortxlogging
if sys.platform != 'win32':
    import fcntl

LOGGER = logging.getLogger(__name__)
uploadObjects = []


class Uploader(object):
    """S3 Uploads class."""
    tsfrConfig = TransferConfig(multipart_threshold=1024 * 1024 * 16,
                                max_concurrency=10,
                                multipart_chunksize=1024 * 1024 * 16,
                                use_threads=True)

    @staticmethod
    def upload(user, keys):
        user_name = user.replace('_', '-')
        access_key = keys[0]
        secret_key = keys[1]
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        buckets = [user_name + '-' + timestamp + '-bucket' + str(i) for i in range(2)]

        try:
            s3 = boto3.resource('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                                endpoint_url=params.S3_ENDPOINT, verify=False)
            LOGGER.info("S3 resource created for %s", user_name)
        except Exception as e:
            LOGGER.info(
                f'could not create s3 object for user {user_name} with '
                f'access key {access_key} secret key {secret_key} exception:{e}')
            return

        for bucket in buckets:
            try:
                file1 = open(di_params.DATASET_FILES, "r")
                obj_file_paths = file1.readlines()
            except Exception as e:
                LOGGER.info(f'could not access file {di_params.DATASET_FILES} exception:{e}')
                return
            else:
                LOGGER.info(f'able to access file {di_params.DATASET_FILES}')

            try:
                s3.create_bucket(Bucket=bucket)
            except Exception as e:
                LOGGER.info(f'could not create create bucket {bucket} exception:{e}')
            else:
                LOGGER.info(f'create bucket {bucket} Done')

            for each_line in obj_file_paths:
                reg = '\(\'(.+)\''
                m = re.search(reg, each_line)
                if m:
                    each_file_path = di_params.DATAGEN_HOME + m.group(1)
                    try:
                        s3.meta.client.upload_file(str(each_file_path),
                                                   bucket,
                                                   os.path.basename(each_file_path))

                    except Exception as e:
                        LOGGER.info(f'{each_file_path} in bucket {bucket} Upload caught exception: {e}')
                    else:
                        LOGGER.info(f'{each_file_path} in bucket {bucket} Upload Done')
                        md5sum = hashlib.md5(open(each_file_path, 'rb').read()).hexdigest()

                        obj_name = os.path.basename(each_file_path)
                        row_data = []
                        uploadObjectList = []
                        row_data.append(user_name)
                        row_data.append(bucket)
                        row_data.append(obj_name)
                        row_data.append(md5sum)
                        uploadObjectList.append(row_data)
                        with open(di_params.UPLOADED_FILES, 'a', newline='') as myfile:
                            wr = csv.writer(myfile, quoting=csv.QUOTE_NONE, delimiter=',', quotechar='',
                                            escapechar='\\')
                            fcntl.flock(myfile, fcntl.LOCK_EX)
                            wr.writerows(uploadObjectList)
                            fcntl.flock(myfile, fcntl.LOCK_UN)

    @staticmethod
    def start(users):
        LOGGER.info('Starting uploads')
        try:
            os.remove(di_params.uploadFinishedFileName)
        except Exception as e:
            LOGGER.info(f'file not able to remove: {e}')
        try:
            os.remove(di_params.UPLOADED_FILES)
        except Exception as e:
            LOGGER.info(f'file not able to remove: {e}')

        users_path = os.path.join(params.LOG_DIR, params.USER_JSON)
        config_utils.create_content_json(users_path, users)

        jobs = []
        for user, udict in users.items():
            keys = [udict['accesskey'], udict['secretkey']]
            p = mp.Process(target=Uploader.upload, args=(user, keys))
            jobs.append(p)
        for p in jobs:
            p.start()
        for p in jobs:
            p.join()
        LOGGER.info('Upload Done for all users')
        with open(di_params.uploadFinishedFileName, 'w') as f:
            pass


class DIChecker(object):
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
                s3 = boto3.resource('s3', aws_access_key_id=access_key,
                                    aws_secret_access_key=secret_key,
                                    endpoint_url=params.S3_ENDPOINT, verify=False)
            except Exception as e:
                LOGGER.error(
                    f'could not create s3 object for user {user_name} with access '
                    f'key {access_key} secret key {secret_key} exception:{e}')

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
                LOGGER.error(f"Error while creating directory for user {user}")

            try:
                s3 = DIChecker.s3ObjectList[user]
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
                    LOGGER.info(
                        "download object checksum {} matches provided checksum {} for"
                        " file {}".format(csum, objcsum, objectpath))
                else:
                    LOGGER.error(
                        "download object checksum {} does not matches provided "
                        "checksum {} for file {}".format(csum, objcsum, objectpath))
                    DIChecker.failedFiles.append(kwargs)
        except Exception as fault:
            LOGGER.exception(fault)
            LOGGER.error(f'Exception occurred for item {kwargs} with exception {fault}')

    @classmethod
    def verify_data_integrity(cls, users_data):
        """
        UploadInfo File format supported is
        #user7,user7-8844buckets0,naPcn6qP47SkUPkxbP_PtJUVF1iv.json,7e2db9e2f7621db0ddfde4d294e92eca
        Downloads the file and compare checksum.
        :return:
        """
        users = dict()
        for user, udict in users_data.items():
            users.update({user.replace('_', '-'):[udict['accesskey'], udict['secretkey']]})
        ulen = len(users)
        workers = worker.Workers()
        workers.start_workers()
        cls.init_s3_conn(users)
        deletedFiles = list()
        uploadedFiles = list()
        deletedDict = dict()
        summary = dict()
        with open(di_params.UPLOADED_FILES, newline='') as f:
            reader = csv.reader(f)
            uploadedFiles = list(reader)

        if len(uploadedFiles) == 0:
            print("uploaded data not found, exiting script")
            LOGGER.info("uploaded data not found, exiting script")
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
                LOGGER.error("Skipped considering deleted file {}".format(f))

        for i in range(1, ulen + 1):
            try:
                if not os.path.exists(os.path.join(di_params.DOWNLOAD_HOME,
                                                   ManagementOPs.user_prefix + str(i))):
                    DIChecker.mkdirs(os.path.join(di_params.DOWNLOAD_HOME,
                                                  ManagementOPs.user_prefix + str(i)))
            except (OSError, Exception) as err:
                LOGGER.error(str(err))
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
            workers.wenque(workQ)
            LOGGER.info(f"Enqueued item {ix} for download and checksum compare")
            # if workQ is not None:
            #    workQ.join()
            # workQ = None
        LOGGER.info(f"processed items {ix} for data integrity check")

        summary['failed_files'] = len(cls.failedFiles) + len(cls.failedFilesServerError)
        summary['uploaded_files'] = ix
        summary['checksum_verified'] = summary['uploaded_files'] - summary['deleted_files']

        if len(cls.failedFiles) > 0:
            keys = cls.failedFiles[0].keys()
            with open(di_params.FailedFiles, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failedFiles)

        for item in cls.failedFiles:
            LOGGER.error(f'checksum mismatch for {item}')

        for item in cls.failedFilesServerError:
            LOGGER.error(f'Server Error for {item}')

        if len(cls.failedFilesServerError) > 0:
            keys = cls.failedFilesServerError[0].keys()
            with open(di_params.FailedFilesServerError, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failedFilesServerError)

        workers.end_workers()
        LOGGER.info('Workers shutdown completed successfully')
        LOGGER.info("Test run summary Uploaded files {}  "
                    "Deleted Files {} ".format(summary['uploaded_files'],
                                               summary['deleted_files']))
        LOGGER.info("Failed files were {} and Checksum verified "
                    "for Files {} ".format(summary['failed_files'],
                                           summary['checksum_verified']))
        assert len(cls.failedFiles) < 1
        assert len(cls.failedFilesServerError) < 1


if __name__ == '__main__':

    file = os.path.join(os.getcwd(),
                        params.LOG_DIR_NAME,
                        'latest',
                        'di-test.log')
    cortxlogging.set_log_handlers(LOGGER, file)
    ops = ManagementOPs()
    users = ops.create_account_users(nusers=2)
    uploader = Uploader()
    uploader.start(users)
    DIChecker.init_s3_conn(users)
    DIChecker.verify_data_integrity(users)
