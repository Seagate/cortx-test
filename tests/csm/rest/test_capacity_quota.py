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
import pytest
import os
import time
from http import HTTPStatus
from random import SystemRandom
from time import perf_counter_ns
from commons import configmanager
from commons import cortxlogging
from commons.constants import Rest as const
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.s3 import s3_misc
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib

# pylint: disable=too-many-instance-attributes
class TestCapacityQuota():
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
        cls.created_iam_users = set()
        cls.buckets_created = []
        cls.user_id = None
        cls.display_name = None
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUpload")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)

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
        self.user_id = resp.json()['tenant'] + "$" + payload["uid"]
        self.created_iam_users.add(self.user_id)
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        #self.akey = resp.json()["access_key"]
        #self.skey = resp.json()["secret_key"]
        self.bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        self.obj_name_prefix = "created_obj"
        self.obj_name = "{0}{1}".format(self.obj_name_prefix, perf_counter_ns())
        self.display_name = "iam-display-name-" + str(int(time.time_ns()))
        #self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
        #              self.bucket, self.akey, self.skey)
        self.cryptogen = SystemRandom()
        #assert s3_misc.create_bucket(self.bucket, self.akey, self.skey), "Failed to create bucket."

    def get_iam_user_payload(self, param=None):
        """
        Creates IAM user payload.
        """
        time.sleep(1)
        user_id = const.IAM_USER + str(int(time.time()))
        display_name = const.IAM_USER + str(int(time.time()))
        if param == "email":
            email = user_id + "@seagate.com"
            return user_id, display_name, email
        elif param == "a_key":
            access_key = user_id.ljust(const.S3_ACCESS_LL, "d")
            return user_id, display_name, access_key
        elif param == "s_key":
            secret_key = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            return user_id, display_name, secret_key
        elif param == "keys":
            access_key = user_id.ljust(const.S3_ACCESS_LL, "d")
            secret_key = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            return user_id, display_name, access_key, secret_key
        elif param == "tenant":
            return user_id, user_id, display_name
        else:
            return user_id, display_name

    def teardown_method(self):
        """
        Teardowm method for deleting s3 account created in setup.
        """
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

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40600')
    def test_40600(self):
        """
        Test that user can set and get the User level quota/capacity for S3 I AM user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40600"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp = self.csm_obj.set_user_quota(user_id, "user", "true", max_size, max_objects)
        assert response.status_code == HTTPStatus.OK, "Status code check failed to set user quota"
        self.log.info("Step 3: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id, "user")
        assert res.status_code == HTTPStatus.OK, "Status code check failed to get user quota"
        self.log.info("Step 4: Verify the user level quota fields as per above PUT request.")
        user_quota = res.json()
        assert user_quota['enabled'] == "True", "Status check failed for enabled field"
        assert user_quota['max_size'] == max_size, "Max size field not matched"
        assert user_quota['max_objects'] == max_objects, "Max objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40601')
    def test_40601(self):
        """
        Test that user can set and get the disabled User level quota/capacity fields for S3 user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40601"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp = self.csm_obj.set_user_quota(user_id, "user", "true", max_size, max_objects)
        assert response.status_code == HTTPStatus.OK, "Status code check failed to set user quota"
        self.log.info("Step 3: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id, "user")
        assert res.status_code == HTTPStatus.OK, "Status code check failed to get user quota"
        user_quota = res.json()
        self.log.info("Step 4: Verify the user level quota fields as per above PUT request.")
        assert user_quota['enabled'] == True, "Status check failed for enabled field"
        assert user_quota['max_size'] == max_size, "Max size field not matched"
        assert user_quota['max_objects'] == max_objects, "Max objects field not matched"
        self.log.info("Step 5: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40601"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp = self.csm_obj.set_user_quota(user_id, "user", "false", max_size, max_objects)
        assert response.status_code == HTTPStatus.OK, "Status code check failed to set user quota"
        self.log.info("Step 6: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id, "user")
        assert res.status_code == HTTPStatus.OK, "Status code check failed to get user quota"
        user_quota = res.json()
        self.log.info("Step 7: Verify the user level quota fields as per above PUT request.")
        assert user_quota['enabled'] == False, "Status check failed for enabled field"
        assert user_quota['max_size'] == max_size, "Max size field not matched"
        assert user_quota['max_objects'] == max_objects, "Max objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40602')
    def test_40602(self):
        """
        Test that user can set and get the User level quota/capacity fields for S3 user using get user info API.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40602"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp = self.csm_obj.set_user_quota(user_id, "user", "true", max_size, max_objects)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed to set user quota"
        self.log.info("Step 3: Perform GET I AM user info API to get user level quota fields.")
        res = self.csm_obj.get_iam_user(user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed to get user quota"
        user_quota = res.json()
        self.log.info("Step 4: Verify the user info level quota fields as per above PUT request.")
        assert user_quota['user_quota']['enabled'] == "True", "Status check failed for enabled field"
        assert user_quota['user_quota']['max_size'] == max_size, "Max size field not matched"
        assert user_quota['user_quota']['max_objects'] == max_objects, "Max objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40603')
    def test_40603(self):
        """
        Test that monitor user can not set the User level quota/capacity for S3 user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40603"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        resp = self.csm_obj.set_user_quota(user_id, "user", "true", max_size, max_objects,
                                           login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status code check failed to set user quota"
        self.log.info("Step 3: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id, "user")
        assert res.status_code == HTTPStatus.OK, "Status code check failed to get user quota"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40604')
    def test_40604(self):
        """
        Test that user can set and get the User level quota/capacity for S3 user under the tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user under the tenant.")
        self.log.info("Creating IAM user payload.")
        user_id, tenant, display_name = self.get_iam_user_payload("tenant")
        payload = {"uid": user_id, "tenant": tenant, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        self.log.info("Step 2: Perform PUT API(tenant$uid) to set user level quota fields")
        test_cfg = self.csm_conf["test_40604"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        tenant_user = tenant  + "$" + user_id
        resp = self.csm_obj.set_user_quota(tenant_user, "user", "true", max_size, max_objects)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed to set user quota"
        self.log.info("Step 3: Perform GET API(tenant$uid) to get user level quota fields.")
        res = self.csm_obj.get_user_quota(tenant_user, "user")
        assert res.status_code == HTTPStatus.OK, "Status code check failed to get user quota"
        self.log.info("Step 4: Verify the user level quota fields as per above PUT request.")
        user_quota = res.json()
        assert user_quota['enabled'] == "True", "Status check failed for enabled field"
        assert user_quota['max_size'] == max_size, "Max size field not matched"
        assert user_quota['max_objects'] == max_objects, "Max objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40605')
    def test_40605(self):
        """
        Test set/get API for User level quota/capacity with Invalid/empty fields. (S3 user)
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        self.log.info("Step 2: Perform PUT API to set user level quota with empty fields")
        resp = self.csm_obj.set_user_quota(user_id, "user", "", "", "")
        self.log.info("response :  %s", resp)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed to set user quota"
        self.log.info("Step 3: Perform PUT API to set user quota with empty fields")
        res = self.csm_obj.set_user_quota(user_id, "user", "", "", "", "")
        self.log.info("response :  %s", res)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed to set user quota"
        self.log.info("Step 4: PUT API to set user quota with invalid/empty user quota endpoint.")
        resp = self.csm_obj.set_user_quota("", "user", "", "", "", "")
        self.log.info("response :  %s", resp)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed to set user quota"
        self.log.info("Step 5: GET API to get user quota fields with invalid/empty user quota endpoint.")
        res = self.csm_obj.get_user_quota("", "user")
        self.log.info("response :  %s", res)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed to set user quota"
