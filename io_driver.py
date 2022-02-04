#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""IO Driver module."""

import os
import logging
import argparse
from commons.io.io_logger import StreamToLogger

logger = logging.getLogger(__name__)


def str_to_bool(string):
    """To convert a string value to bool."""
    if isinstance(string, bool):
        return string
    if string.lower() in ('yes', 'true', 'y', '1'):
        return True
    elif string.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def initialize_loghandler(level=logging.DEBUG):
    """Initialize io driver runner logging with stream and file handlers."""
    logger.setLevel(level)
    dir_path = os.path.join(os.path.join(os.getcwd(), "log", "latest"))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    name = os.path.splitext(os.path.basename(__file__))[0]
    name = os.path.join(dir_path, f"{name}.log")
    StreamToLogger(name, logger)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_level", type=int, default=10,
                        help="log level value as defined below: " +
                             "CRITICAL = 50 " +
                             "ERROR = 40 " +
                             "WARNING = 30 " +
                             "INFO = 20 " +
                             "DEBUG = 10"
                        )
    parser.add_argument("--use_ssl", type=str_to_bool, default=True,
                        help="Use HTTPS/SSL connection for S3 endpoint.")

    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()
    level = logging.getLevelName(opts.log_level)
    initialize_loghandler(level=level)
