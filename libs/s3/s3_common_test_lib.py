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

from config import CMN_CFG
from config import S3_CFG
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from libs.s3 import s3_test_lib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

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


def create_s3_acc(
        account_name: str = None,
        email_id: str = None,
        password: str = None) -> tuple:
    """
    Function will create s3 accounts with specified account name and email-id.

    :param str account_name: Name of account to be created.
    :param str email_id: Email id for account creation.
    :param password: account password.
    :param account_dict:
    :return tuple: It returns multiple values such as access_key,
    secret_key and s3 objects which required to perform further operations.
    """
    rest_obj = S3AccountOperations()
    LOG.info(
        "Step : Creating account with name %s and email_id %s",
        account_name,
        email_id)
    create_account = rest_obj.create_s3_account(
        account_name, email_id, password)
    del rest_obj
    assert_utils.assert_true(create_account[0], create_account[1])
    access_key = create_account[1]["access_key"]
    secret_key = create_account[1]["secret_key"]
    LOG.info("Step Successfully created the s3 account")
    s3_obj = s3_test_lib.S3TestLib(
        access_key,
        secret_key,
        endpoint_url=S3_CFG["s3_url"],
        s3_cert_path=S3_CFG["s3_cert_path"],
        region=S3_CFG["region"])
    response = (
        s3_obj,
        access_key,
        secret_key)

    return response
