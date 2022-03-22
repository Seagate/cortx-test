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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""Unittest s3 init file."""

import os
import logging
from src.commons.logger import StreamToLogger


logger = logging.getLogger()
logger.setLevel(logging.INFO)
dir_path = os.path.join(os.path.join(os.getcwd(), "log", "unittest"))
if not os.path.exists(dir_path):
    os.makedirs(dir_path, exist_ok=True)
name = os.path.splitext(os.path.basename(__file__))[0]
name = os.path.join(dir_path, f"{name}_console.log")
StreamToLogger(name, logger)
