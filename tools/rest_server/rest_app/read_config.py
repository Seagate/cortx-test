# -*- coding: utf-8 -*-
# !/usr/bin/python
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

mongodb_uri = "mongodb://{0}:{1}@{2}"
