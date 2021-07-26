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

"""
Python library contains methods which allows you to create m0* commands.
"""

import subprocess
import logging
import json
import re
import os
import sys
import libs.motr as motr_cons
from commons.helpers import node_helper 
from config import CMN_CFG

logger = logging.getLogger(__name__)

class MotrTestLib():

    def __init__(self):
        self.files_to_delete = []
        self.hosts = []
        self.per_host_services_pids_endps = {}
        self.host = CMN_CFG["nodes"][0]["hostname"]
        self.uname = CMN_CFG["nodes"][0]["username"]
        self.passwd = CMN_CFG["nodes"][0]["password"]
        self.cluster_info = None
        self.profile_fid = None
        self.process_fid = None
        self.local_endpoint = None
        self.ha_endpoint = None
        self.client_index = 0
        self.utils_obj = node_helper.Node(
            hostname=self.host, username=self.uname, password=self.passwd)
        self.parse_funcs = {
                            "m0crate": self.m0crate_parse_func,
                            "m0": self.m0_parse_func,
                            "m0kv": self.m0kv_parse_func,
                            "other": self.other_parse_func,
                            }

    def get_max_client_index(self, my_svcs_info):
        count = 0
        for temp in my_svcs_info:
            if (temp["name"] == "m0_client"):
                count = count + 1
        return count - 1

    def is_localhost(self, hostname: str) -> bool:
        name = CMN_CFG["nodes"][0]["hostname"]
        temp = hostname in ('localhost', '127.0.0.1', name, f'{name}.local')
        return hostname in ('localhost', '127.0.0.1', name, f'{name}.local')

    def get_cluster_info(self):
        ret = 0

        srvnode1 = self.host 
        cmd = '{}sudo hctl status --json'.format( '' if self.is_localhost(self.host) else f'ssh srvnode-1{self.host} ')
        self.cluster_info = json.loads(self.utils_obj.execute_cmd(cmd))
        if (self.cluster_info != None):
            self.profile_fid = self.cluster_info["profiles"][0]
            self.profile_fid = self.profile_fid["fid"]
            nodes_data = self.cluster_info["nodes"]
            for node in nodes_data:
                nodename = node["name"]
                if (nodename.startswith("srvnode") == True):
                    cmd1 = 'salt-call pillar.get cluster:{}:hostname'.format(nodename)
                    cmd2 = 'cut -f 2 -d ":" | tr -d [:space:]'
                    cmd = ''.join([cmd1, ' | ', cmd2])
                    nodename = self.utils_obj.execute_cmd(cmd)
                self.hosts.append(nodename)
                self.per_host_services_pids_endps[nodename] = node["svcs"]
            my_svcs_info = self.per_host_services_pids_endps[srvnode1]
            if (self.client_index < 0):
                print("User provided client index = {}".format(self.client_index))
                print("Setting user client index to 0(default)")
                self.client_index = 0
            else:
                max_client_index = self.get_max_client_index(my_svcs_info)
                if max_client_index < self.client_index:
                    print("Max client index = {}".format(max_client_index))
                    print("But user provided client index = {}. ".format(
                           self.client_index))
                    print("Setting user client index to 0(default)")
                    self.client_index = 0
            m0_client_counter = 0
            for temp in my_svcs_info:
                if (temp["name"] == "hax"):
                    self.ha_endpoint = temp["ep"]
                    continue
                if (temp["name"] == "m0_client"):
                    if (m0_client_counter == self.client_index):
                       temp_pid = re.findall('0x[0-9A-Fa-f]+', temp["fid"])
                       self.process_fid = "{}:{}".format(temp_pid[0], temp_pid[1] )
                       self.local_endpoint = temp["ep"]
                       m0_client_counter = m0_client_counter + 1
                    else:
                       m0_client_counter = m0_client_counter + 1
                    continue
        else:
            print("Could not fetch cluster info\n", file=sys.stderr)
            return -1

        return ret

    def get_workload_file_name(self, params):
        params_list = params.split()
        workload_file = params_list[1].split('/')[-1]
        return workload_file


    def delete_remote_files(self):
        # Delete files from remote machine
        if self.files_to_delete:
            for file in self.files_to_delete:
                logger.debug(f'Deleting file {file} from node')
                result = self.utils_obj.remove_file_remote(file)
                logger.debug(result)

    def update_workload_file(self, fname):
        ret = self.get_cluster_info()
        if ret:
            return ret

        str = "s/^\([[:space:]]*MOTR_LOCAL_ADDR: *\).*/\\1\"{}\"/""".format(self.local_endpoint)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)

        str = "s/^\([[:space:]]*MOTR_HA_ADDR: *\).*/\\1\"{}\"/".format(self.ha_endpoint)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)

        str = "s/^\([[:space:]]*PROF: *\).*/\\1\"{}\"/".format(self.profile_fid)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)

        str = "s/^\([[:space:]]*PROCESS_FID: *\).*/\\1\"{}\"/".format(self.process_fid)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)

    def m0crate_parse_func(self, cmd_dict):
        workload_file = self.get_workload_file_name(cmd_dict['params'])
        local_file_path = f'{motr_cons.WORKLOAD_FILES_DIR}/{workload_file}'
        self.update_workload_file(local_file_path)
        remote_file_path = f'{motr_cons.TEMP_PATH}{workload_file}'

        # Copy m0crate workload file to remote tmp directory
        logger.debug(f"Copying file {workload_file} to node")
        result = self.utils_obj.copy_file_to_remote(local_file_path, remote_file_path)
        logger.debug(result)
        #self.files_to_delete.append(remote_file_path)

        cmd = f'm0crate -S {remote_file_path}'
        return cmd

    def other_parse_func(self, cmd_dict):
        params = cmd_dict['params'].split()
        cmd = cmd_dict['cmnd']
        for param in params:
            cmd = f'{cmd} {param}'
        return cmd

    def m0_parse_func(self, cmd_dict):
        ret = self.get_cluster_info()
        params = cmd_dict['params'].split()
        cmd = cmd_dict['cmnd']
        cluster_info = " -l "+ self.local_endpoint + " -H " + self.ha_endpoint + " -p " + self.profile_fid + " -P " + self.process_fid

        param = ' '.join([str(elem) for elem in params])
        cmd = f'{cmd} {cluster_info} {param}'
        return cmd

    def m0kv_parse_func(self, cmd_dict): 
        ret = self.get_cluster_info()
        params = cmd_dict['params'].split()
        cmd = cmd_dict['cmnd']
        cluster_info = " -l "+ self.local_endpoint + " -h " + self.ha_endpoint + " -p " + self.profile_fid + " -f " + self.process_fid

        param = ' '.join([str(elem) for elem in params])
        cmd = f'{cmd} {cluster_info} {param}'
        return cmd


    def get_command_str(self, cmd_dict):
        m0_commands = ["m0cp", "m0cat", "m0cp_mt", "m0mt", "m0touch", "m0trunc",
                       "m0unlink", "m0composite"]
        cmd = ""
        if (cmd_dict["cmnd"] == "m0crate"):
            cmd = self.parse_funcs["m0crate"](cmd_dict)
        elif (cmd_dict["cmnd"] in m0_commands):
            cmd = self.parse_funcs["m0"](cmd_dict)
        elif (cmd_dict["cmnd"] == "m0kv"):
            cmd = self.parse_funcs["m0kv"](cmd_dict)
        else:
            cmd = self.parse_funcs["other"](cmd_dict)
        return cmd
