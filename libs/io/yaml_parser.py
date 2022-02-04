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
"""Yaml Parser for IO stability"""

import datetime
import yaml
import logging

logger = logging.getLogger()


def yaml_parser(yaml_file):
    """
    YAML file to python dictionary
    """
    logger.debug("YAML file selected for parse: %s", yaml_file)
    yaml_dict = dict()
    with open(yaml_file) as obj:
        data = yaml.safe_load(obj)
        yaml_dict.update(data)
    return yaml_dict


def convert_to_bytes(size):
    """
    function to convert any size to bytes
    """
    kb = 1000
    kib = 1024
    sz = size.lower()
    if 'bytes' in sz or 'byte' in sz:
        return int(sz.split('byte')[0])
    elif 'kb' in sz:
        return int(sz.split('kb')[0]) * kb
    elif 'kib' in sz:
        return int(sz.split('kib')[0]) * kib
    elif 'mb' in sz:
        return int(sz.split('mb')[0]) * kb * kb
    elif 'mib' in sz:
        return int(sz.split('mib')[0]) * kib * kib
    elif 'gb' in sz:
        return int(sz.split('gb')[0]) * kb * kb * kb
    elif 'gib' in sz:
        return int(sz.split('gib')[0]) * kib * kib * kib
    elif 'tb' in sz:
        return int(sz.split('tb')[0]) * kb * kb * kb * kb
    elif 'tib' in sz:
        return int(sz.split('tib')[0]) * kib * kib * kib * kib


def convert_to_time_delta(time):
    """
    function to convert execution time in time delta format
    """
    time = time.lower()
    days = hrs = mnt = sec = 00
    if 'd' in time:
        days = int(time.split('d')[0])
        time = time.split('d')[1]
    if 'h' in time:
        hrs = int(time.split('h')[0])
        time = time.split('h')[1]
    if 'm' in time:
        mnt = int(time.split('m')[0])
        time = time.split('m')[1]
    if 's' in time:
        sec = int(time.split('s')[0])
    return datetime.timedelta(days=days, hours=hrs, minutes=mnt, seconds=sec)


def test_parser(yaml_file):
    """
    parse a test yaml file
    """
    s3_io_test = yaml_parser(yaml_file)
    delta_list = list()
    for test, data in s3_io_test.items():
        start_bytes = convert_to_bytes(data['start_range'])
        data['start_range'] = start_bytes
        end_bytes = convert_to_bytes(data['end_range'])
        data['end_range'] = end_bytes
        if test == "test_1":
            data['start_time'] = str(datetime.timedelta(hours=00, minutes=00, seconds=00))
            delta_list.append(convert_to_time_delta(data['result_duration']))
        else:
            data['start_time'] = delta_list.pop()
            delta_list.append(data['start_time'] + convert_to_time_delta(data['result_duration']))
    return s3_io_test
