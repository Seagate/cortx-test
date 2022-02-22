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
"""Tests various operations on IAM users using REST API
NOTE: These tests are no longer valid as CSM will no longer support IAM user operations.
"""
import logging
import time
from http import HTTPStatus
import os
from random import SystemRandom
import pytest

from commons import configmanager
from commons import cortxlogging
from commons.constants import Rest as const
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CSM_REST_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.s3.s3_test_lib import S3TestLib



class TestIamUser():
    """REST API Test cases for IAM users"""

    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_iam_user.yaml")
        cls.log.info("Ended test module setups")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_s3account_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3()
        assert setup_ready
        cls.created_iam_users = set()
        cls.rest_iam_user = RestIamUser()
        cls.log.info("Initiating Rest Client ...")

    def teardown_method(self):
        """Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        for user in self.created_iam_users:
            self.rest_iam_user.delete_iam_user(
                login_as="s3account_user", user=user)
        self.log.info("Teardown ended")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10732')
    def test_1133(self):
        """Test that IAM users are not permitted to login
          """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        status_code = self.csm_conf["test_1133"]
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_name = response['user_name']
        self.created_iam_users.add(response['user_name'])
        assert (
                self.rest_iam_user.iam_user_login(user=user_name) == status_code["status_code"])
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14749')
    def test_1041(self):
        """Test that S3 account should have access to create IAM user from back end
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Creating IAM user")
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        print(status)
        self.log.info(
            "Verifying status code returned is 200 and response is not null")
        assert status, response

        for key, value in response.items():
            self.log.info("Verifying %s is not empty", key)
            assert value

        self.log.info("Verified that S3 account %s was successfully able to create IAM user: %s",
                      self.rest_iam_user.config["s3account_user"]["username"], response)

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17189')
    def test_1022(self):
        """
        Test that IAM user is not able to execute and access the CSM REST APIs.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.debug(
            "Verifying that IAM user is not able to execute and access the CSM REST APIs")
        assert self.rest_iam_user.verify_unauthorized_access_to_csm_user_api()
        self.log.debug(
            "Verified that IAM user is not able to execute and access the CSM REST APIs")
        self.log.info("##### Test ended -  %s #####", test_case_name)


class TestIamUserRGW():
    """
    Tests related to RGW
    """

    @classmethod
    def setup_class(cls):
        """
        setup class
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("[START] CSM setup class started.")
        cls.log.info("Initializing test configuration...")
        cls.csm_obj = csm_api_factory("rest")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_iam_user.yaml")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_csm_user_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_users()
        assert setup_ready
        cls.created_iam_users = set()
        cls.cryptogen = SystemRandom()
        cls.file_size = cls.cryptogen.randrange(10, 100)
        cls.log.info("[END] CSM setup class completed.")

    def teardown_method(self):
        """Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        for user in self.created_iam_users:
            # TODO delete iam user
            self.log.info("deleting iam user %s", user)
        self.log.info("Teardown ended")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35603')
    def test_35603(self):
        """
        Test create IAM User with Invalid uid and display-name parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing with empty UID")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload["uid"] = ""
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for empty uid"
        self.log.info("[END] Testing with empty UID")

        self.log.info("[START] Testing with empty display name")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload["display_name"] = ""
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for empty display name"
        self.log.info("[END] Testing with empty display name")

        self.log.info("[START] Testing with empty UID and display name")
        payload = {"uid": "", "display_name": ""}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for empty uid and display name"
        self.log.info("[END] Testing with empty UID and display name")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35604')
    def test_35604(self):
        """
        Test create IAM User with missing uid and display-name parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing with missing UID")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="loaded")
        payload.pop("uid")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status check failed for missing uid"
        self.log.info("[END] Testing with missing UID")

        self.log.info("[START] Testing with missing display name")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="loaded")
        payload.pop("display_name")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for missing display name"
        self.log.info("[END] Testing with missing display name")

        self.log.info("[START] Testing with missing UID and display name")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="loaded")
        payload.pop("display_name")
        payload.pop("uid")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for missing uid and display name"
        self.log.info("[END] Testing with missing UID and display name")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35605')
    def test_35605(self):
        """
        Test create IAM User with mandatory/Non-mandatory parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with basic parameters")
        result, resp = self.csm_obj.verify_create_iam_user_rgw(user_type="valid",
                                                               verify_response=True)
        assert result, "Failed to create IAM user using basic parameters."
        self.log.info("Response : %s", resp)
        self.log.info("[END]Creating IAM user with basic parameters")
        self.created_iam_users.add(resp['user_id'])

        self.log.info("[START] Creating IAM user with all parameters")
        result, resp = self.csm_obj.verify_create_iam_user_rgw(user_type="loaded",
                                                               verify_response=True)
        assert result, "Failed to create IAM user using all parameters."
        self.log.info("Response : %s", resp)
        self.log.info("[END]Creating IAM user with all parameters")
        self.created_iam_users.add(resp['user_id'])
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35606')
    def test_35606(self):
        """
        Test create IAM User with Invalid Keys and Capability parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing with invalid access key")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"access_key": ""})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status check failed for missing uid"
        self.log.info("[END] Testing with invalid access key")

        self.log.info("[START] Testing with invalid secret key")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"secret_key": ""})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status check failed for missing uid"
        self.log.info("[END] Testing with invalid secret key")

        self.log.info("[START] Testing with invalid key-type")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"key_type": "abc"})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status check failed for missing uid"
        self.log.info("[END] Testing with invalid key-type")


        self.log.info("[START] Testing with invalid capability parameter")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"user_caps": ""})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status check failed for missing uid"
        self.log.info("[END] Testing with invalid capability parameter")

        self.log.info("[START] Testing with invalid token")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        self.log.info("payload :  %s", payload)
        headers = {'Authorization': 'abc'}
        resp = self.csm_obj.restapi.rest_call("post", endpoint=CSM_REST_CFG["s3_iam_user_endpoint"],
                                                json_dict=payload,
                                                headers=headers)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED, "Status check failed for invalid token"
        self.log.info("[END] Testing with invalid token")

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35607')
    def test_35607(self):
        """
        Test create IAM User with csm monitor user.( non admin)
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with basic parameters")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload,
                            login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Failed to create IAM user"
        self.log.info("TODO Verify Response : %s", resp)
        self.log.info("[END]Creating IAM user with basic parameters")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35929')
    def test_35929(self):
        """
        Test create IAM User with random selection of optional parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with random selection of optional parameters")
        optional_payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(optional_payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
        self.created_iam_users.add(optional_payload['uid'])
        resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
        assert_utils.assert_true(resp[0], f"Value mismatch found for key {resp[1]} , "
                                          f"expected was {resp[2]}, received {resp[3]}")
        self.log.info("Verified Response")
        self.log.info("[END]Creating IAM user with random selection of optional parameters")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35930')
    def test_35930(self):
        """
        Test create MAX IAM Users with random selection of optional parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating %s IAM user with random selection of optional parameters",
                      const.MAX_IAM_USERS)
        for cnt in range(const.MAX_IAM_USERS):
            self.log.info("Creating IAM user number %s with random selection of optional "
                          "parameters", cnt)
            optional_payload = self.csm_obj.iam_user_payload_rgw("random")
            resp = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
            self.created_iam_users.add(optional_payload['uid'])
            resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
            assert_utils.assert_true(resp[0], f"Value mismatch found for key {resp[1]} , "
                                              f"expected was {resp[2]}, received {resp[3]}")
        self.log.info("[END]Creating Max IAM user with random selection of optional parameters")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35931')
    def test_35931(self):
        """
        Test create IAM users with different tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM users with different tenant")
        bucket_name = "iam_user_bucket_" + str(int(time.time()))
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            resp = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
            self.created_iam_users.add(optional_payload['uid'])
            resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
            assert_utils.assert_true(resp[0], f"Value mismatch found for key {resp[1]} , "
                                              f"expected was {resp[2]}, received {resp[3]}")
            self.log.info("Create bucket and perform IO")
            s3_obj = S3TestLib(access_key=resp["keys"][0]["access_key"],
                               secret_key=resp["keys"][0]["secret_key"])
            self.log.info("Step: Verify create bucket")
            status, resp = s3_obj.create_bucket(bucket_name)
            assert_utils.assert_true(status, resp)
            test_file = "test-object.txt"
            file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
            if os.path.exists(file_path_upload):
                os.remove(file_path_upload)
            system_utils.create_file(file_path_upload, self.file_size)
            self.log.info("Step: Verify put object.")
            resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                     file_path=file_path_upload)
            self.log.info("Removing uploaded object from a local path.")
            os.remove(file_path_upload)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step: Verify get object.")
            resp = s3_obj.get_object(bucket_name, test_file)
            assert_utils.assert_false(resp[0], resp)
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35932')
    def test_35932(self):
        """
        Test create IAM user with suspended true, and perform IO
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with suspended")
        uid = "iam_user_1_" + str(int(time.time()))
        bucket_name = "iam_user_bucket_" + str(int(time.time()))
        self.log.info("Creating new iam user  %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        payload.update({"suspended": True})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
        self.created_iam_users.add(uid)
        resp = self.csm_obj.compare_iam_payload_response(resp, payload)
        assert_utils.assert_true(resp[0], f"Value mismatch found for key {resp[1]} , "
                                          f"expected was {resp[2]}, received {resp[3]}")
        self.log.info("Verify create bucket")
        s3_obj = S3TestLib(access_key=resp["keys"][0]["access_key"],
                           secret_key=resp["keys"][0]["secret_key"])
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_false(status, resp)
        self.log.info("[END]Creating IAM user with suspended")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35933')
    def test_35933(self):
        """
        Create user and check max bucket parameter
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with max bucket 1")
        uid = "iam_user_1_" + str(int(time.time()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        payload.update({"max_buckets": 1})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
        self.created_iam_users.add(uid)
        resp = self.csm_obj.compare_iam_payload_response(resp, payload)
        assert_utils.assert_true(resp[0], f"Value mismatch found for key {resp[1]} , "
                                          f"expected was {resp[2]}, received {resp[3]}")
        for bucket_cnt in range(2):
            bucket_name = "iam_user_bucket_" + str(bucket_cnt) + str(int(time.time()))
            # Create bucket with bucket_name and perform IO
            s3_obj = S3TestLib(access_key=resp["keys"][0]["access_key"],
                               secret_key=resp["keys"][0]["secret_key"])
            status, resp = s3_obj.create_bucket(bucket_name)
            if bucket_cnt == 0:
                assert_utils.assert_true(status, resp)
                test_file = "test-object.txt"
                file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
                if os.path.exists(file_path_upload):
                    os.remove(file_path_upload)
                system_utils.create_file(file_path_upload, self.file_size)
                resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                         file_path=file_path_upload)
                self.log.info("Removing uploaded object from a local path.")
                os.remove(file_path_upload)
                assert_utils.assert_true(resp[0], resp[1])
                self.log.info("Step: Verify get object.")
                resp = s3_obj.get_object(bucket_name, test_file)
                assert_utils.assert_false(resp[0], resp)
            else:
                assert_utils.assert_false(status, resp)
        self.log.info("[END]Creating IAM user with max bucket 1")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35934')
    def test_35934(self):
        """
        Create user and check max bucket parameter
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with max buckets")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
        self.created_iam_users.add(payload["uid"])
        resp = self.csm_obj.compare_iam_payload_response(resp, payload)
        assert_utils.assert_true(resp[0], f"Value mismatch found for key {resp[1]} , "
                                          f"expected was {resp[2]}, received {resp[3]}")
        for bucket_cnt in range(1001):
            bucket_name = "iam_user_bucket_" + str(bucket_cnt) + str(int(time.time()))
            # Create bucket with bucket_name and perform IO
            s3_obj = S3TestLib(access_key=resp["keys"][0]["access_key"],
                               secret_key=resp["keys"][0]["secret_key"])
            status, resp = s3_obj.create_bucket(bucket_name)
            if bucket_cnt < 1000:
                assert_utils.assert_true(status, resp)
                test_file = "test-object.txt"
                file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
                if os.path.exists(file_path_upload):
                    os.remove(file_path_upload)
                system_utils.create_file(file_path_upload, self.file_size)
                resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                         file_path=file_path_upload)
                self.log.info("Removing uploaded object from a local path.")
                os.remove(file_path_upload)
                assert_utils.assert_true(resp[0], resp[1])
                self.log.info("Step: Verify get object.")
                resp = s3_obj.get_object(bucket_name, test_file)
                assert_utils.assert_false(resp[0], resp)
            else:
                assert_utils.assert_false(status, resp)
        self.log.info("[END]Creating IAM user with max buckets")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35935')
    def test_35935(self):
        """
        Create user with generate-keys=false
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user with generate-keys=false")
        self.log.info("Creating new iam user")
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"generate-keys": False})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user creation failed")
        self.created_iam_users.add(payload["uid"])
        if resp["keys"][0]["access_key"] != "":
            assert_utils.assert_true(False, "access key is available in response")
        elif resp["keys"][0]["secret_key"] != "":
            assert_utils.assert_true(False, "secret key is available in response")
        self.log.info("[END]Creating IAM user with generate-keys=false")
        self.log.info("##### Test completed -  %s #####", test_case_name)
