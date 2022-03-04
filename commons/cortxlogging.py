# !/usr/bin/python
# -*- coding: utf-8 -*-
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
"""
Extended log rotation class for cortx log files
"""
import os
import inspect
import gzip
import shutil
import datetime
import logging
from logging import handlers
from commons import params

LOG_FILE = 'cortx-test.log'


def init_loghandler(log, level=logging.DEBUG) -> None:
    """Initialize logging with stream and file handlers."""
    log.setLevel(level)
    make_log_dir(params.LOG_DIR_NAME)
    fh = logging.FileHandler(os.path.join(os.getcwd(),
                                          params.LOG_DIR_NAME,
                                          'latest',
                                          LOG_FILE),
                             mode='w')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)


def set_log_handlers(log, name, mode='w', level=logging.DEBUG):
    """Set stream and file handlers."""
    fh = logging.FileHandler(name, mode=mode)
    fh.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)


def make_log_dir(dirpath) -> None:
    """Create dir if not exists.Don't throw error for existence."""
    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def get_frame():
    """Get current frame and name."""
    return inspect.stack()[1][3]


class CortxRotatingFileHandler(handlers.RotatingFileHandler):
    """
    Handler overriding the existing RotatingFileHandler for switching cortx-test log files
    when the current file reaches a certain size.
    """

    def __init__(self, filename="cortx-test.log", maxBytes=10485760, backupCount=5):
        """
        Initialization for cortx rotating file handler
        """
        self.baseFilename = filename
        super().__init__(filename=self.baseFilename, maxBytes=maxBytes, backupCount=backupCount)
        self.namer = self.log_namer
        self.rotator = self.log_rotator

    def log_namer(self, name):
        """
        Method to form log file name for rotation internally called by rotation_filename() method
        :param name: name of the base file
        :return: cortx rotated log file name e.g., cortx-test.log-YYYY-MM-DD-1.gz
        """
        return "{}-{}-{}.gz".format(self.baseFilename, str(datetime.date.today()), name.split('.')[-1])

    def log_rotator(self, source, dest):
        """
        Method to compress and rotate the current log when size limit is reached.
        :param source: current log file path
        :param dest: destination path for rotated file
        """
        with open(source, "rb") as sf:
            with gzip.open(dest, "wb", 9) as df:
                shutil.copyfileobj(sf, df)
        os.remove(source)
