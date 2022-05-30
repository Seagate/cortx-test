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

"""UnitTest module to test None Health Check Function helper."""

import logging
from random import SystemRandom
import time
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG
from libs.s3 import S3H_OBJ


class TestNodeHealthHelper:
    """Test Node Health Check class."""

    @classmethod
    def setup_class(cls) -> None:
        """Suite level setup."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Test suite level setup started.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.system_random = SystemRandom()
        cls.node_list = []
        cls.host_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.restored = True

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.uname, password=cls.passwd))
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname,
                                       password=cls.passwd))
        cls.log.info("ENDED: Test suite level setup completed.")

    def setup_method(self):
        """Test case setup."""
        self.log.info("START: Test case setup started.")
        self.log.info("Check if cluster is in clean state")
        res = self.hlt_list[0].check_node_health()
        self.log.info("check_node_health resp = %s", res)
        if not res[0]:
            res = self.restart_cluster()
            assert_utils.assert_true(res[0], res[1])
        self.log.info("END: Test case setup completed.")

    def teardown_method(self):
        """Test case teardown."""
        self.log.info("START: Test case teardown started.")
        if not self.restored:
            res = self.restart_cluster()
            assert_utils.assert_true(res[0], res[1])
        self.log.info("END: Test case teardown completed.")

    def restart_cluster(self, node: str = "--all"):
        """Restart Cluster Method."""
        self.log.info("Restarting cluster stop/start/cleanup")
        resp = self.node_list[0].execute_cmd(
            f"cortx cluster stop {node}", read_lines=True, exc=False)
        self.log.info("cortx cluster stop resp = %s", resp[0])
        time.sleep(120)
        resp = self.node_list[0].execute_cmd(
            f"cortx cluster start {node}", read_lines=True, exc=False)
        time.sleep(120)
        self.log.info("cortx cluster start resp = %s", resp[0])
        resp = self.node_list[0].execute_cmd(
            "pcs resource cleanup --all", read_lines=True, exc=False)
        time.sleep(120)
        self.log.info("pcs resource cleanup --all resp = %s", resp[0])
        resp = self.hlt_list[0].check_node_health()
        self.log.info("check_node_health resp = %s", resp)
        return resp

    def test_pcs_not_clean(self) -> None:
        """Test pcs status not clean test."""
        self.log.info("START: Test pcs status not clean test scenario.")
        self.restored = False
        service_stp = 'hax-clone'
        self.log.info(
            "Executing pcs resource disable %s on %s",
            service_stp,
            self.srvnode_list[0])
        self.node_list[0].execute_cmd(
            f"pcs resource disable {service_stp}",
            read_lines=True,
            exc=False)
        time.sleep(10)

        self.log.info(
            "Executing check_node_health on %s",
            self.srvnode_list[0])
        res = self.hlt_list[0].check_node_health()
        self.log.info("check_node_health resp = %s", res)
        assert_utils.assert_false(res[0], res[1])

        self.log.info(
            "Executing pcs resource enable %s on %s",
            service_stp,
            self.srvnode_list[0])
        self.node_list[0].execute_cmd(
            f"pcs resource enable {service_stp}",
            read_lines=True,
            exc=False)
        time.sleep(10)

        res = self.hlt_list[0].check_node_health()
        self.log.info("check_node_health resp = %s", res)
        if not res[0]:
            res = self.restart_cluster()
            assert_utils.assert_true(res[0], res[1])
        self.restored = True
        self.log.info("END: Tested pcs status not clean test scenario.")

    def test_hctl_not_clean(self) -> None:
        """Test hctl status not clean test"""
        self.log.info("START: Test hctl status not clean scenario.")
        self.log.info("Get s3server fids.")
        self.restored = False
        _resp, get_s3server_fids = S3H_OBJ.get_s3server_fids()
        self.log.info("Get s3server fids. resp = %s", get_s3server_fids)

        for index, hlt_obj in enumerate(self.hlt_list):
            self.log.info(
                "Executing systemctl stop %s on %s",
                get_s3server_fids[index],
                self.srvnode_list[index])
            self.node_list[index].execute_cmd(
                f"systemctl stop {get_s3server_fids[index]}",
                read_lines=True,
                exc=False)
            res = hlt_obj.check_node_health()
            self.log.info("check_node_health resp = %s", res)
            assert_utils.assert_false(res[0], res[1])
            self.log.info(
                "Executing systemctl start %s on %s",
                get_s3server_fids[index],
                self.srvnode_list[index])
            self.node_list[index].execute_cmd(
                f"systemctl start {get_s3server_fids[index]}",
                read_lines=True,
                exc=False)

        res = self.hlt_list[0].check_node_health()
        self.log.info("check_node_health resp = %s", res)
        if not res[0]:
            res = self.restart_cluster()
            assert_utils.assert_true(res[0], res[1])
        self.restored = True
        self.log.info("END: Tested hctl status not clean scenario.")

    def test_pcs_cluster_stoped(self) -> None:
        """Test pcs cluster stopped test"""
        self.log.info("START: Test pcs/hctl cluster stopped scenario.")

        node = "srvnode-1.data.private"
        self.restored = False
        self.log.info("Executing pcs cluster stop on %s", node)
        self.node_list[0].execute_cmd(
            f"pcs cluster stop {node}",
            read_lines=True,
            exc=False)
        time.sleep(60)
        for index, hlt_obj in enumerate(self.hlt_list):
            res = hlt_obj.check_node_health()
            self.log.info("check_node_health resp = %s", res)
            if index:
                assert_utils.assert_false(res[0], res[1])
            else:
                assert_utils.assert_in(
                    "Failed to get", res[1], "Cluster response is not as expected.")

        self.log.info("Executing pcs cluster start on %s", node)
        self.node_list[0].execute_cmd(
            "pcs cluster start --all",
            read_lines=True,
            exc=False)
        time.sleep(150)
        self.log.info("Executing pcs resource cleanup on --all")
        self.node_list[0].execute_cmd(
            "pcs resource cleanup --all",
            read_lines=True,
            exc=False)
        time.sleep(60)

        res = self.hlt_list[0].check_node_health()
        self.log.info("check_node_health resp = %s", res)
        if not res[0]:
            res = self.restart_cluster()
            assert_utils.assert_true(res[0], res[1])
        self.restored = True
        self.log.info("END: Tested pcs/hctl cluster stopped scenario.")
