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

"""SSPL test cases: Primary Node."""

import logging
import secrets
import time

import pytest

from commons import cortxlogging
from commons.constants import CONF_SSPL_SRV_THRS_INACT_TIME
from commons.constants import LOG_STORE_PATH
from commons.constants import SSPL_CFG_URL
from commons.constants import SwAlerts as const
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG
from config import RAS_VAL
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.ras.sw_alerts import SoftwareAlert
from libs.ras.sw_alerts_gui import SoftwareAlertGUI

LOGGER = logging.getLogger(__name__)


class Test3PSvcMonitoringGUI:
    """3rd party service monitoring test suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("############ Running setup_class ############")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.sspl_stop = cls.changed_level = cls.selinux_enabled = False
        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.sw_alert_obj = SoftwareAlert(cls.host, cls.uname, cls.passwd)
        cls.svc_path_dict = {}
        cls.sspl_cfg_url = SSPL_CFG_URL
        cls.intrmdt_state_timeout = \
            RAS_VAL["ras_sspl_alert"]["os_lvl_monitor_timeouts"]["intrmdt_state"]
        cls.sspl_thrs_inact_time = CONF_SSPL_SRV_THRS_INACT_TIME
        cls.thrs_inact_time_org = None
        cls.setup_type = CMN_CFG["setup_type"]
        if cls.setup_type == "VM":
            cls.external_svcs = const.SVCS_3P_ENABLED_VM
        else:
            cls.external_svcs = const.SVCS_3P
        # required for Robot_GUI
        cls.ras_gui_obj = SoftwareAlertGUI()
        LOGGER.info("External service list : %s", cls.external_svcs)
        LOGGER.info("############ Completed setup_class ############")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("############ Running setup_method ############")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        self.timeouts = common_cfg["os_lvl_monitor_timeouts"]

        LOGGER.info("Check that all the 3rd party services are active")
        resp = self.sw_alert_obj.get_inactive_svcs(self.external_svcs)
        assert resp == [], f"{resp} are in inactive state"
        LOGGER.info("All 3rd party services are in active state.")

        self.starttime = time.time()
        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd()
            assert_utils.assert_true(resp, "Failed to start message bus reader")
            LOGGER.info("Successfully started read_message_bus.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")
        LOGGER.info("############ Setup method completed ############")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("############ Performing Teardown operation ############")
        resp = self.ras_test_obj.get_conf_store_vals(
            url=self.sspl_cfg_url, field=self.sspl_thrs_inact_time)
        if resp != self.thrs_inact_time_org:
            LOGGER.info("Restore threshold_inactive_time to %s", self.thrs_inact_time_org)
            self.ras_test_obj.set_conf_store_vals(
                url=self.sspl_cfg_url,
                encl_vals={"CONF_SSPL_SRV_THRS_INACT_TIME": self.thrs_inact_time_org})
            resp = self.ras_test_obj.get_conf_store_vals(
                url=self.sspl_cfg_url, field=self.sspl_thrs_inact_time)
            assert resp == self.thrs_inact_time_org, "Unable to restore threshold_inactive_time " \
                                                     "in teardown"
            LOGGER.info("Successfully restored threshold_inactive_time to : %s", resp)

        LOGGER.info("Restore service config for all the 3rd party services")
        self.sw_alert_obj.restore_svc_config(
            teardown_restore=True, svc_path_dict=self.svc_path_dict)
        for svc in self.external_svcs:
            response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                     timeout=const.SVC_LOAD_TIMEOUT_SEC)
            LOGGER.info("Service recovery details : %s", response)
            assert response["state"] == "active", f"Unable to recover the {svc} service"
        LOGGER.info("All 3rd party services recovered and in active state.")

        if self.changed_level:
            kv_store_path = LOG_STORE_PATH
            common_cfg = RAS_VAL["ras_sspl_alert"]["sspl_config"]
            res = self.ras_test_obj.update_threshold_values(
                kv_store_path, common_cfg["sspl_log_level_key"],
                common_cfg["sspl_log_dval"],
                update=True)
            assert_utils.assert_true(res)

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.node_obj.read_file(
            filename=self.cm_cfg["file"]["sspl_log_file"],
            local_path=self.cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug("======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug("======================================================")

        LOGGER.info("Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        try:
            self.node_obj.remove_file(filename=self.cm_cfg["file"]["sspl_log_file"])
            if self.start_msg_bus:
                LOGGER.info("Terminating the process read_message_bus.py")
                self.ras_test_obj.kill_remote_process("read_message_bus.py")
                files = [self.cm_cfg["file"]["alert_log_file"],
                         self.cm_cfg["file"]["extracted_alert_file"],
                         self.cm_cfg["file"]["screen_log"]]
                for file in files:
                    LOGGER.info("Removing log file %s from the Node", file)
                    self.node_obj.remove_file(filename=file)
        except FileNotFoundError as error:
            LOGGER.warning(error)
        LOGGER.info("############ Successfully performed Teardown operation ############")

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-21265")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21265_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : SaltStack
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "salt-master.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)

        svc = "salt-minion.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21257")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21257_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : ElasticSearch-OSS
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "elasticsearch.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21256")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21256_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Consul
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "hare-consul-agent.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21258")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21258_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Scsi-network-relay
        """
        assert_utils.assert_equals(self.setup_type, "HW", 'Test valid on HW only')
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "scsi-network-relay.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21260")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21260_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Statsd
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "statsd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21266")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21266_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : GlusterFS
        """
        assert_utils.assert_equals(self.setup_type, "HW", 'Test valid on HW only')
        # TODO: may need to update after BUG : EOS-20795
        # TODO: verify while TE
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "glusterd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21264")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21264_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Lustre
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "lnet.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21261")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21261_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Rsyslog
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "rsyslog.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Rsyslog is the medium to raise alerts. So when Rsyslog is down, no alerts will come.
        # Once Rsyslog is up, then both alerts will come.
        # LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        # self.ras_gui_obj.verify_sw_service_inactive_alert(svc)
        # TODO: verify while TE

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Rsyslog is the medium to raise alerts. So when Rsyslog is down, no alerts will come.
        # Once Rsyslog is up, then both alerts will come.
        # LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        # self.ras_gui_obj.verify_sw_service_inactive_alert(svc)
        # TODO: verify while TE

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21263")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21263_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : OpenLDAP
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "slapd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21267")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21267_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Multipathd
        """
        assert_utils.assert_equals(self.setup_type, "HW", 'Test valid on HW only')
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "multipathd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service is in deactivat state service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21259")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_21259_3ps_monitoring_gui(self):
        """
        CSM GUI: Verify Alerts for SW Service : Kafka
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "kafka.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_init(svc)

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Kafka is the medium to raise alerts. So when Kafka is down, no alerts will come.
        # Once Kafka is up, then both alerts will come.
        # LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        # self.ras_gui_obj.verify_sw_service_inactive_alert(svc)
        # TODO: verify while TE

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service inactive alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_inactive_alert_resolved(svc)

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Kafka is the medium to raise alerts. So when Kafka is down, no alerts will come.
        # Once Kafka is up, then both alerts will come.
        # LOGGER.info(" verify the sw service is in inactive state service:  %s ------", svc)
        # self.ras_gui_obj.verify_sw_service_inactive_alert(svc)

        LOGGER.info("Start the %s service again", svc)
        response = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                                 timeout=const.SVC_LOAD_TIMEOUT_SEC)
        LOGGER.info("Service recovery details : %s", response)
        assert response["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        LOGGER.info(" verify the sw service deactivat alert is in resolved state :  %s ------", svc)
        self.ras_gui_obj.verify_sw_service_deactivat_alert_resolved(svc)

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-19878")
    def test_19878_multiple_services_monitoring_gui(self):
        """
        Multiple 3rd party services monitoring and management
        """
        secure_range = secrets.SystemRandom()
        starttime = time.time()
        # svc = "salt-master.service"
        # LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        # self.ras_gui_obj.verify_sw_service_init(svc)
        # TODO: enable while TE

        LOGGER.info("Stopping multiple randomly selected services")
        num_services = secure_range.randrange(0, len(self.external_svcs))
        random_services = secure_range.sample(self.external_svcs, num_services)
        self.node_obj.send_systemctl_cmd("stop", services=random_services)
        LOGGER.info("Checking that %s services are in stopped state", random_services)
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=random_services,
                                                decode=True, exc=False)
        stat_list = list(filter(lambda j: resp[j] == "active", range(0, len(resp))))
        active_list = []
        if stat_list:
            for i in stat_list:
                active_list.append(random_services[i])
            assert_utils.assert_true(False, f"Failed to put {active_list} services in "
                                            "stopped/inactive state")
        LOGGER.info("Successfully stopped %s", random_services)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        LOGGER.info("Wait completed")

        LOGGER.info("Check if fault alert is generated for %s services", random_services)
        resp = self.csm_alert_obj.wait_for_alert(200, starttime, const.ResourceType.SW_SVC, False)
        assert resp[0], resp[1]

        LOGGER.info("Starting %s", random_services)
        self.node_obj.send_systemctl_cmd("start", services=random_services)
        LOGGER.info("Checking that %s services are in active state", random_services)
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=random_services,
                                                decode=True, exc=False)
        stat_list = list(filter(lambda j: resp[j] != "active", range(0, len(resp))))
        inactive_list = []
        if stat_list:
            for i in stat_list:
                inactive_list.append(random_services[i])
            assert_utils.assert_true(False, f"Failed to put {inactive_list} services in "
                                            "active state")
        LOGGER.info("Successfully started %s", random_services)

        time.sleep(self.timeouts["alert_timeout"])
        LOGGER.info("Check if fault_resolved alert is generated for %s services", random_services)
        resp = self.csm_alert_obj.wait_for_alert(200, starttime, const.ResourceType.SW_SVC, True)
        assert resp[0], resp[1]
