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

"""
Prov test file for all the Prov tests scenarios for SW update disruptive.
"""

import os
import logging
import random
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons import constants as common_cnst
from commons.utils import assert_utils
from commons import pswdmanager
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, PROV_CFG
from libs.prov.provisioner import Provisioner

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestSWUpdateDisruptive:
    """
    Test suite for prov tests scenarios for SW update disruptive.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.build = os.getenv("Build", None)
        cls.build = "{}/{}".format(cls.build,
                                   "prod") if cls.build else "last_successful_prod"
        cls.build_branch = os.getenv("Build_Branch", "stable")
        cls.build_path = PROV_CFG["build_url"].format(
            cls.build_branch, cls.build)
        LOGGER.info(
            "User provided Hostname: {} and build path: {}".format(
                cls.host, cls.build_path))
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.hlt_obj = Health(hostname=cls.host, username=cls.uname,
                             password=cls.passwd)
        cls.prov_obj = Provisioner()
        LOGGER.info("Done: Setup module operations")
