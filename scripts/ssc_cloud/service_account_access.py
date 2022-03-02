""" Service account access utility."""
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
# -*- coding: utf-8 -*-

import os
import argparse
import csv
from vm_management import VmStateManagement


# cloned test plan csv name
AVAILABLE_VM_CSV = 'available_vms.csv'
COLLECTION = "r2_vm_pool"


def main(args):
    """
    main function to service account info from db
    """
    vm_state = VmStateManagement(COLLECTION)
    if args.action == "get_setup":
        nodes = int(args.nodes)
        lock_acquired, setup_info = vm_state.get_available_system(nodes)
        if lock_acquired:
            with open(os.path.join(os.getcwd(), AVAILABLE_VM_CSV), 'w', newline='') as vm_info_csv:
                writer = csv.writer(vm_info_csv)
                writer.writerow([setup_info["setup_name"], setup_info["client"],
                                 setup_info["hostnames"], setup_info["data_ip"],
                                 setup_info['m_vip'], setup_info['nodes']])
            return lock_acquired
    elif args.action == "mark_setup_free":
        lock_released = vm_state.unlock_system(args.setupname)
        return lock_released


def parse_args():
    """
    parse user args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", choices=['get_setup', 'mark_setup_free'], required=True,
                        help="action to be performed")
    parser.add_argument("-s", "--setupname", type=str,
                        help="set up name")
    parser.add_argument("-n", "--nodes", type=str,
                        help="number of nodes in set up")
    parser.add_argument("-c", "--client", type=str,
                        help="client hostname")
    parser.add_argument("-v", "--vm_names", nargs='+', type=str,
                        help="hostnames")
    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
