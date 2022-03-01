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

    @pytest.mark.skip("Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
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

    @pytest.mark.skip("Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
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

    @pytest.mark.skip(reason="Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
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

    @pytest.mark.skip(reason="Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
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

    @pytest.mark.skip("Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
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
