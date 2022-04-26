# pylint: disable=too-many-lines
# !/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Tests System capacity scenarios using REST API
"""
import logging
import math
import random
import time
from http import HTTPStatus
from random import SystemRandom
from time import perf_counter_ns

import pytest

from commons import configmanager
from commons import cortxlogging
from commons.utils import assert_utils
from libs.csm.csm_interface import csm_api_factory
from libs.csm.rest.csm_rest_quota import GetSetQuota
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import s3_misc, s3_test_lib

class TestSystemCapacity():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_obj = csm_api_factory("rest")
        cls.cryptogen = SystemRandom()
        cls.log.info("Initiating Rest Client ...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.quota_obj = GetSetQuota()
        cls.created_iam_users = set()
        cls.s3_obj = s3_test_lib.S3TestLib()
        cls.buckets_created = []
        cls.user_id = None
        cls.display_name = None

    def setup_method(self):
        """
        Setup method for creating s3 user
        """
        self.log.info("Creating S3 account")
        self.log.info("Creating IAM user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        self.created_iam_users.add(resp.json()['tenant'] + "$" + payload["uid"])
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.bucket = "iam-user-bucket-" + str(int(time.time()))
        self.obj_name_prefix = "created_obj"
        self.obj_name = "{0}{1}".format(self.obj_name_prefix, perf_counter_ns())
        self.user_id = "iam-user-id-" + str(int(time.time_ns()))
        self.display_name = "iam-display-name-" + str(int(time.time_ns()))
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        self.cryptogen = SystemRandom()
        assert s3_misc.create_bucket(self.bucket, self.akey, self.skey), "Failed to create bucket."

    def teardown_method(self):
        """
        Teardowm method for deleting s3 account created in setup.
        """
        self.log.info("Deleting bucket %s & associated objects", self.bucket)
        assert s3_misc.delete_objects_bucket(
            self.bucket, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Deleting buckets %s & associated objects", self.buckets_created)
        buckets_deleted = []
        iam_deleted = []
        for bucket in self.buckets_created:
            resp = s3_misc.delete_objects_bucket(bucket[0], bucket[1], bucket[2])
            if resp:
                buckets_deleted.append(bucket)
            else:
                self.log.error("Bucket deletion failed for %s ", bucket)
        self.log.info("buckets deleted %s", buckets_deleted)
        for bucket in buckets_deleted:
            self.buckets_created.remove(bucket)

        self.log.info("Deleting iam account %s created in test", self.created_iam_users)
        for iam_user in self.created_iam_users:
            resp = s3_misc.delete_iam_user(iam_user[0], iam_user[1], iam_user[2])
            if resp:
                iam_deleted.append(iam_user)
            else:
                self.log.error("IAM deletion failed for %s ", iam_user)
        self.log.info("IAMs deleted %s", iam_deleted)
        for iam in iam_deleted:
            self.created_iam_users.remove(iam)
        assert_utils.assert_true(len(self.buckets_created) == 0, "Bucket deletion failed")
        assert_utils.assert_true(len(self.created_iam_users) == 0, "IAM deletion failed")
        self.log.info("[ENDED] ######### Teardown #########")

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40632')
    def test_40632(self):
        """
        Test set & get API for User level quota & capacity admin user - enable
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating IAM user with login as manage user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        self.created_iam_users.add(resp.json()['tenant'] + "$" + payload["uid"])
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.log.info("Step 2: Create bucket under above IAM user")
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
        self.bucket_name, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket_name, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Perform PUT API to set user level quota with random values")
        uid = resp1.json()['tenant'] + "$" + payload["uid"]
        test_cfg = self.csm_conf["test_40632"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp3 = self.quota_obj.set_user_quota(uid, "user","true", max_size, max_objects)
        assert_utils.assert_true(resp3[0],resp3[1])
        self.log.info("Step 4: Perform GET API to get user level quota")
        resp4 = self.quota_obj.get_user_quota(uid, "user")
        assert_utils.assert_true(resp4[0], resp4[1])
        self.log.info("Step 5: Perform Put operation for 1 object of max size")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=max_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 6: Perform Put operation of Random size and 1 object")
        random_size = self.cryptogen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 7: Delete object")
        assert s3_misc.delete_object(
            self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Step 8: Perform Put operation of small size and N object")
        small_size = math.floor(max_size/max_objects)
        for _ in range(0, max_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=small_size)
            assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 9: Perform Put operation of Random size and 1 object")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40633')
    def test_40633(self):
        """
        Test set & get API for User level quota & capacity manage user - enabled
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating IAM user with login as manage user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload, login_as="csm_user_manage")
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        self.created_iam_users.add(resp.json()['tenant'] + "$" + payload["uid"])
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.log.info("Step 2: Create bucket under above IAM user")
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket_name, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket_name, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Perform PUT API to set user level quota with random values")
        uid = resp1.json()['tenant'] + "$" + payload["uid"]
        test_cfg = self.csm_conf["test_40633"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp3 = self.quota_obj.set_user_quota(uid, "user", "true", max_size, max_objects)
        assert_utils.assert_true(resp3[0], resp3[1])
        self.log.info("Step 4: Perform GET API to get user level quota")
        resp4 = self.quota_obj.get_user_quota(uid, "user")
        assert_utils.assert_true(resp4[0], resp4[1])
        self.log.info("Step 5: Perform Put operation for 1 object of max size")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=max_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 6: Perform Put operation of Random size and 1 object")
        random_size = self.cryptogen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 7: Delete object")
        assert s3_misc.delete_object(
            self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Step 8: Perform Put operation of small size and N object")
        small_size = math.floor(max_size/max_objects)
        for _ in range(0, max_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=small_size)
            assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 9: Perform Put operation of Random size and 1 object")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40634')
    def test_40634(self):
        """
        Test set & get API for User level quota & capacity loop - random
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating IAM user with login as manage user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        self.created_iam_users.add(resp.json()['tenant'] + "$" + payload["uid"])
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.log.info("Step 2: Create bucket under above IAM user")
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket_name, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket_name, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Perform PUT API to set user level quota with random values")
        uid = resp1.json()['tenant'] + "$" + payload["uid"]
        test_cfg = self.csm_conf["test_40634"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp3 = self.quota_obj.set_user_quota(uid, "user", "true", max_size, max_objects)
        assert_utils.assert_true(resp3[0], resp3[1])
        test_cfg = self.csm_conf["test_40634"]
        for _ in range(0, test_cfg["num_iterations"]):
            self.log.info("Step 4: Perform GET API to get user level quota")
            resp4 = self.quota_obj.get_user_quota(uid, "user")
            assert_utils.assert_true(resp4[0], resp4[1])
            self.log.info("Step 5: Perform Put operation for 1 object of max size")
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=max_size)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Step 6: Perform Put operation of Random size and 1 object")
            random_size = self.cryptogen.randrange(1, max_size)
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=random_size)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Step 7: Delete object")
            assert s3_misc.delete_object(
                self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
            self.log.info("Step 8: Perform Put operation of small size and N object")
            small_size = math.floor(max_size/max_objects)
            for _ in range(0, max_objects):
                resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                                  self.akey, self.skey, object_size=small_size)
                assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Step 9: Perform Put operation of Random size and 1 object")
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=random_size)
            assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40635')
    def test_40635(self):
        """
        Test that if user set the disabled User level quota & capacity fields,
        other fields works as default.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating IAM user with login as manage user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload, login_as="csm_user_manage")
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        self.created_iam_users.add(resp.json()['tenant'] + "$" + payload["uid"])
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.log.info("Step 2: Create bucket under above IAM user")
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket_name, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket_name, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Perform PUT API to set user level quota with random values")
        uid = resp1.json()['tenant'] + "$" + payload["uid"]
        test_cfg = self.csm_conf["test_40635"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp3 = self.quota_obj.set_user_quota(uid, "user", "false", max_size, max_objects)
        assert_utils.assert_true(resp3[0], resp3[1])
        self.log.info("Step 4: Perform GET API to get user level quota")
        resp4 = self.quota_obj.get_user_quota(uid, "user")
        assert_utils.assert_true(resp4[0], resp4[1])
        self.log.info("Step 5: Perform Put operation for 1 object of max size")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=max_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 6: Perform Put operation of Random size and 1 object")
        random_size = self.cryptogen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 7: Delete object")
        assert s3_misc.delete_object(
            self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Step 8: Perform Put operation of small size and N object")
        small_size = math.floor(max_size/max_objects)
        for _ in range(0, max_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=small_size)
            assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 9: Perform Put operation of Random size and 1 object")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40636')
    def test_40636(self):
        """
        Test set & get API for User level quota & capacity admin user - enable
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating 2 IAM user with same uid but different tenant")
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"uid": self.user_id})
            optional_payload.update({"display_name": self.display_name})
            self.log.info("updated payload :  %s", optional_payload)
            resp = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            uid = resp.json()['tenant'] + "$" + optional_payload['uid']
            self.created_iam_users.add(uid)
            self.log.info("Step 2: Create bucket under above IAM user")
            self.akey = resp.json()["access_key"]
            self.skey = resp.json()["secret_key"]
            self.bucket_name = "iam-user-bucket-" + str(int(time.time()))
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          self.bucket_name, self.akey, self.skey)
            bucket_created = s3_misc.create_bucket(self.bucket_name, self.akey, self.skey)
            assert bucket_created, "Failed to create bucket"
            self.log.info("Step 3: Perform PUT API to set user level quota with random values")
            test_cfg = self.csm_conf["test_40636"]
            max_size = test_cfg["max_size"]
            max_objects = test_cfg["max_objects"]
            resp3 = self.quota_obj.set_user_quota(uid, "user", "true", max_size, max_objects)
            assert_utils.assert_true(resp3[0], resp3[1])
            self.log.info("Step 4: Perform GET API to get user level quota")
            resp4 = self.quota_obj.get_user_quota(uid, "user")
            assert_utils.assert_true(resp4[0], resp4[1])
            self.log.info("Step 5: Perform Put operation for 1 object of max size")
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=max_size)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Step 6: Perform Put operation of Random size and 1 object")
            random_size = self.cryptogen.randrange(1, max_size)
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=random_size)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Step 7: Delete object")
            assert s3_misc.delete_object(
                self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
            self.log.info("Step 8: Perform Put operation of small size and N object")
            small_size = math.floor(max_size / max_objects)
            for _ in range(0, max_objects):
                resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                                  self.akey, self.skey, object_size=small_size)
                assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("Step 9: Perform Put operation of Random size and 1 object")
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket_name,
                                              self.akey, self.skey, object_size=random_size)
            assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)
