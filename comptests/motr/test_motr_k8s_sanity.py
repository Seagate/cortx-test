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
import csv
import logging
from random import SystemRandom
import pytest
from commons.utils import config_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)


M0CRATE_WORKLOAD_YML = os.path.join(os.getcwd(), "config/motr/sample_m0crate.yaml")
M0CRATE_TEST_CSV = os.path.join(os.getcwd(), "config/motr/m0crate_tests.csv")
with open(M0CRATE_TEST_CSV) as CSV_FH:
    CSV_DATA = [row for row in csv.DictReader(CSV_FH)]


@pytest.fixture(params=CSV_DATA)
def param_loop(request):
    """
    This fixture helps to run over a row of csv data:
    param: list of values to go over one by one
    """
    return request.param


class TestExecuteK8Sanity:
    """Execute Motr K8s Test suite"""

    @classmethod
    def setup_class(cls):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        cls.motr_obj = MotrCoreK8s()
        cls.system_random = SystemRandom()
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

    @pytest.mark.tags("TEST-14925")
    @pytest.mark.motr_sanity
    def test_m0crate_utility(self, param_loop):
        """
        This is to run the m0crate utility tests.
        param: param_loop: Fixture which provides one set of values required to run the utility
        """
        source_file = TEMP_PATH + 'source_file'
        remote_file = TEMP_PATH + M0CRATE_WORKLOAD_YML.split("/")[-1]
        m0cfg = config_utils.read_yaml(M0CRATE_WORKLOAD_YML)[1]
        node = self.system_random.choice(self.motr_obj.cortx_node_list)
        node_enpts = self.motr_obj.get_cortx_node_endpoints(node)
        for key, value in param_loop.items():
            if value.isdigit():
                value = int(value)
            if key in m0cfg['MOTR_CONFIG'].keys():
                m0cfg['MOTR_CONFIG'][key] = value
            elif key in m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD'].keys():
                m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD'][key] = value
            else:
                if key == 'TEST_ID':
                    logger.info("Executing the test: %s", value)
                elif key == 'SOURCE_FILE_SIZE':
                    file_size = value
        m0cfg['MOTR_CONFIG']['MOTR_HA_ADDR'] = node_enpts['hax_ep']
        m0cfg['MOTR_CONFIG']['PROF'] = self.motr_obj.profile_fid
        m0cfg['MOTR_CONFIG']['PROCESS_FID'] = node_enpts['m0client'][0]['fid']
        m0cfg['MOTR_CONFIG']['MOTR_LOCAL_ADDR'] = node_enpts['m0client'][0]['ep']
        m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['SOURCE_FILE'] = source_file
        logger.info(m0cfg['MOTR_CONFIG'])
        logger.info(m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD'])
        b_size = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['BLOCK_SIZE']
        count = self.motr_obj.byte_conversion(file_size)//self.motr_obj.byte_conversion(b_size)
        self.motr_obj.dd_cmd(b_size.upper(), str(count), source_file, node)
        config_utils.write_yaml(M0CRATE_WORKLOAD_YML, m0cfg, backup=False, sort_keys=False)
        self.motr_obj.m0crate_run(M0CRATE_WORKLOAD_YML, remote_file, node)

    @pytest.mark.tags("TEST-23036")
    @pytest.mark.motr_sanity
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
