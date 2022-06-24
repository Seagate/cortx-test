# pylint: disable=too-many-lines
# !/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Tests System capacity scenarios using REST API
"""
import os
import logging
import time
from http import HTTPStatus
import pandas
import pytest
from commons import configmanager
from commons import cortxlogging
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.constants import RESTORE_SCALE_REPLICAS, K8S_SCRIPTS_PATH, K8S_PRE_DISK
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import s3_misc
from libs.csm.csm_interface import csm_api_factory
from libs.s3 import s3_test_lib
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from scripts.s3_bench.s3bench import s3bench

class TestSystemCapacity():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("[START] Setup Class")
        cls.csm_obj = csm_api_factory("rest")
        cls.log.info("Initiating Rest Client ...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.username = cls.csm_obj.config["csm_admin_user"]["username"]
        cls.user_pass = cls.csm_obj.config["csm_admin_user"]["password"]
        cls.deploy = False
        cls.akey = ""
        cls.skey = ""
        cls.s3_user = ""
        cls.bucket = ""
        cls.row_temp = "N{} failure"
        cls.node_list = []
        cls.host_list = []
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.io_bucket_name = f"iobkt1-copyobject-{time.perf_counter_ns()}"
        cls.s3_obj = s3_test_lib.S3TestLib()
        cls.ha_obj = HAK8s()
        for node in CMN_CFG["nodes"]:
            if node["node_type"] == "master":
                cls.log.debug("Master node : %s", node["hostname"])
                cls.master = LogicalNode(hostname=node["hostname"],
                                         username=node["username"],
                                         password=node["password"])
                cls.hlth_master = Health(hostname=node["hostname"],
                                         username=node["username"],
                                         password=node["password"])
            else:
                cls.log.debug("Worker node : %s", node["hostname"])
                cls.node_list.append(LogicalNode(hostname=node["hostname"],
                                                 username=node["username"],
                                                 password=node["password"]))
                host = node["hostname"]
                cls.host_list.append(host)
        cls.log.info("Master node object: %s", cls.master)
        cls.log.info("Worker node List: %s", cls.host_list)
        cls.num_worker = len(cls.host_list)
        cls.log.info("Number of workers detected: %s", cls.num_worker)
        cls.nd_obj = LogicalNode(hostname=CMN_CFG["nodes"][0]["hostname"],
                                 username=CMN_CFG["nodes"][0]["username"],
                                 password=CMN_CFG["nodes"][0]["password"])

        cls.log.debug("Node object list : %s", cls.nd_obj)
        cls.restore_pod = None
        cls.restore_method = RESTORE_SCALE_REPLICAS
        cls.deployment_name = []
        cls.failed_pod = []
        cls.deployment_backup = None
        cls.fail_cnt = 0
        cls.deploy_list = cls.master.get_deployment_name(cls.num_nodes)
        cls.update_seconds = cls.csm_conf["update_seconds"]
        cls.log.info("Get the value of K for the given cluster.")
        resp = cls.ha_obj.get_config_value(cls.master)
        if resp[0]:
            cls.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
            cls.nvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['data'])
        else:
            cls.log.info("Failed to get parity value, will use 1.")
            cls.kvalue = 1
        cls.cap_df = pandas.DataFrame()
        cls.aligned_size = 4 * cls.nvalue
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.err_margin = (cls.nvalue/(cls.nvalue+cls.kvalue))*100 + 1
        cls.s3_cleanup = False
        cls.deploy = True
        cls.restore_pod = True
        cls.log.info("[END] Setup Class")

    def setup_method(self):
        """
        Setup method for creating s3 user
        """
        self.log.info("[START] Setup Method")
        self.failed_pod = []
        self.log.info("Cleanup: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.master)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Cleanup: Cluster status checked successfully")

        self.log.info("Creating S3 account")
        resp = self.csm_obj.create_s3_account()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.s3_user = resp.json()["account_name"]
        self.bucket = "iam-user-bucket-" + str(int(time.time()))

        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        assert s3_misc.create_bucket(self.bucket, self.akey, self.skey), "Failed to create bucket."

        self.cap_df = pandas.DataFrame()
        total_written = s3_misc.get_total_used(self.akey, self.skey)

        self.log.info("[Start] Start some IOs")
        obj = f"object{self.s3_user}{time.time_ns()}.txt"
        self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, self.aligned_size,
                        self.bucket)
        resp = s3_misc.create_put_objects(
            obj, self.bucket, self.akey, self.skey, object_size=self.aligned_size)
        assert resp, "Put object Failed"
        self.log.info("[End] Start some IOs")

        self.log.info("[Start] Sleep %s", self.update_seconds)
        time.sleep(self.update_seconds)
        self.log.info("[Start] Sleep %s", self.update_seconds)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)

        new_write = self.aligned_size * 1024 * 1024
        total_written += new_write

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=self.err_margin, total=total_written)
        assert result[0], result[1]
        self.log.info("[END] Setup Method")

    def teardown_method(self):
        """
        Teardowm method for deleting s3 account created in setup.
        """
        self.log.info("[START] Teardown Method")
        if self.restore_pod:
            self.log.info("Failed deployments : %s", self.failed_pod)
            for deploy_name in self.failed_pod:
                self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
                resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
                self.log.debug("Response: %s", resp)
                assert resp[0], f"Failed to restore pod by {self.restore_method} way"
                self.log.info("Successfully restored pod by %s way", self.restore_method)
                self.log.info("[End] Restore deleted pods : %s", deploy_name)

        if self.s3_cleanup:
            self.log.info("Deleting bucket %s & associated objects", self.bucket)
            resp = s3_misc.delete_all_buckets(self.akey,self.skey)
            assert resp, "Delete all buckets and object failed."
            self.log.info("Deleting S3 account %s created in setup", self.s3_user)
            resp = self.csm_obj.delete_s3_account_user(self.s3_user)
            assert resp.status_code == HTTPStatus.OK, "Failed to delete S3 user"

        self.deploy = True
        if self.deploy:
            self.log.info("Cleanup: Destroying the cluster ")
            resp = self.deploy_lc_obj.destroy_setup(self.master, self.node_list, K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Cleanup: Cluster destroyed successfully")

            self.log.info("Cleanup: Setting prerequisite")
            self.deploy_lc_obj.execute_prereq_cortx(self.master,
                                                    K8S_SCRIPTS_PATH,
                                                    K8S_PRE_DISK)

            for node in self.node_list:
                self.deploy_lc_obj.execute_prereq_cortx(node, K8S_SCRIPTS_PATH,
                                                        K8S_PRE_DISK)
            self.log.info("Cleanup: Prerequisite set successfully")

            self.log.info("Cleanup: Deploying the Cluster")
            resp_cls = self.deploy_lc_obj.deploy_cluster(self.master,
                                                            K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp_cls[0], resp_cls[1])
            self.log.info("Cleanup: Cluster deployment successfully")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)

            self.log.info("Cleanup: Check cluster status")
            resp = self.ha_obj.poll_cluster_status(self.master)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Cleanup: Cluster status checked successfully")

        self.log.info("[END] Teardown Method")

    # pylint: disable-msg=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33899')
    def test_33899(self):
        """
        Test degraded capacity with Transient node failure in flexible protection scheme with Y
        extra nodes without write
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_33899"]
        cap_df = pandas.DataFrame()
        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = s3_misc.get_total_used(self.akey, self.skey)
        new_row = pandas.Series(data=resp, name='Nofail')
        cap_df = cap_df.append(new_row, ignore_index=False)

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        assert result[0], result[1]

        self.log.info("[START] Failure loop")
        for failure_cnt in range(1, self.kvalue + 2):
            deploy_name = self.deploy_list[failure_cnt]
            self.log.info("[Start] Shutdown the data pod safely")
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {deploy_name}")
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            index = deploy_name + "offline"
            new_row = pandas.Series(data=resp, name=index)
            cap_df = cap_df.append(new_row, ignore_index=False)

            result = self.csm_obj.verify_bytecount_all(resp,failure_cnt, self.kvalue,
                test_cfg["err_margin"], total_written)
            assert result[0], result[1]
        self.log.info("[END] Failure loop")

        self.log.info("[START] Recovery loop")
        failure_cnt = len(self.failed_pod)
        for deploy_name in reversed(self.failed_pod):
            self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.failed_pod.remove(deploy_name)
            self.log.info("[End] Restore deleted pods : %s", deploy_name)
            failure_cnt -=1

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            index = deploy_name + "online"
            new_row = pandas.Series(data=resp, name=index)
            cap_df = cap_df.append(new_row, ignore_index=False)

            result = self.csm_obj.verify_bytecount_all(resp,failure_cnt, self.kvalue,
                test_cfg["err_margin"], total_written)
            assert result[0], result[1] + f"for {failure_cnt} failures"
        self.deploy = True

    # pylint: disable=broad-except
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33919')
    def test_33919(self):
        """
        Test degraded capacity with Transient node failure in flexible protection scheme with K
        extra nodes with aligned write
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33919"]
        cap_df = pandas.DataFrame(columns=self.deploy_list)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = s3_misc.get_total_used(self.akey, self.skey)

        cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, resp["healthy"])
        self.log.debug("Collected data frame : %s", cap_df.to_string())

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        assert result[0], result[1]

        self.log.info("[START] Failure loop")
        for failure_cnt in range(1, self.kvalue + 1):
            deploy_name = self.deploy_list[failure_cnt]
            self.log.info("[Start] Shutdown the data pod safely")
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {deploy_name}")
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
            critical=None, damaged=None, err_margin=test_cfg["err_margin"], total=total_written)
            assert result[0], result[1]

            new_write = self.aligned_size * failure_cnt
            self.log.info("[Start] Start some IOs")
            obj = f"object{self.s3_user}{time.time_ns()}.txt"
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, new_write,
                            self.bucket)
            try:
                resp = s3_misc.create_put_objects(
                    obj, self.bucket, self.akey, self.skey, object_size=new_write)

                new_write *= 1024 * 1024
                total_written += new_write
                cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, new_write, obj,
                                                self.bucket, self.akey, self.skey)
                self.log.debug("Collected data frame : %s", cap_df.to_string())
            except BaseException as error:
                if failure_cnt > self.kvalue:
                    pass
                else:
                    raise error
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1]
        self.log.info("[END] Failure loop")

        self.log.info("[START] Recovery loop")
        failure_cnt = len(self.failed_pod)
        for deploy_name in reversed(self.failed_pod):
            self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.failed_pod.remove(deploy_name)
            self.log.info("[End] Restore deleted pods : %s", deploy_name)
            failure_cnt -=1
            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)
            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1] + f"for {failure_cnt} failures"
        assert self.csm_obj.verify_checksum(cap_df)
        self.deploy = True

    # pylint: disable=broad-except
    @pytest.mark.skip(reason="CORTX-31578")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33920')
    def test_33920(self):
        """
        Test degraded capacity with Transient node failure in flexible protection scheme with extra
        nodes with create S3 account in degraded mode.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33920"]
        cap_df = pandas.DataFrame(columns=self.deploy_list)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = s3_misc.get_total_used(self.akey, self.skey)

        cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, resp["healthy"])
        self.log.debug("Collected data frame : %s", cap_df.to_string())

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        assert result[0], result[1]

        self.log.info("[START] Failure loop")
        for failure_cnt in range(1, self.kvalue + 1):
            deploy_name = self.deploy_list[failure_cnt]
            self.log.info("[Start] Shutdown the data pod safely")
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {deploy_name}")
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            new_write = self.aligned_size * failure_cnt
            self.log.info("[Start] Start some IOs")
            obj = f"object{self.s3_user}{time.time_ns()}.txt"
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, new_write,
                            self.bucket)
            try:
                self.log.info("[START] Create S3 account")
                resp = self.csm_obj.create_s3_account()
                assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
                akey = resp.json()["access_key"]
                skey = resp.json()["secret_key"]
                s3_user = resp.json()["account_name"]
                self.log.info("[END] Create S3 account")

                self.log.info("[START] Create Bucket")
                bucket = "iam-user-bucket-" + str(int(time.time()))
                msg = f"bucket:{bucket} with access key: {akey} and secret key: {akey}"
                self.log.info("Verify create %s", msg)
                assert s3_misc.create_bucket(bucket, akey, skey), f"Failed to {msg}"
                self.log.info("[END] Create Bucket")

                new_write = self.csm_obj.random_gen.randrange(
                    test_cfg["object_size"]["start_range"],
                    test_cfg["object_size"]["stop_range"])

                self.log.info("[Start] IOs")
                obj = f"object{s3_user}{time.time_ns()}.txt"
                self.log.info("Put Object: %s of %s MB write in %s", obj, new_write, msg)
                resp = s3_misc.create_put_objects(obj, bucket, akey, skey, object_size=new_write)
                assert resp, "Put object Failed"
                self.log.info("[End] IOs")
                new_write *= 1024 * 1024
                total_written += new_write
                cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, new_write, obj, bucket,
                                                akey, skey)
                self.log.debug("Collected data frame : %s", cap_df.to_string())
            except BaseException as error:
                if failure_cnt > self.kvalue:
                    pass
                else:
                    raise error

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1]
        self.log.info("[END] Failure loop")

        self.log.info("[START] Recovery loop")
        failure_cnt = len(self.failed_pod)
        for deploy_name in reversed(self.failed_pod):
            self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.failed_pod.remove(deploy_name)
            self.log.info("[End] Restore deleted pods : %s", deploy_name)
            failure_cnt -= 1
            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)
            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1] + f"for {failure_cnt} failures"
        assert self.csm_obj.verify_checksum(cap_df)
        self.deploy = True

    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33927')
    def test_33927(self):
        """
        Test degraded capacity values is persistent across cluster restart.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_33927"]
        cap_df = pandas.DataFrame()
        total_written = s3_misc.get_total_used(self.akey, self.skey)
        self.log.info("[Start] IOs")
        obj = f"object{self.s3_user}{time.time_ns()}.txt"
        msg = f"bucket:{self.bucket} with access key: {self.akey} and secret key: {self.skey}"

        obj_size = self.csm_obj.random_gen.randrange(test_cfg["start_range"],
                                                     test_cfg["stop_range"])
        self.log.info("Put Object: %s of %s MB write in %s", obj, obj_size, msg)
        resp = s3_misc.create_put_objects(obj, self.bucket, self.akey, self.skey,
                                          object_size=obj_size)
        assert resp, "Put object Failed"
        csum = s3_misc.get_object_checksum(obj, self.bucket, self.akey, self.skey)
        self.log.info("[End] IOs")

        self.log.info("[Start] Sleep %s", self.update_seconds)
        time.sleep(self.update_seconds)
        self.log.info("[End] Sleep %s", self.update_seconds)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written += obj_size * 1024 * 1024
        new_row = pandas.Series(data=resp, name='BeforeClusterRestart')
        cap_df = cap_df.append(new_row, ignore_index=False)
        cap_df["csum"] = csum

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=self.err_margin, total=total_written)
        assert result[0], result[1]

        self.log.info("[Start] Stop Cluster")
        resp = self.ha_obj.cortx_stop_cluster(self.master)
        assert resp[0], resp[1]
        time.sleep(60)
        self.log.info("[End] Stop Cluster")

        self.log.info("[Start] Cluster restart.")
        self.log.info("Check whether cluster restart command ran successfully.")
        resp = self.ha_obj.cortx_start_cluster(self.master)
        assert resp[0], resp[1]
        self.log.info("Cluster is up and running.")
        self.log.info("Checking whether all CORTX Data pods have been restarted.")
        resp = self.ha_obj.check_pod_status(self.master)
        assert resp[0], resp[1]
        self.log.info("[End] Cluster restart.")

        self.log.info("[Start] Sleep %s", self.update_seconds)
        time.sleep(self.update_seconds)
        self.log.info("[End] Sleep %s", self.update_seconds)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = resp["healthy"]
        new_row = pandas.Series(data=resp, name='AfterClusterRestart')
        cap_df = cap_df.append(new_row, ignore_index=False)

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=self.err_margin, total=total_written)
        assert result[0], result[1]

        csum = s3_misc.get_object_checksum(obj, self.bucket, self.akey, self.skey)
        cap_df["csum"]["AfterClusterRestart"] = csum

        result = (cap_df.loc["AfterClusterRestart"] == cap_df.loc["BeforeClusterRestart"]).all()
        self.log.info("Check the cluster value before and after restart are same")
        assert result, "Values are not consistent."
        self.deploy=True

    # pylint: disable=broad-except
    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33929')
    def test_33929(self):
        """
        Test degraded capacity with Transient node failure in flexible protection scheme with K+2
        extra nodes with aligned write - recovery 2
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33929"]
        cap_df = pandas.DataFrame(columns=self.deploy_list)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = resp["healthy"]

        cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, resp["healthy"])
        self.log.debug("Collected data frame : %s", cap_df.to_string())

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        assert result[0], result[1]

        self.log.info("[START] Failure loop")
        for failure_cnt in range(1, self.kvalue + 1):
            deploy_name = self.deploy_list[failure_cnt]
            self.log.info("[Start] Shutdown the data pod safely")
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {deploy_name}")
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)

            result = self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
            critical=None, damaged=None, err_margin=test_cfg["err_margin"], total=total_written)
            assert result[0], result[1]

            new_write = self.aligned_size * failure_cnt
            self.log.info("[Start] Start some IOs")
            obj = f"object{self.s3_user}{time.time_ns()}.txt"
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, new_write,
                            self.bucket)
            try:
                resp = s3_misc.create_put_objects(
                    obj, self.bucket, self.akey, self.skey, object_size=new_write)
                new_write *= 1024 * 1024
                total_written += new_write
                cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, new_write, obj,
                                                self.bucket, self.akey, self.skey)
                self.log.debug("Collected data frame : %s", cap_df.to_string())
            except BaseException as error:
                if failure_cnt > self.kvalue:
                    pass
                else:
                    raise error
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1]
        self.log.info("[END] Failure loop")

        self.log.info("[START] Recovery loop")
        failure_cnt = len(self.failed_pod)
        for deploy_name in self.failed_pod:
            self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
            self.log.debug("Response: %s", resp)
            assert resp[0], f"Failed to restore pod by {self.restore_method} way"
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.failed_pod.remove(deploy_name)
            self.log.info("[End] Restore deleted pods : %s", deploy_name)
            failure_cnt -=1
            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)
            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1] + f"for {failure_cnt} failures"
        self.deploy = True

    # pylint: disable=broad-except
    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33928')
    def test_33928(self):
        """
        Test degraded capacity with single node failure ( K>0 ) with IOs for 2+1+0 config with 3
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33928"]
        cap_df = pandas.DataFrame(columns=self.deploy_list)

        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = resp["healthy"]

        cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, resp["healthy"])
        self.log.debug("Collected data frame : %s", cap_df.to_string())

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        assert result[0], result[1]

        self.log.info("[START] Failure loop")
        for failure_cnt in range(1, self.kvalue + 1):
            deploy_name = self.deploy_list[failure_cnt]
            self.log.info("[Start] Shutdown the data pod safely")
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {deploy_name}")
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            new_write = self.csm_obj.random_gen.randrange(test_cfg["start_range"],
                                                          test_cfg["stop_range"])
            self.log.info("[Start] Start some IOs")
            obj = f"object{self.s3_user}{time.time_ns()}.txt"
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, new_write,
                            self.bucket)
            try:
                resp = s3_misc.create_put_objects(
                    obj, self.bucket, self.akey, self.skey, object_size=new_write)

                new_write *= 1024 * 1024
                total_written += new_write
                cap_df = self.csm_obj.append_df(cap_df, self.failed_pod, new_write, obj,
                                                self.bucket, self.akey, self.skey)
                self.log.debug("Collected data frame : %s", cap_df.to_string())
            except BaseException as error:
                if failure_cnt > self.kvalue:
                    pass
                else:
                    raise error
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1]
        self.log.info("[END] Failure loop")

        self.log.info("[START] Recovery loop")
        failure_cnt = len(self.failed_pod)
        for deploy_name in reversed(self.failed_pod):
            self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.failed_pod.remove(deploy_name)
            self.log.info("[End] Restore deleted pods : %s", deploy_name)
            failure_cnt -=1
            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)
            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_flexi_protection(resp, cap_df, self.failed_pod,
                self.kvalue, test_cfg["err_margin"])
            assert result[0], result[1] + f"for {failure_cnt} failures"
        assert self.csm_obj.verify_checksum(cap_df)
        self.deploy = True

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34716')
    def test_34716(self):
        """
        Check the api response for unauthorized request for capacity
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 2: Modify header to invalid key")
        header['Authorization1'] = header.pop('Authorization')
        self.log.info("Step 3: Call degraded capacity api with invalid key in header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed for invalid key access")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed for invalid key access")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34717')
    def test_34717(self):
        """
        Check the api response for appropriate error when missing Param provided
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 2: Modify header for missing params")
        header['Authorization'] = ''
        self.log.info("Step 3: Call degraded capacity api with missing params in header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34718')
    def test_34718(self):
        """
        Check the api response when telemetry_auth: 'false' and without key and value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Delete control pod and wait for restart")
        resp = self.csm_obj.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        # To get all the services up and running
        time.sleep(40)
        self.log.info("Step 2: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 3: Modify header to delete key and value")
        del header['Authorization']
        self.log.info("Step 4: Call degraded capacity api with deleted key and value in header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34719')
    def test_34719(self):
        """
        Check the api response when telemetry_auth: 'false' and with valid key and value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Call degraded capacity api with valid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34720')
    def test_34720(self):
        """
        Check the api response when telemetry_auth: 'false' and invalid value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Delete control pod and wait for restart")
        resp = self.csm_obj.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        # To get all the services up and running
        time.sleep(40)
        self.log.info("Step 2: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 3: Modify header for invalid value")
        header['Authorization'] = 'abc'
        self.log.info("Step 4: Call degraded capacity api with invalid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34722')
    def test_34722(self):
        """
        Check the api response when telemetry_auth:'true', key=valid and value="Invalid"
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 2: Modify header for invalid value")
        header['Authorization'] = 'abc'
        self.log.info("Step 3: Call degraded capacity api with invalid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34723')
    def test_34723(self):
        """
        Check all required variable are coming in rest response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Get header for admin user")
        header = self.csm_obj.get_headers(self.username, self.user_pass)
        self.log.info("Step 2: Call degraded capacity api with valid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("Step 3: Check all variables are present in rest response")
        resp = self.csm_obj.validate_metrics(response.json())
        self.log.info("Printing response %s", resp)
        assert_utils.assert_true(resp, "Rest data metrics check failed")
        self.log.info("Step 4: Verified metric data for bytecount")
        response = self.csm_obj.get_degraded_capacity(endpoint_param=None)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("Step 5: Check all variables are present in rest response")
        resp = self.csm_obj.validate_metrics(response.json(), endpoint_param=None)
        assert_utils.assert_true(resp, "Rest data metrics check failed in full mode")
        self.log.info("##### Test ended -  %s #####", test_case_name)
        self.deploy = False

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-39923')
    def test_39923(self):
        """
        Test degraded capacity with single node failure ( K>0 ) with IOs for 3+2+0 config with 5
        nodes using aws
        """
        test_case_name = cortxlogging.get_frame()
        test_cfg = self.csm_conf["test_39923"]

        self.log.info("##### Test started -  %s #####", test_case_name)
        resp = self.csm_obj.get_degraded_all(self.hlth_master)
        total_written = s3_misc.get_total_used(self.akey, self.skey)
        self.log.info("Bytes written : %s", total_written)

        cap_df = self.csm_obj.append_df(self.cap_df, self.failed_pod, resp["healthy"])
        self.log.debug("Collected data frame : %s", cap_df.to_string())

        result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written, degraded=0,
            critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        assert result[0], result[1]

        self.log.info("[START] loop")
        for deploy_name in self.deploy_list:

            self.log.info("[Start] Shutdown the data pod safely %s", deploy_name)
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {deploy_name}")
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            self.log.info("[Start] Start some IOs")
            bucket = f"test39923buck{time.time_ns()}"
            resp = s3bench(
                        self.akey,
                        self.skey,
                        bucket=bucket,
                        end_point=S3_CFG["s3_url"],
                        num_clients=test_cfg["num_clients"],
                        num_sample=test_cfg["num_sample"],
                        obj_name_pref=test_cfg["obj_name_pref"],
                        obj_size=test_cfg["obj_size"],
                        duration=test_cfg["duration"],
                        log_file_prefix=test_case_name,
                        validate_certs=S3_CFG["validate_certs"],
                        skip_cleanup=True)
            self.log.info(resp)
            assert os.path.exists(resp[1]), "Log file not found."
            self.log.info("[End] Start some IOs")

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[End] Sleep %s", self.update_seconds)

            _, new_write = s3_misc.get_objects_size_bucket(bucket,self.akey,self.skey)
            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_degraded_capacity(resp, healthy=new_write,
                degraded=total_written, critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                total=total_written+new_write)
            assert result, "Degraded byte check failed"

            total_written += new_write
            self.log.info("[START] Recovery loop")
            self.log.info("[Start]  Restore deleted pods : %s", deploy_name)
            resp = self.master.create_pod_replicas(num_replica=1, deploy=deploy_name)
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.failed_pod.remove(deploy_name)
            self.log.info("[End] Restore deleted pods : %s", deploy_name)

            self.log.info("[Start] Sleep %s", self.update_seconds)
            time.sleep(self.update_seconds)
            self.log.info("[Start] Sleep %s", self.update_seconds)
            resp = self.csm_obj.get_degraded_all(self.hlth_master)
            result = self.csm_obj.verify_degraded_capacity(resp, healthy=total_written,
                            degraded=0, critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                            total=total_written)
            assert result[0], result[1]
            # Uncomment next lines and remove break when CORTX-32322 is fixed.
            #resp = s3_misc.delete_all_buckets(self.akey,self.skey)
            #assert resp, "Delete all buckets and object failed."
            break
        self.log.info("[END] completed")
        self.deploy = True
