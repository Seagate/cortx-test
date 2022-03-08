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

"""S3 package initializer."""

from commons import constants as const
from commons.helpers.s3_helper import S3Helper
from config import CMN_CFG
from config.s3 import S3_CFG

S3H_OBJ = S3Helper.get_instance(CMN_CFG, S3_CFG)
# S3 default access_key, secret key.
ACCESS_KEY, SECRET_KEY = S3H_OBJ.get_local_keys()
ldap = CMN_CFG.get("ldap", None)
LDAP_USERNAME = ldap["username"] if ldap else None  # Ldap username.
LDAP_PASSWD = ldap["password"] if ldap else None  # Ldap password.
