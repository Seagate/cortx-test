#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This file contains the Alert Simulation API.
"""
import json
import logging
from eos_test.utility import utility
from eos_test.ras.ras_test_lib import RASTestLib
import eos_test.ras.constants as cons
from ctp.common.ctpexception import CTPException
import eos_test.common.eos_errors as err
from ctp.utils import ctpyaml
from aenum import Enum, NoAlias
import eos_test.utility.alerts_simulator.constants as dict_cons
from eos_test.utility.alerts_simulator.generate_alert_wrappers import GenerateAlertWrapper

LOGGER = logging.getLogger(__name__)

UTIL_OBJ = utility.Utility()
RAS_TEST_OBJ = RASTestLib()
ALERT_WRAP = GenerateAlertWrapper()

COMMON_CONF = ctpyaml.read_yaml(cons.COMMON_CONFIG_PATH)
CONS_OBJ_DICT = cons.RAS_BUILD_VER[COMMON_CONF["BUILD_VER_TYPE"]]

RAS_VAL = ctpyaml.read_yaml(CONS_OBJ_DICT["CONFIG_PATH"])
SSPL_VAL = ctpyaml.read_yaml(CONS_OBJ_DICT["SSPL_CONFIG_PATH"])

BYTES_TO_READ = cons.BYTES_TO_READ


class AlertType(Enum, settings=NoAlias):
    controller_fault = 1
    controller_fault_resolved = 1
    controller_a_fault = 1
    controller_a_fault_resolved = 1
    controller_b_fault = 1
    controller_b_fault_resolved = 1
    psu_fault = 1
    psu_fault_resolved = 1
    disk_disable = 2
    disk_enable = 2
    disk_fault_no_alert = 3
    disk_fault_alert = 3
    disk_fault_resolved_alert = 3
    cpu_usage_no_alert = 4
    cpu_usage_alert = 4
    cpu_usage_resolved_alert = 4
    mem_usage_no_alert = 5
    mem_usage_alert = 5
    mem_usage_resolved_alert = 5
    raid_assemble_device_alert = 6
    raid_stop_device_alert = 6
    raid_fail_disk_alert = 6
    raid_remove_disk_alert = 6
    raid_add_disk_alert = 6
    iem_test_error_alert = 7

class GenerateAlertLib:
    """
    This class provides the Alert Simulation API.
    """
    def generate_alert(self, alert_type: AlertType, host_details=None,
                       enclosure_details=None, input_parameters=None):
        """
        This API can be used to simulate faults using different tools
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
        LOGGER.info(f"Generating fault {alert_type.name}")

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
        LOGGER.info(f"Running command {command}")
        resp = eval(command)
        return resp
