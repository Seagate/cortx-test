# pylint: disable=too-many-lines
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
# pylint: disable-msg=too-many-statements
"""
Tests operations on S3 Users using REST API
"""

import json
import string
from string import Template
import logging
from http import HTTPStatus
import pytest
from commons.constants import Rest as const
from commons import cortxlogging
from commons import configmanager
from commons.utils import config_utils
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.params import TEST_DATA_FOLDER
from libs.csm.csm_setup import CSMConfigsCheck
from libs.s3 import s3_misc
from libs.csm.csm_interface import csm_api_factory
from config import CSM_REST_CFG


# pylint: disable-msg=too-many-public-methods
class TestS3user():
    """
    S3 user test class
    """

    @classmethod
    def setup_class(cls):
        """
        This is method is for test suite set-up
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("[STARTED] ######### Setup class #########")
        cls.log.info("Initializing test setups ......")
        cls.config = CSMConfigsCheck()
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        user_already_present = cls.config.check_predefined_s3account_present()
        if not user_already_present:
            user_already_present = cls.config.setup_csm_s3()
        assert user_already_present
        cls.buckets_created = []
        cls.account_created = []
        cls.iam_users_created = []
        cls.s3user = csm_api_factory("rest")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_s3_user.yaml")
        cls.log.info("Initiating Rest Client for Alert ...")
        if not system_utils.path_exists(TEST_DATA_FOLDER):
            system_utils.make_dirs(TEST_DATA_FOLDER)
        cls.log.info("[COMPLETED] ######### Setup class #########")

    def teardown_method(self):
        """"
        Teardown for deleting any S3 user which is not deleted due to test failure.
        """
        self.log.info("[STARTED] ######### Teardown #########")
        buckets_deleted = []
        iam_deleted = []
        s3_account_deleted = []
        self.log.info("Deleting buckets %s & associated objects", self.buckets_created)
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
        self.log.info("[COMPLETED] ######### Teardown #########")

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10744")
    def test_276(self):
        """
        Initiating the test case for the verifying success rest alert
        response.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.create_s3_account()
        self.log.debug("Verifying new S3 account got created successfully")
        assert response.status_code == HTTPStatus.CREATED.value
        self.log.debug("Verified new S3 account %s got created successfully",
                       response.json()["account_name"])
        self.account_created.append(response.json()["account_name"])
        assert self.s3user.verify_list_s3account_details()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10746")
    def test_290(self):
        """
        Initiating the test case for the verifying success rest alert response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.create_and_verify_s3account(
            user="valid", expect_status_code=HTTPStatus.CREATED.value)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1]["account_name"])
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10747")
    def test_291(self):
        """
        Initiating the test case for the verifying success rest alert response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.create_and_verify_s3account(
            user="invalid", expect_status_code=const.BAD_REQUEST)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10749")
    def test_293(self):
        """
        Initiating the test case for the verifying success rest alert response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.s3user.create_s3_account()
        resp = self.s3user.create_and_verify_s3account(
            user="duplicate", expect_status_code=const.CONFLICT)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10748")
    def test_292(self):
        """
        Initiating the test case for the verifying success rest alert response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.create_and_verify_s3account(
            user="missing", expect_status_code=const.BAD_REQUEST)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10750")
    def test_294(self):
        """
        Initiating the test case for unauthorized user try to create
        s3account user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.rest_login(login_as="s3account_user")
        assert response.status_code == const.UNAUTHORIZED
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10752")
    def test_586(self):
        """
        Initiating the test case for the verifying success rest alert response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.edit_and_verify_s3_account_user(
            user_payload="valid")
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1])
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("EOS-27117 Test is not valid anymore")
    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10753")
    def test_590(self):
        """
        Initiating the test case for REST API to update S3
        account/non_existing_user using PATCH request.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.edit_s3_account_user(
            "non_existing_user", login_as="s3account_user")
        assert response.status_code == const.FORBIDDEN
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10754")
    def test_587(self):
        """
        Initiating the test case for user Does not update secret/access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.edit_and_verify_s3_account_user(
            user_payload="unchanged_access")
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1])
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10755")
    def test_592(self):
        """
        Initiating the test case for Sender has no permission to update s3 account
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        # verifying No IAM user should present on first visit to s3 account
        response = self.s3user.edit_s3_account_user(
            username=self.s3user.config["s3account_user"]["username"], login_as="csm_admin_user")
        assert response.status_code == const.FORBIDDEN
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10756")
    def test_615(self):
        """
        Initiating the test case for user Does not update secret/access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.edit_and_verify_s3_account_user(
            user_payload="no_payload")
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1])
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10757")
    def test_598(self):
        """
        Initiating the test case for user only reset access key value False
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.edit_and_verify_s3_account_user(
            user_payload="only_reset_access_key")
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1])
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10758")
    def test_595(self):
        """
        Initiating the test case for user only reset access key value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.edit_and_verify_s3_account_user(
            user_payload="only_reset_access_key")
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1])
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10759")
    def test_606(self):
        """
        Initiating the test case for user only password field
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.s3user.edit_and_verify_s3_account_user(
            user_payload="only_password")
        assert_utils.assert_true(resp[0], resp[1])
        self.account_created.append(resp[1])
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10760")
    def test_488(self):
        """
        Initiating the test case for Successful delete account user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.delete_and_verify_s3_account_user()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10761")
    def test_491(self):
        """
        Initiating the test case for delete non existing s3account user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.delete_s3_account_user("non_existing_user")
        assert response.status_code == const.METHOD_NOT_FOUND
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10762")
    def test_492(self):
        """
        Initiating the test case for delete s3account user without permission
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.delete_s3_account_user(
            self.s3user.config["s3account_user"]["username"], login_as="csm_admin_user")
        assert response.status_code == const.CONFLICT
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("EOS-27117 Test is not valid anymore")
    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-10763")
    def test_493(self):
        """
        Initiating the test case for delete s3account without account name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        # passing user name as blank
        response = self.s3user.delete_s3_account_user(
            username="", login_as="s3account_user")
        assert response.status_code == const.METHOD_NOT_FOUND
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-12842")
    def test_1914(self):
        """
        Initiating the test to test that error is returned when payload is incorrect
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Fetching the s3 account name")
        account_name = self.s3user.config["s3account_user"]["username"]

        self.log.info(
            "Creating payload with invalid password for the Patch request")
        payload = self.csm_conf["test_1914"]["payload"]

        self.log.info(
            "Providing invalid password for s3 account %s in Patch request", account_name)

        response = self.s3user.edit_s3_account(
            username=account_name,
            payload=json.dumps(payload))

        self.log.info(
            "Verifying response returned for s3 account %s", account_name)
        assert response.status_code == const.BAD_REQUEST

        self.log.info(
            "Verified that response returned for invalid password in Patch "
            "request for s3 account %s is %s", account_name, response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("EOS-27117 Test is not valid anymore")
    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-17188")
    def test_1915(self):
        """
        Test that error should be returned when s3 user enters some other s3 user's account name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that error should be returned when s3 user enters some"
            " other s3 user's account name")
        test_cfg = self.csm_conf["test_1915"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = data[resp_msg_index]
        self.log.info("Creating new S3 account for test purpose")
        response = self.s3user.create_s3_account()

        self.log.debug("Verifying new S3 account got created successfully")
        assert response.status_code == HTTPStatus.CREATED.value
        self.log.debug("Verified new S3 account %s got created successfully",
                       response.json()["account_name"])

        s3_acc = response.json()["account_name"]
        self.account_created.append(s3_acc)

        self.log.info(
            "Logging in with with existing s3 account %s and trying to change the "
            "password for new %s account", self.s3user.config["s3account_user"]["username"], s3_acc)
        response = self.s3user.edit_s3_account_user(
            username=s3_acc, payload="valid", login_as="s3account_user")

        self.log.debug("Verifying the response returned %s", response)
        assert response.status_code, const.FORBIDDEN
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(response.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(response.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(response.json()["message"], msg)

        self.log.debug("Verified that expected status code %s and expected response "
                       "message %s was returned", response.status_code, response.json())

        self.log.info(
            "Verified that is returned when s3 user enters some other s3 user's account name")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28932")
    def test_28932(self):
        """
        Test create S3 account with different combination of the valid AWS access key and run IO
        using it.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        access_keys = []
        access_keys.append("_" + config_utils.gen_rand_string(length=const.S3_ACCESS_LL))
        access_keys.append("a" * const.S3_ACCESS_UL)
        access_keys.append(config_utils.gen_rand_string(chars=string.digits,
                                                        length=const.S3_ACCESS_LL))
        for access_key in access_keys:
            self.log.info("Creating custom S3 account with access key %s.", access_key)
            user_data = self.s3user.create_custom_s3_payload("valid")
            user_data.update({"access_key": access_key})
            resp = self.s3user.create_custom_s3_user(user_data)

            self.log.info("Verify Status code of the Create user operation.")
            assert resp.status_code == HTTPStatus.CREATED.value, "Unexpected Status code"

            self.log.info("Verify created S3 account returns correct access key.")
            assert resp.json()["access_key"] == access_key, "Access key mismatch"

            akey = resp.json()["access_key"]
            skey = resp.json()["secret_key"]
            s3_user = resp.json()["account_name"]
            self.account_created.append(s3_user)
            iam_user = f"iam{s3_user}"
            bucket = f"bucket{s3_user}"
            obj = f"object{s3_user}.txt"

            self.log.info("Verify Create IAM user: %s with access key: %s and secret key: %s",
                          iam_user, akey, skey)
            assert s3_misc.create_iam_user(iam_user, akey, skey), "Failed to create IAM user."
            self.iam_users_created.append([iam_user, akey, skey])
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s", bucket,
                          akey, skey)
            assert s3_misc.create_bucket(bucket, akey, skey), "Failed to create bucket."
            self.buckets_created.append([bucket, akey, skey])
            self.log.info("Verify Put Object: %s in the bucket: %s with access key: %s and secret "
                          "key: %s", obj, bucket, akey, skey)
            assert s3_misc.create_put_objects(obj, bucket, akey, skey), "Put object Failed"

            self.log.info("Verify Delete Object: %s and bucket: %s with access key: %s and "
                          "secret key: %s", obj, bucket, akey, skey)
            assert s3_misc.delete_objects_bucket(bucket, akey, skey), "Failed to delete bucket."
            self.buckets_created.remove([bucket, akey, skey])
            self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                          iam_user, akey, skey)
            assert s3_misc.delete_iam_user(iam_user, akey, skey), "Failed to delete IAM user."
            self.iam_users_created.remove([iam_user, akey, skey])
            self.log.info("Verify Delete S3 user: %s with access key: %s and secret key: %s",
                          s3_user, akey, skey)
            resp = self.s3user.delete_s3_account_user(s3_user)
            assert resp.status_code == HTTPStatus.OK.value, "Failed to delete S3 user."
            self.account_created.remove(s3_user)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28924")
    def test_28924(self):
        """
        Test create S3 account with Invalid AWS secret key.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28924"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        secret_keys = []
        self.log.info("Key 1: Empty Secret key")
        secret_keys.append("")

        sk_len = const.S3_SECRET_LL - 1
        self.log.info("Key 2: Secret key less than %s", const.S3_SECRET_LL)
        secret_keys.append("a" * sk_len)

        sk_len = const.S3_SECRET_UL + 1
        self.log.info("Key 3: Secret key greather than %s", const.S3_SECRET_UL)
        secret_keys.append("x" * sk_len)

        for secret_key in secret_keys:
            self.log.info("[START] Secret Key : %s", secret_key)
            self.log.info("Creating custom S3 account with Secret key %s.", secret_key)
            user_data = self.s3user.create_custom_s3_payload("valid")
            user_data.update({"secret_key": secret_key})
            resp = self.s3user.create_custom_s3_user(user_data)
            assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed."
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                assert_utils.assert_equals(resp.json()["message"], msg)

            self.log.info("[END] Secret Key : %s", secret_key)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28773")
    def test_28773(self):
        """
        Test create S3 account with Invalid AWS access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28773"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        access_keys = []
        self.log.info("Key 1: Empty Access key")
        access_keys.append("")

        ak_len = const.S3_ACCESS_LL - 1
        self.log.info("Key 2: Access key less than %s", const.S3_ACCESS_LL)
        access_keys.append("a" * ak_len)

        ak_len = const.S3_ACCESS_UL + 1
        self.log.info("Key 3: Access key greather than %s", const.S3_ACCESS_UL)
        access_keys.append("x" * ak_len)

        self.log.info("Key 4: Access key special character except _")
        access_keys.append(string.punctuation)

        for access_key in access_keys:
            self.log.info("[START] Access Key : %s", access_key)
            self.log.info("Creating custom S3 account with access key %s.", access_key)
            user_data = self.s3user.create_custom_s3_payload("valid")
            user_data.update({"access_key": access_key})
            resp = self.s3user.create_custom_s3_user(user_data)
            assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed."
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                assert_utils.assert_equals(resp.json()["message"].lower(),
                                           Template(msg).substitute(A="_schema",
                                                                    B="access_key").lower())

            self.log.info("[END] Access Key : %s", access_key)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28925")
    def test_28925(self):
        """
        Test create S3 account with missing AWS access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28925"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        result, resp = self.s3user.create_verify_s3_custom(
            "missing_access", expected_response=HTTPStatus.BAD_REQUEST.value)
        assert result, "Status code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28926")
    def test_28926(self):
        """
        Test create S3 account with missing AWS secret key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28926"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        result, resp = self.s3user.create_verify_s3_custom(
            "missing_secret", expected_response=HTTPStatus.BAD_REQUEST.value)
        assert result, "Status code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28927")
    def test_28927(self):
        """
        Test create S3 account with duplicate usernames
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28927"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        # verify_err_args=True not working for RGW yet
        result, resp = self.s3user.create_verify_s3_custom(
            "duplicate_user", expected_response=HTTPStatus.CONFLICT.value)
        assert result, "Status code check or error arg check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28928")
    def test_28928(self):
        """
        Test create S3 account with duplicate email address
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28928"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        # verify_err_args=True not working for RGW yet
        result, resp = self.s3user.create_verify_s3_custom(
            "duplicate_email", expected_response=HTTPStatus.CONFLICT.value)
        assert result, "Status code check or error arg check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28929")
    def test_28929(self):
        """
        Test create S3 account with duplicate AWS access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28929"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        # verify_err_args=True not working for RGW yet
        result, resp = self.s3user.create_verify_s3_custom(
            "duplicate_access", expected_response=HTTPStatus.CONFLICT.value)
        assert result, "Status code check or error arg check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28930")
    def test_28930(self):
        """
        Test create S3 account with duplicate AWS secret key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        result, resp = self.s3user.create_verify_s3_custom(
            "duplicate_secret", expected_response=HTTPStatus.CREATED.value)
        assert result, "Status code check failed."

        akey = resp.json()["access_key"]
        skey = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)
        iam_user = f"iam{s3_user}"
        bucket = f"bucket{s3_user}"
        obj = f"object{s3_user}.txt"
        self.log.info("Verify Create IAM user: %s with access key: %s and secret key: %s",
                      iam_user, akey, skey)
        assert s3_misc.create_iam_user(iam_user, akey, skey), "Failed to create IAM user."
        self.iam_users_created.append([iam_user, akey, skey])
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s", bucket,
                      akey, skey)
        assert s3_misc.create_bucket(bucket, akey, skey), "Failed to create bucket."
        self.buckets_created.append([bucket, akey, skey])
        self.log.info("Verify Put Object: %s in the bucket: %s with access key: %s and secret "
                      "key: %s", obj, bucket, akey, skey)
        assert s3_misc.create_put_objects(obj, bucket, akey, skey), "Put object Failed"

        self.log.info("Verify Delete Object: %s and bucket: %s with access key: %s and "
                      "secret key: %s", obj, bucket, akey, skey)
        assert s3_misc.delete_objects_bucket(bucket, akey, skey), "Failed to delete bucket."
        self.buckets_created.remove([bucket, akey, skey])
        self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                      iam_user, akey, skey)
        assert s3_misc.delete_iam_user(iam_user, akey, skey), "Failed to delete IAM user."
        self.iam_users_created.remove([iam_user, akey, skey])
        self.log.info("Verify Delete S3 user: %s with access key: %s and secret key: %s",
                      s3_user, akey, skey)
        resp = self.s3user.delete_s3_account_user(s3_user)
        assert resp.status_code == HTTPStatus.OK.value, "Failed to delete S3 user"
        self.account_created.remove(s3_user)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28931")
    def test_28931(self):
        """
        Test create , get, edit and delete max number of S3 account with custom AWS access key and
        secret key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_28931"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        resp = self.s3user.list_all_created_s3account()
        assert resp.status_code == HTTPStatus.OK, "List S3 account failed."
        user_data = resp.json()
        self.log.info("List user response : %s", user_data)
        existing_user = len(user_data['s3_accounts'])
        self.log.info("Existing S3 users count: %s", existing_user)
        self.log.info("Max S3 users : %s", const.MAX_S3_USERS)
        new_users = const.MAX_S3_USERS - existing_user
        self.log.info("New users to create: %s", new_users)
        created_users = []
        self.log.info("Creating %s S3 users...", new_users)
        for i in range(new_users):
            self.log.info("[START] Create User count : %s", i + 1)
            result, resp = self.s3user.create_verify_s3_custom("valid")
            assert result, "Status code check failed for user"
            user_data = resp.json()
            usr = user_data["account_name"]
            self.log.info("Created S3 user : %s", usr)
            created_users.append(user_data)
            self.account_created.append(usr)
            self.log.info("[END] Create User count : %s", i + 1)

        #  check error on 1001 user
        resp = self.s3user.list_all_created_s3account()
        assert resp.status_code == HTTPStatus.OK, "List S3 account failed."
        user_data = resp.json()
        s3_users = user_data['s3_accounts']
        self.log.info("Listed user count : %s", len(s3_users))
        err_msg = f"Number of users less than {const.MAX_S3_USERS}"
        assert len(s3_users) == const.MAX_S3_USERS, err_msg
        result, resp = self.s3user.\
            create_verify_s3_custom("valid", expected_response=HTTPStatus.FORBIDDEN.value)
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        # add pre-defined user to the created_user
        # create loop
        for created_user in created_users:
            self.log.info("-" * 50)
            akey = created_user["access_key"]
            skey = created_user["secret_key"]
            usr = created_user["account_name"]
            self.log.info("Creating IAM users for %s user", usr)
            iam_users_cnt = 0
            for i in range(const.MAX_IAM_USERS):
                iam_user = f"{usr}iam{i}"
                self.log.info("Verify Create IAM user: %s with access key: %s and secret key: %s",
                              iam_user, akey, skey)
                if s3_misc.create_iam_user(iam_user, akey, skey):
                    iam_users_cnt = iam_users_cnt + 1
                    self.log.info("IAM user count : %s", iam_users_cnt)
                    self.iam_users_created.append([iam_user, akey, skey])
                else:
                    assert False, "Failed to create IAM user."
            self.log.info("Creating Buckets and objects for %s user", usr)
            bucket_cnt = 0
            for i in range(const.MAX_BUCKETS):
                self.log.info("[START] Create Bucket count : %s", i + 1)
                bucket = f"{usr}bucket{i}"
                self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                              bucket, akey, skey)
                if s3_misc.create_bucket(bucket, akey, skey):
                    bucket_cnt = bucket_cnt + 1
                    self.buckets_created.append([bucket, akey, skey])
                else:
                    assert False, "Failed to create bucket."
                obj = f"{bucket}obj{i}.txt"
                self.log.info("Verify Put Object: %s in the bucket: %s with access key: %s and "
                              "secret key: %s", obj, bucket, akey, skey)
                if not s3_misc.create_put_objects(obj, bucket, akey, skey):
                    assert False, "Put object Failed"
                self.log.info("[END] Create Bucket count : %s", i + 1)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags("TEST-28933")
    def test_28933(self):
        """
        Test create S3 account with different combination of the valid AWS secret key and run IO
        using it.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        secret_keys = []
        secret_keys.append("_" + config_utils.gen_rand_string(length=const.S3_SECRET_LL))
        secret_keys.append("a" * const.S3_SECRET_UL)
        secret_keys.append(config_utils.gen_rand_string(chars=string.digits,
                                                        length=const.S3_SECRET_LL))
        secret_keys.append(string.punctuation)

        for secret_key in secret_keys:
            self.log.info("-" * 50)
            self.log.info("Creating custom S3 account with secret key: %s.", secret_key)
            user_data = self.s3user.create_custom_s3_payload("valid")
            user_data.update({"secret_key": secret_key})
            resp = self.s3user.create_custom_s3_user(user_data)

            self.log.info("Verify Status code of the Create user operation.")
            assert resp.status_code == HTTPStatus.CREATED.value, "Unexpected Status code"
            self.account_created.append(resp.json()["account_name"])
            self.log.info("Verify created S3 account returns correct secret key.")
            assert resp.json()["secret_key"] == secret_key, "Secret key mismatch"

            akey = resp.json()["access_key"]
            skey = resp.json()["secret_key"]
            s3_user = resp.json()["account_name"]
            iam_user = f"iam{s3_user}"
            bucket = f"bucket{s3_user}"
            obj = f"object{s3_user}.txt"

            self.log.info("Verify Create IAM user: %s with access key: %s and secret key: %s",
                          iam_user, akey, skey)
            assert s3_misc.create_iam_user(iam_user, akey, skey), "Failed to create IAM user."
            self.iam_users_created.append([iam_user, akey, skey])
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s", bucket,
                          akey, skey)
            assert s3_misc.create_bucket(bucket, akey, skey), "Failed to create bucket."
            self.buckets_created.append([bucket, akey, skey])
            self.log.info("Verify Put Object: %s in the bucket: %s with access key: %s and secret "
                          "key: %s", obj, bucket, akey, skey)
            assert s3_misc.create_put_objects(obj, bucket, akey, skey), "Put object Failed"

            self.log.info("Verify Delete Object: %s and bucket: %s with access key: %s and "
                          "secret key: %s", obj, bucket, akey, skey)
            assert s3_misc.delete_objects_bucket(bucket, akey, skey), "Failed to delete bucket."
            self.buckets_created.remove([bucket, akey, skey])
            self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                          iam_user, akey, skey)
            assert s3_misc.delete_iam_user(iam_user, akey, skey), "Failed to delete IAM user."
            self.iam_users_created.remove([iam_user, akey, skey])
            self.log.info("Verify Delete S3 user: %s with access key: %s and secret key: %s",
                          s3_user, akey, skey)
            resp = self.s3user.delete_s3_account_user(s3_user)
            assert resp.status_code == HTTPStatus.OK.value, "Failed to delete S3 user"
            self.account_created.remove(s3_user)
            self.log.info("-" * 50)
        self.log.info("##### Test completed -  %s #####", test_case_name)
