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

m0cp -G -l inet:tcp:cortx-client-headless-svc-ssc-vm-rhev4-2620@21201
-H inet:tcp:cortx-client-headless-svc-ssc-vm-rhev4-2620@22001
-p 0x7000000000000001:0x110 -P 0x7200000000000001:0xae

m0cp from data unit aligned offset 0
-s 4096 -c 10 -o 1048583 /root/infile -L 3
-s 4096 -c 1 -o 1048583 /root/myfile -L 3 -u -O 0
m0cat   -o 1048583 -s 4096 -c 10 -L 3 /root/dest_myfile

2) m0cp from data unit aligned offset 16384
m0cp  -s 4096 -c 10 -o 1048584 /root/myfile -L 3
m0cat   -o 1048584 -s 4096 -c 10 -L 3 /root/dest_myfile
m0cp  -s 4096 -c 1 -o 1048584 /root/myfile -L 3 -u -O 16384
m0cat   -o 1048584 -s 4096 -c 10 -L 3 /root/dest_myfile
m0cp  -s 4096 -c 4 -o 1048584 /root/myfile -L 3 -u -O 16384
m0cat   -o 1048584 -s 4096 -c 10 -L 3 /root/dest_myfile
3) m0cp from non aligned offset 4096
m0cp  -s 4096 -c 10 -o 1048587 /root/myfile -L 3
m0cat -o 1048587 -s 4096 -c 10 -L 3 /root/dest_myfile
m0cp  -s 4096 -c 4 -o 1048587 /root/myfile -L 3 -u -O 4096
m0cat -o 1048587 -s 4096 -c 10 -L 3 /root/dest_myfile

"""

import os
import csv
import logging
import secrets
import pytest
from commons.utils import config_utils
from config import CMN_CFG
from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class", autouse=False)
def setup_teardown_fixture(request):
    """
    Yield fixture to setup pre requisites and teardown them.
    Part before yield will be invoked prior to each test case and
    part after yield will be invoked after test call i.e as teardown.
    """
    request.cls.log = logging.getLogger(__name__)
    request.cls.log.info("STARTED: Setup test operations.")
    request.cls.secure_range = secrets.SystemRandom()
    request.cls.nodes = CMN_CFG["nodes"]
    request.cls.m0crate_workload_yaml = os.path.join(
        os.getcwd(), "config/motr/sample_m0crate.yaml")
    request.cls.m0crate_test_csv = os.path.join(
        os.getcwd(), "config/motr/m0crate_tests.csv")
    with open(request.cls.m0crate_test_csv) as csv_fh:
        request.cls.csv_data = [row for row in csv.DictReader(csv_fh)]
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

    # pylint: disable=R0914
    def m0cp_corrupt_data_m0cat(self, layout_ids, bsize_list, count_list, offsets):
        """
        Create an object with M0CP, corrupt with M0CP and
        validate the corruption with md5sum after M0CAT.
        """
        logger.info("STARTED: m0cp, corrupt and m0cat workflow")
        infile = TEMP_PATH + 'input'
        outfile = TEMP_PATH + 'output'
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        motr_client_num = self.motr_obj.get_number_of_motr_clients()
        for client_num in range(motr_client_num):
            for node in node_pod_dict:

                for b_size, (cnt_c, cnt_u), layout in zip(bsize_list, count_list,
                                                          layout_ids, offsets):
                    object_id = str(self.system_random.randint(1, 1024 * 1024)) + ":" + \
                                str(self.system_random.randint(1, 1024 * 1024))
                    self.motr_obj.dd_cmd(b_size, cnt_c, infile, node)
                    self.motr_obj.cp_cmd(b_size, cnt_c, object_id, layout, infile, node, client_num)
                    self.motr_obj.cat_cmd(b_size, cnt_c, object_id, layout, outfile, node,
                                          client_num)
                    self.motr_obj.cp_update_cmd(b_size=b_size, count=cnt_u,
                                                object_id=object_id, layout=layout,
                                                infile=infile, node=node, client_num=client_num)
                    self.motr_obj.cat_cmd(b_size, cnt_c, object_id, layout, outfile, node,
                                          client_num)
                    self.motr_obj.md5sum_cmd(infile, outfile, node)
                    self.motr_obj.unlink_cmd(object_id, layout, node, client_num)

            logger.info("Stop: Verify multiple m0cp/cat operation")

    @pytest.mark.skip(reason="Feature Unavailable")
    @pytest.mark.tags("TEST-41739")
    @pytest.mark.motr_di
    def test_m0cp_m0cat_block_corruption(self):
        """
        Corrupt data block using m0cp and reading from object with m0cat should error.
        -s 4096 -c 10 -o 1048583 /root/infile -L 3
        -s 4096 -c 1 -o 1048583 /root/myfile -L 3 -u -O 0
        -o 1048583 -s 4096 -c 10 -L 3 /root/dest_myfile
        """
        count_list = [['10', '1'], ['10', '1']]
        bsize_list = ['4K', '4K']
        layout_ids = ['3', '3']
        offsets = [0, 16384]
        self.m0cp_corrupt_data_m0cat(layout_ids, bsize_list, count_list, offsets)

    @pytest.mark.skip(reason="Test incomplete without teardown")
    @pytest.mark.tags("TEST-41766")
    @pytest.mark.motr_di
    def test_m0cp_m0cat_block_corruption_degraded_mode(self):
        """
        In degraded mode Corrupt data block using m0cp and reading
        from object with m0cat should error.
        """
        logger.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert resp[1], "Failed to shutdown/delete pod"
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert resp[0], "Cluster/Services status is not as expected"
        logger.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        count_list = [['10', '1'], ['10', '1']]
        bsize_list = ['4K', '4K']
        layout_ids = ['3', '3']
        offsets = [0, 16384]
        self.m0cp_corrupt_data_m0cat(layout_ids, bsize_list, count_list, offsets)

    @pytest.mark.skip(reason="Feature Unavailable")
    @pytest.mark.tags("TEST-41911")
    @pytest.mark.motr_di
    def test_m0cp_m0cat_block_corruption_unaligned(self):
        """
        Corrupt data block using m0cp and reading from object with m0cat should error.
        -s 4096 -c 10 -o 1048583 /root/infile -L 3
        -s 4096 -c 1 -o 1048583 /root/myfile -L 3 -u -O 0
        -o 1048583 -s 4096 -c 10 -L 3 /root/dest_myfile
        """
        count_list = [['10', '10']]
        bsize_list = ['4K']
        layout_ids = ['3']
        offsets = [4096]
        self.m0cp_corrupt_data_m0cat(layout_ids, bsize_list, count_list, offsets)
