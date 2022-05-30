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
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG

logger = logging.getLogger(__name__)


# pylint:disable=too-many-public-methods
# pylint:disable=too-many-instance-attributes
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
        self.endpoints = {}
        self.client_index = 0
        self.host_list = []
        self.uname_list = []
        self.passwd_list = []
        self.parse_funcs = {
                            "m0crate": self.m0crate_parse_func,
                            "m0": self.m0_parse_func,
                            "m0kv": self.m0kv_parse_func,
                            "other": self.__other_parse_func,
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

    @staticmethod
    def __get_max_client_index(my_svcs_info):
        """To calculate motr client number"""
        count = 0
        for temp in my_svcs_info:
            if temp["name"] == "m0_client":
                count = count + 1
        return count - 1

    @staticmethod
    def __is_localhost(hostname: str) -> bool:
        """To Check provided host is local host or not"""
        name = CMN_CFG["nodes"][0]["hostname"]
        temp = hostname in ('localhost', '127.0.0.1', name, f'{name}.local')
        return temp

    def get_svcs_info(self, nodes_data, srvnode):
        """Extract node svcs data from complete cluster data"""
        for node in nodes_data:
            nodename = node["name"]
            nodename = nodename.split(".")[0]
            if nodename.startswith("srvnode") is True:
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
        return my_svcs_info

    def get_cluster_info(self, hostname):
        """Get cluster related info like endpoints, fids"""
        srvnode = self.host_list[0]
        if hostname:
            srvnode = hostname

        cmd = f'ssh {srvnode} hctl status --json'
        self.cluster_info = json.loads(self.utils_obj.execute_cmd(cmd))
        if self.cluster_info is not None:
            self.profile_fid = self.cluster_info["profiles"][0]
            self.profile_fid = self.profile_fid["fid"]
            nodes_data = self.cluster_info["nodes"]
            my_svcs_info = self.get_svcs_info(nodes_data, srvnode)
            if self.client_index < 0:
                print("User provided client index = {}".format(self.client_index))
                print("Setting user client index to 0(default)")
                self.client_index = 0
            else:
                max_client_index = self.__get_max_client_index(my_svcs_info)
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

    @staticmethod
    def __get_workload_file_name(params):
        """To fetch workload file name from params"""
        params_list = params.split()
        workload_file = params_list[1].split('/')[-1]
        return workload_file

    def delete_remote_files(self):
        """Delete files from remote machine"""
        if self.files_to_delete:
            for file in self.files_to_delete:
                logger.debug('Deleting file %s from node', file)
                result = self.utils_obj.remove_file(file)
                logger.debug(result)

    def update_workload_file(self, fname):
        """Update endpoints and fids in workload files"""
        ret = self.get_cluster_info(self.host_list[0])
        assert_utils.assert_true(ret, "Not able to Fetch cluster INFO. Please check cluster status")

        f_str = "s/^\([[:space:]]*MOTR_LOCAL_ADDR: *\).*/\\1\"{}\"/""".format(self.local_endpoint)
        cmd = "sed -i \"{}\" {}".format(f_str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

        f_str = "s/^\([[:space:]]*MOTR_HA_ADDR: *\).*/\\1\"{}\"/".format(self.ha_endpoint)
        cmd = "sed -i \"{}\" {}".format(f_str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

        f_str = "s/^\([[:space:]]*PROF: *\).*/\\1\"{}\"/".format(self.profile_fid)
        cmd = "sed -i \"{}\" {}".format(f_str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

        f_str = "s/^\([[:space:]]*PROCESS_FID: *\).*/\\1\"{}\"/".format(self.process_fid)
        cmd = "sed -i \"{}\" {}".format(f_str, fname)
        ret = os.system(cmd)
        assert_utils.assert_equal(ret, 0)

    def m0crate_parse_func(self, cmd_dict):
        """m0crate parse function"""
        workload_file = self.__get_workload_file_name(cmd_dict['params'])
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

    @staticmethod
    def __other_parse_func(cmd_dict):
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
        self.endpoints["l"] = self.local_endpoint
        self.endpoints["H"] = self.ha_endpoint
        self.endpoints["P"] = self.process_fid
        self.endpoints["p"] = self.profile_fid
        return self.endpoints

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
        private_ip = {}
        for host in self.host_list:
            ret = self.get_cluster_info(host)
            assert_utils.assert_true(ret,
                                     "Not able to Fetch cluster INFO. Please check cluster status")
            endpoint = self.local_endpoint
            ip_add = endpoint.split("@")
            private_ip[host] = ip_add[0]
        print("Private IPs of all host is: %s", private_ip)
        return private_ip

    def fi_ping_pong(self):
        """Libfabric pingpong run with different protocol"""
        self.verify_libfabric_version()
        private_ip = self.get_private_if_ip()
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
                ret, out = system_utils.run_remote_cmd(
                    cmd=commands.FI_CLIENT_CMD.format(private_ip[self.host_list[0]], protocol),
                    hostname=self.host_list[i+1],
                    username=self.uname,
                    password=self.passwd)
                assert_utils.assert_true(ret, 'FI Client command Failed, Please check system')
                logger.info('FI Client command Passed, \n Output is: %s\n', out)
            logger.info('Ping-pong testing of %s PASSED', protocol)

    def dd_cmd(self, b_size, count, file, node_num):
        """DD command for creating new file"""
        cmd = commands.CREATE_FILE.format("/dev/urandom", file, b_size, count)
        if node_num is None:
            node_num = 0
        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd,
                                                                      self.host_list[node_num],
                                                                      self.uname_list[node_num],
                                                                      self.passwd_list[node_num])
        logger.info("%s , %s", result, error1)
        if ret:
            logger.info('"%s" Failed, Please check the log', cmd)
            assert False
        if (b"ERROR" or b"Error") in error1:
            logger.error('"%s" failed, please check the log', cmd)
            assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')

    # pylint: disable=too-many-arguments
    def cp_cmd(self, b_size, count, obj, layout, file, node_num):
        """M0CP command creation"""
        if node_num is None:
            node_num = 0
        endpoints = self.get_endpoints(self.host_list[node_num])
        cmd = commands.M0CP.format(endpoints["l"], endpoints["H"], endpoints["P"],
                                   endpoints["p"], b_size.lower(), count, obj, layout, file)
        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd,
                                                                      self.host_list[node_num],
                                                                      self.uname_list[node_num],
                                                                      self.passwd_list[node_num])
        logger.info("%s , %s", result, error1)
        if ret:
            logger.info('"%s" Failed, Please check the log', cmd)
            assert False
        if (b"ERROR" or b"Error") in error1:
            logger.error('"%s" failed, please check the log', cmd)
            assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')

    # pylint: disable=too-many-arguments
    def cat_cmd(self, b_size, count, obj, layout, file, node_num):
        """M0CAT command creation"""
        if node_num is None:
            node_num = 0
        endpoints = self.get_endpoints(self.host_list[node_num])
        cmd = commands.M0CAT.format(endpoints["l"], endpoints["H"], endpoints["P"],
                                    endpoints["p"], b_size.lower(), count, obj, layout, file)
        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd,
                                                                      self.host_list[node_num],
                                                                      self.uname_list[node_num],
                                                                      self.passwd_list[node_num])
        logger.info("%s , %s", result, error1)
        if ret:
            logger.info('"%s" Failed, Please check the log', cmd)
            assert False
        if (b"ERROR" or b"Error") in error1:
            logger.error('"%s" failed, please check the log', cmd)
            assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')

    def unlink_cmd(self, obj, layout, node_num):
        """M0UNLINK command creation"""
        if node_num is None:
            node_num = 0
        endpoints = self.get_endpoints(self.host_list[node_num])
        cmd = commands.M0UNLINK.format(endpoints["l"], endpoints["H"], endpoints["P"],
                                       endpoints["p"], obj, layout)
        result, error1, ret = system_utils.run_remote_cmd_wo_decision(cmd,
                                                                      self.host_list[node_num],
                                                                      self.uname_list[node_num],
                                                                      self.passwd_list[node_num])
        logger.info("%s , %s", result, error1)
        if ret:
            logger.info('"%s" Failed, Please check the log', cmd)
            assert False
        if (b"ERROR" or b"Error") in error1:
            logger.error('"%s" failed, please check the log', cmd)
            assert_utils.assert_not_in(error1, b"ERROR" or b"Error",
                                       f'"{cmd}" Failed, Please check the log')

    def diff_cmd(self, file1, file2, node_num):
        """DIFF command creation"""
        if node_num is None:
            node_num = 0
        cmd = commands.DIFF.format(file1, file2)
        ret, result = system_utils.run_remote_cmd(cmd, self.host_list[node_num],
                                                  self.uname_list[node_num],
                                                  self.passwd_list[node_num])
        logger.info("%s", result)
        assert_utils.assert_true(ret, f'"{cmd}" Failed, Please check the log')

    def md5sum_cmd(self, file1, file2, node_num):
        """MD5SUM command creation"""
        if node_num is None:
            node_num = 0
        cmd = commands.MD5SUM.format(file1, file2)
        ret, result = system_utils.run_remote_cmd(cmd, self.host_list[node_num],
                                                  self.uname_list[node_num],
                                                  self.passwd_list[node_num])
        logger.info("%s", result)
        assert_utils.assert_true(ret, f'"{cmd}" Failed, Please check the log')
