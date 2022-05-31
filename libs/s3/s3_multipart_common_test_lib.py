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
"""
Contains common functions for S3 Multipart tests.

Checks/validation logic that is common to the test methods across the versioning related test
modules should be extracted out and added to this module to reduce code duplication.

Functions added here can accept cortx-test test libraries as parameters and can contain
assertions as well, with the main aim being to have leaner and cleaner code in the test modules.
"""

import os
import logging

from commons.utils.system_utils import create_file
from commons.utils import s3_utils
from libs.s3.s3_common_test_lib import S3BackgroundIO

LOGGER = logging.getLogger(__name__)


def start_ios_get_precalc_parts(mp_config: dict, obj_path: str, **kwargs):
    """
    Creates a file, start IOs, initiate mpu and get the precalculated parts for uploading
    to multipart upload
    :param mp_config: configuration dict for multipart upload
    :param obj_path: path to object file
    """
    log_prefix = kwargs.get("log_prefix", None)
    duration = kwargs.get("duration", None)
    s3_test_obj = kwargs.get("s3_test_lib_obj", "s3_test_lib_obj")
    if os.path.exists(obj_path):
        os.remove(obj_path)
    create_file(obj_path, mp_config["file_size"])
    s3_background_io = S3BackgroundIO(s3_test_lib_obj=s3_test_obj)
    LOGGER.info("start s3 IO's")
    s3_background_io.start(log_prefix, duration)
    precalc_parts = s3_utils.get_precalculated_parts(obj_path, mp_config["part_sizes"],
                                                     chunk_size=mp_config["chunk_size"])
    keys = list(precalc_parts.keys())
    return precalc_parts, keys, s3_background_io
