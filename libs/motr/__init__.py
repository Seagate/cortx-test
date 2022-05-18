#!/usr/bin/python
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
#

"""Motr package initializer."""

import os
import tempfile
from commons.utils import config_utils

CURR_LIB_VERSION=b"1.11.2"

# dd tools commands.
# Parameter in order: if:Source file path, of:
# Destination file path, bs(k, M, G) * count(number): Total size.
CMD_DD_CREATE_FILE = "dd if=/dev/urandom of=%s bs=%s count=%s"
CMD_DD_CREATE_128M_FILE = "dd if=/dev/urandom of=/tmp/128M bs=1M count=128"

# path of directories
SANDBOX_DIR_NAME = "sandbox"
SANDBOX_DIR_PATH = f"tmp/{SANDBOX_DIR_NAME}"
TEMP_PATH = tempfile.gettempdir()
WORKLOAD_FILES_DIR = "config/motr"
TEMP_128M_FILE_PATH = os.path.join(tempfile.gettempdir(), '128M')

#Read test workload
WORKLOAD_CFG = config_utils.read_yaml("config/motr/test_workload.yaml")

# Motr configs
FILE_BLOCK_COUNT = [1,2]
