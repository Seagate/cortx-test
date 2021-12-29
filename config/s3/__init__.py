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
from commons.params import S3_VER_CFG_PATH
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
S3_VER_CFG = configmanager.get_config_wrapper(fpath=S3_VER_CFG_PATH)
