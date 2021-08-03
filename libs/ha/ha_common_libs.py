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

"""
HA utility methods
"""
import os
import logging
import time
from commons import commands as common_cmd
from commons.utils import system_utils
from commons.exceptions import CTException
from commons import errorcodes as err
from commons import pswdmanager
from commons.constants import Rest as Const
from config import CMN_CFG, HA_CFG, S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.s3 import s3_test_lib
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.di.di_run_man import RunDataCheckManager
LOGGER = logging.getLogger(__name__)


class HALibs:
    """
    This class contains common utility methods for HA related operations.
    """

    def __init__(self):
        self.system_health = SystemHealth()
        self.setup_type = CMN_CFG["setup_type"]
        self.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        self.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        self.bmc_user = CMN_CFG["bmc"]["username"]
        self.bmc_pwd = CMN_CFG["bmc"]["password"]
        self.t_power_on = HA_CFG["common_params"]["power_on_time"]
        self.t_power_off = HA_CFG["common_params"]["power_off_time"]
        self.mgnt_ops = ManagementOPs()
        self.num_nodes = len(CMN_CFG["nodes"])
        self.s3bkt_obj = CortxCliS3BucketOperations()

    @staticmethod
    def check_csm_service(node_object, srvnode_list, sys_list):
        """
        Helper function to know the node where CSM service is running.
        :param node_object: node object for the node to execute command
        :param srvnode_list: list of srvnode names
        :param sys_list: List of system objects
        :return: boolean, system_object/error
        """
        try:
            if len(srvnode_list) == 0 or len(sys_list) == 0:
                raise ValueError("srvnode_list or sys_list list is empty")
            res = node_object.execute_cmd(
                common_cmd.CMD_PCS_SERV.format("csm_agent"))
            data = str(res, 'UTF-8')
            for index, srvnode in enumerate(srvnode_list):
                if srvnode in data:
                    LOGGER.info("CSM running on: {}".format(srvnode))
                    sys_obj = sys_list[index]
                    return True, sys_obj
        except IOError as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.check_csm_service.__name__,
                         error)
            return False, error

    @staticmethod
    def check_service_other_nodes(node_id, num_nodes, node_list):
        """
        Helper function to get services status on nodes which are online.
        :param node_id: node which is down to be skipped
        :param num_nodes: number of nodes in the cluster
        :param node_list: list of nodes in the cluster
        :return: boolean
        """
        try:
            for node in range(num_nodes):
                if node != node_id:
                    node_name = "srvnode-{}".format(node + 1)
                    LOGGER.info("Checking services on: {}".format(node_name))
                    res = node_list[node].execute_cmd(
                        common_cmd.CMD_PCS_GREP.format(node_name))
                    data = str(res, 'UTF-8')
                    for line in data:
                        if "FAILED" in line or "Stopped" in line:
                            return False
            return True
        except IOError as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.check_service_other_nodes.__name__,
                         error)
            return False

    @staticmethod
    def verify_node_health_status(
            sys_obj,
            status: list):
        """
        This method will verify node status with health show node command response
        :param sys_obj: System object
        :param status: Expected status value for node
        :return: bool, Response Message
        """
        try:
            sys_obj.open_connection()
            sys_obj.login_cortx_cli()
            resp = sys_obj.check_health_status(
                common_cmd.CMD_HEALTH_SHOW.format("node"))
            if not resp[0]:
                raise ValueError("Failed to get node health ")
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for health check for all nodes: %s",
                resp_table)
            for index, item in enumerate(resp_table):
                if item[2] != status[index].lower():
                    return False, f"Node-{int(item[1])+1}'s health status is {item[2]}"
                LOGGER.info("Node-%s's health status is %s",
                            int(item[1]) + 1, item[2])
            return True, "All node status is as expected"
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.verify_node_health_status.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error
        finally:
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection(set_session_obj_none=True)

    @staticmethod
    def verify_csr_health_status(
            sys_obj,
            status: str):
        """
        This method will Get and verify cluster, site and rack status with health show
        cluster command response
        :param sys_obj: System object
        :param status: Expected status for cluster, site and rack
        :return: bool, Response Message
        """
        try:
            sys_obj.open_connection()
            sys_obj.login_cortx_cli()
            resp = sys_obj.check_health_status(
                common_cmd.CMD_HEALTH_SHOW.format("cluster"))
            if not resp[0]:
                raise ValueError("Failed to get cluster health ")
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for health check for all nodes: %s",
                resp_table)
            for item in resp_table[:3]:
                if item[2] != status.lower():
                    return False, f"{item[0]}'s health status is {item[2]}"
                LOGGER.info("%s's health status is %s", item[0], item[2])
            return True, "Cluster, site and rack health status is as expected"
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.verify_csr_health_status.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error
        finally:
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection(set_session_obj_none=True)

    def polling_host(self,
            max_timeout: int,
            host: str,
            exp_resp: bool,
            bmc_obj):
        """
        Helper function to poll for host ping response.
        :param max_timeout: Max timeout allowed for expected response from ping
        :param host: Host to ping
        :param exp_resp: Expected resp True/False for host state Reachable/Unreachable
        :param bmc_obj: BMC object
        :return: bool
        """

        poll = time.time() + max_timeout  # max timeout
        while poll > time.time():
            time.sleep(20)
            resp = system_utils.check_ping(host)
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                vm_info = system_utils.execute_cmd(
                    common_cmd.CMD_VM_INFO.format(
                        self.vm_username, self.vm_password, vm_name))
                if not vm_info[0]:
                    raise CTException(err.CLI_COMMAND_FAILURE,
                                      msg=f"Unable to get VM power status for {vm_name}")
                data = vm_info[1].split("\\n")
                pw_state = ""
                for lines in data:
                    if 'power_state' in lines:
                        pw_state = (lines.split(':')[1].strip('," '))
                LOGGER.debug("Power state for %s : %s", host, pw_state)
                if exp_resp:
                    exp_state = pw_state == 'up'
                else:
                    exp_state = pw_state == 'down'
            else:
                resp = bmc_obj.bmc_node_power_status(bmc_obj.get_bmc_ip(), self.bmc_user, self.bmc_pwd)
                if exp_resp:
                    exp_state = "on" in resp[0]
                else:
                    exp_state = "off" in resp[0]

            if resp == exp_resp and exp_state:
                return True
        return False

    @staticmethod
    def get_iface_ip_list(node_list: list, num_nodes: int):
        """
        Helper function to get ip and interfaces for private data network ports.
        :param node_list: List of nodes in cluster
        :param num_nodes: Number of nodes in cluster
        :return: interface list, ip list
        :rtype: list,list
        """
        try:
            iface_list = []
            private_ip_list = []
            LOGGER.info(
                "Execute command to gte private data IPs for all nodes.")
            resp_ip = node_list[0].execute_cmd(
                common_cmd.CMD_HOSTS, read_lines=True)
            LOGGER.debug("Response for /etc/hosts: {}".format(resp_ip))
            for node in range(num_nodes):
                for line in resp_ip:
                    if "srvnode-{}.data.private".format(node + 1) in line:
                        ip = line.split()[0]
                        private_ip_list.append(ip)
                        res = node_list[node].execute_cmd(
                            common_cmd.CMD_IFACE_IP.format(ip), read_lines=True)
                        ifname = res[0].strip(":\n")
                        iface_list.append(ifname)

            return iface_list, private_ip_list
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.get_iface_ip_list.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error

    def host_power_on(self, host: str, bmc_obj=None):
        """
        Helper function for host power on
        :param host: Host to be power on
        :param bmc_obj: BMC object
        :rtype: boolean from polling_host() response
        """

        if self.setup_type == "VM":
            vm_name = host.split(".")[0]
            resp = system_utils.execute_cmd(
                common_cmd.CMD_VM_POWER_ON.format(
                    self.vm_username, self.vm_password, vm_name))
            if not resp[0]:
                raise CTException(err.CLI_COMMAND_FAILURE, msg=f"VM power on command not executed")
        else:
            bmc_obj.bmc_node_power_on_off(bmc_obj.get_bmc_ip(), self.bmc_user, self.bmc_pwd, "on")

        LOGGER.info("Check if %s is powered on.", host)
        # SSC cloud is taking time to on VM host hence timeout
        resp = self.polling_host(max_timeout=self.t_power_on, host=host, exp_resp=True, bmc_obj=bmc_obj)
        return resp

    def host_safe_unsafe_power_off(self, host: str, bmc_obj=None,
                                   node_obj=None, is_safe: bool = False):
        """
        Helper function for safe/unsafe host power off
        :param host: Host to be power off
        :param bmc_obj: BMC object
        :param node_obj: Node object
        :param is_safe: Power off host with safe/unsafe shutdown
        :rtype: boolean from polling_host() response
        """
        if is_safe:
            resp = node_obj.execute_cmd(cmd="shutdown -P now", exc=False)
            LOGGER.debug("Response for shutdown: {}".format(resp))
        else:
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                if not resp[0]:
                    raise CTException(err.CLI_COMMAND_FAILURE,
                                      msg=f"VM power off command not executed")
            else:
                bmc_obj.bmc_node_power_on_off(bmc_obj.get_bmc_ip(),
                                              self.bmc_user, self.bmc_pwd, "off")

        LOGGER.info("Check if %s is powered off.", host)
        # SSC cloud is taking time to off VM host hence timeout
        resp = self.polling_host(
            max_timeout=self.t_power_off, host=host, exp_resp=False, bmc_obj=bmc_obj)
        return resp

    def status_nodes_online(self, node_obj, srvnode_list, sys_list, no_nodes: int):
        """
        Helper function to check that all nodes are shown online in cortx cli/REST
        :param node_obj: Node object to execute command
        :param srvnode_list: List of srvnode names
        :param sys_list: List of system objects
        :param no_nodes: Number of nodes in system
        :rtype: None
        """
        try:
            LOGGER.info("Get the node which is running CSM service.")
            resp = self.check_csm_service(node_obj, srvnode_list, sys_list)
            if not resp[0]:
                raise CTException(err.CLI_COMMAND_FAILURE, resp[1])

            sys_obj = resp[1]
            LOGGER.info("Check all nodes health status is online in CLI and REST")
            check_rem_node = ["online" for _ in range(no_nodes)]
            cli_resp = self.verify_node_health_status(
                sys_obj, status=check_rem_node)
            if not cli_resp[0]:
                raise CTException(err.HA_BAD_NODE_HEALTH, cli_resp[1])
            LOGGER.info("CLI response for nodes health status. %s", cli_resp[1])
            rest_resp = self.system_health.verify_node_health_status_rest(exp_status=check_rem_node)
            if not rest_resp[0]:
                raise CTException(err.HA_BAD_NODE_HEALTH, rest_resp[1])
            LOGGER.info("REST response for nodes health status. %s", rest_resp[1])
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.status_nodes_online.__name__,
                         error)

    def status_cluster_resource_online(self, srvnode_list: list, sys_list: list, node_obj):
        """
        Check cluster/rack/site/nodes are shown online in Cortx CLI/REST
        :param srvnode_list: list of srvnode names
        :param sys_list: list of sys objects for all nodes
        :param node_obj: node object from which health will be verified
        """
        LOGGER.info("Check the node which is running CSM service and login to CSM on that node.")
        sys_obj = self.check_csm_service(node_obj, srvnode_list, sys_list)

        LOGGER.info("Check cluster, site and rack health status is online in CLI")
        resp = self.verify_csr_health_status(sys_obj[1], status="online")
        if not resp[0]:
            raise CTException(err.HA_BAD_CLUSTER_HEALTH, resp[1])

        LOGGER.info("Check cluster, site and rack health status is online in REST")
        resp = self.system_health.check_csr_health_status_rest(exp_status='online')
        if resp[0]:
            raise CTException(err.HA_BAD_CLUSTER_HEALTH, resp[1])

        LOGGER.info("Cluster, site and rack health status is online in CLI and REST")

        LOGGER.info("Check all nodes health status is online in CLI")
        check_rem_node = ["online" for _ in range(len(srvnode_list))]
        resp = self.verify_node_health_status(sys_obj[1], status=check_rem_node)
        if resp[0]:
            raise CTException(err.HA_BAD_NODE_HEALTH, resp[1])

        LOGGER.info("Check all nodes health status is online in REST")
        resp = self.system_health.verify_node_health_status_rest(check_rem_node)
        if resp[0]:
            raise CTException(err.HA_BAD_NODE_HEALTH, resp[1])

        LOGGER.info("Node health status is online in CLI and REST")

    def check_csr_deg_node_offline_status(self, sys_obj, node_id: int):
        """
        Check cluster/rack/site are shown degraded and node offline in Cortx CLI/REST
        :param sys_obj: System object
        :param node_id: Node to check for offline
        :return: (bool, response)
        """
        check_rem_node = [
            "offline" if num == node_id else "online" for num in range(
                self.num_nodes)]
        LOGGER.info(
            "Checking srvnode-%s status is offline via CortxCLI",
            node_id + 1)
        resp = self.verify_node_health_status(sys_obj, status=check_rem_node)
        if not resp[0]:
            raise CTException(err.HA_HEALTH_VALIDATION_ERROR, resp[1])
        LOGGER.info(
            "Checking Cluster/Site/Rack status is degraded via CortxCLI")
        resp = self.verify_csr_health_status(sys_obj, "degraded")
        if not resp[0]:
            raise CTException(err.HA_HEALTH_VALIDATION_ERROR, resp[1])
        LOGGER.info("Checking %s status is failed via REST", node_id + 1)
        resp = self.system_health.verify_node_health_status_rest(
            check_rem_node)
        if not resp[0]:
            raise CTException(err.HA_HEALTH_VALIDATION_ERROR, resp[1])
        LOGGER.info("Checking Cluster/Site/Rack status is degraded via REST")
        resp = self.system_health.check_csr_health_status_rest("degraded")
        if not resp[0]:
            raise CTException(err.HA_HEALTH_VALIDATION_ERROR, resp[1])

        return True, "cluster/rack/site are shown degraded and node offline in Cortx CLI/REST"

    def get_csm_failover_node(self, srvnode_list: list, node_list: list, sys_list: list, node: int):
        """
        This function will get new node on which CSM is failover
        :param srvnode_list: list of srvnode names
        :param node_list: list of srvnode names
        :param sys_list: List of system objects
        :param node: Node ID from which CSM failover
        :return: (bool, check_csm_service response, node_object)
        """
        LOGGER.info("Get the new node on which CSM service failover.")
        if srvnode_list[node] == srvnode_list[-1]:
            nd_obj = node_list[0]
        else:
            nd_obj = node_list[node + 1]
        resp = self.check_csm_service(nd_obj, srvnode_list, sys_list)
        if not resp[0]:
            return False, "Failed to get CSM failover node"
        return resp[0], resp[1], nd_obj

    @staticmethod
    def perf_node_operation(
            sys_obj,
            op: str,
            resource_id,
            f_start: bool = False,
            user: str = None,
            pswd: str = None):
        """
        This function will perform node start/stop/poweroff operation on resource_id
        :param op: Operation to be performed (stop/poweroff/start).
        :param sys_obj: System object
        :param resource_id: Email id of csm user
        :param f_start: If true, enables force start on node
        :param user: Manage user name
        :param pswd: Manage user password
        return: (bool, Command Response)
        """
        try:
            sys_obj.open_connection()
            sys_obj.login_cortx_cli(username=user, password=pswd)
            resp = sys_obj.node_operation(
                operation=op, resource_id=resource_id, force_op=f_start)
            return resp
        except Exception as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.perf_node_operation.__name__,
                         error)
            return False, error
        finally:
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection(set_session_obj_none=True)

    @staticmethod
    def check_pcs_status_resp(node, node_obj, hlt_obj, checknode: list):
        """
        This will get pcs status xml and hctl status json response and
        check node health status after performing node stop operation.
        :param node: Node ID for which health check is required
        :param node_obj: Node object
        :param hlt_obj: Health class object
        :param checknode: Node info required to check node health
        :return: (bool, response)
        """
        hostname = CMN_CFG["nodes"][node]["hostname"]
        username = CMN_CFG["nodes"][node]["username"]
        password = CMN_CFG["nodes"][node]["password"]
        # Get the pcs status
        status, result = system_utils.run_remote_cmd(
            cmd=common_cmd.PCS_STATUS_CMD,
            hostname=hostname,
            username=username,
            password=password,
            read_lines=True)
        if not status:
            return False, f"Failed to get PCS status {result}"
        # Get the pcs status xml
        response = node_obj.execute_cmd(
            cmd=common_cmd.CMD_PCS_GET_XML,
            read_lines=False,
            exc=False)
        if isinstance(response, bytes):
            response = str(response, 'UTF-8')
        json_format = hlt_obj.get_node_health_xml(pcs_response=response)
        crm_mon_res = json_format['crm_mon']['resources']
        no_node = int(json_format['crm_mon']['summary']
                      ['nodes_configured']['@number'])
        hctl_services_failed = {}
        clone_set_dict = hlt_obj.get_clone_set_status(crm_mon_res, no_node)
        svcs_elem = {'node': None, 'status': None}
        for pcs_key, pcs_value in clone_set_dict.items():
            hctl_services_failed['{}'.format(pcs_key)] = list()
            for srvnode, status in pcs_value.items():
                temp_svc = svcs_elem.copy()
                LOGGER.info(
                    " pcs_key = {} pcs_value = {}".format(
                        pcs_key, pcs_value))
                if srvnode == checknode[0]:
                    if status != 'Stopped':
                        temp_svc['node'] = srvnode
                        temp_svc['status'] = status
                        hctl_services_failed['{}'.format(
                            pcs_key)].append(temp_svc)
                else:
                    if status != 'Started':
                        temp_svc['node'] = srvnode
                        temp_svc['status'] = status
                        hctl_services_failed['{}'.format(
                            pcs_key)].append(temp_svc)
        # Extract data for PCS resource group elements
        resource_dict = hlt_obj.get_resource_status(crm_mon_res)
        for pcs_key, pcs_value in resource_dict.items():
            hctl_services_failed['{}'.format(pcs_key)] = list()
            if pcs_value['status'] == 'Stopped':
                temp_svc = svcs_elem.copy()
                temp_svc['status'] = pcs_value['status']
                hctl_services_failed['{}'.format(pcs_key)].append(temp_svc)
        # Extract data for PCS group elements
        group_dict = hlt_obj.get_group_status(crm_mon_res)
        for pcs_key, pcs_value in group_dict.items():
            hctl_services_failed['{}'.format(pcs_key)] = list()
            if pcs_value['status'] == 'Stopped':
                temp_svc = svcs_elem.copy()
                temp_svc['status'] = pcs_value['status']
                hctl_services_failed['{}'.format(pcs_key)].append(temp_svc)
        # Get hctl status response
        status, result = system_utils.run_remote_cmd(
            cmd=common_cmd.MOTR_STATUS_CMD,
            hostname=hostname,
            username=username,
            password=password,
            read_lines=True)
        if not status:
            return False, f"Failed to get HCTL status {result}"
        # Get hctl status --json response
        resp = hlt_obj.hctl_status_json()
        hctl_services_failed = {}
        svcs_elem = {'service': None, 'status': None}
        for node_data in resp['nodes']:
            hctl_services_failed[node_data['name']] = list()
            if node_data['name'] == checknode[1]:
                for svcs in node_data['svcs']:
                    temp_svc = svcs_elem.copy()
                    if svcs['name'] != "m0_client" and svcs['status'] == 'started':
                        temp_svc['service'] = svcs['name']
                        temp_svc['status'] = svcs['status']
                        hctl_services_failed[node_data['name']].append(
                            temp_svc)
            else:
                for svcs in node_data['svcs']:
                    temp_svc = svcs_elem.copy()
                    if svcs['name'] != "m0_client" and svcs['status'] != 'started':
                        temp_svc['service'] = svcs['name']
                        temp_svc['status'] = svcs['status']
                        hctl_services_failed[node_data['name']].append(
                            temp_svc)
        # Extract node health data which is not as expected
        node_hctl_failure = {}
        for key, val in hctl_services_failed.items():
            if val:
                node_hctl_failure[key] = val
        if node_hctl_failure:
            return False, node_hctl_failure
        return True, f"Check node health status is as expected for {checknode[1]}"

    def delete_s3_acc_buckets(self, s3_data: dict):
        """
        This function deletes s3 buckets, s3 account
        :param s3_data: Dictionary for s3 operation info
        :return: (bool, response)
        """
        try:
            for account, details in s3_data.items():
                self.s3bkt_obj.open_connection()
                s3acc_obj = CortxCliS3AccountOperations(
                    session_obj=self.s3bkt_obj.session_obj)
                login = s3acc_obj.login_cortx_cli(
                    username=details['user_name'], password=details['password'])
                if not login[0]:
                    raise CTException(err.S3_LOGGING_FAILED, login[1])
                s3_del = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"],
                                               access_key=details['accesskey'],
                                               secret_key=details['secretkey'])
                response = s3_del.delete_all_buckets()
                if not response[0]:
                    raise CTException(
                        err.S3_DELETE_BUCKET_REQUEST_FAILED, response[1])
                response = s3acc_obj.delete_s3account_cortx_cli(
                    account_name=details['user_name'])
                if not response[0]:
                    raise CTException(
                        err.S3_DELETE_ACC_REQUEST_FAILED, response[1])
                response = s3acc_obj.logout_cortx_cli()
                if not response[0]:
                    raise CTException(err.S3_LOGOUT_FAILED, response[1])
                self.s3bkt_obj.close_connection(set_session_obj_none=True)
                return True, "Successfully performed S3 operation clean up"
        except (Exception, CTException) as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.delete_s3_acc_buckets.__name__,
                         error)
            return False, error

    def perform_ios_ops(
            self,
            prefix_data: str = None,
            di_data: tuple = None,
            is_di: bool = False):
        """
        This function creates s3 acc, buckets and performs IO and DI check.
        :param prefix_data: Prefix data for IO Operation
        :param di_data: Data for DI check operation
        :param is_di: To perform DI check operation
        :return: (bool, response)
        """
        try:
            if not is_di:
                LOGGER.info("create s3 acc, buckets and upload objects.")
                users = self.mgnt_ops.create_account_users(
                    nusers=1, use_cortx_cli=False)
                io_data = self.mgnt_ops.create_buckets(
                    nbuckets=1, users=users, use_cortxcli=True)
                run_data_chk_obj = RunDataCheckManager(users=io_data)
                pref_dir = {"prefix_dir": prefix_data}
                star_res = run_data_chk_obj.start_io(
                    users=io_data, buckets=None, files_count=8, prefs=pref_dir)
                if not star_res:
                    raise CTException(err.S3_START_IO_FAILED, star_res)
                return True, run_data_chk_obj, io_data
            else:
                LOGGER.info("Checking DI for IOs run.")
                stop_res = di_data[0].stop_io(users=di_data[1], di_check=is_di)
                if not stop_res[0]:
                    raise CTException(err.S3_STOP_IO_FAILED, stop_res[1])
                del_resp = self.delete_s3_acc_buckets(di_data[1])
                if not del_resp[0]:
                    raise CTException(err.S3_STOP_IO_FAILED, del_resp[1])
                return True, "Di check for IOs passed successfully"
        except (Exception, CTException) as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HALibs.perform_ios_ops.__name__,
                         error)
            return False, error
