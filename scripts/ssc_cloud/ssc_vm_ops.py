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
#
import argparse
import csv
import json
import logging
import os
import random
import string
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.packages import urllib3
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)

# Disable insecure-certificate-warning message
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global Variable declaration
VM_INFO_CSV = 'vm_details.csv'
MAX_RETRY = 2
MAX_RETRY_FOR_SESSION = 2
BACK_OFF_FACTOR = 0.3
TIME_BETWEEN_RETRIES = 1000
ERROR_CODES = (500, 502, 504)
ITER_COUNT = 20


def requests_retry_session(retries=MAX_RETRY_FOR_SESSION,
                           back_off_factor=BACK_OFF_FACTOR,
                           status_force_list=ERROR_CODES,
                           session=None):
    """
    Create a session to process SSC API request
    Parameters:
    ----------
        status_force_list (list): Error codes list to retry
        back_off_factor (float): Back-off factor
        retries (float): Maximum retry per session
        session (object): None
    Returns:
    -------
       session (object): Session Object to process REST API
    """
    session = session
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=back_off_factor,
                  status_forcelist=status_force_list,
                  allowed_methods=frozenset(['GET', 'POST']))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_args():
    """
    Read the parameter from commandline
    Returns:
    parser (list): Parsed commandline parameter
    """
    # Create the parser
    parser = argparse.ArgumentParser()
    # Add the arguments
    parser.add_argument('--action', '-a',
                        choices=['create_vm_snap', 'create_vm', 'list_vm_snaps', 'revert_vm_snap',
                                 'retire_vm', 'get_vm_info', 'get_vms', 'refresh_vm',
                                 'power_on', 'power_off'], required=True,
                        help="Perform the Operation")
    parser.add_argument('--token', '-t', help="Token for API Authentication")
    parser.add_argument('--fqdn', '-f', choices=['ssc-cloud.colo.seagate.com'],
                        default="ssc-cloud.colo.seagate.com", help="SSC hostname")
    parser.add_argument('--service_template', '-s', help="Service Template ID for VM creation")
    parser.add_argument('--service_id', '-i', help="Service Template ID for VM creation")
    parser.add_argument('--host', '-v', help="SSC VM name")
    parser.add_argument('--extra_disk_count', '-d', default=8, choices=range(1, 12),
                        help="Extra disk count of the VM")
    parser.add_argument('--extra_disk_size', '-k', default=25, choices=[25, 50, 75, 100],
                        help="Extra disk size of the VM")
    parser.add_argument('--cpu', '-c', default=4, choices=[1, 2, 4, 8],
                        help="Number of Core for VM")
    parser.add_argument('--memory', '-m', default=8192, choices=[4096, 8192, 16384],
                        help="VM Memory")
    parser.add_argument('--snap_id', '-n', help="Snap ID of the VM")
    parser.add_argument('--user', '-u', help="GID of the user for SSC Auth")
    parser.add_argument('--password', '-p', help="Password of the user for SSC Auth")
    parser.add_argument('--vm_service_id', '-r', help="Service ID of the VM")
    # Execute the parse_args() method and return
    return parser.parse_args()


class VMOperations:
    """
    This will help to reduce manual workload required to create vm's for deployment and other
    vm related testing.
    Attributes
    ----------
    parameters (list) : Commandline Inputs
    Methods
    -------
    create_vm(): Create the SSC VM for the given service template
    get_vm_info(): Get the information about the VM
    retire_service(): Retires given service
    retire_vm(): Retires the given VM
    list_vm_snaps(): List all the snapshots for the given VM
    get_catalog_id(): Get the service catalog for the given VM
    revert_vm_snap(): Revert the snapshot for the given VM
    power_off_vm(): Stop the operation for given VM
    power_on_vm(): Start the operation for given VM
    get_vms() : Download all available VMs to csv
    refresh_vm_state(): Refresh the given VM state
    """

    def __init__(self, parameters):
        self.args = parameters
        self.url = ""
        self.method = "GET"
        self.payload = {}
        self.headers = {'content-type': 'application/json'}
        self.session = requests_retry_session(session=requests.Session())

        if not parameters.token:
            _url = 'https://%s/api/auth' % parameters.fqdn
            _response = self.session.get(_url,
                                         auth=HTTPBasicAuth(parameters.user, parameters.password),
                                         verify=False)
            self.args.token = _response.json()['auth_token']
            print(self.args.token)

    def execute_request(self):
        """
        Execute request
        """
        try:

            if self.method == "POST":
                r = self.session.post(self.url, data=json.dumps(self.payload), headers=self.headers,
                                      verify=False)
            else:
                r = self.session.get(self.url, data=json.dumps(self.payload), headers=self.headers,
                                     verify=False)
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        return r.json()

    def check_status(self, _response):
        """
        Check status of request
        """
        self.url = _response['task_href']
        self.method = "GET"
        self.payload = ""
        _count = 0
        _res = ''
        while _count < ITER_COUNT:
            time.sleep(30)
            _res = self.execute_request()
            _rss_state = _res['state']
            if _rss_state == "Finished":
                print(json.dumps(_res, indent=4, sort_keys=True))
                break
            else:
                print("Checking the VM status again...")
                if _count == ITER_COUNT:
                    print(
                        'The request has been processed, but response state is not matched '
                        'with expectation')
                    sys.exit()
            _count += 1
        return _res

    def get_catalog_id(self):
        """
        Get catalog id
        """
        self.method = "GET"
        self.payload = ""
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        self.url = "https://%s/api/service_templates/%s" % (
            self.args.fqdn, self.args.service_template)
        # Process the request
        return self.execute_request()

    def create_vm(self):
        """
        Create new vm
        """
        service_template_resp = self.get_catalog_id()
        service_catalog_id = service_template_resp['service_template_catalog_id']
        self.method = "POST"
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        self.url = "https://%s/api/service_catalogs/%s/service_templates/%s" \
                   % (self.args.fqdn, service_catalog_id, self.args.service_template)
        self.payload = {
            "action": "order",
            "resource": {
                "href": "https://%s/api/service_templates/%s" % (
                    self.args.fqdn, self.args.service_template),
                "dialog_check_box_1": "t",
                "extra_disk_count": self.args.extra_disk_count,
                "extra_disk_size": self.args.extra_disk_size,
                "option_0_vm_memory": self.args.memory,
                "option_0_cores_per_socket": self.args.cpu,
                "dialog_share_vms_disks": "t"
            }
        }

        # Process the request
        _response = self.execute_request()
        if _response['status'] == "Ok":
            self.method = "GET"
            _service_req_url = _response['href']
            self.url = "%s??expand=request_tasks" % _service_req_url
            self.payload = ""
            print("Creating the VM might take time...")
            _count = 0
            while _count < ITER_COUNT:
                time.sleep(60)
                vm_status_res = self.execute_request()
                _vm_state = vm_status_res['request_state']
                _count += 1
                if _vm_state == "finished":
                    print("Expected VM state is matched with current VM state")
                    _vm_message = vm_status_res['message']
                    print("VM message: %s" % _vm_message)
                    print(json.dumps(vm_status_res, indent=4, sort_keys=True))
                    break
                else:
                    print("Expected VM state is finished, but current state is %s..." % _vm_state)
                    if _count == ITER_COUNT:
                        print('VM has ordered successfully, but VM state is not matched')
                        sys.exit()
        else:
            print("Failed to process the VM request..%s" % _response)
        return _response

    def get_vms(self):
        """
        Get vms information
        """
        self.payload = ""
        self.method = "GET"
        self.url = f"https://{self.args.fqdn}/api/services?expand=resources"
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        res = self.execute_request()
        with open(os.path.join(os.getcwd(), VM_INFO_CSV), 'w', newline='') as vm_info_csv:
            writer = csv.writer(vm_info_csv)
            writer.writerow(['service_id', 'service_name', 'name', 'power_state', 'created_on',
                             'cores', 'memory', 'disks', 'disk_size', 'retire_status',
                             'retires_on'])
            res_info = res['resources']
            for i in range(len(res['resources'])):
                ser_id = res_info[i]['id']
                self.url = f"https://{self.args.fqdn}/api/services/{ser_id}/vms?expand=resources"
                vm_res = self.execute_request()
                name = vm_res['resources'][0]['name']
                power_state = vm_res['resources'][0]['power_state']
                created_on = vm_res['resources'][0]['created_on']
                ret_status = vm_res['resources'][0]['retired']
                retires_on = vm_res['resources'][0]['retires_on']
                writer.writerow(
                    [ser_id, res_info[i]['name'], name, power_state, created_on,
                     res_info[i]['options']['dialog']['dialog_option_0_cores_per_socket'],
                     res_info[i]['options']['dialog']['dialog_option_0_vm_memory'],
                     res_info[i]['options']['dialog']['dialog_extra_disk_count'],
                     res_info[i]['options']['dialog']['dialog_extra_disk_size'],
                     ret_status, retires_on])
        return res

    def get_vm_info(self):
        """
        Get vm information
        """
        self.payload = ""
        self.method = "GET"
        self.url = "https://%s/api/vms?expand=resources&filter%%5B%%5D=name='%s'" \
                   % (self.args.fqdn, self.args.host)
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        return self.execute_request()

    def retire_vm(self):
        """
        Retire a vm
        """
        _get_vm_info = self.get_vm_info()
        _response = ""
        if _get_vm_info['resources'][0]['retirement_state'] != "retired":
            _vm_id = _get_vm_info['resources'][0]['id']
            self.method = "POST"
            # self.url = "https://%s/api/vms/%s" % (self.args.fqdn, _vm_id)
            self.url = f"https://{self.args.fqdn}/api/services/{self.args.vm_service_id}"
            self.payload = {
                "action": "request_retire"
            }
            self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
            # Process the request
            _response = self.execute_request()
            print("Retiring the VM might take time...")
            _count = 0
            while _count < ITER_COUNT:
                time.sleep(30)
                _vm_info = self.get_vm_info()
                _vm_state = _vm_info['resources'][0]['retirement_state']
                if _vm_state == "retired":
                    print("Matched current VM state and expected VM state")
                    print("VM has been retired successfully....")
                    print(json.dumps(_vm_info, indent=4, sort_keys=True))
                    break
                else:
                    print("Current VM state is %s, expected VM state is finished.." % _vm_state)
                    if _count == ITER_COUNT:
                        print('VM retire request has processed, but VM state is unexpected..')
                        sys.exit()
                _count += 1
        else:
            print("The VM already is in retired state...")
            sys.exit()
        return _response

    def list_vm_snaps(self):
        """
        List vm snapshots
        """
        _vm_info = self.get_vm_info()
        _vm_id = _vm_info['resources'][0]['id']
        self.url = "https://%s/api/vms/%s/snapshots" % (self.args.fqdn, _vm_id)
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        # Process the request
        return self.execute_request()

    def power_on_vm(self):
        """
        Power on VM
        """
        _vm_info = self.get_vm_info()
        _vm_state = _vm_info['resources'][0]['power_state']
        _vm_id = _vm_info['resources'][0]['id']
        _start_res = ""
        # Power off the VM
        if _vm_state == "on":
            print("VM is already ON")
        else:
            _start_res = self.start_vm(_vm_id)
            if _start_res:
                print("Started the VM")
                print(json.dumps(_start_res, indent=4, sort_keys=True))
            else:
                print("Failed to start the VM")
        return _start_res

    def power_off_vm(self):
        """
        Power off vm
        """
        _vm_info = self.get_vm_info()
        _vm_state = _vm_info['resources'][0]['power_state']
        _vm_id = _vm_info['resources'][0]['id']
        _stop_res = ""
        # Power off the VM
        if _vm_state == "on":
            _stop_res = self.stop_vm(_vm_id)
            if _stop_res:
                time.sleep(30)
                _vm_info = self.get_vm_info()
                _vm_state = _vm_info['resources'][0]['power_state']
                print("VM has been stopped successfully. VM status is %s.." % _vm_state)
        else:
            print("VM is already stopped...")
        return _stop_res

    def stop_vm(self, vm_id):
        """
        Stop vm
        """
        self.method = "POST"
        self.url = "https://%s/api/vms/%s" % (self.args.fqdn, vm_id)
        self.payload = {
            "action": "stop"
        }
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        # Process the request
        _response = self.execute_request()
        if _response['success']:
            print("Stopping the VM might take time...")
            _res_stop = self.check_status(_response)
        return _response

    def refresh_vm_state(self, vm_id=None):
        """
        Refresh vm state
        """
        _vm_info = self.get_vm_info()
        _vm_id = _vm_info['resources'][0]['id']
        vm_id = vm_id if vm_id else _vm_id
        self.method = "POST"
        self.url = "https://%s/api/vms/%s" % (self.args.fqdn, vm_id)
        self.payload = {
            "action": "refresh"
        }
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        # Process the request
        _response = self.execute_request()
        if _response['success']:
            print("Refreshing the VM might take time...")
            _res_stop = self.check_status(_response)
        return _response

    def start_vm(self, vm_id):
        """
        Start VM
        """
        self.method = "POST"
        self.url = "https://%s/api/vms/%s" % (self.args.fqdn, vm_id)
        self.payload = {
            "action": "start"
        }
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
        # Process the request
        _response = self.execute_request()
        if _response['success']:
            print("Starting the VM might take time...")
            _res_start = self.check_status(_response)
        return _response

    def create_vm_snap(self, _response=''):
        """
        Create vm snapshot
        """
        _vm_info = self.get_vm_info()
        _vm_name = _vm_info['resources'][0]['name']
        name = "%s-%s" % (_vm_name, ''.join(random.sample(string.ascii_lowercase, 6)))
        self.method = "POST"
        self.url = _vm_info['resources'][0]['href'] + "/snapshots"
        self.payload = {
            "action": "create",
            "resources": [{"name": name, "description": name}]
        }
        _response = self.execute_request()
        if _response['results'][0]['success']:
            print(_response['results'][0]['message'])
            _snap_res = self.check_status(_response['results'][0])
            if _snap_res['state'] == "Finished":
                print("Created the VM snapshot. Message: %s" % _snap_res['message'])
                print(json.dumps(_snap_res, indent=4, sort_keys=True))
            else:
                print("Failed to create the VM snapshot...")
                print("Response: %s" % _snap_res)
        else:
            print("Failed to process the create VM snapshot API request...")
            sys.exit()
        return _response

    def revert_vm_snap(self, _response=''):
        """
        Revert vm snapshot
        """
        LOGGER.debug('Running revert vm snap')
        if not self.args.snap_id:
            self.payload = ""
            self.method = "GET"
            self.url = "https://%s/api/vms?expand=resources&attributes=" \
                       "name,vendor,snapshots&filter[]=name='%s'" \
                       % (self.args.fqdn, self.args.host)
            self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
            res = self.execute_request()
            if res:
                snapshots = res['resources'][0]['snapshots']
                for _, snap in enumerate(snapshots):
                    name = snap['name']
                    if name != 'Active VM':
                        print(name)
                        LOGGER.debug('vm name %s', name)
                        snap_id = snap['id']
                        print(snap_id)
                        LOGGER.debug('snap_id %s', snap_id)
                        self.args.snap_id = snap_id
                        break
        _vm_info = self.get_vm_info()
        _vm_state = _vm_info['resources'][0]['power_state']
        _vm_id = _vm_info['resources'][0]['id']
        _stop_res = ""

        # Stop the VM before snapshot revert
        if _vm_state == "on":
            _stop_res = self.stop_vm(_vm_id)
            if _stop_res:
                time.sleep(120)
                _vm_info = self.get_vm_info()
                _vm_state = _vm_info['resources'][0]['power_state']
                while _vm_state != "off":
                    time.sleep(60)
                    self.refresh_vm_state(_vm_id)
                    _vm_info = self.get_vm_info()
                    _vm_state = _vm_info['resources'][0]['power_state']
                    LOGGER.debug("VM status is %s", _vm_state)
                print("VM has been stopped successfully. VM status is %s.." % _vm_state)
                LOGGER.debug("VM has been stopped successfully. VM status is %s", _vm_state)
        else:
            print("VM is already stopped...")
            LOGGER.debug("VM is already stopped...")

        time.sleep(120)  # add wait for VM to get stopped

        if _stop_res or _vm_state == "off":
            print("Revert the VM snapshots...")
            LOGGER.debug("Revert the VM snapshots...")
            self.method = "POST"
            self.payload = {"action": "revert"}
            self.url = "https://%s/api/vms/%s/snapshots/%s" % (
                self.args.fqdn, _vm_id, self.args.snap_id)
            self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.args.token}
            # Process the request
            _response = self.execute_request()
            LOGGER.debug(json.dumps(_response, indent=4, sort_keys=True))
            if _response["success"]:
                _revert_res = self.check_status(_response)
                if _revert_res['state'] == "Finished":
                    print("Revert message: %s" % _revert_res['message'])
                    LOGGER.debug("Revert message: %s", _revert_res['message'])
                    print(json.dumps(_revert_res, indent=4, sort_keys=True))
                    LOGGER.debug(json.dumps(_revert_res, indent=4, sort_keys=True))
                    # Start the VM after snapshot revert
                    time.sleep(60)
                    _start_res = self.start_vm(_vm_id)
                    if _start_res:
                        _vm_info = self.get_vm_info()
                        _vm_state = _vm_info['resources'][0]['power_state']
                        while _vm_state != "on":
                            time.sleep(60)
                            self.refresh_vm_state(_vm_id)
                            _vm_info = self.get_vm_info()
                            _vm_state = _vm_info['resources'][0]['power_state']
                            LOGGER.debug("VM status is %s", _vm_state)
                        print("Started the VM after snapshot revert")
                        print(json.dumps(_start_res, indent=4, sort_keys=True))
                        LOGGER.debug("Started the VM after snapshot revert")
                        LOGGER.debug(json.dumps(_start_res, indent=4, sort_keys=True))
                    else:
                        print("Failed to start the VM after revert...")
                        LOGGER.debug("Failed to start the VM after revert...")
                        sys.exit(1)
                else:
                    print("Failed to revert the VM...")
                    print("Response: %s" % _revert_res)
                    LOGGER.debug("Failed to revert the VM...")
                    LOGGER.debug("Response: %s", _revert_res)
                    sys.exit(1)
            else:
                print("Failed to process the revert API request...")
                LOGGER.debug("Failed to process the revert API request...")
                sys.exit(1)
        else:
            print("Could not stop VM")
            LOGGER.debug("Could not stop VM")
            sys.exit(1)
        return _response


def main():
    """
    main function
    """
    args = get_args()
    if not (args.user and args.password) and not args.token:
        sys.exit("Specify either token/password for SSC Auth...")

    result = {}
    # Create a VM operations object
    vm_object = VMOperations(args)
    print("Processing the %s....." % args.action)

    # Check validation for each actions
    if args.action == "create_vm":
        if args.service_template:
            result = vm_object.create_vm()
    elif args.action == "retire_vm":
        if args.host and args.vm_service_id:
            result = vm_object.retire_vm()
    elif args.action == "get_vm_info":
        if args.host:
            result = vm_object.get_vm_info()
    elif args.action == "get_vms":
        result = vm_object.get_vms()
    elif args.action == "list_vm_snaps":
        if args.host:
            result = vm_object.list_vm_snaps()
    elif args.action == "revert_vm_snap":
        if args.host:
            result = vm_object.revert_vm_snap()
    elif args.action == "create_vm_snap":
        if args.host:
            result = vm_object.create_vm_snap()
    elif args.action == "power_on":
        if args.host:
            result = vm_object.power_on_vm()
    elif args.action == "power_off":
        if args.host:
            result = vm_object.power_off_vm()
    elif args.action == "refresh_vm":
        if args.host:
            result = vm_object.refresh_vm_state()

    if result:
        print("VM operation %s request has been polled successfully....." % args.action)
        print(json.dumps(result, indent=4, sort_keys=True))
    else:
        print("Please check the command-line parameter")


if __name__ == '__main__':
    main()
