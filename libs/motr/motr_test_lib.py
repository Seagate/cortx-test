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

import json
import logging
import os
import re
import sys

import libs.motr as motr_cons
from commons import commands
from commons.helpers import node_helper
from commons.utils import assert_utils, system_utils
from config import CMN_CFG

logger = logging.getLogger(__name__)


class MotrTestLib():
    """
    This class contain Motr test related operations
    """
    def __init__(self):
        self.files_to_delete = []
        self.hosts = []
        self.per_host_services_pids_endps = {}
        self.num_nodes = len(CMN_CFG["nodes"])
        self.setuptype = CMN_CFG["setup_type"]
        self.cluster_info = None
        self.profile_fid = None
        self.process_fid = None
        self.local_endpoint = None
        self.ha_endpoint = None
        self.client_index = 0
        self.host_list = []
        self.uname_list = []
        self.passwd_list = []
        self.parse_funcs = {
                            "m0crate": self.m0crate_parse_func,
                            "m0": self.m0_parse_func,
                            "m0kv": self.m0kv_parse_func,
                            "other": self.other_parse_func,
                            }
        for node in range(self.num_nodes):
            self.host = CMN_CFG["nodes"][node]["hostname"]
            self.uname = CMN_CFG["nodes"][node]["username"]
            self.passwd = CMN_CFG["nodes"][node]["password"]
            self.host_list.append(self.host)
            self.uname_list.append(self.uname)
            self.passwd_list.append(self.passwd)
        self.utils_obj = node_helper.Node(
            hostname=self.host_list[0], username=self.uname_list[0], password=self.passwd_list[0])

    def get_max_client_index(self, my_svcs_info):
        """To calculate motr client number"""
        count = 0
        for temp in my_svcs_info:
            if (temp["name"] == "m0_client"):
                count = count + 1
        return count - 1

    def is_localhost(self, hostname: str) -> bool:
        """To Check provided host is local host or not"""
        name = CMN_CFG["nodes"][0]["hostname"]
        temp = hostname in ('localhost', '127.0.0.1', name, f'{name}.local')
        return temp

    def get_cluster_info(self, hostname):
        """Get cluster related info like endpoints, fids"""
        srvnode = self.host_list[0]
        if hostname:
            srvnode = hostname

        cmd = f'ssh {srvnode} hctl status --json'
        self.cluster_info = json.loads(self.utils_obj.execute_cmd(cmd))
        if self.cluster_info != None:
            self.profile_fid = self.cluster_info["profiles"][0]
            self.profile_fid = self.profile_fid["fid"]
            nodes_data = self.cluster_info["nodes"]
            for node in nodes_data:
                nodename = node["name"]
                nodename = nodename.split(".")[0]
                if nodename.startswith("srvnode") == True:
                    cmd1 = 'salt-call pillar.get cluster:{}:hostname'.format(nodename)
                    cmd2 = 'cut -f 2 -d ":" | tr -d [:space:]'
                    cmd = ''.join([cmd1, ' | ', cmd2])
                    nodename = self.utils_obj.execute_cmd(cmd)
                self.hosts.append(nodename)
                self.per_host_services_pids_endps[nodename] = node["svcs"]
            svcs_host = self.hosts[0]
            if bytes(srvnode, 'utf-8') in self.hosts:
                svcs_host = bytes(srvnode, 'utf-8')
            my_svcs_info = self.per_host_services_pids_endps[svcs_host]
            if self.client_index < 0:
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
                if temp["name"] == "hax":
                    self.ha_endpoint = temp["ep"]
                    continue
                if temp["name"] == "m0_client":
                    if m0_client_counter == self.client_index:
                        temp_pid = re.findall('0x[0-9A-Fa-f]+', temp["fid"])
                        self.process_fid = "{}:{}".format(temp_pid[0], temp_pid[1] )
                        self.local_endpoint = temp["ep"]
                        m0_client_counter = m0_client_counter + 1
                    else:
                        m0_client_counter = m0_client_counter + 1
                    continue
        else:
            print("Could not fetch cluster info\n %s", file=sys.stderr)
            return False
     
        return True

    def get_workload_file_name(self, params):
        """To fetch workload file name from params"""
        params_list = params.split()
        workload_file = params_list[1].split('/')[-1]
        return workload_file


    def delete_remote_files(self):
        """Delete files from remote machine"""
        if self.files_to_delete:
            for file in self.files_to_delete:
                logger.debug('Deleting file %s from node', file)
                result = self.utils_obj.remove_file_remote(file)
                logger.debug(result)

    def update_workload_file(self, fname):
        """Update endpoints and fids in workload files"""
        ret = self.get_cluster_info(self.host_list[0])
        assert_utils.assert_true(ret, "Not able to Fetch cluster INFO. Please check cluster status")

        str = "s/^\([[:space:]]*MOTR_LOCAL_ADDR: *\).*/\\1\"{}\"/""".format(self.local_endpoint)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

        str = "s/^\([[:space:]]*MOTR_HA_ADDR: *\).*/\\1\"{}\"/".format(self.ha_endpoint)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

        str = "s/^\([[:space:]]*PROF: *\).*/\\1\"{}\"/".format(self.profile_fid)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

        str = "s/^\([[:space:]]*PROCESS_FID: *\).*/\\1\"{}\"/".format(self.process_fid)
        cmd = "sed -i \"{}\" {}".format(str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

    def m0crate_parse_func(self, cmd_dict):
        """m0crate parse function"""
        workload_file = self.get_workload_file_name(cmd_dict['params'])
        local_file_path = f'{motr_cons.WORKLOAD_FILES_DIR}/{workload_file}'
        self.update_workload_file(local_file_path)
        remote_file_path = f'{motr_cons.TEMP_PATH}{workload_file}'

        # Copy m0crate workload file to remote tmp directory
        logger.debug("Copying file %s to node", workload_file)
        result = self.utils_obj.copy_file_to_remote(local_file_path, remote_file_path)
        logger.debug(result)
        #self.files_to_delete.append(remote_file_path)

        cmd = f'm0crate -S {remote_file_path}'
        return cmd

    def other_parse_func(self, cmd_dict):
        """Other command like dd parse function"""
        params = cmd_dict['params'].split()
        cmd = cmd_dict['cmnd']
        for param in params:
            cmd = f'{cmd} {param}'
        return cmd

    def m0_parse_func(self, cmd_dict):
        """m0 utility command parse function"""
        ret = self.get_cluster_info(self.host_list[0])
        assert_utils.assert_true(ret, "Not able to Fetch cluster INFO. Please check cluster status")
        params = cmd_dict['params'].split()
        cmd = cmd_dict['cmnd']
        cluster_info = " -l " + self.local_endpoint + " -H " + self.ha_endpoint + " -p " \
                       + self.profile_fid + " -P " + self.process_fid

        param = ' '.join([str(elem) for elem in params])
        cmd = f'{cmd} {cluster_info} {param}'
        return cmd

    def m0kv_parse_func(self, cmd_dict):
        """m0kv command parse function"""
        ret = self.get_cluster_info(self.host_list[0])
        assert_utils.assert_true(ret, "Not able to Fetch cluster INFO. Please check cluster status")
        params = cmd_dict['params'].split()
        cmd = cmd_dict['cmnd']
        cluster_info = " -l "+ self.local_endpoint + " -h " + self.ha_endpoint + " -p " \
                       + self.profile_fid + " -f " + self.process_fid

        param = ' '.join([str(elem) for elem in params])
        cmd = f'{cmd} {cluster_info} {param}'
        return cmd


    def get_command_str(self, cmd_dict):
        """get particular parse command function"""
        m0_commands = ["m0cp", "m0cat", "m0cp_mt", "m0mt", "m0touch", "m0trunc",
                       "m0unlink", "m0composite"]
        cmd = ""
        if cmd_dict["cmnd"] == "m0crate":
            cmd = self.parse_funcs["m0crate"](cmd_dict)
        elif cmd_dict["cmnd"] in m0_commands:
            cmd = self.parse_funcs["m0"](cmd_dict)
        elif cmd_dict["cmnd"] == "m0kv":
            cmd = self.parse_funcs["m0kv"](cmd_dict)
        else:
            cmd = self.parse_funcs["other"](cmd_dict)
        return cmd

    def get_endpoints(self, hostname):
        """Function which return endpoints, fids"""
        ret = self.get_cluster_info(hostname)
        assert_utils.assert_true(ret, "Not able to extract cluster details."
                                      "Please check cluster status.")
        return self.local_endpoint, self.ha_endpoint, self.process_fid, self.profile_fid

    def verify_libfabric_version(self):
        """TO check libfabric version and protocol status"""
        for i in range(self.num_nodes):
            logger.info('Checking libfabric rpm')
            ret, out = system_utils.run_remote_cmd(cmd=commands.GETRPM.format("libfab"),
                                                   hostname=self.host_list[i],
                                                   username=self.uname_list[i],
                                                   password=self.passwd_list[i])
            assert_utils.assert_true(ret, 'Libfabric is not preset on HW. Please check the system')
            assert_utils.assert_not_in(out, b"libfabric",
                                       'Get RPM command Failed, Please check the log')
            logger.info('Checking libfabric version')
            ret, out = system_utils.run_remote_cmd(cmd=commands.LIBFAB_VERSION,
                                                   hostname=self.host_list[i],
                                                   username=self.uname_list[i],
                                                   password=self.passwd_list[i])
            assert_utils.assert_true(ret, 'Libfabric is not preset on HW. Please check the system')
            assert_utils.assert_greater_equal(out, motr_cons.CURR_LIB_VERSION,
                                              'Get Version command Failed, Please check the log')
            logger.info('Checking libfabric tcp protocol presence')
            ret, out = system_utils.run_remote_cmd(cmd=commands.LIBFAB_TCP,
                                                   hostname=self.host_list[i],
                                                   username=self.uname_list[i],
                                                   password=self.passwd_list[i])
            assert_utils.assert_true(ret, 'TCP is not preset on HW. Please check the system')
            assert_utils.assert_not_in(out, b"FI_PROTO_SOCK_TCP",
                                       'TCP command Failed, Please check the log')
            logger.info('Checking libfabric socket protocol presence')
            ret, out = system_utils.run_remote_cmd(cmd=commands.LIBFAB_SOCKET,
                                                   hostname=self.host_list[i],
                                                   username=self.uname_list[i],
                                                   password=self.passwd_list[i])
            assert_utils.assert_true(ret, 'Socket is not preset on HW. Please check the system')
            assert_utils.assert_not_in(out, b"FI_PROTO_SOCK_TCP",
                                       'Socket command Failed, Please check the log')
            logger.info('Checking libfabric verbs protocol presence')
            if self.setuptype == "HW":
                ret, out = system_utils.run_remote_cmd(cmd=commands.LIBFAB_VERBS,
                                                       hostname=self.host_list[i],
                                                       username=self.uname_list[i],
                                                       password=self.passwd_list[i])
                assert_utils.assert_true(ret, 'Verbs is not preset on HW. Please check the system')
                assert_utils.assert_not_in(out, b"FI_PROTO_RXD",
                                           'Verbs command Failed, Please check the log')

    def get_private_if_ip(self):
        """Obtain all private IP from a cluster"""
        privateIP = {}
        for host in self.host_list:
            ret = self.get_cluster_info(host)
            assert_utils.assert_true(ret,
                                     "Not able to Fetch cluster INFO. Please check cluster status")
            endpoint = self.local_endpoint
            ip = endpoint.split("@")
            privateIP[host] = ip[0]
        print("Private IPs of all host is: %s", privateIP)
        return privateIP

    def fi_ping_pong(self):
        """Libfabric pingpong run with different protocol"""
        self.verify_libfabric_version()
        privateIP = self.get_private_if_ip()
        protocols = ["tcp", "socket", "verbs"]
        for protocol in protocols:
            logger.info('Testing ping pong for %s', protocol)
            for i in range(2):
                ret, out = system_utils.run_remote_cmd(cmd=commands.FI_SERVER_CMD.format(protocol),
                                                       hostname=self.host_list[0],
                                                       username=self.uname,
                                                       password=self.passwd)
                assert_utils.assert_true(ret, 'FI Server command Failed, Please check system')
                logger.info('FI Server command Passed, \n Output is: %s \n', out)
                ret, out = system_utils.run_remote_cmd(cmd=commands.FI_CLIENT_CMD.format(privateIP[self.host_list[0]], protocol),
                                                       hostname=self.host_list[i+1],
                                                       username=self.uname,
                                                       password=self.passwd)
                assert_utils.assert_true(ret, 'FI Client command Failed, Please check system')
                logger.info('FI Client command Passed, \n Output is: %s\n', out)
            logger.info('Ping-pong testing of %s PASSED', protocol)



