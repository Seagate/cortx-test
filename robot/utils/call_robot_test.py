#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""Function to call robot in python file"""

import os
import logging
from robot import run_cli

LOGGER = logging.getLogger(__name__)


def trigger_robot(arg_dict):
    """
    Trigger robot test
    """
    try:
        log_path = os.path.join(arg_dict['log_path'], 'output.xml')
    except KeyError:
        LOGGER.error("Log path is not provided")
        return False
    cmd_line = form_run_cli_cmd(arg_dict)
    print(cmd_line)
    LOGGER.info("Robot command line is {}".format(cmd_line))
    print('Run robot command line')
    run_cli(cmd_line, exit=False)
    print('Robot cli execution done')
    LOGGER.info("Robot log path is {}".format(log_path))
    with open(log_path, 'r') as f:
        data = f.read()
        if 'status="FAIL"' in data:
            LOGGER.error("Robot test failed")
            return False
        else:
            LOGGER.info("Robot test passed")
            return True


def form_run_cli_cmd(arg_dict):
    """
    Form command line for robot test
    """
    cmd = []
    for k, v in arg_dict.items():
        if k == 'log_path':
            cmd.append('-d')
            cmd.append(v)
        elif k == 'variable':
            for item in v:
                cmd.append('-v')
                cmd.append(item)
        elif k == 'tag':
            cmd.append('-i')
            cmd.append(v)
    cmd.append('testsuites/gui/.')
    return cmd
