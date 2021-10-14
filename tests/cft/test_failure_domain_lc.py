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

"""Failure Domain LC Test Suite."""
import logging
import os
from multiprocessing import Pool

import pytest

from commons.utils import system_utils
from libs.prov.prov_lc_deploy import ProvDeployLCLib
from commons import commands as common_cmd, pswdmanager
from commons.utils import assert_utils
from config import CMN_CFG,HA_CFG

class TestFailureDomainLC:
    """Test Failure Domain LC (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.git_id = os.getenv("GIT_ID")
        cls.git_token = os.getenv("GIT_PASSWORD")
        #TODO: Update Docker credentials
        cls.docker_username = os.getenv("DOCKER_USERNAME")
        cls.docker_password = os.getenv("DOCKER_PASSWORD")
        cls.vm_username = os.getenv("QA_VM_POOL_ID", pswdmanager.decrypt(HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv("QA_VM_POOL_PASSWORD", pswdmanager.decrypt(HA_CFG["vm_params"]["passwd"]))
        cls.deploy_lc_obj = ProvDeployLCLib()
        cls.host_list = []
        for node in range(len(CMN_CFG["nodes"])):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)

    def setup_method(self):
        """Revert the VM's before starting the deployment tests"""
        #Assuming the last captured snapshot is after the k8's deployment
        self.log.info("Reverting all the VM before deployment")
        with Pool(len(CMN_CFG["nodes"])) as proc_pool:
            proc_pool.map(self.revert_vm_snapshot, self.host_list)

    def revert_vm_snapshot(self, host):
        """Revert VM snapshot
           host: VM name """
        resp = system_utils.execute_cmd(cmd=common_cmd.CMD_VM_REVERT.format(
            self.vm_username, self.vm_password, host), read_lines=True)

        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.run(order=1)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29485")
    def test_29485(self):
        """
        Intel ISA  - 3node - SNS- 4+2+0 Deployment
        """
        #TODO : Retrieve solution file
        self.deploy_lc_obj.deploy_cortx_cluster("solution.yaml", self.docker_username,
                                                self.docker_password, self.git_id, self.git_token)
