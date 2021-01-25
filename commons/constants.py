# !/usr/bin/python
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

"""All common constants from cortx-test."""

from commons import const
from commons.utils import config_utils

CMN_CFG = config_utils.read_yaml("config/common_config.yaml")[1]

#: NWORKERS specifies number of worker (python) threads  in a worker pool.
NWORKERS = 32

#: NGREENLETS specifies number of greenlets in a thread. These greenlets will run in parallel.
NGREENLETS = 32

""" S3 constants """
const.S3_CONFIG = "/opt/seagate/cortx/s3/conf/s3config.yaml"
const.CA_CERT_PATH = "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
const.REMOTE_DEFAULT_DIR = "/var/motr"
const.CFG_FILES = ["/etc/haproxy/haproxy.cfg",
                   "/opt/seagate/cortx/s3/conf/s3config.yaml",
                   "/opt/seagate/cortx/auth/resources/authserver.properties",
                   "/opt/seagate/cortx/s3/s3backgrounddelete/config.yaml",
                   "/opt/seagate/cortx/s3/s3startsystem.sh"]
const.AUTHSERVER_FILE = "/opt/seagate/cortx/auth/resources/authserver.properties"
const.SCRIPT_PATH = "cd /opt/seagate/cortx/auth/scripts"
const.LDAP_CREDS = {
    "ldap_username": CMN_CFG["ldap_username"],
    "ldap_passwd": CMN_CFG["ldap_passwd"]
}


class Rest():
    # REST LIB
    EXCEPTION_ERROR = "Error in"
    SSL_CERTIFIED = "https://"
    NON_SSL = "http://"
    JOSN_FILE = "json_report.json"
    DELETE_SUCCESS_MSG = "Account Deleted Successfully."
    S3_ACCOUNTS = "s3_accounts"
    ACC_NAME = "account_name"
    ACC_EMAIL = "account_email"
    SECRET_KEY = "secret_key"
    IAMUSERS = "iam_users"
    ACCESS_KEY = "access_key"
    USER_NAME = "user_name"
    USER_ID = "user_id"
    IAM_USER = "test_iam_user"
    IAM_PASSWORD = ""
    ARN = "arn"
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    CONFLICT = 409
    SUCCESS_STATUS = 200
    FORBIDDEN = 403
    METHOD_NOT_FOUND = 404
    SUCCESS_STATUS_FOR_POST = 201
    USER_DATA = "{\"username\": \"testusername\", \"password\": \"Testuser@123\"," \
                " \"roles\": [\"user_role\"],\"email\":\"testmonitoruser@seagate.com\"," \
                "\"alert_notification\":true}"
    MISSING_USER_DATA = "{\"username\": \"testusername\", \"roles\": [\"user_role\"]}"
    CONTENT_TYPE = {'Content-Type': 'application/json'}
    BUCKET_NAME = "bucket_name"
    BUCKET = "buckets"
    NAME = "name"
    LOGIN_PAYLOAD = "{\"username\":\"$username\",\"password\":\"$password\"}"
    BUCKET_PAYLOAD = "{\"bucket_name\":\"buk$value\"}"
    BUCKET_POLICY_PAYLOAD = "{\"Statement\": [{\"Action\": [\"s3:$s3operation\"]," \
                            "\"Effect\": \"$effect\",\"Resource\": \"arn:aws:s3:::$value/*\"," \
                            "\"Principal\": \"$principal\"}]}"
    BUCKET_POLICY_PAYLOAD_IAM = "{\"Statement\": [{\"Action\": [\"s3:$s3operation\"]," \
                                "\"Effect\": \"$effect\",\"Resource\": \"arn:aws:s3:::$value/*\"," \
                                "\"Principal\": {\"AWS\":\"$principal\"}}]}"
    IAM_USER_DATA_PAYLOAD = "{\"user_name\": \"$iamuser\",\"password\": \"$iampassword\"," \
                            "\"require_reset\": $requireresetval}"
    IAM_USER_LOGIN_PAYLOAD = "{\"username\":\"$username\",\"password\":\"$password\"}"
    MULTI_BUCKET_POLICY_PAYLOAD = "{\"Statement\": [{\"Action\": [\"s3:$s3operation1\"," \
                                  "\"s3:$s3operation2\"],\"Effect\": \"$effect\"," \
                                  "\"Resource\": \"arn:aws:s3:::$value/*\"," \
                                  "\"Principal\": {\"AWS\":\"$principal\"}}]}"
    SORT_BY_ERROR = "{\'sort_by\': [\'Must be one of: user_id, username," \
                    " user_type, created_time, updated_time.\']}"
    CSM_USER_LIST_OFFSET = 1
    CSM_USER_LIST_LIMIT = 5
    CSM_USER_LIST_SORT_BY = "username"
    CSM_USER_LIST_SORT_DIR = "asc"
    CSM_NUM_OF_USERS_TO_CREATE = 5
    RANDOM_NUM_START = 3
    RANDOM_NUM_END = 9
    SORT_DIR_ERROR = "{\'sort_dir\': [\'Must be one of: desc, asc.\']}"
    CSM_USER_LIST_OFFSET = 1
    CSM_USER_LIST_LIMIT = 5
    CSM_USER_LIST_SORT_BY = "username"
    CSM_USER_LIST_SORT_DIR = "asc"
    CSM_NUM_OF_USERS_TO_CREATE = 5
    SORT_BY_EMPTY_PARAM_ERROR_RESPONSE = {
        'error_code': '4099', 'message_id': "{'sort_by': ['Must be one of: user_id,"
                                            " username, user_type, created_time, updated_time.']}",
        'message': 'Invalid Parameter for alerts', 'error_format_args': None}
    NODE_ID_OPTIONS= {"storage": "storage_encl", "node": "node:{}{}"}
    HEALTH_SUMMARY_INSTANCE = "health_summary"
    HEALTH_SUMMARY_SCHEMA = {
        "type": "object",
        "properties": {
            "total": { "type": "number" },
            "fault": { "type": "number" },
            "good":  { "type": "number" }
        },
        "required": ["total", "good"]
    }


# RAS constant
BYTES_TO_READ = 8000
ONE_BYTE_TO_READ = 1
EXCEPTION_ERROR = "Error in"
CPU_USAGE_KEY = "cpu_usage_threshold"
MEM_USAGE_KEY = "host_memory_usage_threshold"
DISK_ALERT_KEY = "diskUsedPercentage"

# RAS node paths used in lib.
RABBIT_MQ_FILE = "/opt/seagate/sspl/low-level/tests/manual/rabbitmq_reader.py"
RABBIT_MQ_LOCAL_PATH = "scripts/setup_client/rabbitmq_reader.py"
LAST_SEL_INDEX = "cd /var/cortx/sspl/data/server && cat last_sel_index"
CHECK_SSPL_LOG_FILE = "tail -f /var/log/cortx/sspl/sspl.log > '{}' 2>&1 &"
MANUAL_PATH = "/opt/seagate/sspl/low-level/tests/manual/"
ENCRYPTOR_FILE_PATH = "scripts/setup_client/encryptor_updated.py"
TELNET_OP_PATH = "scripts/setup_client/telnet_operations.py"
STORAGE_ENCLOSURE_PATH = "/opt/seagate/cortx/provisioner/pillar/components/storage_enclosure.sls"
CLUSTER_PATH = "/opt/seagate/cortx/provisioner/pillar/components/cluster.sls"
CONFIG_PATH = "config/ras/ras_config.yaml"
SSPL_CONFIG_PATH = "config/ras/test_sspl.yaml"
SERVICE_STATUS_PATH = "/var/cortx/sspl/data/state.txt"
CONSUL_PATH = "/usr/bin/consul"
KV_STORE_PATH = "sspl/config/STORAGE_ENCLOSURE"
LOG_STORE_PATH = "sspl/config/SYSTEM_INFORMATION"
KV_STORE_DISK_USAGE = "sspl/config/NODEDATAMSGHANDLER"
SSPL_STATE_CMD = "cat /var/cortx/sspl/data/state.txt"
KV_STORE_LOG_LEVEL = "sspl/config/SYSTEM_INFORMATION"
IEM_DIRECTORY = "/opt/seagate/cortx/iem/iec_mapping"
SSPL_LOG_FILE_PATH = "/var/log/cortx/sspl/sspl.log"
COMMON_CONFIG_PATH = "config/common_config.yaml"
CSM_CONF = "config/csm/csm_config.yaml"
REMOTE_TELNET_PATH = "/root/telnet_operations.py"
CTRL_LOG_PATH = "/root/telnet.xml"
RAS_CFG = "config/ras_config.yaml"
SELINUX_FILE_PATH = "/etc/selinux/config"
