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
"""Tests System capacity scenarios using REST API
"""
import logging
import pytest
from libs.csm.rest.csm_rest_capacity import SystemCapacity
from commons.helpers.health_helper import Health
from commons.utils import assert_utils
from commons.utils import config_utils
from commons import cortxlogging

class TestSystemCapacity():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.system_capacity = SystemCapacity()
        cls.log.info("Initiating Rest Client ...")
        main_conf = config_utils.read_yaml("config\\common_config.yaml")[1]
        cls.health_helper = Health(main_conf["server_hostname"]+main_conf["host_domain"],
                                    main_conf["server_username"],
                                    main_conf["server_password"])

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-15200')
    def test_4202(self):
        """Test REST API for GET request with default arguments return 200 and json response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        results = self.system_capacity.parse_capacity_usage()
        csm_total, csm_avail, csm_used, csm_used_percent, csm_unit = results
        ha_total, ha_avail, ha_used = self.health_helper.get_sys_capacity()
        ha_used_percent = round((ha_used / ha_total) * 100, 1)
        csm_used_percent = round(csm_used_percent, 1)
        assert_utils.assert_equals(
            csm_total, ha_total, "Total capacity check failed.")
        assert_utils.assert_equals(
            csm_avail, ha_avail, "Available capacity check failed.")
        assert_utils.assert_equals(
            csm_used, ha_used, "Used capacity check failed.")
        assert_utils.assert_equals(
            csm_used_percent, ha_used_percent, "Used capacity percentage check failed.")
        assert_utils.assert_equals(
            csm_unit, 'BYTES', "Capacity unit check failed.")
        self.log.info("Capacity reported by CSM matched HCTL response.")
        self.log.info("##### Test ended -  %s #####", test_case_name)
