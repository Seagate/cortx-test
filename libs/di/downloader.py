# -*- coding: utf-8 -*-
# !/usr/bin/python
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
"""Download S3 files in multiple threads and micro threads.
Simulates parallel downloads.
"""
import os
import logging
import csv
import queue
import hashlib
from pathlib import Path
from commons import params
from commons import worker
from commons.utils import system_utils
from libs.di import di_base
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di import uploader

LOGGER = logging.getLogger(__name__)


class DataIntegrityValidator:
    s3_objects = dict()
    failed_files = list()
    failed_files_server_error = list()

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
            cwd = params.DOWNLOAD_HOME
            basepath = os.path.join(cwd, user)
            objpth = os.path.join(cwd, user, objectpath)
            try:
                if not os.path.exists(basepath):
                    system_utils.mkdirs(basepath)
            except (OSError, Exception) as fault:
                LOGGER.error(f"Error {fault} while creating directory for user {user}")

            try:
                s3 = DataIntegrityValidator.s3_objects[user]
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
                DataIntegrityValidator.failed_files_server_error.append(kwargs)
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
                    except (OSError, Exception) as fault:
                        LOGGER.error('Fault %s occurred duing unlink. Trying rm command', fault)
                        rmLocalObject = "rm -rf " + str(filepath)
                        os.system(rmLocalObject)

                if objcsum == csum.strip():
                    LOGGER.info(
                        "download object checksum {} matches provided checksum {} for file {}".format(csum, objcsum,
                                                                                                      objectpath))
                else:
                    LOGGER.error(
                        "download object checksum {} does not matches provided checksum {} for file {}".format(csum,
                                                                                                               objcsum,
                                                                                                               objectpath))
                    DataIntegrityValidator.failed_files.append(kwargs)
                    if os.path.exists(filepath):
                        os.remove(filepath)
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
        workers.start_workers()
        cls.s3_objects = di_base.init_s3_connections(users=users)
        deletedFiles = list()
        uploadedFiles = list()
        deletedDict = dict()
        summary = dict()
        with open(params.UPLOADED_FILES, newline='') as f:
            reader = csv.reader(f)
            # uploadedFiles = list(reader)
            uploadedFiles = [el for el in list(reader) if el[0] in users.keys()]

        if len(uploadedFiles) == 0:
            print("uploaded data not found, exiting script")
            LOGGER.info("uploaded data not found, exiting script")
            workers.end_workers()
            return

        if os.path.exists(params.DELETE_OP_FILE_NAME):
            with open(params.DELETE_OP_FILE_NAME, newline='') as f:
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
                if not os.path.exists(os.path.join(params.DOWNLOAD_HOME,
                                                   ManagementOPs.user_prefix + str(i))):
                    system_utils.mkdirs(os.path.join(params.DOWNLOAD_HOME,
                                                     ManagementOPs.user_prefix + str(i)))
            except (OSError, Exception) as exe:
                LOGGER.error(f"Error {exe} while creating directory for user {i}")

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
            kwargs['accesskey'] = users.get(ent[0])['accesskey']
            kwargs['secret'] = users.get(ent[0])['secretkey']
            workQ.put(kwargs)
            workers.wenque(workQ)
            LOGGER.info(f"Enqueued item {ix} for download and checksum compare")
            # if workQ is not None:
            #    workQ.join()
            # workQ = None
        LOGGER.info(f"processed items {ix} for data integrity check")

        summary['failed_files'] = len(cls.failed_files) + len(cls.failed_files_server_error)
        summary['uploaded_files'] = ix
        summary['checksum_verified'] = summary['uploaded_files'] - summary['deleted_files']

        if len(cls.failed_files) > 0:
            keys = cls.failed_files[0].keys()
            with open(params.FAILED_FILES, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failed_files)

        for item in cls.failed_files:
            LOGGER.error(f'checksum mismatch for {item}')

        for item in cls.failed_files_server_error:
            LOGGER.error(f'Server Error for {item}')

        if len(cls.failed_files_server_error) > 0:
            keys = cls.failed_files_server_error[0].keys()
            with open(params.FAILED_FILES_SERVER_ERROR, 'w', newline='') as fp:
                wr = csv.DictWriter(fp, keys)
                wr.writerows(cls.failed_files_server_error)

        workers.end_workers()
        LOGGER.info('Workers shutdown completed successfully')
        LOGGER.info("Test run summary Uploaded files {}  "
                    "Deleted Files {} ".format(summary['uploaded_files'],
                                               summary['deleted_files']))
        LOGGER.info("Failed files were {}  and "
                    "Checksum verified for Files {} ".format(summary['failed_files'],
                                                             summary['checksum_verified']))
        return summary


if __name__ == '__main__':
    ops = ManagementOPs()
    users = ops.create_account_users(nusers=4)
    uploader = uploader.Uploader()
    uploader.start(users)
    downloader = DataIntegrityValidator()
    downloader.verify_data_integrity(users)
