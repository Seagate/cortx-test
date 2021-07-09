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
#

"""Python library which will perform ras component related and system level operations."""
import logging
import re
import os
import time
from collections import OrderedDict
from commons import commands
from libs.ras.ras_core_lib import RASCoreLib
from config import RAS_VAL
from commons import constants as const

LOGGER = logging.getLogger(__name__)


class SoftwareAlert(RASCoreLib):
    """A class including functions for ras component related operations."""

    def __init__(self, host: str, username: str, password: str) -> None:
        super().__init__(host, username, password)
        self.svc_path = None

    def run_verify_svc_state(self, svc: str, action: str, monitor_svcs: list,
                             ignore_param: list = ['timestamp', 'comment'], timeout: int = 5):
        """Perform the given action on the given service and verify systemctl response.

        :param svc: service name on which action is to be performed
        :param action: start/stop/restart/..
        :param monitor_svcs: other services which should be monitored along with action.
        :param timeout: time to wait for service to change state before declaring timeout
        :param ignore_param: List of parameters that can be avoided while checking remaining service
         change state
        :return [type]: bool, expected csm response
        """
        monitor_svcs_rem = [svc_rem for svc_rem in monitor_svcs if svc_rem != svc]

        LOGGER.info("Get systemctl status for %s ...", monitor_svcs_rem)
        prev_svcs_status = self.get_svc_status(monitor_svcs_rem)

        LOGGER.info("Get systemctl status for %s ...", svc)
        prev_svc_state = self.get_svc_status([svc])[svc]

        LOGGER.info("Performing %s operation on %s ...", action, svc)
        if action == "deactivating":
            self.put_svc_deactivating(svc)
        elif action == "activating":
            self.put_svc_activating(svc)
        elif action == "restarting":
            self.put_svc_restarting(svc)
        elif action == "failed":
            self.put_svc_failed(svc)
        elif action == "reloading":
            self.put_svc_reloading(svc)
        else:
            self.node_utils.send_systemctl_cmd(action, [svc], exc=True)

        LOGGER.info("Get systemctl status for %s ...", svc)
        starttime = time.time()
        svc_result = False
        time_lapsed = 0
        while not svc_result and time_lapsed < timeout:
            services_status = self.get_svc_status([svc])
            a_sysctl_resp = services_status[svc]
            e_sysctl_resp = self.get_expected_systemctl_resp(action)
            svc_result = self.verify_systemctl_response(
                expected=e_sysctl_resp, actual=a_sysctl_resp)
            time_lapsed = time.time() - starttime

        LOGGER.info("Time take for service to change state: %s seconds", time_lapsed)
        if svc_result:
            LOGGER.info("%s service state is as expected.", svc)
        else:
            LOGGER.info("%s service state is NOT as expected.", svc)

        LOGGER.info("Get systemctl status for %s ...", monitor_svcs_rem)
        new_svcs_status = self.get_svc_status(monitor_svcs_rem)
        for svcs in new_svcs_status.keys():
            [new_svcs_status[svcs].pop(key, None) for key in ignore_param]

        for svcs in prev_svcs_status.keys():
            [prev_svcs_status[svcs].pop(key, None) for key in ignore_param]

        monitor_svcs_result = new_svcs_status == prev_svcs_status
        if monitor_svcs_result:
            LOGGER.info("There is no change in the state of other services")
        else:
            LOGGER.error("There is change in the state of the other services")
        result = svc_result and monitor_svcs_result
        return result

    def verify_systemctl_response(self, expected: dict, actual: dict):
        """Verify systemctl status actual response against expected dictionary

        :param expected: Expected systemctl response dictionary
        :param actual: Actual systemctl response in form of dictionary
        :return [bool]: True if expected is subset of expected.
        """
        result = True
        LOGGER.info("Expected response : %s", expected)
        LOGGER.info("Actual response : %s", actual)
        for key, value in expected.items():
            if actual[key] != value:
                result = False
        return result

    def get_expected_systemctl_resp(self, action: str):
        """Find the expected response based on action performed on the service and it's previous
        state
        :param action: systemctl action like start/stop/restart/..
        :return dict: dictionary of expected systemctl response
        """
        if action == "start":
            systemctl_status = {'state': 'active'}
        elif action == "stop":
            systemctl_status = {'state': 'inactive'}
        elif action == "restart":
            systemctl_status = {'state': 'active'}
        elif action == "enable":
            systemctl_status = {'enabled': 'enabled'}
        elif action == "disable":
            systemctl_status = {'enabled': 'disabled'}
        elif action == "deactivating":
            systemctl_status = {'state': 'deactivating'}
        elif action == "activating":
            systemctl_status = {'state': 'activating'}
        elif action == "restarting":
            systemctl_status = {'state': 'activating'}
        elif action == "failed":
            systemctl_status = {'state': 'failed'}
        elif action == "reloading":
            systemctl_status = {'state': 'reloading'}
        return systemctl_status

    def get_svc_status(self, services: list):
        """Read the systemctl status for all the services and parse it readable dictionary.

        :param services: List of services
        :return [type]: dictionary of form
        {service1: systemctl_status_resp, service2: systemctl_status_resp, }
        """
        status = {}
        responses = self.node_utils.send_systemctl_cmd("status", services, exc=False)
        for svc, response in zip(services, responses):
            LOGGER.info("Systemctl status for %s service is %s", svc, response)
            if isinstance(response, bytes):
                response = response.decode("utf8")
                status[svc] = self.parse_systemctl_status(response)
            elif isinstance(response, str):
                status[svc] = self.parse_systemctl_status(response)
            else:
                raise Exception(response)
        return status

    def get_disabled_svcs(self, services: list):
        """Extract the inactive service from the given service list

        :param services: List of services to verified
        :return [type]: list of inactive services
        """
        LOGGER.info("Check that all services are in active state: %s", services)
        resp = self.get_svc_status(services=services)
        LOGGER.info("Get service status response : %s", resp)
        disabled_list = []
        for svc, sresp in resp.items():
            LOGGER.info("%s : %s", svc, sresp["enabled"])
            if sresp["enabled"] != "enabled":
                disabled_list.append(svc)
        return disabled_list

    def get_inactive_svcs(self, services: list):
        """Extract the inactive service from the given service list

        :param services: List of services to verified
        :return [type]: list of inactive services
        """
        LOGGER.info("Check that all services are in active state: %s", services)
        resp = self.node_utils.send_systemctl_cmd(command="is-active",
                                                  services=services,
                                                  decode=True, exc=False)
        inactive_list = []
        for state, svc in zip(resp, services):
            LOGGER.info("%s : %s", svc, state)
            if state != "active":
                inactive_list.append(svc)
        return inactive_list

    def parse_systemctl_status(self, response):
        """Parse the keywords from the systemctl response.

        :param response: byte response
        :return [type]: Parsed systemctl status response.
        """
        parsed_op = {}
        for line in response.splitlines():
            line = line.lstrip().rstrip()
            if "● " in line:
                if " - " in line:
                    service_tokenizer = re.compile(r'● (?P<service>.*?) - (?P<description>.*)')
                else:
                    service_tokenizer = re.compile(r'● (?P<service>.*)')
                match = re.match(service_tokenizer, line)
                parsed_op.update(match.groupdict())
            if "Active:" in line:
                if "since" in line:
                    state_tokenizer = re.compile(
                        r'Active: (?P<state>.*?) (?P<sub_state>.*) since (?P<timestamp>.*)')
                else:
                    state_tokenizer = re.compile(r'Active: (?P<state>.*?) (?P<sub_state>.*)')
                match = re.match(state_tokenizer, line)
                parsed_op.update(match.groupdict())
            if "Loaded:" in line and "vendor preset:" in line and ";" in line:
                load_tokenizer = re.compile(
                    r'Loaded: (?P<loaded>.*?) \((?P<path>.*?); (?P<enabled>.*); vendor preset: (?P<vendorpreset>.*)\)')
                match = re.match(load_tokenizer, line)
                parsed_op.update(match.groupdict())
            if "Main PID:" in line:
                pid_tokenizer = re.compile(r'Main PID: (?P<pid>.*?) (?P<comment>.*)')
                match = re.match(pid_tokenizer, line)
                parsed_op.update(match.groupdict())
        return parsed_op

    def put_svc_failed(self, svc):
        """Function to generate deactivating alert

        :param svc: Service Name
        """
        svc_status = self.get_svc_status([svc])[svc]
        ppid = svc_status["pid"]
        LOGGER.info("Process ID of the service : %s", ppid)
        self.svc_path = svc_status["path"]
        LOGGER.info("Old service configuration path : %s", self.svc_path)
        tmp_path = self.get_tmp_svc_path()
        LOGGER.info("New service configuration path : %s", tmp_path)
        self.node_utils.rename_file(self.svc_path, tmp_path)
        self.apply_svc_setting()
        cmd = commands.KILL_CMD.format(ppid)
        LOGGER.info("Sending kill command : %s", cmd)
        try:
            self.node_utils.execute_cmd(cmd)
        except OSError as error:
            LOGGER.warning(error)
            LOGGER.info("Process is not running.")

    def put_svc_deactivating(self, svc):
        """Function to generate deactivating alert

        :param svc: Service Name
        """
        self.write_svc_file(
            svc, {
                "Service": {
                    "ExecStop": "/bin/sleep 200", "TimeoutStopSec": "500"}})
        self.apply_svc_setting()
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_STOP_CMD.format(svc))

    def put_svc_reloading(self, svc):
        """Function to generate reloading alert

        :param svc: Service Name
        """
        self.write_svc_file(
            svc, {
                "Service": {
                    "ExecReload": "/bin/sleep 50"}})
        self.apply_svc_setting()
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_RELOAD_CMD.format(svc))

    def put_svc_activating(self, svc):
        """Function to generate activating alert

        :param svc: Service Name
        """
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_STOP_CMD.format(svc))
        self.write_svc_file(
            svc, {
                "Service": {
                    "ExecStartPre": "/bin/sleep 500", "TimeoutStartSec": "600"}})
        self.apply_svc_setting()
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_START_CMD.format(svc))

    def put_svc_restarting(self, svc):
        """Function to generate restarting alert

        :param svc: Service Name
        """
        self.write_svc_file(
            svc, {
                "Service": {
                    "ExecStartPre": "/bin/sleep 200", "TimeoutStartSec": "500"}})
        self.apply_svc_setting()
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_RESTART_CMD.format(svc))

    def recover_svc(self, svc: str, attempt_start: bool = True, timeout=200):
        """
        response recovery time is with +5sec precision
        :param attempt_start: If True , it will try to start the stopped services.
        :param timeout: Wait for service to come up until timeout. Seconds
        :return dict: response: {svc_name1:{state:<value>,recovery_time:<value>},...}
        """
        starttime = time.time()
        op = {}
        time_lapsed = 0
        while time_lapsed < timeout:
            response = self.get_svc_status([svc])
            op = {"state": response[svc]["state"], "recovery_time": time.time() - starttime}
            LOGGER.info(svc + ":" + response[svc]["state"])
            if response[svc]["state"] == "active":
                LOGGER.info("%s is recovered in %s seconds", svc, time_lapsed)
                break
            if attempt_start and response[svc]["state"] != "active":
                self.node_utils.send_systemctl_cmd("start", [svc], exc=True)
            time.sleep(1)
            time_lapsed = time.time() - starttime
        return op

    def get_tmp_svc_path(self):
        """Generate the name of the temporary service configuration file.

        :return [str]: backup for original service configuration
        """
        dpath, fname = os.path.split(self.svc_path)
        tmp_svc_path = os.path.join(dpath, fname + "tmp")
        return tmp_svc_path

    def read_svc_file(self, svc):
        """
        Read the service configuration file and parse the same in form of dictionary
        :param svc: service name whose file needs to be read
        :return [dict]: parse service file
        """
        response = self.node_utils.read_file(self.get_svc_status([svc])[svc]["path"])
        op = OrderedDict()
        section = None
        for line in response.splitlines():
            if "[" in line and "]" in line:
                section = re.sub("\\[", "", line)
                section = re.sub("\\]", "", section)
                op[section] = {}
            elif section is not None and "=" in line:
                txt = line.split("=")
                if len(txt) > 2:
                    separator = '='
                    key = separator.join(txt[:-1])
                else:
                    key = txt[0]
                    op[section].update({key: txt[-1]})
        return op

    def store_svc_config(self, svc):
        """Store the service configuration file

        :param svc: service name whose file needs to be store
        """

        fpath = self.get_svc_status([svc])[svc]["path"]
        self.node_utils.make_dir(const.SVC_COPY_CONFG_PATH)
        res = self.cp_file(path=fpath, backup_path=const.SVC_COPY_CONFG_PATH)
        LOGGER.info("Copy file resp : %s", res)
        return fpath

    def write_svc_file(self, svc, content):
        """Writes content to the service configuration file

        :param svc: Service name whose configuration file is to be modified.
        :param content: Content to added or updated. It should be in format {section:{key:value}}
        """
        fpath = self.get_svc_status([svc])[svc]["path"]
        self.svc_path = fpath
        op = self.read_svc_file(svc)
        LOGGER.info("Existing service configuration :")
        LOGGER.info(op)
        self.node_utils.rename_file(self.svc_path, self.get_tmp_svc_path())
        LOGGER.info("Content modified in service configuration : %s", content)
        for section, _ in content.items():
            op[section].update(content[section])
            txt = ""
            for key, value in op.items():
                txt = txt + "[" + key + "]" + "\n"
                for k, v in value.items():
                    txt = txt + k + "=" + v + "\n"
            self.node_utils.write_file(fpath, txt)
        LOGGER.info("Changed service configuration :")
        LOGGER.info(txt)

    def apply_svc_setting(self):
        """Apply the changed setting using reload daemon command.

        """
        reload_systemctl = "systemctl daemon-reload"
        LOGGER.info("Sending %s command...", reload_systemctl)
        self.node_utils.execute_cmd(cmd=reload_systemctl)
        LOGGER.info("Successfully reloaded systemctl.")

    def restore_svc_config(self, teardown_restore=False, svc_path_dict: dict = None):
        """Removes the changed configuration file and restores the original one.

        :param teardown_restore: Service configuration file restored from backup folder in teardown.
        :param svc_path_dict: dictionary for service and its configaration file path
        """

        LOGGER.info("Restoring the service configuration...")
        if not teardown_restore:
            try:
                self.node_utils.remove_file(self.svc_path)
            except FileNotFoundError:
                LOGGER.info("Ignoring file %s not found", self.svc_path)
            self.node_utils.rename_file(self.get_tmp_svc_path(), self.svc_path)
            self.apply_svc_setting()
        else:
            for svc_path_val in svc_path_dict.values():
                fname = os.path.split(svc_path_val)
                tmp_svc_path = const.SVC_COPY_CONFG_PATH + fname[1]
                self.cp_file(path=tmp_svc_path, backup_path=svc_path_val)
            self.apply_svc_setting()
            self.node_utils.delete_dir_sftp(const.SVC_COPY_CONFG_PATH)
        LOGGER.info("Service configuration is successfully restored.")

    ############### Server OS functions####################
    def gen_cpu_usage_fault_thres(self, delta_cpu_usage):
        """Creates CPU faults

        :param delta_cpu_usage: Delta to be added to CPU usage.
        :return [type]: True, error message
        """
        LOGGER.info("Fetching CPU usage from server node")
        cpu_usage = self.health_obj.get_cpu_usage()
        LOGGER.info("Current cpu usage of server node %s is %s", self.host, cpu_usage)
        cpu_usage_thresh = float("{:.1f}".format(sum([cpu_usage, delta_cpu_usage])))
        LOGGER.info("Setting new value of cpu_usage_threshold %s", cpu_usage_thresh)
        self.set_conf_store_vals(
            url=const.SSPL_CFG_URL, encl_vals={
                "CONF_CPU_USAGE": cpu_usage_thresh})
        self.restart_sspl()
        resp = self.get_conf_store_vals(url=const.SSPL_CFG_URL, field=const.CONF_CPU_USAGE)
        LOGGER.info("Expected Threshold value %s", cpu_usage_thresh)
        LOGGER.info("Actual Threshold value %s", resp)
        return float(resp) == float(cpu_usage_thresh), "CPU usage threshold is not set as expected."

    def resolv_cpu_usage_fault_thresh(self, cpu_usage_thresh):
        """Resolves CPU faults

        :param cpu_usage_thresh: CPU thresold value to restore the CPU fault
        :return [type]: True, error message
        """
        self.set_conf_store_vals(
            url=const.SSPL_CFG_URL, encl_vals={
                "CONF_CPU_USAGE": cpu_usage_thresh})
        self.restart_sspl()
        resp = self.get_conf_store_vals(url=const.SSPL_CFG_URL, field=const.CONF_CPU_USAGE)
        LOGGER.info("Expected Threshold value %s", cpu_usage_thresh)
        LOGGER.info("Actual Threshold value %s", resp)
        return float(resp) == float(cpu_usage_thresh), "CPU usage threshold is not set as expected."

    def gen_mem_usage_fault(self, delta_mem_usage):
        """Creates memory faults

        :param delta_mem_usage: Delta to be added to memory usage.
        :return [type]: True, error message
        """
        LOGGER.info("Fetching memory usage from server node")
        mem_usage = self.health_obj.get_memory_usage()
        LOGGER.info("Current memory usage of server is %s", mem_usage)
        mem_usage_thresh = float("{:.1f}".format(sum([mem_usage, delta_mem_usage])))
        LOGGER.info("Setting new value of host_memory_usage_threshold to %s", mem_usage_thresh)
        self.set_conf_store_vals(
            url=const.SSPL_CFG_URL, encl_vals={
                "CONF_MEM_USAGE": mem_usage_thresh})
        self.restart_sspl()
        resp = self.get_conf_store_vals(url=const.SSPL_CFG_URL, field=const.CONF_MEM_USAGE)
        LOGGER.info("Expected Threshold value %s", mem_usage_thresh)
        LOGGER.info("Actual Threshold value %s", resp)
        return float(resp) == float(
            mem_usage_thresh), "Memory usage threshold is not set as expected."

    def resolv_mem_usage_fault(self, mem_usage_thresh):
        """Resolves memory faults

        :param mem_usage_thresh: Value to the memory usage threshold to be set.
        :return [type]: True, error message
        """
        self.set_conf_store_vals(
            url=const.SSPL_CFG_URL, encl_vals={
                "CONF_MEM_USAGE": mem_usage_thresh})
        self.restart_sspl()
        resp = self.get_conf_store_vals(url=const.SSPL_CFG_URL, field=const.CONF_MEM_USAGE)
        LOGGER.info("Expected Threshold value %s", mem_usage_thresh)
        LOGGER.info("Actual Threshold value %s", resp)
        return float(resp) == float(
            mem_usage_thresh), "Memory usage threshold is not set as expected."

    def gen_disk_usage_fault(self, delta_disk_usage):
        """Creates disk faults

        :param delta_disk_usage: Delta to be added to disk usage.
        :return [type]: True, error message
        """
        LOGGER.info("Fetching disk usage from server node")
        status, disk_usage = self.node_utils.disk_usage_python_interpreter_cmd(
            dir_path="/", field_val=3)
        if not status:
            return False, "Unable to read disk usage"
        LOGGER.info("Current disk usage of server is %s", disk_usage)
        disk_usage_thresh = float("{:.1f}".format(sum([float(disk_usage), delta_disk_usage])))
        self.set_conf_store_vals(
            url=const.SSPL_CFG_URL, encl_vals={
                "CONF_DISK_USAGE": disk_usage_thresh})
        self.restart_sspl()
        resp = self.get_conf_store_vals(url=const.SSPL_CFG_URL, field=const.CONF_DISK_USAGE)
        LOGGER.info("Expected Threshold value %s", disk_usage_thresh)
        LOGGER.info("Actual Threshold value %s", resp)
        return float(resp) == float(
            disk_usage_thresh), "Disk usage threshold is not set as expected."

    def resolv_disk_usage_fault(self, disk_usage_thresh):
        """Resolves disk faults

        :param disk_usage_thresh: Value of the disk threshold to be set.
        :return [type]: True, error message
        """
        self.set_conf_store_vals(
            url=const.SSPL_CFG_URL, encl_vals={
                "CONF_DISK_USAGE": disk_usage_thresh})
        self.restart_sspl()
        resp = self.get_conf_store_vals(url=const.SSPL_CFG_URL, field=const.CONF_DISK_USAGE)
        LOGGER.info("Expected Threshold value %s", disk_usage_thresh)
        LOGGER.info("Actual Threshold value %s", resp)
        return float(resp) == float(
            disk_usage_thresh), "Disk usage threshold is not set as expected."

    def restart_sspl(self):
        """Restart sspl service
        """
        LOGGER.info("Restarting sspl service")
        resp = self.health_obj.restart_pcs_resource(RAS_VAL["ras_sspl_alert"]["sspl_resource_id"])
        if resp:
            time.sleep(RAS_VAL["ras_sspl_alert"]["sspl_timeout"])
            LOGGER.info("Verifying the status of sspl service is online")
            resp = self.health_obj.pcs_service_status(RAS_VAL["ras_sspl_alert"]["sspl_resource_id"])
            result = resp[0]
        else:
            LOGGER.error("Failed to restart sspl-ll")
            result = False
        return result

    def gen_cpu_fault(self, faulty_cpu_id: list):
        """Generate CPU faults

        :param n_cpu: CPU core ID starting from 0 to number cores on which fault will be created.
        :return [tuple]: bool, error message
        """
        faulty_cpu_id = [int(i) for i in faulty_cpu_id]
        n_cpu = set(faulty_cpu_id).intersection(self.get_available_cpus())
        for cpu in n_cpu:
            LOGGER.info("Generating CPU fault for CPU-%s", cpu)
            cmd = commands.CPU_FAULT.format(cpu)
            self.node_utils.execute_cmd(cmd=cmd)
        self.restart_sspl()
        return len(self.get_available_cpus().intersection(
            set(n_cpu))) == 0, "Could not create CPU fault"

    def resolv_cpu_fault(self, faulty_cpu_id: list):
        """Resolve the CPU faults

        :param n_cpu: CPU core ID starting from 0 to number cores on which fault will be resolved
        :return [type]: bool, error message
        """
        faulty_cpu_id = [int(i) for i in faulty_cpu_id]
        for cpu in faulty_cpu_id:
            LOGGER.info("Resolving CPU fault for CPU-%s", cpu)
            cmd = commands.CPU_RESOLVE.format(cpu)
            self.node_utils.execute_cmd(cmd=cmd)
        self.restart_sspl()
        return len(self.get_available_cpus().intersection(set(faulty_cpu_id))
                   ) == len(faulty_cpu_id), "Could not resolve CPU fault"

    def get_available_cpus(self):
        """Find the available online CPUs

        :return [list]: List of core ID which are online.
        """
        resp = self.node_utils.execute_cmd(cmd=commands.CPU_COUNT).decode('utf-8')
        LOGGER.DEBUG("%s response : %s", commands.CPU_COUNT, resp)
        if "," in resp:
            resp = resp.split(",")
        else:
            resp = [resp]
        cpus = []
        for i in resp:
            if "-" in i:
                start, end = i.split("-")
                cpus.extend(list(range(int(start), int(end) + 1)))
            else:
                cpus.append(int(i))
        LOGGER.info("Available CPUs : %s", cpus)
        return set(cpus)
