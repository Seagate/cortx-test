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

import os
import logging
from time import perf_counter_ns

from config import CMN_CFG
from config import S3_CFG
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.system_utils import calculate_checksum
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


def perform_s3_io(s3_obj, s3_bucket, dir_path, obj_prefix="S3obj", size=10, num_sample=3):
    """
    Perform s3 read, write, verify object operations on the s3_bucket.

    :param s3_obj: s3 object.
    :param s3_bucket: Name of the s3 bucket.
    :param dir_path: Directory path where files getting created.
    :param obj_prefix: Prefix of the s3 object.
    :param size: size of the object multiple of 1MB.
    :param num_sample: Number of object getting created.
    """
    buckets = s3_obj.bucket_list()[1]
    if s3_bucket not in buckets:
        resp = s3_obj.create_bucket(s3_bucket)
        assert_utils.assert_true(resp[0], resp[1])
    resp = system_utils.path_exists(dir_path)
    assert_utils.assert_true(resp, f"Path not exists: {dir_path}")
    LOG.info("S3 IO started....")
    for _ in range(num_sample):
        f1name = f"{obj_prefix}-{perf_counter_ns()}.txt"
        f2name = f"{obj_prefix}-{perf_counter_ns()}.txt"
        f1path = os.path.join(dir_path, f1name)
        f2path = os.path.join(dir_path, f2name)
        resp = system_utils.create_file(f1path, count=size)
        assert_utils.assert_true(resp[0], resp[1])
        before_checksum = calculate_checksum(f1path)
        resp = s3_obj.put_object(s3_bucket, f1name, f1path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj.object_download(s3_bucket, f1name, f2path)
        assert_utils.assert_true(resp[0], resp[1])
        LOG.info("Verify uploaded and downloaded s3 file.")
        after_checksum = calculate_checksum(f2path)
        assert_utils.assert_equal(before_checksum, after_checksum,
                                  f"Failed to match checksum: {before_checksum}, {after_checksum}")
        LOG.info("Checksum verified successfully.")
        resp = system_utils.remove_file(f1path)
        assert_utils.assert_true(resp, f"Failed to delete {f1path}.")
        resp = system_utils.remove_file(f2path)
        assert_utils.assert_true(resp, f"Failed to delete {f2path}.")
    LOG.info("S3 IO completed successfully...")

    return True, f"S3 IO's completed successfully on {s3_bucket}"
