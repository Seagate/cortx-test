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
#

"""
Module is intended to cater Motr level DI tests which utilize M0* utils and validate data
corruption detection. It will host all test classes or functions related to detection of
discrepancies in data blocks, checksum, parity and emaps.
"""

import os
import csv
import logging
import secrets
import pytest
from commons.utils import config_utils
from commons import constants as common_const
from config import CMN_CFG
from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class", autouse=False)
def setup_multipart_fixture(request):
    """
    Yield fixture to setup pre requisites and teardown them.
    Part before yield will be invoked prior to each test case and
    part after yield will be invoked after test call i.e as teardown.
    """
    request.cls.log = logging.getLogger(__name__)
    request.cls.log.info("STARTED: Setup test operations.")
    request.cls.secure_range = secrets.SystemRandom()
    request.cls.nodes = CMN_CFG["nodes"]
    request.cls.M0CRATE_WORKLOAD_YML = os.path.join(
        os.getcwd(), "config/motr/sample_m0crate.yaml")
    request.cls.M0CRATE_TEST_CSV = os.path.join(
        os.getcwd(), "config/motr/m0crate_tests.csv")
    with open(request.cls.M0CRATE_TEST_CSV) as CSV_FH:
        request.cls.CSV_DATA = [row for row in csv.DictReader(CSV_FH)]
    request.cls.log.info("ENDED: Setup test suite operations.")
    yield
    request.cls.log.info("STARTED: Test suite Teardown operations")
    request.cls.log.info("ENDED: Test suite Teardown operations")


class TestCorruptDataDetection:
    """Test suite aimed at verifying detection of data corruption in degraded mode.
    Detection supported for following entities in Normal and degraded mode.
    1. Checksum
    2. Data blocks
    3. Parity
    """

    @classmethod
    def setup_class(cls):
        """ Setup class for running Motr tests"""
        logger.info("STARTED: Setup Operation")
        cls.motr_obj = MotrCoreK8s()
        cls.m0kv_cfg = config_utils.read_yaml("config/motr/m0kv_test.yaml")
        logger.info("ENDED: Setup Operation")

    def teardown_class(self):
        """Teardown Node object"""
        for con in self.connections:
            con.disconnect()
        del self.motr_obj

    def update_m0crate_config(self, config_file, node):
        """
        This will modify the m0crate workload config yaml with the node details
        param: confile_file: Path of m0crate workload config yaml
        param: node: Cortx node on which m0crate utility to be executed
        """
        m0cfg = config_utils.read_yaml(config_file)[1]
        node_enpts = self.motr_obj.get_cortx_node_endpoints(node)
        # modify m0cfg and write back to file
        m0cfg['MOTR_CONFIG']['MOTR_HA_ADDR'] = node_enpts['hax_ep']
        m0cfg['MOTR_CONFIG']['PROF'] = self.motr_obj.profile_fid
        m0cfg['MOTR_CONFIG']['PROCESS_FID'] = node_enpts[common_const.MOTR_CLIENT][0]['fid']
        m0cfg['MOTR_CONFIG']['MOTR_LOCAL_ADDR'] = node_enpts[common_const.MOTR_CLIENT][0]['ep']
        b_size = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['BLOCK_SIZE']
        source_file = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['SOURCE_FILE']
        file_size = source_file.split('/')[-1]
        count = self.motr_obj.byte_conversion(file_size) // self.motr_obj.byte_conversion(b_size)
        self.motr_obj.dd_cmd(b_size.upper(), str(count), source_file, node)
        config_utils.write_yaml(config_file, m0cfg, backup=False, sort_keys=False)

    @pytest.mark.tags("TEST-14925")
    @pytest.mark.motr_sanity
    def test_m0crate_utility(self, param_loop):
        """
        This is to run the m0crate utility tests.
        param: param_loop: Fixture which provides one set of values required to run the utility
        """
        source_file = TEMP_PATH + 'source_file'
        remote_file = TEMP_PATH + self.M0CRATE_WORKLOAD_YML.split("/")[-1]
        m0cfg = config_utils.read_yaml(self.M0CRATE_WORKLOAD_YML)[1]
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
        m0cfg['MOTR_CONFIG']['PROCESS_FID'] = node_enpts[common_const.MOTR_CLIENT][0]['fid']
        m0cfg['MOTR_CONFIG']['MOTR_LOCAL_ADDR'] = node_enpts[common_const.MOTR_CLIENT][0]['ep']
        m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['SOURCE_FILE'] = source_file
        logger.info(m0cfg['MOTR_CONFIG'])
        logger.info(m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD'])
        b_size = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['BLOCK_SIZE']
        count = self.motr_obj.byte_conversion(file_size) // self.motr_obj.byte_conversion(b_size)
        self.motr_obj.dd_cmd(b_size.upper(), str(count), source_file, node)
        config_utils.write_yaml(self.M0CRATE_WORKLOAD_YML, m0cfg, backup=False, sort_keys=False)
        self.motr_obj.m0crate_run(self.M0CRATE_WORKLOAD_YML, remote_file, node)

    def m0cp_corrupt_m0cat(self):
        logger.info("STARTED: Verify multiple m0cp/m0cat operation")
        infile = TEMP_PATH + 'input'
        outfile = TEMP_PATH + 'output'
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        motr_client_num = self.motr_obj.get_number_of_motr_clients()
        for client_num in range(motr_client_num):
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
                    self.motr_obj.md5sum_cmd(infile, outfile, node)
                    self.motr_obj.unlink_cmd(object_id, layout, node, client_num)

            logger.info("Stop: Verify multiple m0cp/cat operation")


    @pytest.mark.tags("TEST-23036")
    @pytest.mark.motr_sanity
    def test_m0cp_m0cat_block_corruption(self):
        """
        Corrupt data block using m0cp and reading from object with m0cat should error.
        """
        self.m0cp_corrupt_m0cat()

    @pytest.mark.tags("TEST-23036")
    @pytest.mark.motr_sanity
    def test_m0cp_m0cat_checksum_corruption(self):
        """
        Corrupt data block using m0cp and reading from object with m0cat should error.
        """
        self.m0cp_corrupt_m0cat()

