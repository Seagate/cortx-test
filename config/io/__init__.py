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
# -*- coding: utf-8 -*-
# !/usr/bin/python
"""IO Configs are initialized here."""


import yaml

from commons.params import S3_IO_CFG_PATH
from config import CMN_CFG


S3_IO_CFG = dict()
with open(S3_IO_CFG_PATH) as fr_obj:
    data = yaml.safe_load(fr_obj)
    S3_IO_CFG.update(data)
CMN_CFG.update(S3_IO_CFG)
