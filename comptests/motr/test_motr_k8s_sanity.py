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
Test class that contains MOTR K8s tests.
"""

import logging
from random import SystemRandom

from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)


class TestExecuteK8Sanity:
    """Execute Motr K8s Test suite"""

    @classmethod
    def setup_class(cls):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        cls.motr_obj = MotrCoreK8s()
        cls.system_random = SystemRandom()
        logger.info("ENDED: Setup Operation")

    def test_motr_k8s_lib(cls):
        """
        Sample test
        """
        # TODO: This a sample test for the usage, need to delete it later
        logger.info(cls.motr_obj.get_data_pod_list())
        logger.info(cls.motr_obj.profile_fid)
        logger.info(cls.motr_obj.node_dict)
        logger.info(cls.motr_obj.cortx_node_list)
        logger.info(cls.motr_obj.get_primary_cortx_node())
        logger.info(cls.motr_obj.get_cortx_node_endpoints())

    def test_m0cp_m0cat_workload(self):
        """
        Verify different size object m0cp m0cat operation
        """
        logger.info("STARTED: Verify multiple m0cp/m0cat operation")
        infile = TEMP_PATH + 'input'
        outfile = TEMP_PATH + 'output'
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        m0client_num = self.motr_obj.get_number_of_m0clients()
        for client_num in range(m0client_num):
            for node in node_pod_dict:
                count_list = ['1', '2', '4', '4', '4', '2', '4', '4', '250',
                              '2', '4', '2', '3', '4', '8', '4', '1024']
                bsize_list = ['4K', '4K', '4K', '8K', '16K', '64K', '64K', '128K',
                              '4K', '1M', '1M', '4M', '4M', '4M', '4M', '16M', '1M']
                layout_ids = ['1', '1', '1', '2', '3', '5', '5', '6', '1',
                              '9', '9', '11', '11', '11', '11', '13', '9']
                for b_size, count, layout in zip(bsize_list, count_list, layout_ids):
                    object_id = str(self.system_random.randint(1, 100)) + ":" + \
                                str(self.system_random.randint(1, 100))
                    self.motr_obj.dd_cmd(b_size, count, infile, node)
                    self.motr_obj.cp_cmd(b_size, count, object_id, layout, infile, node, client_num)
                    self.motr_obj.cat_cmd(b_size, count, object_id, layout, outfile, node,
                                          client_num)
                    self.motr_obj.diff_cmd(infile, outfile, node)
                    self.motr_obj.md5sum_cmd(infile, outfile, node)
                    self.motr_obj.unlink_cmd(object_id, layout, node, client_num)

            logger.info("Stop: Verify multiple m0cp/cat operation")
