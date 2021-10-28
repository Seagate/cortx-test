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
import os
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
        self.hosts = []
        self.unames = []
        self.passwds = []
        self.nd_objs = []

        for i in range(len(CMN_CFG["nodes"])):
            self.hosts.append(CMN_CFG["nodes"][i]["hostname"])
            self.unames.append(CMN_CFG["nodes"][i]["username"])
            self.passwds.append(CMN_CFG["nodes"][i]["password"])
            self.nd_objs.append(Node(hostname=self.hosts[i], username=self.unames[i],
                                     password=self.passwds[i]))

        # self.service_repo = "/root/deploy-scripts/k8_cortx_cloud"
        self.service_repo = os.getenv("Solution_yaml_path", "/root/cortx-k8s/k8_cortx_cloud")

    def modify_solution_file(self, key, value):
        """
        Modify solution yaml file
        """
        local_file = '/root/solution.yaml'
        if os.path.exists(local_file):
            os.remove(local_file)
        remote_file = os.path.join(self.service_repo, 'solution.yaml')
        self.nd_objs[0].copy_file_to_local(remote_file, local_file)
        input_stream = open(local_file, 'r')
        data = yaml.safe_load(input_stream)
        if key == 'csm_mgmt_admin_secret':
            data['solution']['secrets']['content']['csm_mgmt_admin_secret'] = value
        with open(local_file, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data))
        self.nd_objs[0].copy_file_to_remote(local_file, remote_file)

    def recover_files(self, recover):
        """
        Recover files modified during tests
        """
        local_config_file = '/tmp/config-template.yaml'
        local_sol_file = '/tmp/solution.yaml'
        remote_config_file = os.path.join(self.service_repo,
                                          'cortx-cloud-helm-pkg/cortx-configmap/'
                                          'templates/config-template.yaml')
        remote_sol_file = os.path.join(self.service_repo, 'solution.yaml')
        if not recover:
            if os.path.exists(local_config_file):
                os.remove(local_config_file)
            if os.path.exists(local_sol_file):
                os.remove(local_sol_file)
            self.nd_objs[0].copy_file_to_local(remote_config_file, local_config_file)
            self.nd_objs[0].copy_file_to_local(remote_sol_file, local_sol_file)
        else:
            self.nd_objs[0].copy_file_to_remote(local_config_file, remote_config_file)
            self.nd_objs[0].copy_file_to_remote(local_sol_file, remote_sol_file)

    def modify_config_template(self, key, value):
        """
        Modify config template file
        """
        local_file = '/root/config-template.yaml'
        if os.path.exists(local_file):
            os.remove(local_file)
        remote_file = os.path.join(self.service_repo,
                                   'cortx-cloud-helm-pkg/cortx-configmap/'
                                   'templates/config-template.yaml')
        self.nd_objs[0].copy_file_to_local(remote_file, local_file)
        with open(local_file, "r") as f:
            data = f.readlines()
        with open(local_file, "w") as f:
            for line in data:
                if key == 'endpoints':
                    if "https://<<.Values.cortx.io.svc>>:8081" in line and value == 'http':
                        line = line.replace('https', 'http')
                    if "http://<<.Values.cortx.io.svc>>:8081" in line and value == 'https':
                        line = line.replace('http', 'https')
                elif key == 'mgmt_admin' and 'mgmt_admin: cortxadmin' in line:
                    line = line.replace('cortxadmin', value)
                f.write(line)
        self.nd_objs[0].copy_file_to_remote(local_file, remote_file)

    def destroy_cluster(self):
        """
        Exceute destroy cluster command
        """
        destroy_cmd = "cd " + self.service_repo + " && ./destroy-cortx-cloud.sh"
        self.nd_objs[0].execute_cmd(destroy_cmd, read_lines=True)
        additional_cmds = ["rm -rf /etc/3rd-party/openldap/var/data/3rd-party/*",
                           "rm -rf /mnt/fs-local-volume/local-path-provisioner/*",
                           "rm -rf /mnt/fs-local-volume/etc/gluster/var/log/cortx/*"]
        for cmd in additional_cmds:
            for i in range(len(self.nd_objs)):
                self.nd_objs[i].execute_cmd(cmd, read_lines=True)

    def install_prerequisites(self):
        """
        Execute prerequisites command
        """
        prereq_cmd = "cd " + self.service_repo + " && ./prereq-deploy-cortx-cloud.sh /dev/sdb"
        for i in range(len(self.nd_objs)):
            self.nd_objs[i].execute_cmd(prereq_cmd, read_lines=True)

    def deploy_cluster(self):
        """
        Execute deploy cluster command
        """
        deploy_cmd = 'cd ' + self.service_repo + " && ./deploy-cortx-cloud.sh"
        self.nd_objs[0].execute_cmd(deploy_cmd, read_lines=True, exc=False)

    def get_pod_status_value(self, pod_name):
        """
        Check for required status in pod
        """
        data = self.nd_objs[0].execute_cmd(cmd=common_cmd.CMD_POD_STATUS, read_lines=True)
        for line in data:
            if pod_name in line and 'Error' in line:
                return True
        return False
