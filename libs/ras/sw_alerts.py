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

LOGGER = logging.getLogger(__name__)


class SoftwareAlert(RASCoreLib):
    """A class including functions for ras component related operations."""

    def __init__(self, host: str, username: str, password: str) -> None:
        super().__init__(host, username, password)
        self.svc_path = None

    def run_verify_svc_state(self, svc: str, action: str, monitor_svcs: list, timeout:int=5):
        """Perform the given action on the given service and verify systemctl response.

        :param svc: service name on whoch action is to be performed
        :param action: start/stop/restart/..
        :param monitor_svcs: other services which should be monitored along with action.
        :param timeout: time to wait for service to change state before declaring timeout
        :return [type]: bool, expected csm response
        """
        try:
            monitor_svcs.remove(svc)
        except ValueError:
            pass

        LOGGER.info("Get systemctl status for %s ...", monitor_svcs)
        prev_svcs_status = self.get_svc_status(monitor_svcs)

        LOGGER.info("Get systemctl status for %s ...", svc)
        prev_svc_state = self.get_svc_status([svc])[svc]

        LOGGER.info("Performing %s operation on %s ...", action, svc)
        if action == "deactivating":
            self.put_svc_deactivating(svc)
        elif action == "activating":
            self.put_svc_activating(svc)
        elif action == "failed":
            self.put_svc_failed(svc)
        else:
            self.node_utils.send_systemctl_cmd(action, [svc], exc=True)

        LOGGER.info("Get systemctl status for %s ...", svc)
        starttime = time.time()
        while( not svc_result and time_lapsed < timeout):
            services_status = self.get_svc_status([svc])
            a_sysctl_resp = services_status[svc]
            e_sysctl_resp = self.get_expected_systemctl_resp(action)
            svc_result = self.verify_systemctl_response(expected=e_sysctl_resp, actual=a_sysctl_resp)
            time_lapsed = time.time() - starttime

        LOGGER.info("Time take for service to change state: %s seconds", time_lapsed)
        if svc_result:
            LOGGER.info("%s service state is as expected.", svc)
        else:
            LOGGER.info("%s service state is NOT as expected.", svc)

        LOGGER.info("Get systemctl status for %s ...", monitor_svcs)
        new_svcs_status = self.get_svc_status(monitor_svcs)
        monitor_svcs_result = new_svcs_status == prev_svcs_status
        if monitor_svcs_result:
            LOGGER.info("There is no change in the state of other services")
        else:
            LOGGER.error("There is change in the state of the other services")

        e_csm_resp = self.get_expected_csm_resp(action, prev_svc_state)
        result = svc_result and monitor_svcs_result
        return result, e_csm_resp

    def verify_systemctl_response(self, expected: dict, actual: dict):
        """Verify systemctl status actual response against expected dictornary

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

    def get_expected_csm_resp(self, action: str, prev_state: dict):
        """
        #TODO: This function will be refined when the CSM is available for testing.
        """
        svc_fault_response = {"description": "{service_name} is failed state.",
                              "alert_type": "fault",
                              "serverity": "critical",
                              "impact": "{service_name} service is unavailable.",
                              "recommendation": "Try to restart the service."}

        svc_timeout_response = {"description": "{service_name} in a "
                                "{inactive/activating/reloading/deactivating} state for more than"
                                "{threshold_inactive_time} seconds. ",
                                "alert_type": "fault",
                                "serverity": "critical",
                                "impact": "{service_name} service is unavailable.",
                                "recommendation": "Try to restart the service."}

        svc_resolved_response = {"description": "{service} in active state.",
                                 "alert_type": "fault_resolved ",
                                 "serverity": "informational",
                                 "impact": "{service} service is available now.",
                                 "recommendation": ""}

        if action == "start":
            if prev_state['state'] not in ["active"]:
                csm_response = svc_resolved_response
            else:
                csm_response = None

        elif action == "stop":
            if prev_state['state'] not in ['inactive']:
                csm_response = svc_fault_response
            else:
                csm_response = None

        elif action == "restart":
            if prev_state['state'] not in ['inactive', 'failed']:
                csm_response = None
            else:
                csm_response = None

        elif action == "enable":
            csm_response = None

        elif action == "disable":
            csm_response = None

        elif action == "deactivating":
            csm_response = None

        elif action == "activating":
            csm_response = None

        elif action == "failed":
            csm_response = None
        return csm_response

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
        elif action == "failed":
            systemctl_status = {'state': 'failed'}
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
            if "● " in line and "-" in line:
                service_tokenizer = re.compile(r'● (?P<service>.*?) - (?P<description>.*)')
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
        self.node_utils.execute_cmd(cmd)

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

    def put_svc_activating(self, svc):
        """Function to generate activating alert

        :param svc: Service Name
        """
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_STOP_CMD.format(svc))
        self.write_svc_file(
            svc, {
                "Service": {
                    "ExecStartPre": "/bin/sleep 200", "TimeoutStartSec": "500"}})
        self.apply_svc_setting()
        self.node_utils.host_obj.exec_command(commands.SYSTEM_CTL_START_CMD.format(svc))

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
            LOGGER.info(svc + ":" + response[svc]["state"])
            if attempt_start and response[svc]["state"] != "active":
                self.node_utils.send_systemctl_cmd("start", [svc], exc=True)
            response = self.get_svc_status([svc])
            op = {"state": response[svc]["state"], "recovery_time": time.time() - starttime}
            time.sleep(5)
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

    def write_svc_file(self, svc, content):
        """Writes content to the service configuration file

        :param svc: Service name whose configaration file is to be modified.
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
        """Apply the changed setting using reload deemon command.
        """
        reload_systemctl = "systemctl daemon-reload"
        LOGGER.info("Sending %s command...", reload_systemctl)
        self.node_utils.execute_cmd(cmd=reload_systemctl)
        LOGGER.info("Successfully reloaded systemctl.")

    def restore_svc_config(self):
        """Removes the changed configuration file and restroes the orhiginal one.
        """
        LOGGER.info("Restoring the service configuration...")
        try:
            self.node_utils.remove_file(self.svc_path)
        except FileNotFoundError:
            LOGGER.info("Ignoring file %s not found", self.svc_path)
        self.node_utils.rename_file(self.get_tmp_svc_path(), self.svc_path)
        self.apply_svc_setting()
        LOGGER.info("Service configuration is successfully restored.")
