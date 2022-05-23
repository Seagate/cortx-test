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
"""Tests Account capacity scenarios using REST API
"""
import json
import logging
import os
import random
from random import SystemRandom
import time
from http import HTTPStatus
from multiprocessing import Pool

import pytest

from commons import configmanager
from commons import cortxlogging
from commons.constants import NORMAL_UPLOAD_SIZES_IN_MB, POD_NAME_PREFIX, RESTORE_SCALE_REPLICAS
from commons.constants import Rest as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils, system_utils
from config import CMN_CFG
from config.s3 import S3_CFG, S3_BLKBOX_CFG
from libs.csm.rest.csm_rest_acc_capacity import AccountCapacity
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import iam_test_lib
from libs.s3 import s3_misc
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_bucket_policy_test_lib import S3BucketPolicyTestLib
from libs.s3.s3_common_test_lib import create_attach_list_iam_policy
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib


class TestAccountCapacity():
    """Account Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.acc_capacity = AccountCapacity()
        cls.log.info("Initiating Rest Client ...")
        cls.s3user = RestS3user()
        cls.buckets_created = []
        cls.account_created = []
        cls.iam_users_created = []
        cls.s3_obj = S3AccountOperations()
        cls.test_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_account_capacity.yaml")

        cls.jc_obj = JCloudClient()
        cls.log.info("setup jClientCloud on runner.")
        res_ls = system_utils.execute_cmd("ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = cls.jc_obj.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"]
            )
            cls.log.info(res)
            assert_utils.assert_true(
                res, "Error: jcloudclient.jar or jclient.jar file does not exists")
        resp = cls.jc_obj.update_jclient_jcloud_properties()
        assert_utils.assert_true(resp, resp)

        cls.ha_obj = HAK8s()
        cls.master_node_list = []
        cls.worker_node_list = []
        cls.hlth_master_list = []
        for node in CMN_CFG["nodes"]:
            if node["node_type"] == "master":
                cls.master_node_list.append(LogicalNode(hostname=node["hostname"],
                                                        username=node["username"],
                                                        password=node["password"]))
                cls.hlth_master_list.append(Health(hostname=node["hostname"],
                                                   username=node["username"],
                                                   password=node["password"]))
            else:
                cls.worker_node_list.append(LogicalNode(hostname=node["hostname"],
                                                        username=node["username"],
                                                        password=node["password"]))
        cls.restore_pod = cls.restore_method = cls.deployment_name = None
        cls.deployment_backup = None
        if not os.path.exists(TEST_DATA_FOLDER):
            os.mkdir(TEST_DATA_FOLDER)

    # pylint: disable-msg=too-many-branches
    def teardown_method(self):
        """
        Teardown for deleting any account and buckets created during tests
        """
        self.log.info("[STARTED] ######### Teardown #########")
        if self.restore_pod:
            self.log.info("Restore deleted pods.")
            resp = self.ha_obj.restore_pod(pod_obj=self.master_node_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)

        self.log.info("Deleting buckets %s & associated objects", self.buckets_created)
        buckets_deleted = []
        iam_deleted = []
        s3_account_deleted = []
        for bucket in self.buckets_created:
            resp = s3_misc.delete_objects_bucket(bucket[0], bucket[1], bucket[2])
            if resp:
                buckets_deleted.append(bucket)
            else:
                self.log.error("Bucket deletion failed for %s ", bucket)
        self.log.info("buckets deleted %s", buckets_deleted)
        for bucket in buckets_deleted:
            self.buckets_created.remove(bucket)

        self.log.info("Deleting iam account %s created in test", self.iam_users_created)
        for iam_user in self.iam_users_created:
            resp = s3_misc.delete_iam_user(iam_user[0], iam_user[1], iam_user[2])
            if resp:
                iam_deleted.append(iam_user)
            else:
                self.log.error("IAM deletion failed for %s ", iam_user)
        self.log.info("IAMs deleted %s", iam_deleted)
        for iam in iam_deleted:
            self.iam_users_created.remove(iam)

        self.log.info("Deleting S3 account %s created in test", self.account_created)
        for account in self.account_created:
            resp = self.s3user.delete_s3_account_user(account)
            if resp.status_code == HTTPStatus.OK:
                s3_account_deleted.append(account)
            else:
                self.log.error("S3 account deletion failed for %s ", account)
        self.log.info("S3 accounts deleted %s", s3_account_deleted)
        for acc in s3_account_deleted:
            self.account_created.remove(acc)

        assert_utils.assert_true(len(self.buckets_created) == 0, "Bucket deletion failed")
        assert_utils.assert_true(len(self.iam_users_created) == 0, "IAM deletion failed")
        assert_utils.assert_true(len(self.account_created) == 0, "S3 account deletion failed")
        self.log.info("[ENDED] ######### Teardown #########")

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33362')
    def test_33362(self):
        """
        Test data usage per account for PUT operation with same object name but different size.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Creating S3 account")
        resp = self.s3user.create_s3_account_for_capacity()
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "Failed to create S3 account.")
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)
        total_cap = 0
        for _ in range(10):
            bucket = "bucket%s" % int(time.time())
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert_utils.assert_true(s3_misc.create_bucket(bucket, access_key, secret_key),
                                     "Failed to create bucket")
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            self.log.info("Start: Put operations")
            obj = f"object{s3_user}.txt"
            write_bytes_mb = SystemRandom().randrange(10, 100)
            total_cap = total_cap + write_bytes_mb
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, access_key, secret_key, object_size=write_bytes_mb)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("End: Put operations")
            self.log.info("verify capacity of account after put operations")
            s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
            resp = self.acc_capacity.verify_account_capacity(s3_account)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("verified capacity of account after put operations")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33369')
    def test_33369(self):
        """
        Test data usage per account while performing concurrent IO operations on multiple accounts.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        s3acct_cnt = self.test_conf["test_33369"]["s3acct_cnt"]
        validate_data_usage = self.test_conf["test_33369"]["validate_data_usage"]

        data_all = []
        self.log.info("Creating  %s S3 account and buckets", s3acct_cnt)
        for cnt in range(0, s3acct_cnt):
            self.log.info("Create S3 Account : %s", cnt)
            resp = self.s3user.create_s3_account_for_capacity()
            assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
            access_key = resp.json()["access_key"]
            secret_key = resp.json()["secret_key"]
            s3_user = resp.json()["account_name"]
            self.account_created.append(s3_user)
            bucket = f"test-33371-s3user{cnt}-bucket"
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket"
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            data_all.append(([s3_user, access_key, secret_key, bucket], NORMAL_UPLOAD_SIZES_IN_MB,
                             validate_data_usage))

        with Pool(len(data_all)) as pool:
            resp = pool.starmap(self.acc_capacity.perform_io_validate_data_usage, data_all)
        assert_utils.assert_true(all(resp),
                                 "Failure in Performing IO operations on S3 accounts")

        self.log.info("##### Test Ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33370')
    def test_33370(self):
        """
        Test data usage per account while performing concurrent IO operations on multiple buckets
        in same account.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        bucket_cnt = self.test_conf["test_33370"]["bucket_cnt"]
        validate_data_usage = self.test_conf["test_33370"]["validate_data_usage"]

        data_all = []
        self.log.info("Create S3 Account")
        resp = self.s3user.create_s3_account_for_capacity()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)

        for cnt in range(0, bucket_cnt):
            bucket = f"test-33370-bucket{cnt}"
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket"
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            data_all.append(([s3_user, access_key, secret_key, bucket], NORMAL_UPLOAD_SIZES_IN_MB,
                             validate_data_usage))

        with Pool(len(data_all)) as pool:
            resp = pool.starmap(self.acc_capacity.perform_io_validate_data_usage, data_all)
        assert_utils.assert_true(all(resp),
                                 "Failure in Performing IO operations on S3 accounts")

        self.log.info("Verify capacity of account after put operations")
        expected_data_usage = bucket_cnt * sum(NORMAL_UPLOAD_SIZES_IN_MB)
        self.log.info("Expected data usage in MB : %s", expected_data_usage)
        s3_account = [{"account_name": s3_user, "capacity": expected_data_usage, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("##### Test Ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33371')
    def test_33371(self):
        """
        Test data usage per account while performing concurrent IO operations on same bucket.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        parallel_io_cnt = self.test_conf["test_33371"]["parallel_io_cnt"]
        validate_data_usage = self.test_conf["test_33371"]["validate_data_usage"]

        data_all = []
        self.log.info("Create S3 Account")
        resp = self.s3user.create_s3_account_for_capacity()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)

        bucket = "test-33371-bucket"
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      bucket, access_key, secret_key)
        assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket"
        self.log.info("bucket created successfully")
        self.buckets_created.append([bucket, access_key, secret_key])

        for _ in range(0, parallel_io_cnt):
            data_all.append(([s3_user, access_key, secret_key, bucket], NORMAL_UPLOAD_SIZES_IN_MB,
                             validate_data_usage))

        with Pool(len(data_all)) as pool:
            resp = pool.starmap(self.acc_capacity.perform_io_validate_data_usage, data_all)
        assert_utils.assert_true(all(resp),
                                 "Failure in Performing IO operations on S3 accounts")

        self.log.info("Verify capacity of account after put operations")
        expected_data_usage = parallel_io_cnt * sum(NORMAL_UPLOAD_SIZES_IN_MB)
        self.log.info("Expected data usage in MB : %s", expected_data_usage)
        s3_account = [{"account_name": s3_user, "capacity": expected_data_usage, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("##### Test Ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33363')
    def test_33363(self):
        """
        Test data usage per account for copy objects operation.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        user1_bucket1 = "S3user1Bucket1"
        user1_bucket2 = "S3user1Bucket2"
        user2_bucket1 = "S3user2Bucket1"
        object_name = "S3user1Bucket1_obj"
        self.log.info("Step-1: Creating first S3 account")
        resp = self.acc_capacity.create_s3_account_for_capacity(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account1_info = resp[1]  # [access_key, secret_key, canonical_id, s3_account,
        # s3_obj, s3_acl_obj]
        self.account_created.append(account1_info[3])
        self.log.info("Step-2: Creating second S3 account")
        resp = self.acc_capacity.create_s3_account_for_capacity(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account2_info = resp[1]
        self.account_created.append(account2_info[3])
        self.log.info("Step-3: create 2 buckets in account-1")
        resp = account1_info[4].create_bucket(user1_bucket1)
        assert_utils.assert_true(resp[0], resp)
        self.buckets_created.append([user1_bucket1, account1_info[0], account1_info[1]])
        resp = account1_info[4].create_bucket(user1_bucket2)
        assert_utils.assert_true(resp[0], resp)
        self.buckets_created.append([user1_bucket2, account1_info[0], account1_info[1]])
        self.log.info("Step-4: create a bucket in account-2")
        resp = account2_info[4].create_bucket(user2_bucket1)
        assert_utils.assert_true(resp[0], resp)
        self.buckets_created.append([user2_bucket1, account2_info[0], account2_info[1]])
        self.log.info("Step-5: put object in first bucket of account-1")
        obj = f"object{account1_info[3]}.txt"
        write_bytes_mb = SystemRandom().randrange(10, 100)
        total_cap = write_bytes_mb
        self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                      user1_bucket1)
        resp = s3_misc.create_put_objects(
            obj, user1_bucket1, account1_info[0], account1_info[1], object_size=write_bytes_mb)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("End: Put operations")
        self.log.info("Step-6: Verify capacity of account-1 after put operations")
        s3_account = [{"account_name": account1_info[3], "capacity": total_cap, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verified capacity of account after put operations")

        self.log.info("Step-7: Copy object to another bucket of same account")
        total_cap = total_cap * 2
        status, response = account1_info[4].copy_object(
            user1_bucket1, object_name, user1_bucket2, object_name)
        assert_utils.assert_true(status, response)
        self.log.info("Step-8: Verify capacity of account-1 after put operations")
        s3_account = [{"account_name": account1_info[3], "capacity": total_cap, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verified capacity of account after put operations")

        self.log.info("Step-9: Copy object to same bucket of same account")
        total_cap = total_cap * 3
        status, response = account1_info[4].copy_object(
            user1_bucket1, object_name, user1_bucket1, object_name + "_copy")
        assert_utils.assert_true(status, response)
        self.log.info("Step-10: Verify capacity of account-1 after put operations")
        s3_account = [{"account_name": account1_info[3], "capacity": total_cap, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verified capacity of account after put operations")

        self.log.info("Step-11: Copy object to another bucket of another account")
        total_cap = write_bytes_mb
        self.log.info("Step 12: From Account2 on bucket2 grant Write ACL to Account1 and full "
                      "control to account2.")
        resp = account2_info[5].put_bucket_multiple_permission(
            bucket_name=user2_bucket1,
            grant_full_control=f"id={account2_info[2]}",
            grant_write=f"id={account1_info[2]}")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 13: From Account2 check the applied ACL in above step.")
        resp = account2_info[5].get_bucket_acl(user2_bucket1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 14: From Account1 copy object from bucket1 to user2 bucket1.")
        status, response = account1_info[4].copy_object(
            user1_bucket1, object_name, user2_bucket1, object_name)
        assert_utils.assert_true(status, response)
        self.log.info("Step 15: Verify capacity of account after put operations")
        s3_account = [{"account_name": account2_info[3], "capacity": total_cap, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verified capacity of account after put operations")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33364')
    def test_33364(self):
        """
        Test data usage per account for Max IAM users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create s3 Account")
        resp = self.acc_capacity.create_s3_account_for_capacity(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account1_info = resp[1]
        self.account_created.append(account1_info[3])
        self.log.info("Step-2: create a bucket in account")
        bucket = f"bucket{account1_info[3]}"
        resp = account1_info[4].create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp)
        self.buckets_created.append([bucket, account1_info[0], account1_info[1]])
        total_cap = 0
        self.log.info("Creating %s IAMs for %s s3 user",const.MAX_IAM_USERS,account1_info[3])
        iam_users = []
        for cnt in range(const.MAX_IAM_USERS):
            iam_user = "iam_user_" + str(cnt) + "_" + str(int(time.time()))
            self.log.info("Creating new iam user %s", iam_user)
            iam_obj = iam_test_lib.IamTestLib(
                access_key=account1_info[0],
                secret_key=account1_info[1])
            resp = iam_obj.create_user(iam_user)
            assert_utils.assert_true(resp[0], resp[1])
            self.iam_users_created.append([iam_user, account1_info[0], account1_info[1]])
            response = iam_obj.create_access_key(iam_user)[1]
            self.log.info("user_acc_key: %s", str(response))
            iam_access_key = response["AccessKey"]["AccessKeyId"]
            iam_secret_key = response["AccessKey"]["SecretAccessKey"]
            iam_users.append(iam_user)
            self.log.info("Start: Put operations")
            obj = f"object{iam_user}" + str(cnt) + ".txt"
            write_bytes_mb = SystemRandom().randrange(10, 100)
            total_cap = total_cap + write_bytes_mb
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, iam_access_key, iam_secret_key, object_size=write_bytes_mb)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("End: Put operations")
            self.log.info("verify capacity of account after put operations")
            s3_account = [{"account_name": account1_info[3], "capacity": total_cap, "unit": 'MB'}]
            resp = self.acc_capacity.verify_account_capacity(s3_account)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("verified capacity of account after put operations")
        self.log.info("ENDED: ")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33372')
    def test_33372(self):
        """
        Test data usage per account with max S3 accounts
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create Max s3 accounts")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        for _ in range(const.MAX_S3_USERS):
            total_cap = 0
            resp = self.s3user.create_s3_account_for_capacity()
            self.log.info("s3 account response %s:", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                     "Failed to create S3 account.")
            access_key = resp.json()["access_key"]
            secret_key = resp.json()["secret_key"]
            s3_user = resp.json()["account_name"]
            s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
            self.account_created.append(s3_user)
            self.log.info("Step 2: Creating bucket for each account")
            bucket = "bucket%s" % int(time.time())
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert_utils.assert_true(s3_misc.create_bucket(bucket, access_key, secret_key),
                                     "Failed to create bucket")
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            self.log.info("Step 3: Putting object of size zero to some specific size in bucket")
            ran_number = SystemRandom().randrange(10, 100)
            for i in [0, ran_number]:
                obj = f"object{i}{s3_user}.txt"
                object_size = i
                self.log.info("Perform %s of %s MB write in the bucket: %s", obj, object_size,
                              bucket)
                resp = s3_misc.create_put_objects(
                    obj, bucket, access_key, secret_key, object_size=object_size)
                assert_utils.assert_true(resp, "Put object Failed")
                self.log.info("End: Put operations")
                s3_account[0]["capacity"] += object_size
                self.log.info("Step 4: Checking data usage")
                resp = self.acc_capacity.verify_account_capacity(s3_account)
                assert_utils.assert_true(resp[0], resp[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33373')
    def test_33373(self):
        """
        Test data usage per account with max buckets in an account
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Creating s3 user")
        resp = self.s3user.create_s3_account_for_capacity()
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "Failed to create S3 account.")
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        total_cap = 0
        s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
        self.account_created.append(s3_user)
        self.log.info("Step 1: Create Max buckets for s3 users")
        for _ in range(const.MAX_BUCKETS):
            bucket = "bucket%s" % int(time.time())
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert_utils.assert_true(s3_misc.create_bucket(bucket, access_key, secret_key),
                                     "Failed to create bucket")
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            self.log.info("Step 2: Put object of specific size in bucket")
            obj = f"object{s3_user}.txt"
            write_bytes_mb = SystemRandom().randrange(10, 100)
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, access_key, secret_key, object_size=write_bytes_mb)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Put operation completed")
            s3_account[0]["capacity"] += write_bytes_mb
        self.log.info("Step 3: Checking data usage")
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33374')
    def test_33374(self):
        """
        Test data usage per S3 account with max objects in a bucket
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Creating s3 user")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        resp = self.s3user.create_s3_account_for_capacity()
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "Failed to create S3 account.")
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        total_cap = 0
        s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
        self.account_created.append(s3_user)
        bucket1 = "bucket%s" % int(time.time())
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      bucket1, access_key, secret_key)
        assert_utils.assert_true(s3_misc.create_bucket(bucket1, access_key, secret_key),
                                 "Failed to create bucket")
        self.log.info("bucket created successfully")
        self.buckets_created.append([bucket1, access_key, secret_key])
        self.log.info("Step 2: Put 1000 objects of size 0 in bucket")
        for _ in range(1000):
            obj = f"object{s3_user}.txt"
            self.log.info("Verify Perform %s of write in the bucket: %s", obj,
                          bucket1)
            resp = s3_misc.create_put_objects(
                obj, bucket1, access_key, secret_key, object_size=0)
            assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Put operation completed")
        self.log.info("Step 3: Checking data usage")
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Put 1000 objects of specific size in bucket")
        for _ in range(1000):
            obj = f"object{s3_user}.txt"
            write_bytes_mb = SystemRandom().randrange(10, 100)
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket1)
            resp = s3_misc.create_put_objects(
                obj, bucket1, access_key, secret_key, object_size=write_bytes_mb)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Put operation completed")
            s3_account[0]["capacity"] += write_bytes_mb
        self.log.info("Step 5: Checking data usage")
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33377')
    def test_33377(self):
        """
        Test data usage per S3 account with IO service failure
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Step 1: Create S3 Account")
        resp = self.s3user.create_s3_account_for_capacity()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)
        self.log.info("Step 1: Created S3 Account!!")

        self.log.info("Step 2: Create a bucket.")
        bucket_name = "test-33377-bucket" + str(int(time.time()))
        assert s3_misc.create_bucket(bucket_name, access_key, secret_key), "Failed to create bucket"
        self.buckets_created.append([bucket_name, access_key, secret_key])
        self.log.info("Step 2: Created bucket %s", bucket_name)

        self.log.info("Step 3: Perform IO operation on %s", bucket_name)
        resp = self.acc_capacity.perform_io_validate_data_usage(
            [s3_user, access_key, secret_key, bucket_name],
            NORMAL_UPLOAD_SIZES_IN_MB, False)
        assert_utils.assert_true(resp, "Error during IO operations")
        self.log.info("Step 3: Performed IO operation on %s", bucket_name)

        self.log.info("Step 4: Check Data usage for %s", s3_user)
        s3_account = [
            {"account_name": s3_user, "capacity": sum(NORMAL_UPLOAD_SIZES_IN_MB), "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Verified Data usage!!!")

        self.log.info("Step 5: Shutdown the data pod safely by making replicas=0")
        self.log.info("Get pod name to be deleted")
        pod_list = self.master_node_list[0].get_all_pods(pod_prefix=POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.master_node_list[0].get_pod_hostname(pod_name=pod_name)

        self.log.info("Deleting pod %s", pod_name)
        resp = self.master_node_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        self.log.info("Step 5: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)

        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = RESTORE_SCALE_REPLICAS

        self.log.info("Step 6: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        assert_utils.assert_false(resp[0], resp)
        self.log.info("Step 6: Cluster is in degraded state")

        self.log.info("Step 7: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        self.log.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 7: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        self.log.info("Step 8: Check services status on remaining pods %s",
                      remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        self.log.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 8: Services of pod are in online state")

        self.log.info("Step 9: Perform IO operation on %s", bucket_name)
        resp = self.acc_capacity.perform_io_validate_data_usage(
            [s3_user, access_key, secret_key, bucket_name],
            NORMAL_UPLOAD_SIZES_IN_MB, False)
        assert_utils.assert_true(resp, "Error during IO operations")
        self.log.info("Step 9: Performed IO operation on %s", bucket_name)

        self.log.info("Step 10: Check Data usage for %s", s3_user)
        s3_account = [
            {"account_name": s3_user, "capacity": sum(NORMAL_UPLOAD_SIZES_IN_MB) * 2, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 10: Verified Data usage!!!")

        self.log.info("Step 11: Restore deleted pods.")
        resp = self.ha_obj.restore_pod(pod_obj=self.master_node_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        self.log.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.log.info("Successfully restored pod by %s way", self.restore_method)

        self.restore_pod = False

        self.log.info("Step 12: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 12: Cluster recovered and in running state")

        self.log.info("Step 13: Perform IO operation on %s", bucket_name)
        resp = self.acc_capacity.perform_io_validate_data_usage(
            [s3_user, access_key, secret_key, bucket_name],
            NORMAL_UPLOAD_SIZES_IN_MB, False)
        assert_utils.assert_true(resp, "Error during IO operations")
        self.log.info("Step 13: Performed IO operation on %s", bucket_name)

        self.log.info("Step 14: Check Data usage for %s", s3_user)
        s3_account = [
            {"account_name": s3_user, "capacity": sum(NORMAL_UPLOAD_SIZES_IN_MB) * 3, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 14: Verified Data usage!!!")

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33378')
    def test_33378(self):
        """
        Test data usage per S3 account with chunked upload
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Step 1: Create S3 Account")
        resp = self.s3user.create_s3_account_for_capacity()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)

        self.log.info("Step 2: Create a bucket.")
        bucket_name = "test-33379-bucket" + str(int(time.time()))
        command = self.jc_obj.create_cmd_format(bucket_name, "mb",
                                                jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"],
                                                chunk=True, access_key=access_key,
                                                secret_key=secret_key)
        resp = system_utils.execute_cmd(command)
        self.buckets_created.append([bucket_name, access_key, secret_key])
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])

        size = SystemRandom().randrange(10, 100)
        self.log.info("Step: 3 Create a file of size %sMB", size)
        test_file = f"test-33379-{str(size)}-MB.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        system_utils.create_file(file_path_upload, size)

        self.log.info("Step 4: Upload object of %s MB into a %s bucket.", size, file_path_upload)
        put_cmd_str = "{} {}".format("put", file_path_upload)
        command = self.jc_obj.create_cmd_format(bucket_name, put_cmd_str,
                                                jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"],
                                                chunk=True, access_key=access_key,
                                                secret_key=secret_key)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])

        self.log.info("Step 5: Checking data usage")
        s3_account = [{"account_name": s3_user, "capacity": size, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verified Data usage!!!")

        self.log.info("Delete created file")
        os.remove(file_path_upload)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33379')
    def test_33379(self):
        """
        Test data usage per S3 account with cross-accounts access to objects
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Step-1: Creating first S3 account")
        resp = self.acc_capacity.create_s3_account_for_capacity(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account1_info = resp[1]  # [access_key, secret_key, canonical_id, s3_account,
        # s3_obj, s3_acl_obj]
        self.account_created.append(account1_info[3])

        self.log.info("Step-2: Creating second S3 account")
        resp = self.acc_capacity.create_s3_account_for_capacity(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account2_info = resp[1]
        self.account_created.append(account2_info[3])

        user1_bucket1 = "s3user1bucket1"
        self.log.info("Step-3: Create 1 bucket in account-1")
        resp = account1_info[4].create_bucket(user1_bucket1)
        assert_utils.assert_true(resp[0], resp)
        self.buckets_created.append([user1_bucket1, account1_info[0], account1_info[1]])

        iam_user = "S3user2iam"
        self.log.info("Step-4 Creating new iam user %s", iam_user)
        iam_obj = iam_test_lib.IamTestLib(
            access_key=account2_info[0],
            secret_key=account2_info[1])
        resp = iam_obj.create_user(iam_user)
        assert_utils.assert_true(resp[0], resp[1])
        user_arn = resp[1]["User"]["Arn"]
        self.iam_users_created.append([iam_user, account2_info[0], account2_info[1]])

        response = iam_obj.create_access_key(iam_user)[1]
        self.log.info("user_acc_key: %s", str(response))
        iam_access_key = response["AccessKey"]["AccessKeyId"]
        iam_secret_key = response["AccessKey"]["SecretAccessKey"]

        self.log.info("Step-5 Create bucket policy using s3account1 for %s of s3account2", iam_user)
        actions = ["s3:PutObject"]
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": f"arn:aws:s3:::{user1_bucket1}/*",
                    "Principal": {"AWS": user_arn}
                }
            ]
        }
        buck_pol_obj = S3BucketPolicyTestLib(access_key=account1_info[0],
                                             secret_key=account1_info[1])
        buck_pol_obj.put_bucket_policy(bucket_name=user1_bucket1,
                                       bucket_policy=json.dumps(bucket_policy))

        self.log.info(
            "Step-6 Create iam policy using s3account1 for %s to access bucket of S3account1",
            iam_user)
        iam_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": [f"arn:aws:s3:::{user1_bucket1}/*", f"arn:aws:s3:::{user1_bucket1}"]
                }
            ]
        }
        policy_name = f"iam-policy-{(int(time.time()))}"
        create_attach_list_iam_policy(access=account2_info[0], secret=account2_info[1],
                                      policy_name=policy_name, iam_policy=iam_policy,
                                      iam_user=iam_user)

        self.log.info("Step-7 Put object using %s user into %s", iam_user, user1_bucket1)
        test_file = "test-object.txt"
        size = SystemRandom().randrange(10, 100)
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        system_utils.create_file(file_path_upload, size)

        s3_obj = S3TestLib(access_key=iam_access_key, secret_key=iam_secret_key)
        resp = s3_obj.put_object(bucket_name=user1_bucket1, object_name=test_file,
                                 file_path=file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step-8 Validate Data usage of S3 account 1, expected : %s", size)
        s3_account = [{"account_name": account1_info[3], "capacity": size, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verified Data usage!!!")

        self.log.info("Step-9 Validate Data usage of S3 account 2, expected : 0")
        s3_account = [{"account_name": account2_info[3], "capacity": 0, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verified Data usage!!!")

        self.log.info("Delete created file")
        os.remove(file_path_upload)
        self.log.info("##### Test ended -  %s #####", test_case_name)
