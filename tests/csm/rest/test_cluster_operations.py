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
"""Tests various csm related operation on Cluster user using REST API
"""
import logging
import time
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
        cls.csm_cluster.pull_provisioner()
        cls.csm_cluster.trigger_prov_command('reimage')

    def teardown_method(self):
        """Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        self.csm_cluster.trigger_prov_command('destroy')
        self.log.info("Teardown ended")

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
        self.csm_cluster.trigger_prov_command('deploy')
        self.csm_cluster.apply_csm_service()
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
        self.csm_cluster.modify_config_file('endpoints', 'http')
        self.csm_cluster.trigger_prov_command('deploy')
        self.csm_cluster.apply_csm_service()
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
        self.csm_cluster.trigger_destroy()
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
        self.log.info("Starting deployment with invalid username")
        self.csm_cluster.modify_config_file('mgmt_admin', 'abc')
        self.csm_cluster.trigger_prov_command('deploy')
        time.sleep(120)
        res = self.csm_cluster.get_pod_status()
        assert_utils.assert_false(res, "Control node is successfully created")
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
        self.log.info("Starting deployment with invalid password")
        self.csm_cluster.modify_secrets_file('123')
        self.csm_cluster.trigger_prov_command('deploy')
        time.sleep(120)
        res = self.csm_cluster.get_pod_status()
        assert_utils.assert_false(res, "Control node is successfully created")
        self.log.info("##### Test completed -  %s #####", test_case_name)
