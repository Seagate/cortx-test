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
#

"""
Utils help to achieve deployment, client setups and test env.
"""
import os
import logging
from typing import List
from urllib.parse import quote_plus
from pymongo import MongoClient
from commons.params import DB_HOSTNAME
from commons.params import DB_NAME
from commons.params import SYS_INFO_COLLECTION


LOGGER = logging.getLogger(__name__)


class CreateSetupJson:

    def __init__(self, hosts: List):
        self.hosts = hosts
        self.repr_object = dict()

    def create_setup_entry(self, target_name, setup_type='VM'):
        target_setup = dict()
        enc = dict()
        pdu = dict()
        nodes = list()
        gc = dict()
        ldap = dict()
        bmc = list()
        csm = list()
        target_setup.update(dict(setupname=target_name,
                                 setup_type=setup_type,
                                 setup_in_useby="",
                                 in_use_for_parallel=False,
                                 parallel_client_cnt=0,
                                 is_setup_free=True))
        for host in self.hosts:
            nodes.append(self._add_nodes_details(host))
        target_setup.update({'nodes': nodes})
        target_setup.update({'enclosure': self.add_enclosure_details(enc)})
        target_setup.update({'pdu': self.add_pdu_details(pdu)})
        target_setup.update({'gem_controller': self.add_gem_controller_details(gc)})
        target_setup.update({'ldap': self.add_ldap_details(ldap)})
        target_setup.update({'bmc': self.add_bmc_details(bmc)})
        target_setup.update({'csm': self.add_csm_details(csm)})
        LOGGER.debug("Setup entry %s created for target %s", target_setup, target_name)
        return target_setup

    def _add_nodes_details(self, node):
        return dict(
            host="srv-node-0",
            hostname="node 0 hostname",
            ip="node 0 ip",
            username="node 0 username",
            password="node 0 password",
            public_data_ip="",
            private_data_ip="",
            mgmt_ip=""
        )

    def add_enclosure_details(self, enc):
        return dict(primary_enclosure_ip="10.0.0.2",
                    secondary_enclosure_ip="10.0.0.3",
                    enclosure_user="",
                    enclosure_pwd=""
                    )

    def add_pdu_details(self, pdu):
        return dict(
            ip="",
            username="",
            password="",
            power_on="on",
            power_off="off",
            sleep_time=120
        )

    def add_gem_controller_details(self, con):
        return dict(
            ip="",
            username="",
            password="",
            port1="9012",
            port2="9014")

    def add_bmc_details(self, bmc):
        return dict(username="",
                    password="")

    def add_ldap_details(self, ldap):
        return dict(username="",
                    password="",
                    sspl_pass="")

    def add_csm_details(self, csm):
        return dict(mgmt_vip="",
                    csm_admin_user=dict(username="",
                                        password="")
                    )


def register_setup_entry(hosts: List, new_entry=True):
    setup_json = CreateSetupJson(hosts)
    DBUSER = os.environ.get('DB_USER')
    DBPSWD = os.environ.get('DB_PASSWORD')
    setupname = setup_json['setupname']
    setup_query = {"setupname": setupname}
    mongodburi = "mongodb://{0}:{1}@{2}"
    uri = mongodburi.format(quote_plus(DBUSER), quote_plus(DBPSWD), DB_HOSTNAME)
    client = MongoClient(uri)
    setup_db = client[DB_NAME]
    collection_obj = setup_db[SYS_INFO_COLLECTION]
    LOGGER.debug("Collection obj for DB interaction %s", collection_obj)
    LOGGER.debug("Setup query : %s", setup_query)
    entry_exist = collection_obj.find(setup_query).count()
    if new_entry and entry_exist:
        LOGGER.error("%s already exists", setup_query)
    elif new_entry and not entry_exist:
        rdata = collection_obj.insert_one(setup_json)
        LOGGER.info("Setup Data is inserted successfully")
    else:
        rdata = collection_obj.update_one(setup_query, {'$set': setup_json})
        LOGGER.debug("Setup Data is updated successfully")
    setup_details = collection_obj.find_one(setup_query)
    return setup_details
