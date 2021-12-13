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

import os
import pytest
import csv
import random
import logging
from commons.utils import config_utils
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)


M0CRATE_WORKLOAD_YML = os.path.join(os.getcwd(), "config/motr/sample_m0crate.yaml")
M0CRATE_TEST_CSV = os.path.join(os.getcwd(), "config/motr/m0crate_tests.csv")
with open(M0CRATE_TEST_CSV) as CSV_FH:
    CSV_DATA = [row for row in csv.DictReader(CSV_FH)]

@pytest.fixture(params=CSV_DATA)
def param_loop(request):
    return request.param

class TestExecuteK8Sanity:
    """Execute Motr K8s Test suite"""        
    
    @classmethod
    def setup_class(cls):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        logger.info("ENDED: Setup Operation")
        cls.motr_obj = MotrCoreK8s()
    
    def teardown_class(self):
        del self.motr_obj

    def test_motr_k8s_lib(self):
        """
        Sample test
        """
        # TODO: This a sample test for the usage, need to delete it later
        logger.info(self.motr_obj.get_data_pod_list())
        logger.info(self.motr_obj.profile_fid)
        logger.info(self.motr_obj.node_dict)
        logger.info(self.motr_obj.cortx_node_list)
        logger.info(self.motr_obj.get_primary_cortx_node())
        logger.info(self.motr_obj.get_cortx_node_endpoints())

    @pytest.mark.reg
    def test_m0trace_utility(self, param_loop):
        M0_CFG = config_utils.read_yaml(M0CRATE_WORKLOAD_YML)[1]
        node = random.choice(self.motr_obj.cortx_node_list)
        node_enpts = self.motr_obj.get_cortx_node_endpoints(node)
        MOTR_HA_ADDR = node_enpts['hax_ep']
        PROF = self.motr_obj.profile_fid
        PROCESS_FID = node_enpts['m0client'][0]['fid']
        MOTR_LOCAL_ADDR = node_enpts['m0client'][0]['ep']
        for key, value in param_loop.items():
            if key in M0_CFG['MOTR_CONFIG'].keys():
                M0_CFG['MOTR_CONFIG'][key] = value
            elif key in M0_CFG['WORKLOAD_SPEC'][0]['WORKLOAD'].keys():
                M0_CFG['WORKLOAD_SPEC'][0]['WORKLOAD'][key] = value
        M0_CFG['MOTR_CONFIG']['MOTR_HA_ADDR'] = MOTR_HA_ADDR
        M0_CFG['MOTR_CONFIG']['PROF'] = PROF
        M0_CFG['MOTR_CONFIG']['PROCESS_FID'] = PROCESS_FID
        M0_CFG['MOTR_CONFIG']['MOTR_LOCAL_ADDR'] = MOTR_LOCAL_ADDR
        # TO DO: Add source file details to M0_CFG
        # TO DO: Get the POD details and run the DD commmand using source file
        logger.info(M0_CFG['MOTR_CONFIG'])
        logger.info(M0_CFG['WORKLOAD_SPEC'][0]['WORKLOAD'])
        config_utils.write_yaml(M0CRATE_WORKLOAD_YML, M0_CFG, backup=False)
        # TO DO: Execute m0crate command on the respective pod