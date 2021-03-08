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
#

"""S3 package initializer."""

from commons.helpers.s3_helper import S3Helper
from commons.utils import config_utils
from commons.params import S3_CONFIG, COMMON_CONFIG
from config import CMN_CFG
S3H_OBJ = S3Helper.get_instance()

S3_CFG = config_utils.read_yaml(S3_CONFIG)[1]  # Read s3 common config.
CM_CFG = CMN_CFG #config_utils.read_yaml(COMMON_CONFIG)[1]  # Read common config.
# S3 default access_key, secret key.
ACCESS_KEY, SECRET_KEY = S3H_OBJ.get_local_keys()
LDAP_USERNAME = CMN_CFG["ldap"]["username"]  # Ldap username.
LDAP_PASSWD = CMN_CFG["ldap"]["password"]  # Ldap password.
