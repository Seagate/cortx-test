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

# pylint: disable=R0904

"""Failure Domain (k8s based Cortx) Test Suite."""
import logging
import os.path

import pytest

from commons.helpers.pods_helper import LogicalNode
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from config import CMN_CFG
from config import  PROV_CFG
from config import  DEPLOY_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib


class TestMultipleConfDeploy:
    """Test Multiple config of N+K+S deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_obj = ProvDeployK8sCortxLib()
        cls.deploy_conf = PROV_CFG['k8s_cortx_deploy']
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
        cls.collect_sb = True

    def teardown_method(self):
        """
        Teardown method
        """
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                            scripts_path=
                                                            self.deploy_conf['k8s_dir'])
        resp = self.deploy_obj.destroy_setup(self.master_node_list[0],
                                             self.worker_node_list)
        assert_utils.assert_true(resp)

    def multiple_node_deployment(self, node, config):
        """
        This Method is used for deployment of various node count
        and its multiple SNS,DIX configs
        :param: nodes: Its the count of worker nodes in K8S cluster.
        :param: config: Its the config for each node defined
                        in deploy_config.yaml file
        """
        config = DEPLOY_CFG[f'nodes_{node}'][f'config_{config}']
        self.log.info("Running %s N with config %s+%s+%s",
                      node, config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_per_node'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list)
        self.collect_sb = False

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31384")
    def test_31384(self):
        """
        Deployment- 3node config_1
        """
        self.multiple_node_deployment(3, 1)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-29975")
    def test_29975(self):
        """
        Deployment- 3node config_2
        """
        self.multiple_node_deployment(3, 2)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-32790")
    def test_32790(self):
        """
        Deployment- 3node config_3
        """
        self.multiple_node_deployment(3, 3)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31946")
    def test_31946(self):
        """
        Deployment- 3node config_4
        """
        self.multiple_node_deployment(3, 4)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31875")
    def test_31875(self):
        """
        Deployment- 3node config_5
        """
        self.multiple_node_deployment(3, 5)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31385")
    def test_31385(self):
        """
        Deployment- 4node config_1
        """
        self.multiple_node_deployment(4, 1)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31386")
    def test_31386(self):
        """
        Deployment- 4node config_2
        """
        self.multiple_node_deployment(4, 2)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31387")
    def test_31387(self):
        """
        Deployment- 4node config_3
        """
        self.multiple_node_deployment(4, 3)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31388")
    def test_31388(self):
        """
        Deployment- 4node config_4
        """
        self.multiple_node_deployment(4, 4)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31568")
    def test_31568(self):
        """
        Deployment- 4node config_5
        """
        self.multiple_node_deployment(4, 5)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31397")
    def test_31397(self):
        """
        Deployment- 4node config_6
        """
        self.multiple_node_deployment(4, 6)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31389")
    def test_31389(self):
        """
        Deployment- 5node config_1
        """
        self.multiple_node_deployment(5, 1)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31390")
    def test_31390(self):
        """
        Deployment- 5node config_2
        """
        self.multiple_node_deployment(5, 2)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31391")
    def test_31391(self):
        """
        Deployment- 5node config_3
        """
        self.multiple_node_deployment(5, 3)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31392")
    def test_31392(self):
        """
        Deployment- 5node config_4
        """
        self.multiple_node_deployment(5, 4)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31393")
    def test_31393(self):
        """
        Deployment- 5node config_5
        """
        self.multiple_node_deployment(5, 5)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31394")
    def test_31394(self):
        """
        Deployment- 5node config_6
        """
        self.multiple_node_deployment(5, 6)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31399")
    def test_31399(self):
        """
        Deployment- 6node config_1
        """
        self.multiple_node_deployment(6, 1)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31396")
    def test_31396(self):
        """
        Deployment- 6node config_2
        """
        self.multiple_node_deployment(6, 2)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31395")
    def test_31395(self):
        """
        Deployment- 6node config_3
        """
        self.multiple_node_deployment(6, 3)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31398")
    def test_31398(self):
        """
        Deployment- 6node config_4
        """
        self.multiple_node_deployment(6, 4)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31400")
    def test_31400(self):
        """
        Deployment- 6node config_5
        """
        self.multiple_node_deployment(6, 5)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31401")
    def test_31401(self):
        """
        Deployment- 6node config_6
        """
        self.multiple_node_deployment(6, 6)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31402")
    def test_31402(self):
        """
        Deployment- 7node config_1
        """
        self.multiple_node_deployment(7, 1)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31403")
    def test_31403(self):
        """
        Deployment- 7node config_2
        """
        self.multiple_node_deployment(7, 2)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31404")
    def test_31404(self):
        """
        Deployment- 7node config_3
        """
        self.multiple_node_deployment(7, 3)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31405")
    def test_31405(self):
        """
        Deployment- 7node config_4
        """
        self.multiple_node_deployment(7, 4)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31406")
    def test_31406(self):
        """
        Deployment- 7node config_5
        """
        self.multiple_node_deployment(7, 5)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31412")
    def test_31412(self):
        """
        Deployment- 7node config_6
        """
        self.multiple_node_deployment(7, 6)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31414")
    def test_31414(self):
        """
        Deployment- 8node config_1
        """
        self.multiple_node_deployment(8, 1)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31415")
    def test_31415(self):
        """
        Deployment- 8node config_2
        """
        self.multiple_node_deployment(8, 2)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31416")
    def test_31416(self):
        """
        Deployment- 8node config_3
        """
        self.multiple_node_deployment(8, 3)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31417")
    def test_31417(self):
        """
        Deployment- 8node config_4
        """
        self.multiple_node_deployment(8, 4)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31418")
    def test_31418(self):
        """
        Deployment- 8node config_5
        """
        self.multiple_node_deployment(8, 5)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31419")
    def test_31419(self):
        """
        Deployment- 8node config_6
        """
        self.multiple_node_deployment(8, 6)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31423")
    def test_31423(self):
        """
        Deployment- 9node config_1
        """
        self.multiple_node_deployment(9, 1)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-32794")
    def test_32794(self):
        """
        Deployment- 9node config_2
        """
        self.multiple_node_deployment(9, 2)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31424")
    def test_31424(self):
        """
        Deployment- 9node config_3
        """
        self.multiple_node_deployment(9, 3)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31421")
    def test_31421(self):
        """
        Deployment- 9node config_4
        """
        self.multiple_node_deployment(9, 4)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31420")
    def test_31420(self):
        """
        Deployment- 9node config_5
        """
        self.multiple_node_deployment(9, 5)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31422")
    def test_31422(self):
        """
        Deployment- 9node config_6
        """
        self.multiple_node_deployment(9, 6)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31439")
    def test_31439(self):
        """
        Deployment- 10node config_1
        """
        self.multiple_node_deployment(10, 1)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31565")
    def test_31565(self):
        """
        Deployment- 10node config_2
        """
        self.multiple_node_deployment(10, 2)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31566")
    def test_31566(self):
        """
        Deployment- 10node config_3
        """
        self.multiple_node_deployment(10, 3)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31567")
    def test_31567(self):
        """
        Deployment- 10node config_4
        """
        self.multiple_node_deployment(10, 4)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31571")
    def test_31571(self):
        """
        Deployment- 10node config_5
        """
        self.multiple_node_deployment(10, 5)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31569")
    def test_31569(self):
        """
        Deployment- 10node config_6
        """
        self.multiple_node_deployment(10, 6)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31570")
    def test_31570(self):
        """
        Deployment- 10node config_7
        """
        self.multiple_node_deployment(10, 7)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31938")
    def test_31938(self):
        """
        Deployment- 11node config_1
        """
        self.multiple_node_deployment(11, 1)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31939")
    def test_31939(self):
        """
        Deployment- 11node config_2
        """
        self.multiple_node_deployment(11, 2)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31940")
    def test_31940(self):
        """
        Deployment- 11node config_3
        """
        self.multiple_node_deployment(11, 3)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31936")
    def test_31936(self):
        """
        Deployment- 11node config_4
        """
        self.multiple_node_deployment(11, 4)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31941")
    def test_31941(self):
        """
        Deployment- 11node config_5
        """
        self.multiple_node_deployment(11, 5)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31942")
    def test_31942(self):
        """
        Deployment- 11node config_6
        """
        self.multiple_node_deployment(11, 6)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31788")
    def test_31788(self):
        """
        Deployment- 12node config_1
        """
        self.multiple_node_deployment(12, 1)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31789")
    def test_31789(self):
        """
        Deployment- 12node config_2
        """
        self.multiple_node_deployment(12, 2)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31790")
    def test_31790(self):
        """
        Deployment- 12node config_3
        """
        self.multiple_node_deployment(12, 3)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31791")
    def test_31791(self):
        """
        Deployment- 12node config_4
        """
        self.multiple_node_deployment(12, 4)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31792")
    def test_31792(self):
        """
        Deployment- 12node config_5
        """
        self.multiple_node_deployment(12, 5)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31793")
    def test_31793(self):
        """
        Deployment- 12node config_6
        """
        self.multiple_node_deployment(12, 6)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31794")
    def test_31794(self):
        """
        Deployment- 12node config_7
        """
        self.multiple_node_deployment(12, 7)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31795")
    def test_31795(self):
        """
        Deployment- 12node config_8
        """
        self.multiple_node_deployment(12, 8)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31943")
    def test_31943(self):
        """
        Deployment- 13node config_1
        """
        self.multiple_node_deployment(13, 1)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31944")
    def test_31944(self):
        """
        Deployment- 13node config_2
        """
        self.multiple_node_deployment(13, 2)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31945")
    def test_31945(self):
        """
        Deployment- 13node config_3
        """
        self.multiple_node_deployment(13, 3)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31934")
    def test_31934(self):
        """
        Deployment- 13node config_4
        """
        self.multiple_node_deployment(13, 4)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-32793")
    def test_32793(self):
        """
        Deployment- 13node config_5
        """
        self.multiple_node_deployment(13, 5)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31947")
    def test_31947(self):
        """
        Deployment- 13node config_6
        """
        self.multiple_node_deployment(13, 6)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31948")
    def test_31948(self):
        """
        Deployment- 14node config_1
        """
        self.multiple_node_deployment(14, 1)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31949")
    def test_31949(self):
        """
        Deployment- 14node config_2
        """
        self.multiple_node_deployment(14, 2)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31935")
    def test_31935(self):
        """
        Deployment- 14node config_3
        """
        self.multiple_node_deployment(14, 3)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31950")
    def test_31950(self):
        """
        Deployment- 14node config_4
        """
        self.multiple_node_deployment(14, 4)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31951")
    def test_31951(self):
        """
        Deployment- 14node config_5
        """
        self.multiple_node_deployment(14, 5)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31952")
    def test_31952(self):
        """
        Deployment- 14node config_6
        """
        self.multiple_node_deployment(14, 6)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31572")
    def test_31572(self):
        """
        Deployment- 15node config_1
        """
        self.multiple_node_deployment(15, 1)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31573")
    def test_31573(self):
        """
        Deployment- 15node config_2
        """
        self.multiple_node_deployment(15, 2)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31574")
    def test_31574(self):
        """
        Deployment- 15node config_3
        """
        self.multiple_node_deployment(15, 3)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31575")
    def test_31575(self):
        """
        Deployment- 15node config_4
        """
        self.multiple_node_deployment(15, 4)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31576")
    def test_31576(self):
        """
        Deployment- 15node config_5
        """
        self.multiple_node_deployment(15, 5)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31577")
    def test_31577(self):
        """
        Deployment- 15node config_6
        """
        self.multiple_node_deployment(15, 6)

    @pytest.mark.lc
    @pytest.mark.twentyfive_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40500")
    def test_40500(self):
        """
        Deployment- 25node config_1
        """
        self.multiple_node_deployment(25, 1)

    @pytest.mark.lc
    @pytest.mark.thirtysix_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40502")
    def test_40502(self):
        """
        Deployment- 36node config_1
        """
        self.multiple_node_deployment(36, 1)
