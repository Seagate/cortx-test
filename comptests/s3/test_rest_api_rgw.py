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

"""All IAM users test  Module."""
import asyncio
import time
import logging
import pytest

from libs.s3.s3_iam_rest_rgw import RestApiRgw

class TestRestApiRgw:
    """
    REST API Test cases for IAM users.
    IAM CRUD operations.
    """
    # no blank line allowed here
    @classmethod
    def setup_class(cls):
        """Function will be invoked before running each test case."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class ")
        cls.obj = RestApiRgw()
        cls.user_name_prefix = "user"
        cls.email_id = "{}@seagate.com"

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36622')
    def test_user_create_36622(self):
        """Create new IAM user."""
        self.log.info("START: Test create new IAM user.")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'display-name': user_name,
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        print(user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        assert status == 200
        self.log.info("END: Tested create new IAM user.")
        self.log.info(
            "Step 4: Deleting a IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status , user_info = loop.run_until_complete(self.obj.delete_user(user_params))
        self.log.info(
            "Step 5: Verifying that new IAM user is Deleted successfully")
        assert status == 200
        self.log.info(
            "END: Deleted created user : %s", user_name)
       
    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36630')
    def test_user_create_36630(self):
        """Create new IAM user."""
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
        print(user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        assert status == 200
        self.log.info("END: Tested create new IAM user.")
        self.log.info(
            "Step 3: Deleting a IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status , user_info = loop.run_until_complete(self.obj.delete_user(user_params))
        self.log.info(
            "Step 4: Verifying that new IAM user is Deleted successfully")
        assert status == 200
        self.log.info(
            "END: Deleted created user : %s", user_name) 

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36632')
    def test_user_create_36632(self):
        """Create new IAM user."""
        self.log.info("START: Test create iam user specifying just uid .")
        user_name = f"{self.user_name_prefix}{str(time.perf_counter_ns()).replace('.', '_')}"
        user_params = {
            'uid' : user_name
         }
        self.log.info(
            "Step 1: Creating a new IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        print(user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user creation get failed when only uid is specified")
        assert status == 400
        self.log.info("END: Test create iam user specifying just uid .")

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36633')
    def test_user_create_36633(self):
        """Create new IAM user."""
        self.log.info("START: Test create using uid which already exist.")
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
        print(user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        assert status == 200
        self.log.info(
            "Step 3: Creating another IAM user with same name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params))
        print(user_info)
        assert status == 409
        self.log.info("END: Test create using uid which already exist.")
        self.log.info(
            "Step 4: Deleting a IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status , user_info = loop.run_until_complete(self.obj.delete_user(user_params))
        self.log.info(
            "Step 4: Verifying that new IAM user is Deleted successfully")
        assert status == 200
        self.log.info(
            "END: Deleted created user : %s", user_name)

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36636')
    def test_user_create_36636(self):
        """Create new IAM user."""
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
        print(user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        assert status == 200
        self.log.info(
            "Step 3: Creating another IAM user with same display name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status, user_info = loop.run_until_complete(self.obj.create_user(user_params2))
        print(user_info)
        self.log.info(
            "Step 4: Verifying that new IAM user is created successfully")
        assert status == 200
        self.log.info("END: Test create using uid which already exist.")
        self.log.info(
            "Step 5: Deleting a IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status , user_info = loop.run_until_complete(self.obj.delete_user(user_params))
        self.log.info(
            "Step 6: Verifying that new IAM user is Deleted successfully")
        assert status == 200
        self.log.info(
            "Deleted created user : %s", user_name)
        self.log.info(
            "Step 7: Deleting a IAM user with name %s", str(user_name2))
        loop = asyncio.get_event_loop()
        status , user_info = loop.run_until_complete(self.obj.delete_user(user_params2))
        self.log.info(
            "Step 8: Verifying that new IAM user is Deleted successfully")
        assert status == 200
        self.log.info(
            "END: Deleted created user : %s", user_name2)


