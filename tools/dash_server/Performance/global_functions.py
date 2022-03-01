"""Global functions needed across Performance files"""
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
# !/usr/bin/python

from __future__ import absolute_import
from builtins import round
import yaml
import sys
from urllib.parse import quote_plus
from Performance.mongodb_api import find_distinct_values
from Performance.schemas import get_dropdown_labels

config_path = 'Performance/configs.yml'


def makeconfig(name):  # function for connecting with configuration file
    with open(name) as config_file:
        configs = yaml.safe_load(config_file)
    return configs


def get_db_details(release=1):

    config = makeconfig(config_path)
    try:
        db_hostname = config["PerfDB"]["hostname"]
        db_name = config["PerfDB"]["database"]
        db_collection = config["PerfDB"]["collection"]["{}".format(release)]
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
    try:
        value = float(value)
        if value < 10:
            return round(value, 3)
        if value < 26:
            return int(value)
        return base * round(value / base)
    except (ValueError, TypeError):
        return "NA"


def get_distinct_keys(release, field_to_query, query):
    uri, db, col = get_db_details(release)
    results = find_distinct_values(field_to_query, query, uri, db, col)

    return results


def get_dict_from_array(options, make_reverse, extension=None):
    """
    returns a dictionary in a format needed for populating dropdowns

    Args:
        options: list of options to show in the dropdown
        make_reverse: bool to reverse the options or not
        extension: a dictionary containing extensions to the options if any

    Returns:
        dict: dictionary of all versions
    """
    if make_reverse:
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


def sort_builds_list(builds):
    """
    function to sort builds chronologicaly

    Args:
        list: list of builds

    Returns:
        list: a list of builds with higher build number first
    """
    temp_builds = list(dict.fromkeys(builds))
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
    """
    function to remove duplicates from the list

    Args:
        list: input list
    Returns:
        list: unique elements list
    """
    unique_list = []
    for x in input_list:
        if x not in unique_list:
            unique_list.append(x)
    return unique_list


def sort_object_sizes_list(obj_sizes):
    """
    function to sort given list of object sizes wrt their units
    given array will have strings of object sizes with units,
    this function will sort them wrt their sizes.

    Args:
        list: list of object sizes

    Returns:
        returns a sorted list
    """
    # Remove any space in object size string, it should only have number and two letter unit without space
    obj_sizes = [s.replace(' ', '') for s in obj_sizes]
    obj_sizes = list(dict.fromkeys(obj_sizes))

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


def sort_sessions(sessions):
    """
    Function to sort sessions array
    Args:
        sessions: list of all sessions

    Returns:
        sessions: list of sorted sessions
    """
    sessions = list(dict.fromkeys(sessions))
    new_sessions = []
    for session in sessions:
        new_sessions.append(int(session))

    return sorted(new_sessions)


def check_empty_list(array):
    """
    Function to check given array is empty or not.
    It will look for all None, all NA or an empty array.

    Args:
        array: list to check if it is empty or not

    Returns:
        bool: True / False for empty or not
    """
    is_empty = False
    elements = list(set(array))
    if not array:
        is_empty = True
    elif elements[0] == "NA" and len(elements) == 1:
        is_empty = True
    elif elements[0] is None and len(elements) == 1:
        is_empty = True
    else:
        is_empty = False

    return is_empty
