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

"""
Utils help to achieve deployment, client setups and test env.
"""
import os
import logging
import json
from typing import List
from urllib.parse import quote_plus
from pymongo import MongoClient
from commons import commands as common_cmd
from commons.helpers.node_helper import Node
from commons.params import DB_HOSTNAME
from commons.params import DB_NAME
from commons.params import SYS_INFO_COLLECTION

LOGGER = logging.getLogger(__name__)


class CreateSetupJson:
    """
    Setup entry creation in db
    """

    def __init__(self, hosts, node_pass):
        self.hosts = hosts
        self.repr_object = dict()
        self.node_pass = node_pass
        self.nd_obj_host = Node(hostname=hosts[0], username='root',
                                password=node_pass)
        remote_path = "/opt/seagate/cortx_configs/provisioner_cluster.json"
        local_path = os.path.join(os.getcwd() + "/provisioner_cluster.json")
        self.nd_obj_host.copy_file_to_local(remote_path=remote_path, local_path=local_path)
        with open('provisioner_cluster.json') as json_file:
            self.data = json.load(json_file)
        data = self.data["cluster"][list(self.data["cluster"].keys())[0]]
        m_vip = str(data['network']['management']['virtual_host'])
        self.m_ip = m_vip.strip()
        # Get required ips
        required_ips = 3
        self.num_nodes = len(hosts)
        self.srvnode_ips = [None] * self.num_nodes * required_ips
        output = self.nd_obj_host.execute_cmd(common_cmd.CMD_HOSTS, read_lines=True)
        for line in output:
            for host_num in range(len(hosts)):
                search_string = "srvnode-{}.mgmt.public".format(host_num + 1)
                if search_string in line:
                    self.srvnode_ips[host_num * required_ips] = line.split()[0]
                search_string = "srvnode-{}.data.public".format(host_num + 1)
                if search_string in line:
                    self.srvnode_ips[(host_num * required_ips) + 1] = line.split()[0]
                search_string = "srvnode-{}.data.private".format(host_num + 1)
                if search_string in line:
                    self.srvnode_ips[(host_num * required_ips) + 2] = line.split()[0]

    def create_setup_entry(self, target_name, setup_type, csm_user, csm_pass):
        """
        Populate all setup entry data
        """
        target_setup = dict()
        nodes = list()
        target_setup.update(dict(setupname=target_name,
                                 setup_type=setup_type,
                                 setup_in_useby="",
                                 in_use_for_parallel=False,
                                 parallel_client_cnt=0,
                                 is_setup_free=True,
                                 lb=""))
        for host_number, host in enumerate(self.hosts):
            node_details = self.add_nodes_details(host_number, host)
            nodes.append(node_details)
        target_setup.update({'nodes': nodes})
        target_setup.update({'enclosure': self.add_enclosure_details()})
        target_setup.update({'pdu': self.add_pdu_details()})
        target_setup.update({'gem_controller': self.add_gem_controller_details()})
        target_setup.update({'ldap': self.add_ldap_details()})
        target_setup.update({'bmc': self.add_bmc_details()})
        target_setup.update({'csm': self.add_csm_details(csm_user, csm_pass)})
        target_setup.update({'s3': self.add_s3_details()})
        LOGGER.debug("Setup entry %s created for target %s", target_setup, target_name)
        return target_setup

    def add_nodes_details(self, host_number, node):
        """
        Add node details in setup entry
        """
        return dict(
            host="srvnode-" + str(host_number),
            hostname=node,
            ip=self.srvnode_ips[host_number * self.num_nodes],
            username='root',
            password=self.node_pass,
            public_data_ip=self.srvnode_ips[(host_number * self.num_nodes) + 1],
            private_data_ip=self.srvnode_ips[(host_number * self.num_nodes) + 2],
            ldpu=dict(ip="", port="", user="", pwd=self.node_pass),
            rpdu=dict(ip="", port="", user="", pwd=self.node_pass),
            encl_lpdu=dict(ip="", port="", user="", pwd=self.node_pass),
            encl_rpdu=dict(ip="", port="", user="", pwd=self.node_pass),
            gem_controller=dict(ip="", user="", pwd=self.node_pass, port1="", port2=""))

    @staticmethod
    def add_enclosure_details():
        """
        Add enclosure details in setup entry
        """
        return dict(primary_enclosure_ip="10.0.0.2",
                    secondary_enclosure_ip="10.0.0.3",
                    enclosure_user="",
                    enclosure_pwd=""
                    )

    @staticmethod
    def add_pdu_details():
        """
        Add pdu details in setup entry
        """
        return dict(
            ip="",
            username="",
            password="",
            power_on="on",
            power_off="off",
            sleep_time=120
        )

    @staticmethod
    def add_gem_controller_details():
        """
        Add gem details in setup entry
        """
        return dict(
            ip="",
            username="",
            password="",
            port1="9012",
            port2="9014")

    @staticmethod
    def add_bmc_details():
        """
        Add bmc details in setup entry
        """
        return dict(username="",
                    password="")

    # pylint: disable=broad-except
    def add_ldap_details(self):
        """
        Add ldap details in setup entry
        """
        ldap_value = ''
        try:
            sgiam_secret = self.data['cortx']['software']['openldap']['sgiam']['secret']
            cmd = common_cmd.CMD_GET_S3CIPHER_CONST_KEY
            resp1 = self.nd_obj_host.execute_cmd(cmd, read_lines=True)
            key = resp1[0]
            key = key.strip('\n')
            cmd = common_cmd.CMD_DECRYPT_S3CIPHER_CONST_KEY.format(key, sgiam_secret)
            resp1 = self.nd_obj_host.execute_cmd(cmd, read_lines=True)
            ldap_value = resp1[0]
            ldap_value = ldap_value.strip('\n')
        except Exception as error:
            LOGGER.debug("Error in getting ldap credentials %s", error)
        return dict(username="sgiamadmin",
                    password=ldap_value,
                    sspl_pass=ldap_value)

    def add_csm_details(self, csm_user, csm_pass):
        """
        Add csm details in setup entry
        """
        return dict(mgmt_vip=self.m_ip,
                    csm_admin_user=dict(username=csm_user,
                                        password=csm_pass)
                    )

    def add_s3_details(self):
        """
        Add s3 details in setup entry
        """
        return dict(s3_server_ip=self.m_ip,
                    s3_server_user=dict(username='root',
                                        password=self.node_pass))


def register_setup_entry(hosts: List, setupname, csm_user, csm_pass, node_pass):
    """
    Add setup entry in db
    """
    setup_json_obj = CreateSetupJson(hosts, node_pass)
    setup_json = setup_json_obj.create_setup_entry(setupname, 'VM', csm_user, csm_pass)
    setup_query = {"setupname": setup_json['setupname']}
    uri = "mongodb://{0}:{1}@{2}".format(quote_plus(os.environ.get('DB_USER')),
                                         quote_plus(os.environ.get('DB_PASSWORD')), DB_HOSTNAME)
    client = MongoClient(uri)
    collection_obj = client[DB_NAME][SYS_INFO_COLLECTION]
    LOGGER.debug("Collection obj for DB interaction %s", collection_obj)
    LOGGER.debug("Setup query : %s", setup_query)
    entry_exist = collection_obj.find(setup_query).count()
    if not entry_exist:
        collection_obj.insert_one(setup_json)
        LOGGER.info("Setup Data is inserted successfully")
    else:
        collection_obj.update_one(setup_query, {'$set': setup_json})
        LOGGER.debug("Setup Data is updated successfully")
    setup_details = collection_obj.find_one(setup_query)
    return setup_details
