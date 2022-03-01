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
This file contains the Alert Simulation API.
"""
import logging
from aenum import Enum, NoAlias
import commons.alerts_simulator.constants as dict_cons
from commons.alerts_simulator.generate_alert_wrappers import \
    GenerateAlertWrapper
from config import CMN_CFG as COMMON_CONF

LOGGER = logging.getLogger(__name__)
ALERT_WRAP = GenerateAlertWrapper()


class AlertType(Enum, settings=NoAlias):
    """Enums for alert types."""

    CONTROLLER_FAULT = 1
    CONTROLLER_FAULT_RESOLVED = 1
    CONTROLLER_A_FAULT = 1
    CONTROLLER_A_FAULT_RESOLVED = 1
    CONTROLLER_B_FAULT = 1
    CONTROLLER_B_FAULT_RESOLVED = 1
    PSU_FAULT = 1
    PSU_FAULT_RESOLVED = 1
    DISK_DISABLE = 2
    DISK_ENABLE = 2
    DISK_FAULT_NO_ALERT = 3
    DISK_FAULT_ALERT = 3
    DISK_FAULT_RESOLVED_ALERT = 3
    CPU_USAGE_NO_ALERT = 4
    CPU_USAGE_ALERT = 4
    CPU_USAGE_RESOLVED_ALERT = 4
    MEM_USAGE_NO_ALERT = 5
    MEM_USAGE_ALERT = 5
    MEM_USAGE_RESOLVED_ALERT = 5
    RAID_ASSEMBLE_DEVICE_ALERT = 6
    RAID_STOP_DEVICE_ALERT = 6
    RAID_FAIL_DISK_ALERT = 6
    RAID_REMOVE_DISK_ALERT = 6
    RAID_ADD_DISK_ALERT = 6
    IEM_TEST_ERROR_ALERT = 7
    NW_PORT_FAULT = 8
    NW_PORT_FAULT_RESOLVED = 9
    DG_FAULT = 10
    DG_FAULT_RESOLVED = 11
    NW_CABLE_FAULT = 12
    NW_CABLE_FAULT_RESOLVED = 12
    OS_DISK_DISABLE = 13
    OS_DISK_ENABLE = 14
    SERVER_PSU_FAULT = 15
    SERVER_PSU_FAULT_RESOLVED = 16
    BMC_CHANGE_FAULT = 17
    BMC_CHANGE_FAULT_RESOLVE = 17
    RAID_INTEGRITY_FAULT = 18
    RAID_INTEGRITY_RESOLVED = 19
    FAN_ALERT = 20
    FAN_ALERT_RESOLVED = 21


class GenerateAlertLib:
    """
    This class provides the Alert Simulation API.
    """

    @staticmethod
    def generate_alert(alert_type: AlertType, host_details=None,
                       enclosure_details=None, input_parameters=None):
        """
        API to simulate faults using different tools.

        :param alert_type: Type of the alert to be simulated
        :type: str (Get alert type string from the enum above)
        :param host_details: This contains IP, username and password of the host
        :type: Dict
        :param enclosure_details: This contains IP, username and password of
        the enclosure
        :type: Dict
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        LOGGER.info("Generating fault %s", alert_type.name)

        if host_details:
            host = host_details["host"]
            h_user = host_details["host_user"]
            h_pwd = host_details["host_password"]
        else:
            host = COMMON_CONF["nodes"][0]["hostname"]
            h_user = COMMON_CONF["nodes"][0]["username"]
            h_pwd = COMMON_CONF["nodes"][0]["password"]

        if enclosure_details:
            enc_ip = enclosure_details["enclosure_ip"]
            enc_user = enclosure_details["enclosure_user"]
            enc_pwd = enclosure_details["enclosure_pwd"]
        else:
            enc_ip = COMMON_CONF["enclosure"]["primary_enclosure_ip"]
            enc_user = COMMON_CONF["enclosure"]["enclosure_user"]
            enc_pwd = COMMON_CONF["enclosure"]["enclosure_pwd"]

        if input_parameters is None:
            input_parameters = eval('dict_cons.{}'.format(alert_type.name))
        switcher = {
            1: {
                'cmd': 'simulatefault',
                'args': f'(encl_ip="{enc_ip}", encl_user="{enc_user}", '
                        f'encl_pwd="{enc_pwd}", host="{host}", '
                        f'h_user="{h_user}", h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            2: {
                'cmd': 'disk_faults',
                'args': f'(encl_ip="{enc_ip}", encl_user="{enc_user}", '
                        f'encl_pwd="{enc_pwd}", host="{host}", '
                        f'h_user="{h_user}", h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            3: {
                'cmd': 'disk_full_fault',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            4: {
                'cmd': 'cpu_usage_fault',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            5: {
                'cmd': 'memory_usage_fault',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            6: {
                'cmd': 'raid_faults',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            7: {
                'cmd': 'iem_alerts',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            8: {
                'cmd': 'create_network_port_fault',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            9: {
                'cmd': 'resolve_network_port_fault',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            10: {
                'cmd': 'create_disk_group_failures',
                'args': f'(encl_ip="{enc_ip}", encl_user="{enc_user}", '
                        f'encl_pwd="{enc_pwd}", host="{host}", '
                        f'h_user="{h_user}", h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            11: {
                'cmd': 'resolve_disk_group_failures',
                'args': f'(encl_ip="{enc_ip}", encl_user="{enc_user}", '
                        f'encl_pwd="{enc_pwd}", host="{host}", '
                        f'h_user="{h_user}", h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            12: {
                'cmd': 'create_resolve_network_cable_faults',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            13: {
                'cmd': 'disconnect_os_drive',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            14: {
                'cmd': 'connect_os_drive',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            15: {'cmd': 'ipmi_alerts',
                'args': f'(host="{host}", h_user="{h_user}", '
                f'h_pwd="{h_pwd}", '
                f'input_parameters={input_parameters})'},
            16: {
                'cmd': 'ipmi_alerts',
                'args': f'(host="{host}", h_user="{h_user}", '
                f'h_pwd="{h_pwd}", '
                f'input_parameters={input_parameters})'},
            17: {
                'cmd': 'create_resolve_bmc_ip_change_fault'},
            18: {
                'cmd': 'create_raid_integrity_faults',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            19: {
                'cmd': 'resolve_raid_integrity_faults',
                'args': f'(host="{host}", h_user="{h_user}", '
                        f'h_pwd="{h_pwd}", '
                        f'input_parameters={input_parameters})'},
            20: {'cmd': 'ipmi_alerts',
                 'args': f'(host="{host}", h_user="{h_user}", '
                 f'h_pwd="{h_pwd}", '
                 f'input_parameters={input_parameters})'},
            21: {'cmd': 'ipmi_alerts',
                 'args': f'(host="{host}", h_user="{h_user}", '
                 f'h_pwd="{h_pwd}", '
                 f'input_parameters={input_parameters})'},
        }

        arguments = (switcher[alert_type.value]['args'])

        cmd = switcher[alert_type.value]['cmd']
        command = f"ALERT_WRAP.{cmd}{arguments}"
        LOGGER.info("Running command %s", command)
        resp = eval(command)

        return resp
