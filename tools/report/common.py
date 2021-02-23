"""Helper functions to generate csv report."""
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
import configparser
import sys
from urllib.parse import quote_plus


def get_db_details():
    """Read DB details from config.init file"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        db_hostname = config["PerfDB"]["db_hostname"]
        db_name = config["PerfDB"]["db_name"]
        db_collection = config["PerfDB"]["db_collection"]
        db_username = config["PerfDB"]["db_username"]
        db_password = config["PerfDB"]["db_password"]
    except KeyError:
        print("Could not get performance DB information. Please verify config.ini file")
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


def round_off(value, base=25):
    """
    Summary: Round off to nearest 25

    Input : (number) - number
            (base) - round off to nearest base
    Returns: (int) - rounded off number
    """
    if value < 26:
        return int(value)
    return base * round(value / base)
