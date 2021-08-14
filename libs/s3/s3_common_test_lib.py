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
#
"""Python library contains methods for s3 tests."""

import logging

from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG

LOG = logging.getLogger(__name__)


def check_cluster_health() -> None:
    """Check the cluster health."""
    LOG.info("Check cluster status, all services are running.")
    nodes = CMN_CFG["nodes"]
    LOG.info(nodes)
    for _, node in enumerate(nodes):
        health_obj = Health(hostname=node["hostname"],
                            username=node["username"],
                            password=node["password"])
        resp = health_obj.check_node_health()
        LOG.info(resp)
        health_obj.disconnect()
        assert_utils.assert_true(resp[0], resp[1])
    LOG.info("Cluster is healthy, all services are running.")


def get_ldap_creds() -> tuple:
    """Get the ldap credentials from node."""
    nodes = CMN_CFG["nodes"]
    node_hobj = Node(hostname=nodes[0]["hostname"],
                     username=nodes[0]["username"],
                     password=nodes[0]["password"])
    node_hobj.connect()
    resp = node_hobj.get_ldap_credential()
    node_hobj.disconnect()

    return resp
