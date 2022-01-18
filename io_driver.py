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

import logging

from config import CMN_CFG
from commons.helpers.health_helper import Health


LOGGER = logging.getLogger(__name__)


def check_cluster_services():
    """Check the cluster services."""
    LOGGER.info("Check cluster status for all nodes.")
    nodes, CH_FLG = CMN_CFG["nodes"], True
    try:
        for node in nodes:
            if node.get("node_type", None).lower() != "master":
                continue
            hostname = node['hostname']
            health = Health(hostname=hostname, username=node['username'], password=node['password'])
            result = health.check_node_health()
            if not result[0]:
                LOGGER.critical(
                    'Cluster Node {%s} failed in health check. Reason: {%s}', hostname, result)
                CH_FLG = False
            health.disconnect()
        if CH_FLG:
            LOGGER.info("Cluster status is healthy.")
    except Exception as error:
        LOGGER.error("An error occurred in check_cluster_services", str(error))
        CH_FLG = False

    return CH_FLG


def check_cluster_space():
    """Checks nodes space and accepts till 98 % occupancy."""
    LOGGER.info("Check cluster storage for all nodes.")
    nodes, CS_FLG = CMN_CFG["nodes"], True
    try:
        for node in nodes:
            if node.get("node_type", None).lower() != "master":
                continue
            hostname = node['hostname']
            health = Health(hostname=hostname, username=node['username'], password=node['password'])
            ha_total, ha_avail, ha_used = health.get_sys_capacity()
            ha_used_percent = round((ha_used / ha_total) * 100, 1)
            if ha_used_percent > 98.0:
                LOGGER.critical('Cluster Node {%s} failed space check.', hostname)
                CS_FLG = False
            health.disconnect()
    except Exception as error:
        LOGGER.error("An error occurred in check_cluster_space", str(error))
        CS_FLG = False

    return CS_FLG


