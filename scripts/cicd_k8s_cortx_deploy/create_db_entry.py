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
Create DB entry for Continuous deployment Jenkins Job.
"""
import json
import os
from subprocess import Popen, PIPE

import yaml

def execute_cmd(cmd):
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, error = proc.communicate()
    print("Output = ", str(output))
    print("\nError = ", str(error))
    if proc.returncode != 0:
        return False, str(error)
    return True, str(output)


def create_db_entry(hosts, cfg, admin_user, admin_pswd, nodes_cnt) -> str:
    """
    Create setup entry in Database
    hosts_list: Multiple Hosts string received input from jenkins
    format: hostname=<hostname>,user=<user>,pass=<password>
    return: setup_name :
    """
    print("********Creating DB entry for setup**************")
    with open(cfg["ori_json_file"], 'r') as file:
        json_data = json.load(file)

    host_list = []
    for count, each in enumerate(hosts.split("\n"), start=1):
        host = each.split(",")
        node_type = "worker"
        if count == 1:
            node_type = "master"
        host_1 = f"srvnode-{count}"
        hostname = host[0].split("=")[1]
        username = host[1].split("=")[1]
        password = host[2].split("=")[1]
        host_list.append(
            {"host": host_1, "hostname": hostname, "username": username, "password": password,
             "node_type": node_type})
        if count == int(nodes_cnt)+1:
            break
    if len(host_list) != int(nodes_cnt)+1:
        raise Exception("Mismatch in Hosts and no of worker nodes given")

    setup_name = host_list[0]["hostname"]
    setup_name = f"CICD_Deploy_{setup_name.split('.')[0]}_{len(host_list)-1}"

    json_data["setupname"] = setup_name
    json_data["product_family"] = "LC"
    json_data["product_type"] = "k8s"
    json_data["setup_in_useby"] = "CICD_Deployment"
    json_data["nodes"] = host_list

    json_data["csm"]["mgmt_vip"] = host_list[1]["hostname"]
    json_data["csm"]["port"] = cfg["csm_port"]
    json_data["csm"]["csm_admin_user"].update(username=admin_user, password=admin_pswd)

    print("New Entry Details : ", json_data)
    with open(cfg["new_json_file"], 'w') as file:
        json.dump(json_data, file)
    return setup_name


def main():
    """
    Main Function.
    """
    try:
        hosts = os.getenv("HOSTS")
        admin_user = os.getenv("ADMIN_USER")
        admin_pswd = os.getenv("ADMIN_PASSWORD")
        nodes_cnt = os.getenv("NODES_COUNT")
        cfg = ""
        with open("scripts/cicd_k8s_cortx_deploy/config.yaml") as f1:
            cfg = yaml.safe_load(f1)
        setupname = create_db_entry(hosts, cfg, admin_user, admin_pswd,nodes_cnt)

        print(f"target_name: {setupname}")
        with open("secrets.json", 'r') as file:
            json_data = json.load(file)

        cmd = "python tools/setup_update/setup_entry.py --fpath {} --dbuser {} --dbpassword {}" \
            .format(cfg['new_json_file'], json_data['DB_USER'], json_data['DB_PASSWORD'])
        resp, output = execute_cmd(cmd=cmd)

        if "Entry already exits" in str(output):
            print(f"\nDB already exists for Setupname :{setupname} , Updating it.\n")
            cmd = cmd + " --new_entry False"
            execute_cmd(cmd=cmd)
        print(f"Setup Entry Done with setup name : {setupname}")
        with open("cicd_setup_name.txt", 'w') as file:
            file.write(setupname)
    except Exception as ex:
        print(f"Exception Occured : {ex}")
        exit(1)
    exit(0)

if __name__ == "__main__":
    main()
