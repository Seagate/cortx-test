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
    """
    Function main to test
    """
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
    node_list = 3
    while iterate <= node_list:
        randomstr = ''.join(random.choices(string.digits, k=32))
        iterate = iterate+1
        # print("random \n", randomstr)
        unique_id_lst.append(randomstr)

    resp = update_sol_yaml(node_obj_list,
                           node_list, CONF_FILE_PATH,
                           cvg_count=1,
                           data_disk_per_cvg=3)
    print("The updated conf is", resp[1])


def update_sol_yaml(obj: list, node_list: int, filepath,
                    **kwargs):
    """
    This function updates the yaml file
    :Param: obj: list of node object
    :Param: node_list:int the count of node
    :Param: filepath: Filename with complete path
    :Keyword: cluster_id: cluster id
    :Keyword: cvg_count: cvg_count per node
    :Keyword: type_cvg: ios or cas
    :Keyword: data_disk_per_cvg: data disk required per cvg
    :Keyword: sns_data: N
    :Keyword: sns_parity: K
    :Keyword: sns_spare: S
    :Keyword: dix_data:
    :Keyword: dix_parity:
    :Keyword: dix_spare:
    :Keyword: size_metadata: size of metadata disk
    :Keyword: size_data_disk: size of data disk
    :Keyword: skip_disk_count_check: disk count check

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
    size_metadata = kwargs.get("size_metadata", '5Gi')
    size_data_disk = kwargs.get("size_data_disk", '5Gi')
    skip_disk_count_check = kwargs.get("skip_disk_count_check", False)

    data_devices = list()  # empty list for data disk
    metadata_devices_per_cvg = list()  # empty metadata list

    # nks = "{}+{}+{}".format(sns_data, sns_parity, sns_spare)  # Value of N+K+S for sns
    # dix = "{}+{}+{}".format(dix_data, dix_parity, dix_spare)  # Value of N+K+S for dix
    valid_disk_count = sns_spare + sns_data + sns_parity
    for node_count, node_obj in enumerate(obj, start=1):
        print(node_count)
        device_list = node_obj.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                           read_lines=True)[0].split(",")
        device_list[-1] = device_list[-1].replace("\n", "")
        metadata_devices = device_list[0:cvg_count * 2]
        # This will split the metadata disk list
        # into metadata devices per cvg
        # 2 is defined the split size based
        # on disk required for metadata,system
        metadata_devices_per_cvg = [metadata_devices[i:i + 2]
                                    for i in range(0, len(metadata_devices), 2)]
        device_list_len = len(device_list)
        new_device_lst_len = (device_list_len - cvg_count * 2)
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
            while count:
                count = count - 1
                new_end = int(count_end + data_disk_per_cvg)
                if new_end > new_device_lst_len:
                    break
                data_devices_ad = device_list[count_end:new_end]
                count_end = int(count_end + data_disk_per_cvg)
                data_devices.append(data_devices_ad)
        else:
            print("Entered in the else to list data_devices\n")
            data_devices_f = device_list[cvg_count * 2:]
            data_devices = [data_devices_f[i:i + data_disk_per_cvg]
                            for i in range(0, len(data_devices_f), data_disk_per_cvg)]
    # Reading the yaml file
    with open(filepath) as soln:
        conf = yaml.safe_load(soln)
        parent_key = conf['solution']  # Parent key
        node = parent_key['nodes']     # Child Key
        total_nodes = node.keys()
        # Creating Default Schema to update the yaml file
        share_value = "/mnt/fs-local-volume"
        disk_schema = {'device': data_devices[0], 'size': size_metadata}
        meta_disk_schema = {'device': metadata_devices_per_cvg[0][0],
                            'size': size_data_disk}
        data_schema = {'d1': disk_schema}
        vol_schema = {'local': share_value, 'share': share_value}
        device_schema = {'metadata': meta_disk_schema, 'data': data_schema}
        vol_key = {'volumes': vol_schema}
        device_key = {'devices': device_schema}
        key_count = len(total_nodes)
        print("key count \n", key_count, total_nodes)
        # Removing the elements from the node dict
        for key_count in list(total_nodes):
            node.pop(key_count)
        # Updating the node dict
        for item in range(0, node_list):
            dict_node = {}
            name = {'name': "node-{}".format(item+1)}
            dict_node.update(name)
            dict_node.update(vol_key)
            dict_node.update(device_key)
            new_node = {'node{}'.format(item+1): dict_node}
            node.update(new_node)
            # Updating the metadata disk in solution.yaml file
            nname = 'node{}'.format(item + 1)
            devices = node[nname]['devices']
            metadata_schema = {'device': metadata_devices_per_cvg[0][0],
                               'size': size_metadata}
            devices['metadata'].update(metadata_schema)
            data_d = devices['data']
            for per_cvg in range(0, cvg_count):
                for disk in range(0, data_disk_per_cvg):
                    data_disk_device = "d{}".format(disk+1)
                    upd_disk = {data_disk_device: {'device': data_devices[per_cvg][disk],
                                                   'size': size_data_disk}}
                    data_d.update(upd_disk)
        conf['solution']['nodes'] = node
        soln.close()
    noalias_dumper = yaml.dumper.SafeDumper
    noalias_dumper.ignore_aliases = lambda self, data: True
    with open(CONF_FILE_PATH, 'w+') as soln:
        yaml.dump(conf, soln, default_flow_style=False,
                  sort_keys=False, Dumper=noalias_dumper)
        soln.close()
    return True, CONF_FILE_PATH


if __name__ == '__main__':
    main()
