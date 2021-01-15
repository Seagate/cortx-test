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
# -*- coding: utf-8 -*-
# !/usr/bin/python

#: NWORKERS specifies number of worker (python) threads  in a worker pool.
NWORKERS = 32

#: NGREENLETS specifies number of greenlets in a thread. These greenlets will run in parallel.
NGREENLETS = 32

# RAS Paths
START_RABBITMQ_READER_CMD = "python3 /opt/seagate/sspl/low-level/tests/" \
                            "manual/rabbitmq_reader.py {} {} {}"
LAST_SEL_INDEX = "cd /var/cortx/sspl/data/server && cat last_sel_index"
CHECK_SSPL_LOG_FILE = "tail -f /var/log/cortx/sspl/sspl.log > '{}' 2>&1 &"
RABBIT_MQ_FILE = "/opt/seagate/sspl/low-level/tests/manual/rabbitmq_reader.py"
MANUAL_PATH = "/opt/seagate/sspl/low-level/tests/manual/"
RABBIT_MQ_LOCAL_PATH = "scripts/setup_client/rabbitmq_reader.py"
ENCRYPTOR_FILE_PATH = "scripts/setup_client/encryptor_updated.py"
STORAGE_ENCLOSURE_PATH = "/opt/seagate/cortx/provisioner/pillar/components" \
                        "/storage_enclosure.sls"
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
TELNET_OP_PATH = "scripts/server_scripts/telnet_operations.py"
CSM_CONF = "config/csm/csm_config.yaml"
REMOTE_TELNET_PATH = "/root/telnet_operations.py"
CTRL_LOG_PATH = "/root/telnet.xml"
SELINUX_FILE_PATH = "/etc/selinux/config"
# RAS Constants
BYTES_TO_READ = 8000
ONE_BYTE_TO_READ = 1
DISK_ALERT_KEY = "diskUsedPercentage"
HEADERS_STREAM_UTILITIES = {"Content-type": "application/x-www-form-urlencoded",
                            "Accept": "text/plain"}
URL_STREAM_UTILITIES = "http://utils-stream.sw.lcd.colo.seagate.com/utility" \
                      "/api/public/v1/get_tripw"
NO_CMD_RECEIVED_MSG = "No command response received !!!"
EXCEPTION_ERROR = "Error in"
MEM_USAGE_KEY = "host_memory_usage_threshold"
PCS_SSPL_SECTION = " Master/Slave Set: sspl-master [sspl]\n"
