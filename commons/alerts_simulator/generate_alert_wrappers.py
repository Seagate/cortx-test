#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This file contains the wrapper functions used by Alert Simulation API.
"""
import logging
import time
from libs.ras_test_lib import RASTestLib
from commons.helpers.host import Host
from commons import constants as cons

LOGGER = logging.getLogger(__name__)

RAS_TEST_OBJ = RASTestLib()


class GenerateAlertWrapper:
    """
    This class contains the wrappers for simulating alerts using different
    tools.
    """
    def simulatefault(self, encl_ip, encl_user, encl_pwd, host, h_user, h_pwd,
                      input_parameters):
        """
        This is wrapper for simulating HW alerts of modules like psu and ctrl
        using simulatefrufault on controller.
        :param encl_ip: IP of the enclosure
        :type: str
        :param encl_user: Username of the enclosure
        :type: str
        :param encl_pwd: Password of the enclosure
        :type: str
        :param host: IP of the remote host
        :type: str
        :param h_user: User of the remote host
        :type: str
        :param h_pwd: Password of the remote user
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        enclid = input_parameters["enclid"]
        pos = input_parameters["pos"]
        fru = input_parameters["fru"]
        type_fault = input_parameters["type_fault"]
        ctrl_name = input_parameters["ctrl_name"]

        try:
            resp = RAS_TEST_OBJ.get_mc_ver_sr(enclosure_ip=encl_ip,
                                              enclosure_user=encl_user,
                                              enclosure_pwd=encl_pwd,
                                              host=host, h_user=h_user,
                                              h_pwd=h_pwd)
            if resp[1] is None:
                return False, f"{resp[1]} is returned for MC Version"
            if resp[2] is None:
                return False, f"{resp[2]} is returned for MC Version"

            LOGGER.info(f"MC version : {resp[1]} Serial Number : "
                        f"{resp[2]}")

            mc_debug_pswd = RAS_TEST_OBJ.get_mc_debug_pswd(resp[1], resp[2])
            if mc_debug_pswd is None:
                return False, f"{mc_debug_pswd} is returned for MC debug " \
                              f"password"

            resp = RAS_TEST_OBJ.simulate_fault_ctrl(
                mc_deb_password=mc_debug_pswd, enclosure_ip=encl_ip,
                enclid=enclid, pos=pos, fru=fru, type_fault=type_fault,
                ctrl_name=ctrl_name, host=host, h_user=h_user, h_pwd=h_pwd)
        except BaseException as error:
            LOGGER.error(
                f"{cons.EXCEPTION_ERROR} "
                f"{GenerateAlertWrapper.simulatefault.__name__}: {error}")

            return False, error

        return resp

    def disk_faults(self, encl_ip, encl_user, encl_pwd, host, h_user, h_pwd,
                    input_parameters):
        """
        This is wrapper for simulating disk disable and enable faults.
        :param encl_ip: IP of the enclosure
        :type: str
        :param encl_user: Username of the enclosure
        :type: str
        :param encl_pwd: Password of the enclosure
        :type: str
        :param host: IP of the remote host
        :type: str
        :param h_user: User of the remote host
        :type: str
        :param h_pwd: Password of the remote user
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        enclid = input_parameters["enclid"]
        ctrl_name = input_parameters["ctrl_name"]
        phy_num = input_parameters["phy_num"]
        operation = input_parameters["operation"]
        exp_status = input_parameters["exp_status"]
        telnet_file = input_parameters["telnet_file"]

        try:
            LOGGER.info(f"Changing status of phy num {phy_num} to {operation}")
            RAS_TEST_OBJ.set_drive_status_telnet(
                enclosure_ip=encl_ip, username=encl_user, pwd=encl_pwd,
                enclosure_id=enclid, controller_name=ctrl_name,
                drive_number=phy_num, status=operation, host=host,
                h_user=h_user, h_pwd=h_pwd)
            resp = None
            timeout, starttime = 120, time.time()
            while time.time() <= starttime + timeout:  # Added to avoid hardcoded wait.
                status, resp = RAS_TEST_OBJ.check_phy_health(
                    enclosure_ip=encl_ip, username=encl_user, pwd=encl_pwd,
                    phy_num=phy_num, telnet_file=telnet_file, host=host,
                    h_user=h_user, h_pwd=h_pwd)
                if isinstance(exp_status, list):
                    if resp == exp_status[0] or resp == exp_status[1]:
                        break
                else:
                    if resp == exp_status:
                        break
                time.sleep(20)  # Added 20s delay to repeat check_phy_health.
            LOGGER.info(f"check phy response: {resp}")
            if isinstance(exp_status, list):
                if resp != exp_status[0] and resp != exp_status[1]:
                    return False, f"Failed to put drive in {exp_status} " \
                                  f"state, response: {resp}"
            else:
                if resp != exp_status:
                    return False, f"Failed to put drive in {exp_status} " \
                                  f"state, response: {resp}"

            LOGGER.info(f"Successfully put phy in {exp_status} state")
        except BaseException as error:
            LOGGER.error(
                f"{cons.EXCEPTION_ERROR}"
                f"{GenerateAlertWrapper.disk_faults.__name__}: {error}")

            return False, error

        return True, exp_status

    def disk_full_fault(self, host, h_user, h_pwd, input_parameters):
        """
        This is wrapper for generating disk alerts on node.
        :param host: IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        du_val = input_parameters["du_val"]
        fault = input_parameters["fault"]
        fault_resolved = input_parameters["fault_resolved"]
        RAS_TEST_OBJ = RASTestLib(host=host, username=h_user, password=h_pwd)
        try:
            resp = RAS_TEST_OBJ.generate_disk_full_alert(du_val=du_val,
                                                         fault=fault,
                                                         fault_resolved=fault_resolved)

            return resp
        except BaseException as error:
            LOGGER.error(f"{cons.EXCEPTION_ERROR} "
                         f"{GenerateAlertWrapper.disk_full_fault.__name__}: "
                         f"{error}")
            return False, error

    def cpu_usage_fault(self, host, h_user, h_pwd, input_parameters):
        """
        This is wrapper for generating cpu usage alerts on the given host.
        :param host: hostname or IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        delta_cpu_usage = input_parameters["delta_cpu_usage"]
        LOGGER.info("Generating CPU usage alert")
        try:
            resp = RAS_TEST_OBJ.generate_cpu_usage_alert(
                delta_cpu_usage=delta_cpu_usage, host=host, username=h_user,
                password=h_pwd)
            return resp, "Completed CPU usage Fault Generation"
        except BaseException as error:
            LOGGER.error(f"{cons.EXCEPTION_ERROR} "
                         f"{GenerateAlertWrapper.cpu_usage_fault.__name__}: "
                         f"{error}")
            return False, error

    def memory_usage_fault(self, host, h_user, h_pwd, input_parameters):
        """
        This is wrapper for generating memory usage alerts on the given host.
        :param host: IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        delta_mem_usage = input_parameters["delta_mem_usage"]
        LOGGER.info("Generating memory usage alert")
        try:
            resp = RAS_TEST_OBJ.generate_memory_usage_alert(
                delta_mem_usage=delta_mem_usage, host=host, username=h_user,
                password=h_pwd)
            return resp, "Completed Memory Usage Fault Generation"
        except BaseException as error:
            LOGGER.error(
                f"{cons.EXCEPTION_ERROR} "
                f"{GenerateAlertWrapper.memory_usage_fault.__name__}: "
                f"{error}")
            return False, error

    def raid_faults(self, host, h_user, h_pwd, input_parameters):
        """
        This is wrapper for generating raid faults on the given host.
        :param host: hostname or IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        RAS_TEST_OBJ = RASTestLib(host=host, username=h_user, password=h_pwd)
        operation = input_parameters["operation"]
        md_device = input_parameters["md_device"]
        disk = input_parameters["disk"]
        LOGGER.info("Device provided for raid operations {}".format(md_device))
        LOGGER.info("Disks provided for raid operations {}".format(disk))
        if not md_device:
            return False, "Please provide RAID device name e.g., /dev/md?"

        try:
            if operation == "assemble":
                resp = RAS_TEST_OBJ.assemble_mdraid_device(md_device=md_device)
            elif operation == "stop":
                resp = RAS_TEST_OBJ.stop_mdraid_device(md_device=md_device)
            elif operation == "fail_disk" and disk:
                resp = RAS_TEST_OBJ.fail_disk_mdraid(
                    md_device=md_device, disk=disk)
            elif operation == "remove_disk" and disk:
                resp = RAS_TEST_OBJ.remove_faulty_disk(
                    md_device=md_device, disk=disk)
            elif operation == "add_disk" and disk:
                resp = RAS_TEST_OBJ.add_disk_mdraid(
                    md_device=md_device, disk=disk)
            else:
                resp = False, None

            return resp
        except BaseException as error:
            LOGGER.error(f"{cons.EXCEPTION_ERROR} "
                         f"{GenerateAlertWrapper.raid_faults.__name__}: "
                         f"{error}")
            return False, error

    def iem_alerts(self, host, h_user, h_pwd, input_parameters):
        """
        This is wrapper for generating iem faults on the given host.
        :param host: hostname or IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: Returns stdout response
        :rtype: (string)
        """
        logger_alert_cmd = input_parameters['cmd']
        LOGGER.info("Logger cmd : {}".format(logger_alert_cmd))
        host_connect = Host(hostname=host, username=h_user, password=h_pwd)
        resp = host_connect.execute_cmd(cmd=logger_alert_cmd, read_lines=True,
                                        shell=False)
        return resp
