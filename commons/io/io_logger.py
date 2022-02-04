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

import logging
from logging.handlers import RotatingFileHandler


class StreamToLogger(object):
    def __init__(self, file_name, log_level=logging.DEBUG):
        self.file_name = file_name
        self.log_level = log_level
        self.formatter = '[%(asctime)s] [%(threadName)-6s] [%(levelname)-6s] ' \
                         '[%(filename)s: %(lineno)d]: %(message)s'
        self.set_stream_logger()
        self.set_filehandler_logger()

    def set_stream_logger(self):
        """
        Add a stream handler for the logging module. default, this logs all messages to ``stdout``.
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(self.log_level)
        handler = logging.StreamHandler()
        handler.setLevel(self.log_level)
        formatter = logging.Formatter(self.formatter)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def set_filehandler_logger(self):
        """
        Add a file handler for the logging module. this logs all messages to ``file_name``.
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(self.log_level)
        handler = RotatingFileHandler(self.file_name, maxBytes=5000000, backupCount=5)
        handler.setLevel(self.log_level)
        formatter = logging.Formatter(self.formatter)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
