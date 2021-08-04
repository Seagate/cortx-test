"""
Utility Class for target locking using DB
"""
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
# -*- coding: utf-8 -*-

import logging
from urllib.parse import quote_plus
from pymongo import MongoClient
from core import runner
from commons.helpers.health_helper import Health

LOGGER = logging.getLogger(__name__)

DB_HOSTNAME = """cftic1.pun.seagate.com:27017,
cftic2.pun.seagate.com:27017,
apollojenkins.pun.seagate.com:27017/
?authSource=cft_test_results&replicaSet=rs0"""
DB_NAME = "cft_test_results"
SYS_INFO_COLLECTION = "r2_systems"


class HealthCheck:
    """
    Health check for all node
    And add health status in mongodb
    """

    def __init__(self):
        self.db_user, self.db_password = runner.get_db_credential()

    def get_setup_details(self, targets):
        """
            Fetch target details from database
            :return: target_dict {setupname : nodes[]}
        """
        target_dict = {}
        mongodburi = "mongodb://{0}:{1}@{2}"
        uri = mongodburi.format(quote_plus(self.db_user), quote_plus(self.db_password), DB_HOSTNAME)
        client = MongoClient(uri)
        setup_db = client[DB_NAME]
        collection_obj = setup_db[SYS_INFO_COLLECTION]
        for target in targets:
            setup_query = {"setupname": target}
            entry_exist = collection_obj.find(setup_query).count()
            if entry_exist == 1:
                setup_details = collection_obj.find_one(setup_query)
                setup_nodes = setup_details['nodes']
                nodes = []
                for node in setup_nodes:
                    nodes.append(node)
                target_dict[target] = nodes
            else:
                LOGGER.error("Target %s details are not found in database", target)
        return target_dict

    def update_health_status(self,target_status_dict):
        """
            Update target health status True/False
            "is_setup_healthy" : True/False
        """
        mongodburi = "mongodb://{0}:{1}@{2}"
        uri = mongodburi.format(quote_plus(self.db_user), quote_plus(self.db_password), DB_HOSTNAME)
        client = MongoClient(uri)
        setup_db = client[DB_NAME]
        collection_obj = setup_db[SYS_INFO_COLLECTION]
        for setupname in target_status_dict:
            setup_query = {"setupname": setupname}
            entry_exist = collection_obj.find(setup_query).count()
            if entry_exist == 1:
                setup_details = collection_obj.find_one(setup_query)
                setup_details["is_setup_healthy"] = target_status_dict[setupname]
                collection_obj.update_one(setup_query, {'$set': setup_details})
                LOGGER.info("Updated health status for target %s", setupname)

    @staticmethod
    def check_cortx_cluster_health(node):
        """
            check target node health status
            :return True/False
        """
        hostname = node['hostname']
        health = Health(hostname=hostname,
                        username=node['username'],
                        password=node['password'])
        result = True
        try:
            result = health.check_node_health(node)
        except:
            result = False
        finally:
            health.disconnect()
        return result

    @staticmethod
    def check_cluster_storage(node):
        """
            check target storage status
            :return True/False
        """

        hostname = node['hostname']
        health = Health(hostname=hostname,
                        username=node['username'],
                        password=node['password'])
        try:
            ha_total, ha_avail, ha_used = health.get_sys_capacity()
            ha_used_percent = round((ha_used / ha_total) * 100, 1)
            result = ha_used_percent < 98.0
        except:
            result = False
        finally:
            health.disconnect()
        return result

    def health_check(self, targets):
        """
            accept targets
            trigger health functions
            pass on health status to update function
            :return target_dict {setupname : True/False}
        """
        target_dict = self.get_setup_details(targets)
        target_status_dict = {}
        for setupname in target_dict:
            nodes = target_dict[setupname]
            for node in nodes:
                health_result = self.check_cortx_cluster_health(node)
                storage_result = self.check_cluster_storage(node)
                if health_result and storage_result:
                    target_status_dict[setupname] = True
                else:
                    target_status_dict[setupname] = False
                    LOGGER.info("Health check failed for %s of target %s", node['host'], setupname)
                    break
        self.update_health_status(target_status_dict)
