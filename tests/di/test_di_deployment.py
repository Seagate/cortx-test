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

"""DI tests with multiple EC deployment (k8s based Cortx) Test Suite."""
from __future__ import division

import logging
import math
import time

import pytest

from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib


class TestDIDeployment:
    """Test DI with multiple Durability Config"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.di_err_lib = DIErrorDetection()

    @staticmethod
    def get_durability_config(num_nodes) -> list:
        """
        Get 3 EC configs based on the number of nodes given as args..
        EC config will be calculated considering CVG as 1,2,3.
        param: num_nodes : Number of nodes
        return : list of configs. (List of Dictionary)
        """
        config_list = []
        for i in range(1, 4):
            config = {}
            cvg_count = i
            sns_total = num_nodes * cvg_count
            sns_data = math.ceil(sns_total / 2)
            sns_data = sns_data + i
            if sns_data >= sns_total:
                sns_data = sns_data - 1
            sns_parity = sns_total - sns_data

            dix_parity = math.ceil((num_nodes + cvg_count) / 2) + i
            if dix_parity > (num_nodes - 1):
                dix_parity = num_nodes - 1

            config["sns_data"] = sns_data
            config["sns_parity"] = sns_parity
            config["sns_spare"] = 0
            config["dix_data"] = 1
            config["dix_parity"] = dix_parity
            config["dix_spare"] = 0
            config["data_disk_per_cvg"] = 0  # To utilize max possible on the available system
            config["cvg_count"] = i
            config_list.append(config)
        return config_list

    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-22496')
    def test_22496(self):
        """
        Test Checksum validation for multiple Erasure Coding scheme.
        """
        num_nodes = len(self.worker_node_list)
        self.log.info("Number of worker nodes : %s",num_nodes)
        config_list = self.get_durability_config(num_nodes)
        for config in config_list:
            self.log.info("Perform Deployment with config SNS (%s+%s+%s) and DIX (%s+%s+%s)",
                          config["sns_data"], config["sns_parity"], config["sns_spare"],
                          config["dix_data"], config["dix_parity"], config["dix_spare"])

            self.deploy_lc_obj.test_deployment(sns_data=config["sns_data"],
                                               sns_parity=config["sns_parity"],
                                               sns_spare=config["sns_spare"],
                                               dix_data=config["dix_data"],
                                               dix_parity=config["dix_parity"],
                                               dix_spare=config["dix_spare"],
                                               cvg_count=config["cvg_count"],
                                               data_disk_per_cvg=config["data_disk_per_cvg"],
                                               master_node_list=self.master_node_list,
                                               worker_node_list=self.worker_node_list,
                                               setup_k8s_cluster_flag=True,
                                               cortx_cluster_deploy_flag=True,
                                               setup_client_config_flag=True,
                                               run_basic_s3_io_flag=False,
                                               run_s3bench_workload_flag=False,
                                               destroy_setup_flag=False)

            self.log.info("Validate if Default values are set for Data Integrity")
            resp = self.di_err_lib.validate_default_config()
            self.log.debug("resp : %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_false(resp[1], "Default values for Data Integrity flags not set")

            access_key, secret_key = S3H_OBJ.get_local_keys()
            s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)
            self.log.info("Step to Perform basic IO operations")
            bucket_name = "bucket-" + str(int(time.time()))
            self.deploy_lc_obj.basic_io_write_read_validate(s3t_obj, bucket_name)

            self.log.info("Step to Perform S3bench IO")
            bucket_name = "bucket-" + str(int(time.time()))
            self.deploy_lc_obj.io_workload(access_key=access_key, secret_key=secret_key,
                                           bucket_prefix=bucket_name)

            self.log.info("Step to Destroy setup")
            resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0], self.worker_node_list)
            assert_utils.assert_true(resp[0], resp[1])
