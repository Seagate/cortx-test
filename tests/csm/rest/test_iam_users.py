#Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
"""
Tests various operations on IAM users using REST API
"""
import logging
from string import Template
import time
from http import HTTPStatus
import os
import secrets
import string
from random import SystemRandom
import pytest
import yaml
from botocore.exceptions import ClientError
from commons import configmanager
from commons import cortxlogging
from commons import commands as common_cmd
from commons.constants import Rest as const
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils import config_utils
from commons.exceptions import CTException
from config import CSM_REST_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.s3.s3_test_lib import S3TestLib
from libs.s3 import s3_misc
from config import CMN_CFG
from commons.helpers.pods_helper import LogicalNode
from commons import constants as cons

class TestIamUser():
    """
    REST API Test cases for IAM users
    """
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
        """
        Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        for user in self.created_iam_users:
            self.rest_iam_user.delete_iam_user(
                login_as="s3account_user", user=user)
        self.log.info("Teardown ended")


    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10732')
    def test_1133(self):
        """
        Test that IAM users are not permitted to login
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


    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14749')
    def test_1041(self):
        """
        Test that S3 account should have access to create IAM user from back end
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
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_csm_user_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_users()
        assert setup_ready
        cls.created_iam_users = {}
        cls.cryptogen = SystemRandom()
        cls.bucket_name = None
        cls.user_id = None
        cls.display_name = None
        cls.test_file = None
        cls.test_file_path = None
        cls.file_size = cls.cryptogen.randrange(10, 100)
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = LogicalNode(hostname=cls.host, username=cls.uname, password=cls.passwd)
        cls.cluster_conf_path = cons.CLUSTER_CONF_PATH
        cls.csm_copy_path = cons.CLUSTER_COPY_PATH
        cls.local_csm_path = cons.CSM_COPY_PATH
        cls.log.info("[END] CSM setup class completed.")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        self.log.info("STARTED: Setup Operations")
        self.bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.user_id = const.IAM_USER + str(int(time.time_ns()))
        self.display_name = const.IAM_USER + str(int(time.time_ns()))
        self.test_file = "test-object.txt"
        self.test_file_path = os.path.join(TEST_DATA_FOLDER, self.test_file)
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        self.log.info("Done: Setup operations.")
        self.created_iam_users = {}

    def teardown_method(self):
        """Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        delete_failed = []
        delete_success = []
        for user_val in self.created_iam_users.values():
            user = user_val["user"]
            akey = user_val["access_key"]
            skey = user_val["secret_key"]
            self.log.info("deleting iam user %s", user)
            if akey != '' or skey != '' :
                result = s3_misc.delete_all_buckets(akey, skey)
                assert result, "Failed to delete buckets"
            resp = self.csm_obj.delete_iam_user(user=user)
            self.log.debug("Verify Response : %s", resp)
            if resp.status_code != HTTPStatus.OK:
                if resp.json()["message_id"] != "NoSuchUser":
                    delete_success.append(user)
                else:
                    delete_failed.append(user)
            else:
                delete_success.append(user)
        for user in delete_success:
            del self.created_iam_users[user]
        self.log.info("IAM delete success list %s", delete_success)
        self.log.info("IAM delete failed list %s", delete_failed)
        assert len(delete_failed) == 0, "Delete failed for IAM users"
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
    @pytest.mark.sanity
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
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("[START] Creating IAM user with all parameters")
        result, resp = self.csm_obj.verify_create_iam_user_rgw(user_type="loaded",
                                                               verify_response=True)
        assert result, "Failed to create IAM user using all parameters."
        self.log.info("Response : %s", resp)
        self.log.info("[END]Creating IAM user with all parameters")
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
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
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status check failed for invalid access key"
        self.log.info("[END] Testing with invalid access key")

        self.log.info("[START] Testing with invalid secret key")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"secret_key": ""})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status check failed forinvalid access key"
        self.log.info("[END] Testing with invalid secret key")

        self.log.info("[START] Testing with invalid key-type")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"key_type": "abc"})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status check failed for invalid key-type"
        self.log.info("[END] Testing with invalid key-type")

        self.log.info("[START] Testing with invalid capability parameter")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"user_caps": ""})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status check failed for invalid capability"
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
        assert resp.status_code == HTTPStatus.FORBIDDEN, \
            "Create user with Monitor user check failed."
        self.log.info("TODO Verify Response : %s", resp)
        self.log.info("[END]Creating IAM user with basic parameters")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35608')
    def test_35608(self):
        """
        Test that user can't create IAM user with duplicate parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing IAM user with duplicate parameters")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        resp = response.json()
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Performing POST API to Create IAM User with same uid as above.")
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp_new = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify user exist error.")
        assert resp_new.status_code == HTTPStatus.CONFLICT, "Check failed for duplicate user creation"
        self.log.info("Perform API to Create IAM User with same email Id as above.")
        user_id2, display_name2 = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id2, "display_name": display_name2, "email": email}
        self.log.info("payload :  %s", payload)
        resp_new = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify status email exist error.")
        assert resp_new.status_code == HTTPStatus.CONFLICT, "Check failed for duplicate user creation"
        self.log.info("Perform API to Create IAM User with already existing user Access Keys.")
        user_id3, display_name3, email3 = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id3, "display_name": display_name3, "email": email3,
                   "access_key": usr_val["access_key"], "secret_key": usr_val["secret_key"]}
        self.log.info("payload:  %s", payload)
        self.log.info("Verify keys_exist error)")
        resp_new = self.csm_obj.create_iam_user_rgw(payload)
        assert resp_new.status_code == HTTPStatus.CONFLICT, "Check failed for duplicate user creation"
        self.log.info("[END] Testing with duplicate uid and email")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35609')
    def test_35609(self):
        """
        Test that user can't create IAM user when server not running/not-reachable.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing IAM user when server not running/reachable")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Verify IAM user when server error")
        # TODO: Verified manually.
        self.log.info("[END] Testing with server error")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35610')
    def test_35610(self):
        """
        Test that user can create IAM user and generated Key pair is returned.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing IAM user creation with generated key pair.")
        self.log.info("Creating payload with access key")
        user_id, display_name, access_key = self.csm_obj.get_iam_user_payload("a_key")
        payload = {"uid": user_id, "display_name": display_name, "access_key": access_key}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        resp = response.json()
        self.log.info("Verify IAM user with access key")
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        assert usr_val["access_key"] != "", "Access key check failed for user creation"
        assert usr_val["secret_key"] != "", "Secret key check failed for user creation"
        self.log.info("Creating payload with secret key")
        user_id, display_name, secret_key = self.csm_obj.get_iam_user_payload("s_key")
        payload = {"uid": user_id, "display_name": display_name, "secret_key": secret_key}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        res_dict = res.json()
        self.log.info("Verify IAM user with secret key")
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = res_dict["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        assert usr_val["access_key"] != "", "Access key check failed for user creation"
        assert usr_val["secret_key"] != "", "Secret key check failed for user creation"
        self.log.info("[END] Testing with generated keys")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35611')
    def test_35611(self):
        """
        Test that user can create IAM user with existing Access Key.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing create IAM user with existing Access Key.")
        user_id, display_name, access_key = self.csm_obj.get_iam_user_payload("a_key")
        payload = {"uid": user_id, "display_name": display_name, "access_key": access_key}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        resp = response.json()
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        assert usr_val["access_key"] != "", "access key check failed for user creation"
        assert usr_val["secret_key"] != "", "Secret key check failed for user creation"
        self.log.info("creating payload with access keys generated in above step")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name,
                   "access_key": usr_val["access_key"]}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CONFLICT, "Status code check failed for user creation"
        self.log.info("Performing POST API to Create IAM User with generate_key=false")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        res_dict = res.json()
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        assert len(res_dict["keys"]) == 0, "User keys check failed for user creation"
        uid = res_dict["tenant"] + "$" + res_dict["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("[END] Testing with existing access keys")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35612')
    def test_35612(self):
        """
        Test that user can create IAM user with generate key.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing with IAM user with generate key")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        resp = response.json()
        self.log.info("Verify no keys returned when generate_key=false.")
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        assert len(resp["keys"]) == 0, "User key check failed for user creation"
        uid = resp["tenant"] + "$" + resp["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Verify keys returned when generate key is false")
        user_id, display_name, access_keys, secret_keys = self.csm_obj.get_iam_user_payload("keys")
        payload = {"uid": user_id, "display_name": display_name,
                   "access_key": access_keys, "secret_key": secret_keys, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        res_dict = res.json()
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        assert len(res_dict["keys"]) != 0, "User key check failed for user creation"
        uid = res_dict["tenant"] + "$" + res_dict["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("[END] Testing with generate key")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-35613')
    def test_35613(self):
        """
        Test that user can create IAM user with suspended user state.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing IAM user with suspended user state")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "suspended": True}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        res_dict = response.json()
        self.log.info("Verify IAM user creation with suspended state")
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = res_dict["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.created_iam_users[usr_val['user']]['access_key'] = ''
        self.created_iam_users[usr_val['user']]['secret_key'] = ''
        assert res_dict["suspended"] == 1, "User key check failed for user creation"
        self.log.info("[END] Testing IAM user with suspended user state")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36166')
    def test_36166(self):
        """
        Test that user can get IAM user information using uid.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing IAM user info with uid")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Create IAM user.")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Get IAM user info using uid.")
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["user_id"] == user_id, "User_id not matched in response."
        assert resp_dict["tenant"] == "", "Tenant not matched in response."
        assert resp_dict["display_name"] == display_name, "Display_name not matched in response."
        assert resp_dict["email"] == "", "Email Id not matched in response."
        assert resp_dict["suspended"] == 0, "Suspended user key value not matched in response."
        assert len(resp_dict["keys"]) != 0, "User keys not returned in response."
        self.log.info("Verified user info in response.")
        self.log.info("[END] Testing Get IAM user info with uid")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36167')
    def test_36167(self):
        """
        Test that user can get IAM user information using uid for suspended user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing get IAM user info for suspended user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        self.log.info("Create user with Suspended state.")
        payload = {"uid": user_id, "display_name": display_name, "suspended": True}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.created_iam_users[usr_val['user']]['access_key'] = ''
        self.created_iam_users[usr_val['user']]['secret_key'] = ''
        self.log.info("Get user info with Suspended state.")
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["suspended"] == 1, "Suspended user key value not matched in response."
        self.log.info("[END] Testing Get IAM user info with uid for suspended user")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36168')
    def test_36168(self):
        """
        Test that user can’t get IAM user information using invalid parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing get IAM user info with invalid parameters")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "suspended": True}
        self.log.info("payload :  %s", payload)
        self.log.info("Create IAM user.")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.created_iam_users[usr_val['user']]['access_key'] = ''
        self.created_iam_users[usr_val['user']]['secret_key'] = ''
        self.log.info("Get user info with empty uid.")
        payload["uid"] = ""
        resp = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify empty uid request failure.")
        assert resp.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user info"
        self.log.info("Get user info with invalid auth token header.")
        payload["uid"] = user_id
        resp_code = self.csm_obj.get_iam_user_rgw(payload['uid'], None)
        self.log.info("Verify invalid auth token request failure.")
        assert resp_code.status_code == HTTPStatus.UNAUTHORIZED, "Status code check failed for user info"
        self.log.info("[END] Testing Get IAM user info with invalid parameters.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36169')
    def test_36169(self):
        """
        Test that monitor user can get IAM user information.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing Get IAM user info with restricted user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Create IAM user by csm admin.")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Get IAM user info by csm monitor user")
        resp = self.csm_obj.get_iam_user(payload['uid'], login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.OK, \
            "Get user with Monitor user check failed."
        self.log.info("[END] Testing Get IAM user info with restricted user.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36170')
    def test_36170(self):
        """
        Test that user can’t get IAM user information when server not-reachable.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing with duplicate parameters")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for user creation"
        self.log.info("Verify get IAM user info when server error")
        # TODO: Verified manually.
        self.log.info("[END] Testing get IAM user with server error")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36171')
    def test_36171(self):
        """
        Test that user can delete the IAM user using the uid.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing delete IAM user with uid")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Verify delete user by uid.")
        resp = self.csm_obj.delete_iam_user(user_id)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for user deletion"
        del self.created_iam_users[usr_val['user']]
        self.log.info("Verify user is deleted.")
        resp = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify get user info request failure.")
        assert resp.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user info"
        self.log.info("[END] Testing delete IAM user by uid.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36172')
    def test_36172(self):
        """
        Test that user can delete the IAM user using the uid and purge-data.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing delete the IAM user using the uid and purge-data.")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Verify delete user by uid and purge-data.")
        resp = self.csm_obj.delete_iam_user(user_id)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for user deletion"
        del self.created_iam_users[usr_val['user']]
        self.log.info("Get deleted user info.")
        payload = {"uid": user_id}
        resp = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify get user info request failure.")
        assert resp.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user info"
        self.log.info("Creating new IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Verify delete user by uid and purge-data=false")
        payload = {"purge_data": False}
        resp = self.csm_obj.delete_iam_user(user_id)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for user deletion"
        del self.created_iam_users[usr_val['user']]
        payload = {"uid": user_id}
        resp = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify new user get info request failure.")
        assert resp.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user info"
        self.log.info("[END] Testing delete IAM user by uid ad purge-data.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36173')
    def test_36173(self):
        """
        Test that user can’t delete the IAM user using the invalid uid and token.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing delete IAM user using the invalid uid and token")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = response.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Verify delete user by empty uid.")
        resp = self.csm_obj.delete_iam_user("")
        assert resp.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user deletion"
        self.log.info("Get user info by uid.")
        res = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify get user info request.")
        assert res.status_code == HTTPStatus.OK, "Status code check failed for user info"
        self.log.info("Verify delete user by invalid token.")
        response = self.csm_obj.delete_iam_user_rgw(user_id, None)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, "Status code check failed for user deletion"
        self.log.info("Verify delete user by uid.")
        response = self.csm_obj.delete_iam_user(user_id)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user deletion"
        del self.created_iam_users[usr_val['user']]
        self.log.info("Get user info by uid.")
        response = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify get user info request failure.")
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user info"
        self.log.info("[END] Testing delete IAM user by invalid uid and token.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36174')
    def test_36174(self):
        """
        Test that user can delete the suspended IAM user using the uid.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing delete suspended IAM user using the uid")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "suspended": True}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = response.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Verify delete user by uid.")
        resp = self.csm_obj.delete_iam_user(user_id)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for user deletion"
        del self.created_iam_users[usr_val['user']]
        self.log.info("Get user info by uid.")
        res = self.csm_obj.get_iam_user(payload['uid'])
        self.log.info("Verify get user info request failure.")
        assert res.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for user info"
        self.log.info("[END] Testing delete suspended IAM user by uid.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36175')
    def test_36175(self):
        """
        Test that restricted user can’t delete the IAM user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing delete IAM user by restricted user")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = response.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Delete IAM user info by csm monitor user")
        resp = self.csm_obj.delete_iam_user(user_id, login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, \
            "Delete user with Monitor user check failed."
        self.log.info("[END] Testing delete IAM user by restricted user.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.skip(reason="Not ready")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36176')
    def test_36176(self):
        """
        Test that user can’t delete IAM user when server not running/not-reachable.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing delete IAM user when server not-reachable")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "suspended": True}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payload = {"uid": user_id}
        self.log.info("Verify get IAM user info when server error")
        ##TODO Verified manually
        self.log.info("[END] Testing delete IAM user with server error")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36582')
    def test_36582(self):
        """
        Test that user can create Key pair for the I AM user using UID.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can create Key pair for the I AM user using UID")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = response.json()["tenant"] + "$" + response.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        payload = {"uid": user_id}
        self.log.info("Perform PUT API to create keys using uid.")
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        resp = response.json()
        self.log.info("Verify keys returned.")
        assert len(resp) != 0, "Keys not created for IAM user."
        assert resp[0]["access_key"] != 0, "Access key not created"
        assert resp[0]["secret_key"] != 0, "Secret key not created"
        self.log.info("Perform PUT API to create keys using uid and Access Key.")
        user_id, display_name, access_key, secret_key = self.csm_obj.get_iam_user_payload("keys")
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = response.json()["tenant"] + "$" + response.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Verify new keys created using uid and access key.")
        payload = {"uid": user_id, "access_key": access_key}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        resp = response.json()
        assert resp[0]["access_key"] == access_key, "Access key not created"
        assert resp[0]["secret_key"] != 0, "Secret key not created"
        self.log.info("Perform PUT API to create keys using uid and Secret Key.")
        user_id, display_name, access_key, secret_key = self.csm_obj.get_iam_user_payload("keys")
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = response.json()["tenant"] + "$" + response.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Verify new keys created using uid and secret key.")
        payload = {"uid": user_id, "secret_key": secret_key}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        resp = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        assert len(resp) != 0, "Keys not created for IAM user."
        assert resp[0]["access_key"] != 0, "Access key not created"
        assert resp[0]["secret_key"] == secret_key, "Secret key not created"
        self.log.info("[END] Testing create IAM user keys with UID")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36583')
    def test_36583(self):
        """
        Test that user can create s3 Key pair for the I AM user using UID.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user can create s3 Key pair for the I AM user using UID.")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = response.json()["tenant"] + "$" + response.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("PUT API to create keys using uid with Key_type=s3")
        payload = {"uid": user_id, "key_type": "s3"}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        resp = response.json()
        self.log.info("Verify keys pair returned.")
        assert len(resp) != 0, "Keys not created for IAM user."
        assert resp[0]["access_key"] != 0, "Access key not created"
        assert resp[0]["secret_key"] != 0, "Secret key not created"
        self.log.info("PUT API to create keys using uid with Key_type=s3 & generate_key=True")
        self.log.info("Creating new IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Verify keys returned when generate_key is True")
        payload = {"uid": user_id, "key_type": "s3", "generate_key": True}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        resp = response.json()
        assert len(resp) != 0, "Keys not created for IAM user."
        assert resp[0]["access_key"] != 0, "Access key not created"
        assert resp[0]["secret_key"] != 0, "Secret key not created"
        self.log.info("PUT API to create keys using uid with Key_type & generate_key")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload_new = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload_new)
        response = self.csm_obj.create_iam_user_rgw(payload_new)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = response.json()["tenant"] + "$" + response.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Verify keys returned when generate_key is False")
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        resp = response.json()
        assert len(resp) != 0, "Keys not created for IAM user."
        assert resp[0]["access_key"] != 0, "Access key not created"
        assert resp[0]["secret_key"] != 0, "Secret key not created"
        self.log.info("[END] Testing create IAM user keys with keys_type and generate_key")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36584')
    def test_36584(self):
        """
        Test that user can’t create duplicate/invalid Keys for the user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user can’t create duplicate/invalid Keys for the user")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        resp = response.json()
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        access_key1 = usr_val["access_key"]
        secret_key1 = usr_val["secret_key"]
        self.log.info("Perform PUT API to create keys using existing user keys.")
        payload = {"uid": user_id, "access_key": access_key1, "secret_key": secret_key1}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.created_iam_users[usr_val['user']]['access_key'] = access_key1
        self.created_iam_users[usr_val['user']]['secret_key'] = secret_key1
        resp = response.json()
        assert len(resp) <= 1, "Keys created with existing Access/Secret keys."
        self.log.info("Perform PUT API to create keys with empty Access key.")
        payload = {"uid": user_id, "access_key": ""}
        res = self.csm_obj.add_key_to_iam_user(**payload)
        assert res.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PUT API to create keys with empty Secret key.")
        payload = {"uid": user_id, "secret_key": ""}
        resp = self.csm_obj.add_key_to_iam_user(**payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("[END] Testing create IAM user keys with invalid keys")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36585')
    def test_36585(self):
        """
        Test that csm monitor user can’t create Keys.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing csm monitor user can’t create Keys")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("create user keys by csm monitor user")
        resp = self.csm_obj.add_key_to_iam_user(**payload, login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, \
            "create user keys with Monitor user check failed."
        self.log.info("[END] Testing create IAM user keys with csm monitor user")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36586')
    def test_36586(self):
        """
        Test that user deletes Keys using Access Key.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user delete Keys using Access Key.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = res.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.created_iam_users[usr_val['user']]['access_key'] = ''
        self.created_iam_users[usr_val['user']]['secret_key'] = ''
        self.log.info("Perform PUT API to create keys.")
        payload = {"uid": user_id}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        resp = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform Delete API to remove the key pair using Access Key.")
        payload = {"access_key": resp[0]["access_key"]}
        res = self.csm_obj.remove_key_from_iam_user(**payload)
        assert res.status_code == HTTPStatus.OK, "Status code check failed for deleting user keys."
        self.log.info("Perform PUT API to create keys.")
        payload = {"uid": user_id}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        resp = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed for deleting user keys."
        self.log.info("Perform Delete API to remove the key pair using Access Key and uid.")
        payload = {"uid": user_id, "access_key": resp[0]["access_key"]}
        response = self.csm_obj.remove_key_from_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for deleting user keys."
        self.log.info("Perform PUT API to create keys.")
        payload = {"uid": user_id}
        res = self.csm_obj.add_key_to_iam_user(**payload)
        resp = res.json()
        assert res.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform Delete API to remove the key pair using Access Key and Key_type=s3.")
        payload = {"access_key": resp[0]["access_key"], "key_type": "s3"}
        resp = self.csm_obj.remove_key_from_iam_user(**payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("[END] Testing delete IAM user keys with access keys")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36587')
    def test_36587(self):
        """
        Test that user can’t delete Keys using invalid Access Key.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user can’t delete Keys using invalid Access Key.")
        self.log.info("Creating IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = resp.json()["tenant"] + "$" + resp.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT API to create keys.")
        payload = {"uid": user_id}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Delete API to remove the key pair using empty Access Key.")
        payload = {"access_key": ""}
        res = self.csm_obj.remove_key_from_iam_user(**payload)
        assert res.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Delete API to remove the key pair using empty Access Key and uid parameter.")
        payload = {"uid": user_id, "access_key": ""}
        resp = self.csm_obj.remove_key_from_iam_user(**payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("[END] Testing user can’t delete Keys using invalid Access Key")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-36588')
    def test_36588(self):
        """
        Test that csm monitor user can’t delete Keys.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing csm monitor user can’t delete Keys.")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.created_iam_users[usr_val['user']]['access_key'] = ''
        self.created_iam_users[usr_val['user']]['secret_key'] = ''
        self.log.info("Perform PUT API to create keys.")
        payload = {"uid": user_id}
        response = self.csm_obj.add_key_to_iam_user(**payload)
        resp = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform Delete API to remove the key pair using Access Key.")
        payload = {"access_key": resp[0]["access_key"]}
        self.log.info("Delete IAM user keys by csm monitor user")
        resp = self.csm_obj.remove_key_from_iam_user(**payload, login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, \
            "Delete user kes with Monitor user check failed."
        self.log.info("[END] Testing csm monitor user can’t delete Keys.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37461')
    def test_37461(self):
        """
            Test that user can modify the fields with valid inputs.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can modify the fields with valid inputs.")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PATCH request to modify the Display Name field.")
        payload = {"display_name": "modified"}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the email address field.")
        email = user_id + "@gmail.com"
        payload = {"email": email}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the access key and secret key pair.")
        _, _, access_key, secret_key = self.csm_obj.get_iam_user_payload("keys")
        payload = {"access_key": access_key, "secret_key": secret_key}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        resp = response.json()
        self.created_iam_users[uid]['access_key'] = access_key
        self.created_iam_users[uid]['secret_key'] = secret_key
        assert len(resp["keys"]) == 1, "Check failed for user keys."
        assert resp["keys"][0]["access_key"] != "", "Access key check failed for user creation"
        assert resp["keys"][0]["secret_key"] != "", "Secret key check failed for user creation"
        self.log.info("Perform PATCH request to modify the user Keys field with generate_key")
        payload = {"generate_key": True}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Max buckets field.")
        payload = {"max_buckets": 500}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Suspended user field.")
        payload = {"suspended": True}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.created_iam_users[uid]['access_key'] = ''
        self.created_iam_users[uid]['secret_key'] = ''
        self.log.info("Perform PATCH request to modify the Op mask field.")
        payload = {"op_mask": "read"}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        self.log.info("Perform GET request to get I am user info and verify modified fields.")
        payload = {"uid": user_id, "display_name": "modified"}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed for creating user keys."
        assert resp["display_name"] == "modified", "Check failed for modified display name."
        assert resp["email"] == email, "Check failed for modified email field."
        assert resp["max_buckets"] == 500, "Check failed for modified max buckets field."
        assert resp["suspended"] == 1, "Check failed for modified suspended field."
        assert resp["op_mask"] == "read", "Check failed for modified suspended field."
        self.log.info("[END] Testing that user can modify the fields with valid inputs.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37462')
    def test_37462(self):
        """
         Test that user can’t modify the fields with empty parameters.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user can’t modify the fields with empty parameters.")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = response.json()["tenant"] + "$" + response.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PATCH request to modify the Display Name with empty string.")
        payload = {"uid": user_id, "display_name": ""}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the email address field.")
        payload = {"email": ""}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the access key and secret key pair.")
        payload = {"access_key": "", "secret_key": ""}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the empty generate_key")
        payload = {"generate_key": ""}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the max buckets field.")
        payload = {"max_buckets": ""}
        resp = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Suspended user field.")
        payload = {"suspended": ""}
        resp = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Op mask field.")
        payload = {"op_mask": ""}
        resp = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("[END] Testing user can’t modify the fields with empty parameters.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37463')
    def test_37463(self):
        """
        Test that user can not modify the fields with already exiting values.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can not modify the fields with already exiting values.")
        self.log.info("Perform POST API to create user1.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        resp = res.json()
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Perform POST API to create user2.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = response.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Perform PATCH request to modify the user2 email field with user1 email address.")
        payload = {"email": email}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.CONFLICT, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the user2 keys with user1 access and secret keys pair.")
        payload = {"access_key": resp["keys"][0]["access_key"], "secret_key": resp["keys"][0]["secret_key"]}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.CONFLICT, "Status code check failed for creating user keys."
        self.log.info("[END] Testing user can not modify the fields with already exiting values.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37464')
    def test_37464(self):
        """
        Test that user can modify the fields with invalid inputs.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can not modify the fields with invalid inputs.")
        self.log.info("Perform POST API to create user.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = res.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Perform PATCH request to modify the email field with invalid email.")
        payload = {"uid": user_id, "email": "invalid.com"}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Generate key field with non Boolean values.")
        payload = {"uid": user_id, "generate_key": "true"}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Suspended user with Non Boolean values.")
        payload = {"uid": user_id, "suspended": "true"}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the Op mask field with invalid op_mask value")
        payload = {"uid": user_id, "op_mask": "Read/Write"}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for creating user keys."
        self.log.info("[END] Testing that user can modify the fields with invalid inputs.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37465')
    def test_37465(self):
        """
        Test that user can not modify the fields with invalid UID.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can not modify the fields with invalid UID.")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Perform PATCH request to modify the user info fields.")
        payload = {"display_name": display_name}
        response = self.csm_obj.modify_iam_user_rgw("", payload)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for creating user keys."
        self.log.info("Perform PATCH request to modify the user info fields.")
        payload = {"suspended": True}
        response = self.csm_obj.modify_iam_user_rgw("", payload)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for creating user keys."
        self.log.info("[END] Testing user can not modify the fields with invalid UID.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37466')
    def test_37466(self):
        """
        Test that user can not modify the fields with invalid/empty authentication token.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user can not modify the fields with invalid/empty authentication token.")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Perform PATCH request to modify the user info fields.")
        payload = {"uid": "", "display_name": display_name}
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload, auth_header=False)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, "Status code check failed for creating user keys."
        self.log.info("[END] Testing user can not modify the fields with invalid/empty authentication token.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37467')
    def test_37467(self):
        """
        Test that csm monitor user can not modify the fields.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing csm monitor user can’t delete Keys.")
        self.log.info("Create IAM user.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Perform PATCH request to modify the user info fields with csm monitor  user.")
        payload = {"display_name": "display_name"}
        resp = self.csm_obj.modify_iam_user_rgw(user_id, payload,
                                                login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, \
            "Modify user info with Monitor user check failed."
        self.log.info("[END] Testing csm monitor user can not modify the fields.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39121')
    def test_39121(self):
        """
        Test that IAM user can add read/write admin capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that IAM user can add read/write admin capabilities.")
        self.log.info("Create IAM user1.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user1 with admin rights.")
        payload = {"user_caps": "usage=read,write;user=write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user1.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["caps"][0]['type'] == 'usage', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched in response."
        assert resp_dict["caps"][1]['type'] == 'user', "caps type not matched in response."
        assert resp_dict["caps"][1]['perm'] == 'write', "caps perm not matched in response."
        self.log.info("Create IAM user2.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user2 with read only.")
        payload = {"user_caps": "usage=read;user=read"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user2.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["caps"][0]['type'] == 'usage', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched in response."
        assert resp_dict["caps"][1]['type'] == 'user', "caps type not matched in response."
        assert resp_dict["caps"][1]['perm'] == 'read', "caps perm not matched in response."
        self.log.info("[END] Testing that IAM user can add read/write admin capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.paralleln
    @pytest.mark.tags('TEST-39123')
    def test_39123(self):
        """
        Test that IAM user can add bucket read/write capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that IAM user can add bucket read/write capabilities.")
        self.log.info("Create IAM user1.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user1 with admin bucket rights")
        payload = {"user_caps": "users=read,write;buckets=read,write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user1.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["caps"][0]['type'] == 'buckets', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched in response."
        assert resp_dict["caps"][1]['type'] == 'users', "caps type not matched in response."
        assert resp_dict["caps"][1]['perm'] == '*', "caps perm not matched in response."
        self.log.info("Create IAM user2.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user2 with read only.")
        payload = {"user_caps": "users=read,write;buckets=read"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user2.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["caps"][0]['type'] == 'buckets', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched in response."
        assert resp_dict["caps"][1]['type'] == 'users', "caps type not matched in response."
        assert resp_dict["caps"][1]['perm'] == '*', "caps perm not matched in response."
        self.log.info("[END] Testing that IAM user can add bucket read/write capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39124')
    def test_39124(self):
        """
            Test that IAM user can remove read/write admin capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that IAM user can remove read/write admin capabilities.")
        self.log.info("Create IAM user1.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user1 with admin rights")
        payload = {"user_caps": "usage=read,write;user=write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform DELETE API to remove usage capability")
        payload = {"user_caps": "usage=read,write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user1.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert len(resp_dict["caps"]) == 1, "capability not removed for user."
        assert resp_dict["caps"][0]['type'] == 'user', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched in response."
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user=write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user1.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert len(resp_dict["caps"]) == 0, "capability not removed for user."
        self.log.info("[END] Testing that IAM user can remove read/write admin capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39125')
    def test_39125(self):
        """
        Test that IAM user can remove bucket read/write capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that IAM user can remove bucket read/write capabilities.")
        self.log.info("Create IAM user1.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user1 with admin bucket rights")
        payload = {"user_caps": "users=*;buckets=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Delete API to remove bucket write caps.")
        payload = {"user_caps": "buckets=write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user1.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert resp_dict["caps"][0]['type'] == 'buckets', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched in response."
        assert resp_dict["caps"][1]['type'] == 'users', "caps type not matched in response."
        assert resp_dict["caps"][1]['perm'] == '*', "caps perm not matched in response."
        self.log.info("Perform Delete API to remove bucket read caps.")
        payload = {"user_caps": "buckets=read"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform Get API for user1.")
        self.log.info("Get IAM user info using uid.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed for user info"
        assert len(resp_dict["caps"]) == 1, "capability not removed for user."
        assert resp_dict["caps"][0]['type'] == 'users', "caps type not matched in response."
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched in response."
        self.log.info("[END] Testing that IAM user can remove bucket read/write capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39126')
    def test_39126(self):
        """
            Test that IAM user can not add invalid capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that IAM user can not add invalid capabilities.")
        self.log.info("Create IAM user1.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add invalid capability")
        payload = {"user_caps": "random=*;buckets=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, \
                                    'Status code check failed for add capability.'
        self.log.info("Perform PUT request to add invalid  caps value")
        payload = {"user_caps": "users=random;buckets=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform PUT request to add invalid  format caps")
        payload = {"user_caps": "users=read,buckets=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("[END] Testing that IAM user can not add invalid capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39127')
    def test_39127(self):
        """
        Test that IAM user can not remove invalid capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that IAM user can not remove invalid capabilities.")
        self.log.info("Create IAM user1.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "generate_key": False}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed for user creation"
        uid = res.json()["tenant"] + "$" + res.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Perform PUT request to add capability for above user1 with admin rights")
        payload = {"user_caps": "usage=read,write;user=write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform DELETE API request to remove invalid capability")
        payload = {"user_caps": "random=*;buckets=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed for add capability."
        self.log.info("Perform DELETE API to remove invalid  caps value")
        payload = {"user_caps": "users=random;buckets=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("Perform DELETE API to remove invalid  format caps")
        payload = {"user_caps": "users=read,buckets=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed for add capability."
        self.log.info("[END] Testing that IAM user can not remove invalid capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)


    @pytest.mark.lc
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
        resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
        self.log.info("Verify Response : %s", resp1)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED, \
                                 "IAM user creation failed")
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Printing resp1 %s:", resp1)
        self.log.info("Printing optional payload %s:", optional_payload)
        resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
        self.log.info("compare payload response is: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verified Response")
        self.log.info("[END]Creating IAM user with random selection of optional parameters")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
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
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED, \
                                     "IAM user creation failed")
            usr_val = resp1.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            self.log.info("Printing resp %s:", resp1)
            self.log.info("Printing optional payload %s:", optional_payload)
            resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
            self.log.info("Printing response %s:", resp)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("[END]Creating Max IAM user with random selection of optional parameters")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-39412')
    def test_39412(self):
        """
        S3 IAM User: Create same name buckets with IAM users of same UID in different tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "[START] Create same name buckets with same name IAM users in different tenant")
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"uid": self.user_id})
            self.log.info("updated payload :  %s", optional_payload)
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp1.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step: Verify no bucket present in new account")
            s3_obj = S3TestLib(access_key=usr_val["access_key"],
                               secret_key=usr_val["secret_key"])
            buckets = s3_obj.bucket_list()[1]
            assert_utils.assert_false(len(buckets), "buckets found on new IAM user")
            self.log.info("Step: Verified no bucket present in new account")
            self.log.info("Create bucket and perform IO")
            resp = s3_obj.create_bucket_put_object(self.bucket_name, self.test_file,
                                 self.test_file_path, self.file_size)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Verify get object.")
            resp = s3_obj.get_object(self.bucket_name, self.test_file)
            assert_utils.assert_true(resp[0], resp)
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-39411')
    def test_39411(self):
        """
        S3 IAM User: Create same name buckets with IAM users of same name in different tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "[START] Create same name buckets with same name IAM users in different tenant")
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"display_name": self.display_name})
            self.log.info("updated payload :  %s", optional_payload)
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp1.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step: Verify no bucket present in new account")
            s3_obj = S3TestLib(access_key=usr_val["access_key"],
                               secret_key=usr_val["secret_key"])
            buckets = s3_obj.bucket_list()[1]
            assert_utils.assert_false(len(buckets), "buckets found on new IAM user")
            self.log.info("Step: Verified no bucket present in new account")
            self.log.info("Create bucket and perform IO")
            resp = s3_obj.create_bucket_put_object(self.bucket_name, self.test_file,
                                 self.test_file_path, self.file_size)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Verify get object.")
            resp = s3_obj.get_object(self.bucket_name, self.test_file)
            assert_utils.assert_true(resp[0], resp)
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-39410')
    def test_39410(self):
        """
        S3 IAM User: Create same name buckets with IAM users of same UID & name in different tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "[START] Create same name buckets with same name IAM users in different tenant")
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"uid": self.user_id})
            optional_payload.update({"display_name": self.display_name})
            self.log.info("updated payload :  %s", optional_payload)
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp1.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step: Verify no bucket present in new account")
            s3_obj = S3TestLib(access_key=usr_val["access_key"],
                               secret_key=usr_val["secret_key"])
            buckets = s3_obj.bucket_list()[1]
            assert_utils.assert_false(len(buckets), "buckets found on new IAM user")
            self.log.info("Step: Verified no bucket present in new account")
            self.log.info("Create bucket and perform IO")
            resp = s3_obj.create_bucket_put_object(self.bucket_name, self.test_file,
                                 self.test_file_path, self.file_size)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Verify get object.")
            resp = s3_obj.get_object(self.bucket_name, self.test_file)
            assert_utils.assert_true(resp[0], resp)
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-35931')
    def test_35931(self):
        """
        S3 IAM User: Create bucket with same name in different users in different tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM users with different tenant")
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            self.log.info("updated payload :  %s", optional_payload)
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp1.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step: Verify no bucket present in new account")
            s3_obj = S3TestLib(access_key=usr_val["access_key"],
                               secret_key=usr_val["secret_key"])
            buckets = s3_obj.bucket_list()[1]
            assert_utils.assert_false(len(buckets), "buckets found on new IAM user")
            self.log.info("Step: Verified no bucket present in new account")
            self.log.info("Create bucket and perform IO")
            resp = s3_obj.create_bucket_put_object(self.bucket_name, self.test_file,
                                 self.test_file_path, self.file_size)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Verify get object.")
            resp = s3_obj.get_object(self.bucket_name, self.test_file)
            assert_utils.assert_true(resp[0], resp)
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable=broad-except
    @pytest.mark.lc
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
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.log.info("Creating new iam user  %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        payload.update({"suspended": True})
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp1)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.created_iam_users[usr_val['user']]['access_key'] = ''
        self.created_iam_users[usr_val['user']]['secret_key'] = ''
        resp = self.csm_obj.compare_iam_payload_response(resp1, payload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verify create bucket")
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        try:
            status, resp = s3_obj.create_bucket(bucket_name)
            self.log.info("Printing response %s", resp.json())
            assert_utils.assert_false(status, resp)
        except Exception as error:
            self.log.info("Expected exception received %s", error)
        self.log.info("[END]Creating IAM user with suspended")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
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
        max_buckets = self.csm_obj.random_gen.randint(1, 10)
        payload.update({"max_buckets": max_buckets})
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp1)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        resp = self.csm_obj.compare_iam_payload_response(resp1, payload)
        assert_utils.assert_true(resp[0], resp[1])
        access_key=usr_val["access_key"]
        secret_key=usr_val["secret_key"]
        test_file = "test-object.txt"
        for bucket_cnt in range(max_buckets):
            bucket_name = "iam-user-bucket-" + str(bucket_cnt) + str(int(time.time_ns()))
            # Create bucket with bucket_name and perform IO
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket_name, access_key, secret_key)
            bucket_created = s3_misc.create_bucket(bucket_name, access_key, secret_key)
            assert bucket_created, "Failed to create bucket"
            resp = s3_misc.create_put_objects(
            test_file, bucket_name, access_key, secret_key, object_size=self.file_size)
            assert_utils.assert_true(resp, "Put object Failed")
        try:
            self.log.info("Create one more than allowed bucket")
            bucket_created = s3_misc.create_bucket(bucket_name, access_key, secret_key)
            assert bucket_created, "More than allowed bucket created."
        except ClientError as error:
            self.log.info("Expected exception received %s", error)
            assert error.response['Error']['Code'] == "TooManyBuckets", "Error check failed."
        self.log.info("[END]Creating IAM user with max bucket %s", max_buckets)
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
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
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp1)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        resp = self.csm_obj.compare_iam_payload_response(resp1, payload)
        self.log.info("Printing response %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        # Create bucket with bucket_name and perform IO
        access_key=usr_val["access_key"]
        secret_key=usr_val["secret_key"]
        test_file = "test-object.txt"
        for bucket_cnt in range(const.MAX_BUCKETS):
            self.log.info("[START] Iteration %s", bucket_cnt)
            bucket_name = "iam-user-bucket-" + str(bucket_cnt) + str(int(time.time_ns()))
            # Create bucket with bucket_name and perform IO
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket_name, access_key, secret_key)
            bucket_created = s3_misc.create_bucket(bucket_name, access_key, secret_key)
            assert bucket_created, "Failed to create bucket"
            resp = s3_misc.create_put_objects(
            test_file, bucket_name, access_key, secret_key, object_size=self.file_size)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("[END] Iteration %s", bucket_cnt)
        try:
            self.log.info("Create one more than allowed bucket")
            bucket_created = s3_misc.create_bucket(bucket_name, access_key, secret_key)
            assert bucket_created, "More than allowed bucket created."
        except ClientError as error:
            self.log.info("Expected exception received %s", error)
            assert error.response['Error']['Code'] == "TooManyBuckets", "Error check failed."
        self.log.info("[END]Creating IAM user with max buckets")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
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
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"generate_key": False})
        self.log.info(payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("printing resp %s:",resp.json())
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED.value, \
                                 "IAM user creation failed")
        uid = resp.json()["tenant"] + "$" + resp.json()["user_id"]
        self.created_iam_users.update({uid:{'user':uid,'access_key':'','secret_key':''}})
        self.log.info("Printing keys %s", resp.json()["keys"])
        for key in resp.json()["keys"]:
            if "access_key" in key or "secret_key" in key:
                assert_utils.assert_true(False, "access and secret keys available in response")
        self.log.info("[END]Creating IAM user with generate-keys=false")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-36446')
    def test_36446(self):
        """
        Create user with read only capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Step 1: Login using csm user and create a user with read capabilities")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        user_cap = "users=read"
        payload.update({"user_caps":user_cap})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, \
            "User could not be created"
        usr_val = resp.json()["keys"][0]
        self.log.info("Printing usr_val %s ",usr_val)
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("iam users set is %s ", self.created_iam_users)
        self.log.info("Step 2: Create bucket and perform IO")
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        self.log.info("Create bucket failed for user")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-36447')
    def test_36447(self):
        """
        Create user with invalid capabilities
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Step 1: Login using csm user and create a user with invalid capabilities")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload.update({"user_caps": "read-write"})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for user"
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-36448')
    def test_36448(self):
        """
        User access/secret key validation.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Login using csm user")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        #Uncomment this code when invalid access key combination is found
        #self.log.info("Step 1: Create a user with invalid access key")
        #invalid_key = self.csm_conf["test_36448"]["invalid_key"]
        #payload.update({"access_key": invalid_key})
        #self.log.info("payload :  %s", payload)
        #resp = self.csm_obj.create_iam_user_rgw(payload)
        #assert resp.status_code == HTTPStatus.BAD_REQUEST
        self.log.info("Step 2: create user with valid access key")
        valid_key = self.csm_conf["test_36448"]["valid_key"]
        payload.update({"access_key": valid_key})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.sanity
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37016')
    def test_37016(self):
        """
        Delete user with userid
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        resp = resp.json()
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Create bucket and perform IO")
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        self.log.info("Step: Verify create bucket")
        bucket_name = "user1" + str(int(time.time()))
        bucket_name = bucket_name.replace("_", "-")
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Step: Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        resp = self.csm_obj.compare_iam_payload_response(get_resp.json(), payload)
        self.log.debug(resp)
        assert_utils.assert_true(resp[0], "Value mismatch found")
        resp = s3_obj.delete_bucket(bucket_name=bucket_name, force=True)
        self.log.debug(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.csm_obj.delete_iam_user(user=uid)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user deletion failed")
        del self.created_iam_users[usr_val['user']]
        resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(resp.status_code == HTTPStatus.NOT_FOUND, "Deleted user exists")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.skip(reason="unsupported / deprecated")
    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37017')
    def test_37017(self):
        """
        Delete user with userid and purge-data
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        resp = resp.json()
        usr_val = resp["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Create bucket and perform IO")
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        self.log.info("Step: Verify create bucket")
        bucket_name = "user1" + str(int(time.time()))
        bucket_name = bucket_name.replace("_", "-")
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Step: Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        resp = self.csm_obj.compare_iam_payload_response(get_resp, payload)
        self.log.debug(resp)
        assert_utils.assert_true(resp[0], "Value mismatch found")
        resp = self.csm_obj.delete_iam_user(user=uid, purge_data=True)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user deletion failed")
        del self.created_iam_users[usr_val['user']]
        resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(resp.status_code == HTTPStatus.NOT_FOUND, "Deleted user exists")
        # CORTX-29180 Need to add Check for buckets and objects created by users are deleted
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37019')
    def test_37019(self):
        """
        Remove user with not existing userid
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        resp = self.csm_obj.delete_iam_user(user=uid + "invalid")
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.NOT_FOUND, "Invalid user deleted")
        resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37014')
    def test_37014(self):
        """
        Create user and verify created user using get iam call
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        resp = self.csm_obj.compare_iam_payload_response(get_resp, payload)
        self.log.debug(resp)
        assert_utils.assert_true(resp[0], "Value mismatch found")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37015')
    def test_37015(self):
        """
        Delete IAM user with CSM user with no authority to delete it
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        mon_usr = CSM_REST_CFG["csm_user_monitor"]["username"]
        mon_pwd = CSM_REST_CFG["csm_user_monitor"]["password"]
        header = self.csm_obj.get_headers(mon_usr, mon_pwd)
        resp = self.csm_obj.delete_iam_user_rgw(uid, header)
        assert_utils.assert_true(resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Monitor user deleted IAM user")
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        resp = self.csm_obj.compare_iam_payload_response(get_resp, payload)
        assert_utils.assert_true(resp[0], "Value mismatch found")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37020')
    def test_37020(self):
        """
        Get iam user using csm monitor user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        get_resp = self.csm_obj.get_iam_user(user=uid, login_as="csm_user_monitor")
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        resp = self.csm_obj.compare_iam_payload_response(get_resp, payload)
        assert_utils.assert_true(resp[0], "Value mismatch found")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-locals
    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37774')
    def test_37774(self):
        """
        Check users new access key generation
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert get_resp.status_code == HTTPStatus.OK, "Get IAM user failed"
        valid_key = self.csm_conf["test_36448"]["valid_key"]
        valid_key = valid_key + system_utils.random_string_generator(5)
        self.log.info("Adding key to user")
        add_resp = self.csm_obj.add_key_to_iam_user(uid=uid, access_key=valid_key)
        assert add_resp.status_code == HTTPStatus.OK, "Add key failed"
        resp = self.csm_obj.validate_added_deleted_keys(get_resp.json()["keys"], add_resp.json())
        self.log.info("Validate response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1][0]['access_key']
        secret_key = resp[1][0]['secret_key']
        assert valid_key == access_key, "Added key is not matching to provided key"
        bucket_name = "iam_user_bucket_" + str(int(time.time()))
        self.log.info("Create bucket and perform IO")
        s3_obj = S3TestLib(access_key=access_key,
                           secret_key=secret_key)
        bucket_name = bucket_name.replace("_", "-")
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Step: Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step: Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-locals
    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37775')
    def test_37775(self):
        """
        Check users new secret key generation
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        valid_key = self.csm_conf["test_36448"]["valid_key"]
        self.log.info("Adding key to user")
        add_resp = self.csm_obj.add_key_to_iam_user(uid=uid, secret_key=valid_key)
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.OK, "Add key failed")
        resp = self.csm_obj.validate_added_deleted_keys(get_resp.json()["keys"], add_resp.json())
        self.log.info("Validate response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1][0]['access_key']
        secret_key = resp[1][0]['secret_key']
        assert_utils.assert_true(valid_key == secret_key,
                                 "Added key is not matching to provided key")
        bucket_name = "iam_user_bucket_" + str(int(time.time()))
        self.log.info("Create bucket and perform IO")
        s3_obj = S3TestLib(access_key=access_key,
                           secret_key=secret_key)
        bucket_name = bucket_name.replace("_", "-")
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Step: Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step: Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-locals
    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37776')
    def test_37776(self):
        """
        Create key request with existing access key of same user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        access_key_init = get_resp.json()["keys"][0]['access_key']
        valid_key = self.csm_conf["test_36448"]["valid_key"]
        self.log.info("Adding key to user")
        add_resp = self.csm_obj.add_key_to_iam_user(uid=uid, access_key=access_key_init,
                                                    secret_key=valid_key)
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.OK, "Add key failed")
        assert_utils.assert_true(len(add_resp.json()) == 1, "More than 1 keys are received")
        access_key = add_resp.json()[0]['access_key']
        secret_key = add_resp.json()[0]['secret_key']
        uid = usr_val['user']
        self.created_iam_users[uid]['access_key'] = access_key
        self.created_iam_users[uid]['secret_key'] = secret_key
        assert_utils.assert_true(access_key == access_key_init, "Access key is not matching")
        assert_utils.assert_true(secret_key == valid_key, "Secret key is not matching")
        bucket_name = "iam_user_bucket_" + str(int(time.time()))
        self.log.info("Create bucket and perform IO")
        s3_obj = S3TestLib(access_key=access_key,
                           secret_key=secret_key)
        bucket_name = bucket_name.replace("_", "-")
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Step: Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step: Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37777')
    def test_37777(self):
        """
        Create key request with existing access key of another user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_37777"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        uids = []
        access_keys = []
        for user in range(2):
            uid = "iam_user_" + str(user) + str(int(time.time_ns()))
            self.log.info("Creating new iam user %s", uid)
            payload = self.csm_obj.iam_user_payload_rgw("loaded")
            payload.update({"uid": uid})
            payload.update({"display_name": uid})
            resp = self.csm_obj.create_iam_user_rgw(payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            uid = payload["tenant"] + "$" + uid
            uids.append(uid)
            usr_val = resp.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            get_resp = self.csm_obj.get_iam_user(user=uid)
            assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
            access_key = get_resp.json()["keys"][0]['access_key']
            access_keys.append(access_key)
        self.log.info("Adding key to user")
        add_resp = self.csm_obj.add_key_to_iam_user(uid=uids[0], access_key=access_keys[1])
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.CONFLICT, "Status Failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(add_resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(add_resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(add_resp.json()["message"], msg)

        for user in range(2):
            get_resp = self.csm_obj.get_iam_user(user=uids[user])
            assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
            access_key = get_resp.json()["keys"][0]['access_key']
            assert_utils.assert_true(access_key == access_keys[user], "Access key is changed")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37778')
    def test_37778(self):
        """
        Create key request with empty access/secret keys
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_37778"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Adding empty key to user")
        add_resp = self.csm_obj.add_key_to_iam_user(uid=uid, access_key="")
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.BAD_REQUEST, "Response failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(add_resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(add_resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(add_resp.json()["message"], msg_1)

        add_resp = self.csm_obj.add_key_to_iam_user(uid=uid, secret_key="")
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.BAD_REQUEST, "Response failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(add_resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(add_resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(add_resp.json()["message"], msg_2)

        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        assert_utils.assert_true(len(get_resp.json()["keys"]) == 1, "Keys are modified")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37779')
    def test_37779(self):
        """
        Create key request with valid access key and no uid
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_37779"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        valid_key = self.csm_conf["test_36448"]["valid_key"]
        add_resp = self.csm_obj.add_key_to_iam_user(uid=None, access_key=valid_key)
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.BAD_REQUEST, "Response failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(add_resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(add_resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(add_resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37780')
    def test_37780(self):
        """
        Remove access key of a user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        usr_val1 = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val1['user']:usr_val1})
        access_key = usr_val1['access_key']
        self.log.info("Removing key from user")
        rem_resp = self.csm_obj.remove_key_from_iam_user(uid=usr_val1['user'], access_key=access_key)
        assert_utils.assert_true(rem_resp.status_code == HTTPStatus.OK, "Remove key failed")
        self.created_iam_users[usr_val1['user']]['access_key'] = ''
        self.created_iam_users[usr_val1['user']]['secret_key'] = ''
        get_resp = self.csm_obj.get_iam_user(user=usr_val1['user'])
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        for key in get_resp.json()["keys"]:
            if "access_key" in key or "secret_key" in key:
                assert_utils.assert_true(False, "access or secret keys is not removed")
        uid2 = "iam_user_2_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid2)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid2})
        payload.update({"display_name": uid2})
        payload.update({"access_key": access_key})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        usr_val2 = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val2['user']:usr_val2})
        assert_utils.assert_true(access_key == usr_val2['access_key'], "Access key is not matching")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37781')
    def test_37781(self):
        """
        Remove non-existing access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        access_key = usr_val['access_key']
        self.log.info("Removing key from user")
        rem_resp = self.csm_obj.remove_key_from_iam_user(uid=usr_val['user'], access_key=access_key + "123")
        assert_utils.assert_true(rem_resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Remove key status check failed")
        get_resp = self.csm_obj.get_iam_user(user=usr_val['user'])
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        assert_utils.assert_true(access_key == usr_val['access_key'],
                                 "Access key is not matching")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37782')
    def test_37782(self):
        """
        Try Removing access key with monitor role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_37782"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        access_key = usr_val['access_key']
        self.log.info("Removing key from user with csm monitor role")
        rem_resp = self.csm_obj.remove_key_from_iam_user(uid=usr_val['user'], access_key=access_key,
                                                         login_as="csm_user_monitor")
        assert_utils.assert_true(rem_resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Remove key status failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(rem_resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(rem_resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(rem_resp.json()["message"], msg)

        get_resp = self.csm_obj.get_iam_user(user=usr_val['user'])
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        assert_utils.assert_true(access_key == get_resp.json()["keys"][0]['access_key'],
                                 "Access key is not matching")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-37783')
    def test_37783(self):
        """
        Add access key with monitor role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_37783"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        access_key = usr_val['access_key']
        add_resp = self.csm_obj.add_key_to_iam_user(uid=uid, access_key=access_key + "123",
                                                    login_as="csm_user_monitor")
        assert_utils.assert_true(add_resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Add key status failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(add_resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(add_resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(add_resp.json()["message"], msg)

        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        assert_utils.assert_true(access_key == get_resp.json()["keys"][0]['access_key'],
                                 "Access key is not matching")
        assert_utils.assert_true(len(get_resp.json()["keys"]) == 1,
                                 "Number of Access keys are not matching")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38087')
    def test_38087(self):
        """
        Update User with display name, correct uid in request.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] STEP 1: Creating IAM user with basic parameters")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = resp.json()["tenant"] + "$" + payload['uid']
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("STEP 2: Perform get iam users")
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 3: Send patch request to update display name")
        payload = {}
        payload.update({"display_name":(uid+"1")})
        resp1 = self.csm_obj.modify_iam_user_rgw(uid, payload)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.OK, "IAM user modify failed")
        self.log.info("STEP 4: Perform get iam users to verify new display name")
        get_resp = self.csm_obj.get_iam_user(uid)
        self.log.info("Print user info %s", get_resp.json())
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 5: Check if update is done successfully")
        assert_utils.assert_true((get_resp.json()["display_name"] == uid+"1"),
                                 "Display Name not updated")
        self.log.info("[END]Update User with display name, correct uid in request.")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38088')
    def test_38088(self):
        """
        Update User with display name, non existing uid in request
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_38088"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Print resp_data[0] %s", resp_data[0])
        self.log.info("[START] STEP 1: Creating IAM user with basic parameters")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = resp.json()["tenant"] + "$" + payload['uid']
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("STEP 2: Perform get iam users")
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 3: Send request with wrong uid in request to update display name")
        uid1 = uid+"1"
        payload = {}
        payload.update({"display_name":(uid+"1")})
        response = self.csm_obj.modify_iam_user_rgw(uid1, payload)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(response.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(response.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(response.json()["message"], msg)

        self.log.info("STEP 4: Perform get iam users to verify new display name")
        get_resp = self.csm_obj.get_iam_user(uid)
        self.log.info("Print user info %s", get_resp.json())
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 5: Check if update is done successfully")
        assert_utils.assert_true((get_resp.json()["display_name"] == resp.json()["display_name"]),
                                 "Display Name updated")
        self.log.info("[END]Update User with display name, non existing uid in request")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-statements
    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38089')
    def test_38089(self):
        """
        Update request with uid and generate-key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] STEP 1: Creating IAM user with basic parameters")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        self.log.info("payload :  %s", payload)
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
        uid = resp1.json()["tenant"] + "$" + payload['uid']
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("STEP 2: Perform get iam users")
        get_resp = self.csm_obj.get_iam_user(uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 3: Send request to update uid and generate-key")
        payload = {}
        payload.update({"generate_key":True})
        resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "IAM user modify failed")
        self.log.info("STEP 4: Perform get iam users to verify newly created keys")
        get_resp = self.csm_obj.get_iam_user(uid)
        self.log.info("Print user info %s", get_resp.json())
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 5: Check if keys are generated successfully")
        if len(get_resp.json()["keys"]) > 1:
            self.log.info("second pair of keys generated")
        assert_utils.assert_true(get_resp.json()["keys"][1]["access_key"]!=resp.json()[
                            "keys"][0]["access_key"], "Access key not generated")
        self.log.info("STEP 6: Create bucket and put object")
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        try:
            status, resp = s3_obj.create_bucket(bucket_name)
            self.log.info("Printing response %s", resp.json())
            assert_utils.assert_true(status, resp)
        except Exception as error:
            self.log.info("Expected exception received %s", error)
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                         file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step: Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("[END]Update request with uid and generate-key")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38090')
    def test_38090(self):
        """
        Update request with uid and other parameters randomly
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] STEP 1: Creating IAM user with basic parameters")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = resp.json()["tenant"] + "$" + payload['uid']
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})

        self.log.info("STEP 2: Perform get iam users")
        get_resp = self.csm_obj.get_iam_user(uid)
        assert(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")

        self.log.info("STEP 3: Update any random parameters for created user")
        payload = self.csm_obj.iam_user_patch_random_payload()
        if "access_key" in payload and "secret_key" not in payload:
            del payload["access_key"]
        elif "secret_key" in payload and "access_key" not in payload:
            del payload["secret_key"]
        self.log.info("Random payload :  %s", payload)

        resp1 = self.csm_obj.modify_iam_user_rgw(uid, payload)
        assert resp1.status_code == HTTPStatus.OK, "IAM user modify failed"

        self.log.info("STEP 4: Perform GET iam users to verify updated random parameters")
        get_resp = self.csm_obj.get_iam_user(uid)
        assert get_resp.status_code == HTTPStatus.OK, "Get IAM user failed"
        get_resp = get_resp.json()

        for key in payload.keys():
            if key == "generate_key":
                assert(len(get_resp["keys"]) < 2, "New key is not generated.")
            elif key == "access_key":
                assert(len(self.csm_obj.search_list_of_dict(
                    key, payload[key], get_resp["keys"])) >= 1)
            elif key == "key_type" or key == "secret_key":
                pass
            else:
                assert payload[key]==get_resp[key], "key mistmatch"

        self.log.info("[END]Update request with uid and other parameters randomly. ")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38093')
    def test_38093(self):
        """
        Verify PATCH iam user request for Invalid key type
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_38093"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        invalid_keys = ["s3swift", "123", None, "", "@#$", "null"]
        for key_value in invalid_keys:
            self.log.info("Testing for key value %s", key_value)
            payload = {}
            payload.update({"key_type": key_value})
            resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                     "Patch request status code failed")
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                if key_value is None:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"], msg_1)
                else:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"], msg_2)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38095')
    def test_38095(self):
        """
        Verify PATCH iam user request for invalid maximum number of buckets
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_38095"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        invalid_buckets = [system_utils.random_string_generator(5), "@$", None, "", "1.2", "null"]
        for key_value in invalid_buckets:
            self.log.info("Testing for key value %s", key_value)
            payload = {}
            payload.update({"max_buckets": key_value})
            resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                     "Patch request status code failed")
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                if key_value is None:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                                                msg_1.format("max_buckets").lower())
                else:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                                                msg_2.format("max_buckets").lower())

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38097')
    def test_38097(self):
        """
        Verify PATCH iam user request for invalid suspended value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_38097"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        invalid_suspended = [system_utils.random_string_generator(5), "@$", None, "", "134", "null"]
        for key_value in invalid_suspended:
            self.log.info("Testing for key value %s", key_value)
            payload = {}
            payload.update({"suspended": key_value})
            resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                     "Patch request status code failed")
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                if key_value is None:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                                                msg_1.format("suspended").lower())
                else:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                                                msg_2.format("suspended").lower())

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38103')
    def test_38103(self):
        """
        Verify PATCH iam user request for invalid op-mask
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_38103"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        invalid_opmask = [system_utils.random_string_generator(5), "read,wrote,delete", "deleted",
                          ""]
        for key_value in invalid_opmask:
            self.log.info("Testing for key value %s", key_value)
            payload = {}
            payload.update({"op_mask": key_value})
            resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                     "Patch request status code failed")
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                if key_value is "":
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                            Template(msg_1).substitute(A="_schema",
                                                                       B="op_mask").lower())
                else:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                            Template(msg_2).substitute(A="op_mask").lower())

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38107')
    def test_38107(self):
        """
        Verify PATCH iam user request for duplicate email address.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_38107"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        email1 = payload["email"]
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payload = {}
        payload.update({"email": email1})
        resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CONFLICT,
                                 "Patch request status code failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38108')
    def test_38108(self):
        """
        Verify PATCH iam user request for same values as old ones
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payload.pop("tenant")
        payload.pop("uid")
        payload.pop("user_caps")
        resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                 "Patch request status code failed")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38091')
    def test_38091(self):
        """
        Verify PATCH iam user request for invalid tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_38091"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        uid_values = ["null", "3", "invalid", payload["tenant"] + "c"]
        payload.pop("tenant")
        payload.pop("uid")
        for uid_value in uid_values:
            resp = self.csm_obj.modify_iam_user_rgw(uid_value + "$" + uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                     "Patch request status code failed")
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38094')
    def test_38094(self):
        """
        Verify PATCH iam user request for Invalid secret key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM user")
        test_cfg = self.csm_conf["test_38094"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        access_key = payload["access_key"]
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payload = {}
        payload.update({"secret_key": ""})
        payload.update({"access_key": access_key})
        resp = self.csm_obj.modify_iam_user_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                 "Patch request status code failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39029')
    def test_39029(self):
        """
        Add-remove random capabilities
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        payload.pop("user_caps")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        for _ in range(10):
            random_cap = self.csm_obj.get_random_caps()
            payload = {}
            payload.update({"user_caps": random_cap})
            self.log.info("STEP 2: Add user capabilities %s", random_cap)
            resp = self.csm_obj.add_user_caps_rgw(uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                     "Add cap request status code failed")
            get_resp = self.csm_obj.get_iam_user(user=uid)
            assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
            self.log.info("STEP 3: Verify added capabilities")
            diff_items = self.csm_obj.verify_caps(random_cap, get_resp.json()["caps"])
            self.log.info("Difference in capabilities %s", diff_items)
            assert_utils.assert_true(len(diff_items) == 0, "Capabilities are not updated properly")
            self.log.info("STEP 4: Remove capabilities")
            resp = self.csm_obj.remove_user_caps_rgw(uid, payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                     "Remove cap request status code failed")
            get_resp = self.csm_obj.get_iam_user(user=uid)
            assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
            self.log.info("STEP 4: Verify removed capabilities")
            assert_utils.assert_true(len(get_resp.json()["caps"]) == 0,
                                     "Capabilities are not updated properly")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39030')
    def test_39030(self):
        """
        Test add/remove capabilities with tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Creating IAM user")
        default_cap = "users=read,write"
        updated_cap = "buckets=read,write"
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        payload.update({"user_caps": default_cap})
        payload.update({"tenant": "abc"})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid1 = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("STEP 2: Create another user with same uid and different tenant")
        payload.update({"tenant": "abcc"})
        payload.update({"access_key": "abcc"})
        payload.update({"email": "abcc@seagate.com"})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid2 = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payload = {}
        payload.update({"user_caps": updated_cap})
        self.log.info("STEP 3: Add capabilities to user-1")
        resp = self.csm_obj.add_user_caps_rgw(uid1, payload, login_as="csm_user_manage")
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                 "Add cap request status code failed")
        get_resp = self.csm_obj.get_iam_user(user=uid1)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 4: Verify added capabilities for user-1")
        diff_items = self.csm_obj.verify_caps(default_cap + ";" + updated_cap,
                                              get_resp.json()["caps"])
        self.log.info("Difference in capabilities %s", diff_items)
        assert_utils.assert_true(len(diff_items) == 0, "Capabilities are not updated properly")
        get_resp = self.csm_obj.get_iam_user(user=uid2)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 5: Verify capabilities of user-2")
        diff_items = self.csm_obj.verify_caps(default_cap, get_resp.json()["caps"])
        self.log.info("Difference in capabilities %s", diff_items)
        assert_utils.assert_true(len(diff_items) == 0, "Capabilities are updated for another user")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39031')
    def test_39031(self):
        """
        Remove capability which is not preset
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Creating IAM user")
        initial_cap = "usage=read;buckets=read;users=read"
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        payload.update({"user_caps": initial_cap})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid1 = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payload = {}
        payload.update({"user_caps": "buckets=write"})
        self.log.info("STEP 2: Remove capabilities which is not present")
        resp = self.csm_obj.remove_user_caps_rgw(uid1, payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                 "Remove cap request status code failed")
        get_resp = self.csm_obj.get_iam_user(user=uid1)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 3: Verify capabilities are not changed")
        diff_items = self.csm_obj.verify_caps(initial_cap, get_resp.json()["caps"])
        self.log.info("Difference in capabilities %s", diff_items)
        assert_utils.assert_true(len(diff_items) == 0, "Capabilities are not updated properly")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39217')
    def test_39217(self):
        """
        Add-remove random capabilities with csm monitor role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Creating IAM user")
        uid = "iam_user_1_" + str(int(time.time_ns()))
        self.log.info("Creating new iam user %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("loaded")
        payload.update({"uid": uid})
        payload.update({"display_name": uid})
        init_cap = payload["user_caps"]
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED, "IAM user creation failed")
        uid = payload["tenant"] + "$" + uid
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        random_cap = self.csm_obj.get_random_caps()
        payload = {}
        payload.update({"user_caps": random_cap})
        self.log.info("STEP 2: Verify added capabilities with monitor csm user")
        resp = self.csm_obj.add_user_caps_rgw(uid, payload, login_as="csm_user_monitor")
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Add cap request status code failed")
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        diff_items = self.csm_obj.verify_caps(init_cap, get_resp.json()["caps"])
        self.log.info("Difference in capabilities %s", diff_items)
        assert_utils.assert_true(len(diff_items) == 0, "Capabilities are not updated properly")
        self.log.info("STEP 3: Verify remove capabilities with csm monitor user")
        resp = self.csm_obj.remove_user_caps_rgw(uid, payload, login_as="csm_user_monitor")
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Remove cap request status code failed")
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        diff_items = self.csm_obj.verify_caps(init_cap, get_resp.json()["caps"])
        self.log.info("Difference in capabilities %s", diff_items)
        assert_utils.assert_true(len(diff_items) == 0, "Capabilities are not updated properly")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38971')
    def test_38971(self):
        """
        Verify create IAM user with uid same as tenant
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Creating IAM user")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})

        self.log.info("Step-2: Creating IAM user with same name as tenant")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        payload.update({"tenant": resp.json()["user_id"]})
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "Status code check failed"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38969')
    def test_38969(self):
        """
        Verify PATCH iam user request for access key that belongs to another user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_38969"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Step-1: Creating IAM user 1")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        usr1 = resp.json()
        usr_val1 = usr1["keys"][0]
        self.created_iam_users.update({usr_val1['user']:usr_val1})

        self.log.info("Step-2: Creating IAM user 2")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        usr2 = resp.json()
        uid2 = usr2["tenant"] + "$" + usr2["user_id"]
        usr_val2 = usr2["keys"][0]
        self.created_iam_users.update({usr_val2['user']:usr_val2})

        self.log.info("Step-3: Edit IAM user with access key of user 1")
        payload = {"access_key": usr_val1["access_key"],
                    "secret_key": usr_val1["secret_key"]}
        resp = self.csm_obj.modify_iam_user_rgw(uid2, payload)
        assert resp.status_code == HTTPStatus.CONFLICT, "PATCH status code check failed"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        self.log.info("##### Test completed -  %s #####", test_case_name)



    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38918')
    def test_38918(self):
        """
        Verify IO operations fails with old key after secret key is modified
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Creating IAM user 1")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        usr = resp.json()
        usr_val = usr["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        akey = usr_val["access_key"]
        skey = usr_val["secret_key"]
        bucket = "testbucket"+ str(int(time.time()))
        test_file = "test-object.txt"

        s3_obj = S3TestLib(access_key = akey, secret_key=skey)
        resp = s3_obj.create_bucket(bucket)
        size = SystemRandom().randrange(10, 100)
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        system_utils.create_file(file_path_upload, size)
        resp = s3_obj.put_object(bucket_name=bucket, object_name=test_file,
                    file_path=file_path_upload)
        new_skey = config_utils.gen_rand_string(length=const.S3_ACCESS_LL)
        payload = {"access_key": usr_val["access_key"],
                    "secret_key":new_skey}
        resp = self.csm_obj.modify_iam_user_rgw(usr["user_id"], payload)
        assert resp.status_code == HTTPStatus.OK, "PATCH request failed."
        resp = resp.json()
        uid = usr_val['user']
        self.created_iam_users[uid]['access_key'] = akey
        self.created_iam_users[uid]['secret_key'] = new_skey
        try:
            resp = s3_obj.put_object(bucket_name=bucket, object_name=test_file,
                        file_path=file_path_upload)
            assert True, "Put object passed with old keys."
        except CTException as err:
            assert "SignatureDoesNotMatch" in err.message, "Error message check failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38914')
    def test_38914(self):
        """
        Verify PATCH iam user request for invalid field
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_38914"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Step-1: Creating IAM user 1")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        usr = resp.json()
        usr_val = usr["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        payloads = self.csm_conf["test_38914"]["payloads"]
        for payload in payloads:
            resp = self.csm_obj.modify_iam_user_rgw(usr["user_id"], payload)
            assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                assert_utils.assert_equals(
                    resp.json()["message"].lower(),
                    Template(msg).substitute(A=list(payload.keys())[0]).lower())

        self.log.info("##### Test completed -  %s #####", test_case_name)



    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-38092')
    def test_38092(self):
        """
        Verify PATCH iam user request for Invalid access key
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_38092"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Step-1: Creating IAM user")
        payload = self.csm_obj.iam_user_payload_rgw("valid")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.CREATED, "IAM user creation failed"
        usr = resp.json()
        usr_val = usr["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})

        self.log.info("Step-2: Modify IAM user with invalid access key")
        payload = {"access_key": "",
                    "secret_key":usr_val["secret_key"]}
        resp = self.csm_obj.modify_iam_user_rgw(usr["user_id"], payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"],
                                       Template(msg).substitute(A="_schema", B="access_key"))

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-39026')
    def test_39026(self):
        """
        Verify IOs with bucket read capability
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Step 1: Login using csm user and create a user with some capabilities")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        user_cap = "usage=read;buckets=read;users=read"
        payload.update({"user_caps": user_cap})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CREATED, \
            "User could not be created"
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Step 2: Create bucket and perform IO")
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        self.log.info("Create bucket successful for user")
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Step: Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step: Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 3: Delete bucket")
        resp = s3_obj.delete_bucket(bucket_name=bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Bucket deleted successfully")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-39027')
    def test_39027(self):
        """
        Verify IOs with bucket write capability
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Step 1: Login using csm user and create a user with some capabilities")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        user_cap = "buckets=read,write"
        payload.update({"user_caps": user_cap})
        self.log.info("payload :  %s", payload)
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        assert resp1.status_code == HTTPStatus.CREATED, \
            "User could not be created"
        uid = resp1.json()['tenant'] + "$" + payload["uid"]
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Step 2: Create bucket and perform IO")
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        self.log.info("Create bucket successful for user")
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 3: Delete bucket")
        resp = s3_obj.delete_bucket(bucket_name=bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Bucket deleted successfully")
        self.log.info("Step 4: Remove existing cap and add new capability")
        payload = {}
        payload.update({"user_caps": user_cap})
        resp = self.csm_obj.remove_user_caps_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                     "Remove cap request status code failed")
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("Step 5: Verify removed capabilities")
        assert_utils.assert_true(len(get_resp.json()["caps"]) == 0,
                                     "Capabilities are not updated properly")
        user_cap = "buckets=*"
        payload.update({"user_caps": user_cap})
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.add_user_caps_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK,
                                     "Add cap request status code failed")
        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 6: Verify added capabilities")
        diff_items = self.csm_obj.verify_caps(user_cap, get_resp.json()["caps"])
        self.log.info("Difference in capabilities %s", diff_items)
        assert_utils.assert_true(len(diff_items) == 0, "Capabilities are not updated properly")
        self.log.info("Step 7: Create bucket and perform IO")
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        s3_obj = S3TestLib(access_key=usr_val["access_key"],
                           secret_key=usr_val["secret_key"])
        status, resp = s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(status, resp)
        self.log.info("Create bucket successful for user")
        test_file = "test-object.txt"
        file_path_upload = os.path.join(TEST_DATA_FOLDER, test_file)
        if os.path.exists(file_path_upload):
            os.remove(file_path_upload)
        if not os.path.isdir(TEST_DATA_FOLDER):
            self.log.debug("File path not exists, create a directory")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(TEST_DATA_FOLDER))
        system_utils.create_file(file_path_upload, self.file_size)
        self.log.info("Verify put object.")
        resp = s3_obj.put_object(bucket_name=bucket_name, object_name=test_file,
                                 file_path=file_path_upload)
        self.log.info("Removing uploaded object from a local path.")
        os.remove(file_path_upload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Verify get object.")
        resp = s3_obj.get_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 8: Delete bucket")
        resp = s3_obj.delete_bucket(bucket_name=bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Bucket deleted successfully")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-39028')
    def test_39028(self):
        """
        Add-remove invalid capabilities
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_39028"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info(
            "Step 1: Login using csm user and create a user with some capabilities")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        user_cap = "usage=read;buckets=write;users=read"
        payload.update({"user_caps": user_cap})
        self.log.info("payload :  %s", payload)
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        assert resp1.status_code == HTTPStatus.CREATED, \
            "User could not be created"
        uid = resp1.json()['tenant'] + "$" + payload["uid"]
        usr_val = resp1.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        self.log.info("Step 2: Add some invalid capabilities")
        user_cap = "random=;buckets="
        payload = {}
        payload.update({"user_caps": user_cap})
        resp = self.csm_obj.add_user_caps_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
                                     "Invalid caps added"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 3: Verify added capabilities")
        assert_utils.assert_true(get_resp.json()["caps"] == resp1.json()["caps"],
                                 "Invalid capabilities added")
        self.log.info("Step 4: Remove invalid capabilities")
        payload = {}
        payload.update({"user_caps": user_cap})
        resp = self.csm_obj.remove_user_caps_rgw(uid, payload)
        self.log.info("Verify Response : %s", resp)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
                                     "Invalid caps added"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)

        get_resp = self.csm_obj.get_iam_user(user=uid)
        assert_utils.assert_true(get_resp.status_code == HTTPStatus.OK, "Get IAM user failed")
        self.log.info("STEP 5: Verify original capabilities are intact")
        assert_utils.assert_true(get_resp.json()["caps"] == resp1.json()["caps"],
                                 "Original caps are not intact")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39401')
    def test_39401(self):
        """
        Test create IAM users with same UID in same tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_39401"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("[START]Try Creating IAM users with same UID")
        user_id = const.IAM_USER + str(int(time.time_ns()))
        tenant = "tenant_" + str(int(time.time_ns()))
        self.log.info("Creating 1st iam user with tenant %s", tenant)
        optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
        optional_payload.update({"tenant": tenant})
        optional_payload.update({"uid": user_id})
        self.log.info("updated payload :  %s", optional_payload)
        resp = self.csm_obj.create_iam_user_rgw(optional_payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                "IAM user creation failed")
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
        self.log.info("Printing response %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Try Creating 2nd iam user with tenant %s", tenant)
        optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
        optional_payload.update({"tenant": tenant})
        optional_payload.update({"uid": user_id})
        self.log.info("updated payload :  %s", optional_payload)
        resp3 = self.csm_obj.create_iam_user_rgw(optional_payload)
        self.log.info("Printing resp %s:", resp3)
        self.log.info("Verify Response : %s", resp3)
        assert_utils.assert_true(resp3.status_code == HTTPStatus.CONFLICT,
                                 "Patch request status code failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp3.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp3.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp3.json()["message"], msg)
        self.log.info("[END]Try Creating IAM users with same UID")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39403')
    def test_39403(self):
        """
        Test create IAM users with same name in same tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM users with different tenant")
        display_name = const.IAM_USER + str(int(time.time_ns()))
        tenant = "tenant_" + str(int(time.time_ns()))
        self.log.info("Creating 1st iam user with tenant %s", tenant)
        optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
        optional_payload.update({"tenant": tenant})
        optional_payload.update({"display_name": display_name})
        self.log.info("updated payload :  %s", optional_payload)
        resp = self.csm_obj.create_iam_user_rgw(optional_payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                    "IAM user creation failed")
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
        self.log.info("Printing response %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Creating 2nd iam user with tenant %s", tenant)
        optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
        optional_payload.update({"tenant": tenant})
        optional_payload.update({"display_name": display_name})
        self.log.info("updated payload :  %s", optional_payload)
        resp = self.csm_obj.create_iam_user_rgw(optional_payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                    "IAM user creation failed")
        usr_val = resp.json()["keys"][0]
        self.created_iam_users.update({usr_val['user']:usr_val})
        resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
        self.log.info("Printing response %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39404')
    def test_39404(self):
        """
        Test create IAM users with same UID in different tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM users with different tenant")
        user_id = const.IAM_USER + str(int(time.time_ns()))
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"uid": user_id})
            self.log.info("updated payload :  %s", optional_payload)
            resp = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39405')
    def test_39405(self):
        """
        Test create IAM users with same name in different tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM users with different tenant")
        display_name = const.IAM_USER + str(int(time.time_ns()))
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"display_name": display_name})
            self.log.info("updated payload :  %s", optional_payload)
            resp = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-39406')
    def test_39406(self):
        """
        Test create IAM users with same UID and name in different tenants.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Creating IAM users with different tenant")
        user_id = const.IAM_USER + str(int(time.time_ns()))
        display_name = const.IAM_USER + str(int(time.time_ns()))
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"uid": user_id})
            optional_payload.update({"display_name": display_name})
            self.log.info("updated payload :  %s", optional_payload)
            resp = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            usr_val = resp.json()["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            resp = self.csm_obj.compare_iam_payload_response(resp, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("[END]Creating IAM users with different tenant")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42270')
    def test_42270(self):
        """
        Test GET IAM user with valid max_entries and marker using Admin login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating %s IAM users.", self.csm_conf["common"]["num_users"])
        users_list = []
        for count in range(self.csm_conf["common"]["num_users"]):
            resp = self.csm_obj.verify_create_iam_user_rgw(verify_response=True)
            assert_utils.assert_true(resp[0], resp[1])
            usr_val = resp[1]["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            users_list.append(resp[1]["user_id"])
            self.log.info("%s IAM user created", count + 1)
        self.log.info("Created users: %s", users_list)
        self.log.info("Step 2: Send GET request with max_entries as 5")
        resp = self.csm_obj.list_iam_users_rgw(max_entries=5)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
        resp_dict = resp.json()
        get_user_list = resp_dict["users"]
        count = resp_dict["count"]
        last_uid = resp_dict["marker"]
        assert_utils.assert_equals(count, 5, "Entries not returned as expected")
        flag = True
        while flag:
            self.log.info("Step 3: Get next two entries")
            resp_new = self.csm_obj.list_iam_users_rgw(max_entries=2, marker=last_uid)
            assert_utils.assert_equals(resp_new.status_code, HTTPStatus.OK, "Status check failed")
            resp_new_dict = resp_new.json()
            count_new = resp_new_dict["count"]
            get_user_list += resp_new_dict["users"]
            if "marker" not in resp_new_dict.keys():
                flag = False
            else:
                last_uid = resp_new_dict["marker"]
                assert_utils.assert_equals(count_new, 2, "Entries not returned as expected")
        counter = len(set(users_list) & set(get_user_list))
        self.log.info("User list from GET response: %s", get_user_list)
        assert_utils.assert_equals(counter, self.csm_conf["common"]["num_users"],
                                   "Did not get all users")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42271')
    def test_42271(self):
        """
        Test GET IAM user without any optional parameters using manage login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        for count in range(self.csm_conf["common"]["iterations"]):
            self.log.info("Starting iteration: %s", count + 1)
            self.log.info("Step 1: Creating IAM user with manage login")
            resp = self.csm_obj.verify_create_iam_user_rgw(verify_response=True,
                                                           login_as="csm_user_manage")
            assert_utils.assert_true(resp[0], resp[1])
            user_id = resp[1]["user_id"]
            self.log.info("IAM user %s is created", user_id)
            self.log.info("Step 2: Send GET request for list users and check if created user %s"
                          "is listed in it", user_id)
            resp = self.csm_obj.list_iam_users_rgw()
            assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
            resp_dict = resp.json()
            get_user_list = resp_dict["users"]
            assert_utils.assert_in(user_id, get_user_list, "created user not found in list")
            self.log.info("IAM user %s is listed in users list: %s", user_id, get_user_list)
            self.log.info("Step 3: Delete created user: %s", user_id)
            resp = self.csm_obj.delete_iam_user(user=user_id)
            self.log.debug("Verify Response : %s", resp)
            assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "User not deleted")
            self.log.info("User %s deleted successfully", user_id)
            self.log.info("Step 4: Again GET list users")
            resp = self.csm_obj.list_iam_users_rgw()
            assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
            resp_dict = resp.json()
            get_user_list = resp_dict["users"]
            assert_utils.assert_not_in(user_id, get_user_list, "deleted user still found in list")
            self.log.info("Deleted user %s is not listed in users list: %s", user_id, get_user_list)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42272')
    def test_42272(self):
        """
        Test GET IAM user with valid max_entries with monitor login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating IAM user with admin login")
        resp = self.csm_obj.verify_create_iam_user_rgw(verify_response=True)
        assert_utils.assert_true(resp[0], resp[1])
        user_id = resp[1]["user_id"]
        self.log.info("IAM user %s is created", user_id)
        self.log.info("Step 2: Send GET request for list users and check if created user %s is "
                      "listed in it", user_id)
        resp = self.csm_obj.list_iam_users_rgw(max_entries=9999999999, login_as="csm_user_monitor")
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
        resp_dict = resp.json()
        get_user_list = resp_dict["users"]
        assert_utils.assert_in(user_id, get_user_list, "created user not found in list")
        self.log.info("IAM user %s is listed in users list: %s", user_id, get_user_list)
        self.log.info("Step 3: Delete created user: %s", user_id)
        resp = self.csm_obj.delete_iam_user(user=user_id)
        self.log.debug("Verify Response : %s", resp)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "User not deleted")
        self.log.info("User %s deleted successfully", user_id)
        self.log.info("Step 4: Again GET list users")
        resp = self.csm_obj.list_iam_users_rgw(max_entries=9999999999, login_as="csm_user_monitor")
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
        resp_dict = resp.json()
        get_user_list = resp_dict["users"]
        assert_utils.assert_not_in(user_id, get_user_list, "deleted user still found in list")
        self.log.info("Deleted user %s is not listed in users list: %s", user_id, get_user_list)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42273')
    def test_42273(self):
        """
        Test GET IAM user with invalid max_entries
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42273"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        random_str = ''.join(secrets.choice(string.ascii_uppercase +
                                            string.ascii_lowercase) for i in range(7))
        special_str = ''.join(secrets.choice(string.punctuation) for i in range(7))
        invalid_values = [-1, 0, hex(255), random_str, special_str, '""']
        for key_value in invalid_values:
            self.log.info("Testing for key value %s", key_value)
            resp = self.csm_obj.list_iam_users_rgw(max_entries=key_value)
            self.log.info("Verify Response : %s", resp)
            assert_utils.assert_true(resp.status_code == HTTPStatus.BAD_REQUEST,
                                     "Status code check failed")
            if CSM_REST_CFG["msg_check"] == "enable":
                self.log.info("Verifying error response...")
                if key_value is invalid_values[0] or key_value is invalid_values[1]:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                        Template(msg_1).substitute(str_part="Max_entries").lower())
                else:
                    assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
                    assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
                    assert_utils.assert_equals(resp.json()["message"].lower(),
                                           Template(msg_2).substitute(A="Max_entries").lower())
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42274')
    def test_42274(self):
        """
        Test GET IAM user returns empty list with invalid marker
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42274"]
        ran_int = test_cfg["ran_int"]
        random_num = self.csm_obj.random_gen.randrange(1, ran_int)
        random_str = ''.join(secrets.choice(string.digits +
                                            string.ascii_lowercase) for i in range(7))
        invalid_markers = ['""', random_num, random_str]
        for marker in invalid_markers:
            self.log.info("Testing for invalid marker %s:", marker)
            resp = self.csm_obj.list_iam_users_rgw(marker=marker)
            assert_utils.assert_equals(resp.status_code, HTTPStatus.OK,
                                   "List IAM User failed")
            assert_utils.assert_equals(len(resp.json()["users"]), 0, "Users list is not empty")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42283')
    def test_42283(self):
        """
        Test GET IAM user with marker with deleted IAM user return empty list.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create IAM User")
        users_list = []
        resp = self.csm_obj.verify_create_iam_user_rgw(verify_response=True)
        assert resp[0], resp[1]
        usr_val = resp[1]["keys"][0]
        users_list.append(resp[1]["user_id"])
        self.log.info("Step 2: Delete IAM User")
        resp = self.csm_obj.delete_iam_user(usr_val['user'])
        self.log.debug("Verify Response : %s", resp)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK,
                                   "Delete IAM User failed")
        self.log.info("Step 3: List IAM users with delete user name as marker")
        resp = self.csm_obj.list_iam_users_rgw(marker=usr_val['user'])
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK,
                                 "List IAM User failed")
        assert_utils.assert_equals(len(resp.json()["users"]), 0, "Users list is not empty")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42284')
    def test_42284(self):
        """
        Test GET IAM user with marker in between the displayed list.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating %s IAM users.", self.csm_conf["common"]["num_users"])
        
        users_list = []

        for count in range(self.csm_conf["common"]["num_users"]):
            resp = self.csm_obj.verify_create_iam_user_rgw(verify_response=True)
            assert_utils.assert_true(resp[0], resp[1])
            usr_val = resp[1]["keys"][0]
            self.created_iam_users.update({usr_val['user']:usr_val})
            users_list.append(resp[1]["user_id"])
            self.log.info("%s IAM user created", count + 1)

        self.log.info("Created users: %s", users_list)

        user_index = self.csm_conf["test_42284"]["max_entries"]
        self.log.info("Step 2: Send GET request to get last %s entries", user_index)
        marker = self.csm_obj.list_iam_users_rgw().json()["users"][-user_index]
        max_entr = self.csm_obj.random_gen.randint(1, 10)

        self.log.info("Step 3: Send GET request with max_entries as %s and "
                      "marker: %s", max_entr, marker)

        resp = self.csm_obj.list_iam_users_rgw(max_entries=max_entr, marker=marker)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
        count_new = resp.json()["count"]
        get_user_list = resp.json()["users"]
        actual_entries = self.csm_conf["common"]["num_users"] - user_index
        assert_utils.assert_equals(count_new, actual_entries, "Entries not returned as expected")

        self.log.info("Printing first user of list %s", get_user_list[0])
        assert_utils.assert_equals(get_user_list[0], marker, "Marker not set"
                                                             "to in between user")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42286')
    def test_42286(self):
        """
        Test that internal user should be visible on the GET IAM user list
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Fetching internal IAM User")
        internal_user = self.csm_obj.fetch_internal_iamuser(self.nd_obj)
        self.log.info(internal_user)
        self.log.info("Step 1: Send get request for fetching iam users list")
        resp = self.csm_obj.list_iam_users_rgw(auth_header=None)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status check failed")
        self.log.info("Step 2: Check whether internal IAM User is visible in "
                      "get response")
        resp_dict = resp.json()
        self.log.info(resp_dict)
        get_user_list = resp_dict["users"]
        assert_utils.assert_in(internal_user, get_user_list,
                                           "internal user not found in list")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42287')
    def test_42287(self):
        """
        Test Delete internal IAM user should fail
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42287"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Fetching internal IAM User")
        internal_user = self.csm_obj.fetch_internal_iamuser(self.nd_obj)
        self.log.info("Step 1: Send delete request for deleting internal iam user")
        resp = self.csm_obj.delete_iam_user(user=internal_user)
        self.log.debug("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Delete Internal IAM User failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42288')
    def test_42288(self):
        """
        Test Patch access key and secret key for internal IAM user should fail
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42288"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Fetching internal IAM User")
        internal_user = self.csm_obj.fetch_internal_iamuser(self.nd_obj)
        payload = {"access_key":"sgiamadmin", "secret_key":"null"}
        resp = self.csm_obj.modify_iam_user_rgw(internal_user, payload)
        assert_utils.assert_true(resp.status_code == HTTPStatus.FORBIDDEN,
                                 "Internal IAM User Modified")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42289')
    def test_42289(self):
        """
        Test Create IAM user with same name as internal IAM user should fail
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42289"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Fetching internal IAM User")
        internal_user = self.csm_obj.fetch_internal_iamuser(self.nd_obj)
        self.log.info("Step 1: Create IAM user with same name as internal IAM user")
        payload = self.csm_obj.iam_user_payload_rgw(user_type="valid")
        payload["uid"] = internal_user
        self.log.info("payload :  %s", payload)
        resp = self.csm_obj.create_iam_user_rgw(payload)
        assert resp.status_code == HTTPStatus.CONFLICT, "Status code check failed"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-42290')
    def test_42290(self):
        """
        GET IAM user with invalid login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42290"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        self.log.info("Step 1: Send GET request with max_entries as 1 and invalid header")
        header= ''.join(secrets.choice(string.digits +
                                            string.ascii_lowercase) for i in range(15))
        resp = self.csm_obj.list_iam_users_rgw(max_entries=1, auth_header=header)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.UNAUTHORIZED,
                                                "Status code check failed")
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41858')
    def test_41858(self):
        """
        Test that user policy with(*, read/write/read, write)caps.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user policy capability is added")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user without user capability.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add capability for above user")
        payload = {"user_caps": "user-policy=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed."
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched in response."
        self.log.info("Perform POST API to create user without user capability.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add capability")
        payload = {"user_caps": "user-policy=read, write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched"
        self.log.info("Perform POST API to create user without user capability.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add capability")
        payload = {"user_caps": "user-policy=read"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched"
        self.log.info("Perform POST API to create user without user capability.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add capability")
        payload = {"user_caps": "user-policy=write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched"
        self.log.info("[END] Testing that user policy capability is added")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41859')
    def test_41859(self):
        """
        Test that user policy capability is added on user creation.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user policy on user creation.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email,
                   "user_caps": "user-policy=*"}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched"
        self.log.info("Perform POST API to create user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name,
                   "user_caps": "user-policy=read, write"}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched"
        self.log.info("Perform POST API to create user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name,
                   "user_caps": "user-policy=read"}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched"
        self.log.info("Perform POST API to create user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name,
                   "user_caps": "user-policy=write"}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched"
        self.log.info("[END] Testing that user policy is added on user creation.")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41860')
    def test_41860(self):
        """
        Test that user policy capability is added on tenant-user creation.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user policy on tenant-user creation.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "tenant": user_id,
                   "user_caps": "user-policy=*"}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create tenant-user")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        tenant_uid = user_id + "$" + user_id
        response = self.csm_obj.get_iam_user(tenant_uid)
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched"
        self.log.info("Perform POST API to create user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "tenant": user_id,
                   "user_caps": "user-policy=read, write"}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        tenant_uid = user_id + "$" + user_id
        response = self.csm_obj.get_iam_user(tenant_uid)
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == '*', "caps perm not matched"
        self.log.info("Perform POST API to create user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "tenant": user_id,
                   "user_caps": "user-policy=read"}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        tenant_uid = user_id + "$" + user_id
        response = self.csm_obj.get_iam_user(tenant_uid)
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched"
        self.log.info("Perform POST API to create user")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name, "tenant": user_id,
                   "user_caps": "user-policy=write"}
        self.log.info("payload :  %s", payload)
        res = self.csm_obj.create_iam_user_rgw(payload)
        assert res.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform Get API for user.")
        tenant_uid = user_id + "$" + user_id
        response = self.csm_obj.get_iam_user(tenant_uid)
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched"
        self.log.info("[END] Testing that user policy on tenant-user creation.")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41861')
    def test_41861(self):
        """
        Test that user-policy capability can be removed.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user-policy caps can be removed.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user without user capability.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add capability for above user")
        payload = {"user_caps": "user-policy=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'read', "caps perm not matched"
        self.log.info("Perform PUT request to add capability for above user")
        payload = {"user_caps": "user-policy=write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=read"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched"
        self.log.info("Perform PUT request to add capability for above user")
        payload = {"user_caps": "user-policy=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=read, write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert len(resp_dict["caps"]) == 0, "caps type not matched"
        self.log.info("Perform PUT request to add capability for above user")
        payload = {"user_caps": "user-policy=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert len(resp_dict["caps"]) == 0, "caps not matched"
        self.log.info("[END] Testing that user-policy capability can be removed.")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41862')
    def test_41862(self):
        """
        Test that user-policy capability can be removed, added on user creation.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user-policy can be removed(user creation)")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email,
                   "user_caps": "user-policy=*"}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=read"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        payload = {"uid": user_id}
        response = self.csm_obj.get_iam_user(payload['uid'])
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert len(resp_dict["caps"]) == 0, "caps not matched in response."
        self.log.info("[END] Testing that user-policy can be removed(user creation)")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41863')
    def test_41863(self):
        """
        Test that user policy capability can be removed(tenant-user).
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user policy can be removed(tenant-user)")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email,
                   "user_caps": "user-policy=*", "tenant": user_id}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create tenant-user with caps")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=read"}
        tenant_id = user_id + "$" + user_id
        response = self.csm_obj.remove_user_caps_rgw(tenant_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        response = self.csm_obj.get_iam_user(tenant_id)
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert resp_dict["caps"][0]['type'] == 'user-policy', "caps type not matched"
        assert resp_dict["caps"][0]['perm'] == 'write', "caps perm not matched"
        self.log.info("Perform DELETE API to remove user capability")
        payload = {"user_caps": "user-policy=write"}
        response = self.csm_obj.remove_user_caps_rgw(tenant_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform Get API for user.")
        response = self.csm_obj.get_iam_user(tenant_id)
        resp_dict = response.json()
        self.log.info("IAM user info: %s", resp_dict)
        self.log.info("Verify user info parameters in response.")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert len(resp_dict["caps"]) == 0, "caps not matched in response."
        self.log.info("[END] Testing that user policy can be removed (tenant-user)")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41864')
    def test_41864(self):
        """
        Test that user can not add invalid user-policy capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing user can not add invalid user-policy")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user without user capability.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add invalid capability")
        payload = {"user_caps": "user-policy=*;random=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"
        self.log.info("Perform PUT request to add invalid capability")
        payload = {"user_caps": "user-policy=random"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform PUT request to add invalid format caps")
        payload = {"user_caps": "user-policy=read,users=*"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform PUT request to add invalid format caps")
        payload = {"user_caps": "user-policy=Write,read"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("[END] Testing that user can not add invalid user-policy")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41865')
    def test_41865(self):
        """
        Test that user can not remove invalid capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can not remove invalid")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user without user capability.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add capability")
        payload = {"user_caps": "user-policy=read,write"}
        response = self.csm_obj.add_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid capability")
        payload = {"user_caps": "random=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid caps value")
        payload = {"user_caps": "user-policy=random"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid format caps")
        payload = {"user_caps": "user-policy=read,users=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("[END] Testing that user can not remove invalid capabilities.")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41866')
    def test_41866(self):
        """
        Test that user can not remove capabilities when not added.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that user can not remove capabilities")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user without user capability.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid capability")
        payload = {"user_caps": "user-policy=*"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid capability")
        payload = {"user_caps": "user-policy=read"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid caps value")
        payload = {"user_caps": "user-policy=write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Perform DELETE request to remove invalid format caps")
        payload = {"user_caps": "user-policy=read, write"}
        response = self.csm_obj.remove_user_caps_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("[END] Testing that user can not remove capabilities")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41867')
    def test_41867(self):
        """
        Test that monitor user can not add/remove capabilities.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing that monitor user can not add/remove caps.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user without user capability.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform PUT request to add {'user_caps':'user-policy=*'}")
        payload = {"user_caps": "user-policy=*"}
        resp = self.csm_obj.add_user_caps_rgw(user_id, payload,
                                              login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed"
        self.log.info("Perform PUT request to add")
        payload = {"user_caps": "user-policy=read"}
        resp = self.csm_obj.add_user_caps_rgw(user_id, payload,
                                              login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform PUT request to add caps")
        payload = {"user_caps": "user-policy=write"}
        resp = self.csm_obj.add_user_caps_rgw(user_id, payload,
                                              login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform PUT request to add caps")
        payload = {"user_caps": "user-policy=read, write"}
        resp = self.csm_obj.add_user_caps_rgw(user_id, payload,
                                              login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=*"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=read"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=write"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=read, write"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("[END] Testing that monitor user can not add/remove caps")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41868')
    def test_41868(self):
        """
        Test that monitor user can not remove capabilities on user creation
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing monitor user cannot remove caps")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email,
                   "user_caps": "user-policy=*"}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create user with caps")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform DELETE request to remove")
        payload = {"user_caps": "user-policy=*"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=read"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=write"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=read, write"}
        resp = self.csm_obj.remove_user_caps_rgw(user_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("[END]Testing monitor user cannot remove caps(user creation)")
        self.log.info("##### Test ended - %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41869')
    def test_41869(self):
        """
        Test that monitor user can not remove capabilities(tenant user).
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing monitor user cannot remove caps")
        self.log.info("Creating IAM user payload.")
        user_id, display_name, email = self.csm_obj.get_iam_user_payload("email")
        payload = {"uid": user_id, "display_name": display_name, "email": email,
                   "tenant": user_id, "user_caps": "user-policy=*"}
        self.log.info("payload :  %s", payload)
        self.log.info("Perform POST API to create tenant-user with caps")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Perform DELETE request to remove")
        payload = {"user_caps": "user-policy=*"}
        tenant_id = user_id + "$" + user_id
        resp = self.csm_obj.remove_user_caps_rgw(tenant_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=read"}
        resp = self.csm_obj.remove_user_caps_rgw(tenant_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=write"}
        resp = self.csm_obj.remove_user_caps_rgw(tenant_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("Perform DELETE request to remove caps")
        payload = {"user_caps": "user-policy=read, write"}
        resp = self.csm_obj.remove_user_caps_rgw(tenant_id, payload,
                                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status check failed."
        self.log.info("[END] Testing monitor user cannot remove caps(tenant user)")
        self.log.info("##### Test ended - %s #####", test_case_name)
