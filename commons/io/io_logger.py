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

import os
import gzip
import shutil
import datetime
import logging
from os import path
from logging import handlers


class StreamToLogger(object):
    def __init__(self, file_path, logger):
        self.file_path = file_path
        self.logger = logger
        self.formatter = '[%(asctime)s] [%(threadName)-6s] [%(levelname)-6s] ' \
                         '[%(filename)s: %(lineno)d]: %(message)s'
        self.make_logdir()
        self.set_stream_logger()
        self.set_filehandler_logger()

    def make_logdir(self) -> None:
        """Create directory if not exists."""
        head, tail = path.split(self.file_path)
        if not os.path.exists(head):
            os.makedirs(head, exist_ok=True)

    def set_stream_logger(self):
        """
        Add a stream handler for the logging module. default, this logs all messages to ``stdout``.
        """
        handler = logging.StreamHandler()
        formatter = logging.Formatter(self.formatter)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def set_filehandler_logger(self):
        """Add a file handler for the logging module. this logs all messages to ``file_name``."""
        handler = CorIORotatingFileHandler(self.file_path, maxbyte=1073741824, backupcount=5)
        formatter = logging.Formatter(self.formatter)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)


class CorIORotatingFileHandler(handlers.RotatingFileHandler):
    """
    Handler overriding the existing RotatingFileHandler for switching corio log files
    when the current file reaches a certain size default is 1GB.
    """

    def __init__(self, filename, maxbyte, backupcount):
        """
        Initialization for cortx rotating file handler
        """
        super().__init__(filename=filename, maxBytes=maxbyte, backupCount=backupcount)

    def rotation_filename(self, name):
        """
        Method to form log file name for rotation internally called by rotation_filename() method
        :param name: name of the base file
        :return: cortx rotated log file name e.g., io_driver-YYYY-MM-DD-1.gz
        """
        return "{}-{}-{}.gz".format(name, str(datetime.date.today()), name.split('.')[-1])

    def rotate(self, source, dest):
        """
        Method to compress and rotate the current log when size limit is reached.
        :param source: current log file path
        :param dest: destination path for rotated file
        """
        with open(source, "rb") as sf:
            with gzip.open(dest, "wb", 9) as df:
                shutil.copyfileobj(sf, df)
        os.remove(source)
