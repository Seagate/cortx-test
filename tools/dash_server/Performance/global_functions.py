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
# -*- coding: utf-8 -*-
# !/usr/bin/python

import yaml

config_path = 'Performance/configs/configs.yml'
benchmark_config = 'Performance/configs/benchmark.yml'

def makeconfig(name):  #function for connecting with configuration file
    with open(name) as config_file:
        configs = yaml.safe_load(config_file)
    return configs


def get_chain(version):
    from Performance.mongodb_api import find_documents
    uri, db, col = get_db_details()
    cursor = find_documents({'Title' : 'Main Chain'}, uri, db, col)
    chain = cursor[0][version]

    return chain


def get_db_details():
    import sys
    from urllib.parse import quote_plus

    config = makeconfig(config_path)
    try:
        db_hostname = config["PerfDB"]["hostname"]
        db_name = config["PerfDB"]["database"]
        db_collection = config["PerfDB"]["collection"]
        db_username = config["PerfDB"]["auth"]["full_access_user"]
        db_password = config["PerfDB"]["auth"]["full_access_password"]

    except KeyError:
        print("Could not get performance DB information. Please verify config.yml file")
        sys.exit(1)

    if not db_username or not db_password:
        print("Please set username and password for performance DB in config.yml file")
        sys.exit(1)

    uri = "mongodb://{0}:{1}@{2}".format(quote_plus(db_username),
                                         quote_plus(db_password),
                                         db_hostname)
    return uri, db_name, db_collection


def keys_exists(element, *keys):
    """Check if *keys (nested) exists in `element` (dict)."""
    if not isinstance(element, dict):
        raise AttributeError('keys_exists() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


def round_off(value, base=1):
    """
    Summary: Round off to nearest int

    Input : (number) - number
            (base) - round off to nearest base
    Returns: (int) - rounded off number
    """
    if value < 1:
        return round(value, 2)
    if value < 26:
        return int(value)
    return base * round(value / base)

def get_dict_from_array(options, makeReverse, allcaps=False):
    if makeReverse:
        options.reverse()
    versions = [
            {'label' : option, 'value' : option} for option in options
    ]

    if allcaps:
        versions = [
            {'label' : option.upper(), 'value' : option} for option in options
        ]
        return versions

    return versions
