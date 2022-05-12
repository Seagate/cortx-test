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

"""
Test class that contains unittests for MOTR lib.
"""

import logging
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)

class TestMotrLib:
    """Execute Motr K8s Test suite"""

    @classmethod
    def setup_class(cls):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        cls.motr_obj = MotrCoreK8s()
        logger.info("ENDED: Setup Operation")

    def teardown_class(self):
        """Teardown of Node object"""
        del self.motr_obj

    def test_motr_k8s_lib(self):
        """
        Sample test
        """
        # TODO: This a sample test for the usage, need to delete it later
        logger.info(self.motr_obj.get_node_pod_dict())
        logger.info(self.motr_obj.profile_fid)
        logger.info(self.motr_obj.node_dict)
        logger.info(self.motr_obj.cortx_node_list)
        logger.info(self.motr_obj.get_primary_cortx_node())
        logger.info(self.motr_obj.get_cortx_node_endpoints())
