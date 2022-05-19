#!/usr/bin/python
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
"""Test library for CSM related cluster operations."""
import os
import re
import time

import yaml

from commons import commands as common_cmd
from commons import constants as cons
from commons.utils import assert_utils
from commons.constants import CONTROL_POD_NAME_PREFIX
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

    def get_pod_name(self, resp):
        """
        Function for getting cortx control pod name from master node
        """
        self.log.info("getting control pod name")
        data = str(resp, 'UTF-8')
        data = data.split("\n")
        res = False
        for line in data:
            if "cortx-control" in line:
                line_found = line
                res = re.sub(' +', ' ', line_found)
                res = res.split()[0]
                break
        return res

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
        with open(local_file, "r") as fptr:
            data = fptr.readlines()
        with open(local_file, "w") as fptr:
            for line in data:
                if key == 'endpoints':
                    if "https://<<.Values.cortx.io.svc>>:8081" in line and value == 'http':
                        line = line.replace('https', 'http')
                    if "http://<<.Values.cortx.io.svc>>:8081" in line and value == 'https':
                        line = line.replace('http', 'https')
                elif key == 'mgmt_admin' and 'mgmt_admin: cortxadmin' in line:
                    line = line.replace('cortxadmin', value)
                fptr.write(line)
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

    def restart_control_pod(self, nd_obj):
        """
        Stop and start control pod
        :param nd_obj: Master node object
        :return True/False: If pod restart is successful
        """
        pod_name = nd_obj.get_pod_name(CONTROL_POD_NAME_PREFIX)
        if not pod_name[0]:
            return pod_name
        resp = nd_obj.delete_pod(pod_name[1])
        if not resp[0]:
            return resp
        self.log.info("Step : Check if control pod is re-deployed")
        pod_up = False
        for _ in range(3):
            resp = nd_obj.get_pod_name(CONTROL_POD_NAME_PREFIX)
            if resp[0]:
                pod_up = True
                break
            time.sleep(30)
        if not pod_up:
            return pod_up, "Pod is not up"
        return pod_up, "Pod is restarted"

    def set_telemetry_auth(self, pod_name, csm_list_key_value, csm_rest_api=True):
        """
        Stop and start control pod
        :param pod_name: Name of the pod
        :param csm_list_key_value: CSM API key value list
        :param csm_rest_api: True when we are not updating consul db
        :return True/False: If able to set Telemetry Auth
        """
        if csm_rest_api:
            self.nd_objs[0].execute_cmd(cmd=common_cmd.K8S_CP_TO_LOCAL_CMD.format(
                pod_name, cons.CSM_CONF_PATH, cons.CSM_COPY_PATH, cons.CORTX_CSM_POD),
                read_lines=False, exc=False)
            resp = self.nd_objs[0].copy_file_to_local(
                remote_path=cons.CSM_COPY_PATH, local_path=cons.CSM_COPY_PATH)
            assert_utils.assert_true(resp[0], resp[1])
            stream = open(cons.CSM_COPY_PATH, 'r')
            data = yaml.safe_load(stream)
            for csm_dict in csm_list_key_value:
                for csm_key, csm_val in csm_dict.items():
                    url_list = csm_key.split('/')
                    dict1 = dict(zip(range(0, len(url_list)), url_list))
                    if len(url_list) == 3:
                        data[dict1[0]][dict1[1]][dict1[2]] = csm_val
                    elif len(url_list) == 2:
                        data[dict1[0]][dict1[1]] = csm_val
                    elif len(url_list) == 1:
                        data[dict1[0]] = csm_val
                    elif len(url_list) == 4:
                        data[dict1[0]][dict1[1]][dict1[2]][dict1[3]] = csm_val
                    elif len(url_list) == 5:
                        data[dict1[0]][dict1[1]][dict1[2]][dict1[3]][dict1[4]] = csm_val
                    elif len(url_list) == 6:
                        data[dict1[0]][dict1[1]][dict1[2]][dict1[3]][dict1[4]][dict1[5]] = csm_val
                    else:
                        return False, "Not able to set telemetry auth using CSM REST"
            with open(cons.CSM_COPY_PATH, 'w') as yaml_file:
                yaml_file.write(yaml.dump(data, default_flow_style=False))
            yaml_file.close()
            resp = self.nd_objs[0].copy_file_to_remote(
                local_path=cons.CSM_COPY_PATH, remote_path=cons.CSM_COPY_PATH)
            assert_utils.assert_true(resp[0], resp[1])
            # cmd = kubectl cp /root/a.text cortx-control-pod-6cb946fc6c-k298q:/tmp -c
            # cortx-csm-agent
            self.nd_objs[0].execute_cmd(cmd=common_cmd.K8S_CP_TO_CONTAINER_CMD.format(
                cons.CSM_COPY_PATH, pod_name, cons.CSM_CONF_PATH, cons.CORTX_CSM_POD),
                read_lines=False, exc=False)
            return True, "Able to set telemetry auth "
        return False, "Not able to set telemetry auth using CSM REST"
