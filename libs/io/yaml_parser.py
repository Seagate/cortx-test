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
    sz = str(size[-2:]).lower()
    if sz == "kb":
        return int(size[:-2]) * kb
    elif sz == "mb":
        return int(size[:-2]) * kb * kb
    elif sz == "gb":
        return int(size[:-2]) * kb * kb * kb
    elif sz == "tb":
        return int(size[:-2]) * kb * kb * kb * kb


def convert_to_time_delta(time):
    """
    function to convert execution time in time delta format
    """
    hrs = time[:2]
    mnt = time[3:5]
    sec = time[6:8]
    return datetime.timedelta(hours=hrs, minutes=mnt, seconds=sec)


def test_parser(yaml_file):
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
