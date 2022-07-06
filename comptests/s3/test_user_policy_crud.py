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
# pylint: disable=E0401
"""All IAM users test  Module."""
import json
import asyncio
import time
import logging
from http import HTTPStatus
import pytest

from libs.s3.s3_iam_rest_rgw import RestApiRgw
from commons import cortxlogging

class TestRgwPolicyCrud:
    """
    REST API Test cases for IAM users.
    IAM CRUD operations.
    """
    @classmethod
    def setup_class(cls):
        """Function will be invoked before running each test case."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class ")
        cls.obj = RestApiRgw()
        cls.user_name_prefix = "user"
        cls.access_key_prefix = "access_key"
        cls.secret_key_prefix = "secret_key"
        cls.created_users = []
        cls.tenant = 'Group1'

    def teardown_method(self):
        """
        Teardown for deleting resources like users,object and bucket created as part of testcases
        """
        self.log.info("[STARTED] ######### Teardown #########")
        self.log.info("Deleting all users created as part of test")
        delete_failed = []
        delete_success = []
        self.log.debug("created_users list : %s",self.created_users)
        for usr in self.created_users:
            self.log.info("Sending request to delete user %s", usr)
            loop = asyncio.get_event_loop()
            status = loop.run_until_complete(self.obj.delete_user(usr))
            if status != HTTPStatus.OK:
                delete_failed.append(usr)
            else:
                delete_success.append(usr)
        for usr in delete_success:
            self.created_users.remove(usr)
        self.log.info("User delete success list %s", delete_success)
        self.log.info("User delete failed list %s", delete_failed)

    def create_user(self,user_params):
        """ Create user function. """
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        return status, user_info

    def put_policy(self,user_params):
        """ Apply Policy to the user function. """
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.put_user_policy(user_params))
        return status

    def delete_policy(self,user_params):
        """ Delete Policy to the user function. """
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.delete_user_policy(user_params))
        return status

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41407')
    def test_41407(self):
        """ Test to DeleteUserPolicy to the Valid user.
        Steps:
        - Create user
        - Apply Policy
        - Verify Delete Policy
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Test to DeleteUserPolicy to the user.")
        self.log.info("Step1 : Creating IAM user.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params1 = {
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info("Step 2: Creating a new IAM user with name %s", str(user_name))
        status = self.create_user(user_params1)
        self.log.info("Step 3: Verifying that new IAM user is created successfully")
        assert status[0] == HTTPStatus.OK, "Not able to create user. Test Failed"
        self.log.info("Step 4: IAM user is created successfully")
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::test1/*"
                }
            ]
        }
        self.log.info("Step 5: Applying user policy to the user")
        self.log.info(policy)
        policy_document = json.dumps(policy)
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'PolicyDocument' : policy_document,
            'Action' : 'PutUserPolicy',
            'format' : 'json'
        }
        status = self.put_policy(user_params2)
        self.log.info("Step 6: verifying Applied user policy to the user")
        assert status[0] == HTTPStatus.OK, "Not able to apply policy"
        self.log.info("Step 7:  Applied user policy Successfully")
        user_params3 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        status = self.delete_policy(user_params3)
        assert status[0] == HTTPStatus.OK, "Not able to delete policy"
        user_params4 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'GetUserPolicy',
            'format' : 'json'
        }
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.get_user_policy(user_params4))
        assert status[0] == HTTPStatus.NOT_FOUND
        self.log.info("Step 8: IAM policy deleted successfully")
        self.created_users.append(user_params1)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41408')
    def test_41408(self):
        """ Test to DeleteUserPolicy to the InValid user.
        - Verify delete policy where user is not Created
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Test to DeleteUserPolicy for invalid user.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::test1/*"
                }
            ]
        }
        self.log.info("Step 1: Deleting user policy to invalid user")
        self.log.info(policy_document)
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        status = self.delete_policy(user_params2)
        self.log.info("Step 2: verifying delete user policy to invalid user")
        assert status[0] == HTTPStatus.NOT_FOUND, "User policy applied"
        self.log.info("END: Test to verify delete policy for invalid user")

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41409')
    def test_41409(self):
        """Test to delete policy for a tenant user
        Steps:
        - Create Tenant user
        - Apply Policy
        - Verify Delete policy for tenant user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create tenant user")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'tenant' : self.tenant,
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating tenant user.")
        status = self.create_user(user_params)
        self.log.info("Step 3: Verifying that tenant IAM user is created successfully")
        assert status[0] == HTTPStatus.OK, "Not able to create user. Test Failed"
        self.log.info("Step 4: Tenant IAM user is created successfully")
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::test1/*"
                }
            ]
        }
        self.log.info("Step 5: Applying user policy to the tenant user")
        self.log.info(policy)
        policy_document = json.dumps(policy)
        user_params2 = {
            'uid' : self.tenant +'$'+user_name,
            'UserName' : self.tenant +'$'+user_name,
            'PolicyName' : 'Policy1',
            'PolicyDocument' : policy_document,
            'Action' : 'PutUserPolicy',
            'format' : 'json'
        }
        status = self.put_policy(user_params2)
        self.log.info("Step 6: verifying Applied user policy to the tenant user")
        assert status[0] == HTTPStatus.OK, "Not able to put user policy"
        self.log.info("Step 7:  Applied user policy Successfully")
        self.log.info("Step 8:  Deleting user policy for tenant user")
        user_params3 = {
            'UserName' : self.tenant +'$'+user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        status = self.delete_policy(user_params3)
        self.log.info(status)
        assert status[0] == HTTPStatus.OK, "Not able to delete policy"
        user_params4 = {
            'UserName' : self.tenant +'$'+user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'GetUserPolicy',
            'format' : 'json'
        }
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.get_user_policy(user_params4))
        assert status[0] == HTTPStatus.NOT_FOUND
        self.log.info("Step 9: Deleted Applied user policy to the tenant user")
        self.created_users.append(user_params2)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41411')
    def test_41411(self):
        """Test to delete policy which does not exist
        Steps:
        - Create User
        - Verify Delete policy which is not applied
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create IAM user")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating IAM user.")
        status = self.create_user(user_params)
        self.log.info("Step 3: Verifying that IAM user is created successfully")
        assert status[0] == HTTPStatus.OK, "Not able to create user. Test Failed"
        self.log.info("Step 4: IAM user is created successfully")
        self.log.info("Step 5:  Deleting user policy for with invalid policy name")
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        self.log.info("Step 6:  Deleting user policy for with invalid policy name")
        status = self.delete_policy(user_params2)
        assert status[0] == HTTPStatus.NOT_FOUND, "User policy deleted"
        self.log.info("Step 7: Verified test to remove invalid policy name")
        self.log.info("END : test to validate delete invalid policy")
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41414')
    def test_41414(self):
        """Test to delete policy by using user Access key and secret key
        Steps:
        - Create user
        - Apply policy
        - Using user access key and secret key to delete policy
        - Verify delete policy
        """
        self.log.info("Step 1: Create IAM user")
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating IAM user.")
        status, user_info = self.create_user(user_params)
        access_key = user_info['keys'][0]['access_key']
        secret_key = user_info['keys'][0]['secret_key']
        self.log.info("Step 3: IAM user is created successfully")
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "iam:DeleteUserPolicy",
                    "Resource": "arn:aws:iam:::user/"+f"{user_name}"
                },
                {
                    "Effect": "Allow",
                    "Action": "iam:GetUserPolicy",
                    "Resource": "arn:aws:iam:::user/"+f"{user_name}"
                }
            ]
        }
        self.log.info(
            "Step 4: Applying user policy to the user")
        self.log.info(policy)
        policy_document = json.dumps(policy)
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'PolicyDocument' : policy_document,
            'Action' : 'PutUserPolicy',
            'format' : 'json'
        }
        status = self.put_policy(user_params2)
        self.log.info("Step 5: Successfully applied policy to the user")
        self.log.info("Step 6: Deleting Policy by using user Access key and Secret key")
        loop = asyncio.get_event_loop()
        user_params3 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        self.log.info("Step 7: Deleting Policy by using user Access key and Secret key")
        status = loop.run_until_complete(
            self.obj.delete_user_policy(user_params3, access_key, secret_key))
        assert status[0] == HTTPStatus.OK, "Not able to delete policy"
        self.log.info("Step 8: Successfully delete policy by self")
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)
        self.log.info(
            "END : test to validate delete policy by using user Access key and secret key")

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41564')
    def test_41564(self):
        """Test to delete policy by the user without having caps
        STeps:
        - Create User
        - Apply policy
        - Delete policy by using user Access key and Secret key
        - Verify delete policy
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create IAM user")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating IAM user.")
        status, user_info = self.create_user(user_params)
        access_key = user_info['keys'][0]['access_key']
        secret_key = user_info['keys'][0]['secret_key']
        self.log.info(
            "Step 3: IAM user is created successfully")
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::testbucket/*"
                }
            ]
        }
        self.log.info(
            "Step 4: Applying user policy to the user")
        self.log.info(policy_document)
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'PolicyDocument' : policy_document,
            'Action' : 'PutUserPolicy',
            'format' : 'json'
        }
        status = self.put_policy(user_params2)
        self.log.info("Step 5: Successfully Applied user policy")
        loop = asyncio.get_event_loop()
        user_params3 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        status = loop.run_until_complete(
            self.obj.delete_user_policy(user_params3, access_key, secret_key))
        assert status[0] == HTTPStatus.FORBIDDEN, "Able to delete user policy"
        self.log.info("Step 6: Validated the deletion of policy by self")
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)
        self.log.info("END : Test to validate delete policy without caps")
