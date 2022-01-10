# pylint: disable=too-many-lines
#!/usr/bin/python
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
from http import HTTPStatus
import logging
import time
from random import SystemRandom
import pytest
from libs.csm.rest.csm_rest_capacity import SystemCapacity
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.ha.ha_common_libs import HALibs
from libs.s3 import s3_misc
from commons import configmanager
from commons.helpers.bmc_helper import Bmc
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons import cortxlogging
from config import CMN_CFG


class TestSystemCapacity():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.system_capacity = SystemCapacity()
        cls.cryptogen = SystemRandom()
        cls.log.info("Initiating Rest Client ...")
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_capacity.yaml")
        cls.s3user = RestS3user()
        cls.akey = ""
        cls.skey = ""
        cls.s3_user = ""
        cls.bucket = ""
        cls.health_helper = Health(CMN_CFG["nodes"][0]["hostname"],
                                   CMN_CFG["nodes"][0]["username"],
                                   CMN_CFG["nodes"][0]["password"])
        cls.ha_obj = HALibs()
        cls.node_list = []
        cls.host_list = []
        cls.bmc_list = []
        cls.username = []
        cls.password = []
        cls.num_nodes = len(CMN_CFG["nodes"])
        for node in range(cls.num_nodes):
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                continue
            host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            cls.host_list.append(host)
            cls.node_list.append(Node(hostname=host,
                                      username=cls.username[node],
                                      password=cls.password[node]))
            cls.bmc_list.append(Bmc(hostname=host,
                                    username=cls.username[node],
                                    password=cls.password[node]))

    def setup_method(self):
        """
        Setup method for creating s3 user
        """
        self.log.info("Creating S3 account")
        resp = self.s3user.create_s3_account()
        assert resp.status_code == HTTPStatus.CREATED.value, "Failed to create S3 account."
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.s3_user = resp.json()["account_name"]
        self.bucket = f"bucket{self.s3_user}"
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        assert s3_misc.create_bucket(
            self.bucket, self.akey, self.skey), "Failed to create bucket."

    def teardown_method(self):
        """
        Teardowm method for deleting s3 account created in setup.
        """
        self.log.info("Deleting bucket %s & associated objects", self.bucket)
        assert s3_misc.delete_objects_bucket(
            self.bucket, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Deleting S3 account %s created in setup", self.s3_user)
        resp = self.s3user.delete_s3_account_user(self.s3_user)
        assert resp.status_code == HTTPStatus.OK.value, "Failed to delete S3 user"

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15200')
    def test_4202(self):
        """Test REST API for GET request with default arguments return 200 and json response
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        results = self.system_capacity.parse_capacity_usage()
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

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('Dummy')
    def test_dummy(self):
        """Dummy test F-71E
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_dummy"]

        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        #results = self.system_capacity.parse_capacity_usage()
        #assert results is None
        self.log.info("[End] Checking cluster capacity")

        self.log.info("[Start] Checking degraded capacity on Consul")
        consul_resp = self.system_capacity.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        consul_resp = "Parse the result for damaged, critical,healthy... byte"
        result = self.system_capacity.verify_degraded_capacity(consul_resp, healthy=None,
                    degraded=0, critical=0, damaged=0, err_margin=test_cfg["err_margin"])
        assert result[0], result[1]
        self.log.info("[End] Checking degraded capacity on Consul")

        self.log.info("[Start] Checking degraded capacity on HCTL")
        # TBD : HCTL output doest have degraded capacity yet.
        result = self.health_helper.get_sys_capacity()
        hctl_resp = "Parse the result for damaged, critical,healthy... byte"
        result = self.system_capacity.verify_degraded_capacity(hctl_resp, healthy=None, degraded=0,
                                                               critical=0, damaged=0,
                                                               err_margin=test_cfg["err_margin"])
        assert result[0], result[1]
        self.log.info("[End] Checking degraded capacity on HCTL")

        self.log.info("[Start] Checking degraded capacity on CSM")
        resp = self.system_capacity.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        csm_resp = resp.json()
        result = self.system_capacity.verify_degraded_capacity(csm_resp, healthy=None, degraded=0,
                                                               critical=0, damaged=0,
                                                               err_margin=test_cfg["err_margin"])
        assert result[0], result[1]
        self.log.info("[End] Checking degraded capacity on CSM")

        for node in range(self.num_nodes+1):
            self.log.info("[Start] Bringing down Node %s", node)
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

            # Capacity checks
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

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")

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
        cap_df = self.system_capacity.get_dataframe_all(self.num_nodes)
        total_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.system_capacity.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.system_capacity.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"])
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
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                                                             critical=0, damaged=0,
                                                             err_margin=test_cfg["err_margin"],
                                                             total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.system_capacity.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                critical=0, damaged=0, err_margin=test_cfg["err_margin"], total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                self.log.debug("Skipping master node...")
                continue
            self.log.info("[Start] Bringing down Node %s: %s",
                          node, self.node_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=0, degraded=None,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.system_capacity.verify_degraded_capacity_all(
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
        cap_df = self.system_capacity.get_dataframe_all(self.num_nodes)
        total_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.system_capacity.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.system_capacity.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        # TBD: Write Function for constructing df from values.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.system_capacity.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                self.log.debug("Skipping master node...")
                continue
            self.log.info("[Start] Bringing down Node %s: %s",
                          node, self.node_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

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

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")

            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.system_capacity.verify_degraded_capacity_all(
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
        cap_df = self.system_capacity.get_dataframe_all(self.num_nodes)
        total_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.system_capacity.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.system_capacity.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.system_capacity.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                self.log.debug("Skipping master node...")
                continue
            self.log.info("[Start] Bringing down Node %s: %s",
                          node, self.node_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

            self.log.info("[Start] Start some IOs on %s", node)

            self.log.info("Creating custom S3 account...")
            user_data = self.s3user.create_custom_s3_payload("valid")
            resp = self.s3user.create_custom_s3_user(user_data)
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

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")

            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.system_capacity.verify_degraded_capacity_all(
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
        cap_df = self.system_capacity.get_dataframe_all(self.num_nodes)
        total_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.system_capacity.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.system_capacity.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.system_capacity.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                self.log.debug("Skipping master node...")
                continue
            self.log.info("[Start] Bringing down Node %s: %s",
                          node, self.node_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=0, degraded=None,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=0, degraded=None,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.system_capacity.verify_degraded_capacity_all(
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
        cap_df = self.system_capacity.get_dataframe_all(self.num_nodes)
        total_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.system_capacity.parse_capacity_usage()
        assert total_cap > 0, "Total capacity is less or equal to Zero."
        self.log.info("[End] Checking cluster capacity")

        self.log.info(
            "[Start] Fetch degraded capacity on Consul with 0 Node failure")
        resp = self.system_capacity.get_capacity_consul()
        # TBD : Consul output doest have degraded capacity yet.
        total_written = resp["healthy"]
        cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
        cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on HCTL with 0 Node failure")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.system_capacity.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        resp = resp.json()
        cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
        cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
        cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
        cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
        cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
        assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                    critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                    total=total_written)
        self.log.info(
            "[End] Fetch degraded capacity on CSM with 0 Node failure")

        for node in range(self.num_nodes+1):
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                self.log.debug("Skipping master node...")
                continue
            self.log.info("[Start] Bringing down Node %s: %s",
                          node, self.node_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

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

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=new_written, degraded=None, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            time.sleep(40)
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")

            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.system_capacity.verify_degraded_capacity_all(
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
        cap_df = self.system_capacity.get_dataframe_all(self.num_nodes)
        total_written = 0
        new_written = 0
        row_temp = "N{} failure"
        self.log.info("[Start] Checking cluster capacity")
        # TBD : Command is not updated on TDS yet.
        total_cap, _, _, _, _ = self.system_capacity.parse_capacity_usage()
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
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            # TBD: Write Function for constructing df from values.
            total_written = resp["healthy"]
            cap_df.loc["No failure"]["consul_healthy"] = resp["healthy"]
            cap_df.loc["No failure"]["consul_degraded"] = resp["degraded"]
            cap_df.loc["No failure"]["consul_critical"] = resp["critical"]
            cap_df.loc["No failure"]["consul_damaged"] = resp["damaged"]
            cap_df.loc["No failure"]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc["No failure"]["csm_healthy"] = resp["healthy"]
            cap_df.loc["No failure"]["csm_degraded"] = resp["degraded"]
            cap_df.loc["No failure"]["csm_critical"] = resp["critical"]
            cap_df.loc["No failure"]["csm_damaged"] = resp["damaged"]
            cap_df.loc["No failure"]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

            if CMN_CFG["nodes"][node]["node_type"] == "master":
                self.log.debug("Skipping master node...")
                continue
            self.log.info("[Start] Bringing down Node %s: %s",
                          node, self.node_list[node])
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")

            self.log.info(
                "Verified %s is powered off and not pinging.", self.host_list[node])
            self.log.info("[End] Bringing down Node %s", node)

            resp = s3_misc.delete_object(
                obj, self.bucket, self.akey, self.skey, object_size=write_bytes_mb)
            assert resp, "Delete object Failed"

            index = row_temp.format(node)
            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 1 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            total_written = total_written - new_written
            assert self.system_capacity.verify_degraded_capacity(
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=0, degraded=total_written, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 1 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM with 1 Node failure")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(
                resp, healthy=0, degraded=total_written, critical=0, damaged=0, err_margin=10,
                total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 1 Node failure")

            self.log.info(
                "[Start] Power on node back from BMC/ssc-cloud and check node status")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            # To get all the services up and running
            self.log.info("Verified %s is powered on and pinging.",
                          self.host_list[node])
            self.log.info(
                "[End] Power on node back from BMC/ssc-cloud and check node status")

            self.log.info(
                "[Start] Fetch degraded capacity on Consul with 0 Node failure")
            resp = self.system_capacity.get_capacity_consul()
            # TBD : Consul output doest have degraded capacity yet.
            cap_df.loc[index]["consul_healthy"] = resp["healthy"]
            cap_df.loc[index]["consul_degraded"] = resp["degraded"]
            cap_df.loc[index]["consul_critical"] = resp["critical"]
            cap_df.loc[index]["consul_damaged"] = resp["damaged"]
            cap_df.loc[index]["consul_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
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
            cap_df.loc[index]["hctl_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on HCTL with 0 Node failure")

            self.log.info("[Start] Fetch degraded capacity on CSM")
            resp = self.system_capacity.get_degraded_capacity()
            assert resp.status_code == HTTPStatus.OK, "Status code check failed."
            resp = resp.json()
            cap_df.loc[index]["csm_healthy"] = resp["healthy"]
            cap_df.loc[index]["csm_degraded"] = resp["degraded"]
            cap_df.loc[index]["csm_critical"] = resp["critical"]
            cap_df.loc[index]["csm_damaged"] = resp["damaged"]
            cap_df.loc[index]["csm_repaired"] = resp["repaired"]
            assert self.system_capacity.verify_degraded_capacity(resp, healthy=None, degraded=0,
                        critical=0, damaged=0, err_margin=test_cfg["err_margin"],
                        total=total_written)
            self.log.info(
                "[End] Fetch degraded capacity on CSM with 0 Node failure")

        self.log.info(
            "Summation check of the healthy bytes from each node failure for consul")
        assert self.system_capacity.verify_degraded_capacity_all(
            cap_df, self.num_nodes), "Overall check failed."
