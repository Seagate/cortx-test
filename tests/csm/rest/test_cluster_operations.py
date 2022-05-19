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
"""Tests various csm related operation on Cluster user using REST API
"""
import logging
from http import HTTPStatus
import pytest

from commons import cortxlogging
from commons.utils import assert_utils
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_cluster import RestCsmCluster
from libs.csm.rest.csm_rest_csmuser import RestCsmUser


class TestCluster():
    """REST API Test cases for CSM related Cluster operations
    """

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.config = CSMConfigsCheck()
        cls.csm_cluster = RestCsmCluster()
        cls.csm_user = RestCsmUser()
        cls.csm_cluster.recover_files(False)

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.
        """
        cls.log.info("Teardown started")
        cls.csm_cluster.destroy_cluster()
        cls.csm_cluster.recover_files(True)
        cls.csm_cluster.install_prerequisites()
        cls.csm_cluster.deploy_cluster()
        cls.log.info("Teardown ended")

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28504')
    def test_28504(self):
        """
        Test secure csm login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Destroying existing cluster")
        self.csm_cluster.destroy_cluster()
        self.log.info("Modify endpoint to https")
        self.csm_cluster.modify_config_template('endpoints', 'https')
        self.log.info("Deploy cluster")
        self.csm_cluster.install_prerequisites()
        self.csm_cluster.deploy_cluster()
        username = self.csm_user.config["csm_admin_user"]["username"]
        password = self.csm_user.config["csm_admin_user"]["password"]
        self.log.info("Verifying login with secure mode")
        config_params = {'secure': True}
        response = self.csm_user.custom_rest_login(username, password, "username", "password",
                                                   True, config_params)
        self.log.info("Expected Response: %s", HTTPStatus.OK)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK)
        self.log.info("Verified login with secure mode")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28507')
    def test_28507(self):
        """
        Test unsecure csm login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Destroying existing cluster")
        self.csm_cluster.destroy_cluster()
        self.log.info("Modify endpoint to http")
        self.csm_cluster.modify_config_template('endpoints', 'http')
        self.log.info("Deploy cluster")
        self.csm_cluster.install_prerequisites()
        self.csm_cluster.deploy_cluster()
        username = self.csm_user.config["csm_admin_user"]["username"]
        password = self.csm_user.config["csm_admin_user"]["password"]
        self.log.info("Verifying login with unsecure mode")
        config_params = {'secure': False}
        response = self.csm_user.custom_rest_login(username, password, "username", "password",
                                                   True, config_params)
        self.log.info("Expected Response: %s", HTTPStatus.OK)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK)
        self.log.info("Verified login with unsecure mode")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28520')
    def test_28520(self):
        """
        Invalid admin username while deployment
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Destroying existing cluster")
        self.csm_cluster.destroy_cluster()
        self.log.info("Starting deployment with invalid username")
        self.csm_cluster.modify_config_template('mgmt_admin', 'abc')
        self.csm_cluster.install_prerequisites()
        self.csm_cluster.deploy_cluster()
        res = self.csm_cluster.get_pod_status_value('control')
        assert res, "Control pod with Error state not found"
        self.log.info("Control pod with Error state found")
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-28521')
    def test_28521(self):
        """
        Invalid admin password while deployment
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Destroying existing cluster")
        self.csm_cluster.destroy_cluster()
        self.log.info("Starting deployment with invalid password")
        self.csm_cluster.modify_solution_file('csm_mgmt_admin_secret', '123')
        self.csm_cluster.install_prerequisites()
        self.csm_cluster.deploy_cluster()
        res = self.csm_cluster.get_pod_status_value('control')
        assert res, "Control pod with Error state not found"
        self.log.info("Control pod with Error state found")
        self.log.info("##### Test completed -  %s #####", test_case_name)
