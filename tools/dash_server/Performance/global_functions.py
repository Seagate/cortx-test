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
import sys
from urllib.parse import quote_plus
from Performance.mongodb_api import find_distinct_values
from Performance.schemas import get_dropdown_labels

config_path = 'Performance/configs/configs.yml'
benchmark_config = 'Performance/configs/benchmark.yml'


def makeconfig(name):  # function for connecting with configuration file
    with open(name) as config_file:
        configs = yaml.safe_load(config_file)
    return configs


def get_chain(version):
    from Performance.mongodb_api import find_documents
    uri, db, col = get_db_details()
    cursor = find_documents({'Title': 'Main Chain'}, uri, db, col)
    chain = cursor[0][version]

    return chain


def get_db_details(release=1):

    config = makeconfig(config_path)
    try:
        db_hostname = config["PerfDB"]["hostname"]
        db_name = config["PerfDB"]["database"]
        db_collection = config["PerfDB"]["collection"]["R{}".format(
            int(release))]
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


def keys_exists(data, key):
    """Check if *keys (nested) exists in `element` (dict)."""
    if not isinstance(data, dict):
        raise AttributeError('keys_exists() expects dict as first argument.')

    if key in data.keys():
        return True
    else:
        return False


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


def get_distinct_keys(release, field_to_query, query):
    uri, db, col = get_db_details(release)
    results = find_distinct_values(field_to_query, query, uri, db, col)

    return results


def get_dict_from_array(options, makeReverse, extension=None):
    if makeReverse:
        options.reverse()

    if extension:
        extension_value = get_dropdown_labels(extension)
        versions = [
            {'label': f"{option}{extension_value}", 'value': option} for option in options
        ]
        return versions
    else:
        versions = [
            {'label': f"{option}", 'value': option} for option in options
        ]
        return versions


def fetch_configs_from_file(benchmark_config, bench, prop):
    config = makeconfig(benchmark_config)
    return config[bench][prop]


def sort_builds_list(builds):
    temp_builds = builds
    data_sorted = []
    for key in builds:
        if key.startswith('cortx'):
            data_sorted.append(key)

    for key in data_sorted:
        temp_builds.remove(key)

    temp_builds.sort(key=lambda x: int(x.split("-")[0]))
    data_sorted = data_sorted + temp_builds

    return data_sorted


def get_unique_object_sizes(input_list):
    unique_list = []
    for x in input_list:
        if x not in unique_list:
            unique_list.append(x)
    return unique_list


def sort_object_sizes_list(obj_sizes):
    #Remove any space in object size string, it should only have number and two letter unit without space
    obj_sizes = [ s.replace(' ', '') for s in obj_sizes ]

    sizes_sorted = {
        'KB': [], 'MB': [], 'GB': [],
    }
    rest = []
    data_sorted = []
    for size in obj_sizes:
        if size.upper().endswith("KB"):
            sizes_sorted['KB'].append(size)
        elif size.upper().endswith("MB"):
            sizes_sorted['MB'].append(size)
        elif size.upper().endswith("GB"):
            sizes_sorted['GB'].append(size)
        else:
            rest.append(size)

    for size_unit in sizes_sorted.keys():
        objects = sizes_sorted[size_unit]
        temp = [int(obj[:-2]) for obj in objects]
        temp.sort()
        for item in temp:
            for obj in objects:
                if obj[:-2] == str(item):
                    data_sorted.append(str(item) + size_unit)
                    break
    if any(rest):
        data_sorted.extend(rest)

    # Removing duplicate sizes which appear if multiple unit format exist on DB to store object size
    data_sorted = get_unique_object_sizes(data_sorted)

    return data_sorted


def get_profiles(release, branch, build):
    pkeys = get_distinct_keys(release, 'PKey', {
        'Branch': branch, 'Build': build
    })

    reference = ('ITR1', '2N', '1C', '0PC', 'NA')
    pkey_split = {}
    options = []

    for key in pkeys:
        pkey_split[key] = key.split("_")[3:]

    for profile_list in list(pkey_split.values()):
        tag = 'Nodes {}, '.format(profile_list[1][:-1])

        if profile_list[2] != reference[2]:
            tag = tag + 'Clients {}, '.format(profile_list[2][:-1])

        tag = tag + 'Filled {}%, '.format(profile_list[3][:-2])
        tag = tag + 'Iteration {}'.format(profile_list[0][3:])
        if profile_list[4] != reference[4]:
            tag = tag + ', {}'.format(profile_list[4])

        option = {'label': tag, 'value': '_'.join(
            [profile_list[0], profile_list[1], profile_list[2], profile_list[3], profile_list[4]])}
        if option not in options:
            options.append(option)

    return options
