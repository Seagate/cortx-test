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
#
"""Python library contains methods for s3 tests."""
import json
import os
import logging
from multiprocessing import Process
from time import perf_counter_ns

from config import CMN_CFG
from config.s3 import S3_CFG
from commons.exceptions import CTException
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.system_utils import calculate_checksum
from commons.utils.system_utils import path_exists
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3 import s3_bucket_policy_test_lib
from libs.s3 import s3_multipart_test_lib
from libs.s3 import s3_tagging_test_lib
from libs.s3.iam_policy_test_lib import IamPolicyTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from scripts.s3_bench import s3bench

LOG = logging.getLogger(__name__)


def check_cluster_health() -> None:
    """Check the cluster health."""
    LOG.info("Check cluster status, all services are running.")
    nodes = CMN_CFG["nodes"]
    LOG.info(nodes)
    if CMN_CFG["product_type"] == "node":
        for _, node in enumerate(nodes):
            health_obj = Health(hostname=node["hostname"],
                                username=node["username"],
                                password=node["password"])
            resp = health_obj.check_node_health()
            LOG.info(resp)
            health_obj.disconnect()
            assert_utils.assert_true(resp[0], resp[1])
    else:
        pass  # TODO: will update as per health helper changes for LC/k8s.
    LOG.info("Cluster is healthy, all services are running.")


def get_ldap_creds() -> tuple:
    """Get the ldap credentials from node."""
    nodes = CMN_CFG["nodes"]
    if CMN_CFG["product_type"] == "node":
        node_hobj = Node(hostname=nodes[0]["hostname"],
                         username=nodes[0]["username"],
                         password=nodes[0]["password"])
        node_hobj.connect()
        resp = node_hobj.get_ldap_credential()
        node_hobj.disconnect()
    else:
        resp = (None, None)  # TODO: will create method for LC/k8s once available.

    return resp


def get_cortx_capacity() -> tuple:
    """Get the cortx capacity stat."""
    nodes = CMN_CFG["nodes"]
    hostname = nodes[0]['hostname']
    username = nodes[0]['username']
    password = nodes[0]['password']
    health = Health(hostname=hostname,
                    username=username,
                    password=password)
    total, avail, used = health.get_sys_capacity()

    return total, avail, used


def create_s3_acc(
        account_name: str = None,
        email_id: str = None,
        password: str = None) -> tuple:
    """
    Create an S3 account with specified account name and email-id.

    :param str account_name: Name of account to be created.
    :param str email_id: Email id for account creation.
    :param password: account password.
    :return tuple: access key and secret key of the newly created S3 account.
    """
    rest_obj = S3AccountOperationsRestAPI()
    LOG.info("Step: Creating account with name %s and email_id %s", account_name, email_id)
    s3_account = rest_obj.create_s3_account(user_name=account_name, email_id=email_id,
                                            passwd=password)
    del rest_obj
    assert_utils.assert_true(s3_account[0], s3_account[1])
    access_key = s3_account[1]["access_key"]
    secret_key = s3_account[1]["secret_key"]
    LOG.info("Step Successfully created the s3 account")

    return access_key, secret_key


def create_s3_acc_get_s3testlib(
        account_name: str = None,
        email_id: str = None,
        password: str = None) -> tuple:
    """
    Create an S3 account and return S3 test library object.

    :param str account_name: Name of account to be created.
    :param str email_id: Email id for account creation.
    :param password: account password.
    :return tuple: It returns multiple values such as access_key,
    secret_key and S3 objects which required to perform further operations.
    """
    access_key, secret_key = create_s3_acc(account_name=account_name, email_id=email_id,
                                           password=password)
    s3_obj = s3_test_lib.S3TestLib(access_key, secret_key, endpoint_url=S3_CFG["s3_url"],
                                   s3_cert_path=S3_CFG["s3_cert_path"], region=S3_CFG["region"])
    return s3_obj, access_key, secret_key


def create_s3_account_get_s3lib_objects(account_name: str, email_id: str, password: str) -> tuple:
    """
    Create an s3 account with specified account name and email-id and returns s3 objects.

    :param account_name: Name of account to be created
    :param email_id: Email id for account creation
    :param password: Password for the account
    :return: It returns account details such as canonical_id, access_key, secret_key,
    account_id and s3 objects which will be required to perform further operations.
    """
    # Function needs to be refactored for CORTX RGW once Canonical IDs and/or Account ID
    # concepts are supported in CORTX RGW; retaining the code for the sake of completeness of
    # legacy (pre-CORTX RGW) S3 tests.
    LOG.info(
        "Step : Creating account with name %s and email_id %s",
        account_name, email_id)
    rest_obj = S3AccountOperations()
    s3_account = rest_obj.create_s3_account(
        acc_name=account_name, email_id=email_id, passwd=password)
    assert_utils.assert_true(s3_account[0], s3_account[1])
    del rest_obj
    access_key = s3_account[1]["access_key"]
    secret_key = s3_account[1]["secret_key"]
    canonical_id = s3_account[1]["canonical_id"]
    account_id = s3_account[1]["account_id"]
    LOG.info("Step Successfully created s3 account.")
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


# pylint:disable=too-many-arguments
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
    for i in range(1, num_sample + 1):
        fpath = os.path.join(os.getcwd(), f"{obj_prefix}-{i}")
        resp = system_utils.create_file(fpath, count=size * i)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(system_utils.path_exists(fpath), f"Failed to create path: {fpath}")
        resp = s3_obj.put_object(s3_bucket, os.path.basename(fpath), fpath)
        assert_utils.assert_true(resp[0], resp[1])
        objects.append(os.path.basename(fpath))
        resp = system_utils.remove_file(fpath)
        assert_utils.assert_true(resp[0], resp[1])

    return objects


def s3_ios(bucket=None,
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
    kwargs.setdefault("validate_certs", S3_CFG["validate_certs"])
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
        log_file_prefix=log_file_prefix,
        validate_certs=kwargs["validate_certs"])
    LOG.info(resp)
    assert_utils.assert_true(
        os.path.exists(
            resp[1]),
        f"failed to generate log: {resp[1]}")
    LOG.info("ENDED: s3 io's operations.")


def create_bucket_put_object(s3_tst_lib, bucket_name: str, obj_name: str, file_path: str,
                             mb_count: int) -> None:
    """
    This function creates a bucket and uploads an object to the bucket.

    :param s3_tst_lib: s3 test lib object
    :param bucket_name: Name of bucket to be created
    :param obj_name: Name of an object to be put to the bucket
    :param file_path: Path of the file to be created and uploaded to bucket
    :param mb_count: Size of file in MBs
    """
    LOG.info("Creating a bucket %s", bucket_name)
    resp = s3_tst_lib.create_bucket(bucket_name)
    assert_utils.assert_true(resp[0], resp[1])
    LOG.info("Created a bucket %s", bucket_name)
    system_utils.create_file(file_path, mb_count)
    LOG.info("Uploading an object %s to bucket %s", obj_name, bucket_name)
    resp = s3_tst_lib.put_object(bucket_name, obj_name, file_path)
    assert_utils.assert_true(resp[0], resp[1])
    LOG.info("Uploaded an object %s to bucket %s", obj_name, bucket_name)


def create_attach_list_iam_policy(access, secret, policy_name, iam_policy, iam_user):
    """
    Create IAM policy, Attach IAM Policy, List IAM Policy and make sure it is attached
    :param access: Access Key of S3 account
    :param secret: Secret Key of S3 account
    :param policy_name: IAM Policy name
    :param iam_policy: IAM Policy content
    :iam_user : IAM username
    """
    iam_policy_test_lib = IamPolicyTestLib(access_key=access, secret_key=secret)
    LOG.info("Creating IAM Policy %s = %s", policy_name, iam_policy)
    _, policy = iam_policy_test_lib.create_policy(
        policy_name=policy_name,
        policy_document=json.dumps(iam_policy))

    LOG.info("Attach Policy1 %s to %s user", policy.arn, iam_user)
    iam_policy_test_lib.attach_user_policy(iam_user, policy.arn)

    LOG.info("List Attached User Policies on %s", iam_user)
    resp = iam_policy_test_lib.check_policy_in_attached_policies(iam_user, policy.arn)
    assert_utils.assert_true(resp)


class S3BackgroundIO:
    """Class to perform/handle background S3 IOs for S3 tests using S3bench."""

    def __init__(self,
                 s3_test_lib_obj,
                 io_bucket_name: str = None) -> None:
        """
        Initialize object and create IO bucket, if not present.

        :param s3_test_lib_obj: Instance of S3TestLib.
        :param io_bucket_name: IO bucket name.
        """
        self.s3_test_lib_obj = s3_test_lib_obj
        self.io_bucket_name = io_bucket_name if io_bucket_name else "s3io-bkt-{}".format(
            perf_counter_ns())
        self.log_prefix = "parallel_io"
        self.parallel_ios = None
        assert_utils.assert_true(path_exists(s3bench.S3_BENCH_PATH),
                                 f"S3bench tool is not installed: {s3bench.S3_BENCH_PATH}")
        try:
            self.bucket_exists, _ = self.s3_test_lib_obj.head_bucket(self.io_bucket_name)
        except CTException as error:
            LOG.warning(error.message)
            self.bucket_exists = False

    @staticmethod
    def s3_ios(bucket: str = None,
               log_file_prefix: str = "parallel_io",
               duration: str = "0h1m",
               obj_size: str = "24Kb",
               **kwargs) -> None:
        """
        Perform IOs for specific durations.

        1. Perform IOs for specified durations.
        2. Check executions are successful.
        """
        kwargs.setdefault("num_clients", 2)
        kwargs.setdefault("num_sample", 5)
        kwargs.setdefault("obj_name_pref", "load_gen_")
        kwargs.setdefault("end_point", S3_CFG["s3_url"])
        kwargs.setdefault("validate_certs", S3_CFG["validate_certs"])
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
            log_file_prefix=log_file_prefix,
            validate_certs=kwargs["validate_certs"])
        LOG.info(resp)
        assert_utils.assert_true(
            os.path.exists(
                resp[1]),
            f"failed to generate log: {resp[1]}")
        LOG.info("ENDED: s3 io's operations.")

    def is_alive(self) -> bool:
        """
        Check if parallel IOs are running.

        :return: False if IO process is not running or if not created else True.
        """
        if not self.parallel_ios:
            return False
        return self.parallel_ios.is_alive()

    def start(self,
              duration: str = "0h1m",
              log_prefix: str = None,
              **kwargs) -> None:
        """
        Start parallel IO process.

        :param duration: Duration of the test in the format NhMm for N hours and M minutes.
        :param log_prefix: Prefix for s3bench logs.
        """
        self.log_prefix = log_prefix if log_prefix else self.log_prefix
        if not self.bucket_exists:
            LOG.info("Creating IO bucket: %s", self.io_bucket_name)
            resp = self.s3_test_lib_obj.create_bucket(self.io_bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            LOG.info("Created IO bucket: %s", self.io_bucket_name)
            self.bucket_exists = True
        LOG.info("Check s3 bench tool installed.")
        self.parallel_ios = Process(
            target=self.s3_ios,
            args=(self.io_bucket_name, self.log_prefix, duration),
            kwargs=kwargs)
        if not self.parallel_ios.is_alive():
            self.parallel_ios.start()
        LOG.info("Parallel IOs started: %s for duration: %s",
                 self.parallel_ios.is_alive(), duration)

    def stop(self) -> None:
        """Stop the parallel IO's/Process and validate logs."""
        if self.parallel_ios.is_alive():
            resp = self.s3_test_lib_obj.object_list(self.io_bucket_name)
            LOG.info(resp)
            self.parallel_ios.join()
            LOG.info("Parallel IOs stopped: %s", not self.parallel_ios.is_alive())
        if self.log_prefix:
            self.validate()

    def validate(self) -> None:
        """Validate s3bench execution logs."""
        resp = system_utils.validate_s3bench_parallel_execution(s3bench.LOG_DIR, self.log_prefix)
        assert_utils.assert_true(resp[0], resp[1])

    def cleanup(self) -> None:
        """Stop parallel IO process and cleanup IO bucket."""
        if self.is_alive():
            self.parallel_ios.join()
        if self.bucket_exists:
            LOG.info("Deleting IO bucket: %s", self.io_bucket_name)
            resp = self.s3_test_lib_obj.delete_bucket(self.io_bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOG.info("Deleted IO bucket: %s", self.io_bucket_name)
