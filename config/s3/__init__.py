# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""S3 configs are initialized here."""

from commons import configmanager
from commons.params import S3_OBJ_TEST_CONFIG
from commons.params import S3_BKT_TEST_CONFIG
from commons.params import S3CMD_TEST_CONFIG
from commons.params import S3_BLACK_BOX_CONFIG_PATH
from commons.params import S3_USER_ACC_MGMT_CONFIG_PATH
from commons.params import S3_TEMP_CRED_CONFIG_PATH
from commons.params import S3_MPART_CFG_PATH
from commons.params import DEL_CFG_PATH
from commons.params import IAM_POLICY_CFG_PATH
from commons.params import S3_LDAP_TEST_CONFIG
from config import S3_CFG as s3_config

S3_CFG = s3_config
DEL_CFG = configmanager.get_config_wrapper(fpath=DEL_CFG_PATH)
S3_OBJ_TST = configmanager.get_config_wrapper(fpath=S3_OBJ_TEST_CONFIG)
S3_BKT_TST = configmanager.get_config_wrapper(fpath=S3_BKT_TEST_CONFIG)
S3CMD_CNF = configmanager.get_config_wrapper(fpath=S3CMD_TEST_CONFIG)
S3_USER_ACC_MGMT_CONFIG = configmanager.get_config_wrapper(fpath=S3_USER_ACC_MGMT_CONFIG_PATH)
S3_BLKBOX_CFG = configmanager.get_config_wrapper(fpath=S3_BLACK_BOX_CONFIG_PATH)
S3_TMP_CRED_CFG = configmanager.get_config_wrapper(fpath=S3_TEMP_CRED_CONFIG_PATH)
MPART_CFG = configmanager.get_config_wrapper(fpath=S3_MPART_CFG_PATH)
S3_LDAP_TST_CFG = configmanager.get_config_wrapper(fpath=S3_LDAP_TEST_CONFIG)
IAM_POLICY_CFG = configmanager.get_config_wrapper(fpath=IAM_POLICY_CFG_PATH)
