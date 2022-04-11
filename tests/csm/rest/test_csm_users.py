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
"""Tests various operation on CSM user using REST API
"""
import json
import logging
import random
import re
import time
from http import HTTPStatus

import pytest
import yaml

from commons import commands as comm
from commons import configmanager
from commons import constants as cons
from commons import cortxlogging
from commons.constants import Rest as const
from commons.helpers.node_helper import Node
from commons.utils import assert_utils, config_utils
from config import CSM_REST_CFG, CMN_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_bucket import RestS3BucketPolicy

from libs.csm.rest.csm_rest_iamuser import RestIamUser

from libs.csm.rest.csm_rest_cluster import RestCsmCluster
from libs.s3.s3_restapi_test_lib import S3AuthServerRestAPI
from libs.csm.csm_interface import csm_api_factory

class TestCsmUser():
    """REST API Test cases for CSM users
    """

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_csm_user.yaml")
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.config = CSMConfigsCheck()
        cls.csm_cluster = RestCsmCluster()
        cls.s3auth_obj = S3AuthServerRestAPI()
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname, password=cls.passwd)
        user_already_present = cls.config.check_predefined_csm_user_present()
        if not user_already_present:
            user_already_present = cls.config.setup_csm_users()
            assert user_already_present
        #s3acc_already_present = cls.config.check_predefined_s3account_present()
        #if not s3acc_already_present:
        #    s3acc_already_present = cls.config.setup_csm_s3()
        #assert s3acc_already_present
        cls.created_users = []
        cls.created_s3_users = []
        cls.remote_path = cons.CLUSTER_CONF_PATH
        cls.local_path = cons.LOCAL_CONF_PATH
        cls.csm_conf_path = cons.CSM_CONF_PATH
        cls.csm_copy_path = cons.CSM_COPY_PATH
        cls.local_csm_path = cons.CSM_COPY_PATH
        cls.csm_obj = csm_api_factory("rest")
        cls.log.info("Initiating Rest Client ...")

    def teardown_method(self):
        """"
        Teardown for deleting any csm user which is not deleted due to test failure.
        """
        self.log.info("[STARTED] ######### Teardown #########")
        self.log.info("Deleting all csm users except predefined ones...")
        delete_failed = []
        delete_success = []
        if self.created_users or self.created_s3_users:
           time.sleep(3)             #EOS-27030
        for usr in self.created_users:
            self.log.info("Sending request to delete csm user %s", usr)
            try:
                response = self.csm_obj.delete_csm_user(usr)
                if response.status_code != HTTPStatus.OK:
                    delete_failed.append(usr)
                else:
                    delete_success.append(usr)
            except BaseException as err:
                self.log.warning("Ignoring %s while deleting user: %s", err, usr)
        for usr in delete_success:
            self.created_users.remove(usr)
        self.log.info("csm delete success list %s", delete_success)
        self.log.info("csm delete failed list %s", delete_failed)
        assert len(delete_failed) == 0, "Delete failed for users"
        self.log.info("Users except pre-defined ones deleted.")
        self.log.info("Deleting all s3 users except predefined ones...")
        s3_delete_failed = []
        s3_delete_success = []
        for usr in self.created_s3_users:
            self.log.info("Sending request to delete s3 user %s", usr)
            try:
                response = self.csm_obj.delete_s3_account_user(username=usr)
                if response.status_code != HTTPStatus.OK:
                    self.log.error(response.status_code)
                    s3_delete_failed.append(usr)
                else:
                    s3_delete_success.append(usr)
            except BaseException as err:
                self.log.warning("Ignoring %s while deleting user: %s", err, usr)
        for usr in s3_delete_success:
            self.created_s3_users.remove(usr)
        self.log.info("s3 delete failed list %s", s3_delete_failed)
        self.log.info("s3 delete success list %s", s3_delete_success)
        assert len(s3_delete_failed) == 0, "Delete failed for s3 users"
        self.log.info("s3 users except pre-defined ones deleted.")
        self.log.info("[COMPLETED] ######### Teardown #########")

    @pytest.mark.lc
    @pytest.mark.cluster_user_ops
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-28936")
    def test_28936(self):
        """
        Test S3 account creation returns error 503 service unavailable
        for wrong values of endpoint and host in csm conf
        """
        # Test will fail until EOS-25584 is fixec for returning error code 503
        self.log.info("Step 1: Edit csm.conf file for incorrect s3 data endpoint")
        resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_GET_PODS,
                                            read_lines=False,
                                            exc=False)
        pod_name = self.csm_obj.get_pod_name(resp_node)
        self.log.info(pod_name)

        # cmd = kubectl cp cortx-control-pod-6cb946fc6c-k298q:/etc/cortx/csm/csm.conf /tmp -c cortx-csm-agent
        resp_node = self.nd_obj.execute_cmd(
            cmd=comm.K8S_CP_TO_LOCAL_CMD.format(
                pod_name, self.csm_conf_path, self.csm_copy_path, cons.CORTX_CSM_POD),
            read_lines=False,
            exc=False)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.csm_copy_path, local_path=self.local_csm_path)
        assert_utils.assert_true(resp[0], resp[1])
        stream = open(self.local_csm_path, 'r')
        data = yaml.load(stream, Loader=yaml.Loader)
        s3_endpoint = data['S3']['iam']['endpoints']
        s3_host = data['S3']['iam']['host']
        data['S3']['iam']['endpoints'] = "https://cortx-io-svc1:9443"
        data['S3']['iam']['host'] = "cortx-io-svc1"
        with open(self.local_csm_path, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data, default_flow_style=False))
        yaml_file.close()
        resp = self.nd_obj.copy_file_to_remote(
            local_path=self.local_csm_path, remote_path=self.csm_copy_path)
        assert_utils.assert_true(resp[0], resp[1])
        # cmd = kubectl cp /root/a.text cortx-control-pod-6cb946fc6c-k298q:/tmp -c cortx-csm-agent
        resp_node = self.nd_obj.execute_cmd(
            cmd=comm.K8S_CP_TO_CONTAINER_CMD.format(
                self.csm_copy_path, pod_name, self.csm_conf_path, cons.CORTX_CSM_POD),
            read_lines=False,
            exc=False)
        self.log.info("Step 2: Delete control pod")
        resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_DELETE_POD.format(pod_name),
                                            read_lines=False,
                                            exc=False)
        self.log.info("Step 3: Check if control pod is re-deployed")
        pod_up = False
        for _ in range(3):
            resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_GET_PODS,
                                                read_lines=False,
                                                exc=False)
            if cons.CONTROL_POD_NAME_PREFIX in resp_node.decode('UTF-8'):
                pod_up = True
                break
            else:
                time.sleep(30)
        if not pod_up:
            assert pod_up, "Pod is not up so cannot proceed. Test Failed"
        self.log.info("Step 4: Create s3account s3acc.")
        response1 = self.csm_obj.create_s3_account(user_type="valid")
        self.log.info("Repeating above steps for correct host and endpoint value")
        self.log.info("Fetch new pod name")
        resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_GET_PODS,
                                            read_lines=False,
                                            exc=False)
        pod_name = self.csm_obj.get_pod_name(resp_node)
        self.log.info("Step 5: Edit csm.conf file for correct s3 data endpoint")
        stream = open(self.local_csm_path, 'r')
        data = yaml.load(stream, Loader=yaml.Loader)
        data['S3']['iam']['endpoints'] = s3_endpoint
        data['S3']['iam']['host'] = s3_host
        with open(self.local_csm_path, 'w') as yaml_file:
            yaml_file.write(yaml.dump(data, default_flow_style=False))
        yaml_file.close()
        resp = self.nd_obj.copy_file_to_remote(
            local_path=self.local_csm_path, remote_path=self.csm_copy_path)
        assert_utils.assert_true(resp[0], resp[1])
        # cmd = kubectl cp /root/a.text cortx-control-pod-6cb946fc6c-k298q:/tmp -c cortx-csm-agent
        resp_node = self.nd_obj.execute_cmd(
            cmd=comm.K8S_CP_TO_CONTAINER_CMD.format(
                self.csm_copy_path, pod_name, self.csm_conf_path, cons.CORTX_CSM_POD),
            read_lines=False,
            exc=False)
        self.log.info("Step 6: Delete control pod")
        resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_DELETE_POD.format(pod_name),
                                            read_lines=False,
                                            exc=False)
        self.log.info("Step 7: Check if control pod is re-deployed")
        pod_up = False
        for _ in range(3):
            resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_GET_PODS,
                                                read_lines=False,
                                                exc=False)
            if cons.CONTROL_POD_NAME_PREFIX in resp_node.decode('UTF-8'):
                pod_up = True
                break
            else:
                time.sleep(30)
        if not pod_up:
            assert pod_up, "Pod is not up so cannot proceed. Test Failed"
        assert response1.status_code == HTTPStatus.SERVICE_UNAVAILABLE.value, "Account creation failed."
        self.log.info("Step 8: Create s3account s3acc.")
        response = self.csm_obj.create_s3_account(user_type="valid")
        username = response.json()["account_name"]
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST, "Account creation successful."
        response = self.csm_obj.delete_s3_account_user(username=username)
        assert response.status_code == const.SUCCESS_STATUS, "User deleted"
        self.log.info("################Test Passed##################")

    @pytest.mark.sanity
    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10720')
    def test_4947(self):
        """Initiating the test case to verify List CSM user.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10721')
    def test_4948(self):
        """Initiating the test case to verify List CSM user with offset=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS, offset=2)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10722')
    def test_4949(self):
        """Initiating the test case to verify List CSM user with offset=<string>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_csm_users(
            expect_status_code=const.BAD_REQUEST, offset='abc',
            verify_negative_scenario=True)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10723')
    def test_4950(self):
        """Initiating the test case to verify List CSM user with offset=<empty>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert (self.csm_obj.list_csm_users(expect_status_code=const.BAD_REQUEST, offset='',
                                             verify_negative_scenario=True))
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10724')
    def test_4951(self):
        """Initiating the test case to verify List CSM user with limit=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS, limit=2)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10725')
    def test_4952(self):
        """Initiating the test case to verify List CSM user with limit=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            limit='abc',
            verify_negative_scenario=True)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10711')
    def test_4954(self):
        """Initiating the test case to create csm users and List CSM user with
        limit > created csm users.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_actual_num_of_csm_users()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10726')
    def test_4955(self):
        """Initiating the test case to verify List CSM user with limit=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            limit='',
            verify_negative_scenario=True)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10727')
    def test_5001(self):
        """
        Test that GET API with invalid value for sort_by param returns 400 response code
        and appropriate error json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        invalid_sortby = self.csm_conf["test_5001"]["invalid_sortby"]
        test_cfg = self.csm_conf["test_5001"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        response = self.csm_obj.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_by=invalid_sortby,
            verify_negative_scenario=True)
        self.log.info("Response : %s", response)
        self.log.info("Verifying the response for invalid value for sort_by")
        assert response, "Status code check has failed check has failed."
        self.log.info("Verified the response for invalid value for sort_by")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10728')
    def test_5002(self):
        """
        Test that GET API with no value for sort_by param returns 400 response code

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_5002"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]

        self.log.info("Fetching csm user with empty sort by string...")
        response = self.csm_obj.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_by="",
            return_actual_response=True)

        self.log.info("Verifying error response...")
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17864')
    def test_5003(self):
        """
        Test that GET API with valid value for sort_dir param returns 200
        response code and appropriate json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        valid_sortdir = self.csm_conf["test_5003"]["valid_sortdir"]
        for sortdir in valid_sortdir:
            self.log.info("Sorting dir by :%s", sortdir)
            response_text = self.csm_obj.list_csm_users(
                expect_status_code=const.SUCCESS_STATUS,
                sort_dir=sortdir,
                return_actual_response=True)
            self.log.info("Verifying the actual response...")
            response = self.csm_obj.verify_list_csm_users(
                response_text.json(), sort_dir=sortdir)
            assert response
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10715')
    def test_5011(self):
        """Initiating the test case for the verifying CSM user creating.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert (self.csm_obj.create_verify_and_delete_csm_user_creation(
            user_type="valid",
            user_role="manage",
            expect_status_code=const.SUCCESS_STATUS_FOR_POST))
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10716')
    def test_5012(self):
        """Initiating the test case for the verifying response for invalid CSM user creating.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.create_verify_and_delete_csm_user_creation(
            user_type="invalid", user_role="manage",
            expect_status_code=const.BAD_REQUEST)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10717')
    def test_5013(self):
        """Initiating the test case for the verifying response with missing
        mandatory argument for CSM user creating.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.create_verify_and_delete_csm_user_creation(
            user_type="missing",
            user_role="manage",
            expect_status_code=const.BAD_REQUEST)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10718')
    def test_5014(self):
        """Initiating the test case for the verifying response unauthorized user
        trying to create csm user.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.csm_obj.create_csm_user(login_as="s3account_user")
        assert response.status_code == const.FORBIDDEN
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10719')
    def test_5015(self):
        """Initiating the test case for the verifying response for duplicate CSM user creation.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.create_verify_and_delete_csm_user_creation(
            user_type="duplicate",
            user_role="manage",
            expect_status_code=const.CONFLICT)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags('TEST-18802')
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    def test_5000(self):
        """
        Test that GET API with valid value for sort_by param returns 200 response code
        and appropriate json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        valid_sortby = self.csm_conf["test_5000"]["valid_sortby"]
        for sortby in valid_sortby:
            self.log.info("Sorting by :%s", sortby)
            response = self.csm_obj.list_csm_users(
                expect_status_code=const.SUCCESS_STATUS,
                sort_by=sortby, return_actual_response=True)
            self.log.info("Verifying the actual response...")
            message_check = self.csm_obj.verify_list_csm_users(
                response.json(), sort_by=sortby)
            assert message_check
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10730')
    def test_5004(self):
        """
        Test that GET API with invalid value for sort_dir param returns 400
        response code and appropriate error json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        invalid_sortdir = self.csm_conf["test_5004"]["invalid_sortdir"]
        self.log.info("Checking the sort dir option...")
        response = self.csm_obj.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_dir=invalid_sortdir, return_actual_response=True)
        self.log.info("Checking the error message text...")
        message_check = const.SORT_DIR_ERROR in response.json()[
            'message_id']
        assert message_check, response.json()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10713')
    def test_5006(self):
        """Initiating the test case to verify list CSM user with valid offset,
        limit,sort_by and sort_dir parameters provided.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_obj.verify_csm_user_list_valid_params()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("EOS-27117 Test is not valid anymore")
    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10714')
    def test_5008(self):
        """Initiating the test case to verify that 403 is returned by csm list
        users api for unauthorised access

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Verifying csm list users api unauthorised access for s3 user")
        assert self.csm_obj.verify_list_csm_users_unauthorised_access_failure(
            login_as="s3account_user")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10712')
    def test_5005(self):
        """
        Test that GET API with empty value for sort_dir param returns 400 response code
        and appropriate error json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_5005"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info(
            "Fetching the response for empty sort_by parameter with the expected status code")
        response = self.csm_obj.list_csm_users_empty_param(
            expect_status_code=const.BAD_REQUEST,
            csm_list_user_param="dir",
            return_actual_response=True)

        self.log.info("Verifying the error response returned status code: %s, response : %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)

        self.log.info(
            "Verified that the returned error response is as expected: %s", response.json())
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10795')
    def test_5009(self):
        """
        Test that GET API returns 200 response code and appropriate json data
        for valid username input.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Step 1: Creating a valid csm user")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST

        self.log.info("Reading the username")
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)

        self.log.info(
            "Step 2: Sending the request to user %s", username)
        response = self.csm_obj.list_csm_single_user(
            request_type="get",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            return_actual_response=True)
        self.log.info("Verifying the status code returned")
        assert const.SUCCESS_STATUS == response.status_code
        actual_response = response.json()

        self.log.info(
            "Step 3: Fetching list of all users")
        response = self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS, return_actual_response=True)
        self.log.info(
            "Verifying that response to fetch all users was successful")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info(
            "Step 4: Fetching the user %s information from the list", username)
        expected_response = []
        for item in response.json()["users"]:
            if item["username"] == username:
                expected_response = item
                break
        self.log.info("Verifying the actual response %s is matching the expected response %s",
                      actual_response, expected_response)
        assert config_utils.verify_json_response(
            actual_result=actual_response,
            expect_result=expected_response,
            match_exact=True)
        self.log.info(
            "Verified that the status code is 200 and response is as expected: %s", actual_response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10797')
    def test_5016(self):
        """
        Test that PATCH API returns 200 response code and appropriate json data
        for valid payload data.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        # Test Purpose 1: Verifying root user can modify manage role user
        self.log.info("Test Purpose 1: Verifying that csm root user can "
                      "modify role and password of csm manage role user")

        user = self.csm_conf["test_5016"]["user"]
        self.log.info(
            "Test Purpose 1: Step 1: Creating csm manage user : %s", user)
        response = self.csm_obj.create_csm_user(
            user_type=user[0], user_role=user[1])
        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info("User %s got created successfully", username)

        self.log.info("Test Purpose 1: Step 2: Login as csm root user and "
                      "change password and role of user %s", username)
        data = self.csm_conf["test_5016"]["payload_monitor"]
        self.log.info("Forming the payload")
        payload = {"role": data["role"], "password": data["password"]}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s and role %s was updated "
                      "successfully for csm user %s",
                      data["password"], data["role"], username)
        self.log.info("Logging in as user %s", username)
        payload_login = {"username": username, "password": data["password"]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS
        assert response.json()["role"] == user[2]

        self.log.info("Test Purpose 1: Verified status code %s was returned "
                      "along with response %s",
                      response.status_code, response.json())
        self.log.info("Test Purpose 2: Verified that the password %s "
                      "and role %s was updated successfully for csm user %s",
                      payload["password"], response.json()["role"], username)

        # Test Purpose 2: Verifying root user can modify monitor role user
        self.log.info(
            "Test Purpose 2: Verifying that csm root user can modify role and "
            "password of csm monitor role user")
        self.log.info("Test Purpose 2: Step 1: Creating csm monitor user")
        response = self.csm_obj.create_csm_user(
            user_type=user[0], user_role=user[2])
        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info("User %s got created successfully", username)

        self.log.info(
            "Test Purpose 2 : Step 2: Login as csm root user and change "
            "password and role of user %s", username)
        data = self.csm_conf["test_5016"]["payload_manage"]
        payload = {"role": data["role"], "password": data["password"]}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s and role %s was updated "
                      "successfully for csm user %s",
                      payload["password"], payload["role"], username)
        self.log.info("Logging in as user %s", username)
        payload_login = {"username": username, "password": payload["password"]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS
        assert response.json()["role"] == user[1]

        self.log.info("Test Purpose 2: Verified status code %s was returned "
                      "along with response %s", response.status_code,
                      response.json())
        self.log.info("Test Purpose 2: Verified that the password %s and "
                      "role %s was updated successfully for csm user %s",
                      payload["password"], response.json()["role"], username)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12023')
    def test_1228(self):
        """
        Test that CSM user with role manager can perform GET and POST API request on S3 Accounts

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose 1: Verifying that csm manage user can perform "
            "POST api request on S3 account")

        self.log.info(
            "Test Purpose 1: Step 1: Logging in as csm user and creating s3 account")
        response = self.csm_obj.create_s3_account(
            login_as="csm_user_manage")
        self.log.info("Verifying response code 201 was returned")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST

        s3_account_name = response.json()["account_name"]

        self.log.info("Verified status code %s was returned along with "
                      "response %s for s3 account %s creation",
                      response.status_code, response.json(), s3_account_name)
        self.log.info(
            "Test Purpose 1: Verified that csm manage user was able to create s3 account")

        self.log.info(
            "Test Purpose 1: Verified that csm manage user can perform POST "
            "api request on S3 account")

        self.log.info(
            "Test Purpose 2: Step 1: Logging in as csm user to get the "
            "details of the s3 account")
        response = self.csm_obj.list_all_created_s3account(
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        s3_accounts = [item["account_name"]
                       for item in response.json()["s3_accounts"]]
        self.log.info(s3_accounts)
        assert s3_account_name in s3_accounts
        self.log.info("Verified status code %s was returned for getting "
                      "account %s details  along with response %s",
                      response.status_code, s3_account_name, response.json())
        self.log.info(
            "Test Purpose 2: Verified that csm manage user was able to "
            "get the details of s3 account")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12022')
    def test_1237(self):
        """
        Test that CSM user with monitor role can perform GET API request for CSM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying that CSM user with monitor role can "
            "perform GET API request for CSM user")

        self.log.info("Step 1: Creating csm user")
        response = self.csm_obj.create_csm_user()
        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info(
            "Step 2: Verified User %s got created successfully", username)

        self.log.info(
            "Step 3: Login as csm monitor user and perform get "
            "request on csm user %s", username)
        response = self.csm_obj.list_csm_single_user(
            request_type="get",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info(
            "Verifying that get request was successful for csm user %s", username)
        assert username in response.json()["username"]

        self.log.info("Verified that status code %s was returned along "
                      "with response: %s for the get request for csm "
                      "user %s", response.status_code,
                      response.json(), username)
        self.log.info(
            "Step 4: Verified that CSM user with monitor role successfully "
            "performed GET API request for CSM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12021')
    def test_1235(self):
        """
        Test that CSM user with role monitor can perform GET API request for S3 Accounts

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying that csm monitor user can perform "
            "GET api request on S3 accounts")

        self.log.info(
            "Step 1: Creating s3 account")
        response = self.csm_obj.create_s3_account()
        self.log.info("Verifying s3 account was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        s3_account_name = response.json()["account_name"]
        self.log.info(
            "Step 2: Verified s3 account %s was successfully created ", s3_account_name)

        self.log.info(
            "Step 3: Logging in as csm monitor user to get the details of the s3 accounts")
        response = self.csm_obj.list_all_created_s3account(
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        s3_accounts = [item["account_name"]
                       for item in response.json()["s3_accounts"]]
        self.log.info(s3_accounts)
        assert s3_account_name in s3_accounts
        self.log.info("Verified status code %s was returned for getting "
                      "account %s details  along with response %s",
                      response.status_code, s3_account_name, response.json())
        self.log.info(
            "Step 4: Verified that csm monitor user was able to get the details "
            "of s3 accounts using GET api")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12018')
    def test_7421(self):
        """
        Test Non root user should able to change its password by specifying
        old_password and new password

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying non root user should able to change its "
            "password by specifying old_password and new password ")

        data = self.csm_conf["test_7421"]["data"]
        username = self.csm_obj.config["csm_user_manage"]["username"]
        self.log.info(
            "Step 1: Login as csm non root user and change password and role of"
            " user without providing old password %s", username)
        self.log.info(
            "Forming the payload specifying old password for csm manage user")
        old_password = self.csm_obj.config["csm_user_manage"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username, data=True, payload=json.dumps(payload_user),
            return_actual_response=True, login_as="csm_user_manage")

        self.log.info("Verifying response code %s and response %s  returned",
                      response.status_code, response.json())
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s was updated successfully for csm user %s",
                      data[0], username)
        self.log.info(
            "Logging in as user %s with new password %s", username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s",
                      response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully"
                      " for %s csm user %s",
                      data[0], response.json()["role"], username)

        self.log.info("Reverting old password for user %s", username)
        payload_user = {"password": old_password}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True)

        self.log.info("Verifying response code %s and response returned %s",
                      response.status_code, response.json())
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12024')
    def test_7411(self):
        """
        Test that root user should able to modify self password through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying Test that root user should able "
            "to modify self password using PATCH request ")

        data = self.csm_conf["test_7411"]["data"]
        username = self.csm_obj.config["csm_admin_user"]["username"]

        self.log.info(
            "Step 1: Login as csm root user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm root user")
        old_password = self.csm_obj.config["csm_admin_user"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True,
            login_as="csm_admin_user")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verifying if the password %s was updated "
                      "successfully for csm user %s",
                      data[0], username)

        self.log.info(
            "Step 2:Logging in as csm root user %s with new "
            "password %s", username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s",
                      response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully"
                      " for csm root user %s",
                      data[0], username)

        self.log.info("Reverting the password...")
        response = self.csm_obj.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info(
            "Verifying password was reverted and response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12025')
    def test_1229(self):
        """
        Test that CSM user with manage role can perform GET, POST, PATCH and
        DELETE API request for CSM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_1229"]["data"]
        self.log.info("Test Purpose 1: Verifying that CSM user with manage role "
                      "can perform POST request and create a new csm user")
        self.log.info(
            "Test Purpose 1: Step 1: CSM manage user performing POST request")
        response = self.csm_obj.create_csm_user(
            user_type=data[0], user_role=data[1], login_as="csm_user_manage")
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)

        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        actual_response = response.json()
        created_time = actual_response["created_time"]
        modified_time_format = self.csm_obj.edit_datetime_format(created_time)
        actual_response["created_time"] = modified_time_format
        updated_time = actual_response["updated_time"]
        modified_time = self.csm_obj.edit_datetime_format(updated_time)
        actual_response["updated_time"] = modified_time
        self.log.info("Printing actual response %s:", actual_response)
        self.log.info(
            "Fetching list of all users")
        response1 = self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(response1.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Fetching the user %s information from the list", username)
        expected_response = []
        for item in response1.json()["users"]:
            if item["username"] == username:
                expected_response = item
                break
        self.log.info("expected response is %s:", expected_response)
        created_time = expected_response["created_time"]
        modified_time_format = self.csm_obj.edit_datetime_format(created_time) 
        expected_response["created_time"] = modified_time_format
        updated_time = expected_response["updated_time"]
        modified_time = self.csm_obj.edit_datetime_format(updated_time)
        expected_response["updated_time"] = modified_time
        self.log.info("Printing expected response %s:", expected_response)
        self.log.info("Verifying the actual response %s is matching the "
                      "expected response %s", actual_response, expected_response)
        assert (config_utils.verify_json_response(
            actual_result=actual_response,
            expect_result=expected_response,
            match_exact=True))
        self.log.info("User %s got created successfully", username)
        self.log.info("Status code %s was returned along with response: %s "
                      "for the POST request for csm user %s",
                      response.status_code,
                      response.json(), username)
        self.log.info(
            "Test Purpose 1: Verified that CSM user with manage role can "
            "perform POST request and create a new csm user")

        self.log.info(
            "Test Purpose 2: Verifying that that CSM user with manage role "
            "can perform GET request for CSM user")
        self.log.info(
            "Test Purpose 2: Step 1: CSM manage user performing GET request")
        response = self.csm_obj.list_csm_single_user(
            request_type="get",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info(
            "Verifying that get request was successful for csm user %s", username)
        assert username in response.json()["username"]
        self.log.info("Status code %s was returned along with response: %s "
                      "for the GET request for csm user %s",
                      response.status_code, response.json(), username)
        self.log.info("Test Purpose 2: Verified that CSM user with manage role can "
                      "perform GET request for CSM user")

        self.log.info("Test Purpose 3: Verifying that that CSM user with manage "
                      " role can perform DELETE itself")
        response = self.csm_obj.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.SUCCESS_STATUS,
            user="csm_user_manage",
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Status code %s was returned along with response %s for "
                      "Delete request", response.status_code, response.json())
        self.log.info("Test Purpose 3: Verified that CSM user with manage role can "
                      "perform DELETE request for CSM user")

        self.log.info(
            "Test Purpose 4: Verifying that that CSM user with manage role can"
            " perform PATCH request for itself")
        self.log.info(
            "Test Purpose 4: Step 1: Create csm manage user")
        response = self.csm_obj.create_csm_user(
            user_type="pre-define", user_role="manage")
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        self.log.info("User %s got created successfully", username)
        username = response.json()["username"]
        userid = response.json()["id"]

        self.log.info("Test Purpose 4: Step 2: Login as csm manage user and "
                      "modify its own password using Patch request")
        self.log.info("Forming the payload")
        old_password = self.csm_obj.config["csm_user_manage"]["password"]
        payload = {"current_password": old_password, "password": data[3]}

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the password %s was updated successfully for csm user %s",
                      data[3], username)
        self.log.info("Logging in as user %s", username)
        payload_login = {"username": username, "password": data[3]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Status code %s was returned along with response %s for "
                      "Patch request", response.status_code, response.json())
        self.log.info("Test Purpose 4: Verified that CSM user with manage role "
                      "can perform PATCH request for itself")

        self.log.info(
            "Reverting the password of pre-configured user csm_user_manage")

        payload = {"current_password": data[3], "password": old_password}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_admin_user")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info(
            "Verified that CSM user with manage role can perform GET, POST, "
            "PATCH and DELETE API request for CSM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12026')
    def test_5019(self):
        """
        Test that PATCH API returns 200 response code and appropriate json data
        for partial payload.

        """

        # Test Purpose 1: Verifying root user can change the role of csm manage
        #  user partially without changing the password
        self.log.info("Test Purpose 1: Verifying that csm root user can partially "
                      "modify csm manage user by modifying only the user's role")

        user = self.csm_conf["test_5019"]["user"]
        payload_login = self.csm_conf["test_5019"]["payload_login"]
        self.log.info("Test Purpose 1: Step 1: Creating csm manage user")
        response = self.csm_obj.create_csm_user(
            user_type=user[0], user_role=user[1])
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info("User %s got created successfully", username)

        self.log.info("Test Purpose 1: Step 2: Login as csm root user and change"
                      " only the role of user %s", username)
        self.log.info("Forming the payload")
        payload = {"role": user[2]}

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the role %s was updated successfully for csm user %s",
                      user[2], username)

        userdata = json.loads(const.USER_DATA)
        self.log.info("Logging in as user %s", username)

        payload_login["username"] = username
        payload_login["password"] = userdata["password"]

        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        assert_utils.assert_equals(response.json()["role"], user[2])

        self.log.info("Test Purpose 1: Verified status code %s was returned "
                      "along with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 1: Verified that the role %s was updated successfully "
                      "for csm user %s", response.json()["role"], username)

        # Test Purpose 2: Verifying root user can change the password of csm manage
        # user partially without changing the role
        self.log.info("Test Purpose 2: Verifying that csm root user can partially modify "
                      "csm manage user by modifying only the user's password")

        self.log.info("Test Purpose 2: Step 1: Login as csm root user and change "
                      "only the password of user %s", username)

        self.log.info("Forming the payload")
        payload = {"password": user[3]}

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm user %s", user[3], username)

        self.log.info(
            "Logging in as user %s with the changed password %s", username, user[3])

        payload_login["username"] = username
        payload_login["password"] = user[3]
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Test Purpose 2: Verified status code %s was returned along "
                      "with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 2: Verified that the password %s was updated "
                      "successfully for csm user %s", user[3], username)

        # Test Purpose 3: Verifying root user can change the role of csm monitor user
        # partially without changing the password
        self.log.info("Test Purpose 3: Verifying that csm root user can partially "
                      "modify csm monitor user by modifying only the user's role")

        self.log.info("Test Purpose 3: Step 1: Creating csm monitor user")
        response = self.csm_obj.create_csm_user(
            user_type=user[0], user_role=user[2])
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info("User %s got created successfully", username)

        self.log.info("Test Purpose 3: Step 2: Login as csm root user and change "
                      "only the role of user %s", username)

        self.log.info("Forming the payload")
        payload = {"role": user[1]}

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the role %s was updated successfully for csm user %s",
                      user[2], username)

        self.log.info("Logging in as user %s", username)

        payload_login["username"] = username
        payload_login["password"] = userdata["password"]
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        assert_utils.assert_equals(response.json()["role"], user[1])

        self.log.info("Test Purpose 3: Verified status code %s was returned along "
                      "with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 3: Verified that the role %s was updated successfully"
                      " for csm user %s", response.json()["role"], username)

        # Test Purpose 4: Verifying root user can change the password of csm
        # monitor user partially without changing the role
        self.log.info("Test Purpose 4: Verifying that csm root user can partially "
                      "modify csm monitor user by modifying only the user's password")

        self.log.info("Test Purpose 4: Step 1: Login as csm root user and change "
                      "only the password of user %s", username)
        self.log.info("Forming the payload")
        payload = {"password": user[3], "confirmPassword": user[3]}

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm user %s", user[3], username)

        self.log.info("Logging in as user %s with the changed password %s",
                      username, user[3])

        payload_login["username"] = username
        payload_login["password"] = user[3]

        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Test Purpose 4: Verified status code %s was returned "
                      "along with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 4: Verified that the password %s was "
                      "updated successfully for csm user %s", user[3], username)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12838')
    def test_7422(self):
        """
        Test that Non root user cannot change roles through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Step 1: Verifying that csm manage user cannot modify its role")

        username = self.csm_obj.config["csm_user_manage"]["username"]
        expected_response_manage = self.csm_conf["test_7422"]["response_manage"]
        expected_response_manage["error_format_args"] = username
        resp_error_code = self.rest_resp_conf["error_codes"]
        resp_msg = self.rest_resp_conf["messages"]
        resp_msg_id = self.rest_resp_conf["message_ids"]
        self.log.info(
            "Creating payload for the Patch request")
        payload = self.csm_conf["test_7422"]["payload_manage"]
        payload["current_password"] = self.csm_obj.config["csm_user_manage"]["password"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")

        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code["code_4101"]))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       resp_msg["message_11"])
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id["message_id_1"])
        self.log.info("Step 1: Verified that csm manage user cannot modify its "
                      "role and response returned is %s", response)

        self.log.info(
            "Step 2: Verifying that csm monitor user cannot modify its role")

        username = self.csm_obj.config["csm_user_monitor"]["username"]

        self.log.info("Creating payload for the Patch request")
        payload = self.csm_conf["test_7422"]["payload_monitor"]
        payload["current_password"] = self.csm_obj.config["csm_user_monitor"]["password"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")

        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified that csm monitor user cannot modify its role and "
            "response returned is %s", response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12839')
    def test_7412(self):
        """
        Test that user should not able to change roles for root user through
        CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        username = self.csm_obj.config["csm_admin_user"]["username"]
        expected_response_admin = self.csm_conf["test_7412"]["response_admin"]
        expected_response_admin["error_format_args"] = username

        self.log.info(
            "Step 1: Verifying that csm admin user should not be able to modify"
            " its own role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload_admin"]
        payload["current_password"] = self.csm_obj.config["csm_admin_user"]["password"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_admin_user")

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        assert_utils.assert_equals(response.json(), expected_response_admin)

        self.log.info(
            "Step 1: Verified that csm admin user is not be able to modify its "
            "own role and response returned is %s", response)

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to modify "
            "csm admin user role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified that csm manage user is not be able to modify "
            "csm admin user role and response returned is %s", response)

        self.log.info(
            "Step 3: Verifying that csm monitor user should not be able to"
            " modify csm admin user role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 3: Verified that csm monitor user is not be able to modify "
            "csm admin user role and response returned is %s", response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12840')
    def test_7408(self):
        """
        Test that user should not be able to change its username through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        payload = self.csm_conf["test_7408"]["payload"]
        test_cfg = self.csm_conf["test_7408"]["response_mesg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info(
            "Step 1: Verifying that csm monitor user should not be able to "
            "modify its username")

        username = self.csm_obj.config["csm_user_monitor"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_obj.config["csm_user_monitor"]["password"]
        self.log.info("Payload for the patch request is: %s", payload)

        self.log.info("Sending the patch request for csm monitor user...")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)
        self.log.info(
            "Step 1: Verified that csm monitor user %s is not able to modify "
            "its username and response returned is %s", username, response)

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to "
            "modify its username")
        username = self.csm_obj.config["csm_user_manage"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_obj.config["csm_user_manage"]["password"]
        self.log.info("Payload for the patch request is: %s", payload)

        self.log.info("Sending the patch request for csm manage user...")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)

        self.log.info(
            "Step 2: Verified that csm manage user %s is not be able to modify "
            "its username and response returned is %s", username, response)

        self.log.info(
            "Step 3: Verifying that csm admin user should not be able to modify"
            " its username")
        username = self.csm_obj.config["csm_admin_user"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_obj.config["csm_admin_user"]["password"]
        self.log.info("Payload for the patch request is: %s", payload)

        self.log.info("Sending the patch request for csm admin user...")
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_admin_user")
        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)

        self.log.info(
            "Step 3: Verified that csm admin user %s is not be able to modify "
            "its username and response returned is %s", username, response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-17865')
    def test_6220(self):
        """
        Test that duplicate users should not be created between csm users and
        s3 account users in CSM REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_6220"]
        test_cfg = data["response_duplicate_csm_manage_user"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info(
            "Step 1: Verifying that csm admin user should not be able to create"
            " duplicate csm user")

        username = self.csm_obj.config["csm_user_manage"]["username"]
        self.log.info(
            "Logging in as csm admin user to create duplicate csm user %s",
            username)
        response = self.csm_obj.create_csm_user(
            user_type="pre-define",
            user_role="manage",
            login_as="csm_admin_user")

        self.log.info("Verifying response code: %s and response returned: %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       (msg + " " + username))
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)
        self.log.info("Verified response returned")

        self.log.info(
            "Step 1: Verified that csm admin user is not able to create "
            "duplicate csm user")
        test_cfg1 = data["response_duplicate_csm_monitor_user"]
        resp_error_code = test_cfg1["error_code"]
        resp_msg_id = test_cfg1["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to "
            "create duplicate csm user")

        username = self.csm_obj.config["csm_user_monitor"]["username"]
        self.log.info(
            "Logging in as csm manage user to create duplicate csm user %s", username)

        response = self.csm_obj.create_csm_user(
            user_type="pre-define",
            user_role="monitor",
            login_as="csm_user_manage")

        self.log.info("Verifying response code: %s and response returned: %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       (msg + " " + username))
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)
        self.log.info("Verified response returned")

        self.log.info(
            "Step 2: Verified that csm manage user is not able to create duplicate csm user")

        test_cfg2 = data["response_duplicate_s3_account"]
        resp_error_code = test_cfg2["error_code"]
        resp_msg_id = test_cfg2["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        s3account = self.csm_obj.config["s3account_user"]["username"]
        data["response_duplicate_s3_account"]["error_format_args"]["account_name"] = s3account
        self.log.info(
            "Step 3: Verifying that csm admin user should not be able to create"
            " duplicate s3 account")

        self.log.info(
            "Logging in as csm admin user to create duplicate s3 account %s", s3account)
        response = self.csm_obj.create_s3_account(
            user_type="pre-define", login_as="csm_admin_user")

        self.log.info("Verifying response")
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(response.json()["error_code"],
                                   resp_error_code)
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)

        self.log.info("Verified response returned is: %s, %s",
                      response, response.json())

        self.log.info(
            "Step 3: Verified that csm admin user is not able to create "
            "duplicate s3 account")

        self.log.info(
            "Step 4: Verifying that csm manage user should not be able to "
            "create duplicate s3 account")

        self.log.info(
            "Logging in as csm manage user to create duplicate s3 account %s",
            s3account)
        response = self.csm_obj.create_s3_account(
            user_type="pre-define", login_as="csm_user_manage")

        self.log.info("Verifying response")
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(response.json()["error_code"],
                                   resp_error_code)
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)

        self.log.info("Verified response returned is: %s, %s",
                      response, response.json())

        self.log.info(
            "Step 4: Verified that csm manage user is not able to create "
            "duplicate s3 account")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14657')
    def test_5021(self):
        """
        Test that DELETE API with default argument returns 200 response code
        and appropriate json data.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Step 1: Verifying that DELETE API with default argument returns 200 "
            "response code and appropriate json data")

        data = self.csm_conf["test_5021"]["response_message"]
        message = data["message"]
        self.log.info("Creating csm user")
        response = self.csm_obj.create_csm_user()

        self.log.info("Verifying that user was successfully created")
        assert (response.status_code ==
                const.SUCCESS_STATUS_FOR_POST)

        self.log.info("Reading the username")
        username = response.json()["username"]

        self.log.info(
            "Sending request to delete csm user %s", username)
        response = self.csm_obj.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.SUCCESS_STATUS,
            user=username, return_actual_response=True)

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Verified success status %s is returned",
                      response.status_code)

        self.log.info("Verifying proper message is returned")
        assert_utils.assert_equals(response.json()["message"],
                                   message)
        self.log.info(
            "Verified message returned is: %s", response.json())

        self.log.info(
            "Step 1: Verified that DELETE API with default argument returns 200"
            " response code and appropriate json data")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14658')
    def test_5023(self):
        """
        Test that DELETE API returns 403 response for unauthorized request.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Step 1: Verifying that DELETE API returns 403 response for "
            "unauthorized request")

        self.log.info(
            "Sending request to delete csm user with s3 authentication")
        response = self.csm_obj.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.FORBIDDEN,
            user="csm_user_manage",
            return_actual_response=True,
            login_as="s3account_user")

        self.log.info("Verifying response returned")

        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)

        self.log.info(
            "Step 1: Verified that DELETE API returns 403 response for "
            "unauthorized request : %s", response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14659')
    def test_5020(self):
        """
        Test that PATCH API returns 400 response code and appropriate json
        data for empty payload.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_5020"]["response_msg"]
        resp_error_code = data["error_code"]
        resp_msg_id = data["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]

        payload = {}
        self.log.info(
            "Step 1: Verifying that PATCH API returns 400 response code and "
            "appropriate json data for empty payload")

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying the status code returned : %s",
                      response.status_code)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : %s", response.json())
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       msg)
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that PATCH API returns 400 response code and "
            "appropriate json data for empty payload")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14660')
    def test_5017(self):
        """
        Test that PATCH API returns 404 response code and appropriate json data
        for user that does not exist.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data_payload = self.csm_conf["test_5017"]
        data = self.csm_conf["test_5017"]["response_msg"]
        resp_error_code = data["error_code"]
        resp_msg_id = data["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        userid = self.csm_conf["test_5017"]["invalid_user_id"]
        self.log.info(
            "Step 1: Verifying that PATCH API returns 404 response code and "
            "appropriate json data for user that does not exist")

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.METHOD_NOT_FOUND,
            user=userid,
            data=True,
            payload=json.dumps(data_payload["payload"]),
            return_actual_response=True)

        self.log.info("Verifying the status code returned : %s",
                      response.status_code)
        assert_utils.assert_equals(response.status_code,
                                   const.METHOD_NOT_FOUND)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : %s", response.json())
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       (msg + " " + userid))
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that PATCH API returns 404 response code and "
            "appropriate json data for user does not exist")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14661')
    def test_5010(self):
        """
        Test that GET API returns 404 response code and appropriate json data
        for non-existing username input.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        userid = self.csm_conf["test_5010"]["invalid_user_id"]
        test_cfg = self.csm_conf["test_5010"]["response_msg"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info(
            "Step 1: Verifying that GET API returns 404 response code and appropriate "
            "json data for non-existing username input")

        response = self.csm_obj.list_csm_single_user(
            request_type="get",
            expect_status_code=const.METHOD_NOT_FOUND,
            user=userid,
            return_actual_response=True)

        self.log.info("Verifying the status code returned : %s",
                      response.status_code)
        assert_utils.assert_equals(response.status_code,
                                   const.METHOD_NOT_FOUND)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : %s", response.json())
        assert_utils.assert_equals(response.json()["error_code"],
                                   str(resp_error_code))
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json()["message"],
                                       (msg + " " + userid))
        assert_utils.assert_equals(response.json()["message_id"],
                                   resp_msg_id)
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that GET API returns 404 response code and "
            "appropriate json data for non-existing(invalid) username input")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14696')
    def test_5018(self):
        """
        Test that PATCH API returns 400 response code and appropriate error json
        data for invalid payload.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_5018"]

        self.log.info(
            "Step 1: Verifying that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password")

        for i in range(1, data["range"][0]):
            self.log.info("Verifying for invalid password: %s",
                          data[f'payload_invalid_password_{str(i)}'])
            response = self.csm_obj.list_csm_single_user(
                request_type="patch",
                expect_status_code=const.BAD_REQUEST,
                user="csm_user_manage",
                data=True,
                payload=json.dumps(data[f'payload_invalid_password_{str(i)}']),
                return_actual_response=True)

            self.log.info("Verifying the returned status code: %s and response:"
                          " %s ", response.status_code, response.json())
            assert response.status_code == const.BAD_REQUEST, "Response code mismatch."
            print(i)
            assert_utils.assert_equals(
                response.json(), data[f'invalid_password_resp_{str(i)}'], "Error message mismatch.")

        self.log.info(
            "Step 1: Verified that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password")

        self.log.info(
            "Step 2: Verifying that PATCH API returns 400 response code and "
            "appropriate error json data for invalid role")

        self.log.info("Verifying for invalid role: %s",
                      data["invalid_role_resp"])
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user="csm_user_manage", data=True,
            payload=json.dumps(data["payload_invalid_role"]),
            return_actual_response=True)

        self.log.info("Verifying the returned status code: %s and response: %s ",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(), data["invalid_role_resp"])

        self.log.info(
            "Step 2: Verified that PATCH API returns 400 response code and  "
            "appropriate error json data for invalid role")

        self.log.info(
            "Step 3: Verifying that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password and role")

        self.log.info("Verifying for invalid role and invalid password: %s",
                      data["payload_invalid_password_role"])
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(data["payload_invalid_password_role"]),
            return_actual_response=True)

        self.log.info("Verifying the returned status code: %s and response: %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)

        data_new1 = response.json()["message"].split(':')
        data_new2 = data_new1[1].split('{')
        if data_new2[1] == "'role'":
            role_passwd_resp = data["invalid_password_role_resp_1"]
        elif data_new2[1] == "'password'":
            role_passwd_resp = data["invalid_password_role_resp_2"]

        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(response.json(), role_passwd_resp)

        self.log.info(
            "Step 3: Verified that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password and role")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15862')
    def test_1173(self):
        """
        Test that in case the password is changed the user should not be able to
        login with the old password

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_1173"]["data"]
        status_code = self.csm_conf["test_1173"]["status_code"]

        # Verifying that CSM admin user should not be able to login with old password
        self.log.info(
            "Step 1: Verifying that CSM admin user should not be able to login"
            " with old password")

        username = self.csm_obj.config["csm_admin_user"]["username"]

        self.log.info(
            "Step 1A: Login as csm root user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm root user")
        old_password = self.csm_obj.config["csm_admin_user"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: %s", payload_user)

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username, data=True, payload=json.dumps(payload_user),
            return_actual_response=True, login_as="csm_admin_user")

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm user %s", data[0], username)
        self.log.info(
            "Step 1B:Logging in as csm root user %s with new password %s",
            username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_obj.verify_modify_csm_user(
            self.log.info(
                "Step 1C:Verifying by logging in as csm root user %s with "
                "old password %s", username,
                self.csm_obj.config["csm_admin_user"]["password"]))
        payload_login = {"username": username, "password": old_password}

        response = self.csm_obj.restapi.rest_call(
            request_type="post",
            endpoint=self.csm_obj.config["rest_login_endpoint"],
            data=json.dumps(payload_login),
            headers=self.csm_obj.config["Login_headers"])

        assert_utils.assert_equals(response.status_code, status_code)

        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_obj.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info(
            "Step 1: Verified that CSM admin user should not be able to login"
            " with old password")

        # Verifying that CSM manage user should not be able to login with old
        # password
        self.log.info(
            "Step 2: Verifying that CSM manage user should not be able to login"
            " with old password")

        username = self.csm_obj.config["csm_user_manage"]["username"]

        self.log.info(
            "Step 2A: Login as csm manage user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm manage user")
        old_password = self.csm_obj.config["csm_user_manage"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: %s", payload_user)

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True,
            login_as="csm_user_manage")

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verifying response code 200 was returned")

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm manage user %s", data[0], username)
        self.log.info(
            "Step 2B:Logging in as csm manage user %s with new password %s",
            username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s", response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully "
                      "for csm manage user %s", data[0], username)

        self.log.info(
            "Step 2C:Verifying by logging in as csm manage user %s with old "
            "password %s", username,
            self.csm_obj.config["csm_user_manage"]["password"])
        payload_login = {"username": username, "password": old_password}

        response = self.csm_obj.restapi.rest_call(
            request_type="post",
            endpoint=self.csm_obj.config["rest_login_endpoint"],
            data=json.dumps(payload_login),
            headers=self.csm_obj.config["Login_headers"])

        self.log.info("Verifying the status code %s returned",
                      response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_obj.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info(
            "Step 2: Verified that CSM manage user should not be able to login"
            " with old password")

        # Verifying that CSM monitor user should not be able to login with old
        # password
        self.log.info(
            "Step 3: Verifying that CSM monitor user should not be able to "
            "login with old password")

        username = self.csm_obj.config["csm_user_monitor"]["username"]

        self.log.info(
            "Step 3A: Login as csm monitor user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm monitor user")
        old_password = self.csm_obj.config["csm_user_monitor"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: %s", payload_user)

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True,
            login_as="csm_user_monitor")

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm monitor user %s", data[0], username)
        self.log.info(
            "Step 3B:Logging in as csm monitor user %s with new "
            "password %s", username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s",
                      response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully "
                      "for csm monitor user %s", data[0], username)

        self.log.info(
            "Step 3C:Verifying by logging in as csm monitor user %s "
            "with old password %s", username,
            self.csm_obj.config["csm_user_monitor"]["password"])
        payload_login = {"username": username, "password": old_password}
        response = self.csm_obj.restapi.rest_call(
            request_type="post",
            endpoint=self.csm_obj.config["rest_login_endpoint"],
            data=json.dumps(payload_login),
            headers=self.csm_obj.config["Login_headers"])

        self.log.info("Verifying the status code %s returned",
                      response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_obj.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info(
            "Step 3: Verified that CSM monitor user should not be able to login"
            " with old password")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16550')
    def test_1227(self):
        """
        Test that CSM user with role manager cannot perform any REST API request
        on IAM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying CSM user with role manager cannot perform any REST API "
            "request on IAM user")
        self.log.info(
            "Step 1: Verifying CSM admin user cannot perform GET request on "
            "IAM user")
        rest_iam_user = RestIamUser()
        new_iam_user = "testiam" + str(int(time.time()))
        response = rest_iam_user.list_iam_users(login_as="csm_admin_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 1: Verified CSM admin user cannot perform GET request on "
            "IAM user")

        self.log.info(
            "Step 2: Verifying CSM manage user cannot perform GET request on "
            "IAM user")
        response = rest_iam_user.list_iam_users(
            login_as="csm_user_manage")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified CSM manage user cannot perform GET request on "
            "IAM user")

        self.log.info("Creating IAM user for test verification purpose")
        rest_iam_user = RestIamUser()
        self.log.info(
            "Step 3: Verifying CSM admin user cannot perform POST request on "
            "IAM user")
        new_iam_user1 = "testiam" + str(int(time.time()))
        response = rest_iam_user.create_iam_user(
            user=new_iam_user1, login_as="csm_admin_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 3: Verified CSM admin user cannot perform POST request on "
            "IAM user")

        self.log.info(
            "Step 4: Verifying CSM manage user cannot perform POST request on "
            "IAM user")
        new_iam_user2 = "testiam" + str(int(time.time()))
        response = rest_iam_user.create_iam_user(
            user=new_iam_user2, login_as="csm_user_manage")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 4: Verified CSM manage user cannot perform POST request on "
            "IAM user")

        self.log.info(
            "Step 5: Verifying CSM admin user cannot perform DELETE request on "
            "IAM user")
        response = rest_iam_user.delete_iam_user(
            user=new_iam_user1, login_as="csm_admin_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 5: Verified CSM admin user cannot perform DELETE request on "
            "IAM user")

        self.log.info(
            "Step 6: Verifying CSM manage user cannot perform DELETE request on"
            " IAM user")
        response = rest_iam_user.delete_iam_user(
            user=new_iam_user1, login_as="csm_user_manage")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 6: Verified CSM manage user cannot perform DELETE request on "
            "IAM user")

        self.log.info(
            "Verified CSM user with role manager cannot perform any REST API "
            "request on IAM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("EOS-27117 Test is not valid anymore")
    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16551')
    def test_1040(self):
        """
        Test that S3 account should not have access to create csm user from backend

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that S3 account does not have access to create csm user "
            "from backend")
        response = self.csm_obj.create_csm_user(login_as="s3account_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Verified that S3 account does not have access to create csm user "
            "from backend")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16552')
    def test_1172(self):
        """
        Test that the error messages related to the Log-in should not display
        any important information.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that the error messages related to the Log-in does not "
            "display any important information.")

        # self.rest_lib = RestTestLib()
        username = self.csm_conf["test_1172"]["username"]
        password = self.csm_conf["test_1172"]["password"]
        status_code = self.csm_conf["test_1172"]["status_code"]

        self.log.info("Step 1: Verifying with incorrect password")
        response = self.csm_obj.custom_rest_login(
            username=self.csm_obj.config["csm_admin_user"]["username"],
            password=password)
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Step 1: Verified with incorrect password")

        self.log.info("Step 2: Verifying with incorrect username")
        response = self.csm_obj.custom_rest_login(
            username=username, password=self.csm_obj.config[
                "csm_admin_user"]["password"])
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Step 2: Verified with incorrect username")

        self.log.info(
            "Verified that the error messages related to the Log-in does not "
            "display any important information.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16936')
    def test_7362(self):
        """
        Test that CSM user with monitor role cannot perform POST, PATCH and
        DELETE request on CSM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        password = self.csm_conf["test_7362"]["password"]

        self.log.info(
            "Step 1: Verifying that CSM user with monitor role cannot perform "
            "POST request to create new csm user")

        response = self.csm_obj.create_csm_user(login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 1: Verified that CSM user with monitor role cannot perform "
            "POST request to create new csm user")

        self.log.info(
            "Creating csm user for testing delete and patch requests")
        response = self.csm_obj.create_csm_user()
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        self.log.info(
            "Verified user was created successfully")
        userid = response.json()["id"]
        self.created_users.append(userid)

        self.log.info(
            "Step 2: Verifying that CSM user with monitor role cannot perform "
            "DELETE request on a csm user")
        response = self.csm_obj.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.FORBIDDEN,
            user=userid,
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 2: Verified that CSM user with monitor role cannot perform"
            " DELETE request on a csm user")

        self.log.info(
            "Step 3: Verifying that CSM user with monitor role cannot perform"
            " PATCH request on a CSM user")

        self.log.info("Forming the payload")
        old_password = self.csm_obj.config["csm_user_monitor"]["password"]
        payload = {"current_password": old_password, "password": password}

        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned : %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 3: Verified that CSM user with monitor role cannot perform "
            "PATCH request on a CSM user")

        self.log.info(
            "Verified that CSM user with monitor role cannot perform POST,"
            " PATCH and DELETE API request for CSM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16935')
    def test_7361(self):
        """
        Test that CSM user with role manager cannot perform DELETE and PATCH
        API request on S3 Accounts

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that CSM user with role manager cannot perform PATCH and"
            " DELETE API request on S3 Account")

        username = self.csm_obj.config["s3account_user"]["username"]

        self.log.info(
            "Step 1: Verifying that root csm user cannot perform PATCH API "
            "request on S3 Account")
        response = self.csm_obj.edit_s3_account_user(
            username=username, login_as="csm_admin_user")

        self.log.debug("Verifying response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 1: Verified that root csm user cannot perform PATCH API "
            "request on S3 Account")

        self.log.info(
            "Step 2: Verifying that CSM user with role manager cannot perform "
            "PATCH API request on S3 Account")
        response = self.csm_obj.edit_s3_account_user(
            username=username, login_as="csm_user_manage")

        self.log.debug("Verifying response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 2: Verified that CSM user with role manager cannot perform "
            "PATCH API request on S3 Account")

        self.log.info(
            "Step 3: Verifying that root csm user cannot perform DELETE API "
            "request on S3 Account")
        response = self.csm_obj.delete_s3_account_user(
            username=username, login_as="csm_admin_user")

        self.log.debug("Verifying response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 3: Verified that root csm user cannot perform DELETE API "
            "request on S3 Account")

        self.log.info(
            "Step 4: Verifying that CSM user with role manager cannot perform "
            "DELETE API request on S3 Account")
        response = self.csm_obj.delete_s3_account_user(
            username=username, login_as="csm_user_manage")

        self.log.debug("Verifying response returned : %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 4: Verified that CSM user with role manager cannot perform "
            "DELETE API request on S3 Account")

        self.log.info(
            "Verified that CSM user with role manager cannot perform PATCH and "
            "DELETE API request on S3 Account")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-17191')
    def test_7360(self):
        """
        Test that CSM user with role manager cannot perform REST API request on
        S3 Buckets
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that CSM user with role manager cannot perform REST "
            "API request on S3 Buckets")
        self.log.info(
            "Creating valid bucket and valid bucket policy for test purpose")
        s3_buckets = RestS3Bucket()
        self.log.info("Creating bucket for test")
        response = s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")

        self.log.debug("Verifying S3 bucket was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.debug("Verified S3 bucket %s was created successfully",
                       response.json()['bucket_name'])
        bucket_name = response.json()['bucket_name']
        bucket_policy_obj = RestS3BucketPolicy(bucket_name)

        self.log.info(
            "Step 1: Verifying that CSM user with role manager cannot perform "
            "GET REST API request on S3 Buckets")
        response = s3_buckets.list_all_created_buckets(
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 1: Verified that CSM user with role manager cannot perform "
            "GET REST API request on S3 Buckets")

        self.log.info(
            "Step 2: Verifying that CSM user with role manager cannot perform "
            "POST REST API request on S3 Buckets")
        response = s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code, const.FORBIDDEN)

        self.log.info(
            "Step 2: Verified that CSM user with role manager cannot perform "
            "POST REST API request on S3 Buckets")

        self.log.info(
            "Step 3: Verifying that CSM user with role manager cannot perform"
            "DELETE REST API request on S3 Buckets")
        response = s3_buckets.delete_s3_bucket(
            bucket_name=bucket_name, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 3: Verified that CSM user with role manager cannot "
            "perform DELETE REST API request on S3 Buckets")

        self.log.info(
            "Step 4: Verifying that CSM manage user cannot perform "
            "PATCH bucket policy request for a S3 bucket")
        operation = "default"
        custom_policy_params = {}
        response = bucket_policy_obj.create_bucket_policy(
            operation=operation, custom_policy_params=custom_policy_params,
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code, const.FORBIDDEN)

        self.log.info(
            "Step 5: Verifying that CSM user with role manager cannot perform "
            "GET bucket policy request for S3 Buckets")
        response = bucket_policy_obj.get_bucket_policy(
            bucket_name=bucket_name, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 5: Verifying that CSM user with role manager cannot perform"
            " GET bucket policy request for S3 Buckets")

        self.log.info(
            "Step 6: Verifying that CSM user with role manager cannot perform "
            "DELETE bucket policy request for S3 Buckets")
        response = bucket_policy_obj.delete_bucket_policy(
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 6: Verified that CSM user with role manager cannot "
            "perform DELETE bucket policy request for S3 Buckets")

        self.log.info(
            "Verified that CSM user with role manager cannot perform "
            "REST API request on S3 Buckets")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12019')
    def test_7420(self):
        """
        Test that Root user should able to change other users password and roles
        without specifying old_password through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying that csm root user should able to change "
            "other users password and roles without specifying old_password")

        data = self.csm_conf["test_7420"]["data"]
        self.log.info("Step 1: Creating csm manage user")
        response = self.csm_obj.create_csm_user(
            user_type=data[0], user_role=data[1])

        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info(
            "Verified User %s got created successfully", username)

        self.log.info(
            "Step 2: Login as csm root user and change password and role of "
            "user without providing old password %s", username)
        self.log.info("Forming the payload without specifying old password")
        payload_user = {"role": data[2], "password": data[3]}
        response = self.csm_obj.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s and role %s was updated "
                      "successfully for csm user %s", data[3], data[2], username)
        self.log.info(
            "Logging in as user %s with new password %s", username, data[3])
        payload_login = {"username": username, "password": data[3]}
        response = self.csm_obj.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS
        assert response.json()["role"] == data[2]

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s", response.status_code, response.json())
        self.log.info("Verified that the password %s and role %s was updated"
                      " successfully for csm user %s", data[3], response.json()["role"], username)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-25278')
    def test_25278(self):
        """
        Function to test Monitor user is not able to edit the roles of the
        admin, manage and other monitor user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25278"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info("Step 1: Creating csm user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Step 2: Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Step 3: Verfying edit user functionality for admin user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor",
                                               user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               role="manage")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_monitor",
                                                            CSM_REST_CFG["csm_admin_user"][
                                                                "username"]), (
                                                                "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 4: Verfying edit user functionality for manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor", user="csm_user_manage",
                                               role="monitor")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_monitor",
                                                            "csm_user_manage"), (
                                                            "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 5: Verfying edit user functionality for monitor user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor", user=username,
                                               role="manage")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_monitor",
                                                            username), "Message check failed."
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info(
            "Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-25280')
    def test_25280(self):
        """
        Function to test Monitor user is not able to edit the passwords of the
        admin, manage and other monitor user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25280"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[1]
        self.log.info("Step 1: Creating csm user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Step 2: Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        password = CSM_REST_CFG["csm_user_monitor"]["password"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        self.log.info("Verified User %s got created successfully", username)
        new_monitor_user = {}
        new_monitor_user['username'] = username
        new_monitor_user['password'] = password
        self.log.info("Step 3: Verifying edit user functionality for admin user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor",
                                               user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               password=CSM_REST_CFG["csm_admin_user"]["password"],
                                               current_password=test_cfg["current_password"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_monitor",
                                                            CSM_REST_CFG["csm_admin_user"][
                                                                "username"]), (
                                                                "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 4: Verifying edit user functionality for manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor",
                                               user=CSM_REST_CFG["csm_user_manage"]["username"],
                                               password=CSM_REST_CFG["csm_user_manage"]["password"],
                                               current_password=test_cfg["current_password"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_monitor",
                                                            "csm_user_manage"), (
                                                            "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."

        self.log.info("Step 5: Verifying edit user functionality for other monitor user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor",

                                               user=username,
                                               password=CSM_REST_CFG["csm_user_monitor"][
                                                   "password"],
                                               current_password=test_cfg["current_password"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_monitor",
                                                            username), "Message check failed."
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 6: Verifying edit user functionality for self monitor user")
        response = self.csm_obj.edit_csm_user(login_as=new_monitor_user,
                                               user=username,
                                               password=test_cfg["current_password"],
                                               current_password=password)

        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info(
            "Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-25282')
    def test_25282(self):
        """
        Function to test Monitor user is not able to edit the email ids of the
        admin, manage and other monitor user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25282"]
        self.log.info("Creating monitor user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        password = CSM_REST_CFG["csm_user_manage"]["password"]
        self.created_users.append(userid)
        self.log.info("users list is %s", self.created_users)
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Creating manage user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        user_name = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Step 3: Verifying edit email functionality for admin user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor",
                                               user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               email=test_cfg["email_id"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(test_cfg["error_code"]), (
            "Error code check failed.")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == test_cfg["message"].format("csm_user_monitor",
                                                                            "admin"), (
                                                                            "Message check failed.")
        assert response.json()["message_id"] == test_cfg["message_id"], "Message ID check failed."
        self.log.info("Step 4: Verifying edit email functionality for manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor",
                                               user=CSM_REST_CFG["csm_user_manage"]["username"],
                                               email=test_cfg["email_id"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(test_cfg["error_code"]), (
            "Error code check failed.")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == test_cfg["message"].format("csm_user_monitor",
                                                                            "csm_user_manage"), (
                                                                            "Message check failed.")
        assert response.json()["message_id"] == test_cfg["message_id"], "Message ID check failed."
        self.log.info("Step 5: Verifying edit email functionality for monitor user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_monitor", user=username,
                                               email=test_cfg["email_id"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(test_cfg["error_code"]), (
            "Error code check failed.")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == test_cfg["message"].format("csm_user_monitor",
                                                                            username), (
                                                                            "Message check failed.")
        assert response.json()["message_id"] == test_cfg["message_id"], "Message ID check failed."
        self.log.info("Step 6: Verifying edit email functionality for self monitor user")
        new_user = {}
        new_user['username'] = username
        new_user['password'] = password
        self.log.info("new user is", new_user)
        response = self.csm_obj.edit_csm_user(login_as=new_user,
                                               user=username,
                                               email=test_cfg["email_id"])
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 7: Verifying edit email functionality for self manage user")
        new_user = {}
        new_user['username'] = user_name
        new_user['password'] = password
        self.log.info("new user is", new_user)
        response = self.csm_obj.edit_csm_user(login_as=new_user,
                                               user=user_name,
                                               email=test_cfg["email_id"])
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info(
            "Sending request to delete csm users %s and %s", username, user_name)
        response = self.csm_obj.delete_csm_user(userid)
        assert response.status_code == const.SUCCESS_STATUS, "Monitor User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(userid)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == const.SUCCESS_STATUS, "Manage User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-25275')
    def test_25275(self):
        """
        Test case for verifying Manage user is not able to create admin user and
        Manage user should be able to create new Manage and monitor users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25275"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        self.log.info("Step 1: Verify create admin user functionality for manage user")
        response = self.csm_obj.create_csm_user(login_as="csm_user_manage",
                                                 user_type="valid", user_role="admin")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin",
                                                            "admin"), "Message check failed."
        self.log.info("Step 2: Verify create manage user functionality for manage user")
        response = self.csm_obj.create_csm_user(login_as="csm_user_manage",
                                                 user_type="valid", user_role="manage")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST, "Status code check failed."
        username = response.json()["username"]
        self.created_users.append(username)
        self.log.info("Step 3: Verify create monitor user functionality for manage user")
        response = self.csm_obj.create_csm_user(login_as="csm_user_manage",
                                                 user_type="valid", user_role="monitor")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST, "Status code check failed."
        username = response.json()["username"]
        self.created_users.append(username)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)
 
    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-25279')
    def test_25279(self):
        """
        Function to test Manage user is not able to edit the passwords of the
        admin user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25279"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[1]
        self.log.info("Step 1: Verifying edit admin password functionality for manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_manage",
                                               user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               password=CSM_REST_CFG["csm_admin_user"]["password"],
                                               current_password=test_cfg["current_password"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_manage",
                                                            CSM_REST_CFG["csm_admin_user"][
                                                                "username"]), (
                                                                "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-25281')
    def test_25281(self):
        """
        Function to test Manage user is not able to edit the email id of the
        admin user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25281"]
        resp_error_code = test_cfg["error_code"]
        resp_msg = self.rest_resp_conf[resp_error_code]["update_not_allowed"][4]
        resp_msg_id = test_cfg["message_id"]
        self.log.info("Creating csm user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Step 1: Verifying edit admin email id functionality for manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_manage",
                                               user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               email=test_cfg["email_id"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        assert response.json()["message"] == resp_msg.format("csm_user_manage",
                                                             "cortxadmin"), "Message check failed."
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 2: Verifying edit monitor user email id functionality for monitor user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_manage",
                                               user=CSM_REST_CFG["csm_user_monitor"]["username"],
                                               email=test_cfg["email_id"])
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."

        self.log.info("Step 3: Verifying edit self email id functionality for manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_manage",
                                               user=CSM_REST_CFG["csm_user_manage"]["username"],
                                               email=test_cfg["email_id"])
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 4: Verifying edit email id functionality for other manage user")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_manage",
                                               user=username,
                                               email=test_cfg["email_id"])
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info(
            "Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-25277')
    def test_25277(self):
        """
        Test case for verifying last admin user is not able to edit self role to manage
        or monitor
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25277"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[3]
        self.log.info("Step 1: Verify if last admin user"
                      "is not able to edit the self role to manage")
        response = self.csm_obj.edit_csm_user(user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               role="manage")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin"), (
                "Message check failed.")
            self.log.info("Msg check successful!!!!")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 2: Verify if last admin user"
                      "is not able to edit the self role to monitor")
        response = self.csm_obj.edit_csm_user(user=CSM_REST_CFG["csm_admin_user"]["username"],
                                               role="monitor")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin"), (
                "Message check failed.")
            self.log.info("Msg check successful!!!!")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Creating csm user")
        password = CSM_REST_CFG["csm_admin_user"]["password"]
        response = self.csm_obj.create_csm_user(user_type="valid",
                                                 user_role="admin", user_password=password)
        self.log.info("Verifying if admin user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info("users list is %s", self.created_users)
        assert response.json()['role'] == 'admin', "User is not created with admin role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        new_user = {}
        new_user['username'] = username
        new_user['password'] = password
        self.log.info("Step 3: Verify if other admin user"
                      "is able to edit the self role to manage")
        response = self.csm_obj.edit_csm_user(login_as=new_user, user=username,
                                               role="manage")
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Creating csm user")
        response = self.csm_obj.create_csm_user(user_type="valid",
                                                 user_role="admin", user_password=password)
        self.log.info("Verifying if admin user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        assert response.json()['role'] == 'admin', "User is not created with admin role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        new_user = {}
        new_user['username'] = username
        new_user['password'] = password
        self.log.info("Step 4: Verify if other admin user"
                      "is able to edit the self role to monitor")
        response = self.csm_obj.edit_csm_user(login_as=new_user, user=username,
                                               role="monitor")
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info(
            "Sending request to delete csm user %s", userid)
        response = self.csm_obj.delete_csm_user(userid)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(userid)
        self.log.info(
            "Sending request to delete csm user %s", user_id)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-25286')
    def test_25286(self):
        """
        Test case for verifying delete last admin user functionality
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25286"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[2]
        self.log.info("Pre-requistile: Checking for admin users")
        resp = self.csm_obj.list_csm_users(HTTPStatus.OK, return_actual_response=True)
        assert resp.status_code == HTTPStatus.OK, "List user failed"
        for user in resp.json()["users"]:
            user_id = user['id']
            if user["role"] == "admin" and user_id != CSM_REST_CFG["csm_admin_user"]["username"]:
                self.log.info("Deleting extra admin user : %s", user_id)
                resp = self.csm_obj.delete_csm_user(user_id)
                assert resp.status_code == HTTPStatus.OK, f"Delete user {user_id} failed"
        self.log.info("Step 1: Verify delete last admin user functionality")
        response = self.csm_obj.delete_csm_user(CSM_REST_CFG["csm_admin_user"]["username"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin"), (
                "Message check failed.")
            self.log.info("Msg check successful!!!!")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-25283')
    def test_25283(self):
        """
        Test case for verifying Manage user is not able to delete admin user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25283"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[2]
        msg1 = resp_data[3]
        self.log.info("Creating manage user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.created_users.append(userid)
        self.log.info("users list is %s", self.created_users)
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Creating monitor user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        user_name = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        self.log.info("Verified User %s got created successfully", user_name)
        self.log.info("Step 1: Verify delete admin user functionality for manage user")
        response = self.csm_obj.delete_csm_user(login_as="csm_user_manage",
                                                 user_id=CSM_REST_CFG["csm_admin_user"]["username"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin"), (
                "Message check failed.")
            self.log.info("Msg check successful!!!!")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 2: Verify delete other monitor user functionality for manage user")
        response = self.csm_obj.delete_csm_user(login_as="csm_user_manage",
                                                 user_id=user_id)
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg1, (
                "Message check failed.")
            self.log.info("Msg check successful!!!!")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(userid)
        self.log.info("Step 3: Verify delete other manage user functionality for manage user")
        response = self.csm_obj.delete_csm_user(login_as="csm_user_manage",
                                                 user_id=userid)
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg1, (
                "Message check failed.")
            self.log.info("Msg check successful!!!!")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-25285')
    def test_25285(self):
        """
        Test case for verifying Monitor user is not able to delete other admin, manage
        or monitor user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25285"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[2]
        msg1 = resp_data[3]
        self.log.info("Step 1: Creating csm manage user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Step 2: Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        password = CSM_REST_CFG["csm_user_manage"]["password"]
        new_user = {}
        new_user['username'] = username
        new_user['password'] = password
        assert response.json()['role'] == 'manage', "User is not created with manage role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 3: Verify delete admin user functionality for monitor user")
        response = self.csm_obj.delete_csm_user(login_as="csm_user_monitor",
                                                 user_id=CSM_REST_CFG["csm_admin_user"]["username"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin"), (
                "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 4: Verify delete manage user functionality for monitor user")
        response = self.csm_obj.delete_csm_user(login_as="csm_user_monitor",
                                                 user_id=CSM_REST_CFG["csm_user_manage"][
                                                     "username"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg1, "Message check failed."
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 5: Verify delete monitor user functionality for monitor user")
        response = self.csm_obj.delete_csm_user(login_as="csm_user_monitor",
                                                 user_id=username)
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg1, "Message check failed."
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 6: Verify delete monitor email functionality for self monitor user")
        response = self.csm_obj.delete_csm_user(login_as=new_user,
                                                 user_id=username)
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-25276')
    def test_25276(self):
        """
        Test case for verifying Monitor user is not able to create other admin, manage
        or monitor user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Verify create admin user functionality for monitor user")
        response = self.csm_obj.create_csm_user(login_as="csm_user_monitor",
                                                 user_type="valid", user_role="admin")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        self.log.info("Step 2: Verify create manage user functionality for monitor user")
        response = self.csm_obj.create_csm_user(login_as="csm_user_monitor",
                                                 user_type="valid", user_role="manage")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        self.log.info("Step 3: Verify create monitor user functionality for monitor user")
        response = self.csm_obj.create_csm_user(login_as="csm_user_monitor",
                                                 user_type="valid", user_role="monitor")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28513')
    def test_28513(self):
        """
        Test that Login API returns error Response Code 401 if Password in payload is Incorrect
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 401 "
            "if Password in payload is Incorrect")

        test_cfg = self.csm_conf["test_28513"]
        incorrect_password = test_cfg["password"]
        status_code = test_cfg["status_code"]
        # resp_error_code = test_cfg["error_code"]
        # msg = test_cfg["message"]
        # resp_msg_id = test_cfg["message_id"]

        self.log.info("Step 1: Verifying with incorrect password")
        response = self.csm_obj.custom_rest_login(
            username=self.csm_obj.config["csm_admin_user"]["username"],
            password=incorrect_password)
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Step 1: Verified with incorrect password")
        #  TODO check response msg
        # self.log.info("Step 2: Verifying error response...")
        # assert_utils.assert_equals(response.json()["error_code"],
        #                            str(resp_error_code))
        # if CSM_REST_CFG["msg_check"] == "enable":
        #     assert_utils.assert_equals(response.json()["message"],
        #                                msg)
        # assert_utils.assert_equals(response.json()["message_id"],
        #                            resp_msg_id)

        self.log.info(
            "Verified that Login API returns error Response Code 401 "
            "if Password in payload is Incorrect")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28512')
    def test_28512(self):
        """
        Test that Login API returns error Response Code 401 if Username in payload is Incorrect
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 401 "
            "if Username in payload is Incorrect")

        test_cfg = self.csm_conf["test_28512"]
        incorrect_username = test_cfg["username"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with incorrect username")
        response = self.csm_obj.custom_rest_login(
            username=incorrect_username, password=self.csm_obj.config[
                "csm_admin_user"]["password"])
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Step 1: Verified with incorrect username")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 401 "
            "if Username in payload is Incorrect")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28515')
    def test_28515(self):
        """
        Test that Login API returns error Response Code 401 if Password in payload is Invalid
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 401 "
            "if Password in payload is Invalid")

        test_cfg = self.csm_conf["test_28515"]
        invalid_password = test_cfg["password"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with invalid password")
        response = self.csm_obj.custom_rest_login(
            username=self.csm_obj.config["csm_admin_user"]["username"],
            password=invalid_password)
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Step 1: Verified with invalid password")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 401 "
            "if Password in payload is Invalid")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28514')
    def test_28514(self):
        """
        Test that Login API returns error Response Code 401 if Username in payload is Invalid
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 401 "
            "if Username in payload is Invalid")

        test_cfg = self.csm_conf["test_28514"]
        invalid_username = test_cfg["username"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with invalid username")
        response = self.csm_obj.custom_rest_login(
            username=invalid_username, password=self.csm_obj.config[
                "csm_admin_user"]["password"])
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Step 1: Verified with invalid username")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 401 "
            "if Username in payload is Invalid")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28511')
    def test_28511(self):
        """
        Test that Login API returns error Response Code 400 if Password in payload is Empty
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 400 "
            "if Password in payload is Empty")

        empty_password = ""
        test_cfg = self.csm_conf["test_28511"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with empty password")
        response = self.csm_obj.custom_rest_login(
            username=self.csm_obj.config["csm_admin_user"]["username"],
            password=empty_password)
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Step 1: Verified with empty password")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 400 "
            "if Password in payload is Empty")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28510')
    def test_28510(self):
        """
        Test that Login API returns error Response Code 400 if Username in payload is Empty
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 400 "
            "if Username in payload is Empty")

        empty_username = ""
        test_cfg = self.csm_conf["test_28510"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with empty username")
        response = self.csm_obj.custom_rest_login(
            username=empty_username, password=self.csm_obj.config[
                "csm_admin_user"]["password"])
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Step 1: Verified with empty username")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 400 "
            "if Username in payload is Empty")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28509')
    def test_28509(self):
        """
        Test that Login API returns error Response Code 400 if Password in payload is Missing
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 400 "
            "if Password in payload is Missing")

        test_cfg = self.csm_conf["test_28509"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with missing password")
        response = self.csm_obj.custom_rest_login_missing_param(
            param1=self.csm_obj.config["csm_admin_user"]["username"],
            param1_key="username")
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Step 1: Verified with missing password")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 400 "
            "if Password in payload is Missing")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28508')
    def test_28508(self):
        """
        Test that Login API returns error Response Code 400 if Username in payload is Missing
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns error Response Code 400 "
            "if Username in payload is Missing")

        test_cfg = self.csm_conf["test_28508"]
        status_code = test_cfg["status_code"]

        self.log.info("Step 1: Verifying with missing username")
        response = self.csm_obj.custom_rest_login_missing_param(
            param1=self.csm_obj.config["csm_admin_user"]["password"],
            param1_key="password")
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Step 1: Verified with missing username")
        #  TODO check response msg

        self.log.info(
            "Verified that Login API returns error Response Code 400 "
            "if Username in payload is Missing")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.sanity
    @pytest.mark.lc
    @pytest.mark.lr
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-28522')
    def test_28522(self):
        """
        Test that Login API returns success Response Code 200(OK) for Correct Credentials
        """
        test_case_name = cortxlogging.get_frame()
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that Login API returns success Response Code 200(OK) "
            "for Correct Credentials")

        self.log.info("Step 1: Verifying with Correct Credentials")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)
        self.log.info("Expected Response: %s", HTTPStatus.OK)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK)
        self.log.info("Step 1: Verified with Correct Credentials")

        self.log.info(
            "Verifying that Login API returns success Response Code 200(OK) "
            "for Correct Credentials")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.sanity
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28501')
    def test_28501(self):
        """
        Function to test password reset functionality: expect 200 response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        new_password = self.csm_conf["test_28501"]["new_password"]
        reset_password = self.csm_conf["test_28501"]["reset_password"]

        self.log.info("Step 1: Changing user password")
        response = self.csm_obj.update_csm_user_password(admin_username, new_password,
                                                          reset_password)

        self.log.info("Step 2: Verify response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 3: Check login with new password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=new_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 4: Reverting user password")
        header = self.csm_obj.get_headers(admin_username, new_password)

        self.log.info("Step 4.1: Changing user password for header {}".format(header))
        response = self.csm_obj.reset_user_password(admin_username, admin_password, reset_password,
                                                     header)

        self.log.info("Step 5: Verify response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 6: Check login with reverted password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28502')
    def test_28502(self):
        """
        Function to test password reset functionality with empty payload:  expect 400 response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        new_password = ""
        reset_password = True

        self.log.info("Step 1: Changing user password")
        response = self.csm_obj.update_csm_user_password(admin_username, new_password,
                                                          reset_password)

        self.log.info("Step 2: Verify response: 400")
        self.csm_obj.check_expected_response(response, HTTPStatus.BAD_REQUEST)
        if CSM_REST_CFG["msg_check"] == "enable":
            resp_data = self.rest_resp_conf[4099]['invalid parameter msg_id']
            assert_utils.assert_equals(response.json()["message"], resp_data[0])

        self.log.info("Step 3: Check login with existing password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28505')
    def test_28505(self):
        """
        Function to test password reset functionality: Dont follow password policy
        Expect 400 response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        new_password = self.csm_conf["test_28505"]["new_password"]
        reset_password = self.csm_conf["test_28505"]["reset_password"]

        self.log.info("Step 1: Changing user password")
        response = self.csm_obj.update_csm_user_password(
            CSM_REST_CFG["csm_admin_user"]["username"], new_password, reset_password)

        self.log.info("Step 2: Verify response 400")
        if response.status_code == HTTPStatus.OK:
            self.log.info("Revert password")
            header = self.csm_obj.get_headers(admin_username, new_password)
            self.log.info("Step: Changing user password for header {}".format(header))
            response_reset = self.csm_obj.reset_user_password(admin_username, admin_password,
                                                               reset_password, header)
            self.log.info("Step: Verify success response")
            self.csm_obj.check_expected_response(response_reset, HTTPStatus.OK)

        self.csm_obj.check_expected_response(response, HTTPStatus.BAD_REQUEST)
        if CSM_REST_CFG["msg_check"] == "enable":
            resp_data = self.rest_resp_conf[4099]['invalid parameter msg_id']
            assert_utils.assert_equals(response.json()["message"], resp_data[1])

        self.log.info("Step 3: Check login with existing password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

    @pytest.mark.sanity
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28506')
    def test_28506(self):
        """
        Function to test password reset functionality: Try login with old password
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        new_password = self.csm_conf["test_28501"]["new_password"]
        reset_password = self.csm_conf["test_28501"]["reset_password"]

        self.log.info("Step 1: Changing user password")
        response = self.csm_obj.update_csm_user_password(admin_username, new_password,
                                                          reset_password)

        self.log.info("Step 2: Verify success response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 3: Check login with new password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=new_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 4: Check login with old password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK, True)

        self.log.info("Step 5: Reverting user password")
        header = self.csm_obj.get_headers(admin_username, new_password)

        self.log.info("Step 5.1: Changing user password for header {}".format(header))
        response = self.csm_obj.reset_user_password(admin_username, admin_password, reset_password,
                                                     header)

        self.log.info("Step 6: Verify success response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 7: Check login with reverted password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)
        if response.status_code == HTTPStatus.OK:
            self.log.info("Verified log in with reverted password")
        else:
            self.log.error("Log in with reverted password failed")
            assert False, "Log in with reverted password failed"

    @pytest.mark.skip
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28517')
    def test_28517(self):
        """
        Function to test token expire after 1 hr
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        new_password = self.csm_conf["test_28517"]["new_password"]
        reset_password = self.csm_conf["test_28517"]["reset_password"]
        token_expire_timeout = self.csm_conf["test_28517"]["token_expire_timeout"]
        sleep_time = 10 * 60  # 10 min

        self.log.info("Step 1: Get header-1")
        header1 = self.csm_obj.get_headers(admin_username, admin_password)

        self.log.info("Step 2: Get header-2")
        header2 = self.csm_obj.get_headers(admin_username, admin_password)

        self.log.info("Step 3: Get header-3")
        header3 = self.csm_obj.get_headers(admin_username, admin_password)

        headers = [header1, header2, header3]
        for header in headers:
            self.log.info("Step 4.1: Changing user password for header {}".format(header))
            response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                         reset_password, header)

            self.log.info("Step 4.2: Verify success response")
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        time.sleep(sleep_time)
        self.log.info("Step 5.1: Changing user password")
        response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                     reset_password, header2)

        self.log.info("Step 5.2: Verify success response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 6: Try resetting user password till token expire timeout")
        end_time = time.time() + (token_expire_timeout - sleep_time)
        while time.time() <= end_time:
            self.log.info("Step 7.1: Changing user password")
            response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                         reset_password, header3)

            self.log.info("Step 7.2: Verify success response")
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
            time.sleep(sleep_time)

        self.log.info("Step 8: Verify that token expires after timeout")
        for header, header_num in enumerate(headers):
            if header_num == 0 or header_num == 1:
                self.log.info("Step 9.1: Changing user password")
                response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                             reset_password, header)
                self.log.info("Step 9.2: Verify response")
                self.log.info("Verifying response code 200 is not returned")
                if response.status_code == HTTPStatus.OK:
                    self.log.info("Revert password")
                    header = self.csm_obj.get_headers(admin_username, new_password)
                    self.log.info("Step: Changing user password for header {}".format(header))
                    response_reset = self.csm_obj.reset_user_password(admin_username,
                                                                       admin_password,
                                                                       reset_password, header)
                    self.log.info("Step: Verify success response")
                    self.csm_obj.check_expected_response(response_reset, HTTPStatus.OK)

                self.csm_obj.check_expected_response(response, HTTPStatus.OK, True)
                time.sleep(sleep_time)

        # Check session active with activity in last 1 hr
        self.log.info("Step 10.1: Changing user password")
        response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                     reset_password, header3)

        self.log.info("Step 10.2: Verify response")
        self.log.info("Verifying response code 200 is returned")
        if response.status_code == HTTPStatus.OK:
            self.log.info("Revert password")
            header = self.csm_obj.get_headers(admin_username, new_password)
            self.log.info("Step: Changing user password for header {}".format(header))
            response_reset = self.csm_obj.reset_user_password(admin_username, admin_password,
                                                               reset_password, header)
            self.log.info("Step: Verify success response")
            self.csm_obj.check_expected_response(response_reset, HTTPStatus.OK)

        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

    @pytest.mark.sanity
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28516')
    def test_28516(self):
        """
        Function to test token expire after logout
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_username = self.csm_obj.config["csm_admin_user"]["username"]
        admin_password = self.csm_obj.config["csm_admin_user"]["password"]
        new_password = self.csm_conf["test_28517"]["new_password"]
        reset_password = self.csm_conf["test_28517"]["reset_password"]

        self.log.info("Step 1: Get header")
        header = self.csm_obj.get_headers(admin_username, admin_password)

        self.log.info("Step 2: Changing user password for header {}".format(header))
        response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                     reset_password, header)

        self.log.info("Step 3: Verify success response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 4: Logout user session")
        response = self.csm_obj.csm_user_logout(header)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 6: Verify that token expires after logout")
        self.log.info("Step 6.1: Changing user password")
        response = self.csm_obj.reset_user_password(admin_username, new_password,
                                                     reset_password, header)

        self.log.info("Step 6.2: Verify response")
        self.log.info("Verifying response code: 401")
        if response.status_code == HTTPStatus.OK:
            self.log.info("Revert password")
            header = self.csm_obj.get_headers(admin_username, new_password)
            self.log.info("Step: Changing user password for header {}".format(header))
            response_reset = self.csm_obj.reset_user_password(admin_username, admin_password,
                                                               reset_password, header)
            self.log.info("Step: Verify success response")
            self.csm_obj.check_expected_response(response_reset, HTTPStatus.OK)

        self.csm_obj.check_expected_response(response, HTTPStatus.UNAUTHORIZED)

        self.log.info("Step 7: Reverting user password")
        header = self.csm_obj.get_headers(admin_username, new_password)

        self.log.info("Step 7.1: Changing user password for header {}".format(header))
        response = self.csm_obj.reset_user_password(admin_username, admin_password,
                                                     reset_password, header)

        self.log.info("Step 8: Verify success response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        self.log.info("Step 9: Check login with reverted password")
        response = self.csm_obj.custom_rest_login(username=admin_username, password=admin_password)

        self.log.info("Step 10: Verify success response")
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32172')
    def test_32172(self):
        """
        Test that manage user should be able to change role of user with monitor role to manage role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating csm monitor user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Step 2: Verifying if monitor user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(username)
        assert response.json()['role'] == 'monitor', "User is not created with monitor role"
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Step 3: Verify manage user can change monitor user role")
        response = self.csm_obj.edit_csm_user(login_as="csm_user_manage",
                                               user=username,
                                               role='manage')
        assert response.status_code == HTTPStatus.OK, "Status code check failed."
        response = self.csm_obj.list_csm_single_user(
            request_type="get",
            expect_status_code=HTTPStatus.OK,
            user=username,
            return_actual_response=True)
        self.log.info("Verifying the status code returned")
        assert HTTPStatus.OK == response.status_code
        assert response.json()['role'] == 'manage', "Role update failed"
        self.log.info("Verified that role is changed to manage")
        self.log.info("Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
        self.created_users.remove(username)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32179')
    def test_32179(self):
        """
        Test that admin user should able to create users with admin, manage and monitor role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating csm monitor user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Step 2: Verifying if monitor user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(username)
        assert response.json()['role'] == 'monitor', "User is not created with monitor role"
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
        self.created_users.remove(username)
        self.log.info("Step 3: Creating csm manage user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Step 4: Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(username)
        assert response.json()['role'] == 'manage', "User is not created with manage role"
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
        self.created_users.remove(username)
        self.log.info("Step 5: Creating csm admin user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="admin")
        self.log.info("Step 6: Verifying if admin user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(username)
        assert response.json()['role'] == 'admin', "User is not created with admin role"
        self.log.info("Verified User %s got created successfully", username)
        self.log.info("Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
        self.created_users.remove(username)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32173')
    def test_32173(self):
        """
        Test that manage user should NOT be able to change role of self to any other role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating csm manage  user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Step 2: Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(username)
        password = CSM_REST_CFG["csm_user_manage"]["password"]
        assert response.json()['role'] == 'manage', "User is not created with manage role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 3: get header")
        header = self.csm_obj.get_headers(username, password)
        roles = ['monitor', 'admin']
        for role in roles:
            self.log.info("Step 4: Verify manage user can not change self role to %s", role)
            response = self.csm_obj.edit_user_with_custom_login(user=username, role=role,
                                                                 header=header)
            assert response.status_code == const.FORBIDDEN, "Status code check failed."
            response = self.csm_obj.list_csm_single_user(
                request_type="get",
                expect_status_code=HTTPStatus.OK,
                user=username,
                return_actual_response=True)
            self.log.info("Verifying the status code returned")
            assert HTTPStatus.OK == response.status_code
            assert response.json()['role'] == 'manage', "Role updated which is not expected"
            self.log.info("Verified that role is not changed ")
        self.log.info("Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Not Deleted Successfully."
        self.created_users.remove(username)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32175')
    def test_32175(self):
        """
        Test that manage user should be able to create and delete users with manage and monitor role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating csm monitor users")
        for _ in range(5):
            response = self.csm_obj.create_csm_user(login_as="csm_user_manage", user_type="valid",
                                                     user_role="monitor")
            self.log.info("Step 2: Verifying if monitor user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            user_id = response.json()["id"]
            self.created_users.append(username)
            assert response.json()['role'] == 'monitor', "User is not created with monitor role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Sending request to delete csm user %s", username)
            response = self.csm_obj.delete_csm_user(user_id)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.created_users.remove(username)
        self.log.info("Step 3: Creating csm manage users")
        for _ in range(5):
            response = self.csm_obj.create_csm_user(login_as="csm_user_manage", user_type="valid",
                                                     user_role="manage")
            self.log.info("Step 2: Verifying if monitor user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            user_id = response.json()["id"]
            self.created_users.append(username)
            assert response.json()['role'] == 'manage', "User is not created with manage role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Sending request to delete csm user %s", username)
            response = self.csm_obj.delete_csm_user(user_id)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.created_users.remove(username)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32176')
    def test_32176(self):
        """
        Test that manage and monitor user should able to login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating csm manage user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Step 2: Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        password = CSM_REST_CFG["csm_user_manage"]["password"]
        assert response.json()['role'] == 'manage', "User is not created with manage role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 3: Creating csm monitor user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Step 4: Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        password = CSM_REST_CFG["csm_user_monitor"]["password"]
        assert response.json()['role'] == 'monitor', "User is not created with monitor role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Sending request to delete csm user %s", username)
        response = self.csm_obj.delete_csm_user(user_id)
        assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(user_id)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32171')
    def test_32171(self):
        """
        Test that manage user should be able to change role of other manage role user 
        (NOT self) from manage role to monitor role and not to admin role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_32171"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        msg = resp_data[0]
        users = []
        self.log.info("Creating csm user")
        response = self.csm_obj.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        csm_username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        self.log.info("users list is %s", self.created_users)
        csm_password = CSM_REST_CFG["csm_user_manage"]["password"]
        assert response.json()['role'] == 'manage', "User is not created with manage role"

        self.log.info("Verified User %s got created successfully", csm_username)
        response = self.csm_obj.custom_rest_login(username=csm_username, password=csm_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)

        new_user = {}
        new_user['username'] = csm_username
        new_user['password'] = csm_password
        self.log.info('New user dict is %s', new_user)
        self.log.info("Creating 4 manage users")

        for _ in range(5):
            response = self.csm_obj.create_csm_user(login_as="csm_user_manage", user_type="valid",

                                                     user_role="manage")
            self.log.info("Verifying if manage user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            user_id = response.json()["id"]
            self.created_users.append(user_id)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'manage', "User is not created with manager role"
            self.log.info("Verified User %s got created successfully", username)
            users.append(username)
        self.log.info("Step 1: Change role of first manage user from manage to monitor %s",
                      csm_username)
        response = self.csm_obj.edit_csm_user(login_as=new_user, user=csm_username,
                                               role="monitor")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format(username,
                                                            username), "Message check failed."
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 2: Change role of second manage user from manage to monitor")
        response = self.csm_obj.edit_csm_user(login_as=new_user,
                                               user=users[1],
                                               role="monitor")
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 3: Change role of third manage user from manage to monitor")
        response = self.csm_obj.edit_csm_user(login_as=new_user,
                                               user=users[2],
                                               role="monitor")
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 4: Change role of fourth manage user from manage to admin")
        response = self.csm_obj.edit_csm_user(login_as=new_user, user=users[3],
                                               role="admin")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_manage",
                                                            "csm_user_manage"), (
                                                            "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 4: Change role of fifth manage user from manage to admin")
        response = self.csm_obj.edit_csm_user(login_as=new_user, user=users[4],
                                               role="admin")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("csm_user_manage",
                                                            "csm_user_manage"), (
                                                            "Message check failed.")
        assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32180')
    def test_32180(self):
        """
        Admin user should be able to delete any user including self if not last admin user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_32180"]
        resp_error_code = test_cfg["error_code"]
        msg = test_cfg["message"]
        resp_msg_id = test_cfg["message_id"]
        self.log.info("Step 1: Creating csm admin users")
        for _ in range(2):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="admin")
            self.log.info("Verifying if admin user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'admin', "User is not created with admin role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Sending request to delete csm admin user %s", username)
            response = self.csm_obj.delete_csm_user(username)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(username)
        self.log.info("Step 2: Creating csm manage users")
        for _ in range(2):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="manage")
            self.log.info("Verifying if manage user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'manage', "User is not created with manage role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Sending request to delete csm manage user %s", username)
            response = self.csm_obj.delete_csm_user(username)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(username)
        self.log.info("Step 3: Creating csm monitor users")
        for _ in range(2):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="monitor")
            self.log.info("Verifying if monitor user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'monitor', "User is not created with monitor role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Sending request to delete csm monitor user %s", username)
            response = self.csm_obj.delete_csm_user(username)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(username)
        self.log.info("Step 4: Sending request to delete self admin user")
        response = self.csm_obj.delete_csm_user(CSM_REST_CFG["csm_admin_user"]["username"])
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(resp_error_code), "Error code check failed."
        if CSM_REST_CFG["msg_check"] == "enable":
            assert response.json()["message"] == msg.format("admin"), "Message check failed."
            assert response.json()["message_id"] == resp_msg_id, "Message ID check failed."
        self.log.info("Step 6: Perform GET users operation")
        response = self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True,
            sort_by="role")
        self.log.info("Response : %s", response)
        self.log.info("Verifying response code 200 was returned for get users")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("##### Test completed -  %s #####", test_case_name)
    
    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32182')
    def test_32182(self):
        """
        Test that rest response gives proper code/msg for unavailable search
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: List user for unavailable user")
        user = "dummy_user" + str(int(time.time()))
        response = self.csm_obj.list_csm_users(expect_status_code=200, username=user,
                                                return_actual_response=True)
        if response:
            assert response.status_code == HTTPStatus.OK, "Status code check failed."
            assert len(response.json()['users']) == 0, "Unavailable user listed"
            self.log.info("Unavailable user is not listed")
        else:
            self.log.error("Unexpected response received")
        self.log.info("Verified: List user for unavailable user")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-32183')
    def test_32183(self):
        """
        List users with username and role
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: List existing csm users")
        roles = ['manage', 'monitor', 'admin']
        new_users = [[], [], []]
        existing_users = [[], [], []]
        response = self.csm_obj.list_csm_users(expect_status_code=HTTPStatus.OK,
                                                return_actual_response=True)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK)
        for item in response.json()["users"]:
            existing_users[roles.index(item["role"])].append(item["username"])

        self.log.info("Step 2: Create csm users")
        for _ in range(10):
            self.log.info("Creating csm user")
            role = roles[random.randrange(0, 3)]
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role=role)
            self.log.info("Verifying if user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            new_users[roles.index(role)].append(response.json()["username"])
            self.created_users.append(response.json()["username"])

        self.log.info("Step 3: List users with roles and cross check")
        for role in roles:
            response = self.csm_obj.list_csm_users(expect_status_code=HTTPStatus.OK, role=role,
                                                    return_actual_response=True)
            assert len(response.json()["users"]) == len(existing_users[roles.index(role)]) + \
                   len(new_users[roles.index(role)]), "users count not matching in list users"
            for item in response.json()["users"]:
                if item["username"] not in existing_users[roles.index(role)] and \
                        (item["username"] not in new_users[roles.index(role)]):
                    assert False, "Listed user name is not present"
        self.log.info("Verified: List users with roles and cross check")

        self.log.info("Step 4: List users with username and it should give correct data")
        for role in roles:
            user_list = new_users[roles.index(role)]
            for user in user_list:
                response = self.csm_obj.list_csm_users(expect_status_code=HTTPStatus.OK,
                                                        username=user, return_actual_response=True)
                if response:
                    assert response.status_code == HTTPStatus.OK, "Status code check failed."
                    assert len(response.json()['users']) == 1, "User not listed"
                    self.log.info("User is listed")
                else:
                    self.log.error("Unexpected response received")
        self.log.info("Verified: List users with username and it should give correct data")

        self.log.info("Step 5: List users with username & role and it should give correct data")
        for role in roles:
            user_list = new_users[roles.index(role)]
            for user in user_list:
                response = self.csm_obj.list_csm_users(expect_status_code=HTTPStatus.OK,
                                                        username=user, role=role,
                                                        return_actual_response=True)
                if response:
                    assert response.status_code == HTTPStatus.OK, "Status code check failed."
                    assert len(response.json()['users']) == 1, \
                        "User not listed with username & role"
                    assert response.json()["users"][0]["username"] == user, "Different user listed"
                    self.log.info("User is listed")
                else:
                    self.log.error("Unexpected response received")
        self.log.info("Verified: List users with username & role and it should give correct data")

        self.log.info("Step 6: List users with substring of username")
        e_users = [usr for sub in existing_users for usr in sub]
        n_users = [usr for sub in new_users for usr in sub]
        for role in roles:
            user_list = new_users[roles.index(role)]
            for user in user_list:
                if len(user) > 3:
                    user_sub_string = [user[:3], user[-3:]]
                    for uname in user_sub_string:
                        response = self.csm_obj.list_csm_users(expect_status_code=HTTPStatus.OK,
                                                                username=uname,
                                                                return_actual_response=True)
                        for item in response.json()["users"]:
                            assert uname in item["username"], "sub string not present in username"
                        for item in response.json()["users"]:
                            if item["username"] not in e_users and \
                                    (item["username"] not in n_users):
                                assert False, "Listed user name is not present"
        self.log.info("Verified: List users with substring of username")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32181')
    def test_32181(self):
        """
        Test that any user with any role should be able to delete themselves, change their own password
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_32181"]
        passwd = test_cfg["current_password"]
        new_password = CSM_REST_CFG["csm_user_manage"]["password"]
        self.log.info("Step 1: Creating csm admin users")
        for _ in range(4):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="admin",user_password=passwd)
            self.log.info("Verifying if admin user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'admin', "User is not created with admin role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Get header")
            header = self.csm_obj.get_headers(username, passwd)
            self.log.info("Verify password change for users")
            response = self.csm_obj.edit_user_with_custom_login(user=username,
                                                   password=new_password,
                                                   current_password=passwd,header=header)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=username, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
            self.log.info("Sending request to delete csm admin user %s", username)
            response = self.csm_obj.delete_user_with_header(username,header)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(username)
        self.log.info("Step 2: Creating csm manage users")
        for _ in range(4):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="manage",user_password=passwd)
            self.log.info("Verifying if manage user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'manage', "User is not created with manage role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Get header")
            header = self.csm_obj.get_headers(username, passwd)
            self.log.info("Verify password change for users")
            response = self.csm_obj.edit_user_with_custom_login(user=username,
                                                   password=new_password,
                                                   current_password=passwd,header=header)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=username, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
            self.log.info("Sending request to delete csm manage user %s", username)
            response = self.csm_obj.delete_user_with_header(username,header)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(username)
        self.log.info("Step 3: Creating csm monitor users")
        for _ in range(4):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="monitor",user_password=passwd)
            self.log.info("Verifying if monitor user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'monitor', "User is not created with monitor role"
            self.log.info("Verified User %s got created successfully", username)
            self.log.info("Get header")
            header = self.csm_obj.get_headers(username, passwd)
            self.log.info("Verify password change for users")
            response = self.csm_obj.edit_user_with_custom_login(user=username,
                                                   password=new_password,
                                                   current_password=passwd,header=header)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=username, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
            self.log.info("Sending request to delete csm monitor user %s", username)
            response = self.csm_obj.delete_user_with_header(username,header)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(username)
            self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest     
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-32242')
    def test_32242(self):
        """
        Create users with same email
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating a valid csm user")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage", user_email="manage_user@seagate.com")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username1 = response.json()["username"]
        self.created_users.append(username1)
        self.log.info("Step 2: Creating a valid csm user with existing user email")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage", user_email="manage_user@seagate.com")
        assert response.status_code == HTTPStatus.CREATED.value, "Status code check failed"
        username2 = response.json()["username"]
        self.created_users.append(username2)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-32241')
    def test_32241(self):
        """
        Update users email to another users existing email
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating a valid csm user")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage", user_email="manage_user@seagate.com")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username1 = response.json()["username"]
        self.created_users.append(username1)
        self.log.info("Step 2: Creating a valid csm user with unique email")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage", user_email="manage_user1@seagate.com")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username2 = response.json()["username"]
        self.created_users.append(username2)
        response = self.csm_obj.edit_csm_user(user=username2,
                                               email="manage_user@seagate.com")
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Verified: Email update working for existing email")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-32616')
    def test_32616(self):
        """
        Login and update using deleted user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating a valid csm user: manage")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username1 = response.json()["username"]
        self.created_users.append(username1)
        self.log.info("Step 2: Creating a valid csm user: admin")
        user_pass = "Testadmin@123"
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="admin", user_password=user_pass)
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username2 = response.json()["username"]
        self.created_users.append(username2)
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_obj.get_headers(username2, user_pass)
        self.log.info("Step 4: Sending request to delete csm user %s", username2)
        response = self.csm_obj.delete_csm_user(username2)
        assert response.status_code == HTTPStatus.OK, "User Deleted Successfully."
        self.log.info("Removing user from list if delete is successful")
        self.created_users.remove(username2)
        self.log.info("Step 5: Try login for deleted user")
        response = self.csm_obj.custom_rest_login(username=username2, password=user_pass)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, "Login for deleted user worked"
        self.log.info("Verified: Login with deleted user not working")
        self.log.info("Step 6: Verify user role can be changed with deleted user header")
        response = self.csm_obj.edit_user_with_custom_login(user=username1, role='monitor',
                                                             header=header)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, "Update with deleted user worked"
        self.log.info("Verified: Update with deleted user not working")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32174')
    def test_32174(self):
        """
        Test that manage user should be able to reset password of users with manage 
        and monitor roles , S3 Account user and self password also
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_32174"]
        new_password = test_cfg["new_password"]
        current_password = CSM_REST_CFG["csm_user_manage"]["password"]
        self.log.info("Creating a csm manage user and fetch its password for further use")
        response = self.csm_obj.create_csm_user(user_type="valid", 
                                                 user_role="manage", user_password=current_password)
        self.log.info("Verifying if manage user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        self.created_users.append(username)
        self.log.info("users list is %s", self.created_users)
        assert response.json()['role'] == 'manage', "User is not created with manage role"
        self.log.info("Verified User %s got created successfully", username)
        response = self.csm_obj.custom_rest_login(username=username, password=current_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        new_user = {}
        new_user['username'] = username
        new_user['password'] = current_password
        self.log.info("Step 1: Creating 2 other csm manage users")
        for _ in range(2):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="manage",
                                                     user_password=current_password)
            self.log.info("Verifying if manage user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'manage', "User is not created with manage role"
            self.log.info("Verified User %s got created successfully", username)

        self.log.info("Step 2: Creating 3 csm monitor users")
        for _ in range(3):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="monitor",
                                                     user_password=current_password)
            self.log.info("Verifying if monitor user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.created_users.append(username)
            self.log.info("users list is %s", self.created_users)
            assert response.json()['role'] == 'monitor', "User is not created with monitor role"
            self.log.info("Verified User %s got created successfully", username)

        self.log.info("Step 3: Creating 3 s3 account users")
        for _ in range(3):
            response = self.csm_obj.create_s3_account(user_type="valid")
            self.log.info("Verifying if s3 user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST, "Account creation successful."
            username = response.json()["account_name"]
            self.created_s3_users.append(username)
            self.log.info("users list is %s", self.created_users)
            self.log.info("Verified User %s got created successfully", username)

        self.log.info("Step 4: Login with first manage user and change password for second")
        response = self.csm_obj.edit_csm_user(login_as=new_user,
                                               user=self.created_users[1],
                                               password=new_password,
                                               current_password=current_password)
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        response = self.csm_obj.custom_rest_login(username=self.created_users[1], password=new_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 5: Login with first manage user and change password for third")
        response = self.csm_obj.edit_csm_user(login_as=new_user,
                                               user=self.created_users[2],
                                               password=new_password,
                                               current_password=current_password)
        assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        response = self.csm_obj.custom_rest_login(username=self.created_users[2], password=new_password)
        self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 6: Login with first manage user and change password for all monitor users")
        for usr in self.created_users[2:6]:
            response = self.csm_obj.edit_csm_user(login_as=new_user,
                                                   user=usr,
                                                   password=new_password,
                                                   current_password=current_password)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=usr, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 7: Login with first manage user and change password for all s3 account users")
        payload = {"password": new_password, "current_password": current_password}
        for usr in self.created_s3_users:
            response = self.csm_obj.edit_s3_account(
                username=usr,
                payload=json.dumps(payload),
                login_as=new_user)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32178')
    def test_32178(self):
        """
        Admin user should able to reset other users role ,email and password
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        admin_usr = manage_usr = monitor_usr = []
        test_cfg = self.csm_conf["test_32178"]
        password = test_cfg["current_password"]
        new_password = CSM_REST_CFG["csm_user_manage"]["password"]
        self.log.info("Step 1: Creating 5 admin users")
        for _ in range(5):
            response = self.csm_obj.create_csm_user(user_role="admin",
                                                     user_type="valid")
            self.log.info("Verifying if users was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            admin_usr.append(username)
            self.created_users.append(username)
            self.log.info("Verified User %s got created successfully", username)

        self.log.info("Step 2: Creating 10 manage users")
        for _ in range(10):
            response = self.csm_obj.create_csm_user(user_role="manage",
                                                     user_type="valid")
            self.log.info("Verifying if users was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            manage_usr.append(username)
            self.created_users.append(username)
            self.log.info("Verified User %s got created successfully", username)

        self.log.info("Step 3: Creating 10 monitor users")
        for _ in range(10):
            response = self.csm_obj.create_csm_user(user_role="monitor",
                                                     user_type="valid")
            self.log.info("Verifying if users was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            monitor_usr.append(username)
            self.created_users.append(username)
            self.log.info("Verified User %s got created successfully", username)

        self.log.info("Step 4: change role of first 5 manage users to monitor")
        for usr in manage_usr[0:6]:
            self.log.info("Editing role for %s manage user", usr)
            response = self.csm_obj.edit_csm_user(user=usr,
                                                   role="monitor")
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 5: change role of first 5 monitor users to manage")
        for usr in monitor_usr[0:6]:
            self.log.info("Editing role for %s monitor user", usr)
            response = self.csm_obj.edit_csm_user(user=usr,
                                                   role="manage")
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 6: change role of first 2 admin users to manage")
        self.log.info("Editing role for %s admin user", usr)
        for usr in admin_usr[0:3]:
            response = self.csm_obj.edit_csm_user(user=usr,
                                                   role="manage")
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
        self.log.info("Step 7: Change passwords and emails of all 10 monitor users and try login")
        for usr in manage_usr:
            self.log.info("Editing password and email for %s manage user", usr)
            response = self.csm_obj.edit_csm_user(user=usr, email=test_cfg["email_id"],
                                                   password=new_password, current_password=password)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=usr, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 8: Change passwords and emails of all 10 manage users and try login")
        for usr in monitor_usr:
            self.log.info("Editing password and email for %s monitor user", usr)
            response = self.csm_obj.edit_csm_user(user=usr, email=test_cfg["email_id"],
                                                   password=new_password, current_password=password)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=usr, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("Step 9: Change passwords and emails of all 3 admin users and try login")
        for usr in admin_usr[2:6]:
            self.log.info("Editing password and email for %s admin user", usr)
            response = self.csm_obj.edit_csm_user(user=usr, email=test_cfg["email_id"],
                                                   password=new_password, current_password=password)
            assert response.status_code == const.SUCCESS_STATUS, "Status code check failed."
            response = self.csm_obj.custom_rest_login(username=usr, password=new_password)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-32177')
    def test_32177(self):
        """
        Verify the limit to create 100 users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        roles = ['monitor', 'admin', 'manage']
        new_users = [[], [], []]
        self.log.info("Deleting all csm users except predefined ones...")
        self.config.delete_csm_users()
        deleted_users = []
        self.log.info("Users except pre-defined ones deleted.")
        self.log.info("Step 1: Listing all csm users")
        response = self.csm_obj.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        user_data = response.json()
        self.log.info("List user response : %s", user_data)
        existing_user = len(user_data['users'])
        self.log.info("Existing CSM users count: %s", existing_user)
        self.log.info("Max csm users : %s", const.MAX_CSM_USERS)
        user_creation_count = const.MAX_CSM_USERS - existing_user
        self.log.info("New users to create: %s", user_creation_count)
        self.log.info("Step 2: Creating users with random role")
        for count in range(user_creation_count):
            self.log.info("Creating csm user %s", count)
            role = roles[random.randrange(0, 3)]
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role=role)
            self.log.info("Verifying if user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            self.created_users.append(response.json()["username"])

        self.log.info("Deleting all random csm users except predefined ones...")
        for usr in self.created_users:
            response = self.csm_obj.delete_csm_user(usr)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            deleted_users.append(usr)
        for usr in deleted_users:
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(usr)
        self.log.info("Users except pre-defined ones deleted.")
        self.log.info("Step 3: Creating %s admin users and deleting it "
                      "except last admin", user_creation_count)
        for _ in range(user_creation_count):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="admin")
            self.log.info("Verifying if admin user was created successfully")
            assert response.status_code == HTTPStatus.CREATED.value
            username = response.json()["username"]
            self.log.info("Verified User %s got created successfully", username)
            self.created_users.append(response.json()["username"])

        self.log.info("Deleting all csm admin users except predefined ones...")
        deleted_users = []
        for usr in self.created_users:
            response = self.csm_obj.delete_csm_user(usr)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            deleted_users.append(usr)
        for usr in deleted_users:
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(usr)
        self.log.info("Users except pre-defined ones deleted.")
        self.log.info("Step 4: Creating %s manage users and deleting it except "
                      "default manage user", user_creation_count)
        for _ in range(user_creation_count):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="manage")
            self.log.info("Verifying if manage user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.log.info("Verified User %s got created successfully", username)
            self.created_users.append(response.json()["username"])

        deleted_users = []
        self.log.info("Deleting all csm manage users except predefined ones...")
        for usr in self.created_users:
            response = self.csm_obj.delete_csm_user(usr)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            deleted_users.append(usr)
        for usr in deleted_users:
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(usr)
        self.log.info("Users except pre-defined ones deleted.")
        self.log.info("Step 5: Creating %s monitor users and deleting it "
                      "except default monitor user", user_creation_count)
        for _ in range(user_creation_count):
            response = self.csm_obj.create_csm_user(user_type="valid",
                                                     user_role="monitor")
            self.log.info("Verifying if monitor user was created successfully")
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            self.log.info("Verified User %s got created successfully", username)
            self.created_users.append(response.json()["username"])

        deleted_users = []
        self.log.info("Deleting all csm monitor users except predefined ones...")
        for usr in self.created_users:
            self.log.info("Deleting user %s", usr)
            response = self.csm_obj.delete_csm_user(usr)
            assert response.status_code == HTTPStatus.OK, "User Not Deleted Successfully."
            deleted_users.append(usr)
        for usr in deleted_users:
            self.log.info("Removing user from list if delete is successful")
            self.created_users.remove(usr)
        self.log.info("Users except pre-defined ones deleted.")
        self.log.info("##### Test completed -  %s #####", test_case_name)
