#!/usr/bin/python  # pylint: disable=C0302
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
HA component utility methods
"""
import logging

from commons import commands as common_cmd
from commons import constants as common_const
from config import CMN_CFG
from commons.helpers.pods_helper import LogicalNode


LOGGER = logging.getLogger(__name__)


class HAK8SCompLib:
    """
    This class contains HA component utility methods.
    """

    @staticmethod
    def check_string_in_log_file(ha_node_obj, sub_str: str, log_file: str) -> tuple:
        """
        Helper function to check sub string in log file.
        :param ha_node_obj: HA node(Logical Node object)
        :param sub_str: Sub string to match.
        :param log_file: Log file.
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
        cmd_halog = f"tail -10 {common_const.HA_LOG}{ha_pvc}/log/ha/*/" \
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

    @staticmethod
    def get_ha_log_prop(node_obj, log_name: str, kvalue: int, fault_tolerance: bool=False, health_monitor: bool=False) -> dict:
        '''
        Helper function to get ha log properties.
        :param node_obj: Master node(Logical Node object)
        :param log_name: Name of the ha log
        :param kvalue: Number of lines required from 'tail' output
        :param fault_tolerance: Bool/If made true, checks fault_tolerance.log
        :param health_monitor: Bool/If made true, checks health_monitor.log
        :return: ha prop data dictionary
        '''
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        ha_pvc = None
        log_list = []
        for ha_pvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in ha_pvc:
                ha_pvc = ha_pvc.replace("\n", "")
                LOGGER.info("ha pvc: %s", ha_pvc)
                break
        if fault_tolerance:
            kvalue *= 9
        if health_monitor:
            kvalue *= 4
        cmd_halog = f"tail -{kvalue} {common_const.HA_LOG}{ha_pvc}/log/ha/*/{log_name}"
        output = node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        output = output.splitlines()
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
        resp_dict = {'source': [], 'resource_status': [], 'resource_type': [], 'generation_id': []}
        for line in output:
            source = line.split("{")[4].split(",")[0].split(":")[1].strip().replace("'", '')
            resource_type = line.split("{")[4].split(",")[6].split(":")[1].strip().replace("'", '')
            resource_status = line.split("{")[4].split(",")[8].split(":")[1].strip().replace("'", '')
            generation_id = line.split("{")[5].split(",")[0].split(":")[1].strip().replace("'", '').replace('}', '')
            resp_dict['source'].append(source)
            resp_dict['resource_status'].append(resource_status)
            resp_dict['resource_type'].append(resource_type)
            resp_dict['generation_id'].append(generation_id)
        return resp_dict
