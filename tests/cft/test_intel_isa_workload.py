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

"""Intel ISA workload suit."""
from __future__ import absolute_import

import logging
import os

import pytest

from commons import configmanager
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from libs.ha.ha_common_libs import HALibs
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib


class TestIntelISAIO:
    """
    Test suite for Intel ISA - IO tests.
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup Module operations")
        test_config = "config/cft/test_intel_isa_workload.yaml"
        cls.test_config = configmanager.get_config_wrapper(fpath=test_config)
        cls.access_key, cls.secret_key = S3H_OBJ.get_local_keys()
        cls.s3t_obj = S3TestLib(access_key=cls.access_key, secret_key=cls.secret_key)
        cls.setup_type = CMN_CFG["setup_type"]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.ha_obj = HALibs()
        cls.prov_obj = ProvDeployK8sCortxLib()
        cls.node_list = []
        cls.hlt_list = []
        cls.reset_s3config = False
        cls.master_node_list = []
        cls.worker_node_list = []
        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname,
                                       password=cls.passwd))
            if CMN_CFG["product_family"] == const.PROD_FAMILY_LR \
                    and CMN_CFG["product_type"] == const.PROD_TYPE_NODE:
                cls.node_list.append(Node(hostname=cls.host,
                                          username=cls.uname, password=cls.passwd))
            elif CMN_CFG["product_family"] == const.PROD_FAMILY_LC:
                node_obj = LogicalNode(hostname=cls.host, username=cls.uname, password=cls.passwd)
                if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                    cls.master_node_list.append(node_obj)
                else:
                    cls.worker_node_list.append(node_obj)

            cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestIntelISAIO")
            if not os.path.exists(cls.test_dir_path):
                os.makedirs(cls.test_dir_path)
            cls.log.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        self.log.info("STARTED: Setup Operations")
        self.reset_s3config = False
        self.log.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        """
        self.log.info("STARTED: Teardown Operations")
        if self.reset_s3config:
            if CMN_CFG["product_family"] == const.PROD_FAMILY_LR and \
                    CMN_CFG["product_type"] == const.PROD_TYPE_NODE:
                self.log.info("Set S3_MOTR_IS_READ_VERIFY to false on all the %s nodes",
                              self.num_nodes)
                for node in range(self.num_nodes):
                    S3H_OBJ.update_s3config(section="S3_MOTR_CONFIG",
                                            parameter=self.test_config["test_basic_io"][
                                                "parity_check_flag"],
                                            value=False,
                                            host=CMN_CFG["nodes"][node]["hostname"],
                                            username=CMN_CFG["nodes"][node]["username"],
                                            password=CMN_CFG["nodes"][node]["password"]
                                            )
                self.log.info("Restart the cluster")
                self.ha_obj.restart_cluster(self.node_list[0], self.hlt_list)
            elif CMN_CFG["product_family"] == const.PROD_FAMILY_LC:
                # TODO : restart s3 and motr services
                self.log.info(
                    "Procedure yet to be defined for restarting services in the containers")

        self.log.info("Deleting all buckets/objects created during TC execution")
        resp = self.s3t_obj.bucket_list()
        for bucket_name in resp[1]:
            if self.test_config["test_bucket_prefix"] in bucket_name:
                resp = self.s3t_obj.delete_bucket(bucket_name, force=True)
                assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Teardown Operations")

    def teardown_class(self):
        """Delete test data directory"""
        self.log.info("STARTED: Class Teardown")
        if system_utils.path_exists(self.test_dir_path):
            resp = system_utils.remove_dirs(self.test_dir_path)
            assert_utils.assert_true(resp, f"Unable to remove {self.test_dir_path}")
            self.log.info(
                "removed path: %s, resp: %s",
                self.test_dir_path,
                resp)

    def basic_io_with_parity_check_enabled(self, bucket_name, parity_check: bool = True):
        """
        Set the read verify flag to true
        Restart the S3 and motr services
        """
        self.log.info("STARTED: Basic IO with parity check")
        self.log.info("Parity Check :%s", parity_check)

        if parity_check:
            if CMN_CFG["product_family"] == const.PROD_FAMILY_LR and \
                    CMN_CFG["product_type"] == const.PROD_TYPE_NODE:
                self.log.info(
                    "Step 1: Set the S3_MOTR_IS_READ_VERIFY flag to true on all the nodes")
                for node in range(self.num_nodes):
                    S3H_OBJ.update_s3config(section="S3_MOTR_CONFIG",
                                            parameter=self.test_config["test_basic_io"],
                                            value=True,
                                            host=CMN_CFG["nodes"][node]["hostname"],
                                            username=CMN_CFG["nodes"][node]["username"],
                                            password=CMN_CFG["nodes"][node]["password"]
                                            )
                    self.reset_s3config = True
                self.log.info("Step 2: Restart the cluster")
                self.ha_obj.restart_cluster(self.node_list[0], self.hlt_list)
            elif CMN_CFG["product_family"] == const.PROD_FAMILY_LC:
                # TODO : restart s3 and motr services
                self.log.info(
                    "Procedure yet to be defined for restarting services within containers")
        self.prov_obj.basic_io_write_read_validate(bucket_name=bucket_name, s3t_obj=self.s3t_obj)

    # Ordering maintained for LR2
    # Order - 1  TEST-23540
    # Order - 2  TEST-24673
    # Order - 3  TEST-25016
    # Order - 4  TEST-22901
    # Order - 5  TEST-26959
    @pytest.mark.run(order=6)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26963")
    def test_26963(self):
        """ Basic IO test
            N+K+S: 8+2+0
            CVG's per node : 1
            Data Devices per CVG: 7
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26963")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=7)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26969")
    def test_26969(self):
        """
        S3bench IO workload test
        N+K+S: 8+2+0
        CVG's per node : 1
        Data Devices per CVG: 7
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26969")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 8 : TEST-26960 (deployment test)

    @pytest.mark.run(order=9)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26964")
    def test_26964(self):
        """ Basic IO test
            N+K+S: 3+2+0
            CVG's per node : 2
            Data Devices per CVG: 3
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26964")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=10)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26970")
    def test_26970(self):
        """
        S3bench IO workload test
        N+K+S: 3+2+0
        CVG's per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26970")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 11 : TEST-26973 (Placeholder for degraded test - Marked R2 Future)
    # Order 12 : TEST-26961
    @pytest.mark.run(order=13)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26967")
    def test_26967(self):
        """ Basic IO test
            N+K+S: 8+4+0
            CVG's per node : 2
            Data Devices per CVG: 3
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26967")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=14)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26971")
    def test_26971(self):
        """
        S3bench IO workload test
        N+K+S: 8+4+0
        CVG's per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26971")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 15 : TEST-26974 (Placeholder for degraded test - Marked R2 Future)
    # Order 16 : TEST-26962
    @pytest.mark.run(order=17)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26968")
    def test_26968(self):
        """ Basic IO test
            N+K+S: 10+5+0
            CVG's per node : 2
            Data Devices per CVG: 3
            Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("269638")
        self.basic_io_with_parity_check_enabled(bucket_name)

    @pytest.mark.run(order=18)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-26972")
    def test_26972(self):
        """
        S3bench IO workload test
        N+K+S: 10+5+0
        CVG's per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("26972")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Ordering maintained for K8s based Cortx
    # Order 1 -  TEST-29485 (Deployment test)
    @pytest.mark.run(order=2)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29486")
    def test_29486(self):
        """ Basic IO test
            3 Node Cluster
            Data Pool : NKS : 4+2+0
            Metadata Pool : NKS : 1+2+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29486")
        self.basic_io_with_parity_check_enabled(bucket_name, parity_check=False)

    @pytest.mark.run(order=3)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29487")
    def test_29487(self):
        """ S3bench workload test
            3 Node Cluster
            Data Pool : NKS : 4+2+0
            Metadata Pool : NKS : 1+2+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29487")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 4 -  TEST-29488 (Deployment test)
    @pytest.mark.run(order=5)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29489")
    def test_29489(self):
        """ Basic IO test
            5 Node Cluster
            Data Pool : NKS : 10+5+0
            Metadata Pool : NKS : 1+2+0
            No of CVG per node: 3
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29489")
        self.basic_io_with_parity_check_enabled(bucket_name, parity_check=False)

    @pytest.mark.run(order=6)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29490")
    def test_29490(self):
        """ S3Bench workload test
            5 Node Cluster
            Data Pool : NKS : 10+5+0
            Metadata Pool : NKS : 1+2+0
            No of CVG per node: 3
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29490")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 7 -  TEST-29491 (Deployment test)
    @pytest.mark.run(order=8)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29492")
    def test_29492(self):
        """ Basic IO test
            5 Node Cluster
            Data Pool : NKS : 6+4+0
            Metadata Pool : NKS : 1+2+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29492")
        self.basic_io_with_parity_check_enabled(bucket_name, parity_check=False)

    @pytest.mark.run(order=9)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29493")
    def test_29493(self):
        """  S3bench workload test
            5 Node Cluster
            Data Pool : NKS : 6+4+0
            Metadata Pool : NKS : 1+2+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29493")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 10 -  TEST-29494 (Deployment test)
    @pytest.mark.run(order=11)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29495")
    def test_29495(self):
        """ Basic IO test
            16 Node Cluster
            Data Pool : NKS : 8+8+0
            Metadata Pool : NKS : 1+8+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29495")
        self.basic_io_with_parity_check_enabled(bucket_name, parity_check=False)

    @pytest.mark.run(order=12)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29496")
    def test_29496(self):
        """ S3bench workload test
            16 Node Cluster
            Data Pool : NKS : 8+8+0
            Metadata Pool : NKS : 1+8+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29496")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)

    # Order 13 -  TEST-29497 (Deployment test)
    @pytest.mark.run(order=14)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29498")
    def test_29498(self):
        """ Basic IO test
            16 Node Cluster
            Data Pool : NKS : 16+4+0
            Metadata Pool : NKS : 1+4+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29498")
        self.basic_io_with_parity_check_enabled(bucket_name, parity_check=False)

    @pytest.mark.run(order=15)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29499")
    def test_29499(self):
        """ S3bench workload test
            16 Node Cluster
            Data Pool : NKS : 16+4+0
            Metadata Pool : NKS : 1+4+0
            No of CVG per node: 2
            No of data disk per CVG : Min 1
        """
        bucket_name = self.test_config["test_bucket_prefix"] + str("29499")
        self.prov_obj.io_workload(secret_key=self.secret_key, access_key=self.access_key,
                                  bucket_prefix=bucket_name)
