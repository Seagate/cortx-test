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
"""Tests various operation on CSM user using REST API
"""
import time
import json
import logging
import pytest
#from commons.constants import Rest as const
from commons import configmanager
from commons import cortxlogging
from libs.jmeter.jmeter_integration import JmeterInt

class TestCsmLoad():
    """REST API Test cases for CSM users
    """
    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.cmn_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_jmeter.yaml")["common_conf"]
        cls.jmx_obj = JmeterInt()
        cls.log.info("Initiating Rest Client ...")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10720')
    def test_poc(self):
        """Initiating the test case to verify List CSM user.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.jmx_obj.run_jmx("CSM_Login.jmx")
        assert resp[0], resp[1]
        assert self.cmn_conf["error"] in resp[1], resp[1]
        self.log.info("##### Test completed -  %s #####", test_case_name)