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
    return datetime_obj


def test_parser(yaml_file):
    """
    parse a test yaml file
    :param yaml_file: accepts and parses a test YAML file
    :return python dictionary containing file contents
    """
    size_types = ["object_size", "part_size"]
    s3_io_test = yaml_parser(yaml_file)
    delta_list = list()
    for test, data in s3_io_test.items():
        if "object_size" not in data:
            logger.error("Object size is compulsory")
            return False
        for size_type in size_types:
            if size_type in data:
                if isinstance(data[size_type], dict):
                    if "start" not in data[size_type] or "end" not in data[size_type]:
                        logger.error("Please define range using start and end keys")
                        return False
                    data[size_type]["start"] = convert_to_bytes(data[size_type]["start"])
                    data[size_type]["end"] = convert_to_bytes(data[size_type]["end"])
                else:
                    size = data[size_type]
                    data[size_type] = {}
                    data[size_type]["start"] = convert_to_bytes(size)
                    data[size_type]["end"] = convert_to_bytes(size) + 1
        if test == "test_1":
            data['start_time'] = datetime.timedelta(hours=00, minutes=00, seconds=00)
            delta_list.append(convert_to_time_delta(data['result_duration']))
        else:
            data['start_time'] = delta_list.pop()
            delta_list.append(data['start_time'] + convert_to_time_delta(data['result_duration']))
        data['result_duration'] = convert_to_time_delta(data['result_duration'])
        if "part_size" not in data:
            data["part_size"] = {}
            data["part_size"]["start"] = 0
            data["part_size"]["end"] = 0
    logger.debug("test object %s: ", s3_io_test)
    return s3_io_test
