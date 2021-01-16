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

cmn_conf = config_utils.read_yaml("config/common_config.yaml")

#: NWORKERS specifies number of worker (python) threads  in a worker pool.
NWORKERS = 32

#: NGREENLETS specifies number of greenlets in a thread. These greenlets will run in parallel.
NGREENLETS = 32

""" S3 constants """
const.S3_BUILD_VER = {
    "CORTX": {
        "s3_config": "/opt/seagate/cortx/s3/conf/s3config.yaml",
        "ca_cert_path": "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt",
        "crash_commands": ["ls -l /var/crash", "ls -lR /var/motr | grep core"],
        "bundle_cmd": "sh /opt/seagate/cortx/s3/scripts/s3_bundle_generate.sh",
        "remote_default_dir": "/var/motr",
        "cfg_files": ["/etc/haproxy/haproxy.cfg", "/opt/seagate/cortx/s3/conf/s3config.yaml",
                      "/opt/seagate/cortx/auth/resources/authserver.properties",
                      "/opt/seagate/cortx/s3/s3backgrounddelete/config.yaml",
                      "/opt/seagate/cortx/s3/s3startsystem.sh"],
        "authserver_file": "/opt/seagate/cortx/auth/resources/authserver.properties",
        "script_path": "cd /opt/seagate/cortx/auth/scripts",
        "ldap_creds": {"ldap_username": cmn_conf[1]["ldap_username"], "ldap_passwd": cmn_conf[1]["ldap_passwd"]}
    },
}
