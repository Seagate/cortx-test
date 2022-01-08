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
import sys
from subprocess import Popen, PIPE

import yaml
from word2number import w2n
from commons.utils import jira_utils


def execute_cmd(cmd) -> tuple:
    """
    Execute Command
    param: cmd : Command to be executed.
    return: Boolean, output/error
    """
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, error = proc.communicate()
    print("Output = ", str(output))
    print("\nError = ", str(error))
    if proc.returncode != 0:
        return False, str(error)
    return True, str(output)


# pylint: disable-msg=too-many-locals
def create_db_entry(hosts, cfg, admin_user, admin_pswd, nodes_cnt) -> str:
    """
    Create setup entry in Database
    hosts: Multiple Hosts string received input from jenkins
           (format: hostname=<hostname>,user=<user>,pass=<password>)
    cfg: Config file for create db entry
    admin_user : Admin username for CSM admin
    admin_pswd: Admin Password for CSM admin
    nodes_cnt: Number of Nodes to be used for db_entry from the hosts pool.
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
        if count == int(nodes_cnt) + 1:
            break
    if len(host_list) != int(nodes_cnt) + 1:
        raise Exception("Mismatch in Hosts and no of worker nodes given")

    setup_name = host_list[0]["hostname"]
    setup_name = f"CICD_Deploy_{setup_name.split('.')[0]}_{len(host_list) - 1}"

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


# pylint: disable=broad-except
def main():
    """
    Main Function.
    """
    try:
        # hosts = os.getenv("HOSTS")
        admin_user = os.getenv("ADMIN_USER")
        admin_pswd = os.getenv("ADMIN_PASSWORD")
        te = os.getenv("TEST_EXECUTION_NUMBER")
        if te is not None:
            jira_obj = jira_utils.JiraTask(admin_user, admin_pswd)
            te_details = jira_obj.get_issue_details(te)
            test_env = te_details.fields.customfield_21006
            print("te details are:\n ", test_env)
            nodes_cnt = w2n.word_to_num(test_env[-1].split("_")[0])
            print("te details are:\n ", nodes_cnt)
        else:
            nodes_cnt = os.getenv("NODES_COUNT")
            print(nodes_cnt)
        cfg = ""
        with open("scripts/cicd_k8s_cortx_deploy/config.yaml") as file:
            cfg = yaml.safe_load(file)
        setupname = create_db_entry(hosts, cfg, admin_user, admin_pswd, nodes_cnt)

        print(f"target_name: {setupname}")
        with open("secrets.json", 'r') as file:
            json_data = json.load(file)

        cmd = "python tools/setup_update/setup_entry.py --fpath {} --dbuser {} --dbpassword {}" \
            .format(cfg['new_json_file'], json_data['DB_USER'], json_data['DB_PASSWORD'])
        resp, output = execute_cmd(cmd=cmd)
        print("resp :", resp)
        if not resp:
            raise Exception("Error during adding db entry")

        if "Entry already exits" in str(output):
            print(f"\nDB already exists for Setupname :{setupname} , Updating it.\n")
            cmd = cmd + " --new_entry False"
            execute_cmd(cmd=cmd)
        print(f"Setup Entry Done with setup name : {setupname}")
        with open("cicd_setup_name.txt", 'w') as file:
            file.write(setupname+"-"+te)

    except Exception as ex:
        print(f"Exception Occured : {ex}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
