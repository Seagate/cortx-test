#!/usr/bin/python  # pylint: disable=C0302
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
HA component utility methods
"""
import logging

from commons import commands as common_cmd
from commons import constants as common_const
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG

LOGGER = logging.getLogger(__name__)


class HAK8SCompLib:
    """
    This class contains HA component utility methods.
    """

    @staticmethod
    def check_string_in_log_file(ha_node_obj,
                                 sub_str: str,
                                 log_file: str,
                                 lines: int = 10) -> tuple:
        """
        Helper function to check sub string in log file.
        :param ha_node_obj: HA node(Logical Node object)
        :param sub_str: Sub string to match.
        :param log_file: Log file.
        :param lines: No of lines needed from 'tail'(Default given as 10)
        :return: True/False and message
        """
        LOGGER.info("Get HA log pvc from pvc list.")
        pvc_list = ha_node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        ha_pvc = None
        for ha_pvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in ha_pvc:
                ha_pvc = ha_pvc.replace("\n", "")
                LOGGER.info("ha pvc: %s", ha_pvc)
                break
        LOGGER.info("Check sub string in log file: %s.", log_file)
        cmd_halog = f"tail -{lines} {common_const.HA_LOG}{ha_pvc}/log/ha/*/" \
            f"{log_file} | grep '{sub_str}'"
        output = ha_node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        if sub_str in output:
            return True, "Sub String found in log file."
        return False, "Sub String not found in log file."

    @staticmethod
    def shutdown_signal(node_obj, local_path: str, remote_path: str) -> tuple:
        """
        Helper function to send shutdown signal to component HA
        :param node_obj: Master node(Logical Node object)
        :param local_path: Local path of script.
        :param remote_path: POD path for copy operation.
        :return: True/False and message/error
        """
        LOGGER.info("Get file name.")
        base_path = local_path.split("/")[-1]
        ha_cp_remote = node_obj.copy_file_to_remote(local_path=local_path, remote_path=remote_path)
        if not ha_cp_remote[0]:
            return False, "File not copied to remote path"
        try:
            LOGGER.info("Run python module from POD.")
            pod_name = node_obj.get_pod_name(pod_prefix=common_const.HA_POD_NAME_PREFIX)
            node_obj.execute_cmd(common_cmd.HA_COPY_CMD.format(common_const.HA_TMP + "/"
                                                               + base_path, pod_name[1],
                                                               common_const.HA_TMP))
            node_obj.execute_cmd(common_cmd.HA_POD_RUN_SCRIPT.format(pod_name[1],
                                                                     '/usr/bin/python3',
                                                                     common_const.HA_TMP +
                                                                     '/' + base_path))
        except IOError as err:
            LOGGER.error("An error occurred in %s:", HAK8SCompLib.shutdown_signal.__name__)
            return False, err
        return True, "Successfully ran the script."

    @staticmethod
    def get_ha_node_object(master_node_obj) -> LogicalNode:
        """
        Helper function to get HA node object.
        :param master_node_obj: Master node(Logical Node object)
        :return: HA node object
        """
        pod_name = master_node_obj.get_pod_name(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        ha_hostname = master_node_obj.get_pods_node_fqdn(pod_name[1])
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_name[1]])
        node_obj = object()
        for node in range(len(CMN_CFG["nodes"])):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_name[1]]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_name[1]],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        return node_obj

    @staticmethod
    def check_ha_services(master_node_obj):
        """
        Helper function to check whether all ha services are running
        :param master_node_obj:  Master node(Logical Node object)
        :return True/False
        """
        pod_list = master_node_obj.get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        output = master_node_obj.execute_cmd(
            cmd=common_cmd.KUBECTL_GET_POD_CONTAINERS.format(pod_name),
            read_lines=True)
        container_list = output[0].split()
        for container in container_list:
            res = master_node_obj.send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=common_const.NAMESPACE,
                command_suffix=f"-c {container} -- {common_cmd.SERVICE_HA_STATUS}", decode=True)
            if common_const.HA_PROCESS not in res:
                return False
        return True

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-branches
    @staticmethod
    def get_ha_log_prop(node_obj, log_name: str, kvalue: int, fault_tolerance: bool = False,
                        health_monitor: bool = False, kubectl_delete: bool = False,
                        status: str = 'online') -> dict:
        """
        Helper function to get ha log properties.
        :param node_obj: Master node(Logical Node object)
        :param log_name: Name of the ha log
        :param kvalue: Number of lines required from 'tail' output
        :param fault_tolerance: Bool/If made true, checks fault_tolerance.log
        :param health_monitor: Bool/If made true, checks health_monitor.log
        :param kubectl_delete: Bool/If made true, checks log for 'kubectl delete'
        :param status: failed/online(Checks for particular alert)
        :return: ha prop data dictionary
        """
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        ha_pvc = None
        log_list = []
        for ha_pvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in ha_pvc:
                ha_pvc = ha_pvc.replace("\n", "")
                LOGGER.info("ha pvc: %s", ha_pvc)
                break
        if fault_tolerance:
            # For one pod operation there will be 9 lines of log
            kvalue *= 9
        if health_monitor:
            if kubectl_delete:
                # For kubectl delete both offline and online logs will be together
                kvalue *= 8
            else:
                # For one pod operation there will be 4 lines of log in health monitor
                kvalue *= 4
        cmd_halog = f"tail -{kvalue} {common_const.HA_LOG}{ha_pvc}/log/ha/*/{log_name}"
        output = node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        output = output.splitlines()
        if kubectl_delete:
            if status == 'failed':
                output = output[:kvalue//2]
            else:
                output = output[kvalue//2:]
        if fault_tolerance:
            for line in output:
                if 'Received the message from message bus' in line:
                    log_list.append(line)
            output = log_list
        if health_monitor:
            for line in output:
                if 'to component hare' in line:
                    log_list.append(line)
            output = log_list
        resp_dict = {'source': [], 'resource_status': [], 'resource_type': [], 'generation_id': [],
                     'node_id': [], 'resource_id': []}
        return HAK8SCompLib.get_properties_data(output, resp_dict)

    @staticmethod
    def get_properties_data(output, resp_dict):
        """
        Function to get HA properties data (Static Helper function to reduce complexity
        of get_ha_log_prop)
        :param output: List of properties data
        :param resp_dict: Dict of properties to be fetched form output
        :return: ha prop data dictionary
        """
        for line in output:
            source = line.split("{")[3].split(",")[0].split(":")[1].strip()\
                .replace("'", '').replace('"', '')
            resource_type = line.split("{")[3].split(",")[6].split(":")[1].strip()\
                .replace("'", '').replace('"', '')
            resource_status = line.split("{")[3].split(",")[8].split(":")[1].strip()\
                .replace("'", '').replace('"', '')
            generation_id = line.split("{")[4].split(",")[0].split(":")[1].strip()\
                .replace("'", '').replace('}', '').replace('"', '')
            node_id = line.split("{")[3].split(",")[5].split(":")[1].strip()\
                .replace("'", '').replace('"', '')
            resource_id = line.split("{")[3].split(",")[7].split(":")[1].strip()\
                .replace("'", '').replace('"', '')
            resp_dict['source'].append(source)
            resp_dict['resource_status'].append(resource_status)
            resp_dict['resource_type'].append(resource_type)
            resp_dict['generation_id'].append(generation_id)
            resp_dict['node_id'].append(node_id)
            resp_dict['resource_id'].append(resource_id)
        return resp_dict

    @staticmethod
    def get_ha_log_wc(node_obj, log_index: int):
        """
        Helper function to get word count of a file
        :param node_obj: Master node(Logical Node object)
        :param log_index: name of the log
        0 - k8s | 1 - fault_tolerance | 2 - health_monitor
        :return: wc_count(Word count of a ha log file)
        """
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        hapvc = wc_count = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("hapvc list %s", hapvc)
                break
        wc_count_cmd = common_const.HA_LOG + hapvc + "/log/ha/*/" + common_const.HA_SHUTDOWN_LOGS[
            log_index]
        wc_count_cmd = common_cmd.LINE_COUNT_CMD.format(wc_count_cmd)
        ha_wc_count = node_obj.execute_cmd(wc_count_cmd)
        if isinstance(ha_wc_count, bytes):
            wc_count = str(ha_wc_count, 'UTF-8')
        return wc_count
