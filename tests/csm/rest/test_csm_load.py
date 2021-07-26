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
"""Tests for performing load testing using Jmeter"""
import logging
import pytest
from commons import cortxlogging
from libs.jmeter.jmeter_integration import JmeterInt

class TestCsmLoad():
    """Test cases for performing CSM REST API load testing using jmeter"""
    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log.info("[STARTED]: Setup class")
        cls.log = logging.getLogger(__name__)
        cls.jmx_obj = JmeterInt()
        cls.log.info("[Completed]: Setup class")

    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-')
    def test_poc(self):
        """Sample test to run any jmeter script."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        jmx_file = "CSM_Login.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        resp = self.jmx_obj.run_jmx(jmx_file)
        assert resp, "Jmeter Execution Failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)
