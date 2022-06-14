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

"""Prov Deployment with Redefined Structure."""
import logging
import os
import secrets
from random import SystemRandom

import pytest
from commons import constants
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils
from commons.utils import config_utils
from commons.utils import support_bundle_utils
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG
from config import PROV_CFG
from config import DEPLOY_CFG
from libs.motr import TEMP_PATH
from libs.motr.motr_core_k8s_lib import MotrCoreK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib


class TestProvPodsDeployment:
    """Test Prov Redefined structure deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_obj = ProvDeployK8sCortxLib()
        cls.prov_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.test_cfg = DEPLOY_CFG["mutidata_pod"]
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
        cls.collect_sb = True
        cls.destroy_flag = True
        cls.system_random = SystemRandom()
        cls.m0kv_cfg = config_utils.read_yaml("config/motr/m0kv_test.yaml")

    def teardown_method(self):
        """
        Teardown method
        """
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                            scripts_path=
                                                            self.prov_cfg['k8s_dir'])
        if self.destroy_flag:
            resp = self.deploy_obj.destroy_setup(self.master_node_list[0],
                                                 self.worker_node_list)
            assert_utils.assert_true(resp)

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33218")
    def test_33218(self):
        """
        Test to verify the CONTROL pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (len(self.worker_node_list)),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), 1)
        self.collect_sb = False
        self.destroy_flag = False
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33219")
    def test_33219(self):
        """
        Test to verify the DATA pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", len(self.worker_node_list),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), len(self.worker_node_list))
        self.collect_sb = False
        self.destroy_flag = False
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33220")
    def test_33220(self):
        """
        Test to verify the SERVER pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", len(self.worker_node_list),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.SERVER_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), len(self.worker_node_list))
        self.collect_sb = False
        self.destroy_flag = False
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33221")
    def test_33221(self):
        """
        Test to verify the HA pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (self.num_nodes - 1),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.HA_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), 1)
        self.collect_sb = False
        self.destroy_flag = False
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40373")
    def test_40373(self):
        """
        Test to verify the data-only pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=
                                                            len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (self.num_nodes - 1),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            deployment_type=self.prov_cfg["deployment_type_data"], client_instances=
            self.prov_cfg["data_client_instance"],
            destroy_setup_flag=False)
        self.log.info("Running m0kv tests")
        self.motr_obj = MotrCoreK8s()
        node_pod_dict = self.motr_obj.get_node_pod_dict()
        node = self.system_random.choice(list(node_pod_dict.keys()))
        m0kv_tests = self.m0kv_cfg[1]
        for test in m0kv_tests:
            self.log.info("RUNNING TEST: %s", test)
            cmd_batch = m0kv_tests[test]["batch"]
            for index, cnt in enumerate(cmd_batch):
                self.log.info("Command number: %s", index)
                cmd = cnt["cmnd"]
                param = cnt["params"]
                self.log.info("CMD: %s, PARAMS: %s", cmd, param)
                if cmd == "m0kv":
                    self.motr_obj.kv_cmd(cnt["params"], node, 0)
                else:
                    cmd = f'{cmd} {param}'
                    resp = self.motr_obj.node_obj.send_k8s_cmd(
                        operation="exec",
                        pod=node_pod_dict[node],
                        namespace=constants.NAMESPACE,
                        command_suffix=
                        f"-c {constants.HAX_CONTAINER_NAME} "
                        f"-- {cmd}", decode=True)
                    self.log.info("Resp: %s", resp)
                    assert_utils.assert_not_in("ERROR" or "Error", resp,
                                               "Failed, Please check the log")

        self.log.info("Stop: Verified multiple m0kv operations")
        self.collect_sb = False
        self.destroy_flag = True
        self.log.info("===Test Completed===")

    # pylint: disable=too-many-locals
    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40374")
    def test_40374(self):
        """
        Test to verify the data-only pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=
                                                            len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (self.num_nodes - 1),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            deployment_type=self.prov_cfg["deployment_type_data"],client_instances=
            self.prov_cfg["data_client_instance"], destroy_setup_flag=False)
        self.log.info("STARTED: Verify multiple m0cp/m0cat operation")
        self.motr_obj = MotrCoreK8s()
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
                    self.motr_obj.diff_cmd(infile, outfile, node)
                    self.motr_obj.md5sum_cmd(infile, outfile, node)
                    self.motr_obj.unlink_cmd(object_id, layout, node, client_num)

            self.log.info("Stop: Verify multiple m0cp/cat operation")
        self.collect_sb = False
        self.destroy_flag = True
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-41907")
    def test_41907(self):
        """
        Test to verify the multidata pod being deployed
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        for config_set in config_list:
            if config_set["cvg_count"] == self.test_cfg["test_41907"]["cvg_count"]:
                config = config_set
                self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", len(self.worker_node_list),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config["cvg_count"], data_disk_per_cvg=
            config['data_disk_per_cvg'], master_node_list=self.master_node_list,
            worker_node_list=self.worker_node_list, destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Data Pod on %s worker node is %s", len(self.worker_node_list), len(resp))
        assert_utils.assert_equal(len(resp), len(self.worker_node_list))
        self.collect_sb = False
        self.destroy_flag = True
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-41909")
    def test_41909(self):
        """
        Test to verify the multidata pod being deployed with 2 cvg
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        for config_set in config_list:
            if config_set["cvg_count"] == self.test_cfg["test_41909"]["cvg_count"]:
                config = config_set
                self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", len(self.worker_node_list),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config["cvg_count"], data_disk_per_cvg=
            config['data_disk_per_cvg'], master_node_list=self.master_node_list,
            worker_node_list=self.worker_node_list, destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Data Pod on %s worker node is %s", len(self.worker_node_list), len(resp))
        assert_utils.assert_equal(len(resp), 2*len(self.worker_node_list))
        self.collect_sb = False
        self.destroy_flag = True
        self.log.info("===Test Completed===")
