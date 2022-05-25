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

"""
HA utility methods
"""
import logging
import os
import time
from multiprocessing import Process

from commons import commands as common_cmd
from commons import errorcodes as err
from commons import pswdmanager
from commons import constants as common_const
from commons.constants import Rest as Const
from commons.exceptions import CTException
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.helpers.health_helper import Health
from config import CMN_CFG, HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_run_man import RunDataCheckManager
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from scripts.s3_bench import s3bench

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes'
# pylint: disable=too-many-public-methods
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
            "QA_VM_POOL_PASSWORD", HA_CFG["vm_params"]["passwd"])
        self.bmc_user = CMN_CFG["bmc"]["username"]
        self.bmc_pwd = CMN_CFG["bmc"]["password"]
        self.t_power_on = HA_CFG["common_params"]["power_on_time"]
        self.t_power_off = HA_CFG["common_params"]["power_off_time"]
        self.mgnt_ops = ManagementOPs()
        self.num_nodes = len(CMN_CFG["nodes"])
        self.s3_rest_obj = S3AccountOperationsRestAPI()
        self.parallel_ios = None

    @staticmethod
    def check_csm_service(node_object, srvnode_list, sys_list):
        """
        Helper function to know the node where CSM service is running
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
                    LOGGER.info("CSM running on: %s", srvnode)
                    sys_obj = sys_list[index]
                    return True, sys_obj
        except IOError as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.check_csm_service.__name__, error)
            return False, error
        return False, "Not able to check CSM services"

    @staticmethod
    def check_service_other_nodes(node_id, num_nodes, node_list):
        """
        Helper function to get services status on nodes which are online
        :param node_id: node which is down to be skipped
        :param num_nodes: number of nodes in the cluster
        :param node_list: list of nodes in the cluster
        :return: boolean
        """
        try:
            for node in range(num_nodes):
                if node != node_id:
                    node_name = "srvnode-{}".format(node + 1)
                    LOGGER.info("Checking services on: %s", node_name)
                    res = node_list[node].execute_cmd(
                        common_cmd.CMD_PCS_GREP.format(node_name))
                    data = str(res, 'UTF-8')
                    for line in data:
                        if "FAILED" in line or "Stopped" in line:
                            return False
            return True
        except IOError as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.check_service_other_nodes.__name__, error)
            return False

    @staticmethod
    def verify_node_health_status(sys_obj, status: list):
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
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.verify_node_health_status.__name__, error)
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
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.verify_csr_health_status.__name__, error)
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
        Helper function to poll for host ping response
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
                out = bmc_obj.bmc_node_power_status(self.bmc_user, self.bmc_pwd)
                if exp_resp:
                    exp_state = "on" in out
                else:
                    exp_state = "off" in out

            if resp == exp_resp and exp_state:
                return True
        return False

    @staticmethod
    def get_iface_ip_list(node_list: list, num_nodes: int):
        """
        Helper function to get ip and interfaces for private data network ports
        :param node_list: List of nodes in cluster
        :param num_nodes: Number of nodes in cluster
        :return: interface list, ip list
        :rtype: list,list
        """
        LOGGER.info("Get the list of private data interfaces for all %s nodes.", num_nodes)
        try:
            iface_list = []
            private_ip_list = []
            LOGGER.info(
                "Execute command to gte private data IPs for all nodes.")
            resp_ip = node_list[0].execute_cmd(
                common_cmd.CMD_HOSTS, read_lines=True)
            LOGGER.debug("Response for /etc/hosts: %s", resp_ip)
            for node in range(num_nodes):
                for line in resp_ip:
                    if "srvnode-{}.data.private".format(node + 1) in line:
                        ip_addr = line.split()[0]
                        private_ip_list.append(ip_addr)
                        res = node_list[node].execute_cmd(
                            common_cmd.CMD_IFACE_IP.format(ip_addr), read_lines=True)
                        ifname = res[0].strip(":\n")
                        iface_list.append(ifname)
            LOGGER.debug("List of private data IP : %s and interfaces on all nodes: %s",
                         private_ip_list, iface_list)
            return iface_list, private_ip_list
        except Exception as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.get_iface_ip_list.__name__, error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error

    def host_power_on(self, host: str, bmc_obj=None):
        """
        Helper function for host power on
        :param host: Host to be power on
        :param bmc_obj: BMC object
        :rtype: boolean from polling_host() response
        """
        LOGGER.info("Powering on %s", host)
        if self.setup_type == "VM":
            vm_name = host.split(".")[0]
            resp = system_utils.execute_cmd(
                common_cmd.CMD_VM_POWER_ON.format(
                    self.vm_username, self.vm_password, vm_name))
            if not resp[0]:
                raise CTException(err.CLI_COMMAND_FAILURE, msg="VM power on command not executed")
        else:
            bmc_obj.bmc_node_power_on_off(self.bmc_user, self.bmc_pwd, "on")

        LOGGER.info("Check if %s is powered on.", host)
        # SSC cloud is taking time to on VM host hence timeout
        resp = self.polling_host(max_timeout=self.t_power_on, host=host,
                                 exp_resp=True, bmc_obj=bmc_obj)
        LOGGER.info("Powered on status for host %s is %s.", host, resp)
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
            LOGGER.info("Safe shutdown %s", host)
            resp = node_obj.execute_cmd(cmd="shutdown -P now", exc=False)
            LOGGER.debug("Response for shutdown: %s", resp)
        else:
            LOGGER.info("Unsafe shutdown %s", host)
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                if not resp[0]:
                    raise CTException(err.CLI_COMMAND_FAILURE,
                                      msg="VM power off command not executed")
            else:
                bmc_obj.bmc_node_power_on_off(self.bmc_user, self.bmc_pwd, "off")

        LOGGER.info("Check if %s is powered off.", host)
        # SSC cloud is taking time to off VM host hence timeout
        resp = self.polling_host(
            max_timeout=self.t_power_off, host=host, exp_resp=False, bmc_obj=bmc_obj)
        LOGGER.info("Powered off status for host %s is %s.", host, resp)
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
        except CTException as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.status_nodes_online.__name__, error)

    def status_cluster_resource_online(self, srvnode_list: list, sys_list: list, node_obj):
        """
        Check cluster/rack/site/nodes are shown online in Cortx CLI/REST
        :param srvnode_list: list of srvnode names
        :param sys_list: list of sys objects for all nodes
        :param node_obj: node object from which health will be verified
        """
        LOGGER.info("Check the node which is running CSM service and login to CSM on that node.")
        sys_obj = self.check_csm_service(node_obj, srvnode_list, sys_list)
        if not sys_obj[0]:
            raise CTException(err.CLI_COMMAND_FAILURE, sys_obj[1])
        resp = self.check_csrn_status(sys_obj[1], csr_sts="online", node_sts="online", node_id=0)
        if not resp[0]:
            raise CTException(err.HA_BAD_CLUSTER_HEALTH, resp[1])
        LOGGER.info("cluster/rack/site/nodes health status is online in CLI and REST")

    def check_csrn_status(self, sys_obj, csr_sts: str, node_sts: str, node_id: int):
        """
        Check cluster/rack/site/node status with expected status using CLI/REST
        :param sys_obj: System object
        :param csr_sts: cluster/rack/site's expected status
        :param node_sts: Node's expected status
        :param node_id: Node ID to check for expected status
        :return: (bool, response)
        """
        check_rem_node = [
            node_sts if num == node_id else "online" for num in range(
                self.num_nodes)]
        LOGGER.info(
            "Checking srvnode-%s status is %s via CortxCLI",
            node_id+1, node_sts)
        resp = self.verify_node_health_status(sys_obj, status=check_rem_node)
        if not resp[0]:
            return resp
        LOGGER.info(
            "Checking Cluster/Site/Rack status is %s via CortxCLI", csr_sts)
        resp = self.verify_csr_health_status(sys_obj, csr_sts)
        if not resp[0]:
            return resp
        LOGGER.info("Checking srvnode-%s status is %s via REST", node_id+1, node_sts)
        resp = self.system_health.verify_node_health_status_rest(
            check_rem_node)
        if not resp[0]:
            return resp
        LOGGER.info("Checking Cluster/Site/Rack status is %s via REST", csr_sts)
        resp = self.system_health.check_csr_health_status_rest(csr_sts)
        if not resp[0]:
            return resp

        return True, f"cluster/rack/site status is {csr_sts} and \
        srvnode-{node_id+1} is {node_sts} in Cortx CLI/REST"

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

    # pylint: disable=too-many-arguments
    @staticmethod
    def perform_node_operation(
            sys_obj,
            operation: str,
            resource_id: int,
            f_opt: bool = False,
            s_off: bool = False,
            user: str = None,
            pswd: str = None):
        """
        This function will perform node start/stop/poweroff operation on resource_id
        :param operation: Operation to be performed (stop/poweroff/start)
        :param sys_obj: System object
        :param resource_id: Resource ID for the operation
        :param f_opt: If true, enables force start on node
        :param s_off: If true, The poweroff operation will be performed along
        with powering off the storage (Valid only with poweroff operation on node)
        :param user: Manage user name
        :param pswd: Manage user password
        :return: (bool, Command Response)
        """
        try:
            sys_obj.open_connection()
            sys_obj.login_cortx_cli(username=user, password=pswd)
            resp = sys_obj.node_operation(
                operation=operation, resource_id=resource_id, force_op=f_opt, storage_off=s_off)
            return resp
        except CTException as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.perform_node_operation.__name__, error)
            return False, error
        finally:
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection(set_session_obj_none=True)

    @staticmethod
    def check_hctl_status_resp(
            hlt_obj,
            host_data: dict,
            hctl_srvs: dict,
            checknode: str):
        """
        This function will check hctl status and if cluster is clean
        it will get the json data and check for the service's not expected status
        and update hctl_srvs for the same
        :param hlt_obj: Health class object
        :param host_data: Dictionary of host data info
        :param hctl_srvs: Dictionary of not expected status service state
        :param checknode: String for node to be checked i.e "srvnode-x.data.private"
        :return: (bool, Response)
        """
        # Get hctl status response for stopped node (Cluster not running)
        resp = system_utils.run_remote_cmd(
            cmd=common_cmd.MOTR_STATUS_CMD,
            hostname=host_data["hostname"],
            username=host_data["username"],
            password=host_data["password"],
            read_lines=True)
        if not resp[0]:
            return False, f"HCTL status: {resp[1]}"
        # Get hctl status --json response for all node hctl services
        resp = hlt_obj.hctl_status_json()
        svcs_elem = {'service': None, 'status': None}
        for node_data in resp['nodes']:
            hctl_srvs[node_data['name']] = list()
            temp_svc = svcs_elem.copy()
            # For stopped node, service should be in stopped state
            if node_data['name'] == checknode:
                for svcs in node_data['svcs']:
                    if svcs['name'] != common_const.MOTR_CLIENT and svcs['status'] == 'started':
                        temp_svc['service'] = svcs['name']
                        temp_svc['status'] = svcs['status']
                        hctl_srvs[node_data['name']].append(temp_svc)
            else:
                for svcs in node_data['svcs']:
                    if svcs['name'] != common_const.MOTR_CLIENT and svcs['status'] != 'started':
                        temp_svc['service'] = svcs['name']
                        temp_svc['status'] = svcs['status']
                        hctl_srvs[node_data['name']].append(temp_svc)
        return True, "HCTL status updated successfully in dictionary"

    # pylint: disable-msg=too-many-locals
    def check_pcs_status_resp(self, node, node_obj, hlt_obj, csm_node):
        """
        This will get pcs status xml and hctl status response and
        check all nodes health status after performing node stop operation on one node
        :param node: Node ID for which health check is required
        :param node_obj: Node object List
        :param hlt_obj: Health class object List
        :param csm_node: Node which is up and CSM is running
        :return: (bool, response/Dictionary for all the service which are not in expected state)
        """
        # Get the next node to check pcs and hctl status
        checknode = f'srvnode-{(node+1)}.data.private'
        host_details = {"hostname": node_obj.hostname,
                        "username": node_obj.username,
                        "password": node_obj.password}
        # Get the pcs status for stopped node (Cluster not running)
        resp = system_utils.run_remote_cmd(
            cmd=common_cmd.PCS_STATUS_CMD,
            hostname=host_details["hostname"],
            username=host_details["username"],
            password=host_details["password"],
            read_lines=True)
        if not resp[0]:
            return False, f"PCS status is {resp[1]} for srvnode-{node+1}"
        # Get the pcs status xml to check service status for all nodes
        response = node_obj.execute_cmd(
            cmd=common_cmd.CMD_PCS_GET_XML,
            read_lines=False,
            exc=False)
        if isinstance(response, bytes):
            response = str(response, 'UTF-8')
        json_format = hlt_obj[csm_node].get_node_health_xml(
            pcs_response=response)
        crm_mon_res = json_format['crm_mon']['resources']
        hctl_services_failed = {}
        # Get the clone set resource state from PCS status
        clone_set_dict = hlt_obj[csm_node].get_clone_set_status(
            crm_mon_res, self.num_nodes)
        svcs_elem = {'node': None, 'status': None}
        for pcs_key, pcs_value in clone_set_dict.items():
            hctl_services_failed[f'{pcs_key}'] = list()
            for srvnode, status in pcs_value.items():
                temp_svc = svcs_elem.copy()
                # For stopped node, service should be in stopped state
                if srvnode == checknode and status != 'Stopped':
                    temp_svc['node'] = srvnode
                    temp_svc['status'] = status
                    hctl_services_failed[f'{pcs_key}'].append(temp_svc)
                elif srvnode != checknode and status != 'Started':
                    temp_svc['node'] = srvnode
                    temp_svc['status'] = status
                    hctl_services_failed[f'{pcs_key}'].append(temp_svc)
        # Extract data for PCS resource group elements
        resource_dict = hlt_obj[csm_node].get_resource_status(crm_mon_res)
        for pcs_key, pcs_value in resource_dict.items():
            hctl_services_failed[f'{pcs_key}'] = list()
            if pcs_value['status'] == 'Stopped':
                hctl_services_failed[f'{pcs_key}'].append(pcs_value)
        # Extract data for PCS group elements
        group_dict = hlt_obj[csm_node].get_group_status(crm_mon_res)
        for pcs_key, pcs_value in group_dict.items():
            hctl_services_failed[f'{pcs_key}'] = list()
            if pcs_value['status'] == 'Stopped':
                hctl_services_failed[f'{pcs_key}'].append(pcs_value)

        resp = self.check_hctl_status_resp(
            hlt_obj[csm_node],
            host_data=host_details,
            hctl_srvs=hctl_services_failed,
            checknode=checknode)
        if not resp:
            return resp
        # if hctl_services_failed list value is not empty get the details of
        # not expected status
        node_hctl_failure = {key: val for (key, val) in hctl_services_failed.items() if val}
        if node_hctl_failure:
            return False, node_hctl_failure

        return True, f"Check node health status is as expected for {checknode}"

    def delete_s3_acc_buckets_objects(self, s3_data: dict):
        """
        This function deletes all s3 buckets objects for the s3 account
        and all s3 accounts
        :param s3_data: Dictionary for s3 operation info
        :return: (bool, response)
        """
        try:
            for details in s3_data.values():
                s3_del = S3TestLib(endpoint_url=S3_CFG["s3_url"],
                                   access_key=details['accesskey'],
                                   secret_key=details['secretkey'])
                response = s3_del.delete_all_buckets()
                if not response[0]:
                    return response
                response = self.s3_rest_obj.delete_s3_account(details['user_name'])
                if not response[0]:
                    return response
            return True, "Successfully performed S3 operation clean up"
        except (ValueError, KeyError, CTException) as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.delete_s3_acc_buckets_objects.__name__, error)
            return False, error

    # pylint: disable=too-many-arguments
    def perform_ios_ops(
            self,
            prefix_data: str = None,
            nusers: int = 2,
            nbuckets: int = 2,
            files_count: int = 10,
            di_data: tuple = None,
            is_di: bool = False,
            async_io: bool = False,
            stop_upload_time: int = 60):
        """
        This function creates s3 acc, buckets and performs IO.
        This will perform DI check if is_di True and once done,
        deletes all the buckets and s3 accounts created
        :param prefix_data: Prefix data for IO Operation
        :param nusers: Number of s3 user
        :param nbuckets: Number of buckets per s3 user
        :param files_count: NUmber of files to be uploaded per bucket
        :param di_data: Data for DI check operation
        :param is_di: To perform DI check operation
        :param async_io: To perform parallel IO operation
        :param stop_upload_time: Approx time allowed for write operation to be finished
        before starting stop_io_async
        :return: (bool, response)
        """
        io_data = None
        try:
            if not is_di:
                LOGGER.info("create s3 acc, buckets and upload objects.")
                users = self.mgnt_ops.create_account_users(nusers=nusers)
                io_data = self.mgnt_ops.create_buckets(
                    nbuckets=nbuckets, users=users)
                run_data_chk_obj = RunDataCheckManager(users=io_data)
                pref_dir = {"prefix_dir": prefix_data}
                if async_io:
                    run_data_chk_obj.start_io_async(
                        users=io_data, buckets=None, files_count=files_count, prefs=pref_dir)
                    run_data_chk_obj.event.set()
                    time.sleep(stop_upload_time)
                    run_data_chk_obj.event.is_set()
                else:
                    star_res = run_data_chk_obj.start_io(
                        users=io_data, buckets=None, files_count=files_count, prefs=pref_dir)
                    if not star_res:
                        raise CTException(err.S3_START_IO_FAILED, star_res)
                return True, run_data_chk_obj, io_data

            LOGGER.info("Checking DI for IOs run.")
            if async_io:
                stop_res = di_data[0].stop_io_async(users=di_data[1], di_check=is_di)
            else:
                stop_res = di_data[0].stop_io(users=di_data[1], di_check=is_di)
            if not stop_res[0]:
                raise CTException(err.S3_STOP_IO_FAILED, stop_res[1])
            del_resp = self.delete_s3_acc_buckets_objects(di_data[1])
            if not del_resp[0]:
                raise CTException(err.S3_STOP_IO_FAILED, del_resp[1])
            return True, "Di check for IOs passed successfully"
        except (ValueError, CTException) as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HALibs.perform_ios_ops.__name__, error)
            if io_data:
                del_resp = self.delete_s3_acc_buckets_objects(io_data)
                if not del_resp[0]:
                    return False, (error, del_resp[1])
            return False, error

    def perform_io_read_parallel(self, di_data, is_di=True, start_read=True):
        """
        This function runs parallel async stop_io function until called again with
        start_read with False
        :param di_data: Tuple of RunDataCheckManager obj and User-bucket info from
        WRITEs call
        :param is_di: IF DI check is required on READ objects
        :param start_read: If True, function will start the parallel READs
        and if False function will Stop the parallel READs
        :return: bool/Process object or stop process status
        """
        if start_read:
            self.parallel_ios = Process(
                target=di_data[0].stop_io, args=(di_data[1], is_di))
            self.parallel_ios.start()
            return_val = (True, self.parallel_ios)
        else:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
            LOGGER.info(
                "Parallel IOs stopped: %s",
                not self.parallel_ios.is_alive())
            return_val = (not self.parallel_ios.is_alive(), "Failed to stop parallel READ IOs.")
        return return_val

    # pylint: disable=too-many-arguments
    def ha_s3_workload_operation(
            self,
            log_prefix: str,
            s3userinfo: dict,
            skipread: bool = False,
            skipwrite: bool = False,
            skipcleanup: bool = False,
            nsamples: int = 20,
            nclients: int = 10):
        """
        This function creates s3 acc, buckets and performs WRITEs/READs/DELETEs
        operations on VM/HW
        :param log_prefix: Test number prefix for log file
        :param s3userinfo: S3 user info
        :param skipread: Skip reading objects created in this run if True
        :param skipwrite: Skip writing objects created in this run if True
        :param skipcleanup: Skip deleting objects created in this run if True
        :param nsamples: Number of samples of object
        :param nclients: Number of clients/workers
        :return: bool/operation response
        """
        workloads = ["0B", "1KB", "16KB", "32KB", "64KB", "128KB", "256KB", "512KB",
                     "1MB", "4MB", "8MB", "16MB", "32MB", "64MB", "128MB", "256MB", "512MB"]
        if self.setup_type == "HW":
            workloads.extend(["1GB", "2GB", "3GB", "4GB", "5GB"])

        resp = s3bench.setup_s3bench()
        if not resp:
            return resp, "Couldn't setup s3bench on client machine."
        for workload in workloads:
            resp = s3bench.s3bench(
                s3userinfo['accesskey'], s3userinfo['secretkey'], bucket=f"bucket_{log_prefix}",
                num_clients=nclients, num_sample=nsamples, obj_name_pref=f"ha_{log_prefix}",
                obj_size=workload, skip_write=skipwrite, skip_read=skipread,
                skip_cleanup=skipcleanup, log_file_prefix=f"log_{log_prefix}")
            resp = s3bench.check_log_file_error(resp[1])
            if resp:
                return resp, f"s3bench operation failed with {resp[1]}"
        return True, "Successfully completed s3bench operation"

    @staticmethod
    def check_cluster_health():
        """Check the cluster health"""
        LOGGER.info("Check cluster status for all nodes.")
        nodes = CMN_CFG["nodes"]
        for node in nodes:
            hostname = node['hostname']
            health = Health(hostname=hostname,
                            username=node['username'],
                            password=node['password'])
            result = health.check_node_health()
            assert_utils.assert_true(result[0],
                                     f'Cluster Node {hostname} failed in '
                                     f'health check. Reason: {result}')
            health.disconnect()
        LOGGER.info("Cluster status is healthy.")

    @staticmethod
    def cortx_start_cluster(node_obj, node: str = "--all"):
        """
        This function starts the cluster
        :param node_obj : Node object from which the command should be triggered
        :param node: Node which should be started, default : --all
        """
        LOGGER.info("Start the cluster")
        resp = node_obj.execute_cmd(f"{common_cmd.CMD_START_CLSTR} {node}", read_lines=True,
                                    exc=False)
        LOGGER.info("%s %s resp = %s", common_cmd.CMD_START_CLSTR, node, resp[0])
        if "Cluster start operation performed" in resp[0]:
            return True, resp[0]
        return False, resp[0]

    @staticmethod
    def cortx_stop_cluster(node_obj, node: str = "--all"):
        """
        This function stops the cluster
        :param node_obj : Node object from which the command should be triggered
        :param node: Node which should be stopped, default : --all
        """
        LOGGER.info("Stop the cluster")
        resp = node_obj.execute_cmd(f"{common_cmd.CMD_STOP_CLSTR} {node}", read_lines=True,
                                    exc=False)
        LOGGER.info("%s %s resp = %s", common_cmd.CMD_STOP_CLSTR, node, resp[0])
        if "Cluster stop is in progress" in resp[0]:
            return True, resp[0]
        return False, resp[0]

    def restart_cluster(self, node_obj, hlt_obj_list):
        """
        Restart the cluster and check all nodes health.
        Commands executed :
        cortx stop cluster --all
        cortx start cluster -all
        pcs resource cleanup
        Validate health of all the nodes
        :param node_obj: node object for stop/start cluster
        :param hlt_obj_list: health object list for all the nodes.
        """
        LOGGER.info("Stop the cluster")
        resp = self.cortx_stop_cluster(node_obj)
        if not resp[0]:
            return False, "Error during Stopping cluster"
        LOGGER.info("Start the cluster")
        resp = self.cortx_start_cluster(node_obj)
        if not resp[0]:
            return False, "Error during Starting cluster"
        time.sleep(CMN_CFG["delay_60sec"])
        LOGGER.info("Perform PCS resource cleanup")
        hlt_obj_list[0].pcs_resource_cleanup()
        LOGGER.info("Checking if all nodes are reachable and PCS clean.")
        for hlt_obj in hlt_obj_list:
            res = hlt_obj.check_node_health()
            if not res[0]:
                return False, f"Error during health check of {hlt_obj}"
        LOGGER.info("All nodes are reachable and PCS looks clean.")
        return True, "Cluster Restarted successfully."
