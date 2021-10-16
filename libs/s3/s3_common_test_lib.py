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
from scripts.s3_bench import s3bench
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.system_utils import calculate_checksum
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3 import s3_bucket_policy_test_lib
from libs.s3 import s3_multipart_test_lib
from libs.s3 import s3_tagging_test_lib
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


def create_s3_account_get_s3objects(account_name: str, email_id: str, password: str) -> tuple:
    """
    function will create s3 account with specified account name and email-id and returns s3 objects.

    :param account_name: Name of account to be created
    :param email_id: Email id for account creation
    :param password: Password for the account
    :return: It returns account details such as canonical_id, access_key, secret_key,
    account_id and s3 objects which will be required to perform further operations.
    """
    LOG.info(
        "Step : Creating account with name %s and email_id %s",
        account_name, email_id)
    rest_obj = S3AccountOperations()
    create_account = rest_obj.create_s3_account(
        acc_name=account_name, email_id=email_id, passwd=password)
    assert_utils.assert_true(create_account[0], create_account[1])
    del rest_obj
    access_key = create_account[1]["access_key"]
    secret_key = create_account[1]["secret_key"]
    canonical_id = create_account[1]["canonical_id"]
    account_id = create_account[1]["account_id"]
    LOG.info("Step Successfully created the cortxcli account")
    s3_obj = s3_test_lib.S3TestLib(access_key=access_key, secret_key=secret_key)
    acl_obj = s3_acl_test_lib.S3AclTestLib(access_key=access_key, secret_key=secret_key)
    s3_bkt_policy_obj = s3_bucket_policy_test_lib.S3BucketPolicyTestLib(
        access_key=access_key, secret_key=secret_key)
    s3_bkt_tag_obj = s3_tagging_test_lib.S3TaggingTestLib(
        access_key=access_key, secret_key=secret_key)
    s3_multipart_obj = s3_multipart_test_lib.S3MultipartTestLib(
        access_key=access_key, secret_key=secret_key)

    return canonical_id, s3_obj, acl_obj, s3_bkt_policy_obj, \
        access_key, secret_key, account_id, s3_bkt_tag_obj, s3_multipart_obj


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


def upload_random_size_objects(s3_obj, s3_bucket, obj_prefix="s3-obj", size=10, num_sample=3):
    """
    Upload number of random size objects using simple upload.

    :param s3_obj: s3 object.
    :param s3_bucket: Name of the s3 bucket.
    :param obj_prefix: Prefix of the s3 object.
    :param size: size of the object multiple of 1MB.
    :param num_sample: Number of object getting created.
    """
    buckets = s3_obj.bucket_list()[1]
    if s3_bucket not in buckets:
        resp = s3_obj.create_bucket(s3_bucket)
        assert_utils.assert_true(resp[0], resp[1])
    objects = []
    for i in range(1, num_sample):
        fpath = os.path.join(os.getcwd(), f"{obj_prefix}-{i}")
        resp = system_utils.create_file(fpath, count=size*i)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(system_utils.path_exists(fpath), f"Failed to create path: {fpath}")
        resp = s3_obj.put_object(s3_bucket, os.path.basename(fpath), fpath)
        assert_utils.assert_true(resp[0], resp[1])
        objects.append(os.path.basename(fpath))
        resp = system_utils.remove_file(fpath)
        assert_utils.assert_true(resp[0], resp[1])

    return objects


def s3_ios(
           bucket=None,
           log_file_prefix="parallel_io",
           duration="0h1m",
           obj_size="24Kb",
           **kwargs):
    """
    Perform io's for specific durations.

    1. Create bucket.
    2. perform io's for specified durations.
    3. Check executions successful.
    """
    kwargs.setdefault("num_clients", 2)
    kwargs.setdefault("num_sample", 5)
    kwargs.setdefault("obj_name_pref", "load_gen_")
    kwargs.setdefault("end_point", S3_CFG["s3_url"])
    LOG.info("STARTED: s3 io's operations.")
    access_key, secret_key = S3H_OBJ.get_local_keys()
    resp = s3bench.s3bench(
        access_key,
        secret_key,
        bucket=bucket,
        end_point=kwargs["end_point"],
        num_clients=kwargs["num_clients"],
        num_sample=kwargs["num_sample"],
        obj_name_pref=kwargs["obj_name_pref"],
        obj_size=obj_size,
        duration=duration,
        log_file_prefix=log_file_prefix)
    LOG.info(resp)
    assert_utils.assert_true(
        os.path.exists(
            resp[1]),
        f"failed to generate log: {resp[1]}")
    LOG.info("ENDED: s3 io's operations.")
