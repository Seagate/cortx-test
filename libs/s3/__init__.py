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
from config import CMN_CFG
from config.s3 import S3_CFG

S3H_OBJ = S3Helper.get_instance(CMN_CFG, S3_CFG)
# S3 default access_key, secret key.
ACCESS_KEY, SECRET_KEY = S3H_OBJ.get_local_keys()
ldap = CMN_CFG.get("ldap", None)
LDAP_USERNAME = ldap["username"] if ldap else None  # Ldap username.
LDAP_PASSWD = ldap["password"] if ldap else None  # Ldap password.
