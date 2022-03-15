# -*- coding: utf-8 -*-
# !/usr/bin/python
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
"""Read config file for database."""

import configparser
import sys

config = configparser.ConfigParser()
config.read('config.ini')
try:
    db_hostname = config["MongoDB"]["db_hostname"]
    db_name = config["MongoDB"]["db_name"]
    results_collection = config["MongoDB"]["results_collection"]
    cmi_collection = config["MongoDB"]["cmi_collection"]
    system_collection = config["MongoDB"]["system_info_collection"]
    timing_collection = config["MongoDB"]["timing_collection"]
    vm_pool_collection = config["MongoDB"]["pool_vm_collection"]
except KeyError:
    print("Could not start REST server. Please verify config.ini file")
    sys.exit(1)

MONGODB_URI = "mongodb://{0}:{1}@{2}"
