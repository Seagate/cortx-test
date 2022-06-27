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
# from uu import test

import pytest
from commons.utils import config_utils
# from commons.utils import assert_utils
from config import CMN_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.ha.ha_comp_libs import HAK8SCompLib
from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s
from libs.motr import motr_test_lib
# from commons import constants as common_const

LOGGER = logging.getLogger(__name__)



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
        os.getcwd(), "config/motr/sample_m0crate.yaml"
    )
    request.cls.m0crate_test_csv = os.path.join(
        os.getcwd(), "config/motr/m0crate_tests.csv"
    )
    with open(request.cls.m0crate_test_csv) as csv_fh:
        request.cls.csv_data = [row for row in csv.DictReader(csv_fh)]
    request.cls.log.info("ENDED: Setup test suite operations.")
    yield
    request.cls.log.info("STARTED: Test suite Teardown operations")
    request.cls.log.info("ENDED: Test suite Teardown operations")


class TestCorruptDataDetection:
    """Test suite aimed at verifying detection of data corruption in Normal and Degraded mode.
    Detection supported for following entities in Normal and degraded mode.
    1. Checksum
    2. Data blocks
    3. Parity
    """

    @classmethod
    def setup_class(cls):
        """Setup class for running Motr tests"""
        LOGGER.info("STARTED: Setup Operation")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_worker_list = []
        cls.node_master_list = []
        cls.host_list = []
        cls.motr_test_obj = motr_test_lib.MotrTestLib()
        cls.ha_obj = HAK8s()
        cls.ha_comp_obj = HAK8SCompLib()
        cls.motr_k8s_obj = MotrCoreK8s()
        cls.m0kv_cfg = config_utils.read_yaml("config/motr/m0kv_test.yaml")
        LOGGER.info("ENDED: Setup Operation")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        LOGGER.info("Check the overall status of the cluster.")
        # Todo:
        # resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        # if not resp[0]:
        #     resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        #     assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        # LOGGER.info("Checking if all the ha services are up and running")
        # resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        # assert_utils.assert_true(resp, "HA services are not running")
        LOGGER.info("Done: Setup operations.")

    def teardown_class(self):
        """Teardown Node object"""
        # for con in self.connections:
        #     con.disconnect()
        del self.motr_k8s_obj

    # pylint: disable=R0914
    def m0cp_corrupt_data_m0cat(self, layout_ids, bsize_list, count_list, offsets):
        """
        Create an object with M0CP, corrupt with M0CP and
        validate the corruption with md5sum after M0CAT.
        """
        LOGGER.info("STARTED: m0cp, corrupt and m0cat workflow")
        infile = TEMP_PATH + "input"
        outfile = TEMP_PATH + "output"
        node_pod_dict = self.motr_k8s_obj.get_node_pod_dict()
        motr_client_num = self.motr_k8s_obj.get_number_of_motr_clients()
        for client_num in range(motr_client_num):
            for node in node_pod_dict:
                for b_size, (cnt_c, cnt_u), layout in zip(
                        bsize_list, count_list, layout_ids, offsets
                ):
                    object_id = (
                            str(self.system_random.randint(1, 1024 * 1024))
                            + ":"
                            + str(self.system_random.randint(1, 1024 * 1024))
                    )
                    self.motr_k8s_obj.dd_cmd(b_size, cnt_c, infile, node)
                    self.motr_k8s_obj.cp_cmd(
                        b_size, cnt_c, object_id, layout, infile, node, client_num
                    )
                    self.motr_k8s_obj.cat_cmd(
                        b_size, cnt_c, object_id, layout, outfile, node, client_num
                    )
                    self.motr_k8s_obj.cp_update_cmd(
                        b_size=b_size,
                        count=cnt_u,
                        object_id=object_id,
                        layout=layout,
                        infile=infile,
                        node=node,
                        client_num=client_num,
                    )
                    self.motr_k8s_obj.cat_cmd(
                        b_size, cnt_c, object_id, layout, outfile, node, client_num
                    )
                    self.motr_k8s_obj.md5sum_cmd(infile, outfile, node)
                    self.motr_k8s_obj.unlink_cmd(object_id, layout, node, client_num)

            LOGGER.info("Stop: Verify multiple m0cp/cat operation")

    # pylint: disable=R0914
    def corrupt_checksum_emap(self, layout_id, bsize, count, offsets):
        """
        Create an object with M0CP, corrupt with M0CP and
        validate the corruption with emap.
        """
        LOGGER.info("STARTED: corrupt_checksum_emap workflow")
        local_file_path = "scripts/server_scripts/error_injection.py"
        infile = os.path.join(TEMP_PATH, "infile")
        outfile = os.path.join(TEMP_PATH, "outfile")
        str_client = ""
        exec_count = 0
        node_pod_dict = self.motr_k8s_obj.get_node_pod_dict()
        motr_client_num = self.motr_k8s_obj.get_number_of_motr_clients()
        LOGGER.info(f'Node_Pod_Dict = {node_pod_dict}')
        LOGGER.info(f'motr_client_num = {motr_client_num}')

        # Collect emap params
        # Login to the node from the dict (Client Node) and execute the emap script with params
        for client_num in range(motr_client_num):
            for node in node_pod_dict:
                # if(node contains word 'client') select that as first node for emap exec
                # Todo: Remove exec_count = 0 and use client_num itself - first client only is sufficient
                if str_client in node and exec_count == 0:
                    # Step 0 - Check if dd cmd is running
                    self.motr_k8s_obj.dd_cmd(bsize, count, infile, node)
                    LOGGER.debug(f'Debug: ~~~~~~~~~~~ dd command done ~~~~~')
                    object_id = (
                            str(self.system_random.randint(1, 1024 * 1024))
                            + ":"
                            + str(self.system_random.randint(1, 1024 * 1024))
                    )
                    self.motr_k8s_obj.cp_cmd(
                        bsize, count, object_id, layout_id, infile, node, client_num
                    )
                    LOGGER.debug(f'Debug: ~~~~~~~~~~~ m0cp command done ~~~~~')

                    self.motr_k8s_obj.cat_cmd(
                        bsize, count, object_id, layout_id, outfile, node, client_num
                    )
                    LOGGER.debug(f'Debug: ~~~~~~~~~~~ m0cat command done ~~~~~')


                    # Copy EMAP script to the Node
                    # kubectl cp ~/error_injection.py
                    # cortx/cortx-data-ssc-vm-rhev4-2740-78bff7b54c-pf584:/root/error_injection.py -c cortx-motr-io-001
                    # ########## Step 1
                    # pod_name = ""
                    # container_path = "cortx/cortx-data-ssc-vm-rhev4-2740-78bff7b54c-pf584"
                    # # copy_file_to_container(self, local_file_path, pod_name, container_path, container_name):
                    # result = self.motr_k8s_obj.node_obj.copy_file_to_container(local_file_path, pod_name,
                    #                                                            container_path,
                    #                                                            common_const.HAX_CONTAINER_NAME)
                    # logging.info(result)
                    # if not result[0]:
                    #     raise Exception("Copy from {} to {} failed with error: \
                    #                              {}".format(local_file_path, common_const.HAX_CONTAINER_NAME,
                    #                                         result[1]))
                    ##########
                    # m0cat outfile
                    # self.motr_k8s_obj.cat_cmd(bsize, count, obj=obj, )
                    exec_count = exec_count + 1
        LOGGER.info("Stop: Test corrupt_checksum_emap operation")

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
        count_list = [["10", "1"], ["10", "1"]]
        bsize_list = ["4K", "4K"]
        layout_ids = ["3", "3"]
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
        LOGGER.info(
            "Step 2: Shutdown random data pod by making replicas=0 and "
            "verify cluster & remaining pods status"
        )
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0],
            health_obj=self.hlth_master_list[0],
        )
        # Assert if empty dictionary
        assert resp[1], "Failed to shutdown/delete pod"
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]["deployment_name"]
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]["method"]
        assert resp[0], "Cluster/Services status is not as expected"
        LOGGER.info(
            "Step 2: Successfully shutdown data pod %s. Verified cluster and "
            "services states are as expected & remaining pods status is online.",
            pod_name,
        )
        count_list = [["10", "1"], ["10", "1"]]
        bsize_list = ["4K", "4K"]
        layout_ids = ["3", "3"]
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
        count_list = [["10", "10"]]
        bsize_list = ["4K"]
        layout_ids = ["3"]
        offsets = [4096]
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
        count_list = [["10", "10"]]
        bsize_list = ["4K"]
        layout_ids = ["3"]
        offsets = [4096]
        self.m0cp_corrupt_data_m0cat(layout_ids, bsize_list, count_list, offsets)

    # @pytest.mark.skip(reason="Feature Unavailable")
    @pytest.mark.tags("TEST-41742")
    @pytest.mark.motr_di
    def test_corrupt_checksum_emap_aligned(self):
        """
        Checksum corruption and detection with EMAP/m0cp and m0cat
        Copy motr block with m0cp and corrupt/update with m0cp and then
        Corrupt checksum block using m0cp+error_injection.py script
        Read from object with m0cat should throw an error.
        -s 4096 -c 10 -o 1048583 /root/infile -L 3
        -s 4096 -c 1 -o 1048583 /root/myfile -L 3 -u -O 0
        -o 1048583 -s 4096 -c 10 -L 3 /root/dest_myfile
        """
        count_list = ["4"]
        bsize_list = ["1M"]
        layout_ids = ["9"]
        offsets = [0]
        # Check for deployment status using kubectl commands - Taken care in setup stage
        # Check for hctl status - taken care in setup
        # Todo: Exract the parameters
        # Get parameters from hctl
        # Format command for m0cp

        # Execute command
        # Format command for corrupt_checksum
        # Execute command
        # Format m0cat command
        # Execute command
        # Validate error

        # Todo: Add in for loop
        self.corrupt_checksum_emap("9", "1M", "4", "0")  # Todo: Remove hard coding

