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
"""Test library for CSM related cluster operations."""
import json
import random
import time
import yaml

from commons import commands as common_cmd
from commons.helpers.node_helper import Node
from config import CMN_CFG
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class RestCsmCluster(RestTestLib):
    """
    RestCsmUser contains the Rest API calls for csm cluster operations
    """

    # TODO: EOS-25417: Modify this file when complete cluster deployment is working.

    def __init__(self):
        super(RestCsmCluster, self).__init__()
        self.config_file = '/root/cortx-prvsnr/test/deploy/kubernetes/solution-config/config.yaml'
        self.secret_file = '/root/cortx-prvsnr/test/deploy/kubernetes/solution-config/secrets.yaml'
        self.host1 = CMN_CFG["nodes"][0]["hostname"]
        self.uname1 = CMN_CFG["nodes"][0]["username"]
        self.passwd1 = CMN_CFG["nodes"][0]["password"]
        self.nd_obj1 = Node(hostname=self.host1, username=self.uname1,
                            password=self.passwd1)

        self.host2 = CMN_CFG["nodes"][1]["hostname"]
        self.uname2 = CMN_CFG["nodes"][1]["username"]
        self.passwd2 = CMN_CFG["nodes"][1]["password"]
        self.nd_obj2 = Node(hostname=self.host2, username=self.uname2,
                            password=self.passwd2)

        self.host3 = CMN_CFG["nodes"][2]["hostname"]
        self.uname3 = CMN_CFG["nodes"][2]["username"]
        self.passwd3 = CMN_CFG["nodes"][2]["password"]
        self.nd_obj3 = Node(hostname=self.host3, username=self.uname3,
                            password=self.passwd3)

    def modify_config_file(self, key, value):
        """
        modify config file
        """
        local_config_file = '/tmp/config.yaml'
        self.nd_obj1.copy_file_to_local(self.config_file, local_config_file)
        input_stream = open(local_config_file, 'r')
        data = yaml.load(input_stream, Loader=yaml.FullLoader)
        if key == 'endpoints':
            endpoint = data['cortx']['csm']['agent']['endpoints']
            if value == 'http':
                endpoint[0] = endpoint[0].replace('https', 'http')
            else:
                endpoint[0] = endpoint[0].replace('http', 'https')
            data['cortx']['csm']['agent']['endpoints'] = endpoint
        elif key == 'mgmt_admin':
            data['cortx']['csm']['mgmt_admin'] = value
        with open(local_config_file, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data))
        self.nd_obj1.copy_file_to_remote(local_config_file, self.config_file)

    def modify_secrets_file(self, value):
        """
        modify secrets file
        """
        local_secrets_file = '/tmp/secrets.yaml'
        self.nd_obj1.copy_file_to_local(self.secret_file, local_secrets_file)
        input_stream = open(local_secrets_file, 'r')
        data = yaml.load(input_stream, Loader=yaml.FullLoader)
        data['stringData']['csm_mgmt_admin_secret'] = value
        with open(local_secrets_file, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data))
        self.nd_obj1.copy_file_to_remote(local_secrets_file, self.secret_file)

    def pull_provisioner(self):
        """
        Pull provisioner scripts
        """
        cmds = ["rm -rf /root/cortx-prvsnr",
                "cd /root && git clone https://github.com/Seagate/cortx-prvsnr -b kubernetes"]
        for cmd in cmds:
            self.nd_obj1.execute_cmd(cmd, read_lines=True)
            self.nd_obj2.execute_cmd(cmd, read_lines=True)
            self.nd_obj3.execute_cmd(cmd, read_lines=True)

    def trigger_prov_command(self, cmd_name):
        """
        Trigger prov scripts
        """
        if cmd_name == 'reimage':
            cmd = "cd /root/cortx-prvsnr/test/deploy/kubernetes && ./reimage.sh"
            self.nd_obj2.execute_cmd(cmd, read_lines=True)
            self.nd_obj3.execute_cmd(cmd, read_lines=True)
        elif cmd_name == 'destroy':
            cmd = "cd /root/cortx-prvsnr/test/deploy/kubernetes && ./destroy.sh"
        elif cmd_name == 'deploy':
            cmd = "cd /root/cortx-prvsnr/test/deploy/kubernetes && ./deploy.sh"
        elif cmd_name == 'service':
            cmd = "cd /root/cortx-prvsnr/test/deploy/kubernetes && ./service.sh"
        self.nd_obj1.execute_cmd(cmd, read_lines=True)

    def get_pod_status(self):
        """
        Get control pod status
        """
        for _ in range(3):
            data = self.nd_obj1.execute_cmd(cmd=common_cmd.CMD_POD_STATUS, read_lines=True)
            complete_status = 0
            self.log.info(data)
            for line in data:
                self.log.info(line)
                if 'control-node' in line and 'Completed' in line:
                    complete_status = complete_status + 1
            self.log.info(complete_status)
            if complete_status == 1:
                return True
            time.sleep(3 * 60)
        return False

    def apply_csm_service(self):
        """
        Apply csm service to access endpoint
        """
        yaml_str = """\
        apiVersion: v1
        kind: Service
        metadata:
          name: csm-agent
          labels:
            app: control-node
        spec:
          type: NodePort
          ports:
          - port: 8081
            nodePort: 32101
          selector:
            app: control-node
        """

        data = yaml.load(yaml_str, Loader=yaml.FullLoader)
        with open('csm_service.yaml', 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)
        self.nd_obj1.copy_file_to_remote('csm_service.yaml', '/root/csm_service.yaml')
        cmd = "kubectl apply -f /root/csm_service.yaml"
        self.nd_obj1.execute_cmd(cmd, read_lines=True)
