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

from config import CMN_CFG
from config import di_cfg
from commons.constants import POD_NAME_PREFIX
from commons.constants import MOTR_CONTAINER_PREFIX
from commons.constants import PID_WATCH_LIST
from commons.utils import assert_utils
from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from libs.motr.emap_fi_adapter import MotrCorruptionAdapter
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
        cls.dtm_obj = DTMRecoveryTestLib()
        cls.emap_adapter_obj = MotrCorruptionAdapter(CMN_CFG, 0)
        cls.system_random = secrets.SystemRandom()
        logger.info("ENDED: Setup Operation")

    def teardown_class(self):
        """Teardown Node object"""
        self.motr_obj.close_connections()
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
        object_id = str(self.system_random.randint(1, 1024 * 1024)) + ":" + \
                    str(self.system_random.randint(1, 1024 * 1024))
        for client_num in range(motr_client_num):
            for node in node_pod_dict:

                for b_size, (cnt_c, cnt_u), layout, offset in zip(bsize_list, count_list,
                                                                  layout_ids, offsets):
                    self.motr_obj.dd_cmd(
                        b_size, cnt_c, infile, node)
                    self.motr_obj.cp_cmd(
                        b_size, cnt_c, object_id,
                        layout, infile, node, client_num)
                    self.motr_obj.cat_cmd(
                        b_size, cnt_c, object_id,
                        layout, outfile, node, client_num)
                    self.motr_obj.cp_update_cmd(
                        b_size=b_size, count=cnt_u,
                        obj=object_id, layout=layout,
                        file=infile, node=node, client_num=client_num, offset=offset)
                    self.motr_obj.cat_cmd(b_size, cnt_c, object_id, layout, outfile, node,
                                          client_num)
                    self.motr_obj.md5sum_cmd(infile, outfile, node, flag=True)
                    self.motr_obj.unlink_cmd(object_id, layout, node, client_num)

            logger.info("Stop: Verify multiple m0cp/cat operation")

    def m0cat_md5sum_m0unlink(self, bsize_list, count_list, layout_ids, object_list,
                              **kwargs):
        """
        Validate the corruption with md5sum after M0CAT and unlink the object
        """
        logger.info("STARTED: m0cat workflow")
        infile = kwargs.get("infile", TEMP_PATH + 'input')
        outfile = kwargs.get("outfile", TEMP_PATH + 'output')
        client_num = kwargs.get("client_num", 1)
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        for node in node_pod_dict:
            for b_size, cnt_c, layout, obj_id in zip(bsize_list, count_list,
                                                     layout_ids, object_list):
                self.motr_obj.cat_cmd(b_size, cnt_c, obj_id,
                                      layout, outfile, node,
                                      client_num)
                # Verify the md5sum
                self.motr_obj.md5sum_cmd(infile, outfile, node, flag=True)
                # Delete the object
                self.motr_obj.unlink_cmd(obj_id, layout, node, client_num)
                logger.info("Stop: Verify m0cat operation")

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
        logger.info("Step 1: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        self.motr_obj.switch_cluster_to_degraded_mode()
        count_list = [['10', '1'], ['10', '1']]
        bsize_list = ['4K', '4K']
        layout_ids = ['3', '3']
        offsets = [0, 16384]
        self.m0cp_corrupt_data_m0cat(layout_ids, bsize_list, count_list, offsets)

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

    @pytest.mark.tags("TEST-45716")
    @pytest.mark.motr_di
    def test_data_block_corruption_one_by_one(self):
        """
        Corrupt data block one by one using emap script and
         reading from object with m0cat should error.
        -s 4096 -c 10 -o 1048583 /root/infile -L 1
        -s 4096 -c 1 -o 1048583 /root/myfile -L 1 -u -O 0
        -o 1048583 -s 4096 -c 10 -L 1 /root/dest_myfile
        """
        count_list = ['10']
        bsize_list = ['4K']
        layout_ids = ['1']
        logger.info("STARTED: m0cp, corrupt and m0cat workflow of "
                    "each Data block one by one")
        infile = TEMP_PATH + 'input'
        outfile = TEMP_PATH + 'output'
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        motr_client_num = self.motr_obj.get_number_of_motr_clients()
        object_list = []
        log_file_list = []
        for client_num in range(motr_client_num):
            for node in node_pod_dict:
                object_id = str(self.system_random.randint(1, 1024 * 1024)) + ":" + \
                            str(self.system_random.randint(1, 1024 * 1024))
                for b_size, cnt_c, layout, in zip(bsize_list, count_list, layout_ids):
                    self.motr_obj.dd_cmd(
                        b_size, cnt_c, infile, node)
                    # Add object id in a list
                    object_list.append(object_id)
                    self.motr_obj.cp_cmd(
                        b_size, cnt_c, object_id,
                        layout, infile, node, client_num,
                        di_g=True)
                filepath = self.motr_obj.dump_m0trace_log(f"{node}-trace_log.txt", node)
                logger.debug("filepath is %s", filepath)
                log_file_list.append(filepath)
                # Fetch the FID from m0trace log
                fid_resp = self.motr_obj.read_m0trace_log(filepath)
                logger.debug("fid_resp is %s", fid_resp)
            metadata_path = self.emap_adapter_obj.get_metadata_shard(
                self.motr_obj.master_node_list[0])
            logger.debug("metadata device is %s", metadata_path[0])
            data_gob_id_resp = self.emap_adapter_obj.get_object_gob_id(
                metadata_path[0], fid=fid_resp)
            logger.debug("metadata device is %s", data_gob_id_resp)
            # Corrupt the data block 1
            for fid in data_gob_id_resp:
                corrupt_data_resp = self.emap_adapter_obj.inject_fault_k8s(fid)
                if not corrupt_data_resp:
                    logger.debug("Failed to corrupt the block %s", fid)
                assert_utils.assert_true(corrupt_data_resp)
            # Read the data using m0cp utility
            self.m0cat_md5sum_m0unlink(bsize_list, count_list, layout_ids, object_list,
                                       client_num=client_num)

    @pytest.mark.skip(reason="Test incomplete without teardown")
    @pytest.mark.tags("TEST-42910")
    @pytest.mark.motr_di
    def test_m0cp_block_corruption_m0cat_degraded_mode(self):
        """
        Corrupt data block using m0cp and reading from object with m0cat should error.
        -s 4096 -c 10 -o 1048583 /root/infile -L 1
        -s 4096 -c 1 -o 1048583 /root/myfile -L 1 -u -O 0
        -o 1048583 -s 4096 -c 10 -L 1 /root/dest_myfile
        """
        count_list = ['8']
        bsize_list = ['4K']
        layout_ids = ['1']
        proc_restart_delay = di_cfg['wait_time_m0d_restart']
        process = PID_WATCH_LIST[0]
        logger.info("STARTED: m0cp, corrupt workflow in healthy state")
        infile = TEMP_PATH + 'input'
        outfile = TEMP_PATH + 'output'
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        motr_client_num = self.motr_obj.get_number_of_motr_clients()
        object_id_list = []
        for client_num in range(motr_client_num):
            for node in node_pod_dict:
                object_id = str(self.system_random.randint(1, 1024 * 1024)) + ":" + \
                            str(self.system_random.randint(1, 1024 * 1024))
                for b_size, cnt_c, layout in zip(bsize_list, count_list, layout_ids):
                    self.motr_obj.dd_cmd(
                        b_size, cnt_c, infile, node)
                    object_id_list.append(object_id)
                    self.motr_obj.cp_cmd(
                        b_size, cnt_c, object_id,
                        layout, infile, node, client_num)
        # Degrade the setup by killing the m0d process
        pod_name, container = self.motr_obj.master_node_list[0].select_random_pod_container(
            POD_NAME_PREFIX, f"{MOTR_CONTAINER_PREFIX}")
        self.dtm_obj.set_proc_restart_duration(
            self.motr_obj.master_node_list[0], pod_name, container, proc_restart_delay)
        try:
            logger.info("Kill %s from %s pod %s container ", process, pod_name, container)
            resp = self.motr_obj.master_node_list[0].kill_process_in_container(
                pod_name=pod_name, container_name=container, process_name=process)
            logger.debug("Resp : %s", resp)
        except (ValueError, IOError) as ex:
            logger.error("Exception Occurred during killing process : %s", ex)
            self.dtm_obj.set_proc_restart_duration(
                self.motr_obj.master_node_list[0], pod_name, container, 0)
            assert False
        # Read the data using m0cat in degraded mode
        for client_num in range(motr_client_num):
            for node in node_pod_dict:
                for b_size, cnt_c, layout, object_id in zip(bsize_list, count_list, layout_ids,
                                                            object_id_list):
                    self.motr_obj.cat_cmd(b_size, cnt_c, object_id, layout,
                                          outfile, node, client_num)
