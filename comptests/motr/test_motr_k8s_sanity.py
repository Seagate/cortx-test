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
Test class that contains K8s tests.
"""

import logging
import pytest
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)

MOTR_OBJ = MotrCoreK8s()

class TestExecuteK8Sanity:
    """Execute Motr K8s Test suite"""

    @pytest.yield_fixture(autouse=True)
    def setup_class(self):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        logger.info("ENDED: Setup Operation")
        yield
        # Perform the clean up for each test.
        logger.info("STARTED: Teardown Operation")
        logger.info("ENDED: Teardown Operation")

    def test_motr_k8s_lib(self):
        """
        Sample test
        """
        # TODO: This a sample test for the usage, need to delete it later
        logger.info(MOTR_OBJ.cluster_info)
        logger.info(MOTR_OBJ.profile_fid)
        logger.info(MOTR_OBJ.node_dict)
        logger.info(MOTR_OBJ.storage_nodes)
        logger.info(MOTR_OBJ.get_primary_podNode())
        logger.info(MOTR_OBJ.get_podNode_endpoints())
