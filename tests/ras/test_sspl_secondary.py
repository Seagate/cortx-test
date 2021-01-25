#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import pytest
import logging
from commons.libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.s3_helper import S3Helper
from commons import constants as cons
from commons import commands as common_cmd
from commons.utils import config_utils as conf_util
from commons.utils.assert_utils import *
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_csmuser import RestCsmUser

CSM_ALERT_OBJ = SystemAlerts()
CSM_USER_OBJ = RestCsmUser()

RAS_TEST_CFG = conf_util.read_yaml(cons.SSPL_TEST_CONFIG_PATH)[1]
COMMON_CONF = conf_util.read_yaml(cons.COMMON_CONFIG_PATH)[1]
RAS_VAL = conf_util.read_yaml(cons.RAS_CONFIG_PATH)[1]
BYTES_TO_READ = cons.BYTES_TO_READ
LOGGER = logging.getLogger(__name__)

test_data = [COMMON_CONF["host2"]]


class SSPLTest:
    """
    SSPL Test Suite
    """
    @pytest.mark.parametrize("host", test_data)
    def setup_module(self, host):
        cm_cfg = RAS_VAL["ras_sspl_alert"]
        self.host2 = host
        self.host = COMMON_CONF["host"]
        self.uname = COMMON_CONF["username"]
        self.passwd = COMMON_CONF["password"]

        self.ras_test_obj = RASTestLib(host=self.host, username=self.uname,
                                       password=self.passwd)
        self.node_obj = Node(hostname=self.host, username=self.uname,
                             password=self.passwd)
        self.health_obj = Health(hostname=self.host, username=self.uname,
                                 password=self.passwd)
        try:
            self.s3obj = S3Helper()
        except:
            self.s3obj = S3Helper.get_instance()

        self.ras_test_obj2 = RASTestLib(host=self.host2, username=self.uname,
                                        password=self.passwd)
        self.node_obj2 = Node(hostname=self.host2, username=self.uname,
                              password=self.passwd)
        self.health_obj2 = Health(hostname=self.host2, username=self.uname,
                                  password=self.passwd)

        # Enable this flag for starting RMQ channel
        self.start_rmq = cm_cfg["start_rmq"]

        field_list = ["primary_controller_ip", "secondary_controller_ip",
                      "primary_controller_port", "secondary_controller_port",
                      "user", "password", "secret"]
        LOGGER.info("Putting expected values in KV store")
        for field in field_list:
            res = self.ras_test_obj.put_kv_store(COMMON_CONF["enclosure_user"],
                                                 COMMON_CONF["enclosure_pwd"],
                                                 field)
            assert res is True

    def setup_function(self):
        """
        Setup operations
        """
        self.starttime = time.time()
        cm_cfg = RAS_VAL["ras_sspl_alert"]

        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj2.retain_config(cm_cfg["file"][
                                             "original_sspl_conf"], False)

        LOGGER.info("Performing Setup operations")

        LOGGER.info("Checking SSPL state file")
        res = self.ras_test_obj2.get_sspl_state()
        if not res:
            LOGGER.info("SSPL not present updating same on server")
            response = self.ras_test_obj2.check_status_file()
            assert response[0] is True, response[1]
        LOGGER.info("Done Checking SSPL state file")

        LOGGER.info("Delete keys with prefix SSPL_")
        cmd = common_cmd.REMOVE_UNWANTED_CONSUL
        response = self.node_obj2.execute_cmd(cmd=cmd,
                                              read_nbytes=BYTES_TO_READ)
        assert response[0] is True, response[1]

        LOGGER.info("Restarting sspl service")
        self.health_obj2.restart_pcs_resource(cm_cfg["sspl_resource_id"],
                                              shell=False)
        time.sleep(cm_cfg["after_service_restart_sleep_val"])
        LOGGER.info(
            "Verifying the status of sspl and rabittmq service is online")

        # Getting SSPl and RabbitMQ service status
        services = cm_cfg["service"]
        for service in services:
            resp = self.s3obj.get_s3server_service_status(
                service=service, host=self.host, user=self.uname,
                pwd=self.passwd)
            assert resp is True

        LOGGER.info(
            "Validated the status of sspl and rabittmq service are online")

        if self.start_rmq:
            LOGGER.info("Running rabbitmq_reader.py script on node")
            resp = self.ras_test_obj2.start_rabbitmq_reader_cmd(
                cm_cfg["sspl_exch"], cm_cfg["sspl_key"])
            assert resp is True, "Failed to start RMQ channel"
            LOGGER.info(
                "Successfully started rabbitmq_reader.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        cmd = common_cmd.CHECK_SSPL_LOG_FILE. \
            format(cm_cfg["file"]["sspl_log_file"])
        response = self.node_obj2.execute_cmd(cmd=cmd,
                                              read_nbytes=BYTES_TO_READ)
        assert response[0] is True, response[1]
        LOGGER.info("Started collection of sspl logs")

        LOGGER.info("Successfully performed Setup operations")

    def teardown_function(self):
        """
        Teardown operations
        """
        LOGGER.info("Performing Teardown operation")
        cm_cfg = RAS_VAL["ras_sspl_alert"]
        self.ras_test_obj2.retain_config(cm_cfg["file"]["original_sspl_conf"],
                                         True)

        if self.start_rmq:
            LOGGER.info("Terminating the process rabbitmq_reader.py")
            self.ras_test_obj2.kill_remote_process("rabbitmq_reader.py")

        if os.path.exists(cm_cfg["file"]["telnet_xml"]):
            LOGGER.info("Remove telnet file")
            os.remove(cm_cfg["file"]["telnet_xml"])

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj2.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.node_obj2.read_file(cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")

        LOGGER.info(
            "Removing file {}".format(cm_cfg["file"]["sspl_log_file"]))
        self.node_obj2.remove_file(filename=cm_cfg["file"]["sspl_log_file"])

        if self.start_rmq:
            files = [cm_cfg["file"]["alert_log_file"],
                     cm_cfg["file"]["extracted_alert_file"],
                     cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info(f"Removing log file {file} from the Node")
                self.node_obj2.remove_file(filename=file)

        self.health_obj2.restart_pcs_resource(
            resource=cm_cfg["sspl_resource_id"], shell=False)
        time.sleep(cm_cfg["sleep_val"])

        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-14034", "pacemaker_sspl", "sw_alert")
    def test_1648(self):
        """
        EOS-10619: Pacemaker Resource Agents for SSPL service(Stop sspl service
        on Node)
        """
        LOGGER.info(
            "STARTED: Pacemaker Resource Agents for SSPL service(Stop sspl "
            "service on Node)")
        cm_cfg = RAS_VAL["ras_sspl_alert"]
        service_cfg = cm_cfg["service"]
        nodes = COMMON_CONF["nodes"]
        test_cfg = RAS_TEST_CFG["test_1648"]

        LOGGER.info(
            "Step 1: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 1: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 2: Checking sspl-ll service status on secondary "
                    "node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 2: Sspl-ll is up and running on secondary node")

        LOGGER.info("Step 3: Checking sspl state on both the nodes")
        res = self.ras_test_obj.get_sspl_state()
        LOGGER.info(f"State of sspl on {nodes[0]} is {res[1]}")

        res = self.ras_test_obj2.get_sspl_state()
        LOGGER.info(f"State of sspl on {nodes[1]} is {res[1]}")

        LOGGER.info(f"Step 4: Stopping sspl-ll service on node {nodes[1]}")
        resp = self.ras_test_obj2.enable_disable_service(
            "disable", service_cfg["sspl_service"])
        assert resp[0] is False, resp[1]
        LOGGER.info(f"Step 4: SSPL service was successfully stopped and "
                    f"validated on node {nodes[1]}")

        time.sleep(cm_cfg["sleep_val"])

        LOGGER.info("Step 5: Checking if sspl-ll is restarted automatically "
                    "by pacemaker")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info(f"Step 5: Sspl-ll is up and running on node {nodes[1]}")

        LOGGER.info("Inducing FAN alert")
        buffer_sz = test_cfg["buffer_sz"]

        LOGGER.info(
            "Step 6: Run 'ipmitool sdr list' to inquire about FAN "
            "state/details")
        fan_name = self.ras_test_obj2.get_fan_name()
        LOGGER.info(f"Step 6: FAN to be used for inducing fault: {fan_name}")

        LOGGER.info("Step 7: Generating fan alert using ipmi tool")
        cmd = test_cfg["ipmitool_event"].format(fan_name, test_cfg["op"])
        LOGGER.info(f"Running command: {cmd}")
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)

        LOGGER.info("SEL response : {}".format(resp))
        assert resp[0] is True, resp[1]
        LOGGER.info(
            f"Step 7: Successfully generated fault on fan {fan_name}")

        time.sleep(test_cfg["wait_time"])
        LOGGER.info("Step 8: Checking CSM REST API for no alerts")
        csm_resp = CSM_ALERT_OBJ.verify_csm_response(self.starttime,
                                                     test_cfg["alert_type"],
                                                     False,
                                                     test_cfg["resource_type"])

        LOGGER.info(f"Step 9: Resolving fan fault using ipmi tool")
        cmd = cons.RESOLVE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info(f"Running command: {cmd}")
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)
        LOGGER.info("SEL response : {}".format(resp))
        assert resp[0] is True, resp[1]
        LOGGER.info(f"Step 9: Successfully resolved fault on fan {fan_name}")

        if self.start_rmq:
            time.sleep(test_cfg["wait_time"])
            LOGGER.info("Step 10: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            LOGGER.debug(f"RMQ alert check: {alert_list}")
            self.ras_test_obj2.alert_validation(alert_list)
            LOGGER.info(
                "Step 10: Successfully verified the RabbitMQ channel for alert "
                "responses")

        assert csm_resp is True, "No alert should be seen in CSM REST API"
        LOGGER.info(
            "Step 8: Successfully checked CSM REST API for no alerts")

        LOGGER.info(
            "ENDED: Pacemaker Resource Agents for SSPL service(Stop sspl "
            "service on Node)")

    @pytest.skip
    @pytest.mark.ras
    @pytest.mark.tags("TEST-14035", "pacemaker_sspl", "sw_alert")
    def test_1783(self):
        """
        EOS-10620: Run SSPL in degraded mode (Fail  SSPL service)
        """
        LOGGER.info(
            "STARTED: Run SSPL in degraded mode (Fail  SSPL service)")
        cm_cfg = RAS_VAL["ras_sspl_alert"]
        service_cfg = cm_cfg["service"]
        nodes = COMMON_CONF["nodes"]
        test_cfg = RAS_TEST_CFG["test_1648"]

        LOGGER.info(
            "Step 1: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 1: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 2: Checking sspl-ll service status on secondary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 2: Sspl-ll is up and running on secondary node")

        LOGGER.info(f"Step 3: Checking sspl state on {nodes[0]}")
        res = self.ras_test_obj.get_sspl_state()
        LOGGER.info(f"State of sspl on {nodes[0]} is {res[1]}")

        LOGGER.info(f"Step 3: Checking sspl state on {nodes[1]}")
        res = self.ras_test_obj2.get_sspl_state()
        LOGGER.info(f"State of sspl on {nodes[1]} is {res[1]}")

        LOGGER.info(f"Step 4: Killing sspl-ll service on node {nodes[1]}")
        resp = HA_TEST_OBJ.check_service_recovery(service_cfg["sspl_service"],
                                                  nodes[1])

        assert resp is True
        LOGGER.info(f"Step 4: SSPL service was successfully killed and "
                    f"validated on node {nodes[1]}")

        time.sleep(cm_cfg["sleep_val"])

        LOGGER.info("Step 5: Checking if sspl-ll is restarted automatically "
                    "by pacemaker")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info(f"Step 5: Sspl-ll is up and running on node {nodes[1]}")

        LOGGER.info("Inducing FAN alert")
        buffer_sz = test_cfg["buffer_sz"]

        LOGGER.info(
            "Step 6: Run 'ipmitool sdr list' to inquire about FAN "
            "state/details")
        fan_name = self.ras_test_obj2.get_fan_name()
        LOGGER.info(f"Step 6: FAN to be used for inducing fault: {fan_name}")

        LOGGER.info("Step 7: Generating fan alert using ipmi tool")
        cmd = test_cfg["ipmitool_event"].format(fan_name, test_cfg["op"])
        LOGGER.info(f"Running command: {cmd}")
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)
        LOGGER.info("SEL response : {}".format(resp))
        assert resp[0] is True, resp[1]

        LOGGER.info(
            f"Step 7: Successfully generated fault on fan {fan_name}")

        time.sleep(test_cfg["wait_time"])
        LOGGER.info("Step 8: Checking CSM REST API for no alerts")
        csm_resp = CSM_ALERT_OBJ.verify_csm_response(self.starttime,
                                                     test_cfg["alert_type"],
                                                     False,
                                                     test_cfg["resource_type"])

        LOGGER.info(f"Step 9: Resolving fan fault using ipmi tool")
        cmd = cons.RESOLVE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info(f"Running command: {cmd}")
        resp = self.node_obj2.execute_cmd(cmd=cmd,
                                          read_nbytes=buffer_sz)
        LOGGER.info("SEL response : {}".format(resp))
        assert resp[0] is True, resp[1]
        LOGGER.info(f"Step 9: Successfully resolved fault on fan {fan_name}")

        if self.start_rmq:
            time.sleep(test_cfg["wait_time"])
            LOGGER.info("Step 10: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            LOGGER.debug(f"RMQ alert check: {alert_list}")
            self.ras_test_obj2.alert_validation(alert_list)
            LOGGER.info(
                "Step 10: Successfully verified the RabbitMQ channel for alert "
                "responses")

        assert csm_resp is True, "No alert should be seen in CSM REST API"
        LOGGER.info(
            "Step 8: Successfully checked CSM REST API for no alerts")

        LOGGER.info(
            "ENDED: Pacemaker Resource Agents for SSPL service(Stop sspl "
            "service on Node)")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-14794", "pacemaker_sspl", "sw_alert")
    def test_1645(self):
        """
        EOS-10618: Pacemaker Resource Agents for SSPL service (Reboot the Node
        server)
        """
        LOGGER.info(
            "STARTED: Pacemaker Resource Agents for SSPL service (Reboot the "
            "Node server)")
        cm_cfg = RAS_VAL["ras_sspl_alert"]
        test_cfg = RAS_TEST_CFG["test_1645"]

        LOGGER.info(
            "Step 1: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 1: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 2: Checking sspl-ll service status on secondary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 2: Sspl-ll is up and running on secondary node")

        LOGGER.info("Checking sspl state on node {0}".format(self.host2))
        res = self.ras_test_obj2.get_sspl_state_pcs()
        LOGGER.info("SSPL state is {0}".format(res))

        master_node = res["masters"].replace("srv", "eos")
        slave_node = res["slaves"].replace("srv", "eos")

        node_obj_master = Node(hostname=master_node, username=self.uname,
                               password=self.passwd)
        node_obj_slave = Node(hostname=slave_node, username=self.uname,
                              password=self.passwd)
        ras_obj_slave = RASTestLib(hostname=slave_node, username=self.uname,
                                   password=self.passwd)
        LOGGER.info(
            "Step 3: Rebooting node {0} having sspl service status as active"
            .format(master_node))
        resp = node_obj_master.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                           read_nbytes=test_cfg["buffer_sz"])
        assert resp[0] is True, resp[1]
        LOGGER.info(
            "Step 3: Rebooted node: {0}, Response: {1}".format(
                master_node, resp[1]))

        LOGGER.info(
            "Step 4: Inducing FAN alert on node {0}".format(slave_node))

        LOGGER.info(
            "Run 'ipmitool sdr list' to inquire about FAN state/details")
        fan_name = ras_obj_slave.get_fan_name()
        LOGGER.info(
            "FAN to be used for inducing fault: {0}".format(fan_name))

        LOGGER.info("Generating fan alert using ipmi tool")
        cmd = cons.GENERATE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info(f"Running command: {cmd}")
        resp = node_obj_slave.execute_cmd(cmd=cmd,
                                          read_nbytes=test_cfg["buffer_sz"])
        LOGGER.info("SEL response : {}".format(resp))
        assert resp[0] is True, resp[1]
        LOGGER.info(
            "Step 4: Successfully generated fault on fan {0}".format(fan_name))

        time.sleep(test_cfg["alert_delay"])
        LOGGER.info("Step 5: Checking CSM REST API for no alerts")
        csm_resp = CSM_ALERT_OBJ.verify_csm_response(self.starttime,
                                                     test_cfg["alert_type"],
                                                     False,
                                                     test_cfg["resource_type"])

        LOGGER.info("Step 6: Resolving fan fault using ipmi tool")
        cmd = cons.RESOLVE_FAN_FAULT.format(fan_name, test_cfg["op"])
        LOGGER.info(f"Running command: {cmd}")
        resp = node_obj_slave.execute_cmd(cmd=cmd,
                                          read_nbytes=test_cfg["buffer_sz"])
        LOGGER.info("SEL response : {}".format(resp))
        assert resp[0] is True, resp[1]
        LOGGER.info(
            "Step 6: Successfully resolved fault on fan {0}".format(fan_name))

        if self.start_rmq:
            time.sleep(test_cfg["alert_delay"])
            LOGGER.info("Step 6: Checking the generated alert logs on node {}"
                        .format(slave_node))
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            LOGGER.debug(f"RMQ alert check: {alert_list}")
            resp = ras_obj_slave(alert_list, restart=False)
            assert resp[0] is True, resp[1]
            LOGGER.info(
                "Step 6: Successfully verified the RabbitMQ channel for fan "
                "alert responses")

        LOGGER.info(
            "Waiting for {0} sec for node {1} and services to come online"
            .format(test_cfg["reboot_delay"], master_node))
        time.sleep(test_cfg["reboot_delay"])

        LOGGER.info(
            "Step 7: Checking sspl-ll service status on primary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 7: Sspl-ll is up and running on primary node")

        LOGGER.info("Step 8: Checking sspl-ll service status on secondary node")
        resp = self.s3obj.get_s3server_service_status(
            service=cm_cfg["service"]["sspl_service"], host=self.host2,
            user=self.uname, pwd=self.passwd)
        assert resp is True
        LOGGER.info("Step 8: Sspl-ll is up and running on secondary node")

        LOGGER.info("Checking sspl state on node {0}".format(self.host2))
        res = self.ras_test_obj2.get_sspl_state_pcs()
        LOGGER.info("SSPL state is {0}".format(res))

        LOGGER.info(
            "Step 9: Check if sspl services has swap their roles after a node "
            "reboot")
        compare(slave_node, res["masters"].replace("srv", "eos"))
        compare(master_node, res["slaves"].replace("srv", "eos"))

        assert csm_resp is True, "No alert should be seen in CSM REST API"
        LOGGER.info(
            "Step 8: Successfully checked CSM REST API for no alerts")

        LOGGER.info(
            "Step 9: Verified that sspl services has swap their roles after a "
            "node reboot")
        LOGGER.info(
            "ENDED: Pacemaker Resource Agents for SSPL service (Reboot the "
            "Node server)")
