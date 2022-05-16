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

class TestRestApiRgw:
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
        cls.email_id = "{}@seagate.com"
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
            try:
                loop = asyncio.get_event_loop()
                status = loop.run_until_complete(self.obj.delete_user(usr))
                if status[0] != HTTPStatus.OK:
                    delete_failed.append(usr)
                else:
                    delete_success.append(usr)
            # pylint: disable=broad-except
            except BaseException as err:
                self.log.warning("Ignoring %s while deleting user: %s", err, usr)
        for usr in delete_success:
            self.created_users.remove(usr)
        self.log.info("User delete success list %s", delete_success)
        self.log.info("User delete failed list %s", delete_failed)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36622')
    def test_user_create_36622(self):
        """Test create iam user specifying uid and display name."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying uid and display name.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36630')
    def test_user_create_36630(self):
        """Test create iam user specifying uid and display name and email."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying uid and display name and email.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36632')
    def test_user_create_36632(self):
        """Test create iam user specifying just uid."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create iam user specifying just uid .")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.BAD_REQUEST, "Able to create user with just uid. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        #self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36633')
    def test_user_create_36633(self):
        """Test create using uid which already exist."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create using uid which already exist.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.CONFLICT , "Didn't get the expected error"
        self.log.info("Create user output: %s",user_info)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36636')
    def test_user_create_36636(self):
        """Test create user using display name which already exist."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user using display name which already exist.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_name2 = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        user_params2 = {
            'display-name': user_name,
            'uid' : user_name2
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same display name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 4: Verifying that new IAM user is created successfully with same display name")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params2))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params2)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36664')
    def test_user_create_36664(self):
        """Test create using email which already exist."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create using email which already exist.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_name2 = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        user_params2 = {
            'display-name': user_name2,
            'email' : email,
            'uid' : user_name2
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info(
            "Step 3: Creating another IAM user with same email %s", str(email))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        assert status == HTTPStatus.CONFLICT , "Didn't get the expected error"
        self.log.info("Create user output: %s",user_info)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36665')
    def test_user_create_36665(self):
        """Test create user with uid containing special characters."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("START: Test create user with uid containing special characters.")
        user_name = '#user##@%@%%@#%^@#%12313223new'
        user_params = {
            'display-name': user_name,
            'uid' : user_name
        }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        assert status == HTTPStatus.OK , "Not able to create user. Test Failed"
        self.log.info("Created user details: %s",user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        status, user_info = loop.run_until_complete(self.obj.get_user_info(user_params))
        assert status == HTTPStatus.OK , "Not able to Get user Info. Test Failed"
        self.log.info("Get user info output: %s",user_info)
        self.created_users.append(user_params)
        self.log.info("END : %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41407')
    def test_41407(self):
        """ Test to DeleteUserPolicy to the Valid user. """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Test to DeleteUserPolicy to the user.")
        self.log.info("Step1 : Creating IAM user.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params1 = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        self.log.info(
            "Step 2: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params1))
        self.log.info(user_info)
        self.log.info(
            "Step 3: Verifying that new IAM user is created successfully")
        assert status == HTTPStatus.OK, "Not able to create user. Test Failed"
        self.log.info(
            "Step 4: IAM user is created successfully")
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
        self.log.info(
            "Step 5: Applying user policy to the user")
        self.log.info(policy)
        policy_document = json.dumps(policy)
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'PolicyDocument' : policy_document,
            'Action' : 'PutUserPolicy',
            'format' : 'json'
        }
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.put_user_policy(user_params2))
        self.log.info(
            "Step 6: verifying Applied user policy to the user")
        assert status[0] == HTTPStatus.OK, "Not able to apply policy"
        self.log.info(
            "Step 7:  Applied user policy Successfully")
        user_params3 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.delete_user_policy(user_params3))
        assert status[0] == HTTPStatus.OK, "Not able to delete policy"
        self.log.info("Step 8: IAM policy deleted successfully")
        self.log.info("Step 9: Deleting created IAM user")
        self.created_users.append(user_params1)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41408')
    def test_41408(self):
        """ Test to DeleteUserPolicy to the InValid user. """
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
        self.log.info(
            "Step 1: Applying user policy to invalid user")
        self.log.info(policy_document)
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'PolicyDocument' : policy_document,
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.delete_user_policy(user_params2))
        self.log.info(
            "Step 2: verifying Applied user policy to invalid user")
        assert status[0] == HTTPStatus.NOT_FOUND, "User policy applied"
        self.log.info("END: Test to verify delete policy for invalid user")

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41409')
    def test_41409(self):
        """Test to delete policy for a tenant user"""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create tenant user")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'tenant' : self.tenant,
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating tenant user.")
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        self.log.info(user_info)
        self.log.info(
            "Step 3: Verifying that tenant IAM user is created successfully")
        assert status == HTTPStatus.OK, "Not able to create user. Test Failed"
        self.log.info(
            "Step 4: Tenant IAM user is created successfully")
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
        self.log.info(
            "Step 5: Applying user policy to the tenant user")
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
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.put_user_policy(user_params2))
        self.log.info(
            "Step 6: verifying Applied user policy to the tenant user")
        assert status[0] == HTTPStatus.OK, "Not able to put user policy"
        self.log.info(
            "Step 7:  Applied user policy Successfully")
        self.log.info(
            "Step 8:  Deleting user policy for tenant user")
        user_params3 = {
            'UserName' : self.tenant +'$'+user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.delete_user_policy(user_params3))
        self.log.info(status)
        assert status[0] == HTTPStatus.OK, "Not able to delete policy"
        self.log.info(
            "Step 9: Deleted Applied user policy to the tenant user")
        self.created_users.append(user_params2)
        self.log.info("END: %s",test_case_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41411')
    def test_41411(self):
        """Test to delete policy which does not exist"""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create IAM user")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating IAM user.")
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        self.log.info(user_info)
        self.log.info(
            "Step 3: Verifying that IAM user is created successfully")
        assert status == HTTPStatus.OK, "Not able to create user. Test Failed"
        self.log.info(
            "Step 4: IAM user is created successfully")
        self.log.info(
            "Step 5:  Deleting user policy for with invalid policy name")
        user_params2 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        self.log.info(
            "Step 6:  Deleting user policy for with invalid policy name")
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.delete_user_policy(user_params2))
        assert status[0] == HTTPStatus.NOT_FOUND, "User policy deleted"
        self.log.info("Step 7: Verified test to remove invalid policy name")
        self.log.info("END : test to validate delete invalid policy")
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)
    # pylint: disable=C0301
    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41414')
    def test_41414(self):
        """Test to delete policy by using user Access key and secret key"""
        self.log.info("Step 1: Create IAM user")
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating IAM user.")
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        self.log.info(user_info)
        access_key = user_info['keys'][0]['access_key']
        secret_key = user_info['keys'][0]['secret_key']
        self.log.info(
            "Step 3: IAM user is created successfully")
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "iam:DeleteUserPolicy",
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
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.put_user_policy(user_params2))
        self.log.info(
            "Step 5: Successfully applied policy to the user")
        self.log.info("Step 6: Deleting Policy by using user Access key and Secret key")
        loop = asyncio.get_event_loop()
        user_params3 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        self.log.info("Step 7: Deleting Policy by using user Access key and Secret key")
        status = loop.run_until_complete(self.obj.delete_policy_with_user_keys(user_params3, access_key, secret_key))
        assert status[0] == HTTPStatus.OK, "Not able to delete policy"
        self.log.info("Step 8: Successfully delete policy by self")
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)
        self.log.info("END : test to validate delete policy by using user Access key and secret key")

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-41564')
    def test_41564(self):
        """Test to delete policy by the user without having caps"""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create IAM user")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        email=f"{user_name}@seagate.com"
        user_params = {
            'display-name': user_name,
            'email' : email,
            'uid' : user_name
        }
        self.log.info("Step 2: Started creating IAM user.")
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        self.log.info(user_info)
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
        loop = asyncio.get_event_loop()
        status = loop.run_until_complete(self.obj.put_user_policy(user_params2))
        self.log.info("Step 5: Successfully Applied user policy")
        loop = asyncio.get_event_loop()
        user_params3 = {
            'UserName' : user_name,
            'PolicyName' : 'Policy1',
            'Action' : 'DeleteUserPolicy',
            'format' : 'json'
        }
        status = loop.run_until_complete(self.obj.delete_policy_with_user_keys(user_params3, access_key, secret_key))
        assert status[0] == HTTPStatus.FORBIDDEN, "Able to delete user policy"
        self.log.info("Step 6: Validated the deletion of policy by self")
        self.created_users.append(user_params)
        self.log.info("END: %s",test_case_name)
        self.log.info("END : Test to validate delete policy without caps")
  