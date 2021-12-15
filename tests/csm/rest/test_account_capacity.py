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
import random
import time
from http import HTTPStatus

import pytest

from commons import cortxlogging
from commons.utils import assert_utils
from libs.csm.rest.csm_rest_acc_capacity import AccountCapacity
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3 import s3_misc


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

    def teardown_method(self):
        """
        Teardown for deleting any account and buckets created during tests
        """
        self.log.info("[STARTED] ######### Teardown #########")
        self.log.info("Deleting buckets %s & associated objects", self.buckets_created)
        for bucket in self.buckets_created:
            assert s3_misc.delete_objects_bucket(bucket[0], bucket[1], bucket[2]), \
                "Failed to delete bucket."
        self.log.info("Deleting S3 account %s created in test", self.account_created)
        for account in self.account_created:
            resp = self.s3user.delete_s3_account_user(account)
            assert resp.status_code == HTTPStatus.OK, "Failed to delete account"

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
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)
        total_cap = 0
        for _ in range(10):
            bucket = "bucket%s" % int(time.time())
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket."
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            self.log.info("[Start] Put operations")
            obj = f"object{s3_user}.txt"
            write_bytes_mb = random.randint(10, 100)
            total_cap = total_cap + write_bytes_mb
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, access_key, secret_key, object_size=write_bytes_mb)
            assert resp, "Put object Failed"
            self.log.info("[End] Put operations")
            self.log.info("verify capacity of account after put operations")
            s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
            resp = self.acc_capacity.verify_account_capacity(s3_account)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("verified capacity of account after put operations")
        self.log.info("##### Test ended -  %s #####", test_case_name)
