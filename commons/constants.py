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

from commons import const
from commons.utils import config_utils

cmn_conf = config_utils.read_yaml("config/common_config.yaml")[1]

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
    "ldap_username": cmn_conf["ldap_username"],
    "ldap_passwd": cmn_conf["ldap_passwd"]
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
