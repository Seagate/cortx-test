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


import os
import logging
from commons.io.io_logger import StreamToLogger


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
dir_path = os.path.join(os.path.join(os.getcwd(), "log", "unittest"))
if not os.path.exists(dir_path):
    os.makedirs(dir_path, exist_ok=True)
name = os.path.splitext(os.path.basename(__file__))[0]
name = os.path.join(dir_path, f"{name}_console.log")
StreamToLogger(name, logger)
