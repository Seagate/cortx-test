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


class TestExecuteK8Sanity:
    """Execute Motr K8s Test suite"""

    @classmethod
    def setup_class(cls):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        logger.info("ENDED: Setup Operation")
        cls.motr_obj = MotrCoreK8s()
        yield
        # Perform the clean up for each test.
        logger.info("STARTED: Teardown Operation")
        del cls.motr_obj
        logger.info("ENDED: Teardown Operation")

    @classmethod
    def test_motr_k8s_lib(cls):
        """
        Sample test
        """
        # TODO: This a sample test for the usage, need to delete it later
        logger.info(cls.motr_obj.cluster_info)
        logger.info(cls.motr_obj.profile_fid)
        logger.info(cls.motr_obj.node_dict)
        logger.info(cls.motr_obj.storage_nodes)
        logger.info(cls.motr_obj.get_primary_podNode())
        logger.info(cls.motr_obj.get_podNode_endpoints())
