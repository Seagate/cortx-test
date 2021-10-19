# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""S3 configs are initialized here."""


from commons import configmanager
from commons.params import S3_CONFIG
from commons.params import DEL_CFG_PATH
from commons.params import S3_MPART_CFG_PATH
from commons.params import S3_BLACK_BOX_CONFIG_PATH

S3_CFG = configmanager.get_config_wrapper(fpath=S3_CONFIG)
DEL_CFG = configmanager.get_config_wrapper(fpath=DEL_CFG_PATH)
MPART_CFG = configmanager.get_config_wrapper(fpath=S3_MPART_CFG_PATH)
S3_BLKBOX_CFG = configmanager.get_config_wrapper(fpath=S3_BLACK_BOX_CONFIG_PATH)
