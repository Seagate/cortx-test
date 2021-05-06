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
from libs.ras.ras_core_lib import RASCoreLib

LOGGER = logging.getLogger(__name__)


class SoftwareAlert(RASCoreLib):
    """A class including functions for ras component related operations."""

    def run_verify_svc_state(self, svc: str, action: str, monitor_svcs: list):
        """Perform the given action on the given service and verify systemctl response.

        :param svc: service name on whoch action is to be performed
        :param action: start/stop/restart/..
        :param monitor_svcs: other services which should be monitored along with action.
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

        LOGGER.info("Performing %s on %s ...", action, svc)
        self.node_utils.send_systemctl_cmd(action, [svc], exc=True)

        LOGGER.info("Get systemctl status for %s ...", svc)
        services_status = self.get_svc_status([svc])
        a_sysctl_resp = services_status[svc]
        e_sysctl_resp = self.get_expected_systemctl_resp(action)
        svc_result = self.verify_systemctl_response(expected=e_sysctl_resp, actual=a_sysctl_resp)
        if svc_result:
            LOGGER.info("%s service state is as expected.")
        else:
            LOGGER.info("%s service state is NOT as expected.")

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
            status[svc] = self.parse_systemctl_status(response)
        return status

    def parse_systemctl_status(self, response):
        """Parse the keywords from the systemctl response.

        :param response: byte response
        :return [type]: Parsed systemctl status response.
        """
        response = response.decode("utf8")
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

    def put_svc_activating(self):
        

    def put_svc_deactivating(self):
        pass

    def put_svc_reloading(self):
        pass

    def put_svc_restarting(self):
        pass

    def edit_svc_config(self, content:dict):
        dpath, fname = os.path.split(self.svc_path)
        response = self.node_utils.read_file(fname,dpath)
        for key, value in content.items():
            if key in response:
                # replace the value
            else:
                # insert the value
        self.node_utils.rename_file(self.svc_path,self.get_tmp_svc_path())
        f_obj = self.node_utils.create_file(self.svc_path, )
        f.obj.write(response)
        

    def restore_svc_config(self):
        self.node_utils.rename_file(self.get_tmp_svc_path(),self.svc_path)

    def get_tmp_svc_path():
        dpath, fname = os.path.split(self.svc_path)
        tmp_svc_path = os.join(dpath,fname+"tmp")
        return tmp_svc_path