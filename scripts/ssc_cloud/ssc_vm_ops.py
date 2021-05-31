""" Script to perform operations on ssc cloud"""
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


import getpass
import os
import csv
import requests
import argparse
import json
import sys
import time
import random
import string

from requests.packages import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.auth import HTTPBasicAuth

# Disable insecure-certificate-warning message
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global Variable declaration
MAX_RETRY = 2
MAX_RETRY_FOR_SESSION = 2
BACK_OFF_FACTOR = 0.3
TIME_BETWEEN_RETRIES = 1000
ERROR_CODES = (500, 502, 504)
ITER_COUNT = 20

VM_INFO_CSV = 'ssc_vm_info.csv'


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
                  method_whitelist=frozenset(['GET', 'POST']))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


class VMOperations:
    """
    This will help to reduce manual workload required to create vm's
    for deployment and other vm related testing.
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
    stop_vm(): Stop the operation for given VM
    """

    def __init__(self, user, password):
        self.fqdn = "ssc-cloud.colo.seagate.com"
        self.url = ""
        self.method = "GET"
        self.payload = {}
        self.headers = {'content-type': 'application/json'}
        self.session = requests_retry_session(session=requests.Session())
        url = 'https://%s/api/auth' % self.fqdn
        response = self.session.get(url,
                                    auth=HTTPBasicAuth(user, password),
                                    verify=False)
        self.token = response.json()['auth_token']

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
        Check status
        """
        self.url = _response['task_href']
        self.method = "GET"
        self.payload = ""
        _count = 0
        return_response = ''
        while _count < ITER_COUNT:
            time.sleep(30)
            return_response = self.execute_request()
            _rss_state = return_response['state']
            if _rss_state == "Finished":
                print(json.dumps(return_response, indent=4, sort_keys=True))
                break
            else:
                print("Checking the VM status again...")
                if _count == ITER_COUNT:
                    print('The request has been processed, but response state is not matched '
                          'with expectation')
                    sys.exit()
            _count += 1
        return return_response

    def get_vm_info(self, host):
        """
        Get VM information
        """
        self.payload = ""
        self.method = "GET"
        self.url = "https://%s/api/vms?expand=resources&filter%%5B%%5D=name='%s'" \
                   % (self.fqdn, host)
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.token}
        return self.execute_request()

    def create_vm_snap(self, host):
        """
        Create VM snapshot
        """
        _vm_info = self.get_vm_info(host)
        _vm_name = _vm_info['resources'][0]['name']
        name = "%s-%s" % (_vm_name, ''.join(random.sample(string.ascii_lowercase, 6)))
        self.method = "POST"
        self.url = _vm_info['resources'][0]['href'] + "/snapshots"
        self.payload = {
            "action": "create",
            "resources": [{"name": name, "description": name}]
        }
        response = self.execute_request()
        if response['results'][0]['success']:
            print(response['results'][0]['message'])
            _snap_res = self.check_status(response['results'][0])
            if _snap_res['state'] == "Finished":
                print("Created the VM snapshot. Message: %s" % _snap_res['message'])
                print(json.dumps(_snap_res, indent=4, sort_keys=True))
            else:
                print("Failed to create the VM snapshot...")
                print("Response: %s" % _snap_res)
        else:
            print("Failed to process the create VM snapshot API request...")
            sys.exit()
        return response

    def stop_vm(self, vm_id):
        """
        Stop VM
        """
        self.method = "POST"
        self.url = "https://%s/api/vms/%s" % (self.fqdn, vm_id)
        self.payload = {
            "action": "stop"
        }
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.token}
        # Process the request
        response = self.execute_request()
        if response['success']:
            print("Stopping the VM might take time...")
            _res_stop = self.check_status(response)
        return response

    def start_vm(self, vm_id):
        """
        Start VM
        """
        self.method = "POST"
        self.url = "https://%s/api/vms/%s" % (self.fqdn, vm_id)
        self.payload = {
            "action": "start"
        }
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.token}
        # Process the request
        response = self.execute_request()
        if response['success']:
            print("Starting the VM might take time...")
            _res_start = self.check_status(response)
        return response

    def revert_vm_snap(self, host, snap_id):
        """
        Revert VM snapshop
        """
        _vm_info = self.get_vm_info(host)
        _vm_state = _vm_info['resources'][0]['power_state']
        _vm_id = _vm_info['resources'][0]['id']
        _stop_res = ""
        vm_on = False
        # Stop the VM before snapshot revert
        if _vm_state == "on":
            _stop_res = self.stop_vm(_vm_id)
            if _stop_res:
                time.sleep(30)
                _vm_info = self.get_vm_info(host)
                _vm_state = _vm_info['resources'][0]['power_state']
                print("VM has been stopped successfully. VM status is %s.." % _vm_state)
        else:
            print("VM is already stopped...")

        if _stop_res or _vm_state == "off":
            print("Revert the VM snapshots...")
            self.method = "POST"
            self.payload = {"action": "revert"}
            self.url = "https://%s/api/vms/%s/snapshots/%s" % (
                self.fqdn, _vm_id, snap_id)
            self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.token}
            # Process the request
            response = self.execute_request()
            import pdb
            pdb.set_trace()
            if response["success"]:
                _revert_res = self.check_status(response)
                if _revert_res['state'] == "Finished":
                    print("Revert message: %s" % _revert_res['message'])
                    print(json.dumps(_revert_res, indent=4, sort_keys=True))
                    # Start the VM after snapshot revert
                    _start_res = self.start_vm(_vm_id)
                    if _start_res:
                        print("Started the VM after snapshot revert")
                        print(json.dumps(_start_res, indent=4, sort_keys=True))
                        vm_on = True
                    else:
                        print("Failed to start the VM after revert...")
                else:
                    print("Failed to revert the VM...")
                    print("Response: %s" % _revert_res)
            else:
                print("Failed to process the revert API request...")
                sys.exit()
        return vm_on

    def list_vm_snaps(self, host):
        """
        List VM snapshots
        """
        _vm_info = self.get_vm_info(host)
        _vm_id = _vm_info['resources'][0]['id']
        self.url = "https://%s/api/vms/%s/snapshots" % (self.fqdn, _vm_id)
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.token}
        # Process the request
        result = self.execute_request()
        last_snap_id = ''
        if result:
            print(json.dumps(result, indent=4, sort_keys=True))
            try:
                last_snapshot = result["resources"][0]['href']
                last_snap_id = last_snapshot.split('/')[-1]
            except Exception as e:
                print(e)
            return last_snap_id

    def get_vms(self):
        """
        Download all VMs information into csv
        """
        self.payload = ""
        self.method = "GET"
        self.url = f"https://{self.fqdn}/api/vms?expand=resources&&filter%%5B%%5D"
        self.headers = {'content-type': 'application/json', 'X-Auth-Token': self.token}
        return_response = self.execute_request()
        vm_names = []
        for i in range(len(return_response['resources'])):
            vm_name = return_response['resources'][i]['name']
            pwr = return_response['resources'][i]["power_state"]
            retired = return_response['resources'][i]["retired"]
            print(vm_name, pwr, retired)
            vm_names.append([vm_name, pwr, retired])
        with open(os.path.join(os.getcwd(), VM_INFO_CSV), 'w', newline='') as vm_info_csv:
            writer = csv.writer(vm_info_csv)
            writer.writerow(['VM Name', 'Power State'])
            for vm in vm_names:
                if not vm[2]:  # non retired vm
                    writer.writerow([vm[0], vm[1]])
        return vm_names


def get_ssc_credential():
    """
    Function to get SSC cloud credentials.
    """
    try:
        ssc_user_id = os.environ['SSC_CLOUD_ID']
        ssc_pd = os.environ['SSC_CLOUD_PASSWORD']
    except KeyError:
        print("SSC credentials not found in environment")
        ssc_user_id = input("SSC username: ")
        ssc_pd = getpass.getpass("SSC password: ")
        os.environ['SSC_CLOUD_ID'] = ssc_user_id
        os.environ['SSC_CLOUD_PASSWORD'] = ssc_pd
    return ssc_user_id, ssc_pd


if __name__ == "__main__":
    ssc_id, ssc_pwd = get_ssc_credential()
    vm_ops = VMOperations(ssc_id, ssc_pwd)
    res = vm_ops.get_vms()
    if res:
        print("Getting vm information is successful")
    else:
        print("Error in getting vm information")
