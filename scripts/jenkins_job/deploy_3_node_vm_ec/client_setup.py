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
Setup file client configuration for executing the Failure domain testcases
"""
import os
import configparser
import json
import logging
import argparse
from scripts.jenkins_job import client_conf
from commons.helpers.node_helper import Node

config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
LOGGER = logging.getLogger(__name__)

config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
LOGGER = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Multinode server and client configuration for executing the R2 regression")
    parser.add_argument("nodes", help="hostnames for each node", nargs="+")
    parser.add_argument("--node_count", help="Number of nodes in cluster", required=True, type=int)
    parser.add_argument("--password", help="password for nodes", required=True)
    parser.add_argument("--mgmt_vip", help="csm mgmt vip", required=True)
    args = parser.parse_args()
    nodes = args.nodes
    node_count = args.node_count
    assert len(nodes) == node_count, "Number of nodes provided does not match with node_count"
    username = "root"

    nd_obj_host = Node(
        hostname=nodes[0],
        username=username,
        password=args.password)

    remote_crt_path = config['default']['s3_crt_path']
    local_crt_path = config['default']['s3_crt_local']
    client_conf.run_cmd("mkdir -p {}".format(os.path.dirname(local_crt_path)))
    if os.path.exists(local_crt_path):
        client_conf.run_cmd("rm -f {}".format(local_crt_path))
    nd_obj_host.copy_file_to_local(
        remote_path=remote_crt_path,
        local_path=local_crt_path)
    client_conf.setup_chrome()
    print("Client Setup Done!!")

if __name__ == "__main__":
    main()
