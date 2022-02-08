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
import logging
import yaml

logger = logging.getLogger()


def yaml_parser(yaml_file):
    """
    YAML file to python dictionary
    :param yaml_file: yaml file to parse
    :return python dict containing file contents
    """
    logger.debug("YAML file selected for parse: %s", yaml_file)
    yaml_dict = dict()
    with open(yaml_file) as obj:
        data = yaml.safe_load(obj)
        yaml_dict.update(data)
    logger.debug("YAML file data: %s", yaml_dict)
    return yaml_dict


def convert_to_bytes(size):
    """
    function to convert any size to bytes
    :param size: object size
    can be provided as byte(s), kb, kib, mb, mib, gb, gib, tb, tib
    :return equivalent bytes value for object size
    """
    kb = 1000
    kib = 1024
    size = size.lower()
    if 'bytes' in size or 'byte' in size:
        return int(size.split('byte')[0])
    if 'kb' in size:
        return int(size.split('kb')[0]) * kb
    if 'kib' in size:
        return int(size.split('kib')[0]) * kib
    if 'mb' in size:
        return int(size.split('mb')[0]) * kb * kb
    if 'mib' in size:
        return int(size.split('mib')[0]) * kib * kib
    if 'gb' in size:
        return int(size.split('gb')[0]) * kb * kb * kb
    if 'gib' in size:
        return int(size.split('gib')[0]) * kib * kib * kib
    if 'tb' in size:
        return int(size.split('tb')[0]) * kb * kb * kb * kb
    if 'tib' in size:
        return int(size.split('tib')[0]) * kib * kib * kib * kib
    return 0


def convert_to_time_delta(time):
    """
    function to convert execution time in time delta format
    :param time : accepts time in format 0d0h0m0s
    :return python timedelta object
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
    datetime_obj = datetime.timedelta(days=days, hours=hrs, minutes=mnt, seconds=sec)
    logger.debug("Date time object: %s", str(datetime_obj))
    return datetime_obj


def test_parser(yaml_file):
    """
    parse a test yaml file
    :param yaml_file: accepts and parses a test YAML file
    :return python dictionary containing file contents
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
    logger.debug("test object %s: ", s3_io_test)
    return s3_io_test
