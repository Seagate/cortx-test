#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This file contains the Alert Simulation API.
"""
import logging
from aenum import Enum, NoAlias
from commons import constants as cons
import commons.alerts_simulator.constants as dict_cons
from commons.utils import config_utils as conf_util
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

        if host_details is not None:
            host = host_details["host"]
            h_user = host_details["host_user"]
            h_pwd = host_details["host_password"]
        else:
            host = COMMON_CONF["host"]
            h_user = COMMON_CONF["username"]
            h_pwd = COMMON_CONF["password"]

        if enclosure_details is not None:
            enc_ip = enclosure_details["enclosure_ip"]
            enc_user = enclosure_details["enclosure_user"]
            enc_pwd = enclosure_details["enclosure_pwd"]
        else:
            enc_ip = COMMON_CONF["primary_enclosure_ip"]
            enc_user = COMMON_CONF["enclosure_user"]
            enc_pwd = COMMON_CONF["enclosure_pwd"]

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
                        f'input_parameters={input_parameters})'}
        }

        arguments = (switcher[alert_type.value]['args'])

        cmd = switcher[alert_type.value]['cmd']
        command = f"ALERT_WRAP.{cmd}{arguments}"
        LOGGER.info("Running command %s", command)
        resp = eval(command)
        return resp
