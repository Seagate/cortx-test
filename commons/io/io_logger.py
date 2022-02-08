#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Function for comparison."""
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
# Logger for CorIO tool.

import os
import gzip
import shutil
import datetime
import logging
from os import path
from logging import handlers


class StreamToLogger:
    """logger class for corio driver."""

    def __init__(self, file_path, logger):
        """"
        Initialize root logger for CorIO.

        :param file_path: File path of the logger.
        :param logger: logger object from logging.getLogger(__name__).
        """
        self.file_path = file_path
        self.logger = logger
        self.formatter = '[%(asctime)s] [%(threadName)-6s] [%(levelname)-6s] ' \
                         '[%(filename)s: %(lineno)d]: %(message)s'
        self.make_logdir()
        self.set_stream_logger()
        self.set_filehandler_logger()

    def make_logdir(self) -> None:
        """Create log directory if not exists."""
        head, _ = path.split(self.file_path)
        if not os.path.exists(head):
            os.makedirs(head, exist_ok=True)

    def set_stream_logger(self):
        """Add a stream handler for the logging module. This logs all messages to ``stdout``."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(self.formatter)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def set_filehandler_logger(self, maxbyte=1073741824, backupcount=5):
        """
        Add a file handler for the logging module. this logs all messages to ``file_name``.

        :param maxbyte: Rollover occurs whenever the current log file is nearly maxBytes in
        length.
        :param backupcount: count of the max rotation/rollover of logs.
        """
        handler = CorIORotatingFileHandler(self.file_path, maxbyte=maxbyte, backupcount=backupcount)
        formatter = logging.Formatter(self.formatter)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)


class CorIORotatingFileHandler(handlers.RotatingFileHandler):
    """Handler overriding the existing RotatingFileHandler for switching corio log files."""

    def __init__(self, filename, maxbyte, backupcount):
        """
        Initialization for cortx rotating file handler.

        :param filename: Filename of the log.
        :param maxbyte: Rollover occurs whenever the current log file is nearly maxBytes in
        length.
        :param backupcount: count of the max rotation/rollover of logs.
        """
        super().__init__(filename=filename, maxBytes=maxbyte, backupCount=backupcount)

    def rotation_filename(self, default_name):
        """
        Method to form log file name for rotation internally called by rotation_filename method.

        :param default_name: name of the base file
        :return: rotated log file name e.g., io_driver-YYYY-MM-DD-1.gz
        """
        return "{}-{}.gz".format(default_name, str(datetime.date.today()))

    def rotate(self, source, dest):
        """
        Method to compress and rotate the current log when size limit is reached.

        :param source: current log file path.
        :param dest: destination path for rotated file.
        """
        with open(source, "rb") as sf_obj:
            with gzip.open(dest, "wb", 9) as df_obj:
                shutil.copyfileobj(sf_obj, df_obj)
        os.remove(source)
