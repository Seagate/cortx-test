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
from libs.di import uploader
from libs.di.downloader import DataIntegrityValidator

LOGGER = logging.getLogger(__name__)


class ASyncIO:
    def __init__(self, upload_cls, users):
        self.uploader = upload_cls
        self.users = users
        self.bg_thread = None

    def start_io_async(self, users, buckets, files_count, prefs):
        self.bg_thread = threading.Thread(
            target=self.uploader.start, args=(users, buckets, files_count, prefs))
        self.bg_thread.start()

    @staticmethod
    def verify_data_integrity(users):
        return DataIntegrityValidator.verify_data_integrity(users)

    def stop_io_async(self, users, di_check=True, stop_gracefully=False):
        if stop_gracefully:
            # in case of failure test failure stop further IO and proceed with verification
            # will implement stop later
            self.uploader.set_eventual_stop(stop_gracefully)
        LOGGER.debug("Joining Run Man API")
        self.bg_thread.join()
        if di_check:
            self.verify_data_integrity(users)


class RunDataCheckManager(ASyncIO):

    def __init__(self, users):
        self.uploader = uploader.Uploader()
        self.users = users
        super(RunDataCheckManager, self).__init__(upload_cls=self.uploader, users=users)

    def start_io(self, users, buckets, files_count, prefs):
        self.uploader.start(users, buckets, files_count, prefs)

    def stop_io(self, users, di_check=True, eventual_stop=False):
        self.uploader.stop(eventual_stop)
        if di_check:
            self.verify_data_integrity(users)
