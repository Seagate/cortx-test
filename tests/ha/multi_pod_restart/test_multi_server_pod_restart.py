#!/usr/bin/python  # pylint: disable=too-many-instance-attributes
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
HA test suite for Multiple server Pod restart
"""

import logging
import secrets
import time

import pytest

from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from config import HA_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.csm.csm_interface import csm_api_factory

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestMultiServerPodRestart:
    """
    Test suite for Multiple Server Pod Restart
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = []
        cls.password = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.csm_obj = csm_api_factory("rest")
        cls.s3_clean = cls.test_prefix = cls.test_prefix_deg = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.qvalue = cls.kvalue = cls.nvalue = None
        cls.set_type = cls.set_name = cls.last_pod = cls.num_replica = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()
        cls.rest_obj = S3AccountOperations()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
                cls.hlth_master_list.append(Health(hostname=cls.host,
                                                   username=cls.username[node],
                                                   password=cls.password[node]))
            else:
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        resp = cls.ha_obj.calculate_multi_value(cls.csm_obj, len(cls.node_worker_list))
        assert_utils.assert_true(resp[0], resp[1])
        cls.qvalue = resp[1]
        LOGGER.info("Getting K value for the cluster")
        resp = cls.csm_obj.get_sns_value()
        if not resp:
            assert_utils.assert_true(False, "Could not retrieve SNS values of cluster")
        LOGGER.info("K value for the cluster is: %s", resp[1])
        cls.kvalue = resp[1]
        cls.nvalue = len(cls.node_worker_list)
        LOGGER.info("N value for the given cluster is: %s", cls.nvalue)

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restore_pod = False
        self.s3_clean = dict()
        self.s3acc_name = f"ha_s3acc_{int(time.perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("Get server pod with prefix %s", const.SERVER_POD_NAME_PREFIX)
        sts_dict = self.node_master_list[0].get_sts_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        LOGGER.debug("%s Statefulset: %s", const.SERVER_POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        self.last_pod = sts_dict[sts][-1]
        self.set_type, self.set_name = self.node_master_list[0].get_set_type_name(
            pod_name=self.last_pod)
        resp = self.node_master_list[0].get_num_replicas(self.set_type, self.set_name)
        assert_utils.assert_true(resp[0], resp)
        self.num_replica = int(resp[1])
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup,
                                                           "num_replica": self.num_replica,
                                                           "set_name": self.set_name})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0],
                                               HA_CFG["common_params"]["60sec_delay"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45588")
    def test_read_after_multi_server_pods_restart(self):
        """
        Verify READs after random between K-1 to N-1 server pods restart
        """
        LOGGER.info("Started: Verify READs after random between K-1 to N-1 server pods restart.")
        LOGGER.info("Completed: Verify READs after random between K-1 to N-1 server pods restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45589")
    def test_read_during_multi_server_pods_restart(self):
        """
        Verify READs in loop during random between K-1 to N-1 server pod restart
        """
        LOGGER.info("Started: Verify READs in loop during random between K-1 to N-1 server pod "
                    "restart.")
        LOGGER.info("Completed: Verify READs in loop during random between K-1 to N-1 server pod "
                    "restart.")
