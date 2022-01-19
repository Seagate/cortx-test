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


"""Continuous Deployment on N nodes config."""
import csv
import distutils.util
import logging
import os

import pytest

from commons import configmanager
from commons.helpers.pods_helper import LogicalNode
from commons.params import LOG_DIR, LATEST_LOG_FOLDER
from config import CMN_CFG
from config import PROV_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

DEPLOY_CFG = configmanager.get_config_wrapper(fpath="config/prov/deploy_config.yaml")


class TestContDeployment:
    """Test Multiple config of N+K+S deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.setup_k8s_cluster_flag = bool(distutils.util.strtobool(os.getenv("setup_k8s_cluster")))
        cls.setup_client_config_flag = \
            bool(distutils.util.strtobool(os.getenv("setup_client_config")))
        cls.cortx_cluster_deploy_flag = \
            bool(distutils.util.strtobool(os.getenv("cortx_cluster_deploy")))
        cls.run_basic_s3_io_flag = bool(distutils.util.strtobool(os.getenv("run_basic_s3_io")))
        cls.run_s3bench_workload_flag = \
            bool(distutils.util.strtobool(os.getenv("run_s3bench_workload")))
        cls.collect_support_bundle = \
            bool(distutils.util.strtobool(os.getenv("collect_support_bundle")))
        cls.destroy_setup_flag = bool(distutils.util.strtobool(os.getenv("destroy_setup")))
        cls.conf = (os.getenv("EC_CONFIG", "")).lower()
        cls.sns = (os.getenv("SNS", "")).split("+")
        cls.dix = (os.getenv("DIX", "")).split("+")
        if cls.sns[0] and cls.dix[0]:
            cls.sns = [int(sns_item) for sns_item in cls.sns]
            cls.dix = [int(dix_item) for dix_item in cls.dix]
            cls.cvg_per_node = int(os.getenv("CVG_PER_NODE"))
            cls.data_disk_per_cvg = int(os.getenv("DATA_DISK_PER_CVG"))
            cls.data_disk_size = os.getenv("DATA_DISK_SIZE",
                                           PROV_CFG["k8s_cortx_deploy"]["data_disk_size"])
            cls.meta_disk_size = os.getenv("METADATA_DISK_SIZE",
                                           PROV_CFG["k8s_cortx_deploy"]["metadata_disk_size"])

        cls.iterations = os.getenv("NO_OF_ITERATIONS")
        cls.raise_jira = bool(distutils.util.strtobool(os.getenv("raise_jira")))
        cls.custom_repo_path = os.getenv("CUSTOM_REPO_PATH",
                                         PROV_CFG["k8s_cortx_deploy"]["git_remote_dir"])
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []

        for node in CMN_CFG["nodes"]:
            vm_name = node["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            if node["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.report_filepath = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
        cls.report_file = os.path.join(cls.report_filepath,
                                       PROV_CFG["k8s_cortx_deploy"]["report_file"])
        logging.info("Report path is %s", cls.report_file)
        if not os.path.isfile(cls.report_file):
            logging.debug("File not exists")
            fields = ['NODES', 'SNS', 'DIX', 'TIME', 'STATUS']
            with open(cls.report_file, 'a')as fptr:
                # writing the fields
                write = csv.writer(fptr)
                write.writerow(fields)
                fptr.close()
            logging.info("File is created %s", cls.report_file)

    @pytest.mark.tags("TEST-N-NODE")
    @pytest.mark.lc
    def test_n(self):
        """
        test to run continuous deployment
        """
        count = int(self.iterations)
        if self.sns[0] and self.dix[0]:
            total_cvg = int(self.cvg_per_node * len(self.worker_node_list))
            self.log.debug("sum of sns is %s total value is %s", sum(self.sns), total_cvg)
            if sum(self.sns) > total_cvg:
                self.log.debug("SNS %s+%s+%s", self.sns[0], self.sns[1], self.sns[2])
                assert False, "The sns value are invalid"
            if self.dix[0] > 1 or self.dix[1] > (len(self.worker_node_list) - 1):
                self.log.debug("The dix %s+%s+%s", self.dix[0], self.dix[1], self.dix[2])
                assert False, "The dix values are invalid"
        if self.conf:
            node = "nodes_{}".format(len(self.worker_node_list))
            self.log.debug("nodes are %s", node)
            config = DEPLOY_CFG[node][self.conf]
            self.sns = []
            self.dix = []
            self.log.debug("SNS and DIX config are %s", config)
            self.sns.append(config['sns_data'])
            self.sns.append(config['sns_parity'])
            self.sns.append(config['sns_spare'])
            self.dix.append(config['dix_data'])
            self.dix.append(config['dix_parity'])
            self.dix.append(config['dix_spare'])
            self.cvg_per_node = config['cvg_per_node']
            self.data_disk_per_cvg = config['data_disk_per_cvg']

        self.log.debug("TEST file setup_k8s_cluster_flag = %s", self.setup_k8s_cluster_flag)
        self.log.debug("TEST file cortx_cluster_deploy_flag = %s", self.cortx_cluster_deploy_flag)
        self.log.debug("TEST file setup_client_config_flag = %s", self.setup_client_config_flag)
        self.log.debug("TEST file run_basic_s3_io_flag = %s", self.run_basic_s3_io_flag)
        self.log.debug("TEST file run_s3bench_workload_flag = %s", self.run_s3bench_workload_flag)
        self.log.debug("TEST file destroy_setup_flag = %s", self.destroy_setup_flag)
        self.log.debug("SNS %s+%s+%s", self.sns[0], self.sns[1], self.sns[2])
        self.log.debug("DIX %s+%s+%s", self.dix[0], self.dix[1], self.dix[2])
        self.log.debug("CVG per node are %s \n Data disk per cvg are %s",
                       self.cvg_per_node, self.data_disk_per_cvg)
        iteration = 0
        while iteration < count:
            self.log.info("The iteration no is %s", (iteration + 1))
            self.deploy_lc_obj.test_deployment(sns_data=self.sns[0],
                                               sns_parity=self.sns[1],
                                               sns_spare=self.sns[2],
                                               dix_data=self.dix[0],
                                               dix_parity=self.dix[1],
                                               dix_spare=self.dix[2],
                                               cvg_count=self.cvg_per_node,
                                               data_disk_per_cvg=self.data_disk_per_cvg,
                                               master_node_list=self.master_node_list,
                                               worker_node_list=self.worker_node_list,
                                               setup_k8s_cluster_flag=self.setup_k8s_cluster_flag,
                                               cortx_cluster_deploy_flag=
                                               self.cortx_cluster_deploy_flag,
                                               setup_client_config_flag=
                                               self.setup_client_config_flag,
                                               run_s3bench_workload_flag=
                                               self.run_s3bench_workload_flag,
                                               run_basic_s3_io_flag=self.run_basic_s3_io_flag,
                                               destroy_setup_flag=self.destroy_setup_flag,
                                               custom_repo_path=self.custom_repo_path,
                                               report_filepath=self.report_file,
                                               data_disk_size=self.data_disk_size,
                                               meta_disk_size=self.meta_disk_size)
            iteration = iteration + 1
