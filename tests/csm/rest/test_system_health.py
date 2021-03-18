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
"""Tests system health reported using REST API
"""
import logging
import pytest
from libs.csm.rest.csm_rest_system_health import SystemHealth
from commons import cortxlogging
from commons.constants import Rest as const

class TestSystemHealth():
    """System Health Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups started......")
        cls.system_health = SystemHealth()
        cls.log.info("Initiating test setup completed ...")
        
    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-12786')
    def test_6813(self):
        """Test that GET request for API '/api/v1/system/health/summary '
        returns 200 response with overall health status of the system.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        expected_response = const.SUCCESS_STATUS
        result = self.system_health.verify_health_summary(expected_response)
        assert result
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17867')
    def test_6819(self):
        """
        Test that GET request for API '/api/v1/system/health/node?node_id=<node_id>'
        for node health summary returns 200 response with overall health summary
        for the specific node or enclosure
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        for node in ["storage", "node-1", "node-2"]:
            expected_response = const.SUCCESS_STATUS
            result = self.system_health.verify_health_node(
                expected_response, node=node)
            assert result
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Known issue EOS-15448 ")
    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17868')
    def test_6820(self):
        """
        Test that GET request for API '/api/v1/system/health/node?'
        for node health summary returns 200 response with overall health summary
        for entire system in case user does not provide specific node or enclosure id.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        expected_response = const.SUCCESS_STATUS
        result = self.system_health.verify_health_node(
            expected_response, node="")
        assert result
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Known issue EOS-15448 ")
    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17869')
    def test_6826(self):
        """
        Test that GET request for API '/api/v1/system/health/view?node_id=<node_id>'
        for node health view returns 200 response with overall health summary
        and list of alerts for that specific node or enclosure
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        for node in ["storage", "node-1", "node-2"]:
            expected_response = const.SUCCESS_STATUS
            result = self.system_health.verify_health_view(
                expected_response, node=node)
            assert result
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17870')
    def test_6827(self):
        """
        Test that GET request for API '/api/v1/system/health/view?' for node health view
        returns 200 response with overall health summary and list of alerts
        for entire system in case user does not provide specific node or enclosure id.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        expected_response = const.SUCCESS_STATUS
        result = self.system_health.verify_health_view(
            expected_response, node="")
        assert result
        self.log.info("##### Test ended -  %s #####", test_case_name)
