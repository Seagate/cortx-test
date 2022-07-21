# !/usr/bin/python
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

"""All common constants from cortx-test."""
import tempfile

from commons import const

#: NWORKERS specifies number of worker (python) threads  in a worker pool.
NWORKERS = 32

#: NGREENLETS specifies number of greenlets in a thread. These greenlets will
# run in parallel.
NGREENLETS = 32

# SB contansts
MIN = 800000
MAX = 1300000

# Product Family and versions
PROD_FAMILY_LC = "LC"
PROD_FAMILY_LR = "LR"
PROD_TYPE_K8S = "k8s"
PROD_TYPE_NODE = "node"

# S3 Engine Type and versions
S3_ENGINE = "MGW"
S3_ENGINE_CORTX = 1
S3_ENGINE_RGW = 2

# K8s for cortx
POD_NAME_PREFIX = "cortx-data"
CORTX_DATA_NODE_PREFIX = "cortx-data-headless-svc-"
SERVER_POD_NAME_PREFIX = "cortx-server"
HA_POD_NAME_PREFIX = "cortx-ha"
HA_K8S_CONTAINER_NAME = "cortx-ha-k8s-monitor"
HA_FAULT_TOLERANCE_CONTAINER_NAME = "cortx-ha-fault-tolerance"
HA_HEALTH_MONITOR_CONTAINER_NAME = "cortx-ha-health-monitor"
HAX_CONTAINER_NAME = "cortx-hax"
RGW_CONTAINER_NAME = "cortx-rgw"
HA_SHUTDOWN_LOGS = ["k8s_resource_monitor.log", "fault_tolerance.log", "health_monitor.log"]
NAMESPACE = "cortx"
CONTROL_POD_NAME_PREFIX = "cortx-control"
CLIENT_POD_NAME_PREFIX = "cortx-client"
MOTR_CONTAINER_PREFIX = "cortx-motr-io"
HA_SHUTDOWN_SIGNAL_PATH = "scripts/server_scripts/ha_shutdown_signal.py"
MOCK_MONITOR_REMOTE_PATH = "/root/mock_health_event_publisher.py"
MOCK_MONITOR_LOCAL_PATH = "scripts/server_scripts/mock_health_event_publisher.py"
HA_CONSUL_VERIFY = "cortx>ha>v1>cluster_stop_key:1"
HA_CONSUL_NOKEY = "NotFound"
HA_TMP = "/root"
HA_LOG = "/mnt/fs-local-volume/local-path-provisioner/"
HA_PROCESS = "/opt/seagate/cortx/ha/bin/ha_start"
HA_CONFIG_FILE = "/root/config.json"
MOTR_CLIENT="motr_client"
UPGRADE_IN_PROGRESS_MSG = "An upgrade is already in progress"
UPGRADE_SUSPEND_MSG = "Upgrade suspended"
UPGRADE_ALREADY_SUSPENDED = "Upgrade Process Not found on the system, Suspend cannot be performed"

# common constant.
ERR_MSG = "Error in %s: %s"

# RAS Paths
BYTES_TO_READ = 8000
ONE_BYTE_TO_READ = 1
EXCEPTION_ERROR = "Error in"
CPU_USAGE_KEY = "cpu_usage_threshold"
MEM_USAGE_KEY = "host_memory_usage_threshold"
DISK_ALERT_KEY = "diskUsedPercentage"
LAST_SEL_INDEX = "cd /var/cortx/sspl/data/server && cat last_sel_index"
CHECK_SSPL_LOG_FILE = "tail -f /var/log/cortx/sspl/sspl.log > '{}' 2>&1 &"
RABBIT_MQ_FILE = "/root/rabbitmq_reader.py"
MSG_BUS_READER_PATH = "/root/read_message_bus.py"
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
RECEIVER_OP_PATH = "scripts/server_scripts/test_receiver.py"
DAEMON_OP_PATH = "scripts/server_scripts/daemon.py"
CSM_CONF = "config/csm/csm_config.yaml"
REMOTE_TELNET_PATH = "/root/telnet_operations.py"
REMOTE_RECEIVER_PATH = "/root/test_receiver.py"
REMOTE_DAEMON_PATH = "/root/daemon.py"
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
CONF_CPU_USAGE = "NODEDATAMSGHANDLER>cpu_usage_threshold"
CONF_MEM_USAGE = "NODEDATAMSGHANDLER>host_memory_usage_threshold"
CONF_DISK_USAGE = "NODEDATAMSGHANDLER>disk_usage_threshold"
CONF_SSPL_SRV_THRS_INACT_TIME = "SERVICEMONITOR>threshold_inactive_time"
CONF_CPU_FAULT_EN = "CPUFAULTSENSOR>monitor"
SSPL_GLOBAL_CONF_URL = 'yaml:///etc/sspl_global_config_copy.yaml'
SSPL_CFG_URL = "yaml:///etc/sspl.conf"
SVC_COPY_CONFG_PATH = "/tmp/svc_backup/"
CONF_SYSFS_BASE_PATH = "SYSTEM_INFORMATION>sysfs_base_path"
CONF_RAID_INTEGRITY = "RAIDINTEGRITYSENSOR>retry_interval"
AUTHSERVER_CONFIG = "/opt/seagate/cortx/auth/resources/authserver.properties"
LOCAL_COPY_PATH = tempfile.gettempdir() + "/authserver.properties"
LOCAL_CONF_PATH = tempfile.gettempdir() + "/cluster.conf"
LOCAL_SOLUTION_PATH = tempfile.gettempdir() + "/solution.yaml"
CLUSTER_CONF_PATH = "/etc/cortx/cluster.conf"
CSM_CONF_PATH = "/etc/cortx/csm/csm.conf"
CSM_COPY_PATH = tempfile.gettempdir() + "/csm.conf"
CLUSTER_COPY_PATH = tempfile.gettempdir() + "/cluster.conf"
CORTX_CSM_POD = "cortx-csm-agent"
LOCAL_PEM_PATH = "/etc/ssl/stx/stx.pem"
SUPPORT_BUNDLE_DIR_PATH = tempfile.gettempdir() + "/csm_support_bundle/"
NODE_INDEX = 2

""" S3 constants """
LOCAL_S3_CERT_PATH = "/etc/ssl/stx-s3-clients/s3/ca.crt"
const.S3_CONFIG = "/opt/seagate/cortx/s3/conf/s3config.yaml"
const.S3_CONFIG_K8s = "/etc/cortx/s3/conf/s3config.yaml"
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
const.S3_DI_WRITE_CHECK = "S3_WRITE_DATA_INTEGRITY_CHECK"
const.S3_DI_READ_CHECK = "S3_READ_DATA_INTEGRITY_CHECK"
const.S3_METADATA_CHECK = "S3_METADATA_INTEGRITY_CHECK"


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
                " \"role\": \"user_role\",\"email\":\"testmonitoruser@seagate.com\"," \
                "\"alert_notification\":true}"
    MISSING_USER_DATA = "{\"username\": \"testusername\", \"role\": \"user_role\"}"
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
    CUSTOM_S3_USER = ["account_name", "account_email", "password", "access_key", "secret_key"]
    S3_ACCESS_UL = 128
    S3_ACCESS_LL = 16
    S3_SECRET_UL = 40
    S3_SECRET_LL = 8
    IAM_ACCESS_UL = 128
    IAM_ACCESS_LL = 16
    IAM_SECRET_UL = 40
    IAM_SECRET_LL = 8
    MAX_S3_USERS = 1000
    MAX_BUCKETS = 1000
    MAX_IAM_USERS = 1000
    MAX_CSM_USERS = 100
    CSM_USER_LIST_OFFSET = 1
    CSM_USER_LIST_LIMIT = 5
    CSM_USER_LIST_SORT_BY = "username"
    CSM_USER_LIST_SORT_DIR = "asc"
    CSM_NUM_OF_USERS_TO_CREATE = 5
    RANDOM_NUM_START = 3
    RANDOM_NUM_END = 9
    SORT_DIR_ERROR = "{\'dir\': [\'Must be one of: desc, asc.\']}"
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
    PERF_STAT_METRICS = ["throughput_read",
                         "throughput_write",
                         "iops_read_object",
                         "latency_create_object",
                         "iops_write_object",
                         "iops_read_bucket",
                         "iops_write_bucket"]


# aws cli errors
AWS_CLI_ERROR = ["ServiceUnavailable",
                 "MalformedPolicy",
                 "InvalidRequest",
                 "Forbidden",
                 "Conflict",
                 "InternalError",
                 "InvalidArgument",
                 "AccessDenied",
                 "Failed:",
                 "An error occurred",
                 "S3 error: ",
                 "Read timeout"
                 "Connection was closed"]

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
CSM_USER_HELP = [
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
PIP_CONFIG = "/etc/pip.conf"

# Locking server
SHARED_LOCK = 'shared'
EXCLUSIVE_LOCK = 'exclusive'


class SwAlerts:
    SVCS_3P = [
        # "elasticsearch.service", # brings down the csm
        # "hare-consul-agent.service", # Disabled on VM EOS-20861
        # "slapd.service", # brings down the csm
        "statsd.service",
        "rsyslog.service",
        # "lnet.service", brings down motr-io service
        "salt-master.service",
        "salt-minion.service",
        "glusterd.service",
        "multipathd.service",
        "scsi-network-relay.service"
    ]

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
        NW_INTFC = "node:interface:nw"


class Sizes:
    KB = 1024
    MB = KB * KB
    GB = MB * KB


KB = 1024
MB = KB * KB
GB = MB * MB

# Removing 0Byte File Size for now.
NORMAL_UPLOAD_SIZES = [4 * KB, 8 * KB, 64 * KB, 256 * KB, 1 * MB, 4 * MB, 8 * MB,
                       16 * MB, 32 * MB, 64 * MB, 128 * MB]

MULTIPART_UPLOAD_SIZES = [1 * MB, 4 * MB, 8 * MB, 16 * MB, 21 * MB, 32 * MB, 64 * MB,
                          128 * MB, 256 * MB, 512 * MB, 1024 * MB]

OFFSET = 1 * KB  # Offset for mis aligned sizes

NORMAL_UPLOAD_SIZES_IN_MB = [1, 4, 8, 16, 32, 64, 128]

MULTIPART_UPLOAD_SIZES_IN_MB = [1, 4, 16, 32, 64, 128, 256, 512, 1024]

# Support Bundle
R2_SUPPORT_BUNDLE_PATH = "/var/log/cortx/support_bundle/"
SUPPORT_BUNDLE_COMPONENT_LIST = ["csm", "sspl", "s3", "motr", "hare", "provisioner",
                                 "manifest", "uds", "elasticsearch", "utils", "HA"]
SB_POD_PREFIX_AND_COMPONENT_LIST = {POD_NAME_PREFIX: ["hare", "motr", "utils"],
                                    SERVER_POD_NAME_PREFIX: ["rgw", "hare", "utils"],
                                    CONTROL_POD_NAME_PREFIX: ["csm", "utils"],
                                    HA_POD_NAME_PREFIX: ["utils"]}
SB_EXTRACTED_PATH = "/etc/cortx/log/"

# K8s env
K8S_SCRIPTS_PATH = "/root/deploy-scripts/k8_cortx_cloud/"
K8S_PEM_PATH = "/opt/seagate/cortx/s3/install/haproxy/ssl/s3.seagate.com.pem"
K8S_CRT_PATH = "/opt/seagate/cortx/s3/install/haproxy/ssl/s3.seagate.com.crt"
K8S_PRE_DISK = "/dev/sdb"
K8S_PEM_FILE_PATH = "/root/deploy-scripts/k8_cortx_cloud/cortx-cloud-helm-pkg/cortx-configmap/" \
                    "ssl-cert/s3.seagate.com.pem"

# haproxy.cfg dummy file Path
HAPROXY_DUMMY_CONFIG = "scripts/cicd_k8s/haproxy_dummy.cfg"
HAPROXY_DUMMY_RGW_CONFIG = "scripts/cicd_k8s/haproxy_rgw_dummy.cfg"

# Pod restore methods
RESTORE_SCALE_REPLICAS = "scale_replicas"
RESTORE_DEPLOYMENT_K8S = "k8s"
RESTORE_DEPLOYMENT_HELM = "helm"

# log rotation
LOG_PATH_CSM = "/etc/cortx/log/csm"
MAX_LOG_FILE_SIZE_CSM_MB = 17
LOG_PATH_FILE_SIZE_MB_S3 = {"/etc/cortx/log/s3/{}/s3backgrounddelete/":5,
                            "/etc/cortx/log/auth/{}/server/":20,
                            "/etc/cortx/log/s3/{}/haproxy/":5}
LOG_PATH_FILE_SIZE_MB_UTILS = {"/etc/cortx/log/utils/{}/iem/":5,
                               "/etc/cortx/log/utils/{}/message_bus/":5}
LOG_PATH_FILE_SIZE_MB_HARE = {"/etc/cortx/log/hare/log/{}/":50}
LOG_PATH_FILE_SIZE_MB_MOTR = {"/etc/cortx/log/motr/{}/addb/":129,
                              "/etc/cortx/log/motr/{}/trace/":17}
MAX_NO_OF_ROTATED_LOG_FILES = {"CSM":10, "Hare":10, "Motr":2, "Utils":6}


# Procpath Collection
PID_WATCH_LIST = ['m0d', 'radosgw', 'hax']
REQUIRED_MODULES = ["Procpath", "apsw-wheels"]

DTM_RECOVERY_STATE = "RECOVERED"
M0D_SVC = "ioservice"
SERVER_SVC = "rgw_s3"
