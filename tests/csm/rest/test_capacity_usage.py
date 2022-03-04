# pylint: disable=too-many-lines
# !/usr/bin/python
# -*- coding: utf-8 -*-
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
#
"""Tests System capacity scenarios using REST API
"""
import logging
import time
from random import SystemRandom
from http import HTTPStatus
import pytest
from commons import configmanager
from commons import cortxlogging
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.constants import POD_NAME_PREFIX
from commons.constants import RESTORE_SCALE_REPLICAS
from config import CMN_CFG
#from libs.csm.rest.csm_rest_capacity import SystemCapacity
#from libs.csm.rest.csm_rest_cluster import RestCsmCluster
#from libs.csm.rest.csm_rest_csmuser import RestCsmUser
#from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import s3_misc
from libs.csm.csm_interface import csm_api_factory

class TestSystemCapacity():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_obj = csm_api_factory("rest")
        #cls.system_capacity = SystemCapacity()
        cls.cryptogen = SystemRandom()
        cls.log.info("Initiating Rest Client ...")
        #cls.csm_cluster = RestCsmCluster()
        #cls.csm_user = RestCsmUser()
        #cls.s3user_obj = RestS3user()
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.username = cls.csm_user.config["csm_admin_user"]["username"]
        cls.user_pass = cls.csm_user.config["csm_admin_user"]["password"]
        cls.akey = ""
        cls.skey = ""
        cls.s3_user = ""
        cls.bucket = ""
        cls.row_temp= "N{} failure"
        cls.health_helper = Health(CMN_CFG["nodes"][0]["hostname"],
                                   CMN_CFG["nodes"][0]["username"],
                                   CMN_CFG["nodes"][0]["password"])
        cls.ha_obj = HAK8s()
        cls.node_list = []
        cls.host_list = []
        cls.num_nodes = len(CMN_CFG["nodes"])
        for node in CMN_CFG["nodes"]:
            if node["node_type"] == "master":
                cls.master = LogicalNode(hostname=node["hostname"],
                                        username=node["username"],
                                        password=node["password"])
                cls.hlth_master = Health(hostname=node["hostname"],
                                         username=node["username"],
                                         password=node["password"])
            else:
                cls.node_list.append(LogicalNode(hostname=node["hostname"],
                                          username=node["username"],
                                          password=node["password"]))
                host = node["hostname"]
                cls.host_list.append(host)
        cls.nd_obj = LogicalNode(hostname=CMN_CFG["nodes"][0]["hostname"],
                                 username=CMN_CFG["nodes"][0]["username"],
                                 password=CMN_CFG["nodes"][0]["password"])
        cls.restore_pod = None
        cls.restore_method = None
        cls.deployment_name = None
        cls.deployment_backup = None

    def setup_method(self):
        """
        Setup method for creating s3 user
        """
        self.log.info("Creating S3 account")
        resp = self.s3user_obj.create_s3_account()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.s3_user = resp.json()["account_name"]
        self.bucket = f"bucket{self.s3_user}"
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        assert s3_misc.create_bucket(self.bucket, self.akey, self.skey), "Failed to create bucket."

    def teardown_method(self):
        """
        Teardowm method for deleting s3 account created in setup.
        """
        self.log.info("Deleting bucket %s & associated objects", self.bucket)
        assert s3_misc.delete_objects_bucket(
            self.bucket, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Deleting S3 account %s created in setup", self.s3_user)
        resp = self.s3user_obj.delete_s3_account_user(self.s3_user)
        assert resp.status_code == HTTPStatus.OK, "Failed to delete S3 user"
        if self.restore_pod:
            self.log.info("Restore deleted pods.")
            resp = self.ha_obj.restore_pod(pod_obj=self.master,
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                           self.deployment_backup})
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15200')
    def test_4202(self):
        """Test REST API for GET request with default arguments return 200 and json response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        results = self.csm_obj.parse_capacity_usage()
        csm_total, csm_avail, csm_used, csm_used_percent, csm_unit = results
        ha_total, ha_avail, ha_used = self.health_helper.get_sys_capacity()
        ha_used_percent = round((ha_used / ha_total) * 100, 1)
        csm_used_percent = round(csm_used_percent, 1)
        assert_utils.assert_equals(
            csm_total, ha_total, "Total capacity check failed.")
        assert_utils.assert_equals(
            csm_avail, ha_avail, "Available capacity check failed.")
        assert_utils.assert_equals(
            csm_used, ha_used, "Used capacity check failed.")
        assert_utils.assert_equals(
            csm_used_percent, ha_used_percent, "Used capacity percentage check failed.")
        assert_utils.assert_equals(
            csm_unit, 'BYTES', "Capacity unit check failed.")
        self.log.info("Capacity reported by CSM matched HCTL response.")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33899')
    def test_33899(self):
        """
        Test degraded capacity with single node failure ( K>0 ) without IOs for 2+1+0 config with 3
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33899"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.csm_obj.get_capacity_consul()
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"])
        self.log.info("[End] Fetch degraded capacity on Consul with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on HCTL with 0 Node failure")
        resp = self.health_helper.hctl_status_json()["bytecount"]
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        self.log.info("[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()["bytecount"]
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        self.log.info("[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

            index = self.row_temp.format(node)
            self.log.info("[Start] Fetch degraded capacity on Consul with %s Node failure",
                            self.host_list[node])
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with %s Node failure",
                            self.host_list[node])

            self.log.info("[Start] Fetch degraded capacity on HCTL with %s Node failure",
                            self.host_list[node])
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with %s Node failure",
                            self.host_list[node])

            self.log.info("[Start] Fetch degraded capacity on CSM with %s Node failure",
                            self.host_list[node])
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with %s Node failure",
                            self.host_list[node])

            self.log.info("[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.", self.host_list[node])
            self.log.info("[End] Power on node back from BMC/ssc-cloud and check node status")

            index = self.row_temp.format(node)
            self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM with 0 Node failure")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info("Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33919')
    def test_33919(self):
        """
        Test degraded capacity with single node failure ( K>0 ) with IOs for 2+1+0 config with 3
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33919"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        # TBD: Write Function for constructing df from values.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"])
        self.log.info(
            "[End] Fetch degraded capacity on Consul with 0 Node failure")

        self.log.info(
            "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", self.host_list[node])

            self.log.info("[Start] Start some IOs on %s", self.host_list[node])
            obj = f"object{self.s3_user}.txt"
            write_bytes_mb = self.cryptogen.randrange(
                test_cfg["object_size"]["start_range"], test_cfg["object_size"]["stop_range"])

            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          self.bucket)
            resp = s3_misc.create_put_objects(
                obj, self.bucket, self.akey, self.skey, object_size=write_bytes_mb)
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs on %s", node)
            new_written = write_bytes_mb * 1024 * 1024
            total_written = total_written + new_written

            index = self.row_temp.format(node)
            self.log.info("[Start] Fetch degraded capacity on Consul with %s Node failure",
                            self.host_list[node])
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with %s Node failure",
                            self.host_list[node])

            self.log.info("[Start] Fetch degraded capacity on HCTL with %s Node failure",
                            self.host_list[node])
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with %s Node failure",
                            self.host_list[node])

            self.log.info("[Start] Fetch degraded capacity on CSM with %s Node failure",
                            self.host_list[node])
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with %s Node failure",
                            self.host_list[node])

            self.log.info("[Start] Power on node back and check node status")
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            self.log.info("[End] Power on node back and check node status")

            index = self.row_temp.format(0)
            self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info("Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33920')
    def test_33920(self):
        """
        Test degraded capacity with single node failure ( K>0 ) with IOs for 2+1+0 config with 3
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33920"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"])
        self.log.info(
            "[End] Fetch degraded capacity on Consul with 0 Node failure")

        self.log.info(
            "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", self.host_list[node])

            self.log.info("[Start] Start some IOs on %s", node)

            self.log.info("Creating custom S3 account...")
            user_data = self.s3user_obj.create_custom_s3_payload("valid")
            resp = self.s3user_obj.create_custom_s3_user(user_data)
            self.log.info("Verify Status code of the Create user operation.")
            assert resp.status_code == HTTPStatus.CREATED.value, "Unexpected Status code"

            akey = resp.json()["access_key"]
            skey = resp.json()["secret_key"]
            s3_user = resp.json()["account_name"]
            bucket = f"bucket{s3_user}"
            obj = f"object{s3_user}.txt"

            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s", bucket,
                          akey, skey)
            assert s3_misc.create_bucket(
                bucket, akey, skey), "Failed to create bucket."

            write_bytes_mb = self.cryptogen.randrange(
                test_cfg["object_size"]["start_range"], test_cfg["object_size"]["stop_range"])

            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, akey, skey, object_size=write_bytes_mb)
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs on %s", node)

            new_written = write_bytes_mb * 1024 * 1024
            total_written = total_written + new_written

            index = self.row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info("[Start] Power on node back and check node status")
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            self.log.info("[End] Power on node back and check node status")

            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33928')
    def test_33928(self):
        """
        Test degraded capacity with multi node failure ( K>0 ) without IOs for 4+2+0 config with 6
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_33928"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"])
        self.log.info(
            "[End] Fetch degraded capacity on Consul with 0 Node failure")

        self.log.info(
            "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", self.host_list[node])

            index = self.row_temp.format(node)
            self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info("[Start] Power on node back and check node status")
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            self.log.info("[End] Power on node back and check node status")

            index = self.row_temp.format(0)
            self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33929')
    def test_33929(self):
        """
        Test degraded capacity with multi node failure ( K>0 ) with IOs for 4+2+0 config with 6
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33929"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"])
        self.log.info(
            "[End] Fetch degraded capacity on Consul with 0 Node failure")

        self.log.info(
            "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", self.host_list[node])

            self.log.info("[Start] Start some IOs on %s", node)
            obj = f"object{self.s3_user}.txt"
            write_bytes_mb = self.cryptogen.randrange(
                test_cfg["object_size"]["start_range"], test_cfg["object_size"]["stop_range"])

            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          self.bucket)
            resp = s3_misc.create_put_objects(
                obj, self.bucket, self.akey, self.skey, object_size=write_bytes_mb)
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs on %s", node)
            new_written = write_bytes_mb * 1024 * 1024
            total_written = total_written + new_written

            index = self.row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info("[Start] Power on node back and check node status")
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            self.log.info("[End] Power on node back and check node status")

            index = self.row_temp.format(0)
            self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                 critical=0, damaged=0,
                                                                 err_margin=test_cfg["err_margin"],
                                                                 total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-34698')
    def test_34698(self):
        """
        Test degraded capacity with single node failure ( K>0 ) with IOs for 2+1+0 config with 3
        nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_34698"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0
        new_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")
        obj = f"object{self.s3_user}.txt"
        write_bytes_mb = self.cryptogen.randrange(
                test_cfg["object_size"]["start_range"], test_cfg["object_size"]["stop_range"])

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Start some IOs")
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                            self.bucket)
            resp = s3_misc.create_put_objects(
                obj, self.bucket, self.akey, self.skey, object_size=write_bytes_mb)
            assert resp, "Put object Failed"
            self.log.info("[End] Start some IOs")
            new_written = write_bytes_mb * 1024 * 1024

            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            # TBD: Write Function for constructing df from values.
            total_written = resp["healthy"]
            cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
            cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
            cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
            cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
            cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                                critical=0, damaged=0,
                                                                err_margin=test_cfg["err_margin"])
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
            cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
            cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
            cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
            cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
            cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
            cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
            cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", self.host_list[node])

            resp = s3_misc.delete_object(
                obj, self.bucket, self.akey, self.skey, object_size=write_bytes_mb)
            assert resp, "Delete object Failed"

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 1 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            total_written = total_written - new_written
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=0, degraded=total_written, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 1 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 1 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=0, degraded=total_written, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 1 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM with 1 Node failure")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(
                resp, healthy=0, degraded=total_written, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 1 Node failure")

            self.log.info("[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.", self.host_list[node])
            self.log.info("[End] Power on node back from BMC/ssc-cloud and check node status")

            self.log.info("[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on Consul with 0 Node failure")

            self.log.info(
                "[Start] Fetch degraded capacity on HCTL with 0 Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33925')
    def test_33925(self):
        """
        Test degraded capacity with ioservice failure with IOs for 2+1+0 config with 3 nodes
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33925"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info("[Start] Fetch degraded capacity on Consul with 0 Pod failure")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"])
        self.log.info("[End] Fetch degraded capacity on Consul with 0 Pod failure")

        self.log.info("[Start] Fetch degraded capacity on HCTL with 0 Pod failure")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info("[End] Fetch degraded capacity on HCTL with 0 Pod failure")

        self.log.info("[Start] Fetch degraded capacity on CSM with 0 Pod failure")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        self.log.info("[End] Fetch degraded capacity on CSM with 0 Pod failure")

        self.log.info("Get pod name to be deleted")
        pod_list = self.master.get_all_pods(pod_prefix=POD_NAME_PREFIX)

        for pod_name in pod_list:
            self.log.info("[Start] Shutdown the data pod safely by making replicas=0")
            self.log.info("Deleting pod %s", pod_name)
            resp = self.master.create_pod_replicas(num_replica=0, pod_name=pod_name)
            assert_utils.assert_false(resp[0],
                f"Failed to delete pod {pod_name} by making replicas=0")
            self.log.info("[End] Successfully shutdown/deleted pod %s by making replicas=0",
                pod_name)

            self.deployment_name = resp[1]
            self.restore_pod = True
            self.restore_method = RESTORE_SCALE_REPLICAS

            self.log.info("[Start] Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.master)
            assert_utils.assert_false(resp[0], resp)
            self.log.info("[End] Cluster is in degraded state")

            self.log.info("[Start] Check services status that were running on pod %s", pod_name)
            resp = self.hlth_master.get_pod_svc_status(pod_list=[pod_name], fail=True)
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            self.log.info("[End] Services of pod are in offline state")

            self.log.info("Step 8: Check services status on remaining pods %s",
                        pod_list.remove(pod_name))
            resp = self.hlth_master.get_pod_svc_status(pod_list=pod_list.remove(pod_name),
                                                            fail=False)
            self.log.debug("[Start] Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            self.log.info("[End] Services of remaining pod are in online state")

            #self.log.info("Step 9: Perform IO operation on %s", bucket_name)
            #resp = self.acc_capacity.perform_io_validate_data_usage(
            #    [s3_user, access_key, secret_key, bucket_name],
            #    NORMAL_UPLOAD_SIZES_IN_MB, False)
            #assert_utils.assert_true(resp, "Error during IO operations")
            #self.log.info("Step 9: Performed IO operation on %s", bucket_name)


            index = pod_name + "offline"
            self.log.info("[Start] Fetch degraded capacity on Consul with %s pod failure", pod_name)
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with %s pod failure", pod_name)

            self.log.info("[Start] Fetch degraded capacity on HCTL with %s pod failure", pod_name)
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with %s pod failure", pod_name)

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with %s pod failure", pod_name)

            self.log.info("[Start]  Restore deleted pods : %s", pod_name)
            resp = self.ha_obj.restore_pod(pod_obj=self.master, restore_method=self.restore_method,
                        restore_params={"deployment_name": self.deployment_name,
                        "deployment_backup": self.deployment_backup})
            self.log.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            self.log.info("Successfully restored pod by %s way", self.restore_method)
            self.restore_pod = False
            self.log.info("[End] Restore deleted pods : %s", pod_name)

            index = pod_name + "online"
            self.log.info("[Start] Fetch degraded capacity on Consul with 0 pod failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with 0 pod failure")

            self.log.info("[Start] Fetch degraded capacity on HCTL with 0 pod failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with 0 pod failure")

            self.log.info("[Start] Fetch degraded capacity on CSM with 0 pod failure")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with 0 pod failure")

        self.log.info("Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-33926')
    def test_33926(self):
        """
        Test degraded capacity with multi node failure ( K>0 ) without IOs for 4+1+0 config with
        greater than 6 nodes.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_33926"]
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info("[Start] Fetch degraded capacity on Consul with no Node failure")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"])
        self.log.info("[End] Fetch degraded capacity on Consul with no Node failure")

        self.log.info("[Start] Fetch degraded capacity on HCTL with no Node failure")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc["No failure"]["hctl_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["hctl_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["hctl_critical"] = resp["critical"]
        cap_df.loc["No failure"]["hctl_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info("[End] Fetch degraded capacity on HCTL with no Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM with no Node failure")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        self.log.info("[End] Fetch degraded capacity on CSM with no Node failure")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s: %s", node, self.host_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not shutdown yet."

            self.log.info("Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", self.host_list[node])

            index =  self.row_temp.format(node)
            self.log.info("[Start] Fetch degraded capacity on Consul with Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with Node failure")

            self.log.info("[Start] Fetch degraded capacity on HCTL with Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM with Node failure")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with Node failure")

            self.log.info("[Start] Power on the node : %s", self.host_list[node])
            resp = self.ha_obj.host_power_on(host=self.host_list[node])
            assert resp, f"{self.host_list[node]} has not powered on yet."
            self.log.info("[End] Power on the node : %s", self.host_list[node])

            index = self.row_temp.format(0)
            self.log.info("[Start] Fetch degraded capacity on Consul with no Node failure")
            resp = self.csm_obj.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on Consul with no Node failure")

            self.log.info("[Start] Fetch degraded capacity on HCTL with no Node failure")
            # TBD : HCTL output doest have degraded capacity yet.
            resp = self.health_helper.hctl_status_json()
            cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
            cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
            cap_df.loc[index]["hctl_critical"] = resp["critical"]
            cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
            #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on HCTL with no Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM with no Node failure")
            resp = self.csm_obj.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info("[End] Fetch degraded capacity on CSM with no Node failure")

        self.log.info("Summation check of the healthy bytes from each node failure for consul")
        assert self.csm_obj.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."

    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
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
        cap_df = self.csm_obj.get_dataframe_all(self.num_nodes)
        total_written = 0
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.csm_obj.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        index = "cluster_start"
        self.log.info("[Start] Fetch degraded capacity on Consul before cluster restart")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc[index]["consul_healthy"] = resp["healthy"]
        cap_df.loc[index]["consul_degraded"] = resp["degraded"]
        cap_df.loc[index]["consul_critical"] = resp["critical"]
        cap_df.loc[index]["consul_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"])
        self.log.info("[End] Fetch degraded capacity on Consul before cluster restart")

        self.log.info("[Start] Fetch degraded capacity on HCTL before cluster restart")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
        cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
        cap_df.loc[index]["hctl_critical"] = resp["critical"]
        cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
        #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info("[End] Fetch degraded capacity on HCTL before cluster restart")

        self.log.info("[Start] Fetch degraded capacity on CSM before cluster restart")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc[index]["csm_healthy"] = resp["healthy"]
        cap_df.loc[index]["csm_degraded"] = resp["degraded"]
        cap_df.loc[index]["csm_critical"] = resp["critical"]
        cap_df.loc[index]["csm_damaged"] = resp["damaged"]
        #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        self.log.info("[End] Fetch degraded capacity on CSM before cluster restart")

        self.log.info("[Start] Stop Cluster")
        resp = self.ha_obj.cortx_stop_cluster(self.master)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Check the cluster status and start the cluster in case its still down.")
        resp = self.ha_obj.check_cluster_status(self.master)
        assert resp[0], "Failed to stop the cluster."
        self.log.info("[End] Stop Cluster")

        index = "cluster_restart"
        self.log.info("[Start] Cluster restart.")
        self.log.info("Check whether cluster restart command ran successfully.")
        resp = self.ha_obj.cortx_start_cluster(self.master)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Cluster is up and running.")
        self.log.info("Checking whether all CORTX Data pods have been restarted.")
        resp = self.ha_obj.check_pod_status(self.master)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("[End] Cluster restart.")

        self.log.info("[Start] Fetch degraded capacity on Consul after cluster restart")
        resp = self.csm_obj.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        cap_df.loc[index]["consul_healthy"] = resp["healthy"]
        cap_df.loc[index]["consul_degraded"] = resp["degraded"]
        cap_df.loc[index]["consul_critical"] = resp["critical"]
        cap_df.loc[index]["consul_damaged"] = resp["damaged"]
        #cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info("[End] Fetch degraded capacity on Consul after cluster restart")

        self.log.info("[Start] Fetch degraded capacity on HCTL after cluster restart")
        # TBD : HCTL output doest have degraded capacity yet.
        resp = self.health_helper.hctl_status_json()
        cap_df.loc[index]["hctl_healthy"] = resp["healthy"]
        cap_df.loc[index]["hctl_degraded"] = resp["degraded"]
        cap_df.loc[index]["hctl_critical"] = resp["critical"]
        cap_df.loc[index]["hctl_damaged"] = resp["damaged"]
        #cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info("[End] Fetch degraded capacity on HCTL after cluster restart")

        self.log.info("[Start] Fetch degraded capacity on CSM after cluster restart")
        resp = self.csm_obj.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc[index]["csm_healthy"] = resp["healthy"]
        cap_df.loc[index]["csm_degraded"] = resp["degraded"]
        cap_df.loc[index]["csm_critical"] = resp["critical"]
        cap_df.loc[index]["csm_damaged"] = resp["damaged"]
        #cap_df.loc[index]["csm_repaired"] = resp["repaired"]
        assert self.csm_obj.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info("[End] Fetch degraded capacity on CSM after cluster restart")

        self.log.info("Check the cluster value before and after restart are same")
        assert cap_df["cluster_restart"] == cap_df["cluster_start"], "Values are not consistent."
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
        self.log.info("Step-1: Change csm config auth variable to True in csm config")
        # TODO : change variable in csm config file to true
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.master)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header to invalid key")
        header['Authorization1'] = header.pop('Authorization')
        self.log.info("Step 5: Call degraded capacity api with invalid key in header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed for invalid key access")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, "full")
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed for invalid key access")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-34717')
    def test_34717(self):
        """
        Check the api response for appropriate error when missing Param provided
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change csm config auth variable to True in csm config")
        # TODO : change variable in csm config file to true
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header for missing params")
        header[''] = header.pop('Authorization')
        header[''] = ''
        self.log.info("Step 5: Call degraded capacity api with missing params in header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, "full")
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-34718')
    def test_34718(self):
        """
        Check the api response when telemetry_auth: 'false' and without key and value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change csm config auth variable to False in csm config")
        # TODO : change variable in csm config file to False
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header to delete key and value")
        del header['Authorization']
        self.log.info("Step 5: Call degraded capacity api with deleted key and value in header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, "full")
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-34719')
    def test_34719(self):
        """
        Check the api response when telemetry_auth: 'false' and with valid key and value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change csm config auth variable to False in csm config")
        # TODO : change variable in csm config file to False
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Call degraded capacity api with valid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, "full")
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-34720')
    def test_34720(self):
        """
        Check the api response when telemetry_auth: 'false' and invalid value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change csm config auth variable to False in csm config")
        # TODO : change variable in csm config file to False
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header for invalid value")
        header['Authorization'] = 'abc'
        self.log.info("Step 5: Call degraded capacity api with invalid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, "full")
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-34722')
    def test_34722(self):
        """
        Check the api response when telemetry_auth:'true', key=valid and value="Invalid"
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change csm config auth variable to True in csm config")
        # TODO : change variable in csm config file to true
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header for invalid value")
        header['Authorization'] = 'abc'
        self.log.info("Step 5: Call degraded capacity api with invalid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        response = self.csm_obj.get_degraded_capacity_custom_login(header, "full")
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-34723')
    def test_34723(self):
        """
        Check all required variable are coming in rest response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change csm config auth variable to True in csm config")
        # TODO : change variable in csm config file to true
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Call degraded capacity api with valid header")
        response = self.csm_obj.get_degraded_capacity_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("Step 5: Check all variables are present in rest response")
        resp = self.csm_obj.validate_metrics(response.json())
        assert_utils.assert_true(resp, "Rest data metrics check failed")
        self.log.info("Step 6: Verified metric data for bytecount")
        response = self.csm_obj.get_degraded_capacity('full')
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("Step 7: Check all variables are present in rest response")
        resp = self.csm_obj.validate_metrics(response.json(), 'full')
        assert_utils.assert_true(resp, "Rest data metrics check failed in full mode")
        self.log.info("##### Test ended -  %s #####", test_case_name)
