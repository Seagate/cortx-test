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
"""Test CSM resource limits using REST API."""

import logging
import time
from http import HTTPStatus

import pytest

from commons import configmanager
from commons import cortxlogging
from commons.constants import Rest as const  # noqa: N813

from libs.csm.csm_interface import csm_api_factory


class TestResourceLimits():
    """REST API Test cases for CSM resource limits."""

    @classmethod
    def setup_class(cls):
        """Set up operations for test suite set-up."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_resource_limits.yaml")
        cls.created_users = []
        cls.csm_obj = csm_api_factory("rest")
        cls.log.info("Initiating Rest Client ...")

    def teardown_method(self):
        """Teardown for deleting temp csm users."""
        self.log.info("[STARTED] ######### Teardown #########")
        self.log.info("Deleting all csm users except predefined ones...")
        delete_failed = []
        delete_success = []
        if self.created_users:
            time.sleep(3)  # EOS-27030
        for usr in self.created_users:
            self.log.info("Sending request to delete csm user %s", usr)
            try:
                response = self.csm_obj.delete_csm_user(usr)
                if response.status_code != HTTPStatus.OK:
                    delete_failed.append(usr)
                else:
                    delete_success.append(usr)
            except BaseException as any_error:  # pylint: disable=W0703
                msg = f"Ignoring {any_error} while deleting user: {usr}"
                self.log.warning(msg)
        for usr in delete_success:
            self.created_users.remove(usr)
        self.log.info("csm delete success list %s", delete_success)
        self.log.info("csm delete failed list %s", delete_failed)
        assert len(delete_failed) == 0, "Delete failed for users"
        self.log.info("[COMPLETED] ######### Teardown #########")

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-43149")
    def test_43149(self):
        """Test active users quota."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started - %s #####", test_case_name)

        active_users_quota = self.csm_conf["test_43149"]["active_users_quota"]
        tmp_users_password = self.csm_conf["test_43149"]["tmp_users_password"]

        msg = f"Step 1: Create and login {active_users_quota - 1} CSM users"
        self.log.info(msg)
        for _ in range(active_users_quota - 1):
            response = self.csm_obj.create_csm_user(
                user_type="valid", user_role="manage",
                user_password=tmp_users_password)
            assert response.status_code == const.SUCCESS_STATUS_FOR_POST
            username = response.json()["username"]
            user_id = response.json()["id"]
            self.created_users.append(user_id)
            response = self.csm_obj.rest_login(
                login_as={"username": username, "password": tmp_users_password})
            assert response.status_code == const.SUCCESS_STATUS

        msg = "Step 2: Create and login CSM user above active users quota"
        self.log.info(msg)
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage",
            user_password=tmp_users_password)
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        response = self.csm_obj.rest_login(
            login_as={"username": username, "password": tmp_users_password})
        assert response.status_code == const.UNAUTHORIZED

        self.log.info("################Test Passed##################")

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-43150")
    def test_43150(self):
        """Test sessions qouta."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started - %s #####", test_case_name)

        sessions_quota = self.csm_conf["test_43150"]["sessions_quota"]
        tmp_user_password = self.csm_conf["test_43150"]["tmp_user_password"]

        msg = "Step 1: Create CSM user."
        self.log.info(msg)
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage",
            user_password=tmp_user_password)
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        user_id = response.json()["id"]
        self.created_users.append(user_id)
        msg = "Step 2: Fulfil the sessions quota by multiple login."
        self.log.info(msg)
        for _ in range(sessions_quota):
            response = self.csm_obj.rest_login(
                login_as={"username": username, "password": tmp_user_password})
        msg = "Step 3: Try to login above the sessions quota."
        self.log.info(msg)
        response = self.csm_obj.rest_login(
            login_as={"username": username, "password": tmp_user_password})
        assert response.status_code == const.UNAUTHORIZED

        self.log.info("################Test Passed##################")

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-43151")
    def test_43151(self):
        """Test requests qouta."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started - %s #####", test_case_name)

        requests_quota = self.csm_conf["test_43151"]["requests_quota"]
        api_endpoint = self.csm_conf["test_43151"]["api_endpoint"]

        msg = f"Step 1: overflow {api_endpoint} with {requests_quota} requests"
        self.log.info(msg)
        is_overflow = self.csm_obj.flood(api_endpoint, requests_quota)
        assert is_overflow
        self.log.info("################Test Passed##################")
