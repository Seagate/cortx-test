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
from http import HTTPStatus
import pytest

from libs.s3.s3_iam_rest_rgw import RestApiRgw

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
        cls.user_name_prefix = "adminuser"
        cls.email_id = "{}@seagate.com"
        cls.created_iam_users = []

    @pytest.mark.api_user_ops
    @pytest.mark.tags('TEST-36622')
    def test_36622(self):
        """Create new IAM user."""
        self.log.info("START: Test create new IAM user.")
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
        self.log.info(user_info)
        self.log.info(
            "Step 2: Verifying that new IAM user is created successfully")
        assert status == HTTPStatus.OK
        self.log.info("END: Tested create new IAM user.")
        self.log.info(
            "Step 4: Deleting a IAM user with name %s", str(user_name))
        loop = asyncio.get_event_loop()
        status ,user_info = loop.run_until_complete(self.obj.delete_user(user_params))
        self.log.info(
            "Step 5: Verifying that new IAM user is Deleted successfully")
        assert status == HTTPStatus.OK
        self.log.info(
            "Step 6: Deleted created user : %s", user_name)
        