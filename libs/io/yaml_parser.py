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
"""IO Configs are initialized here."""

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
    sz = str(size[-2:]).lower()
    if sz in ['kb', 'mb', 'gb', 'tb']:
        if sz == "kb":
            return int(size[:-2]) * kb
        elif sz == "mb":
            return int(size[:-2]) * kb * kb
        elif sz == "gb":
            return int(size[:-2]) * kb * kb * kb
        elif sz == "tb":
            return int(size[:-2]) * kb * kb * kb * kb
    else:
        sz = str(size[-3:]).lower()
        if sz == "kib":
            return int(size[:-3]) * kib
        elif sz == "mib":
            return int(size[:-3]) * kib * kib
        elif sz == "gib":
            return int(size[:-3]) * kib * kib * kib
        elif sz == "tib":
            return int(size[:-3]) * kib * kib * kib * kib


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
