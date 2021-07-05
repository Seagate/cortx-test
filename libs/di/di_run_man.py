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
import logging
import threading
from multiprocessing import Value
from libs.di import uploader
from libs.di.downloader import DataIntegrityValidator

LOGGER = logging.getLogger(__name__)


class ASyncIO:
    def __init__(self, upload_cls, users):
        self.uploader = upload_cls
        self.users = users
        self.event = threading.Event()
        self.bg_thread = None

    def start_io_async(self, users, buckets, files_count, prefs, event=None):
        event = event if event else self.event
        LOGGER.debug("File counts %s", str(files_count))
        self.bg_thread = threading.Thread(
            target=self.uploader.start, args=(users, buckets, files_count,
                                              prefs, event))
        self.bg_thread.start()

    @staticmethod
    def verify_data_integrity(users):
        return DataIntegrityValidator.verify_data_integrity(users)

    def stop_io_async(self, users, di_check=True, eventual_stop=False):
        if eventual_stop:
            LOGGER.debug("Setting stop event.")
            self.event.set()
        LOGGER.debug("Joining Run Man API")
        self.bg_thread.join()
        if di_check:
            return self.verify_data_integrity(users)


class RunDataCheckManager(ASyncIO):

    def __init__(self, users):
        self.uploader = uploader.Uploader()
        self.users = users
        self.future_value = Value('b', False)
        self.future_thread_value = threading.Event()
        super(RunDataCheckManager, self).__init__(
            upload_cls=self.uploader, users=users)

    def __check_upload(self):
        """
        read upload file uploadInfo.csv
        check users name in upload file response
        :return:
        """
        from commons import params
        import os
        import csv
        upload_file = params.UPLOADED_FILES
        if os.path.exists(upload_file):
            with open(params.UPLOADED_FILES, newline='') as f:
                reader = csv.reader(f)
                uploaded_file_lst = [el for el in list(reader) if el[0] in self.users.keys()]
            result = len(uploaded_file_lst) > 1
        else:
            result = False

        return result

    def start_io_async(self, users, buckets, files_count, prefs, event=None):
        event = event if event else self.event
        super().start_io_async(users, buckets, files_count, prefs, event)

    def stop_io_async(self, users, di_check=True, eventual_stop=False):
        response = super().stop_io_async(users, di_check, eventual_stop)
        status = response.get("failed_files") == 0

        return status, response

    def start_io(self, users, buckets, files_count, prefs, event=None, future_class=None):
        event = event if event else self.event
        future_class = future_class if future_class else self.future_value
        self.uploader.start(users, buckets, files_count, prefs, event, future_class)

        return future_class.value

    def stop_io(self, users, di_check=True, eventual_stop=False):
        response = dict()
        status = False
        if eventual_stop:
            LOGGER.debug("Setting stop event.")
            self.event.set()
        if di_check:
            response = self.verify_data_integrity(users)
            status = response["failed_files"] == 0

        return status, response

    def run_io_sequentially(self, users, buckets=None, files_count=10,
                            prefs=None, di_check=True):
        """
        Function to start IO within test sequentially(write, read, verify)
        prefs = {
            'prefix_dir': test_name
        }
        :param users: user data includes username, accessKey, secretKey,
         account id etc
        :param buckets: user buckets in
        :param files_count: objects to be uploaded per buckets
        :param prefs: dir prefix where objects will be created for uploading
        :param di_check: checks for data integrity
        :return: None
        """
        prefs_dict = prefs if isinstance(prefs, dict) else {
            "prefix_dir": prefs}
        self.start_io(
            users=users, buckets=buckets, files_count=files_count,
            prefs=prefs_dict)
        self.stop_io(users, di_check=di_check)
