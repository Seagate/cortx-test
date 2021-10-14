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

"""Failure Domain LC Test Suite."""
import logging
import os

import pytest
from libs.prov.prov_lc_deploy import ProvDeployLCLib


class TestFailureDomainLC:
    """Test Failure Domain LC (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.git_id = os.getenv("GIT_ID")
        cls.git_token = os.getenv("GIT_PASSWORD")
        cls.docker_username = ""
        cls.docker_password = ""
        cls.deploy_lc_obj = ProvDeployLCLib()

    @pytest.mark.run(order=1)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29485")
    def test_29485(self):
        """
        Intel ISA  - 3node - SNS- 4+2+0 Deployment
        """
        #TODO : Retrieve solution file
        self.deploy_lc_obj.deploy_cortx_cluster("solution.yaml", self.docker_username,
                                                self.docker_password, self.git_id, self.git_token)
