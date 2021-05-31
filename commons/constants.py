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


#: NWORKERS specifies number of worker (python) threads  in a worker pool.
NWORKERS = 32

#: NGREENLETS specifies number of greenlets in a thread. These greenlets will
# run in parallel.
NGREENLETS = 32

# RAS Paths
BYTES_TO_READ = 8000
ONE_BYTE_TO_READ = 1
EXCEPTION_ERROR = "Error in"
CPU_USAGE_KEY = "cpu_usage_threshold"
MEM_USAGE_KEY = "host_memory_usage_threshold"
DISK_ALERT_KEY = "diskUsedPercentage"
LAST_SEL_INDEX = "cd /var/cortx/sspl/data/server && cat last_sel_index"
CHECK_SSPL_LOG_FILE = "tail -f /var/log/cortx/sspl/sspl.log > '{}' 2>&1 &"
RABBIT_MQ_FILE = "/home/rabbitmq_reader.py"
MSG_BUS_READER_PATH = "/home/read_message_bus.py"
MANUAL_PATH = "/opt/seagate/sspl/low-level/tests/manual/"
RABBIT_MQ_LOCAL_PATH = "scripts/server_scripts/rabbitmq_reader.py"
MSG_BUS_READER_LOCAL_PATH = "scripts/server_scripts/read_message_bus.py"
ENCRYPTOR_FILE_PATH = "scripts/server_scripts/encryptor.py"
STORAGE_ENCLOSURE_PATH = "/opt/seagate/cortx/provisioner/pillar/components" \
                        "/storage_enclosure.sls"
CLUSTER_PATH = "/opt/seagate/cortx/provisioner/pillar/components/cluster.sls"
RAS_CONFIG_PATH = "config/ras_config.yaml"
SSPL_TEST_CONFIG_PATH = "config/ras_test.yaml"
COMMON_DESTRUCTIVE_CONFIG_PATH = "config/common_destructive.yaml"
CONFIG_PATH = "config/ras/ras_config.yaml"
SSPL_CONFIG_PATH = "config/ras_test.yaml"
SERVICE_STATUS_PATH = "/var/cortx/sspl/data/state.txt"
CONSUL_PATH = "/usr/bin/consul"
KV_STORE_PATH = "sspl/config/STORAGE_ENCLOSURE"
LOG_STORE_PATH = "sspl/config/SYSTEM_INFORMATION"
KV_STORE_DISK_USAGE = "sspl/config/NODEDATAMSGHANDLER"
SSPL_STATE_CMD = "cat /var/cortx/sspl/data/state.txt"
KV_STORE_LOG_LEVEL = "sspl/config/SYSTEM_INFORMATION"
SECRET_KEY = "controller/secret"
IEM_DIRECTORY = "/opt/seagate/cortx/iem/iec_mapping"
SSPL_LOG_FILE_PATH = "/var/log/cortx/sspl/sspl.log"
COMMON_CONFIG_PATH = "config/common_config.yaml"
TELNET_OP_PATH = "scripts/server_scripts/telnet_operations.py"
CSM_CONF = "config/csm/csm_config.yaml"
REMOTE_TELNET_PATH = "/root/telnet_operations.py"
CTRL_LOG_PATH = "/root/telnet.xml"
SELINUX_FILE_PATH = "/etc/selinux/config"
HEADERS_STREAM_UTILITIES = {"Content-type": "application/x-www-form-urlencoded",
                            "Accept": "text/plain"}
URL_STREAM_UTILITIES = "http://utils-stream.sw.lcd.colo.seagate.com/utility" \
                      "/api/public/v1/get_tripw"
NO_CMD_RECEIVED_MSG = "No command response received !!!"
PCS_SSPL_SECTION = " Master/Slave Set: sspl-master [sspl]\n"
RAS_CFG = "config/ras_config.yaml"
CLUSTER_STATUS_MSG = "cluster is not currently running on this node"
NODE_RANGE_START = 1
NODE_RANGE_END = 3
NODE_PREFIX = "eosnode-"
CONF_STORE_ENCL_KEY = "storage_enclosure>enc_614f595926904dd0ab0f68395bfa7f11>controller"
CONF_PRIMARY_IP = CONF_STORE_ENCL_KEY + ">primary>ip"
CONF_PRIMARY_PORT = CONF_STORE_ENCL_KEY + ">primary>port"
CONF_SECONDARY_IP = CONF_STORE_ENCL_KEY + ">secondary>ip"
CONF_SECONDARY_PORT = CONF_STORE_ENCL_KEY + ">secondary>port"
CONF_ENCL_USER = CONF_STORE_ENCL_KEY + ">secret"
CONF_ENCL_SECRET = CONF_STORE_ENCL_KEY + ">user"
CONF_SSPL_LOG_LEVEL = "SYSTEM_INFORMATION>log_level"
SSPL_GLOBAL_CONF_URL = 'yaml:///etc/sspl_global_config_copy.yaml'

""" S3 constants """
const.S3_CONFIG = "/opt/seagate/cortx/s3/conf/s3config.yaml"
const.LOCAL_S3_CONFIG = "/tmp/s3config.yaml"
const.CA_CERT_PATH = "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
const.REMOTE_DEFAULT_DIR = "/var/motr"
const.CFG_FILES = ["/etc/haproxy/haproxy.cfg",
                   "/opt/seagate/cortx/s3/conf/s3config.yaml",
                   "/opt/seagate/cortx/auth/resources/authserver.properties",
                   "/opt/seagate/cortx/s3/s3backgrounddelete/config.yaml",
                   "/opt/seagate/cortx/s3/s3startsystem.sh"]
const.AUTHSERVER_FILE = "/opt/seagate/cortx/auth/resources/authserver.properties"
const.SCRIPT_PATH = "cd /opt/seagate/cortx/auth/scripts"
const.CRASH_COMMANDS = ["ls -l /var/crash", "ls -lR /var/motr | grep core"],
const.AUTHSERVER_LOG_PATH = "/var/log/seagate/auth/server/app.log"
const.S3CMD = "s3cmd"
const.S3FS = "s3fs-fuse"
const.SLAPD = "slapd"
const.HAPROXY = "haproxy"
const.S3AUTHSERVER = "s3authserver"
const.HAPROXY_LOG_PATH = "/var/log/haproxy.log"
const.S3_LOG_PATH = "/var/log/seagate/s3"
const.SUPPORT_BUNDLE_SUCCESS_MSG = "S3 support bundle generated successfully"
const.CLUSTER_NOT_RUNNING_MSG = "Cluster is not running"
const.LOG_MSG_PATH = "/var/log/messages"


class Rest:
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
    IAM_PASSWORD = "Seagate@123"
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
    SORT_BY_EMPTY_PARAM_ERROR_RESPONSE = {
        'error_code': '4099', 'message_id': "{'sort_by': ['Must be one of: user_id,"
                                            " username, user_type, created_time, updated_time.']}",
        'message': 'Invalid Parameter for alerts', 'error_format_args': None}
    NODE_ID_OPTIONS = {"storage": "storage_encl", "node": "node:{}"}
    HEALTH_SUMMARY_INSTANCE = "health_summary"
    HEALTH_SUMMARY_SCHEMA = {
        "type": "object",
        "properties": {
            "total": {"type": "number"},
            "fault": {"type": "number"},
            "good": {"type": "number"}
        },
        "required": ["total", "good"]
    }

# cortxcli constants
S3BUCKET_HELP = [
    f'usage: cortxcli s3buckets [-h] {{show,create,delete}}',
    'positional arguments:',
    '{show,create,delete}',
    'show                Displays S3 buckets On The CLI',
    'create              Create new S3 bucket',
    'delete              Delete the bucket',
    'optional arguments:',
    '-h, --help            show this help message and exit']
S3BUCKET_CREATE_HELP = [
    f"usage: cortxcli s3buckets create [-h] bucket_name",
    "positional arguments:",
    "bucket_name  Give a bucket name to create.",
    "optional arguments:",
    "-h, --help   show this help message and exit"]
S3BUCKET_SHOW_HELP = [
    f"usage: cortxcli s3buckets show [-h] [-f {{table,xml,json}}]",
    "optional arguments:",
    "-h, --help           show this help message and exit",
    "-f {table,xml,json}  Format of Output"]
S3BUCKET_DELETE_HELP = [
    f"usage: cortxcli s3buckets delete [-h] bucket_name",
    "positional arguments:",
    "bucket_name  Bucket Name",
    "optional arguments:",
    "-h, --help   show this help message and exit"]
S3ACCOUNT_HELP_CMDS = [
        "s3iamusers",
        "support_bundle",
        "system",
        "s3buckets",
        "s3accounts",
        "s3bucketpolicy"]
S3ACCOUNT_HELP = ["positional arguments:",
                  "{show,create,reset_password}",
                  "show                Displays S3 Accounts On the cli",
                  "create              Create a new S3 Account",
                  "reset_password      Reset password for S3 Account"]
S3ACC_CREATE_HELP = ["positional arguments:",
                     "account_name   Name to be given to S3 account",
                     "account_email  Email to be given to S3 account"]
S3ACC_SHOW_HELP = ["optional arguments:",
                   "-h, --help           show this help message and exit",
                   "-f {table,xml,json}  Format of Output"]
S3ACC_DELETE_HELP = ["positional arguments:",
                     "account_name  Name of the account to be Deleted."]
S3ACC_RESET_PWD_HELP = [
    "positional arguments:",
    "account_name  Name of S3 account whose password want to be reset."]
SUPPORT_BUNDLE_PATH = "/var/log/seagate/support_bundle/"
TAR_POSTFIX = "tar.gz"
SB_STATUS = "status"
BUNDLE_ID = "bundle_id"
SB_COMMENT = "comment"
NODE_NAME = "node_name"
MESSAGE = "message"
RESULT = "result"
JSON_LIST_FORMAT = "json"
TABLE_LIST_FORMAT = "table"
XML_LIST_FORMAT = "xml"
SUPPORT_BUNDLE_MSG = "Support bundle generation completed"
CSM_USER_HELP =[
    "support_bundle",
    "alerts",
    "s3accounts",
    "system",
    "users"]

# Prov Constants:
JENKINS_USERNAME = "6LS9f5yJ1IFpxbasg/wPKG4p5ycaBT6x/j7Kj7anTSk="
JENKINS_PASSWORD = "/AxML7GgiVqRSmKGcPSJSorUq0X9FLZrfrlEyw6tjKnccwT67II+SwOcKBWPV6SWoBwM/46rAky+fXKumyX41Q=="
TOKEN_NAME = "10Mnx/XE4tEN8xrzQTNp2iSGQxPjpcHXbIdZgJyIN7Y="
PARAMS = {"CORTX_BUILD": "{0}", "HOST": "{1}", "HOST_PASS": "{2}", "DEBUG": "True"}

#Locking server
SHARED_LOCK = 'shared'
EXCLUSIVE_LOCK = 'exclusive'

class SwAlerts:
    SVCS_3P = [
        "hare-consul-agent.service",
        "elasticsearch.service",
        "statsd.service",
        "rsyslog.service",
#        "haproxy.service",  # commented due to defect EOS-20842
        "hare-consul-agent.service",
        "lnet.service",
        "slapd.service",
        "lnet.service",
        "salt-master.service",
        "salt-minion.service",
        "glusterd.service",
        "multipathd.service",
        "scsi-network-relay.service"]

    SVCS_3P_UNAVAIL_VM = [
        "glusterd.service",
        "multipathd.service",
        "scsi-network-relay.service"]

    SVCS_3P_ENABLED_VM = list(set(SVCS_3P) - set(SVCS_3P_UNAVAIL_VM))

    SVC_LOAD_TIMEOUT_SEC = 30
    class AlertType:
        FAULT = "fault"
        RESOLVED = "fault_resolved"

    class Severity:
        CRITICAL = "critical"
        INFO = "informational"

    class ResourceType:
        SW_SVC = "node:sw:os:service"
