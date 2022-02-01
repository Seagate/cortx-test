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
    return yaml_file


def test_parser():
    s3_io_test = yaml_parser()
    
