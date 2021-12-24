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
"""Tests Account capacity scenarios using REST API
"""
import logging
import pytest
import random
import time
from http import HTTPStatus
from multiprocessing import Pool

from commons import configmanager
from commons import cortxlogging
from commons.constants import NORMAL_UPLOAD_SIZES_IN_MB
from commons.constants import Rest as const
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_acc_capacity import AccountCapacity
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3 import s3_misc
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

    def teardown_method(self):
        """
        Teardown for deleting any account and buckets created during tests
        """
        self.log.info("[STARTED] ######### Teardown #########")
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
        resp = self.s3user.create_s3_account()
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
            write_bytes_mb = random.randint(10, 100)
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
            resp = self.s3user.create_s3_account()
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
        resp = self.s3user.create_s3_account()
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
        resp = self.s3user.create_s3_account()
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
        resp = self.acc_capacity.create_s3_account(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account1_info = resp[1]  # [access_key, secret_key, canonical_id, s3_account,
        # s3_obj, s3_acl_obj]
        self.account_created.append(account1_info[3])
        self.log.info("Step-2: Creating second S3 account")
        resp = self.acc_capacity.create_s3_account(True, True)
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
        write_bytes_mb = random.randint(10, 100)
        total_cap = write_bytes_mb
        self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                      bucket)
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
            grant_full_control="id={}".format(account2_info[2]),
            grant_write="id={}".format(account1_info[2]))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 13: From Account2 check the applied ACL in above step.")
        resp = account2_info[5].get_bucket_acl(user2_bucket1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 14: From Account1 copy object from bucket1 to user2 bucket1.")
        status, response = account1_info[4].copy_object(
            user1_bucket1, object_name, user2_bucket1, object_name)
        assert_utils.assert_true(status, response)
        self.log.info("Step 15: Verify capacity of account after put operations")
        s3_account = [{"account_name": account2_info[3], "capacity": total_cap, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verified capacity of account after put operations")
        self.log.info("##### Test ended -  %s #####", test_case_name)

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
        resp = self.acc_capacity.create_s3_account(True, True)
        assert_utils.assert_true(resp[0], resp[1])
        account1_info = resp[1]
        self.account_created.append(account1_info[3])
        self.log.info("Step-2: create a bucket in account")
        bucket = f"bucket{account1_info[3]}"
        resp = account1_info[4].create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp)
        self.buckets_created.append([bucket, account1_info[0], account1_info[1]])
        total_cap = 0
        self.log.info(f"creating {const.MAX_IAM_USERS} IAMs for {account1_info[3]} s3 user")
        iam_users = []
        for cnt in range(const.MAX_IAM_USERS):
            iam_user = "iam_user_" + str(cnt) + "_" + str(int(time.time()))
            self.log.info(f"Creating new iam user {iam_user}")
            iam_obj = iam_test_lib.IamTestLib(
                access_key=account1_info[0],
                secret_key=account1_info[1])
            resp = iam_obj.create_user(iam_user)
            assert_true(resp[0], resp[1])
            self.iam_users_created([iam_user, account1_info[0], account1_info[1]])
            iam_access_key = resp[1]["access_key"]
            iam_secret_key = resp[1]["secret_key"]
            iam_users.append(iam_user)
            self.log.info("Start: Put operations")
            obj = f"object{s3_user}" + str(cnt) + ".txt"
            write_bytes_mb = random.randint(10, 100)
            total_cap = total_cap + write_bytes_mb
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, iam_access_key, iam_secret_key, object_size=write_bytes_mb)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("End: Put operations")
            self.log.info("verify capacity of account after put operations")
            s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
            resp = self.acc_capacity.verify_account_capacity(s3_account)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("verified capacity of account after put operations")
        self.log.info("ENDED: ")

    # pylint: disable-msg=too-many-locals
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
            resp = self.s3user.create_s3_account()
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
            ran_number = random.randint(10, 100)
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
        resp = self.s3user.create_s3_account()
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
            write_bytes_mb = random.randint(10, 100)
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
        resp = self.s3user.create_s3_account()
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
            write_bytes_mb = random.randint(10, 100)
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
