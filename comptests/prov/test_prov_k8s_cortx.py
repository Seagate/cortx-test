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

"""Provisioner Component level test cases for CORTX deployment in k8s environment."""

import logging
import time
import pytest

from commons import configmanager
from commons import constants as common_const
from commons import commands
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import PROV_CFG
from config import PROV_TEST_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_test_lib import S3TestLib

DEPLOY_CFG = configmanager.get_config_wrapper(fpath="config/prov/deploy_config.yaml")

LOGGER = logging.getLogger(__name__)

SECRETS_FILES_LIST = ["s3_auth_admin_secret", "openldap_admin_secret", "kafka_admin_secret",
                      "csm_mgmt_admin_secret", "csm_auth_admin_secret", "consul_admin_secret",
                      "common_admin_secret"]
PVC_LIST = ["cluster.conf", "config", "consul_conf", "hare", "log", "motr", "rgw_s3", "solution"]

class TestProvK8Cortx:

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        cls.s3t_obj = S3TestLib()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.ha_obj = HAK8s()
        cls.dir_path = common_const.K8S_SCRIPTS_PATH
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.local_sol_path = common_const.LOCAL_SOLUTION_PATH
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.master_node_list.append(node_obj)
                cls.master_node_obj.execute_cmd(cmd=commands.SET_NAMESPACE.format
                                        (common_const.NAMESPACE),read_lines=True)
            else:
                cls.worker_node_list.append(node_obj)
        LOGGER.info("Done: Setup operations finished.")

    # pylint: disable=R0915
    # pylint: disable=too-many-arguments,too-many-locals
    def single_node_deployment(self, sns_data,
                        sns_parity,sns_spare, dix_data,
                        dix_parity, dix_spare,
                        cvg_count, data_disk_per_cvg, master_node_list,
                        worker_node_list):
        """
        This method is used for deployment with various config on One node
        param: sns_data
        param: sns_parity
        param: sns_spare
        param: dix_data
        param: dix_parity
        param: dix_spare
        param: cvg_count
        param: data disk per cvg
        param: master node obj list
        """
        LOGGER.info("STARTED: {%s node (SNS-%s+%s+%s) (DIX-%s+%s+%s) "
                    "k8s based Cortx Deployment", len(worker_node_list),
                    sns_data, sns_parity, sns_spare, dix_data, dix_parity, dix_spare)

        LOGGER.info("Step to Download solution file template")
        path = self.deploy_lc_obj.checkout_solution_file(self.deploy_lc_obj.git_script_tag)
        print(path)
        LOGGER.info("Step to Update solution file template")
        resp = self.deploy_lc_obj.update_sol_yaml(worker_obj=master_node_list, filepath=path,
                                    cortx_image=self.deploy_lc_obj.cortx_image,
                                    sns_data=sns_data, sns_parity=sns_parity,
                                    sns_spare=sns_spare, dix_data=dix_data,
                                    dix_parity=dix_parity, dix_spare=dix_spare,
                                    cvg_count=cvg_count, data_disk_per_cvg=data_disk_per_cvg,
                                    size_data_disk="20Gi", size_metadata="20Gi",
                                    glusterfs_size="20Gi")
        assert_utils.assert_true(resp[0], "Failure updating solution.yaml")
        with open(resp[1]) as file:
            LOGGER.info("The solution yaml file is %s\n", file)
        sol_file_path = resp[1]
        system_disk_dict = resp[2]
        LOGGER.info("Step to Perform Cortx Cluster Deployment")
        resp = self.deploy_lc_obj.deploy_cortx_cluster(sol_file_path, master_node_list,
                                            master_node_list, system_disk_dict,
                                            self.deploy_lc_obj.git_script_tag)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cortx Cluster Deployed Successfully")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-30239")
    def test_30239(self):
        """
        Verify N-Node Cortx Stack Deployment in K8s environment.
        """
        LOGGER.info("STARTED: N-Node k8s based Cortx Deployment.")
        LOGGER.info("Step 1: Perform k8s Cluster Deployment.")
        resp = self.deploy_lc_obj.deploy_cortx_k8s_re_job(self.master_node_list,
                                                          self.worker_node_list)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Cluster Deployment completed.")
        LOGGER.info("Step 2: Check Pods Status.")
        path = self.deploy_cfg["k8s_dir"]
        for node in self.master_node_list:
            resp = self.deploy_lc_obj.validate_cluster_status(node, path)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2: Done.")
        LOGGER.info("Step 3: Check s3 server status.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")
        LOGGER.info("ENDED: Test Case Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-29269")
    def test_29269(self):
        """
        Verify if all the third party services (kafka, consul, openldap) pods are running.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check third party services Pods status.")
        resp = ProvDeployK8sCortxLib.check_pods_status(self.master_node_obj)
        assert_utils.assert_true(resp)
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28387")
    def test_28387(self):
        """
        Verify if components secrets are copied inside the POD.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check secret files are copied inside the POD.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0], data_pod_list[1])
        LOGGER.info("Step 2: Check secret files are copied to each data pod.")
        secrets_path = "ls /etc/cortx/solution/secret/"
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(cmd=commands.K8S_POD_INTERACTIVE_CMD.
                                                    format(pod_name, secrets_path),
                                                    read_lines=True)
            assert_utils.assert_is_not_none(resp)
            for secret in resp:
                secret = secret.split("\n")
                assert_utils.assert_in(secret[0], SECRETS_FILES_LIST)
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28437")
    def test_28437(self):
        """
        Verify machine id is unique in every POD.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check every machine id is unique in each pod.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        LOGGER.info("Step 2: Check machine id is unique in every pod.")
        machine_id_list = []
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.K8S_POD_INTERACTIVE_CMD.format(pod_name, 'cat /etc/machine-id'),
                read_lines=True)
            machine_id_list.append(resp[0])
        assert_utils.assert_true(len(machine_id_list) == len(set(machine_id_list)))
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28384")
    def test_28384(self):
        """
        Verify files are copied and accessible to containers through shared Persistent volume.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check files are copied and accessible to containers.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        time.sleep(100)
        assert_utils.assert_true(data_pod_list[0])
        LOGGER.info("Step 2: Check files are copied and accessible to containers.")
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.K8S_POD_INTERACTIVE_CMD.format(pod_name, 'ls /etc/cortx'),
                read_lines=True)
            LOGGER.info("Output %s", resp)
            assert_utils.assert_is_not_none(resp)
            for out in resp:
                out = out.split("\n")
                LOGGER.info(out[0])
                assert_utils.assert_in(out[0], PVC_LIST)
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28351")
    def test_28351(self):
        """
        Verify cortx_setup commands are running inside Provisioner Container.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check cortx_setup commands are running inside Provisioner Container.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        LOGGER.info("Step 2: Check cortx_setup commands are running inside Provisioner Container.")
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.K8S_POD_INTERACTIVE_CMD.format(pod_name, 'cortx_setup --help'),
                read_lines=True)
            assert_utils.assert_is_not_none(resp)
            for output in resp:
                output = output.split("\n")
                resp = str(resp)
                assert_utils.assert_not_in(resp, "error")
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-29114")
    def test_29114(self):
        """
        Verify single Provisioner Container pod get deployed on each VM/node.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check single Provisioner Container pod get deployed on each VM/node.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        data_pod_count = (data_pod_list[1:])
        LOGGER.info("Step 2: Get all running data nodes from cluster.")
        resp = self.master_node_obj.execute_cmd(cmd=commands.CMD_GET_NODE, read_lines=True)
        node_list = resp[1:]
        LOGGER.info("Identify pods and nodes are equal.")
        assert_utils.assert_true(len(list(data_pod_count[0])) == len(node_list))
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28436")
    def test_28436(self):
        """
        Verify cluster id from cluster.yaml matches with cluster.conf file.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        cluster_yaml_cmd = "cat " + self.deploy_cfg["cluster_yaml_path"] + " | grep id"
        cluster_conf_cmd = "cat " + self.deploy_cfg["cluster_conf_path"] + " | grep cluster_id"
        LOGGER.info("Step 2: Fetch Cluster ID from cluster.yaml and cluster.conf.")
        for pod_name in data_pod_list[1]:
            cluster_id_yaml = self.master_node_obj.execute_cmd(cmd=commands.
                                                               K8S_POD_INTERACTIVE_CMD.
                                                               format(pod_name,
                                                                      cluster_yaml_cmd),
                                                               read_lines=True)
            assert_utils.assert_is_not_none(cluster_id_yaml)
            cluster_id_yaml = cluster_id_yaml[0].split("\n")[0].strip().split(":")[1].strip()
            cluster_id_conf = self.master_node_obj.execute_cmd(cmd=commands.
                                                               K8S_POD_INTERACTIVE_CMD.
                                                               format(pod_name,
                                                                      cluster_conf_cmd),
                                                               read_lines=True)
            assert_utils.assert_is_not_none(cluster_id_conf)
            cluster_id_conf = cluster_id_conf[0].split("\n")[0].strip().split(":")[1].strip()
            assert_utils.assert_exact_string(cluster_id_yaml, cluster_id_conf,
                                             "Cluster ID does not match in both files..")
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.singlenode
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32940")
    def test_32940(self):
        """
        Verify cortx cluster shutdown command.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Check whether all pods are online")
        resp1 = self.ha_obj.check_pod_status(self.master_node_list[0])
        assert_utils.assert_true(resp1[0], resp1[1])
        LOGGER.info("Executing cortx cluster shutdown command.")
        LOGGER.info("Step 2: Check whether cluster shutdown command ran successfully.")
        resp = self.ha_obj.cortx_stop_cluster(self.master_node_list[0],
                                              dir_path=self.prov_deploy_cfg["git_remote_path"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Check whether data and control pods are not present")
        resp2 = self.ha_obj.check_pod_status(self.master_node_list[0])
        LOGGER.info(resp2)
        data = []
        data1 = []
        for i in resp1[1]:
            data.append(i.split(" ")[0])
        for i in resp2[1]:
            data1.append(i.split(" ")[0])
        set_difference = set(data) - set(data1)
        list_difference = list(set_difference)
        # LOGGER.info("Pods which are not present after shut_down command ran are"
        # + str(list_difference))
        LOGGER.info(list_difference)
        is_same = resp1[1] == resp2[1]
        assert_utils.assert_false(is_same)
        LOGGER.info("Step 4: Check the cluster status and start the cluster "
                    "in case its still down.")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0],
                                                dir_path=self.prov_deploy_cfg["git_remote_path"])
        if not resp[0]:
            LOGGER.info("Cluster not in good state, trying to restart it.")
            resp = self.ha_obj.cortx_start_cluster(self.master_node_list[0],
                                                   dir_path=self.prov_deploy_cfg["git_remote_path"])
            time.sleep(100)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and running.")
        LOGGER.info("Step 5: Cluster is back online.")
        LOGGER.info("Test Completed.")

    @pytest.mark.prov_sanity
    @pytest.mark.singlenode
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32939")
    def test_32939(self):
        """
        Verify cortx cluster restart command.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Check whether cluster shutdown command ran successfully.")
        resp = self.ha_obj.cortx_stop_cluster(self.master_node_list[0],
                                              dir_path=self.prov_deploy_cfg["git_remote_path"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Check the cluster status and start the cluster "
                    "in case its still down.")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0],
                                                dir_path=self.prov_deploy_cfg["git_remote_path"])
        if not resp[0]:
            LOGGER.info("Cluster not in good state, trying to restart it.")
        LOGGER.info("Executing cortx cluster restart command.")
        LOGGER.info("Step 3: Check whether cluster restart command ran successfully.")
        resp = self.ha_obj.cortx_start_cluster(self.master_node_list[0],
                                               dir_path=self.prov_deploy_cfg["git_remote_path"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and running.")
        time.sleep(100)
        LOGGER.info("Step 4: Checking whether all CORTX Data pods have been restarted.")
        resp = self.ha_obj.check_pod_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Test Completed.")

    @pytest.mark.singlenode
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32640")
    def test_32640(self):
        """
        Deployment- 1node config_1
        """
        config = DEPLOY_CFG['nodes_1']['config_1']
        LOGGER.info("Running 1 N with config %s+%s+%s",
                config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.single_node_deployment(sns_data=config['sns_data'],
                                    sns_parity=config['sns_parity'],
                                    sns_spare=config['sns_spare'],
                                    dix_data=config['dix_data'],
                                    dix_parity=config['dix_parity'],
                                    dix_spare=config['dix_spare'],
                                    cvg_count=config['cvg_per_node'],
                                    data_disk_per_cvg=config['data_disk_per_cvg'],
                                    master_node_list=self.master_node_list,
                                    worker_node_list=self.master_node_list)

    @pytest.mark.singlenode
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32654")
    def test_32654(self):
        """
        Deployment- 1node config_2
        """
        config = DEPLOY_CFG['nodes_1']['config_2']
        LOGGER.info("Running 1 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.single_node_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.master_node_list)

    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-41569")
    def test_41569(self):
        """
        S3 IO Operations
        """
        access_key, secret_key = self.deploy_lc_obj.get_default_access_secret_key(self.local_sol_path)
        LOGGER.debug("access key and secret key are %s , %s",access_key, secret_key)
        client_config_res = self.deploy_lc_obj.client_config(self.master_node_list, common_const.NAMESPACE, access_key=access_key, secret_key=secret_key, flag="component")
        LOGGER.info(client_config_res)
        LOGGER.info("Step to Perform basic IO operations")
        bucket_name = "bucket-" + str(int(time.time()))
        # ext_port_ip = client_config_res[2][2]
        s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                    endpoint_url=client_config_res[2][2])
        create_bucket_resp = s3t_obj.create_bucket(bucket_name)
        LOGGER.info("Created bucket name %s", bucket_name)
        assert_utils.assert_true(create_bucket_resp[0], create_bucket_resp[1])
        bucket_resp = s3t_obj.bucket_list()
        LOGGER.debug("bucket_list %s", bucket_resp[1])
        cmd = commands.CMD_AWSCLI_HEAD_BUCKET.format(bucket_name) + " --endpoint-url " + client_config_res[2][2]
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        resp=s3t_obj.delete_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Uploading the bucket")
        self.deploy_lc_obj.basic_io_write_read_validate(s3t_obj, bucket_name)
       