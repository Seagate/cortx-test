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
Utility Class for health status check and update to database
"""


import logging
from urllib.parse import quote_plus
from pymongo import MongoClient
from commons.helpers.health_helper import Health
from commons.params import DB_HOSTNAME
from commons.params import DB_NAME
from commons.params import SYS_INFO_COLLECTION

LOGGER = logging.getLogger(__name__)


class HealthCheck:

    """
    Health check for all node
    And add health status in mongodb
    """

    def __init__(self, credentials):
        self.db_user, self.db_password = credentials

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
                target_dict[target] = setup_details
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
            setup = target_dict[setupname]
            if not setup["is_setup_free"] and not setup["in_use_for_parallel"]:
                continue
            if not setup["is_setup_free"] and setup["in_use_for_parallel"]:
                if not setup["setup_in_useby"] == "":
                    continue
            nodes = setup["nodes"]
            for node in nodes:
                result = Health.check_cortx_cluster_health(node)
                if result:
                    target_status_dict[setupname] = True
                else:
                    target_status_dict[setupname] = False
                    LOGGER.info("Health check failed for %s of %s", node['host'], setupname)
                    break
        self.update_health_status(target_status_dict)
