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
Script to Update the cluster/config yaml files
"""

import random
import string

import yaml

from commons import commands as common_cmd
from commons.helpers.pods_helper import LogicalNode

CONF_FILE_PATH = "scripts/k8s_cluster_setup/solution.yaml"


def main():
    hosts = ["ssc-vm-g3-rhev4-1300.colo.seagate.com"]
    uname = "root"
    passwd = "seagate"
    node_obj_list = []
    unique_id_lst = []
    iterate = 0
    for node in hosts:
        nd_obj = LogicalNode(hostname=node, username=uname,
                             password=passwd)
        node_obj_list.append(nd_obj)
    node_list = 5
    while iterate <= node_list:
        randomstr = ''.join(random.choices(string.digits, k=32))
        iterate = iterate+1
        print("random \n", randomstr)
        unique_id_lst.append(randomstr)

    update_yaml(node_obj_list, node_list, CONF_FILE_PATH,
                cvg_count=1,
                data_disk_per_cvg=3)

    print("The updated conf is", CONF_FILE_PATH)


def update_yaml(obj: list, node_list: int, filepath,
                **kwargs):
    """
    This function updates the yaml file
    :Param: obj Its the list of node object
    :Param:  Its the list of node object

    """
    # cluster_id = kwargs.get("cluster_id", 1)
    cvg_count = kwargs.get("cvg_count", 1)
    # type_cvg = kwargs.get("type_cvg", "cas")
    data_disk_per_cvg = kwargs.get("data_disk_per_cvg", "0")
    sns_data = kwargs.get("sns_data", 1)
    sns_parity = kwargs.get("sns_parity", 0)
    sns_spare = kwargs.get("sns_spare", 0)
    # dix_data = kwargs.get("dix_data", 1)
    # dix_parity = kwargs.get("dix_parity", 2)
    # dix_spare = kwargs.get("dix_spare", 0)
    skip_disk_count_check = kwargs.get("skip_disk_count_check", False)

    data_devices = list()  # empty list for data disk
    metadata_devices_per_cvg = list()  # empty metadata list

    # nks = "{}+{}+{}".format(sns_data, sns_parity, sns_spare)  # Value of N+K+S for sns
    # dix = "{}+{}+{}".format(dix_data, dix_parity, dix_spare)  # Value of N+K+S for dix
    valid_disk_count = sns_spare + sns_data + sns_parity
    for node_count, node_obj in enumerate(obj, start=1):
        device_list = node_obj.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                           read_lines=True)[0].split(",")
        device_list[-1] = device_list[-1].replace("\n", "")
        metadata_devices = device_list[0:cvg_count * 2]
        # This will split the metadata disk list into metadata devices per cvg
        # 2 is defined the split size based on disk required for metadata,system
        metadata_devices_per_cvg = [metadata_devices[i:i + 2] for i in range(0, len(metadata_devices), 2)]
        device_list_len = len(device_list)
        new_device_lst_len = (device_list_len - cvg_count * 2)
        print("new disk len is ", new_device_lst_len)
        count = cvg_count
        if data_disk_per_cvg == "0":
            data_disk_per_cvg = len(device_list[cvg_count * 2:])
        # The condition to validate the config.
        if not skip_disk_count_check and valid_disk_count > \
                (data_disk_per_cvg * cvg_count * node_list):
            return False, "The sum of data disks per cvg " \
                          "is less than N+K+S count"
        # This condition validated the total available disk count
        # and split the disks per cvg.
        if (data_disk_per_cvg * cvg_count) < new_device_lst_len and data_disk_per_cvg != "0":
            count_end = int(data_disk_per_cvg + cvg_count * 2)
            data_devices.append(device_list[cvg_count * 2:count_end])
            print("Entered in loop", data_devices)
            print("count end in loop", count_end)
            while count:
                count = count - 1
                new_end = int(count_end + data_disk_per_cvg)
                print("new count end in loop", new_end)
                if new_end > new_device_lst_len:
                    break
                print("new count end after break ", new_end)
                data_devices_ad = device_list[count_end:new_end]
                count_end = int(count_end + data_disk_per_cvg)
                print(" 2 count end in loop", count_end)
                data_devices.append(data_devices_ad)
                print("Final data devices\n", data_devices)
        else:
            print("Entered in the else to list data_devices\n")
            data_devices_f = device_list[cvg_count * 2:]
            data_devices = [data_devices_f[i:i + data_disk_per_cvg]
                            for i in range(0, len(data_devices_f), data_disk_per_cvg)]

        print("The disk list is \n", data_devices)
    with open(filepath) as f:
        conf = yaml.safe_load(f)
    print(type(conf['solution']))
    parent_key = conf['solution']

    # common = parent_key['common']
    node = parent_key['nodes']
    print("node ", type(node))
    total_nodes_sol = len(node.keys())
    share_value = "/mnt/fs-local-volume"
    # print("The key is ", total_nodes_sol)
    data = {'d1': '', 'd2': ''}
    vol = {'local': share_value, 'share': share_value}
    device = {'system': '/dev/sdb', 'metadata': '/dev/sdc', 'data': data}
    vol_key = {'volumes': vol}
    device_key = {'devices': device}
    dict_node = {}
    print("Before ", node)
    if node_list > 4:
        # print("Enter in node addition\n")
        for nodes in range(5, node_list+1):
            name = {'name': "node-{}".format(nodes)}
            new_node = {'node{}'.format(nodes): ''}
            dict_node.update(name)
            dict_node.update(vol_key)
            dict_node.update(device_key)
            print(dict_node)
            new_node['node{}'.format(nodes)] = dict_node  # assigning the value to the dict
            print(new_node)
            node.update(new_node)
        print("After", node)

    for item in range(0, node_list):
        nn = 'node{}'.format(item + 1)
        devices = node[nn]['devices']
        if node_list in (1, 2, 3):   # This statement make sure to remove additional entries in the sol .yaml file
            for node_req in range(node_list, total_nodes_sol):
                node_c = "node{}".format(node_req+1)
                node.pop(node_c)
        print("the device dict is ", devices)
        # Updating the metadata , system disk in solution.yaml file
        print("Before d", devices['system'])
        devices['system'] = metadata_devices_per_cvg[0][1]
        devices['metadata'] = metadata_devices_per_cvg[0][0]
        print("After d", devices['system'])
        data_d = devices['data']
        print("the data d is ", data_d)

        if data_disk_per_cvg < 2:
            data_d.pop('d2')  # removing the additional disk if data per disk is < 2
            data_d['d1'] = data_devices[0]
        else:
            print("Data devices list is \n", data_disk_per_cvg)
            # for loop for adding multiple data disks
            for per_cvg in range(0, cvg_count):
                for disk in range(0, data_disk_per_cvg):
                    print("the disk per", data_devices[per_cvg][disk])
                    data_d["d{}".format(disk+1)] = data_devices[per_cvg][disk]
    # End of for loop
    print("The final update dict is \n", node)

    with open(filepath, 'w') as f:
        yaml.safe_dump(conf, f, sort_keys=False)


if __name__ == '__main__':
    main()
