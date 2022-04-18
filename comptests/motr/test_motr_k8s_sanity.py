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
#

"""
Test class that contains MOTR K8s tests.
"""

import os
import csv
import logging
from random import SystemRandom
from tkinter import E
import pytest
from commons.utils import assert_utils
from commons.utils import config_utils
from commons import constants as common_const
from libs.motr import TEMP_PATH, BSIZE_LAYOUT_MAP
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
        cls.m0kv_cfg = config_utils.read_yaml("config/motr/m0kv_test.yaml")
        logger.info("ENDED: Setup Operation")

    def teardown_class(self):
        """Teardown of Node object"""
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
        m0cfg['MOTR_CONFIG']['PROCESS_FID'] = node_enpts['m0client'][0]['fid']
        m0cfg['MOTR_CONFIG']['MOTR_LOCAL_ADDR'] = node_enpts['m0client'][0]['ep']
        b_size = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['BLOCK_SIZE']
        source_file = m0cfg['WORKLOAD_SPEC'][0]['WORKLOAD']['SOURCE_FILE']
        file_size = source_file.split('/')[-1]
        count = self.motr_obj.byte_conversion(file_size) // self.motr_obj.byte_conversion(b_size)
        self.motr_obj.dd_cmd(b_size.upper(), str(count), source_file, node)
        config_utils.write_yaml(config_file, m0cfg, backup=False, sort_keys=False)

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
        count = self.motr_obj.byte_conversion(file_size) // self.motr_obj.byte_conversion(b_size)
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

    @pytest.mark.tags("TEST-14921")
    @pytest.mark.motr_sanity
    def test_m0kv_utility(self):
        """
        This is to run the m0kv utility tests.
        Verify different options of m0kv utility
        """
        logger.info("Running m0kv tests")
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        node = self.system_random.choice(list(node_pod_dict.keys()))
        m0kv_tests = self.m0kv_cfg[1]
        for test in m0kv_tests:
            logger.info("RUNNING TEST: %s", test)
            cmd_batch = m0kv_tests[test]["batch"]
            for index, cnt in enumerate(cmd_batch):
                logger.info("Command number: %s", index)
                cmd = cnt["cmnd"]
                param = cnt["params"]
                logger.info("CMD: %s, PARAMS: %s", cmd, param)
                if cmd == "m0kv":
                    self.motr_obj.kv_cmd(cnt["params"], node, 0)
                else:
                    cmd = f'{cmd} {param}'
                    resp = self.motr_obj.node_obj.send_k8s_cmd(
                                                           operation="exec",
                                                           pod=node_pod_dict[node],
                                                           namespace=common_const.NAMESPACE,
                                                           command_suffix=
                                                           f"-c {common_const.HAX_CONTAINER_NAME} "
                                                           f"-- {cmd}", decode=True)
                    logger.info("Resp: %s", resp)
                    assert_utils.assert_not_in("ERROR" or "Error", resp,
                                               f'"{cmd}" Failed, Please check the log')

        logger.info("Stop: Verified multiple m0kv operations")

    @pytest.mark.tags("TEST-29708")
    @pytest.mark.motr_sanity
    def test_cluster_shutdown_with_m0cp(self):
        """
        This will test if the data written remains intact after cluster shutdown
        """
        infile = TEMP_PATH + 'input'
        outfile = TEMP_PATH + 'output'
        object_md5sum_dict = {}
        object_bsize_dict = {}
        try:
            for node in self.motr_obj.get_node_pod_dict():
                for b_size in BSIZE_LAYOUT_MAP.keys():
                    object_id = str(self.system_random.randint(1, 100)) + ":" + \
                                    str(self.system_random.randint(1, 1000))
                    self.motr_obj.dd_cmd(b_size, '4', infile, node)
                    self.motr_obj.cp_cmd(b_size, '4', object_id, BSIZE_LAYOUT_MAP[b_size],
                        infile, node)
                    md5sum = self.motr_obj.get_md5sum(infile, node)
                    object_bsize_dict[object_id] = b_size
                    object_md5sum_dict[object_id] = md5sum
            # Triggering Cluster shutdown
            self.motr_obj.shutdown_cluster()
            for obj_id in object_bsize_dict:
                self.motr_obj.cat_cmd(object_bsize_dict[obj_id],
                    '4', obj_id, BSIZE_LAYOUT_MAP[object_bsize_dict[obj_id]], outfile, node)
                md5sum = self.motr_obj.get_md5sum(outfile, node)
                assert_utils.assert_equal(object_md5sum_dict[obj_id], md5sum,
                        'Failed, Checksum did not match after cluster shutdown')
        except Exception as exc:
            logger.exception("Test has failed with execption: %s", exc)
            raise exc
        finally:
            node = self.system_random.choice(self.motr_obj.cortx_node_list)
            # Deleting Objects at the end
            for obj_id in object_bsize_dict:
                self.motr_obj.unlink_cmd(obj_id, BSIZE_LAYOUT_MAP[object_bsize_dict[obj_id]], node)

    @pytest.mark.tags("TEST-29707")
    @pytest.mark.motr_sanity
    def test_cluster_shutdown_with_m0crate(self):
        """
        This will test cluster health with m0crate IOs after cluster shutdown
        """
        config_file = os.path.join(os.getcwd(), "config/motr/test_29707_m0crate_workload.yaml")
        remote_file = TEMP_PATH + config_file.split("/")[-1]
        for node in self.motr_obj.get_node_pod_dict():
            self.update_m0crate_config(config_file, node)
            self.motr_obj.m0crate_run(config_file, remote_file, node)
        self.motr_obj.shutdown_cluster()
        for node in self.motr_obj.get_node_pod_dict():
            self.update_m0crate_config(config_file, node)
            self.motr_obj.m0crate_run(config_file, remote_file, node)
